"""Candidate shaping helpers for daily recommendations."""

from __future__ import annotations

from re import fullmatch
from re import search
from typing import Any

from research_os import daily_recommendation_evidence


def _contains_any(value: object, terms: tuple[str, ...]) -> bool:
    text = str(value or "").lower()
    return any(term.lower() in text for term in terms)


def _signal_item(
    *,
    key: str,
    label: str,
    summary: str,
    count: int = 0,
    score_applied: bool = False,
    tone: str = "neutral",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "count": max(0, int(count or 0)),
        "score_applied": bool(score_applied),
        "tone": tone,
    }


def build_recommendation_signal_breakdown(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    components = [
        item
        for item in candidate.get("score_components", [])
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    evidence_sources = [str(item or "").strip() for item in candidate.get("evidence_sources", []) if str(item or "").strip()]
    documents = [
        item
        for item in candidate.get("evidence_documents", [])
        if isinstance(item, dict)
    ]
    component_labels = [str(item.get("label") or "") for item in components]
    market_components = [
        item
        for item in components
        if _contains_any(item.get("label"), ("시장", "목표가", "현재가", "가격", "보유", "포트폴리오", "투자 방향"))
    ]
    filing_documents = [
        item
        for item in documents
        if _contains_any(item.get("source_type"), ("filing", "dart"))
        or _contains_any(item.get("report_type"), ("filing", "dart"))
    ]
    policy_signal = candidate.get("policy_signal_summary") if isinstance(candidate.get("policy_signal_summary"), dict) else {}
    policy_count = int(policy_signal.get("count") or 0)
    policy_level = str(policy_signal.get("match_level_label") or policy_signal.get("match_level") or "참고").strip()
    policy_summary = (
        f"{policy_level} {policy_count}건 · {'점수 반영' if policy_signal.get('score_applied') else '참고만'}"
        if policy_count
        else "직접 정책 신호 없음"
    )
    news_documents = [
        item
        for item in documents
        if item not in filing_documents
        and not _contains_any(item.get("source_type"), ("policy", "filing", "dart"))
        and not _contains_any(item.get("report_type"), ("official_policy", "filing", "dart"))
    ]
    news_sources = [
        item
        for item in evidence_sources
        if _contains_any(item, ("뉴스", "리포트", "자료 묶음", "공개 IR", "SEC", "RAG"))
    ]
    profile = candidate.get("investment_direction_profile") if isinstance(candidate.get("investment_direction_profile"), dict) else {}
    profile_labels: list[str] = []
    if profile:
        for item in (profile.get("matched_directions") or profile.get("directions") or profile.get("labels") or []):
            label = item.get("label") or item.get("name") if isinstance(item, dict) else item
            label_text = str(label or "").strip()
            if label_text:
                profile_labels.append(label_text)
    sentiment_sources = [
        *[label for label in component_labels if _contains_any(label, ("투자 방향", "심리", "센티먼트", "추세"))],
        *[item for item in evidence_sources if _contains_any(item, ("시장일지", "심리", "센티먼트", "투자 방향"))],
        *profile_labels,
    ]
    market_summary = (
        f"{market_components[0].get('label')} +{int(market_components[0].get('points') or 0)}점"
        if market_components
        else "시장/가격 신호는 참고 수준"
    )
    filing_summary = (
        f"최근 공시 {len(filing_documents)}건 연결"
        if filing_documents
        else "직접 공시 근거 없음"
    )
    news_summary = (
        f"뉴스/리포트 근거 {max(len(news_documents), len(news_sources))}건"
        if news_documents or news_sources
        else "뉴스 근거 없음"
    )
    sentiment_summary = (
        " · ".join(dict.fromkeys(sentiment_sources[:3]))
        if sentiment_sources
        else "심리/방향성 신호 없음"
    )
    return [
        _signal_item(
            key="market",
            label="시장",
            summary=market_summary,
            count=len(market_components),
            score_applied=bool(market_components),
            tone="ok" if market_components else "neutral",
        ),
        _signal_item(
            key="filing",
            label="공시",
            summary=filing_summary,
            count=len(filing_documents),
            score_applied=any(_contains_any(label, ("공시", "DART")) for label in component_labels),
            tone="ok" if filing_documents else "neutral",
        ),
        _signal_item(
            key="policy",
            label="정책",
            summary=policy_summary,
            count=policy_count,
            score_applied=bool(policy_signal.get("score_applied")),
            tone="ok" if policy_signal.get("score_applied") else "reference" if policy_count else "neutral",
        ),
        _signal_item(
            key="news",
            label="뉴스",
            summary=news_summary,
            count=max(len(news_documents), len(news_sources)),
            score_applied=any(_contains_any(label, ("리포트", "자료", "RAG")) for label in component_labels),
            tone="ok" if news_documents or news_sources else "neutral",
        ),
        _signal_item(
            key="sentiment",
            label="심리",
            summary=sentiment_summary,
            count=len(sentiment_sources),
            score_applied=bool(sentiment_sources),
            tone="ok" if sentiment_sources else "neutral",
        ),
    ]


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
        "signal_breakdown": candidate.get("signal_breakdown") or build_recommendation_signal_breakdown(candidate),
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
    candidate["signal_breakdown"] = build_recommendation_signal_breakdown(candidate)
    return candidate
