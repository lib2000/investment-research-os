from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
BANNED_STALE_CLAIMS = [
    "오늘 구현 작업 없음",
    "특별히 새로 구현된 작업 기록 없음",
    "오늘 시스템에 새로 구현되거나 변경된 작업은 없습니다",
    "오늘 별도로 요청하신 추가 구현 작업은 없었습니다",
    "새로운 기능 개발이나 코드 수정 활동을 수행하지 않았습니다",
]


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


def compact_summary_items(today_report: dict[str, Any]) -> list[str]:
    summary = today_report.get("summary")
    if isinstance(summary, list) and summary:
        return [str(item) for item in summary[:6]]
    categories = today_report.get("implemented_categories") or today_report.get("categories") or []
    items: list[str] = []
    for category in categories:
        if not isinstance(category, dict):
            continue
        title = category.get("title") or category.get("name") or category.get("id") or category.get("key")
        if title:
            items.append(str(title))
    return items[:6]


def build_expected_answer(payload: dict[str, Any]) -> str:
    today_report = payload.get("today_work_report") or {}
    schedule = payload.get("next_schedule") or []
    commit_count = int(today_report.get("commit_count") or 0)
    lines = [
        "오늘 구현 작업 보고",
        f"- 기준 파일: openclaw_first_read.json / bridge_status.json",
        f"- 오늘 반영 커밋: {commit_count}건",
    ]
    for item in compact_summary_items(today_report):
        lines.append(f"- {item}")
    lines.extend(["", "다음 스케줄"])
    for item in schedule[:8]:
        if not isinstance(item, dict):
            continue
        time_text = item.get("time") or item.get("scheduled_time") or "시간 미정"
        task = item.get("task") or item.get("title") or item.get("name") or "작업"
        status = item.get("status") or "예정"
        lines.append(f"- {time_text}: {task} ({status})")
    return "\n".join(lines).strip() + "\n"


def validate_answer_quality(payload: dict[str, Any], answer: str) -> list[str]:
    errors: list[str] = []
    today_report = payload.get("today_work_report")
    if not isinstance(today_report, dict):
        raise AssertionError("today_work_report missing from first-read payload")
    commit_count = int(today_report.get("commit_count") or 0)
    if today_report.get("has_implementation_today") is not True or commit_count <= 0:
        errors.append("today_work_report must indicate positive implementation work")

    schedule = payload.get("next_schedule")
    if not isinstance(schedule, list) or not schedule:
        errors.append("next_schedule must be non-empty")

    for banned in BANNED_STALE_CLAIMS:
        if banned in answer:
            errors.append(f"answer contains banned stale claim: {banned}")

    required_fragments = [
        "오늘 구현 작업 보고",
        "다음 스케줄",
        str(commit_count),
    ]
    for item in schedule[:4]:
        if isinstance(item, dict) and item.get("time"):
            required_fragments.append(str(item["time"]))
    for fragment in required_fragments:
        if fragment and fragment not in answer:
            errors.append(f"answer missing required fragment: {fragment}")

    if "today_work_report" not in answer and "openclaw_first_read.json" not in answer and "bridge_status.json" not in answer:
        errors.append("answer must cite today_work_report, openclaw_first_read.json, or bridge_status.json as basis")

    if errors:
        raise AssertionError("; ".join(errors))
    return [
        f"commit_count={commit_count}",
        f"schedule_items={len(schedule)}",
        "banned_stale_claims_absent=true",
    ]


def build_result(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR, answer_file: Path | None = None) -> dict[str, Any]:
    payload = load_json(openclaw_dir / FIRST_READ_JSON_FILE)
    answer = answer_file.read_text(encoding="utf-8-sig") if answer_file else build_expected_answer(payload)
    messages = validate_answer_quality(payload, answer)
    today_report = payload.get("today_work_report") or {}
    return {
        "status": "ok",
        "openclaw_dir": str(openclaw_dir),
        "answer_source": str(answer_file) if answer_file else "generated_expected_answer",
        "generated_at": payload.get("generated_at"),
        "today_commit_count": today_report.get("commit_count"),
        "next_schedule_count": len(payload.get("next_schedule") or []),
        "messages": messages,
        "answer_preview": answer[:1200],
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw today-answer quality: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- answer_source: {result.get('answer_source')}",
        f"- today_commit_count: {result.get('today_commit_count')}",
        f"- next_schedule_count: {result.get('next_schedule_count')}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test OpenClaw's today-work/next-schedule answer quality.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(args.openclaw_dir.resolve(), args.answer_file.resolve() if args.answer_file else None)
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
        if args.answer_file:
            result["answer_source"] = str(args.answer_file.resolve())
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"OpenClaw today-answer quality: failure\n- error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
