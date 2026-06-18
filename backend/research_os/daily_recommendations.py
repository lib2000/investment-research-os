"""Daily recommendation tracker for the research OS.

The module stays deliberately data-source agnostic. The FastAPI layer supplies
ranked candidates and price lookups, while this module owns stable storage,
record de-duplication, milestone tracking, and Korean-facing status text.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from re import search
from typing import Any, Callable

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence
from research_os import daily_recommendation_profiles
from research_os import daily_recommendation_quality
from research_os import daily_recommendation_recent
from research_os import daily_recommendation_scoring
from research_os import daily_recommendation_tracking
from research_os.settings import Settings
from research_os.daily_recommendation_store import (
    current_recommendation_datetime,
    daily_recommendation_state_path,
    daily_recommendation_store_path,
    parse_daily_recommendations_time,
    parse_date,
    read_daily_recommendation_store,
    read_json_payload,
    recommendation_record_id,
    should_run_daily_recommendations,
    write_daily_recommendation_store,
    write_json_payload,
)

TRACKING_MILESTONES = daily_recommendation_tracking.TRACKING_MILESTONES


def _normalize_evidence_relative_path(value: object) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("./").lower()


def daily_recommendation_evidence_link_index(settings: Settings, *, limit: int = 120) -> dict[str, Any]:
    """Index recommendation records by RAG evidence document path."""
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = str(store.get("latest_recommendation_date") or "")
    index: dict[str, list[dict[str, Any]]] = {}
    linked_record_ids: set[str] = set()
    linked_latest_record_ids: set[str] = set()
    for record in records[: max(1, limit)]:
        record_id = str(record.get("record_id") or "").strip()
        link = {
            "record_id": record_id,
            "recommendation_date": str(record.get("recommendation_date") or ""),
            "rank": record.get("rank"),
            "ticker": str(record.get("ticker") or "").strip(),
            "company_name": str(record.get("company_name") or "").strip(),
            "is_latest": bool(latest_date and record.get("recommendation_date") == latest_date),
        }
        for document in record.get("evidence_documents") or []:
            if not isinstance(document, dict):
                continue
            for field in ("source_relative_path", "json_relative_path"):
                key = _normalize_evidence_relative_path(document.get(field))
                if not key:
                    continue
                bucket = index.setdefault(key, [])
                if not any(existing.get("record_id") == record_id for existing in bucket):
                    bucket.append(link)
                if record_id:
                    linked_record_ids.add(record_id)
                    if link["is_latest"]:
                        linked_latest_record_ids.add(record_id)
    return {
        "latest_recommendation_date": latest_date,
        "by_relative_path": index,
        "linked_record_count": len(linked_record_ids),
        "latest_linked_record_count": len(linked_latest_record_ids),
    }

def normalize_evidence_documents(value: object, limit: int = 5) -> list[dict[str, Any]]:
    return daily_recommendation_evidence.normalize_evidence_documents(value, limit)

def normalize_candidate(candidate: dict) -> dict:
    return daily_recommendation_candidates.normalize_candidate(candidate)


def normalize_recommendation_ticker(value: object) -> str:
    return daily_recommendation_evidence.normalize_recommendation_ticker(value)

def daily_recommendation_consensus_label(item: dict, ticker: str) -> str:
    return str(item.get("company_name") or ticker).strip()


def daily_recommendation_target_key(item: dict) -> str:
    return normalize_recommendation_ticker(item.get("ticker") or item.get("key"))


def daily_recommendation_target_label(item: dict, ticker: str) -> str:
    return str(
        item.get("label")
        or item.get("company_name")
        or item.get("name")
        or ticker
    )


def daily_recommendation_candidate_is_valid(ticker: str, company_name: str) -> bool:
    return daily_recommendation_candidates.daily_recommendation_candidate_is_valid(ticker, company_name)


def ensure_daily_recommendation_candidate(
    candidates_by_ticker: dict[str, dict],
    ticker: str,
    company_name: str,
) -> dict:
    return daily_recommendation_candidates.ensure_daily_recommendation_candidate(
        candidates_by_ticker,
        ticker,
        company_name,
    )


def daily_recommendation_manifest_quality_by_ticker(manifest_entries: list[dict]) -> dict[str, dict]:
    return daily_recommendation_quality.daily_recommendation_manifest_quality_by_ticker(manifest_entries)


def add_daily_recommendation_score(candidate: dict, points: int | float, label: str) -> None:
    daily_recommendation_candidates.add_daily_recommendation_score(candidate, points, label)


def add_daily_recommendation_penalty(candidate: dict, label: str, points: int | float = 0) -> None:
    daily_recommendation_candidates.add_daily_recommendation_penalty(candidate, label, points)


def apply_daily_recommendation_storage_quality(candidate: dict, quality: dict | None) -> None:
    daily_recommendation_quality.apply_daily_recommendation_storage_quality(candidate, quality)


def apply_daily_recommendation_consensus_row(
    candidate: dict,
    item: dict,
    *,
    price_refresh_mode: object = None,
    as_of: object = None,
) -> dict:
    return daily_recommendation_scoring.apply_daily_recommendation_consensus_row(
        candidate,
        item,
        price_refresh_mode=price_refresh_mode,
        as_of=as_of,
    )


def apply_daily_recommendation_priority_target(candidate: dict, target: dict) -> dict:
    return daily_recommendation_scoring.apply_daily_recommendation_priority_target(candidate, target)


def apply_daily_recommendation_recent_weekly_evidence(
    candidate: dict,
    recent_items: list[dict],
    weekly_groups: list[dict] | None = None,
) -> dict:
    return daily_recommendation_recent.apply_daily_recommendation_recent_weekly_evidence(
        candidate,
        recent_items,
        weekly_groups,
    )


def apply_daily_recommendation_evidence_documents(
    candidate: dict,
    rag_evidence_documents: list[dict] | None,
) -> dict:
    recent_evidence_documents = list(candidate.get("evidence_documents") or [])
    candidate["evidence_documents"] = [
        *recent_evidence_documents,
        *(rag_evidence_documents or []),
    ]
    return candidate


def apply_daily_recommendation_freshness_profile(
    candidate: dict,
    *,
    ticker: str,
    verification: object,
    profile: dict | None,
    freshness: dict | None,
) -> dict:
    return daily_recommendation_profiles.apply_daily_recommendation_freshness_profile(
        candidate,
        ticker=ticker,
        verification=verification,
        profile=profile,
        freshness=freshness,
    )


def apply_daily_recommendation_overseas_tracking(candidate: dict) -> dict:
    return daily_recommendation_profiles.apply_daily_recommendation_overseas_tracking(candidate)


def apply_daily_recommendation_price_check(
    candidate: dict,
    *,
    price: object,
    source: object = None,
    checked_at: object = None,
) -> dict:
    return daily_recommendation_scoring.apply_daily_recommendation_price_check(
        candidate,
        price=price,
        source=source,
        checked_at=checked_at,
    )


def daily_recommendation_tracking_feedback(records: list[dict]) -> dict[str, dict]:
    return daily_recommendation_tracking.daily_recommendation_tracking_feedback(records)


def build_daily_recommendation_tracking_feedback(settings: Settings) -> dict[str, dict]:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    return daily_recommendation_tracking_feedback(records)


def apply_daily_recommendation_tracking_feedback(candidate: dict, feedback: dict | None) -> dict:
    return daily_recommendation_tracking.apply_daily_recommendation_tracking_feedback(candidate, feedback)


def daily_recommendation_candidate_review_hold(candidate: dict) -> bool:
    return daily_recommendation_tracking.daily_recommendation_candidate_review_hold(candidate)


def finalize_daily_recommendation_ranking(
    candidates_by_ticker: dict[str, dict],
    *,
    limit: int,
    as_of: str,
    consensus_summary: object = None,
    warnings: list | None = None,
) -> dict:
    candidates = sorted(
        candidates_by_ticker.values(),
        key=lambda item: (
            int(item.get("score") or 0),
            item.get("baseline_price") is not None,
            str(item.get("company_name") or ""),
        ),
        reverse=True,
    )
    selected_limit = max(1, min(limit, 10))
    non_hold_candidates = [
        candidate
        for candidate in candidates
        if not daily_recommendation_candidate_review_hold(candidate)
    ]
    hold_candidates = [
        candidate
        for candidate in candidates
        if daily_recommendation_candidate_review_hold(candidate)
    ]
    selected_candidates = (
        non_hold_candidates[:selected_limit]
        if len(non_hold_candidates) >= selected_limit
        else (non_hold_candidates + hold_candidates)[:selected_limit]
    )
    omitted_hold_tickers = [
        str(candidate.get("ticker") or "").strip()
        for candidate in hold_candidates
        if candidate not in selected_candidates and str(candidate.get("ticker") or "").strip()
    ][:5]
    result_warnings = []
    if omitted_hold_tickers:
        result_warnings.append(f"반복 부진 top3 보류: {', '.join(omitted_hold_tickers)}")
    result_warnings.extend(list(warnings or []))
    ranked_candidates = [
        {**candidate, "rank": index}
        for index, candidate in enumerate(selected_candidates, start=1)
    ]
    return {
        "status": "success",
        "module": "daily_recommendation_candidate_ranking",
        "as_of": as_of,
        "universe_count": len(candidates_by_ticker),
        "selected_count": len(ranked_candidates),
        "consensus_summary": consensus_summary,
        "candidates": ranked_candidates,
        "warnings": result_warnings[:10],
    }


def compact_recommendation_text(value: object, max_length: int = 180) -> str:
    return daily_recommendation_recent.compact_recommendation_text(value, max_length)


def daily_recommendation_recent_weekly_index(recent_weekly: dict) -> dict[str, dict[str, list[dict]]]:
    return daily_recommendation_recent.daily_recommendation_recent_weekly_index(recent_weekly)


def daily_recommendation_recent_item_evidence_document(item: dict) -> dict | None:
    return daily_recommendation_recent.daily_recommendation_recent_item_evidence_document(item)


def daily_recommendation_weekly_group_evidence_text(group: dict) -> str:
    return daily_recommendation_recent.daily_recommendation_weekly_group_evidence_text(group)

RAG_REPORT_TYPE_PRIORITY = daily_recommendation_evidence.RAG_REPORT_TYPE_PRIORITY


def _safe_float(value: object, default: float = 0.7) -> float:
    return daily_recommendation_evidence.safe_float(value, default)


def _json_list(value: object) -> list[Any]:
    return daily_recommendation_evidence.json_list(value)


def _evidence_document_claims(document: dict[str, Any], claims: list[str]) -> list[str]:
    return daily_recommendation_evidence.evidence_document_claims(document, claims)


def build_daily_recommendation_evidence_documents(
    vault_dir: Path,
    ticker: str,
    evidence_sources: list[str] | tuple[str, ...] | None,
    reasons: list[str] | tuple[str, ...] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    return daily_recommendation_evidence.build_daily_recommendation_evidence_documents(
        vault_dir,
        ticker,
        evidence_sources,
        reasons=reasons,
        limit=limit,
    )

def unique_text_items(values: list | tuple | None, limit: int) -> list[str]:
    return daily_recommendation_evidence.unique_text_items(values, limit)


def finalize_daily_recommendation_candidate(candidate: dict) -> dict:
    """Normalize recommendation reasons, evidence, risks, and score explanation."""
    if not candidate.get("reasons"):
        candidate.setdefault("reasons", []).append("보유/관심목록과 저장 리서치에 포함된 일일 점검 후보입니다.")
    candidate["reasons"] = unique_text_items(candidate.get("reasons"), 6)
    candidate["evidence_sources"] = unique_text_items(candidate.get("evidence_sources"), 8)
    candidate["evidence_documents"] = normalize_evidence_documents(candidate.get("evidence_documents"))
    candidate["risk_notes"] = unique_text_items(candidate.get("risk_notes"), 5)
    candidate["score_penalties"] = unique_text_items(candidate.get("score_penalties"), 6)
    candidate["quality_flags"] = unique_text_items(candidate.get("quality_flags"), 6)
    score_components = [
        component
        for component in candidate.get("score_components", [])
        if isinstance(component, dict) and str(component.get("label") or "").strip()
    ]
    candidate["score_components"] = score_components
    positive_points = sum(int(component.get("points") or 0) for component in score_components)
    penalty_points = sum(
        int(match.group(1))
        for item in candidate.get("score_penalties", [])
        for match in [search(r"\(-(\d+)\)", str(item))]
        if match
    )
    if positive_points:
        candidate["score_explanation"] = {
            "positive_points": positive_points,
            "penalty_points": penalty_points,
            "final_score": int(candidate.get("score") or 0),
            "top_component": max(
                score_components,
                key=lambda component: int(component.get("points") or 0),
            ),
            "component_weights": [
                {
                    "label": component.get("label"),
                    "points": int(component.get("points") or 0),
                    "weight_pct": round(int(component.get("points") or 0) / positive_points * 100, 1),
                }
                for component in score_components[:8]
            ],
        }
    return candidate


def build_tracking_milestones(recommendation_date: date) -> list[dict]:
    return daily_recommendation_tracking.build_tracking_milestones(recommendation_date)


def build_recommendation_record(
    candidate: dict,
    *,
    rank: int,
    recommendation_date: date,
    generated_at: str,
) -> dict:
    normalized = normalize_candidate(candidate)
    baseline_price = normalized.get("baseline_price")
    record = {
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
        "tracking_milestones": build_tracking_milestones(recommendation_date),
    }
    return record


def summarize_tracking_performance(records: list[dict]) -> dict:
    return daily_recommendation_tracking.summarize_tracking_performance(records)


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


def investment_situation(change_pct: float | None) -> str:
    return daily_recommendation_tracking.investment_situation(change_pct)


PriceLookup = Callable[[str], tuple[float | None, str | None]]


def saved_portfolio_price_lookup(portfolio_store: dict[str, Any]) -> dict[str, tuple[float, str]]:
    return daily_recommendation_tracking.saved_portfolio_price_lookup(portfolio_store)


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
                    "investment_situation": investment_situation(change_pct),
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


def summarize_daily_recommendation_store(settings: Settings, *, limit: int = 30) -> dict:
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
        "performance_summary": summarize_tracking_performance(records),
        "storage_path": str(daily_recommendation_store_path(settings)),
    }
