"""Daily recommendation milestone tracking helpers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence


TRACKING_MILESTONES = [
    {"key": "7d", "label": "추천 후 1주일", "days": 7},
    {"key": "15d", "label": "추천 후 15일", "days": 15},
    {"key": "1m", "label": "추천 후 1달", "days": 30},
    {"key": "3m", "label": "추천 후 3달", "days": 90},
    {"key": "6m", "label": "추천 후 6달", "days": 180},
]


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


def saved_portfolio_price_lookup(portfolio_store: dict[str, Any]) -> dict[str, tuple[float, str]]:
    """Build a latest saved-current-price lookup from the portfolio store."""
    portfolios = portfolio_store.get("portfolios") if isinstance(portfolio_store, dict) else {}
    if isinstance(portfolios, dict):
        portfolio_values = portfolios.values()
    elif isinstance(portfolios, list):
        portfolio_values = portfolios
    else:
        portfolio_values = []
    latest_by_ticker: dict[str, tuple[float, str, str]] = {}
    for portfolio in portfolio_values:
        if not isinstance(portfolio, dict):
            continue
        for holding in portfolio.get("holdings") or []:
            if not isinstance(holding, dict):
                continue
            ticker = str(holding.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            try:
                price = float(str(holding.get("current_price") or "").replace(",", ""))
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            checked_at = str(holding.get("price_checked_at") or "")
            source = str(holding.get("price_source") or "saved_portfolio").strip() or "saved_portfolio"
            lookup_source = source if source.startswith("saved_portfolio") else f"saved_portfolio:{source}"
            existing = latest_by_ticker.get(ticker)
            if existing is None or checked_at >= existing[2]:
                latest_by_ticker[ticker] = (price, lookup_source, checked_at)
    return {ticker: (price, source) for ticker, (price, source, _checked_at) in latest_by_ticker.items()}


def daily_recommendation_tracking_feedback(records: list[dict]) -> dict[str, dict]:
    def update_stats(stats: dict, change_pct: float) -> None:
        stats["completed_count"] += 1
        stats["change_sum"] += change_pct
        if change_pct > 0.02:
            stats["positive_count"] += 1
        elif -0.02 <= change_pct <= 0.02:
            stats["flat_count"] += 1
        else:
            stats["negative_count"] += 1
        if stats["worst_change_pct"] is None or change_pct < stats["worst_change_pct"]:
            stats["worst_change_pct"] = change_pct
        if stats["best_change_pct"] is None or change_pct > stats["best_change_pct"]:
            stats["best_change_pct"] = change_pct

    def summarize_stats(key: str, stats: dict) -> dict:
        completed = int(stats["completed_count"])
        hit_rate = (int(stats["positive_count"]) + 0.5 * int(stats["flat_count"])) / completed
        average_change_pct = float(stats["change_sum"]) / completed
        return {
            "key": key,
            "label": stats.get("label") or key,
            "completed_count": completed,
            "positive_count": stats["positive_count"],
            "flat_count": stats["flat_count"],
            "negative_count": stats["negative_count"],
            "hit_rate": round(hit_rate, 4),
            "average_change_pct": round(average_change_pct, 4),
            "worst_change_pct": round(float(stats["worst_change_pct"]), 4),
            "best_change_pct": round(float(stats["best_change_pct"]), 4),
        }

    feedback: dict[str, dict] = {}
    for record in records:
        ticker = daily_recommendation_evidence.normalize_recommendation_ticker(record.get("ticker"))
        if not ticker:
            continue
        stats = feedback.setdefault(
            ticker,
            {
                "ticker": ticker,
                "completed_count": 0,
                "positive_count": 0,
                "flat_count": 0,
                "negative_count": 0,
                "change_sum": 0.0,
                "worst_change_pct": None,
                "best_change_pct": None,
                "milestones": {},
            },
        )
        for milestone in record.get("tracking_milestones") or []:
            if not isinstance(milestone, dict) or milestone.get("status") != "complete":
                continue
            try:
                change_pct = float(milestone.get("price_change_pct"))
            except (TypeError, ValueError):
                continue
            update_stats(stats, change_pct)
            milestone_key = str(milestone.get("key") or milestone.get("label") or "unknown")
            milestone_stats = stats["milestones"].setdefault(
                milestone_key,
                {
                    "label": str(milestone.get("label") or milestone_key),
                    "completed_count": 0,
                    "positive_count": 0,
                    "flat_count": 0,
                    "negative_count": 0,
                    "change_sum": 0.0,
                    "worst_change_pct": None,
                    "best_change_pct": None,
                },
            )
            update_stats(milestone_stats, change_pct)

    actionable: dict[str, dict] = {}
    for ticker, stats in feedback.items():
        completed = int(stats["completed_count"])
        if completed < 2:
            continue
        hit_rate = (int(stats["positive_count"]) + 0.5 * int(stats["flat_count"])) / completed
        average_change_pct = float(stats["change_sum"]) / completed
        milestone_breakdown = [
            summarize_stats(key, value)
            for key, value in stats.get("milestones", {}).items()
            if int(value.get("completed_count") or 0) > 0
        ]
        milestone_breakdown.sort(key=lambda item: (item["hit_rate"], item["average_change_pct"], -item["completed_count"]))
        weakest_milestone = milestone_breakdown[0] if milestone_breakdown else None
        penalty = 0
        if hit_rate < 0.25 and average_change_pct <= -0.05:
            penalty = 12
        elif hit_rate < 0.4 and average_change_pct < 0:
            penalty = 6
        horizon_penalty = 0
        weak_15d = next((item for item in milestone_breakdown if item["key"] == "15d"), None)
        if (
            weak_15d
            and weak_15d["completed_count"] >= 2
            and weak_15d["hit_rate"] < 0.25
            and weak_15d["average_change_pct"] <= -0.05
        ):
            horizon_penalty = 4
            penalty += horizon_penalty
        if penalty <= 0:
            continue
        actionable[ticker] = {
            "ticker": ticker,
            "completed_count": completed,
            "positive_count": stats["positive_count"],
            "flat_count": stats["flat_count"],
            "negative_count": stats["negative_count"],
            "worst_change_pct": stats["worst_change_pct"],
            "best_change_pct": stats["best_change_pct"],
            "hit_rate": round(hit_rate, 4),
            "average_change_pct": round(average_change_pct, 4),
            "penalty_points": penalty,
            "base_penalty_points": penalty - horizon_penalty,
            "horizon_penalty_points": horizon_penalty,
            "weakest_milestone": weakest_milestone,
            "milestone_breakdown": milestone_breakdown,
        }
    return actionable


def apply_daily_recommendation_tracking_feedback(candidate: dict, feedback: dict | None) -> dict:
    if not feedback:
        return candidate
    completed = int(feedback.get("completed_count") or 0)
    hit_rate = float(feedback.get("hit_rate") or 0)
    average_change_pct = float(feedback.get("average_change_pct") or 0)
    penalty = int(feedback.get("penalty_points") or 0)
    weakest = feedback.get("weakest_milestone") if isinstance(feedback.get("weakest_milestone"), dict) else None
    review_hold = completed >= 3 and penalty >= 12 and hit_rate <= 0.05 and average_change_pct <= -0.05
    candidate["tracking_feedback_profile"] = {
        "completed_count": completed,
        "hit_rate": round(hit_rate, 4),
        "average_change_pct": round(average_change_pct, 4),
        "penalty_points": penalty,
        "horizon_penalty_points": int(feedback.get("horizon_penalty_points") or 0),
        "weakest_milestone": weakest,
        "review_hold": review_hold,
    }
    daily_recommendation_candidates.add_daily_recommendation_penalty(candidate, "최근 추천 성과 부진 피드백", penalty)
    candidate.setdefault("risk_notes", []).append(
        f"최근 추천 추적 {completed}건 hit rate {hit_rate * 100:.1f}%, 평균 수익률 {average_change_pct * 100:.1f}%로 재추천 전 논거 재검증이 필요합니다."
    )
    if weakest:
        candidate.setdefault("risk_notes", []).append(
            f"취약 추적 구간: {weakest.get('label')} hit rate {float(weakest.get('hit_rate') or 0) * 100:.1f}%, 평균 {float(weakest.get('average_change_pct') or 0) * 100:.1f}%."
        )
    candidate.setdefault("quality_flags", []).append("최근 추천 성과 피드백 감점")
    if review_hold:
        candidate.setdefault("quality_flags", []).append("반복 부진 후보 top3 보류")
        candidate.setdefault("risk_notes", []).append("충분한 대체 후보가 있으면 반복 부진 해소 전 top3 추천에서 보류합니다.")
    candidate.setdefault("evidence_sources", []).append(
        f"추적 성과 피드백: 완료 {completed}건 · hit rate {hit_rate * 100:.1f}% · 평균 {average_change_pct * 100:.1f}%"
    )
    return candidate


def daily_recommendation_candidate_review_hold(candidate: dict) -> bool:
    profile = candidate.get("tracking_feedback_profile")
    if not isinstance(profile, dict):
        return False
    return bool(profile.get("review_hold"))
