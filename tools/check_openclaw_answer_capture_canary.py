"""Run a disposable OpenClaw answer-capture canary without polluting live answers."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
TOOLS_DIR = Path(__file__).resolve().parent
REQUIRED_SOURCE_FILES = (
    "bridge_status.json",
    "openclaw_first_read.json",
)


def load_tool(module_name: str):
    path = TOOLS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load OpenClaw canary module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector_tool = load_tool("collect_openclaw_pending_answers")
status_tool = load_tool("check_openclaw_actual_answer_capture_status")
audit_tool = load_tool("check_openclaw_actual_answer_audit")
today_quality_tool = load_tool("check_openclaw_today_answer_quality")
priority_quality_tool = load_tool("check_openclaw_priority_answer_quality")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"required OpenClaw canary source file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def copy_canary_bundle(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILES:
        source_path = source_dir / filename
        if not source_path.exists():
            raise AssertionError(f"required OpenClaw canary source file not found: {source_path}")
        shutil.copy2(source_path, target_dir / filename)


def build_canary_answer(route_id: str, first_read: dict[str, Any]) -> str:
    if route_id == "today_work_report":
        return today_quality_tool.build_expected_answer(first_read)
    if route_id == "recommendations_priority":
        return priority_quality_tool.build_expected_answer(first_read)
    raise AssertionError(f"unsupported canary route_id: {route_id}")


def write_pending_answer(openclaw_dir: Path, *, route_id: str, answer: str) -> Path:
    pending_dir = openclaw_dir / "pending_actual_answers"
    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_file = pending_dir / f"{route_id}.canary.json"
    pending_file.write_text(
        json.dumps(
            {
                "route_id": route_id,
                "source": "openclaw_answer_capture_canary",
                "answer": answer,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return pending_file


def run_canary_in_dir(canary_dir: Path, *, route_id: str) -> dict[str, Any]:
    first_read = load_json(canary_dir / "openclaw_first_read.json")
    answer = build_canary_answer(route_id, first_read)
    pending_file = write_pending_answer(canary_dir, route_id=route_id, answer=answer)
    collector = collector_tool.collect_pending_answers(canary_dir, dry_run=False, audit=True)
    capture_status = status_tool.build_result(
        canary_dir,
        require_recent=True,
        require_routes=[route_id],
    )
    audit = audit_tool.build_result(canary_dir, require_answers=True)
    pending_exists = pending_file.exists()
    processed_files = sorted(str(path) for path in (canary_dir / "processed_actual_answers").glob(f"{route_id}*"))
    answer_files = sorted(str(path) for path in (canary_dir / "actual_answers").glob(f"{route_id}*"))
    errors: list[str] = []
    for label, payload in (("collector", collector), ("capture_status", capture_status), ("audit", audit)):
        if payload.get("status") != "ok":
            errors.extend(f"{label}: {error}" for error in payload.get("errors") or [f"{label} failed"])
    if pending_exists:
        errors.append("canary pending file was not archived")
    if len(processed_files) != 1:
        errors.append(f"expected one processed canary file, found {len(processed_files)}")
    if len(answer_files) != 1:
        errors.append(f"expected one actual answer canary file, found {len(answer_files)}")
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "route_id": route_id,
        "canary_dir": str(canary_dir),
        "pending_file_archived": not pending_exists,
        "processed_files": processed_files,
        "answer_files": answer_files,
        "collector": collector,
        "capture_status": capture_status,
        "audit": audit,
    }


def build_result(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    *,
    route_id: str = "today_work_report",
    keep_artifacts: bool = False,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = openclaw_dir.resolve()
    if keep_artifacts:
        canary_dir = (artifacts_dir or (source_dir / "_canary_answer_capture")).resolve()
        if canary_dir.exists():
            shutil.rmtree(canary_dir)
        copy_canary_bundle(source_dir, canary_dir)
        result = run_canary_in_dir(canary_dir, route_id=route_id)
        result["artifacts_kept"] = True
    else:
        with tempfile.TemporaryDirectory(prefix="openclaw-answer-canary-") as tmp:
            canary_dir = Path(tmp) / "investment_research"
            copy_canary_bundle(source_dir, canary_dir)
            result = run_canary_in_dir(canary_dir, route_id=route_id)
            result["artifacts_kept"] = False
    result["source_openclaw_dir"] = str(source_dir)
    return result


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw answer capture canary: {result.get('status')}",
        f"- source_openclaw_dir: {result.get('source_openclaw_dir')}",
        f"- route_id: {result.get('route_id')}",
        f"- artifacts_kept: {result.get('artifacts_kept')}",
        f"- pending_file_archived: {result.get('pending_file_archived')}",
        f"- processed_count: {len(result.get('processed_files') or [])}",
        f"- answer_count: {len(result.get('answer_files') or [])}",
    ]
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a disposable OpenClaw pending-answer capture canary.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--route-id", choices=["today_work_report", "recommendations_priority"], default="today_work_report")
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument("--artifacts-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_result(
            args.openclaw_dir,
            route_id=args.route_id,
            keep_artifacts=args.keep_artifacts,
            artifacts_dir=args.artifacts_dir,
        )
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "failure", "errors": [str(exc)], "source_openclaw_dir": str(args.openclaw_dir.resolve())}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
