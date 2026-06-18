"""Candidate profile enrichment helpers for daily recommendations."""

from __future__ import annotations

from typing import Any

from research_os import daily_recommendation_candidates


def apply_daily_recommendation_freshness_profile(
    candidate: dict[str, Any],
    *,
    ticker: str,
    verification: object,
    profile: dict[str, Any] | None,
    freshness: dict[str, Any] | None,
) -> dict[str, Any]:
    company_name = str(getattr(verification, "company_name", "") or "").strip()
    if company_name and candidate.get("company_name") == ticker:
        candidate["company_name"] = company_name

    freshness = freshness if isinstance(freshness, dict) else {}
    tone = freshness.get("tone")
    if tone == "ok":
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 10, "저장자료 신선도 양호")
    elif tone == "warning":
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 5, "저장자료 신선도 확인 필요")
        candidate.setdefault("quality_flags", []).append("저장자료 신선도 확인 필요")
        daily_recommendation_candidates.add_daily_recommendation_penalty(candidate, "최근 자료 신선도 보강 필요", 2)
    candidate.setdefault("evidence_sources", []).append(freshness.get("summary") or "저장자료 신선도 확인")

    profile = profile if isinstance(profile, dict) else {}
    if profile.get("analysis_focus"):
        candidate.setdefault("reasons", []).append(f"분석 초점: {profile.get('analysis_focus')}")
    return candidate


def apply_daily_recommendation_overseas_tracking(candidate: dict[str, Any]) -> dict[str, Any]:
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
