from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
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


def first_scheduled_clock(schedule: object) -> time | None:
    if not isinstance(schedule, list):
        return None
    clocks: list[time] = []
    for item in schedule:
        if not isinstance(item, dict):
            continue
        raw_value = item.get("time") or item.get("scheduled_time")
        if not isinstance(raw_value, str):
            continue
        try:
            clocks.append(datetime.strptime(raw_value.strip(), "%H:%M").time())
        except ValueError:
            continue
    return min(clocks) if clocks else None


def pre_schedule_pending(payload: dict[str, Any], schedule: object) -> bool:
    generated_at = str(payload.get("generated_at") or "").strip()
    today_report = payload.get("today_work_report")
    if not generated_at or not isinstance(today_report, dict):
        return False
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if str(today_report.get("date") or "")[:10] != generated.date().isoformat():
        return False
    first_clock = first_scheduled_clock(schedule)
    return first_clock is not None and generated.time() < first_clock


def operational_update_signal(payload: dict[str, Any]) -> dict[str, Any]:
    generated_at = str(payload.get("generated_at") or "")
    generated_date = generated_at[:10]
    today_report = payload.get("today_work_report")
    operational_updates = []
    if isinstance(today_report, dict):
        raw_updates = today_report.get("operational_updates")
        if isinstance(raw_updates, list):
            operational_updates = [item for item in raw_updates if isinstance(item, dict)]
    latest_date = str(payload.get("latest_recommendation_date") or "")
    latest_recommendations = payload.get("latest_recommendations")
    if not isinstance(latest_recommendations, list):
        latest_recommendations = []
    latest_market_counts = payload.get("latest_market_counts")
    if not isinstance(latest_market_counts, dict):
        latest_market_counts = {}

    if not latest_date:
        current_state = payload.get("current_state")
        if isinstance(current_state, dict):
            daily = current_state.get("daily_recommendations")
            if isinstance(daily, dict):
                latest_date = str(daily.get("latest_recommendation_date") or "")
                latest_rows = daily.get("latest_rows")
                if not latest_recommendations and isinstance(latest_rows, list):
                    latest_recommendations = latest_rows
                counts = daily.get("latest_market_counts")
                if not latest_market_counts and isinstance(counts, dict):
                    latest_market_counts = counts

    recommendation_count = len(latest_recommendations)
    kr_count = int(latest_market_counts.get("KR") or 0)
    us_count = int(latest_market_counts.get("US") or 0)
    has_today_recommendations = (
        bool(generated_date)
        and latest_date == generated_date
        and recommendation_count >= 6
        and kr_count >= 3
        and us_count >= 3
    )
    has_reported_operational_update = any(
        str(item.get("date") or "").strip()[:10] == generated_date
        for item in operational_updates
    )
    return {
        "has_operational_update_today": has_today_recommendations or has_reported_operational_update,
        "pre_schedule_pending": pre_schedule_pending(payload, payload.get("next_schedule")),
        "latest_recommendation_date": latest_date,
        "recommendation_count": recommendation_count,
        "latest_market_counts": {"KR": kr_count, "US": us_count},
        "operational_update_count": len(operational_updates),
    }


def validate_payload(payload: dict[str, Any], markdown: str) -> list[str]:
    if payload.get("schema") != "openclaw_investment_research_first_read_v1":
        raise AssertionError("first-read schema mismatch")

    today_report = payload.get("today_work_report")
    if not isinstance(today_report, dict):
        raise AssertionError("today_work_report missing from first-read payload")
    commit_count = int(today_report.get("commit_count") or 0)
    has_implementation = today_report.get("has_implementation_today") is True and commit_count > 0
    operational = operational_update_signal(payload)
    if (
        not has_implementation
        and not operational["has_operational_update_today"]
        and not operational["pre_schedule_pending"]
    ):
        raise AssertionError("today_work_report or latest operational data must indicate today's work")

    categories = today_report.get("implemented_categories") or today_report.get("categories")
    if not isinstance(categories, list):
        categories = []
    category_ids = {
        str(item.get("id") or item.get("key") or "")
        for item in categories
        if isinstance(item, dict)
    }
    category_ids.discard("")
    if has_implementation and not category_ids:
        raise AssertionError("today_work_report categories must include id/key values")

    latest_commits = today_report.get("latest_commits")
    if has_implementation and (not isinstance(latest_commits, list) or not latest_commits):
        raise AssertionError("today_work_report latest_commits must be non-empty")

    schedule = payload.get("next_schedule")
    if not isinstance(schedule, list) or not schedule:
        raise AssertionError("next_schedule must be non-empty")
    schedule_text = json.dumps(schedule, ensure_ascii=False)
    for required in ("07:00", "07:10", "07:20", "22:00"):
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
    valid_answer_states = (
        "오늘 구현 작업",
        "오늘 운영 작업",
        "오늘 정기 운영 시작 전 상태",
        "다음 스케줄",
    )
    if not any(state in correction_text for state in valid_answer_states):
        raise AssertionError("answer_correction must describe today's work, scheduled pre-start state, or next schedule")

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
        f"work_signal={'implementation' if has_implementation else ('pre_schedule_pending' if operational['pre_schedule_pending'] else 'operational_data')}",
        f"latest_recommendation_date={operational['latest_recommendation_date']}",
        f"recommendation_count={operational['recommendation_count']}",
        f"operational_update_count={operational['operational_update_count']}",
        f"categories={len(category_ids)}",
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
    commit_count = int(today_report.get("commit_count") or 0)
    has_implementation = today_report.get("has_implementation_today") is True and commit_count > 0
    operational = operational_update_signal(payload)
    if has_implementation:
        answer_heading = "오늘 구현 작업 보고"
    elif operational["pre_schedule_pending"]:
        answer_heading = "오늘 정기 운영 시작 전 상태"
    else:
        answer_heading = "오늘 운영 작업 보고"
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
            "must_include": [
                answer_heading,
                "다음 스케줄",
            ],
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
