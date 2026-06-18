"""Storage and schedule helpers for daily recommendations."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from re import search
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence
from research_os import daily_recommendation_tracking
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


def daily_recommendation_store_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations.json"


def daily_recommendation_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations_state.json"


def current_recommendation_datetime() -> datetime:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return datetime.now().replace(microsecond=0)
    return datetime.now(korea_timezone).replace(microsecond=0)


def parse_daily_recommendations_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.daily_recommendations_time or "08:00").strip())
    if not match:
        return 8, 0
    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return hour, minute


def should_run_daily_recommendations(settings: Settings, now: datetime | None = None) -> bool:
    if not settings.daily_recommendations_enabled:
        return False
    now = now or current_recommendation_datetime()
    hour, minute = parse_daily_recommendations_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = read_json_payload(daily_recommendation_state_path(settings), {})
    return state.get("last_run_date") != now.date().isoformat()


def read_json_payload(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_daily_recommendation_store(settings: Settings) -> dict:
    return read_json_payload(
        daily_recommendation_store_path(settings),
        {
            "module": "daily_stock_recommendations",
            "records": [],
        },
    )


def write_daily_recommendation_store(settings: Settings, payload: dict) -> None:
    payload["module"] = "daily_stock_recommendations"
    write_json_payload(daily_recommendation_store_path(settings), payload)


def parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def recommendation_record_id(recommendation_date: date, rank: int, ticker: str) -> str:
    return f"{recommendation_date.isoformat()}-{rank:02d}-{str(ticker or '').upper()}"


def build_recommendation_record(
    candidate: dict,
    *,
    rank: int,
    recommendation_date: date,
    generated_at: str,
) -> dict:
    normalized = daily_recommendation_candidates.normalize_candidate(candidate)
    baseline_price = normalized.get("baseline_price")
    return {
        "record_id": recommendation_record_id(recommendation_date, rank, normalized["ticker"]),
        "recommendation_date": recommendation_date.isoformat(),
        "generated_at": generated_at,
        "rank": rank,
        "ticker": normalized["ticker"],
        "company_name": normalized["company_name"],
        "score": normalized["score"],
        "score_components": normalized.get("score_components") or [],
        "score_explanation": normalized.get("score_explanation") or {},
        "score_penalties": normalized.get("score_penalties") or [],
        "quality_flags": normalized.get("quality_flags") or [],
        "recommendation_type": "daily_review_candidate",
        "action_label": "오늘의 검토 후보",
        "baseline_price": baseline_price,
        "baseline_price_source": normalized.get("baseline_price_source"),
        "baseline_price_checked_at": normalized.get("baseline_price_checked_at"),
        "currency": normalized.get("currency") or "KRW",
        "reasons": normalized["reasons"],
        "evidence_sources": normalized["evidence_sources"],
        "evidence_documents": normalized.get("evidence_documents") or [],
        "risk_notes": [
            str(item).strip()
            for item in normalized.get("risk_notes", [])
            if str(item or "").strip()
        ][:5],
        "portfolio_context": normalized.get("portfolio_context") or [],
        "investment_direction_profile": normalized.get("investment_direction_profile") or {},
        "portfolio_risk_connection": normalized.get("portfolio_risk_connection") or {},
        "overseas_tracking": normalized.get("overseas_tracking") or {},
        "tracking_milestones": daily_recommendation_tracking.build_tracking_milestones(recommendation_date),
    }


def upsert_daily_recommendations(
    settings: Settings,
    *,
    candidates: list[dict],
    recommendation_date: date,
    generated_at: str,
    force: bool = False,
) -> dict:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    existing_today = [
        item
        for item in records
        if item.get("recommendation_date") == recommendation_date.isoformat()
    ]
    if existing_today and not force:
        return {
            "status": "skipped_existing",
            "module": "daily_stock_recommendations",
            "message": "오늘 추천 후보는 이미 저장되어 있어 중복 저장하지 않았습니다.",
            "recommendation_date": recommendation_date.isoformat(),
            "records": sorted(existing_today, key=lambda item: int(item.get("rank") or 999))[:3],
            "storage_path": str(daily_recommendation_store_path(settings)),
        }

    if force and existing_today:
        today_ids = {item.get("record_id") for item in existing_today}
        records = [item for item in records if item.get("record_id") not in today_ids]

    new_records = [
        build_recommendation_record(
            candidate,
            rank=index + 1,
            recommendation_date=recommendation_date,
            generated_at=generated_at,
        )
        for index, candidate in enumerate(candidates[:3])
    ]
    records.extend(new_records)
    records.sort(
        key=lambda item: (
            str(item.get("recommendation_date") or ""),
            -int(item.get("rank") or 999),
        ),
        reverse=True,
    )
    store.update(
        {
            "updated_at": generated_at,
            "latest_recommendation_date": recommendation_date.isoformat(),
            "records": records,
        }
    )
    write_daily_recommendation_store(settings, store)
    return {
        "status": "success",
        "module": "daily_stock_recommendations",
        "recommendation_date": recommendation_date.isoformat(),
        "saved_count": len(new_records),
        "records": new_records,
        "storage_path": str(daily_recommendation_store_path(settings)),
    }


PriceLookup = Callable[[str], tuple[float | None, str | None]]


def update_recommendation_tracking(
    settings: Settings,
    *,
    as_of: date,
    checked_at: str,
    price_lookup: PriceLookup,
) -> dict:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    updated: list[dict] = []
    due_count = 0
    pending_count = 0
    unavailable_count = 0
    for record in records:
        baseline_price = record.get("baseline_price")
        try:
            baseline = float(baseline_price) if baseline_price is not None else None
        except (TypeError, ValueError):
            baseline = None
        milestones = []
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            target_date = parse_date(milestone.get("target_date"))
            if not target_date or target_date > as_of:
                pending_count += 1
                milestones.append(milestone)
                continue
            if milestone.get("status") == "complete" and milestone.get("price") is not None:
                milestones.append(milestone)
                continue
            due_count += 1
            price, source = price_lookup(str(record.get("ticker") or ""))
            if price is None or baseline is None or baseline <= 0:
                unavailable_count += 1
                milestones.append(
                    {
                        **milestone,
                        "status": "price_unavailable",
                        "price_checked_at": checked_at,
                        "price_source": source,
                        "investment_situation": "추적일이 도래했지만 현재가 또는 기준가를 확인하지 못했습니다.",
                    }
                )
                continue
            change = price - baseline
            change_pct = change / baseline
            milestones.append(
                {
                    **milestone,
                    "status": "complete",
                    "price": round(price, 4),
                    "price_checked_at": checked_at,
                    "price_source": source,
                    "price_change": round(change, 4),
                    "price_change_pct": round(change_pct, 4),
                    "investment_situation": daily_recommendation_tracking.investment_situation(change_pct),
                }
            )
        record["tracking_milestones"] = milestones
        updated.append(record)

    store["records"] = updated
    store["tracking_updated_at"] = checked_at
    write_daily_recommendation_store(settings, store)
    return {
        "status": "success",
        "module": "daily_recommendation_tracking",
        "as_of": as_of.isoformat(),
        "checked_at": checked_at,
        "record_count": len(updated),
        "due_count": due_count,
        "pending_count": pending_count,
        "price_unavailable_count": unavailable_count,
        "storage_path": str(daily_recommendation_store_path(settings)),
    }


def latest_daily_recommendation_policy_alignment(records: list[dict], latest_records: list[dict]) -> dict[str, Any]:
    feedback_by_ticker = daily_recommendation_tracking.daily_recommendation_tracking_feedback(records)
    review_hold_records: list[dict[str, Any]] = []
    for record in sorted(latest_records, key=lambda item: int(item.get("rank") or 999)):
        ticker = daily_recommendation_evidence.normalize_recommendation_ticker(record.get("ticker"))
        if not ticker:
            continue
        profile = daily_recommendation_tracking.daily_recommendation_tracking_feedback_profile(
            feedback_by_ticker.get(ticker)
        )
        if not profile.get("review_hold"):
            continue
        review_hold_records.append(
            {
                "rank": record.get("rank"),
                "ticker": ticker,
                "company_name": record.get("company_name") or ticker,
                "completed_count": profile.get("completed_count"),
                "hit_rate": profile.get("hit_rate"),
                "average_change_pct": profile.get("average_change_pct"),
                "penalty_points": profile.get("penalty_points"),
                "horizon_penalty_points": profile.get("horizon_penalty_points"),
                "weakest_milestone": profile.get("weakest_milestone"),
            }
        )
    return {
        "status": "drift" if review_hold_records else "ok",
        "review_hold_count": len(review_hold_records),
        "review_hold_records": review_hold_records,
        "message": (
            "최신 추천에 반복 부진 보류 후보가 포함되어 다음 추천 갱신에서 재정렬이 필요합니다."
            if review_hold_records
            else "최신 추천은 현재 추적 피드백 보류 기준과 정렬되어 있습니다."
        ),
    }


def daily_recommendation_status_payload(settings: Settings, *, today: str | None = None) -> dict[str, Any]:
    payload = summarize_daily_recommendation_store(settings)
    state = read_json_payload(daily_recommendation_state_path(settings), {})
    today_key = today or current_recommendation_datetime().date().isoformat()
    today_records = [
        item
        for item in (payload.get("records") or [])
        if item.get("recommendation_date") == today_key
    ]
    payload["enabled"] = settings.daily_recommendations_enabled
    payload["daily_time"] = settings.daily_recommendations_time
    payload["tracking_enabled"] = settings.daily_recommendations_tracking_enabled
    payload["due_now"] = should_run_daily_recommendations(settings)
    payload["today_recommendation_date"] = today_key
    payload["today_records"] = sorted(today_records, key=lambda item: int(item.get("rank") or 999))[:3]
    payload["has_today_recommendations"] = bool(today_records)
    payload["state"] = state
    return payload


def summarize_daily_recommendation_store(settings: Settings, *, limit: int = 30) -> dict[str, Any]:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = store.get("latest_recommendation_date")
    latest_records = [
        item for item in records if item.get("recommendation_date") == latest_date
    ] if latest_date else []
    recommendation_dates = sorted(
        {
            str(item.get("recommendation_date"))
            for item in records
            if item.get("recommendation_date")
        },
        reverse=True,
    )
    due_milestones = []
    for record in records:
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            if milestone.get("status") in {"price_unavailable", "complete"}:
                continue
            due_milestones.append(
                {
                    "record_id": record.get("record_id"),
                    "company_name": record.get("company_name"),
                    "ticker": record.get("ticker"),
                    "rank": record.get("rank"),
                    "recommendation_date": record.get("recommendation_date"),
                    "milestone": milestone.get("label"),
                    "target_date": milestone.get("target_date"),
                    "status": milestone.get("status"),
                }
            )
    return {
        "status": "success",
        "module": "daily_stock_recommendations",
        "updated_at": store.get("updated_at"),
        "tracking_updated_at": store.get("tracking_updated_at"),
        "latest_recommendation_date": latest_date,
        "record_count": len(records),
        "recommendation_dates": recommendation_dates[:30],
        "latest_records": sorted(latest_records, key=lambda item: int(item.get("rank") or 999))[:3],
        "records": records[: max(1, min(limit, 200))],
        "due_or_pending_milestones": due_milestones[:30],
        "performance_summary": daily_recommendation_tracking.summarize_tracking_performance(records),
        "latest_policy_alignment": latest_daily_recommendation_policy_alignment(records, latest_records),
        "storage_path": str(daily_recommendation_store_path(settings)),
    }
