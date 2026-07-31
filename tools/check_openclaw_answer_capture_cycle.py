from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_answer_capture_cycle_state.json"
TOOLS_DIR = Path(__file__).resolve().parent


def load_tool(module_name: str):
    path = TOOLS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load OpenClaw capture cycle module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector_tool = load_tool("collect_openclaw_pending_answers")
status_tool = load_tool("check_openclaw_actual_answer_capture_status")
audit_tool = load_tool("check_openclaw_actual_answer_audit")


def write_state_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_result(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    *,
    collect: bool = False,
    archive_failures: bool = False,
    write_state: bool = False,
    state_file: Path = DEFAULT_STATE_FILE,
    require_recent: bool = False,
    require_routes: list[str] | None = None,
    max_age_hours: float = 24.0,
) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    errors: list[str] = []
    collector = collector_tool.collect_pending_answers(
        openclaw_dir,
        dry_run=not collect,
        audit=True,
        archive_failures=archive_failures,
    )
    if collector.get("status") != "ok":
        errors.extend(f"collector: {error}" for error in collector.get("errors") or ["pending answer collector failed"])
    capture_status = status_tool.build_result(
        openclaw_dir,
        max_age_hours=max_age_hours,
        require_recent=require_recent,
        require_routes=require_routes or [],
    )
    if capture_status.get("status") != "ok":
        errors.extend(f"capture_status: {error}" for error in capture_status.get("errors") or ["capture status failed"])
    audit = audit_tool.build_result(openclaw_dir, require_answers=require_recent)
    if audit.get("status") != "ok":
        errors.extend(f"audit: {error}" for error in audit.get("errors") or ["actual answer audit failed"])

    result = {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "collect": collect,
        "archive_failures": archive_failures,
        "checked_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "collector": collector,
        "capture_status": capture_status,
        "audit": audit,
        "state_file": str(state_file.resolve()),
        "state_written": False,
    }
    if write_state:
        write_state_file(state_file.resolve(), result)
        result["state_written"] = True
    return result


def render_text(result: dict[str, Any]) -> str:
    collector = result.get("collector") or {}
    capture_status = result.get("capture_status") or {}
    latest = (capture_status.get("latest_capture") or {}) if isinstance(capture_status, dict) else {}
    audit = result.get("audit") or {}
    lines = [
        f"OpenClaw answer capture cycle: {result.get('status')}",
        f"- collect: {result.get('collect')}",
        f"- pending_count: {collector.get('pending_count')}",
        f"- captured_count: {collector.get('captured_count')}",
        f"- failed_count: {collector.get('failed_count')}",
        f"- total_capture_count: {capture_status.get('capture_count')}",
        f"- latest_route: {latest.get('route_id')}",
        f"- latest_age_hours: {latest.get('age_hours')}",
        f"- audited_count: {audit.get('audited_count')}",
        f"- state_written: {result.get('state_written')}",
    ]
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OpenClaw pending-answer capture cycle.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--collect", action="store_true", help="Capture and archive pending answers instead of dry-run scanning.")
    parser.add_argument("--archive-failures", action="store_true")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--require-recent", action="store_true")
    parser.add_argument("--require-route", action="append", default=[])
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_result(
            args.openclaw_dir,
            collect=args.collect,
            archive_failures=args.archive_failures,
            write_state=args.write_state,
            state_file=args.state_file,
            require_recent=args.require_recent,
            require_routes=args.require_route,
            max_age_hours=args.max_age_hours,
        )
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
