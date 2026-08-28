from __future__ import annotations

import argparse
import importlib.util
import json
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


def load_sibling_tool(module_name: str):
    path = TOOLS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load sibling tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


answer_samples = load_sibling_tool("check_openclaw_answer_samples")
priority_quality = load_sibling_tool("check_openclaw_priority_answer_quality")
today_quality = load_sibling_tool("check_openclaw_today_answer_quality")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"required file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def route_from_filename(path: Path) -> str:
    stem = path.stem
    for route_id in ROUTE_IDS:
        if stem == route_id or stem.startswith(f"{route_id}.") or stem.startswith(f"{route_id}_"):
            return route_id
    return stem


def answer_text_from_json(payload: dict[str, Any]) -> str:
    for key in ("answer", "text", "content", "response", "reply", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise AssertionError("answer JSON must include one of: answer, text, content, response, reply, message")


def route_id_from_json(payload: dict[str, Any], fallback: str) -> str:
    for key in ("route_id", "route", "id", "question_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def iter_answer_records(answers_dir: Path) -> list[dict[str, str]]:
    if not answers_dir.exists():
        return []
    if not answers_dir.is_dir():
        raise AssertionError(f"answers path must be a directory: {answers_dir}")
    records: list[dict[str, str]] = []
    for path in sorted(answers_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        fallback_route = route_from_filename(path)
        if path.suffix.lower() == ".json":
            payload = load_json(path)
            records.append(
                {
                    "path": str(path),
                    "route_id": route_id_from_json(payload, fallback_route),
                    "answer": answer_text_from_json(payload),
                }
            )
        elif path.suffix.lower() == ".jsonl":
            for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise AssertionError(f"JSONL row must be object: {path}:{index}")
                records.append(
                    {
                        "path": f"{path}:{index}",
                        "route_id": route_id_from_json(payload, fallback_route),
                        "answer": answer_text_from_json(payload),
                    }
                )
        else:
            records.append(
                {
                    "path": str(path),
                    "route_id": fallback_route,
                    "answer": path.read_text(encoding="utf-8-sig"),
                }
            )
    return records


def required_fragments_for(
    route_id: str,
    *,
    first_read: dict[str, Any],
    bridge_status: dict[str, Any],
) -> list[str]:
    if route_id == "today_work_report":
        today_report = first_read.get("today_work_report") or {}
        commit_count = int(today_report.get("commit_count") or 0)
        if today_report.get("has_implementation_today") is True and commit_count > 0:
            return ["오늘 구현 작업 보고", "다음 스케줄", str(commit_count)]
        operational = today_quality.operational_update_signal(first_read)
        if operational["pre_schedule_pending"]:
            return ["오늘 정기 운영 시작 전 상태", "다음 스케줄", str(operational["first_scheduled_time"])]
        return ["오늘 운영 작업 보고", "다음 스케줄"]
    if route_id == "recommendations_priority":
        return [
            "오늘 추천 종목",
            "중요 메시지",
            "KR#1",
            "US#1",
            str((first_read.get("telegram") or {}).get("favorite_saved_count")),
        ]
    if route_id == "bridge_status_completion":
        return ["OpenClaw 연동 상태", "source git", "final audit", str(bridge_status.get("source_git_commit"))]
    if route_id == "knowledge_graph_context":
        return ["투자 방향과 지식 그래프 컨텍스트", "graph schema", "seed nodes", "시장별 추천"]
    return []


def validate_record(record: dict[str, str], *, first_read: dict[str, Any], bridge_status: dict[str, Any]) -> list[str]:
    route_id = record["route_id"]
    answer = record["answer"]
    if route_id not in ROUTE_IDS:
        return [f"unknown route_id: {route_id}"]
    errors: list[str] = []
    if route_id == "today_work_report":
        try:
            today_quality.validate_answer_quality(first_read, answer)
        except AssertionError as exc:
            errors.append(str(exc))
    elif route_id == "recommendations_priority":
        try:
            priority_quality.validate_answer_quality(first_read, answer)
        except AssertionError as exc:
            errors.append(str(exc))
    errors.extend(
        answer_samples.validate_answer(
            route_id,
            answer,
            required_fragments_for(route_id, first_read=first_read, bridge_status=bridge_status),
        )
    )
    return errors


def build_result(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    answers_dir: Path | None = None,
    *,
    require_answers: bool = False,
) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    answers_dir = (answers_dir or (openclaw_dir / DEFAULT_ANSWERS_DIR_NAME)).resolve()
    first_read = load_json(openclaw_dir / "openclaw_first_read.json")
    bridge_status = load_json(openclaw_dir / "bridge_status.json")
    records = iter_answer_records(answers_dir)
    errors: list[str] = []
    if require_answers and not records:
        errors.append(f"no actual answer files found: {answers_dir}")
    results = []
    for record in records:
        record_errors = validate_record(record, first_read=first_read, bridge_status=bridge_status)
        errors.extend(f"{record['path']}: {error}" for error in record_errors)
        results.append(
            {
                "path": record["path"],
                "route_id": record["route_id"],
                "status": "ok" if not record_errors else "failure",
                "answer_preview": record["answer"][:800],
                "errors": record_errors,
            }
        )
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "answers_dir": str(answers_dir),
        "audited_count": len(records),
        "require_answers": require_answers,
        "generated_at": first_read.get("generated_at"),
        "source_git": {
            "branch": bridge_status.get("source_git_branch"),
            "commit": bridge_status.get("source_git_commit"),
            "dirty": bridge_status.get("source_git_dirty"),
        },
        "answers": results,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw actual-answer audit: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- answers_dir: {result.get('answers_dir')}",
        f"- audited_count: {result.get('audited_count')}",
    ]
    for item in result.get("answers") or []:
        lines.append(f"  - {item.get('route_id')}: {item.get('status')} | {item.get('path')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit captured OpenClaw actual answers against bridge evidence.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--answers-dir", type=Path)
    parser.add_argument("--require-answers", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_result(
            args.openclaw_dir,
            args.answers_dir,
            require_answers=args.require_answers,
        )
    except (AssertionError, json.JSONDecodeError) as exc:
        result = {
            "status": "failure",
            "errors": [str(exc)],
            "openclaw_dir": str(args.openclaw_dir.resolve()),
        }
        if args.answers_dir:
            result["answers_dir"] = str(args.answers_dir.resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
