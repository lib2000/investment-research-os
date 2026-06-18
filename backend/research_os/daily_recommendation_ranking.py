"""Daily recommendation candidate ranking helpers."""

from __future__ import annotations

from research_os import daily_recommendation_tracking


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
