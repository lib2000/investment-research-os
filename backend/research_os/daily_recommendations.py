"""Daily recommendation tracker for the research OS.

The module stays deliberately data-source agnostic. The FastAPI layer supplies
ranked candidates and price lookups, while this module owns stable storage,
record de-duplication, milestone tracking, and Korean-facing status text.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from re import search
from re import fullmatch
from typing import Any, Callable

from research_os import daily_recommendation_evidence
from research_os import daily_recommendation_recent
from research_os import daily_recommendation_tracking
from research_os.interest_automation import compact_interest_text
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
from research_os.storage_quality import (
    is_archived_research_entry,
    storage_quality_entry_is_policy_url_only,
    storage_quality_entry_needs_body,
    storage_quality_entry_needs_ocr,
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
        "score_components": score_components,
        "reasons": reasons[:6],
        "evidence_sources": evidence[:8],
        "evidence_documents": normalize_evidence_documents(candidate.get("evidence_documents")),
        "score_explanation": candidate.get("score_explanation") or {},
        "score_penalties": [
            str(item).strip()
            for item in candidate.get("score_penalties", [])
            if str(item or "").strip()
        ][:6],
        "quality_flags": [
            str(item).strip()
            for item in candidate.get("quality_flags", [])
            if str(item or "").strip()
        ][:6],
        "investment_direction_profile": candidate.get("investment_direction_profile") or {},
        "overseas_tracking": candidate.get("overseas_tracking") or {},
        "portfolio_risk_connection": candidate.get("portfolio_risk_connection") or {},
    }


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
    if not ticker or ticker in {"CASH", "UNKNOWN"}:
        return False
    if fullmatch(r"\d+", ticker) and not fullmatch(r"\d{6}", ticker):
        return False
    if not company_name or company_name.upper().startswith("UNKNOWN"):
        return False
    return True


def ensure_daily_recommendation_candidate(
    candidates_by_ticker: dict[str, dict],
    ticker: str,
    company_name: str,
) -> dict:
    key = normalize_recommendation_ticker(ticker)
    row = candidates_by_ticker.setdefault(
        key,
        {
            "ticker": key,
            "company_name": company_name,
            "score": 0,
            "reasons": [],
            "evidence_sources": [],
            "risk_notes": [],
            "portfolio_context": [],
            "score_penalties": [],
            "quality_flags": [],
            "portfolio_risk_connection": {},
            "overseas_tracking": {},
            "currency": "KRW" if fullmatch(r"\d{6}", key) else "USD",
            "baseline_price": None,
            "baseline_price_source": None,
            "baseline_price_checked_at": None,
        },
    )
    if company_name and (row.get("company_name") == key or not row.get("company_name")):
        row["company_name"] = company_name
    return row


def daily_recommendation_manifest_quality_by_ticker(manifest_entries: list[dict]) -> dict[str, dict]:
    quality_by_ticker: dict[str, dict] = {}
    for entry in manifest_entries:
        if not isinstance(entry, dict):
            continue
        ticker = normalize_recommendation_ticker(entry.get("ticker"))
        if not ticker:
            continue
        quality = quality_by_ticker.setdefault(
            ticker,
            {
                "active_count": 0,
                "archived_count": 0,
                "high_quality_count": 0,
                "duplicate_suspected_count": 0,
                "body_missing_count": 0,
                "ocr_needed_count": 0,
                "policy_url_only_count": 0,
                "latest_quality_date": None,
            },
        )
        if is_archived_research_entry(entry):
            quality["archived_count"] += 1
            continue
        quality["active_count"] += 1
        date_text = str(entry.get("date") or "")[:10]
        if date_text and (not quality["latest_quality_date"] or date_text > quality["latest_quality_date"]):
            quality["latest_quality_date"] = date_text
        duplicate_check = entry.get("duplicate_check") if isinstance(entry.get("duplicate_check"), dict) else {}
        duplicate_suspected = bool(
            duplicate_check.get("is_duplicate_suspected")
            or entry.get("duplicate_reason")
            or int(entry.get("duplicate_count") or 0) > 0
        )
        needs_body = storage_quality_entry_needs_body(entry)
        needs_ocr = storage_quality_entry_needs_ocr(entry)
        policy_url_only = storage_quality_entry_is_policy_url_only(entry)
        if duplicate_suspected:
            quality["duplicate_suspected_count"] += 1
        if needs_body:
            quality["body_missing_count"] += 1
        if needs_ocr:
            quality["ocr_needed_count"] += 1
        if policy_url_only:
            quality["policy_url_only_count"] += 1
        if not duplicate_suspected and not needs_body and not needs_ocr and not policy_url_only:
            quality["high_quality_count"] += 1
    return quality_by_ticker


def add_daily_recommendation_score(candidate: dict, points: int | float, label: str) -> None:
    try:
        numeric_points = int(points)
    except (TypeError, ValueError):
        numeric_points = 0
    if numeric_points <= 0:
        return
    candidate["score"] = int(candidate.get("score") or 0) + numeric_points
    candidate.setdefault("score_components", []).append(
        {"label": str(label or "").strip() or "점수", "points": numeric_points}
    )


def add_daily_recommendation_penalty(candidate: dict, label: str, points: int | float = 0) -> None:
    try:
        numeric_points = abs(int(points))
    except (TypeError, ValueError):
        numeric_points = 0
    text = str(label or "").strip()
    if not text:
        return
    if numeric_points:
        candidate["score"] = int(candidate.get("score") or 0) - numeric_points
        text = f"{text} (-{numeric_points})"
    candidate.setdefault("score_penalties", []).append(text)


def apply_daily_recommendation_storage_quality(candidate: dict, quality: dict | None) -> None:
    if not quality:
        candidate.setdefault("quality_flags", []).append("저장 품질 대시보드 연결 없음")
        quality = {}
    high_quality_count = int(quality.get("high_quality_count") or 0)
    duplicate_count = int(quality.get("duplicate_suspected_count") or 0)
    body_missing_count = int(quality.get("body_missing_count") or 0)
    ocr_needed_count = int(quality.get("ocr_needed_count") or 0)
    archived_count = int(quality.get("archived_count") or 0)
    active_count = int(quality.get("active_count") or 0)
    if high_quality_count >= 3:
        add_daily_recommendation_score(candidate, 8, "검증 저장자료 품질")
    elif high_quality_count > 0:
        add_daily_recommendation_score(candidate, 3, "검증 저장자료 품질")
    else:
        candidate.setdefault("quality_flags", []).append("검증된 활성 저장자료 부족")
        add_points = 3 if active_count else 5
        add_daily_recommendation_penalty(candidate, "검증된 활성 저장자료 부족", add_points)
    if duplicate_count:
        penalty = min(8, max(2, duplicate_count))
        add_daily_recommendation_penalty(candidate, "중복 의심 저장자료 대표화 필요", penalty)
        candidate.setdefault("quality_flags", []).append("중복 의심 자료는 대표 자료만 근거로 사용")
    if body_missing_count or ocr_needed_count:
        penalty = min(10, (body_missing_count * 3) + (ocr_needed_count * 3))
        add_daily_recommendation_penalty(candidate, "본문/OCR 보강 필요 자료 존재", penalty)
        candidate.setdefault("quality_flags", []).append("본문/OCR 보강 전 투자 근거 가중치 제한")
    if archived_count and not active_count:
        candidate.setdefault("quality_flags", []).append("활성 근거 없이 보관 자료만 존재")
    quality_evidence = (
        "저장 품질: "
        f"활용 가능 {high_quality_count}건 · "
        f"중복 제외 {duplicate_count}건 · "
        f"보강 필요 {body_missing_count + ocr_needed_count}건"
    )
    evidence_sources = candidate.setdefault("evidence_sources", [])
    if quality_evidence not in evidence_sources:
        evidence_sources.insert(0, quality_evidence)


def apply_daily_recommendation_consensus_row(
    candidate: dict,
    item: dict,
    *,
    price_refresh_mode: object = None,
    as_of: object = None,
) -> dict:
    candidate["currency"] = item.get("currency") or candidate.get("currency")
    if item.get("current_price") is not None:
        candidate["baseline_price"] = item.get("current_price")
        candidate["baseline_price_source"] = item.get("price_source") or price_refresh_mode
        candidate["baseline_price_checked_at"] = as_of

    target_upside = item.get("target_upside")
    if target_upside is not None:
        add_daily_recommendation_score(
            candidate,
            max(0, min(35, int(float(target_upside) * 100))),
            "증권사 목표가 상승여력",
        )
        candidate.setdefault("reasons", []).append(
            f"저장된 증권사 목표주가 대비 상승여력 {float(target_upside) * 100:.1f}%"
        )
    if item.get("valuation_signal") and item.get("valuation_signal") != "계산 보류":
        add_daily_recommendation_score(candidate, 10, "밸류에이션 신호")
        candidate.setdefault("reasons", []).append(f"밸류에이션 신호: {item.get('valuation_signal')}")
    if item.get("source_count"):
        add_daily_recommendation_score(candidate, min(15, int(item.get("source_count") or 0) * 3), "리포트 근거 수")
        candidate.setdefault("evidence_sources", []).append(
            f"목표가/리포트 근거 {item.get('source_count')}건"
        )
    if item.get("market_value"):
        market_value = float(item.get("market_value") or 0)
        add_daily_recommendation_score(candidate, 20, "실제 보유 포트폴리오 비중")
        candidate.setdefault("portfolio_context", []).append(
            f"보유 포트폴리오 평가금액 {round(market_value):,}원"
        )
        candidate["portfolio_risk_connection"] = {
            "linked": True,
            "priority": "high" if market_value >= 10_000_000 else "normal",
            "market_value_krw": round(market_value),
            "message": "보유 비중이 연결된 추천 후보입니다. 포트폴리오 리스크 스캔에서 비중·섹터 쏠림을 함께 확인하세요.",
        }
    if item.get("interest"):
        add_daily_recommendation_score(candidate, 10, "관심종목 등록")
        candidate.setdefault("portfolio_context", []).append("관심종목 등록")
        if not candidate.get("portfolio_risk_connection"):
            candidate["portfolio_risk_connection"] = {
                "linked": True,
                "priority": "watch",
                "message": "관심종목 등록 후보입니다. 실제 보유 편입 전 가격 조건과 기존 보유 노출을 함께 확인하세요.",
            }
    if item.get("latest_source_file"):
        candidate.setdefault("evidence_sources", []).append(f"최근 근거 파일: {item.get('latest_source_file')}")
    if item.get("source_scope"):
        candidate.setdefault("evidence_sources", []).append(f"대상 범위: {item.get('source_scope')}")
    return candidate


def apply_daily_recommendation_priority_target(candidate: dict, target: dict) -> dict:
    priority = str(target.get("priority") or "medium")
    add_daily_recommendation_score(
        candidate,
        {"high": 20, "medium": 10, "low": 3}.get(priority, 10),
        "보유/관심 우선순위",
    )
    recent_count = int(target.get("recent_document_count") or 0)
    rag_count = int(target.get("rag_document_count") or 0)
    if recent_count:
        add_daily_recommendation_score(candidate, min(15, recent_count), "최근 저장자료")
        candidate.setdefault("reasons", []).append(f"최근 저장자료 {recent_count}건")
    if rag_count:
        add_daily_recommendation_score(candidate, min(15, rag_count), "RAG 연결 문서")
        candidate.setdefault("evidence_sources", []).append(f"RAG 연결 문서 {rag_count}건")
    if target.get("thesis_snapshot_connected"):
        add_daily_recommendation_score(candidate, 12, "최신 투자 논거 스냅샷")
        candidate.setdefault("evidence_sources", []).append("최신 투자 논거 스냅샷 연결")
    market_matches = target.get("market_journal_matches") or []
    if market_matches:
        add_daily_recommendation_score(candidate, min(10, len(market_matches) * 3), "시장일지 연결")
        latest_market = market_matches[0]
        candidate.setdefault("reasons", []).append(
            "시장일지 연결: "
            + compact_interest_text(latest_market.get("summary") or latest_market.get("session_date"), 90)
        )
    if target.get("next_action"):
        candidate.setdefault("risk_notes", []).append(str(target.get("next_action")))
    return candidate


def apply_daily_recommendation_recent_weekly_evidence(
    candidate: dict,
    recent_items: list[dict],
    weekly_groups: list[dict] | None = None,
) -> dict:
    important_count = sum(1 for item in recent_items if item.get("category") == "filing")
    report_count = sum(1 for item in recent_items if item.get("category") == "report")
    public_ir_sec_items = [item for item in recent_items if item.get("category") == "public_ir_sec"]
    public_ir_sec_count = len(public_ir_sec_items)
    usable_public_ir_sec_count = sum(1 for item in public_ir_sec_items if item.get("usable_for_recommendation"))
    blocked_public_ir_sec_count = public_ir_sec_count - usable_public_ir_sec_count

    if important_count:
        add_daily_recommendation_score(candidate, min(20, important_count * 5), "최근 중요 공시 반영")
        candidate.setdefault("reasons", []).append(f"최근 1주 중요 공시 {important_count}건 확인")
        candidate.setdefault("evidence_sources", []).append("최근 1주 공시 브리프 반영")
    if report_count:
        add_daily_recommendation_score(candidate, min(12, report_count * 3), "최근 핵심 리포트 반영")
        candidate.setdefault("evidence_sources", []).append(f"최근 1주 핵심 리포트 {report_count}건")
    if usable_public_ir_sec_count:
        add_daily_recommendation_score(candidate, min(12, usable_public_ir_sec_count * 4), "최근 공개 IR/SEC 반영")
        candidate.setdefault("evidence_sources", []).append(f"최근 1주 공개 IR/SEC 자료 {usable_public_ir_sec_count}건")
        candidate.setdefault("reasons", []).append("본문 추출이 확인된 공개 IR/SEC 자료가 최근 1주 브리프와 RAG 근거에 연결됨")
    if blocked_public_ir_sec_count:
        candidate.setdefault("risk_notes", []).append(f"공개 IR/SEC URL-only 자료 {blocked_public_ir_sec_count}건은 본문 보강 전 추천 점수 가산에서 제외")
        candidate.setdefault("quality_flags", []).append("공개 IR/SEC 본문 보강 필요")

    for recent_item in recent_items[:8]:
        document = daily_recommendation_recent_item_evidence_document(recent_item)
        if document:
            candidate.setdefault("evidence_documents", []).append(document)

    deduped_weekly_groups = []
    seen_group_keys = set()
    for group in weekly_groups or []:
        group_key = str(group.get("key") or group.get("label") or "")
        if group_key in seen_group_keys:
            continue
        seen_group_keys.add(group_key)
        deduped_weekly_groups.append(group)
    if deduped_weekly_groups:
        candidate["weekly_evidence_groups"] = deduped_weekly_groups[:5]
        weekly_group_text = ", ".join(
            item
            for item in (daily_recommendation_weekly_group_evidence_text(group) for group in deduped_weekly_groups[:4])
            if item
        )
        if weekly_group_text:
            candidate.setdefault("evidence_sources", []).append(f"최근 1주 자료 묶음: {weekly_group_text}")
    return candidate


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
    company_name = str(getattr(verification, "company_name", "") or "").strip()
    if company_name and candidate.get("company_name") == ticker:
        candidate["company_name"] = company_name

    freshness = freshness if isinstance(freshness, dict) else {}
    tone = freshness.get("tone")
    if tone == "ok":
        add_daily_recommendation_score(candidate, 10, "저장자료 신선도 양호")
    elif tone == "warning":
        add_daily_recommendation_score(candidate, 5, "저장자료 신선도 확인 필요")
        candidate.setdefault("quality_flags", []).append("저장자료 신선도 확인 필요")
        add_daily_recommendation_penalty(candidate, "최근 자료 신선도 보강 필요", 2)
    candidate.setdefault("evidence_sources", []).append(freshness.get("summary") or "저장자료 신선도 확인")

    profile = profile if isinstance(profile, dict) else {}
    if profile.get("analysis_focus"):
        candidate.setdefault("reasons", []).append(f"분석 초점: {profile.get('analysis_focus')}")
    return candidate


def apply_daily_recommendation_overseas_tracking(candidate: dict) -> dict:
    currency = str(candidate.get("currency") or "KRW").upper()
    if currency != "KRW":
        candidate["overseas_tracking"] = {
            "currency": currency,
            "baseline_price": candidate.get("baseline_price"),
            "needs_fx_conversion": True,
            "fx_note": "해외 종목은 원통화 기준 수익률을 우선 추적하고, 포트폴리오 평가에는 USD/KRW 환율 반영 상태를 함께 확인합니다.",
            "price_source": candidate.get("baseline_price_source"),
            "price_checked_at": candidate.get("baseline_price_checked_at"),
        }
        candidate.setdefault("quality_flags", []).append("해외 종목: 환율·원화 평가 병행 확인")
    else:
        candidate["overseas_tracking"] = {
            "currency": "KRW",
            "needs_fx_conversion": False,
        }
    return candidate


def apply_daily_recommendation_price_check(
    candidate: dict,
    *,
    price: object,
    source: object = None,
    checked_at: object = None,
) -> dict:
    if price is not None:
        candidate["baseline_price"] = price
        candidate["baseline_price_source"] = source or "data_provider"
        candidate["baseline_price_checked_at"] = checked_at
        add_daily_recommendation_score(candidate, 5, "현재가 확인")
    else:
        candidate.setdefault("risk_notes", []).append("기준 현재가를 확인하지 못해 사후 수익률 추적은 가격 확보 후 보강됩니다.")
        candidate.setdefault("quality_flags", []).append("기준 현재가 미확인")
        add_daily_recommendation_penalty(candidate, "현재가 미확인", 5)
    return candidate


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
    ranked_candidates = [
        {**candidate, "rank": index}
        for index, candidate in enumerate(candidates[:selected_limit], start=1)
    ]
    return {
        "status": "success",
        "module": "daily_recommendation_candidate_ranking",
        "as_of": as_of,
        "universe_count": len(candidates_by_ticker),
        "selected_count": min(limit, len(candidates)),
        "consensus_summary": consensus_summary,
        "candidates": ranked_candidates,
        "warnings": list(warnings or [])[:10],
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
    seen: dict[str, None] = {}
    for value in values or []:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text, None)
    return list(seen.keys())[:limit]


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
