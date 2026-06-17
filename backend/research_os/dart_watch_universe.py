"""DART watch universe and daily coverage helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from re import fullmatch

from research_os.dart_watch_exclusions import append_unique_dart_exclusion
from research_os.dart_watch_exclusions import dart_excluded_ticker_entry
from research_os.dart_watch_exclusions import dart_watch_exclusion_reason


def dart_watch_universe(runtime, settings) -> dict:
    portfolio_tickers: set[str] = set()
    interest_tickers: set[str] = set()
    excluded_tickers: list[dict] = []
    try:
        store = runtime.read_portfolio_store(settings)
        for portfolio in (store.get("portfolios") or {}).values():
            if not isinstance(portfolio, dict):
                continue
            for holding in portfolio.get("holdings") or []:
                ticker = runtime.normalize_ticker(str((holding or {}).get("ticker") or ""))
                exclusion_reason = dart_watch_exclusion_reason(holding)
                if fullmatch(r"\d{6}", ticker) and not exclusion_reason:
                    portfolio_tickers.add(ticker)
                elif ticker and ticker not in {"UNKNOWN", "CASH"}:
                    append_unique_dart_exclusion(
                        runtime,
                        excluded_tickers,
                        dart_excluded_ticker_entry(
                            ticker,
                            "portfolio",
                            exclusion_reason or "non_kr_ticker",
                            holding,
                        ),
                    )
    except Exception:
        pass
    try:
        interests = runtime.read_interest_list(settings)
        for item in interests.get("tickers", []):
            if not isinstance(item, dict):
                continue
            ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
            exclusion_reason = dart_watch_exclusion_reason(item)
            if fullmatch(r"\d{6}", ticker) and not exclusion_reason:
                interest_tickers.add(ticker)
            elif ticker and ticker not in {"UNKNOWN", "CASH"}:
                append_unique_dart_exclusion(
                    runtime,
                    excluded_tickers,
                    dart_excluded_ticker_entry(
                        ticker,
                        "interest",
                        exclusion_reason or "non_kr_ticker",
                        item,
                    ),
                )
    except Exception:
        pass
    target_tickers = sorted(portfolio_tickers | interest_tickers)
    return {
        "target_tickers": target_tickers,
        "portfolio_tickers": sorted(portfolio_tickers),
        "interest_tickers": sorted(interest_tickers),
        "excluded_tickers": excluded_tickers,
        "target_count": len(target_tickers),
        "portfolio_count": len(portfolio_tickers),
        "interest_count": len(interest_tickers),
    }


def dart_watch_tickers(runtime, settings) -> list[str]:
    return list(dart_watch_universe(runtime, settings).get("target_tickers") or [])


def dart_daily_check_status(runtime, cache: dict, settings) -> dict:
    today = runtime.current_storage_date().isoformat()
    daily_check = cache.get("daily_check") if isinstance(cache, dict) else {}
    if not isinstance(daily_check, dict):
        daily_check = {}
    checked_date = str(daily_check.get("date") or "")
    target_universe = runtime.dart_watch_universe(settings)
    missing_today = checked_date != today
    missing_targets = sorted(
        set(target_universe.get("target_tickers") or [])
        - set(daily_check.get("checked_tickers") or [])
    ) if not missing_today else list(target_universe.get("target_tickers") or [])
    target_ticker_set = {
        runtime.normalize_ticker(str(item))
        for item in (target_universe.get("target_tickers") or [])
        if runtime.normalize_ticker(str(item))
    }
    failed_tickers = sorted(
        {
            runtime.normalize_ticker(str(item))
            for item in (daily_check.get("failed_tickers") or [])
            if runtime.normalize_ticker(str(item)) and runtime.normalize_ticker(str(item)) in target_ticker_set
        }
    )
    excluded_tickers = target_universe.get("excluded_tickers") or daily_check.get("excluded_tickers") or []
    due = bool(missing_today or missing_targets)
    current_target_count = int(target_universe.get("target_count") or 0)
    checked_tickers = [
        runtime.normalize_ticker(str(item))
        for item in (daily_check.get("checked_tickers") or [])
        if runtime.normalize_ticker(str(item))
    ]
    checked_target_tickers = set(checked_tickers) & target_ticker_set
    checked_count = 0 if missing_today else len(checked_target_tickers - set(failed_tickers))
    coverage_rate = checked_count / current_target_count if current_target_count else 1.0
    if due:
        reliability_status = "점검 필요"
    elif failed_tickers:
        reliability_status = "부분 신뢰"
    else:
        reliability_status = "신뢰 가능"
    next_check_after = None
    checked_at = daily_check.get("checked_at")
    if checked_at:
        try:
            base_dt = datetime.fromisoformat(str(checked_at))
            next_check_after = (base_dt + timedelta(hours=max(settings.dart_filing_refresh_hours, 1))).isoformat()
        except ValueError:
            next_check_after = None
    return {
        "date": today,
        "status": "due" if due else "partial_success" if failed_tickers else "complete",
        "due": due,
        "last_checked_date": checked_date or None,
        "last_checked_at": checked_at,
        "next_check_after": next_check_after,
        "last_target_count": daily_check.get("target_count", 0),
        "current_target_count": current_target_count,
        "checked_count": checked_count,
        "coverage_rate": coverage_rate,
        "reliability_status": reliability_status,
        "reliability_message": (
            f"{today} 기준 {checked_count}/{current_target_count}개 종목 공시 점검 완료"
            if current_target_count
            else "점검 대상 국내 종목이 없습니다."
        ),
        "missing_tickers": missing_targets,
        "failed_tickers": failed_tickers,
        "failure_count": len(failed_tickers),
        "excluded_tickers": excluded_tickers,
        "excluded_count": len(excluded_tickers),
        "target_universe": target_universe,
    }


def active_dart_last_failures(runtime, cache: dict, target_universe: dict, limit: int = 10) -> list[dict]:
    """Return DART failures that still belong to the current watch universe."""
    if not isinstance(cache, dict):
        return []
    target_tickers = {
        runtime.normalize_ticker(str(item))
        for item in (target_universe.get("target_tickers") or [])
        if runtime.normalize_ticker(str(item))
    }
    excluded_tickers = {
        runtime.normalize_ticker(str((item or {}).get("ticker") or ""))
        for item in (target_universe.get("excluded_tickers") or [])
        if isinstance(item, dict) and runtime.normalize_ticker(str(item.get("ticker") or ""))
    }
    active_failures: list[dict] = []
    for item in cache.get("last_failures") or []:
        if not isinstance(item, dict):
            continue
        ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
        if ticker and ticker in excluded_tickers:
            continue
        if ticker and target_tickers and ticker not in target_tickers:
            continue
        active_failures.append(item)
        if len(active_failures) >= max(1, int(limit or 10)):
            break
    return active_failures
