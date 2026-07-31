from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
DEFAULT_ANSWERS_DIR_NAME = "actual_answers"
TOOLS_DIR = Path(__file__).resolve().parent
ROUTE_IDS = {
    "today_work_report",
    "recommendations_priority",
    "bridge_status_completion",
    "knowledge_graph_context",
}


def load_audit_tool():
    path = TOOLS_DIR / "check_openclaw_actual_answer_audit.py"
    spec = importlib.util.spec_from_file_location("check_openclaw_actual_answer_audit", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load audit tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be object: {path}")
    return payload


def read_answer(args: argparse.Namespace) -> str:
    sources = [bool(args.answer), bool(args.answer_file), bool(args.stdin)]
    if sum(sources) != 1:
        raise AssertionError("provide exactly one answer source: --answer, --answer-file, or --stdin")
    if args.answer:
        answer = args.answer
    elif args.answer_file:
        answer = args.answer_file.read_text(encoding="utf-8-sig")
    else:
        answer = sys.stdin.read()
    if not answer.strip():
        raise AssertionError("answer text must not be empty")
    return answer


def safe_timestamp(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "-", value).strip("-")


def default_output_path(answers_dir: Path, route_id: str, captured_at: str) -> Path:
    answers_dir.mkdir(parents=True, exist_ok=True)
    return answers_dir / f"{route_id}.{safe_timestamp(captured_at)}.json"


def build_capture_payload(
    *,
    route_id: str,
    answer: str,
    openclaw_dir: Path,
    captured_at: str,
    source: str | None = None,
) -> dict[str, Any]:
    bridge_status = read_json(openclaw_dir / "bridge_status.json")
    first_read = read_json(openclaw_dir / "openclaw_first_read.json")
    return {
        "schema": "openclaw_actual_answer_capture_v1",
        "route_id": route_id,
        "captured_at": captured_at,
        "source": source or "manual",
        "answer": answer,
        "bridge_generated_at": first_read.get("generated_at"),
        "source_git": {
            "branch": bridge_status.get("source_git_branch"),
            "commit": bridge_status.get("source_git_commit"),
            "dirty": bridge_status.get("source_git_dirty"),
        },
    }


def build_result(
    *,
    route_id: str,
    answer: str,
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    answers_dir: Path | None = None,
    output_file: Path | None = None,
    source: str | None = None,
    audit: bool = False,
) -> dict[str, Any]:
    if route_id not in ROUTE_IDS:
        raise AssertionError(f"unknown route_id: {route_id}")
    openclaw_dir = openclaw_dir.resolve()
    answers_dir = (answers_dir or (openclaw_dir / DEFAULT_ANSWERS_DIR_NAME)).resolve()
    captured_at = datetime.now().astimezone().replace(microsecond=0).isoformat()
    output_file = (output_file or default_output_path(answers_dir, route_id, captured_at)).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = build_capture_payload(
        route_id=route_id,
        answer=answer,
        openclaw_dir=openclaw_dir,
        captured_at=captured_at,
        source=source,
    )
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_result = None
    errors: list[str] = []
    if audit:
        audit_tool = load_audit_tool()
        audit_result = audit_tool.build_result(openclaw_dir, answers_dir, require_answers=True)
        if audit_result.get("status") != "ok":
            errors.extend(audit_result.get("errors") or ["actual answer audit failed"])
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "answers_dir": str(answers_dir),
        "output_file": str(output_file),
        "route_id": route_id,
        "captured_at": captured_at,
        "audit": audit_result,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw actual-answer capture: {result.get('status')}",
        f"- route_id: {result.get('route_id')}",
        f"- output_file: {result.get('output_file')}",
    ]
    audit = result.get("audit") or {}
    if audit:
        lines.append(f"- audit: {audit.get('status')} audited_count={audit.get('audited_count')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture an OpenClaw actual answer and optionally audit it.")
    parser.add_argument("--route-id", required=True, choices=sorted(ROUTE_IDS))
    parser.add_argument("--answer")
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--answers-dir", type=Path)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_result(
            route_id=args.route_id,
            answer=read_answer(args),
            openclaw_dir=args.openclaw_dir,
            answers_dir=args.answers_dir,
            output_file=args.output_file,
            source=args.source,
            audit=args.audit,
        )
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "failure", "errors": [str(exc)], "route_id": args.route_id}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
