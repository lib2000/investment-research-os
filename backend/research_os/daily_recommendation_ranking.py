"""Daily recommendation candidate ranking helpers."""

from __future__ import annotations

from research_os import daily_recommendation_tracking

MARKET_ORDER = {"KR": 0, "US": 1}


def daily_recommendation_candidate_review_hold(candidate: dict) -> bool:
    return daily_recommendation_tracking.daily_recommendation_candidate_review_hold(candidate)


def daily_recommendation_candidate_soft_tracking_hold(candidate: dict) -> bool:
    return daily_recommendation_tracking.daily_recommendation_candidate_soft_tracking_hold(candidate)


def daily_recommendation_candidate_market(candidate: dict) -> str:
    market = str(candidate.get("market") or "").strip().upper()
    if market in MARKET_ORDER:
        return market
    currency = str(candidate.get("currency") or "").strip().upper()
    ticker = str(candidate.get("ticker") or "").strip()
    if currency == "KRW" or (ticker.isdigit() and len(ticker) == 6):
        return "KR"
    return "US"


def _market_label(market: str) -> str:
    return "한국" if market == "KR" else "미국" if market == "US" else market


def _rank_candidates(candidates: list[dict], selected_limit: int, *, market: str, include_market_label: bool) -> tuple[list[dict], list[str]]:
    strong_candidates = [
        candidate
        for candidate in candidates
        if not daily_recommendation_candidate_review_hold(candidate)
        and not daily_recommendation_candidate_soft_tracking_hold(candidate)
    ]
    soft_hold_candidates = [
        candidate
        for candidate in candidates
        if not daily_recommendation_candidate_review_hold(candidate)
        and daily_recommendation_candidate_soft_tracking_hold(candidate)
    ]
    hold_candidates = [
        candidate
        for candidate in candidates
        if daily_recommendation_candidate_review_hold(candidate)
    ]
    selected_candidates = (
        strong_candidates[:selected_limit]
        if len(strong_candidates) >= selected_limit
        else (strong_candidates + soft_hold_candidates + hold_candidates)[:selected_limit]
    )
    omitted_soft_hold_tickers = [
        str(candidate.get("ticker") or "").strip()
        for candidate in soft_hold_candidates
        if candidate not in selected_candidates and str(candidate.get("ticker") or "").strip()
    ][:5]
    omitted_hold_tickers = [
        str(candidate.get("ticker") or "").strip()
        for candidate in hold_candidates
        if candidate not in selected_candidates and str(candidate.get("ticker") or "").strip()
    ][:5]
    warning_prefix = f"{_market_label(market)} " if include_market_label else ""
    warnings: list[str] = []
    if omitted_soft_hold_tickers:
        warnings.append(f"{warning_prefix}추적 성과 약세 top3 대체: {', '.join(omitted_soft_hold_tickers)}")
    if omitted_hold_tickers:
        warnings.append(f"{warning_prefix}반복 부진 top3 보류: {', '.join(omitted_hold_tickers)}")
    ranked_candidates = [
        {
            **candidate,
            "market": market,
            "market_label": _market_label(market),
            "rank": index,
        }
        for index, candidate in enumerate(selected_candidates, start=1)
    ]
    return ranked_candidates, warnings


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
    result_warnings = []
    candidates_by_market: dict[str, list[dict]] = {market: [] for market in MARKET_ORDER}
    for candidate in candidates:
        candidates_by_market.setdefault(daily_recommendation_candidate_market(candidate), []).append(candidate)
    active_markets = [market for market, rows in candidates_by_market.items() if rows]
    include_market_label = len(active_markets) > 1
    ranked_candidates: list[dict] = []
    market_counts: dict[str, int] = {}
    for market in sorted(active_markets, key=lambda value: MARKET_ORDER.get(value, 99)):
        ranked_market_candidates, market_warnings = _rank_candidates(
            candidates_by_market[market],
            selected_limit,
            market=market,
            include_market_label=include_market_label,
        )
        ranked_candidates.extend(ranked_market_candidates)
        market_counts[market] = len(ranked_market_candidates)
        result_warnings.extend(market_warnings)
    result_warnings.extend(list(warnings or []))
    return {
        "status": "success",
        "module": "daily_recommendation_candidate_ranking",
        "as_of": as_of,
        "universe_count": len(candidates_by_ticker),
        "per_market_limit": selected_limit,
        "market_counts": market_counts,
        "selected_count": len(ranked_candidates),
        "consensus_summary": consensus_summary,
        "candidates": ranked_candidates,
        "warnings": result_warnings[:10],
    }
