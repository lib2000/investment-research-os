"""Scoring helpers for daily recommendation candidates."""

from __future__ import annotations

from typing import Any

from research_os import daily_recommendation_candidates
from research_os.interest_automation import compact_interest_text


def apply_daily_recommendation_consensus_row(
    candidate: dict[str, Any],
    item: dict[str, Any],
    *,
    price_refresh_mode: object = None,
    as_of: object = None,
) -> dict[str, Any]:
    candidate["currency"] = item.get("currency") or candidate.get("currency")
    if item.get("current_price") is not None:
        candidate["baseline_price"] = item.get("current_price")
        candidate["baseline_price_source"] = item.get("price_source") or price_refresh_mode
        candidate["baseline_price_checked_at"] = as_of

    target_upside = item.get("target_upside")
    if target_upside is not None:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            max(0, min(35, int(float(target_upside) * 100))),
            "증권사 목표가 상승여력",
        )
        candidate.setdefault("reasons", []).append(
            f"저장된 증권사 목표주가 대비 상승여력 {float(target_upside) * 100:.1f}%"
        )
    if item.get("valuation_signal") and item.get("valuation_signal") != "계산 보류":
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 10, "밸류에이션 신호")
        candidate.setdefault("reasons", []).append(f"밸류에이션 신호: {item.get('valuation_signal')}")
    if item.get("source_count"):
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(15, int(item.get("source_count") or 0) * 3),
            "리포트 근거 수",
        )
        candidate.setdefault("evidence_sources", []).append(
            f"목표가/리포트 근거 {item.get('source_count')}건"
        )
    else:
        candidate.setdefault("evidence_sources", []).append("목표가/리포트 확인 필요: 저장 데이터에서 증권사 목표주가를 찾지 못했습니다.")
        candidate.setdefault("quality_flags", []).append("목표가/리포트 확인 필요")
        candidate.setdefault("risk_notes", []).append("증권사 목표가나 리포트 근거가 부족해 가격 조건은 별도 확인이 필요합니다.")
    if item.get("market_value"):
        market_value = float(item.get("market_value") or 0)
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 20, "실제 보유 포트폴리오 비중")
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
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 10, "관심종목 등록")
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


def apply_daily_recommendation_priority_target(
    candidate: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    priority = str(target.get("priority") or "medium")
    daily_recommendation_candidates.add_daily_recommendation_score(
        candidate,
        {"high": 20, "medium": 10, "low": 3}.get(priority, 10),
        "보유/관심 우선순위",
    )
    recent_count = int(target.get("recent_document_count") or 0)
    rag_count = int(target.get("rag_document_count") or 0)
    if recent_count:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(15, recent_count),
            "최근 저장자료",
        )
        candidate.setdefault("reasons", []).append(f"최근 저장자료 {recent_count}건")
    if rag_count:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(15, rag_count),
            "RAG 연결 문서",
        )
        candidate.setdefault("evidence_sources", []).append(f"RAG 연결 문서 {rag_count}건")
    if target.get("thesis_snapshot_connected"):
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 12, "최신 투자 논거 스냅샷")
        candidate.setdefault("evidence_sources", []).append("최신 투자 논거 스냅샷 연결")
    market_matches = target.get("market_journal_matches") or []
    if market_matches:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(10, len(market_matches) * 3),
            "시장일지 연결",
        )
        latest_market = market_matches[0]
        candidate.setdefault("reasons", []).append(
            "시장일지 연결: "
            + compact_interest_text(latest_market.get("summary") or latest_market.get("session_date"), 90)
        )
    if target.get("next_action"):
        candidate.setdefault("risk_notes", []).append(str(target.get("next_action")))
    return candidate


def apply_daily_recommendation_price_check(
    candidate: dict[str, Any],
    *,
    price: object,
    source: object = None,
    checked_at: object = None,
) -> dict[str, Any]:
    if price is not None:
        candidate["baseline_price"] = price
        candidate["baseline_price_source"] = source or "data_provider"
        candidate["baseline_price_checked_at"] = checked_at
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 5, "현재가 확인")
    else:
        candidate.setdefault("risk_notes", []).append("기준 현재가를 확인하지 못해 사후 수익률 추적은 가격 확보 후 보강됩니다.")
        candidate.setdefault("quality_flags", []).append("기준 현재가 미확인")
        daily_recommendation_candidates.add_daily_recommendation_penalty(candidate, "현재가 미확인", 5)
    return candidate
