from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
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


def pre_schedule_pending(payload: dict[str, Any], schedule: object) -> tuple[bool, str]:
    """Allow a clean first-read generated before the day's first scheduled operation.

    The condition is intentionally narrow: the report date must match the generated
    date and the generated clock must be before an explicit clock-form schedule item.
    Once the first operation is due, a same-day update is still required.
    """
    generated_at = str(payload.get("generated_at") or "").strip()
    today_report = payload.get("today_work_report")
    if not generated_at or not isinstance(today_report, dict):
        return False, ""
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return False, ""
    if str(today_report.get("date") or "")[:10] != generated.date().isoformat():
        return False, ""
    first_clock = first_scheduled_clock(schedule)
    if first_clock is None or generated.time() >= first_clock:
        return False, ""
    return True, first_clock.strftime("%H:%M")


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
    pending_before_first_schedule, first_scheduled_time = pre_schedule_pending(
        payload,
        payload.get("next_schedule"),
    )
    return {
        "has_operational_update_today": has_today_recommendations or has_reported_operational_update,
        "pre_schedule_pending": pending_before_first_schedule,
        "first_scheduled_time": first_scheduled_time,
        "generated_date": generated_date,
        "latest_recommendation_date": latest_date,
        "recommendation_count": recommendation_count,
        "latest_market_counts": {"KR": kr_count, "US": us_count},
        "operational_update_count": len(operational_updates),
        "operational_updates": operational_updates,
    }


def build_expected_answer(payload: dict[str, Any]) -> str:
    today_report = payload.get("today_work_report") or {}
    schedule = payload.get("next_schedule") or []
    commit_count = int(today_report.get("commit_count") or 0)
    operational = operational_update_signal(payload)
    has_implementation = today_report.get("has_implementation_today") is True and commit_count > 0
    if has_implementation:
        lines = [
            "오늘 구현 작업 보고",
            f"- 기준 파일: openclaw_first_read.json / bridge_status.json",
            f"- 오늘 반영 커밋: {commit_count}건",
        ]
        for item in compact_summary_items(today_report):
            lines.append(f"- {item}")
    elif operational["pre_schedule_pending"]:
        counts = operational["latest_market_counts"]
        lines = [
            "오늘 정기 운영 시작 전 상태",
            f"- 기준 파일: openclaw_first_read.json / bridge_status.json",
            f"- 첫 예정 작업: {operational['first_scheduled_time']}",
            f"- 최신 추천 기준일: {operational['latest_recommendation_date']}",
            f"- 최신 추천 저장: {operational['recommendation_count']}개 (KR {counts['KR']} / US {counts['US']})",
        ]
    else:
        counts = operational["latest_market_counts"]
        lines = [
            "오늘 운영 작업 보고",
            f"- 기준 파일: openclaw_first_read.json / bridge_status.json",
            f"- 최신 추천 기준일: {operational['latest_recommendation_date']}",
            f"- 오늘 추천 저장: {operational['recommendation_count']}개 (KR {counts['KR']} / US {counts['US']})",
        ]
        for item in operational.get("operational_updates") or []:
            label = item.get("label") or item.get("key") or "운영 데이터 갱신"
            status = item.get("status") or "updated"
            lines.append(f"- {label}: {status}")
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
    has_implementation = today_report.get("has_implementation_today") is True and commit_count > 0
    operational = operational_update_signal(payload)
    if (
        not has_implementation
        and not operational["has_operational_update_today"]
        and not operational["pre_schedule_pending"]
    ):
        errors.append("today_work_report or latest operational data must indicate today's work")

    schedule = payload.get("next_schedule")
    if not isinstance(schedule, list) or not schedule:
        errors.append("next_schedule must be non-empty")

    for banned in BANNED_STALE_CLAIMS:
        if banned in answer:
            errors.append(f"answer contains banned stale claim: {banned}")

    required_fragments = ["다음 스케줄"]
    if has_implementation:
        required_fragments.extend(["오늘 구현 작업 보고", str(commit_count)])
    elif operational["pre_schedule_pending"]:
        required_fragments.extend([
            "오늘 정기 운영 시작 전 상태",
            str(operational["first_scheduled_time"]),
            str(operational["latest_recommendation_date"]),
            str(operational["recommendation_count"]),
        ])
    else:
        required_fragments.extend([
            "오늘 운영 작업 보고",
            str(operational["latest_recommendation_date"]),
            str(operational["recommendation_count"]),
        ])
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
        f"work_signal={'implementation' if has_implementation else ('pre_schedule_pending' if operational['pre_schedule_pending'] else 'operational_data')}",
        f"latest_recommendation_date={operational['latest_recommendation_date']}",
        f"recommendation_count={operational['recommendation_count']}",
        f"operational_update_count={operational['operational_update_count']}",
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
