"""Daily recommendation tracker for the research OS.

The module stays deliberately data-source agnostic. The FastAPI layer supplies
ranked candidates and price lookups, while this module owns stable storage,
record de-duplication, milestone tracking, and Korean-facing status text.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


TRACKING_MILESTONES = [
    {"key": "7d", "label": "추천 후 1주일", "days": 7},
    {"key": "15d", "label": "추천 후 15일", "days": 15},
    {"key": "1m", "label": "추천 후 1달", "days": 30},
    {"key": "3m", "label": "추천 후 3달", "days": 90},
    {"key": "6m", "label": "추천 후 6달", "days": 180},
]


def daily_recommendation_store_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations.json"


def daily_recommendation_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations_state.json"


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


def normalize_candidate(candidate: dict) -> dict:
    ticker = str(candidate.get("ticker") or "").strip().upper()
    company_name = str(candidate.get("company_name") or candidate.get("name") or ticker).strip()
    reasons = [str(item).strip() for item in candidate.get("reasons", []) if str(item or "").strip()]
    evidence = [str(item).strip() for item in candidate.get("evidence_sources", []) if str(item or "").strip()]
    score_components = [
        item
        for item in candidate.get("score_components", [])
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    return {
        **candidate,
        "ticker": ticker,
        "company_name": company_name,
        "score": int(candidate.get("score") or 0),
        "score_components": score_components[:10],
        "reasons": reasons[:6],
        "evidence_sources": evidence[:8],
    }


def build_tracking_milestones(recommendation_date: date) -> list[dict]:
    return [
        {
            **milestone,
            "target_date": (recommendation_date + timedelta(days=int(milestone["days"]))).isoformat(),
            "status": "pending",
            "price": None,
            "price_checked_at": None,
            "price_change": None,
            "price_change_pct": None,
            "investment_situation": "아직 추적 예정일 전입니다.",
        }
        for milestone in TRACKING_MILESTONES
    ]


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
        "recommendation_type": "daily_review_candidate",
        "action_label": "오늘의 검토 후보",
        "baseline_price": baseline_price,
        "baseline_price_source": normalized.get("baseline_price_source"),
        "baseline_price_checked_at": normalized.get("baseline_price_checked_at"),
        "currency": normalized.get("currency") or "KRW",
        "reasons": normalized["reasons"],
        "evidence_sources": normalized["evidence_sources"],
        "risk_notes": [
            str(item).strip()
            for item in normalized.get("risk_notes", [])
            if str(item or "").strip()
        ][:5],
        "portfolio_context": normalized.get("portfolio_context") or [],
        "tracking_milestones": build_tracking_milestones(recommendation_date),
    }
    return record


def summarize_tracking_performance(records: list[dict]) -> dict:
    summary = {
        "total_milestones": 0,
        "complete_count": 0,
        "pending_count": 0,
        "price_unavailable_count": 0,
        "positive_count": 0,
        "negative_count": 0,
        "flat_count": 0,
        "best": None,
        "worst": None,
    }
    completed_rows: list[dict] = []
    for record in records:
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            summary["total_milestones"] += 1
            status = milestone.get("status") or "pending"
            if status == "complete":
                summary["complete_count"] += 1
                try:
                    change_pct = float(milestone.get("price_change_pct") or 0)
                except (TypeError, ValueError):
                    change_pct = 0.0
                if change_pct > 0:
                    summary["positive_count"] += 1
                elif change_pct < 0:
                    summary["negative_count"] += 1
                else:
                    summary["flat_count"] += 1
                completed_rows.append(
                    {
                        "record_id": record.get("record_id"),
                        "company_name": record.get("company_name"),
                        "ticker": record.get("ticker"),
                        "rank": record.get("rank"),
                        "recommendation_date": record.get("recommendation_date"),
                        "milestone": milestone.get("label") or milestone.get("key"),
                        "target_date": milestone.get("target_date"),
                        "baseline_price": record.get("baseline_price"),
                        "price": milestone.get("price"),
                        "price_change": milestone.get("price_change"),
                        "price_change_pct": change_pct,
                        "investment_situation": milestone.get("investment_situation"),
                    }
                )
            elif status == "price_unavailable":
                summary["price_unavailable_count"] += 1
            else:
                summary["pending_count"] += 1
    completed_rows.sort(key=lambda item: item.get("price_change_pct") or 0, reverse=True)
    if completed_rows:
        summary["best"] = completed_rows[0]
        summary["worst"] = completed_rows[-1]
    return summary


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
    if change_pct is None:
        return "현재가를 확인하지 못해 추적 보류 상태입니다."
    pct = change_pct * 100
    if pct >= 15:
        return "추천 후 강한 상승 구간입니다. 차익 실현/비중 유지 근거를 함께 점검하세요."
    if pct >= 5:
        return "추천 후 양호한 상승 구간입니다. 초기 근거가 유지되는지 확인하세요."
    if pct >= -5:
        return "추천 후 큰 변동 없이 관찰 구간입니다. 추가 근거를 더 확인하세요."
    if pct >= -15:
        return "추천 후 약세 구간입니다. 손실 원인과 투자 논거 훼손 여부를 점검하세요."
    return "추천 후 큰 폭의 약세입니다. 리스크 경고로 분류하고 재검토가 필요합니다."


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
