"""Candidate shaping helpers for daily recommendations."""

from __future__ import annotations

from re import fullmatch
from re import search
from typing import Any

from research_os import daily_recommendation_evidence


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
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
        "evidence_documents": daily_recommendation_evidence.normalize_evidence_documents(
            candidate.get("evidence_documents")
        ),
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
        "policy_signal_summary": candidate.get("policy_signal_summary") or {},
    }


def daily_recommendation_candidate_is_valid(ticker: str, company_name: str) -> bool:
    if not ticker or ticker in {"CASH", "UNKNOWN"}:
        return False
    if fullmatch(r"\d+", ticker) and not fullmatch(r"\d{6}", ticker):
        return False
    if not company_name or company_name.upper().startswith("UNKNOWN"):
        return False
    return True


def ensure_daily_recommendation_candidate(
    candidates_by_ticker: dict[str, dict[str, Any]],
    ticker: str,
    company_name: str,
) -> dict[str, Any]:
    key = daily_recommendation_evidence.normalize_recommendation_ticker(ticker)
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


def add_daily_recommendation_score(candidate: dict[str, Any], points: int | float, label: str) -> None:
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


def add_daily_recommendation_penalty(
    candidate: dict[str, Any],
    label: str,
    points: int | float = 0,
) -> None:
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


def finalize_daily_recommendation_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Normalize recommendation reasons, evidence, risks, and score explanation."""
    if not candidate.get("reasons"):
        candidate.setdefault("reasons", []).append("보유/관심목록과 저장 리서치에 포함된 일일 점검 후보입니다.")
    candidate["reasons"] = daily_recommendation_evidence.unique_text_items(candidate.get("reasons"), 6)
    candidate["evidence_sources"] = daily_recommendation_evidence.unique_text_items(candidate.get("evidence_sources"), 8)
    candidate["evidence_documents"] = daily_recommendation_evidence.normalize_evidence_documents(
        candidate.get("evidence_documents")
    )
    candidate["risk_notes"] = daily_recommendation_evidence.unique_text_items(candidate.get("risk_notes"), 5)
    candidate["score_penalties"] = daily_recommendation_evidence.unique_text_items(candidate.get("score_penalties"), 6)
    candidate["quality_flags"] = daily_recommendation_evidence.unique_text_items(candidate.get("quality_flags"), 6)
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
