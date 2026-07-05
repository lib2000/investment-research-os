from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
FIRST_READ_MARKDOWN_FILE = "openclaw_first_read.md"


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


def load_markdown(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"required file not found: {path}")
    return path.read_text(encoding="utf-8-sig")


def validate_payload(payload: dict[str, Any], markdown: str) -> list[str]:
    if payload.get("schema") != "openclaw_investment_research_first_read_v1":
        raise AssertionError("first-read schema mismatch")

    today_report = payload.get("today_work_report")
    if not isinstance(today_report, dict):
        raise AssertionError("today_work_report missing from first-read payload")
    if today_report.get("has_implementation_today") is not True:
        raise AssertionError("today_work_report must mark has_implementation_today=true")
    commit_count = int(today_report.get("commit_count") or 0)
    if commit_count <= 0:
        raise AssertionError("today_work_report commit_count must be positive")

    categories = today_report.get("implemented_categories") or today_report.get("categories")
    if not isinstance(categories, list) or not categories:
        raise AssertionError("today_work_report categories must be non-empty")
    category_ids = {
        str(item.get("id") or item.get("key") or "")
        for item in categories
        if isinstance(item, dict)
    }
    for required in ("openclaw_bridge", "telegram_pipeline", "local_ai_agent_foundation"):
        if required not in category_ids:
            raise AssertionError(f"today_work_report missing required category: {required}")

    latest_commits = today_report.get("latest_commits")
    if not isinstance(latest_commits, list) or not latest_commits:
        raise AssertionError("today_work_report latest_commits must be non-empty")

    schedule = payload.get("next_schedule")
    if not isinstance(schedule, list) or not schedule:
        raise AssertionError("next_schedule must be non-empty")
    schedule_text = json.dumps(schedule, ensure_ascii=False)
    for required in ("07:00", "07:20", "08:00", "22:00"):
        if required not in schedule_text:
            raise AssertionError(f"next_schedule missing required time: {required}")

    answer_correction = payload.get("answer_correction")
    if not isinstance(answer_correction, dict):
        raise AssertionError("answer_correction missing")
    wrong_claim = str(answer_correction.get("wrong_claim") or "")
    correction_text = " ".join(
        str(item or "")
        for item in (
            answer_correction.get("required_reply"),
            answer_correction.get("expected_answer"),
            answer_correction.get("correct_basis"),
            today_report.get("correction_for_openclaw"),
        )
    )
    if "오늘 구현 작업 없음" not in wrong_claim and "특별히 새로 구현된 작업" not in wrong_claim:
        raise AssertionError("answer_correction must include the stale no-work claim")
    if "today_work_report" not in correction_text:
        raise AssertionError("answer_correction must route answers through today_work_report")
    if "오늘 구현 작업" not in correction_text and "다음 스케줄" not in correction_text:
        raise AssertionError("answer_correction must describe today's work or next schedule")

    for required_text in (
        "Today Implementation Report",
        "Latest Today Commits",
        "Next Schedule",
        "Answer Correction",
        "wrong claim to avoid",
        "today_work_report",
    ):
        if required_text not in markdown:
            raise AssertionError(f"first-read Markdown missing required answer text: {required_text}")

    return [
        f"commit_count={commit_count}",
        f"categories={len(categories)}",
        f"schedule_items={len(schedule)}",
    ]


def build_result(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR) -> dict[str, Any]:
    first_read_json = openclaw_dir / FIRST_READ_JSON_FILE
    first_read_markdown = openclaw_dir / FIRST_READ_MARKDOWN_FILE
    payload = load_json(first_read_json)
    markdown = load_markdown(first_read_markdown)
    messages = validate_payload(payload, markdown)
    today_report = payload.get("today_work_report") or {}
    schedule = payload.get("next_schedule") or []
    return {
        "status": "ok",
        "openclaw_dir": str(openclaw_dir),
        "generated_at": payload.get("generated_at"),
        "today_commit_count": today_report.get("commit_count"),
        "today_categories": [
            item.get("id") or item.get("key")
            for item in (today_report.get("implemented_categories") or today_report.get("categories") or [])
            if isinstance(item, dict)
        ],
        "next_schedule_count": len(schedule),
        "messages": messages,
        "expected_answer_summary": {
            "must_not_answer": "오늘 구현 작업 없음",
            "must_include": ["오늘 구현 작업 보고", "다음 스케줄"],
        },
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw today-answer readiness: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- generated_at: {result.get('generated_at')}",
        f"- today_commit_count: {result.get('today_commit_count')}",
        f"- next_schedule_count: {result.get('next_schedule_count')}",
        "- today_categories:",
    ]
    for category in result.get("today_categories") or []:
        lines.append(f"  - {category}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify OpenClaw first-read context can answer today's work report and next schedule."
    )
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(args.openclaw_dir.resolve())
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"OpenClaw today-answer readiness: failure\n- error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
