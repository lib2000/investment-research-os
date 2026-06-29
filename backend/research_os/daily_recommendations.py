"""Daily recommendation tracker for the research OS.

The module stays deliberately data-source agnostic. The FastAPI layer supplies
ranked candidates and price lookups, while this module owns stable storage,
record de-duplication, milestone tracking, and Korean-facing status text.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence
from research_os import daily_recommendation_profiles
from research_os import daily_recommendation_policy
from research_os import daily_recommendation_quality
from research_os import daily_recommendation_ranking
from research_os import daily_recommendation_recent
from research_os import daily_recommendation_scoring
from research_os import daily_recommendation_tracking
from research_os.settings import Settings
from research_os.daily_recommendation_store import (
    build_recommendation_record as store_build_recommendation_record,
    current_recommendation_datetime,
    daily_recommendation_state_path,
    parse_daily_recommendations_time,
    read_daily_recommendation_store,
    read_json_payload,
    run_daily_recommendation_evidence_repair_queue as store_run_daily_recommendation_evidence_repair_queue,
    should_run_daily_recommendations,
    daily_recommendation_status_payload as store_daily_recommendation_status_payload,
    summarize_daily_recommendation_store as store_summarize_daily_recommendation_store,
    update_recommendation_tracking as store_update_recommendation_tracking,
    upsert_daily_recommendations as store_upsert_daily_recommendations,
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


def build_policy_signal_index(policy_watch: dict | None, news_inbox: dict | None = None) -> dict[str, Any]:
    return daily_recommendation_policy.build_policy_signal_index(policy_watch, news_inbox)


def apply_daily_recommendation_policy_signals(
    candidate: dict,
    policy_signal_index: dict | None,
) -> dict:
    return daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, policy_signal_index)


def build_policy_signal_quality_dashboard(recommendation_payload: dict[str, Any]) -> dict[str, Any]:
    return daily_recommendation_policy.build_policy_signal_quality_dashboard(recommendation_payload)


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


def daily_recommendation_tracking_feedback_profile(feedback: dict | None) -> dict:
    return daily_recommendation_tracking.daily_recommendation_tracking_feedback_profile(feedback)


def build_daily_recommendation_tracking_feedback(settings: Settings) -> dict[str, dict]:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    return daily_recommendation_tracking_feedback(records)


def daily_recommendation_status_payload(settings: Settings, *, today: str | None = None) -> dict[str, Any]:
    return store_daily_recommendation_status_payload(settings, today=today)


def apply_daily_recommendation_tracking_feedback(candidate: dict, feedback: dict | None) -> dict:
    return daily_recommendation_tracking.apply_daily_recommendation_tracking_feedback(candidate, feedback)


def daily_recommendation_candidate_review_hold(candidate: dict) -> bool:
    return daily_recommendation_ranking.daily_recommendation_candidate_review_hold(candidate)


def daily_recommendation_candidate_soft_tracking_hold(candidate: dict) -> bool:
    return daily_recommendation_ranking.daily_recommendation_candidate_soft_tracking_hold(candidate)


def finalize_daily_recommendation_ranking(
    candidates_by_ticker: dict[str, dict],
    *,
    limit: int,
    as_of: str,
    consensus_summary: object = None,
    warnings: list | None = None,
) -> dict:
    return daily_recommendation_ranking.finalize_daily_recommendation_ranking(
        candidates_by_ticker,
        limit=limit,
        as_of=as_of,
        consensus_summary=consensus_summary,
        warnings=warnings,
    )


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
    return daily_recommendation_candidates.finalize_daily_recommendation_candidate(candidate)


def build_tracking_milestones(recommendation_date: date) -> list[dict]:
    return daily_recommendation_tracking.build_tracking_milestones(recommendation_date)


def build_recommendation_record(
    candidate: dict,
    *,
    rank: int,
    recommendation_date: date,
    generated_at: str,
) -> dict:
    return store_build_recommendation_record(
        candidate,
        rank=rank,
        recommendation_date=recommendation_date,
        generated_at=generated_at,
    )


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
    return store_upsert_daily_recommendations(
        settings,
        candidates=candidates,
        recommendation_date=recommendation_date,
        generated_at=generated_at,
        force=force,
    )


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
    return store_update_recommendation_tracking(
        settings,
        as_of=as_of,
        checked_at=checked_at,
        price_lookup=price_lookup,
    )


def summarize_daily_recommendation_store(settings: Settings, *, limit: int = 30) -> dict:
    return store_summarize_daily_recommendation_store(settings, limit=limit)


def run_daily_recommendation_evidence_repair_queue(
    settings: Settings,
    *,
    latest_only: bool = False,
    dry_run: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    return store_run_daily_recommendation_evidence_repair_queue(
        settings,
        latest_only=latest_only,
        dry_run=dry_run,
        limit=limit,
    )
