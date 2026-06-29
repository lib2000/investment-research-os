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

MARKET_ORDER = {"KR": 0, "US": 1}
MARKET_LABELS = {"KR": "한국", "US": "미국"}


def daily_recommendation_store_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations.json"


def daily_recommendation_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations_state.json"


def daily_recommendation_repair_queue_status_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendation_evidence_repair_queue_status.json"


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


def daily_recommendation_repair_queue_action(queue_item: dict[str, Any]) -> dict[str, Any]:
    task_type = str(queue_item.get("task_type") or "general_review")
    if task_type == "source_trace":
        action = "연결 문서의 title, source_relative_path, matched_claims를 재검증하고 누락된 추적 메타데이터를 보강합니다."
        handler = "repair_source_trace_metadata"
    elif task_type == "fresh_evidence":
        action = "최근 7~30일 DART/SEC 공시, 뉴스 인박스, 리서치 저장소를 재조회합니다."
        handler = "refresh_recent_evidence_sources"
    elif task_type == "source_diversity":
        action = "부족한 출처 유형을 찾아 공시, 리포트, 뉴스, 정책 근거 균형을 보강합니다."
        handler = "scan_missing_source_families"
    elif task_type == "signal_coverage":
        action = "시장, 공시, 정책, 뉴스, 심리 신호별 누락 축을 다시 스캔합니다."
        handler = "rescan_signal_coverage"
    elif task_type == "source_body":
        action = "원문/PDF/OCR/본문 보강 대기 항목으로 등록합니다."
        handler = "queue_source_body_supplement"
    else:
        action = "근거 품질 보강 사유를 확인하고 관련 원천 자료 수집 계획을 생성합니다."
        handler = "review_evidence_quality_gap"
    return {
        "handler": handler,
        "action": action,
        "dry_run_supported": True,
    }


def run_daily_recommendation_evidence_repair_queue(
    settings: Settings,
    *,
    latest_only: bool = False,
    dry_run: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = str(store.get("latest_recommendation_date") or "")
    if latest_only and latest_date:
        records = [item for item in records if item.get("recommendation_date") == latest_date]
    queue_rows: list[dict[str, Any]] = []
    for record in records:
        quality = record.get("evidence_quality_summary") if isinstance(record.get("evidence_quality_summary"), dict) else {}
        queue = quality.get("evidence_repair_queue") if isinstance(quality.get("evidence_repair_queue"), list) else []
        for item in queue:
            if not isinstance(item, dict):
                continue
            action = daily_recommendation_repair_queue_action(item)
            queue_rows.append(
                {
                    "record_id": record.get("record_id"),
                    "recommendation_date": record.get("recommendation_date"),
                    "ticker": record.get("ticker"),
                    "company_name": record.get("company_name"),
                    "rank": record.get("rank"),
                    "market": recommendation_market(record),
                    "grade": quality.get("grade"),
                    "score": quality.get("score"),
                    "reason": item.get("reason"),
                    "task_type": item.get("task_type"),
                    "label": item.get("label"),
                    "next_action": item.get("next_action") or action["action"],
                    "handler": action["handler"],
                    "planned_action": action["action"],
                    "status": "dry_run" if dry_run else "queued_for_execution",
                }
            )
    queue_rows.sort(
        key=lambda item: (
            str(item.get("recommendation_date") or ""),
            -int(item.get("rank") or 999),
            str(item.get("ticker") or ""),
            str(item.get("task_type") or ""),
        ),
        reverse=True,
    )
    limited_rows = queue_rows[: max(1, min(int(limit or 50), 200))]
    by_task_type: dict[str, int] = {}
    for item in queue_rows:
        task_type = str(item.get("task_type") or "general_review")
        by_task_type[task_type] = by_task_type.get(task_type, 0) + 1
    payload = {
        "status": "dry_run" if dry_run else "queued",
        "module": "daily_recommendation_evidence_repair_queue",
        "dry_run": dry_run,
        "latest_only": latest_only,
        "latest_recommendation_date": latest_date,
        "checked_at": current_recommendation_datetime().isoformat(),
        "record_count": len(records),
        "queue_count": len(queue_rows),
        "returned_count": len(limited_rows),
        "task_type_counts": by_task_type,
        "queue": limited_rows,
        "message": (
            "근거 보강 큐 dry-run 미리보기를 저장했습니다."
            if dry_run
            else "근거 보강 큐 실행 대상을 저장했습니다."
        ),
        "storage_path": str(daily_recommendation_repair_queue_status_path(settings)),
    }
    write_json_payload(daily_recommendation_repair_queue_status_path(settings), payload)
    return payload


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


def recommendation_market(candidate: dict[str, Any]) -> str:
    market = str(candidate.get("market") or "").strip().upper()
    if market in MARKET_ORDER:
        return market
    currency = str(candidate.get("currency") or "").strip().upper()
    ticker = str(candidate.get("ticker") or "").strip()
    if currency == "KRW" or (ticker.isdigit() and len(ticker) == 6):
        return "KR"
    return "US"


def recommendation_market_label(market: str) -> str:
    return MARKET_LABELS.get(str(market or "").upper(), str(market or "").upper() or "시장")


def recommendation_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    market = recommendation_market(item)
    return (
        MARKET_ORDER.get(market, 99),
        int(item.get("rank") or 999),
        str(item.get("ticker") or ""),
    )


def recommendation_record_id(recommendation_date: date, market: str, rank: int, ticker: str) -> str:
    return f"{recommendation_date.isoformat()}-{market}-{rank:02d}-{str(ticker or '').upper()}"


def daily_recommendation_market_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for market in sorted({recommendation_market(record) for record in records}, key=lambda value: MARKET_ORDER.get(value, 99)):
        market_records = sorted(
            [record for record in records if recommendation_market(record) == market],
            key=recommendation_sort_key,
        )
        groups.append(
            {
                "market": market,
                "label": recommendation_market_label(market),
                "count": len(market_records),
                "records": market_records,
            }
        )
    return groups


def build_recommendation_record(
    candidate: dict,
    *,
    rank: int,
    recommendation_date: date,
    generated_at: str,
) -> dict:
    normalized = daily_recommendation_candidates.normalize_candidate(candidate)
    baseline_price = normalized.get("baseline_price")
    market = recommendation_market(normalized)
    return {
        "record_id": recommendation_record_id(recommendation_date, market, rank, normalized["ticker"]),
        "recommendation_date": recommendation_date.isoformat(),
        "generated_at": generated_at,
        "market": market,
        "market_label": recommendation_market_label(market),
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
        "evidence_quality_summary": normalized.get("evidence_quality_summary") or {},
        "risk_notes": [
            str(item).strip()
            for item in normalized.get("risk_notes", [])
            if str(item or "").strip()
        ][:5],
        "portfolio_context": normalized.get("portfolio_context") or [],
        "investment_direction_profile": normalized.get("investment_direction_profile") or {},
        "portfolio_risk_connection": normalized.get("portfolio_risk_connection") or {},
        "overseas_tracking": normalized.get("overseas_tracking") or {},
        "policy_signal_summary": normalized.get("policy_signal_summary") or {},
        "signal_breakdown": normalized.get("signal_breakdown") or [],
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
            "records": sorted(existing_today, key=recommendation_sort_key),
            "market_groups": daily_recommendation_market_groups(existing_today),
            "storage_path": str(daily_recommendation_store_path(settings)),
        }

    if force and existing_today:
        today_ids = {item.get("record_id") for item in existing_today}
        records = [item for item in records if item.get("record_id") not in today_ids]

    market_rank_counts: dict[str, int] = {}
    ranked_candidates: list[tuple[dict, int]] = []
    for index, candidate in enumerate(candidates):
        market = recommendation_market(candidate)
        market_rank_counts[market] = market_rank_counts.get(market, 0) + 1
        rank = int(candidate.get("rank") or market_rank_counts[market] or index + 1)
        ranked_candidates.append((candidate, rank))
    new_records = [
        build_recommendation_record(
            candidate,
            rank=rank,
            recommendation_date=recommendation_date,
            generated_at=generated_at,
        )
        for candidate, rank in ranked_candidates
    ]
    records.extend(new_records)
    records.sort(
        key=lambda item: (
            str(item.get("recommendation_date") or ""),
            -MARKET_ORDER.get(recommendation_market(item), 99),
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
        "market_groups": daily_recommendation_market_groups(new_records),
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
    payload["today_records"] = sorted(today_records, key=recommendation_sort_key)
    payload["today_market_groups"] = daily_recommendation_market_groups(today_records)
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
        "latest_records": sorted(latest_records, key=recommendation_sort_key),
        "latest_market_groups": daily_recommendation_market_groups(latest_records),
        "records": records[: max(1, min(limit, 200))],
        "due_or_pending_milestones": due_milestones[:30],
        "performance_summary": daily_recommendation_tracking.summarize_tracking_performance(records),
        "latest_policy_alignment": latest_daily_recommendation_policy_alignment(records, latest_records),
        "storage_path": str(daily_recommendation_store_path(settings)),
    }
