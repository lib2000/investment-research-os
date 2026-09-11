"""Portfolio account-sync calculation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.portfolio_import import (
    is_domestic_sync_like_ticker,
    normalize_import_ticker,
    portfolio_currency_for_ticker,
)
from research_os.portfolio_store import infer_holding_fx_rate
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


MIN_PLAUSIBLE_KRW_FX_RATE = 100.0
MAX_PLAUSIBLE_KRW_FX_RATE = 10_000.0


def _current_sync_timestamp() -> str:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))
    return datetime.now(korea_timezone).isoformat(timespec="seconds")


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _plausible_krw_fx_rate(value: float | None) -> bool:
    return bool(
        value is not None
        and MIN_PLAUSIBLE_KRW_FX_RATE <= value <= MAX_PLAUSIBLE_KRW_FX_RATE
    )


def _holding_krw_fx_rate(holding: PortfolioHolding) -> float | None:
    rate = infer_holding_fx_rate(holding)
    return rate if _plausible_krw_fx_rate(rate) else None


def _portfolio_usd_krw_fx_rate(portfolio: SavedPortfolio) -> float | None:
    rates = [
        rate
        for holding in portfolio.holdings
        if holding.currency.upper() == "USD"
        and (rate := _holding_krw_fx_rate(holding)) is not None
    ]
    return float(median(rates)) if rates else None


def _convert_toss_usd_valuation(
    source: dict,
    *,
    fx_rate: float,
    fallback: PortfolioHolding | None = None,
) -> dict[str, float | None]:
    """Convert Toss-native USD totals into the portfolio's KRW value basis."""
    source_market_value = _number(source.get("market_value"))
    source_cost_basis = _number(source.get("cost_basis"))
    market_value = (
        round(source_market_value * fx_rate, 2)
        if source_market_value is not None
        else fallback.market_value if fallback else None
    )
    cost_basis = (
        round(source_cost_basis * fx_rate, 2)
        if source_cost_basis is not None
        else fallback.cost_basis if fallback else None
    )
    if market_value is not None and cost_basis is not None:
        unrealized_gain = round(market_value - cost_basis, 2)
    else:
        source_gain = _number(source.get("unrealized_gain"))
        unrealized_gain = (
            round(source_gain * fx_rate, 2)
            if source_gain is not None
            else fallback.unrealized_gain if fallback else None
        )
    return {
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_gain": unrealized_gain,
    }


def portfolio_sync_history_path(settings: Settings) -> Path:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "portfolio_sync_history.jsonl"


def append_portfolio_sync_history(
    settings: Settings,
    *,
    portfolio_name: str,
    summary: dict,
) -> None:
    path = portfolio_sync_history_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": _current_sync_timestamp(),
        "portfolio_name": portfolio_name,
        "broker": summary.get("broker"),
        "scope": summary.get("scope"),
        "mode": summary.get("mode"),
        "checked_at": summary.get("checked_at"),
        "updated_count": summary.get("updated_count", 0),
        "confirmed_count": summary.get("confirmed_count", 0),
        "imported_count": summary.get("imported_count", 0),
        "skipped_count": summary.get("skipped_count", 0),
        "changes": summary.get("changes", []),
        "skipped": summary.get("skipped", []),
        "message": summary.get("message"),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def read_portfolio_sync_history(settings: Settings, *, limit: int = 10) -> list[dict]:
    path = portfolio_sync_history_path(settings)
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
        if len(records) >= limit:
            break
    return records


def protect_manual_or_overseas_holding_sync_state(
    holding: PortfolioHolding,
    *,
    checked_at: str | None = None,
) -> PortfolioHolding:
    """Mark non-domestic or manual holdings so account sync cannot overwrite them later."""
    ticker = normalize_import_ticker(holding.ticker)
    holding_currency = portfolio_currency_for_ticker(ticker, holding.currency)
    update = {
        "ticker": ticker,
        "currency": holding_currency,
    }
    if ticker == "CASH" or (holding_currency == "KRW" and is_domestic_sync_like_ticker(ticker)):
        return holding.model_copy(update=update)
    if holding.sync_status:
        return holding.model_copy(update=update)
    update.update(
        {
            "sync_status": "manual_or_overseas_protected",
            "sync_source": holding.sync_source or "portfolio_state_guard",
            "sync_checked_at": holding.sync_checked_at or checked_at,
            "sync_message": holding.sync_message
            or "해외주식 또는 수동 관리 종목이라 기존 수량을 보호했습니다.",
        }
    )
    return holding.model_copy(update=update)


def apply_kiwoom_domestic_balance_to_portfolio(
    portfolio: SavedPortfolio,
    balance: dict,
    *,
    checked_at: str,
) -> tuple[SavedPortfolio, dict]:
    """Apply Kiwoom domestic balances while preserving overseas/manual holdings."""
    balance_by_ticker = {
        normalize_import_ticker(item.get("ticker", "")): item
        for item in balance.get("holdings", [])
        if isinstance(item, dict) and item.get("ticker")
    }
    changes: list[dict] = []
    skipped: list[dict] = []
    synced_holdings: list[PortfolioHolding] = []

    for holding in portfolio.holdings:
        ticker = normalize_import_ticker(holding.ticker)
        holding_currency = portfolio_currency_for_ticker(ticker, holding.currency)
        source = balance_by_ticker.get(ticker) if holding_currency == "KRW" else None
        if source:
            update = {
                "ticker": ticker,
                "name": holding.name or source.get("name"),
                "quantity": source.get("quantity") if source.get("quantity") is not None else holding.quantity,
                "average_cost": source.get("average_cost") if source.get("average_cost") is not None else holding.average_cost,
                "current_price": source.get("current_price") if source.get("current_price") is not None else holding.current_price,
                "market_value": source.get("market_value") if source.get("market_value") is not None else holding.market_value,
                "cost_basis": source.get("cost_basis") if source.get("cost_basis") is not None else holding.cost_basis,
                "unrealized_gain": source.get("unrealized_gain") if source.get("unrealized_gain") is not None else holding.unrealized_gain,
                "unrealized_return": source.get("unrealized_return") if source.get("unrealized_return") is not None else holding.unrealized_return,
                "currency": "KRW",
                "price_source": "kiwoom_domestic_balance",
                "price_refresh_status": "account_synced",
                "price_checked_at": checked_at,
                "sync_status": "account_synced",
                "sync_source": "kiwoom_domestic_balance",
                "sync_checked_at": checked_at,
                "sync_message": "키움 국내 잔고와 매칭되어 수량/평단/평가금액을 갱신했습니다.",
            }
            synced = holding.model_copy(update=update)
            synced_holdings.append(synced)
            changes.append(
                {
                    "ticker": ticker,
                    "name": synced.name or source.get("name") or ticker,
                    "old_quantity": holding.quantity,
                    "new_quantity": synced.quantity,
                    "old_average_cost": holding.average_cost,
                    "new_average_cost": synced.average_cost,
                    "old_market_value": holding.market_value,
                    "new_market_value": synced.market_value,
                    "changed": (holding.quantity != synced.quantity)
                    or (holding.average_cost != synced.average_cost)
                    or (holding.market_value != synced.market_value),
                }
            )
            continue

        reason = (
            "kiwoom_domestic_missing"
            if holding_currency == "KRW" and is_domestic_sync_like_ticker(ticker)
            else "manual_or_overseas_protected"
        )
        message = (
            "키움 국내 잔고에서 찾지 못해 기존 수량을 유지했습니다."
            if reason == "kiwoom_domestic_missing"
            else "해외주식 또는 수동 관리 종목이라 기존 수량을 보호했습니다."
        )
        synced_holdings.append(
            holding.model_copy(
                update={
                    "currency": holding_currency,
                    "sync_status": reason,
                    "sync_source": "kiwoom_domestic_balance",
                    "sync_checked_at": checked_at,
                    "sync_message": message,
                }
            )
        )
        skipped.append(
            {
                "ticker": ticker,
                "name": holding.name or ticker,
                "quantity": holding.quantity,
                "reason": reason,
            }
        )

    synced_portfolio = portfolio.model_copy(
        update={
            "holdings": synced_holdings,
            "updated_at": checked_at,
            "holding_count": len(synced_holdings),
        }
    )
    return synced_portfolio, {
        "status": "success",
        "broker": "KIWOOM",
        "scope": "domestic_stock_only",
        "api_id": balance.get("api_id", "kt00018"),
        "checked_at": checked_at,
        "updated_count": sum(1 for item in changes if item.get("changed")),
        "confirmed_count": sum(1 for item in changes if not item.get("changed")),
        "skipped_count": len(skipped),
        "changes": changes,
        "skipped": skipped,
        "message": "키움 국내 잔고와 매칭된 종목만 수량/평단/평가금액을 갱신했습니다. 해외·수동 종목은 기존 수량을 보존했습니다.",
    }


def apply_toss_holdings_to_portfolio(
    portfolio: SavedPortfolio,
    balance: dict,
    *,
    checked_at: str,
    import_untracked: bool = False,
    preserve_non_toss_holdings: bool = False,
) -> tuple[SavedPortfolio, dict]:
    """Apply read-only Toss KR/US holdings to a saved portfolio.

    Existing holdings are updated only when their ticker is present in the
    Toss response. Holdings absent from the response stay untouched and are
    marked as ``toss_missing`` for review. Remote holdings that are not yet in
    the selected saved portfolio are reported as ``untracked_remote`` rather
    than silently added by default. The automatic owner workflow opts into
    importing remote positions while preserving holdings owned by other
    brokers or entered manually.
    """
    balance_by_ticker = {
        normalize_import_ticker(item.get("ticker", "")): item
        for item in balance.get("holdings", [])
        if isinstance(item, dict) and item.get("ticker")
    }
    changes: list[dict] = []
    skipped: list[dict] = []
    synced_holdings: list[PortfolioHolding] = []
    matched_tickers: set[str] = set()
    applied_fx_rates: dict[str, float] = {}
    fallback_usd_fx_rate = _portfolio_usd_krw_fx_rate(portfolio)

    for holding in portfolio.holdings:
        ticker = normalize_import_ticker(holding.ticker)
        source = balance_by_ticker.get(ticker)
        if source:
            matched_tickers.add(ticker)
            source_currency = portfolio_currency_for_ticker(
                ticker,
                source.get("currency") or holding.currency,
            )
            valuation_update: dict[str, float | None]
            applied_fx_rate: float | None = None
            if source_currency == "USD":
                applied_fx_rate = _holding_krw_fx_rate(holding) or fallback_usd_fx_rate
                if applied_fx_rate is None:
                    synced_holdings.append(
                        holding.model_copy(
                            update={
                                "sync_status": "toss_fx_unavailable",
                                "sync_source": "toss_holdings",
                                "sync_checked_at": checked_at,
                                "sync_message": (
                                    "토스증권의 USD 보유자산은 확인했지만 원화 환산 기준을 "
                                    "확인하지 못해 기존 수량과 평가금액을 보존했습니다."
                                ),
                            }
                        )
                    )
                    skipped.append(
                        {
                            "ticker": ticker,
                            "name": holding.name or source.get("name") or ticker,
                            "quantity": holding.quantity,
                            "reason": "toss_fx_unavailable",
                        }
                    )
                    continue
                valuation_update = _convert_toss_usd_valuation(
                    source,
                    fx_rate=applied_fx_rate,
                    fallback=holding,
                )
                applied_fx_rates[ticker] = round(applied_fx_rate, 4)
            else:
                valuation_update = {
                    "market_value": source.get("market_value")
                    if source.get("market_value") is not None
                    else holding.market_value,
                    "cost_basis": source.get("cost_basis")
                    if source.get("cost_basis") is not None
                    else holding.cost_basis,
                    "unrealized_gain": source.get("unrealized_gain")
                    if source.get("unrealized_gain") is not None
                    else holding.unrealized_gain,
                }
            update = {
                "ticker": ticker,
                "name": holding.name or source.get("name"),
                "quantity": source.get("quantity") if source.get("quantity") is not None else holding.quantity,
                "average_cost": source.get("average_cost") if source.get("average_cost") is not None else holding.average_cost,
                "current_price": source.get("current_price") if source.get("current_price") is not None else holding.current_price,
                **valuation_update,
                "unrealized_return": source.get("unrealized_return") if source.get("unrealized_return") is not None else holding.unrealized_return,
                "currency": source_currency,
                "price_source": "toss_holdings",
                "price_refresh_status": "account_synced",
                "price_checked_at": checked_at,
                "sync_status": "account_synced",
                "sync_source": "toss_holdings",
                "sync_checked_at": checked_at,
                "sync_message": (
                    f"토스증권 보유자산과 매칭되어 수량/평단/평가금액을 갱신했습니다. "
                    f"USD 평가는 저장 포트폴리오 기준환율 {applied_fx_rate:,.2f}원을 적용했습니다."
                    if applied_fx_rate is not None
                    else "토스증권 보유자산과 매칭되어 수량/평단/평가금액을 갱신했습니다."
                ),
            }
            synced = holding.model_copy(update=update)
            synced_holdings.append(synced)
            changes.append(
                {
                    "ticker": ticker,
                    "name": synced.name or source.get("name") or ticker,
                    "old_quantity": holding.quantity,
                    "new_quantity": synced.quantity,
                    "old_average_cost": holding.average_cost,
                    "new_average_cost": synced.average_cost,
                    "old_market_value": holding.market_value,
                    "new_market_value": synced.market_value,
                    "valuation_fx_rate": applied_fx_rate,
                    "changed": (holding.quantity != synced.quantity)
                    or (holding.average_cost != synced.average_cost)
                    or (holding.market_value != synced.market_value),
                }
            )
            continue

        if preserve_non_toss_holdings and holding.sync_source != "toss_holdings":
            synced_holdings.append(holding)
            skipped.append(
                {
                    "ticker": ticker,
                    "name": holding.name or ticker,
                    "quantity": holding.quantity,
                    "reason": "non_toss_holding_preserved",
                }
            )
            continue

        synced_holdings.append(
            holding.model_copy(
                update={
                    "sync_status": "toss_missing",
                    "sync_source": "toss_holdings",
                    "sync_checked_at": checked_at,
                    "sync_message": "토스증권 보유자산 응답에서 찾지 못해 기존 수량을 유지했습니다.",
                }
            )
        )
        skipped.append(
            {
                "ticker": ticker,
                "name": holding.name or ticker,
                "quantity": holding.quantity,
                "reason": "toss_missing",
            }
        )

    remote_candidates = [
        {
            "ticker": ticker,
            "name": item.get("name") or ticker,
            "quantity": item.get("quantity"),
            "market_value": item.get("market_value"),
            "currency": item.get("currency"),
            "reason": "untracked_remote",
        }
        for ticker, item in balance_by_ticker.items()
        if ticker not in matched_tickers
    ]
    imported_remote: list[dict] = []
    untracked_remote: list[dict] = []
    if import_untracked:
        for remote in remote_candidates:
            source = balance_by_ticker[remote["ticker"]]
            source_currency = portfolio_currency_for_ticker(
                remote["ticker"],
                source.get("currency"),
            )
            valuation_update: dict[str, float | None]
            applied_fx_rate: float | None = None
            if source_currency == "USD":
                applied_fx_rate = fallback_usd_fx_rate
                if applied_fx_rate is None:
                    unavailable = {**remote, "reason": "toss_fx_unavailable"}
                    untracked_remote.append(unavailable)
                    skipped.append(unavailable)
                    continue
                valuation_update = _convert_toss_usd_valuation(
                    source,
                    fx_rate=applied_fx_rate,
                )
                applied_fx_rates[remote["ticker"]] = round(applied_fx_rate, 4)
            else:
                valuation_update = {
                    "market_value": source.get("market_value"),
                    "cost_basis": source.get("cost_basis"),
                    "unrealized_gain": source.get("unrealized_gain"),
                }
            synced_holdings.append(
                PortfolioHolding(
                    ticker=remote["ticker"],
                    name=source.get("name") or remote["ticker"],
                    quantity=source.get("quantity"),
                    average_cost=source.get("average_cost"),
                    current_price=source.get("current_price"),
                    **valuation_update,
                    unrealized_return=source.get("unrealized_return"),
                    currency=source_currency,
                    price_source="toss_holdings",
                    price_refresh_status="account_synced",
                    price_checked_at=checked_at,
                    sync_status="account_synced",
                    sync_source="toss_holdings",
                    sync_checked_at=checked_at,
                    sync_message=(
                        "토스증권 보유자산에서 확인되어 지정 포트폴리오에 자동 편입했습니다. "
                        f"USD 평가는 저장 포트폴리오 기준환율 {applied_fx_rate:,.2f}원을 적용했습니다."
                        if applied_fx_rate is not None
                        else "토스증권 보유자산에서 확인되어 지정 포트폴리오에 자동 편입했습니다."
                    ),
                )
            )
            imported_remote.append(
                {
                    **remote,
                    "reason": "imported_remote",
                    "valuation_fx_rate": applied_fx_rate,
                }
            )
            changes.append(
                {
                    "ticker": remote["ticker"],
                    "name": source.get("name") or remote["ticker"],
                    "old_quantity": None,
                    "new_quantity": source.get("quantity"),
                    "old_average_cost": None,
                    "new_average_cost": source.get("average_cost"),
                    "old_market_value": None,
                    "new_market_value": valuation_update.get("market_value"),
                    "valuation_fx_rate": applied_fx_rate,
                    "changed": True,
                    "reason": "imported_remote",
                }
            )
    else:
        untracked_remote = remote_candidates
    synced_portfolio = portfolio.model_copy(
        update={
            "holdings": synced_holdings,
            "updated_at": checked_at,
            "holding_count": len(synced_holdings),
        }
    )
    return synced_portfolio, {
        "status": "warning" if any(
            item.get("reason") == "toss_fx_unavailable" for item in skipped
        ) else "success",
        "broker": "TOSS",
        "scope": "kr_us_holdings",
        "api_id": balance.get("api_path", "/api/v1/holdings"),
        "account_seq": balance.get("account_seq"),
        "checked_at": checked_at,
        "updated_count": sum(1 for item in changes if item.get("changed")),
        "confirmed_count": sum(1 for item in changes if not item.get("changed")),
        "imported_count": len(imported_remote),
        "skipped_count": len(skipped),
        "changes": changes,
        "skipped": skipped,
        "imported_remote": imported_remote,
        "untracked_remote": untracked_remote,
        "valuation_currency": "KRW",
        "applied_fx_rates": applied_fx_rates,
        "message": (
            "토스증권 보유자산을 지정 포트폴리오에 반영하고 다른 증권사·수동 보유 종목은 보존했습니다."
            if import_untracked and preserve_non_toss_holdings
            else "토스증권 보유자산과 매칭된 종목만 갱신했습니다. 미매칭 기존 종목은 보존하고 원격 신규 종목은 자동 추가하지 않았습니다."
        ),
    }


def portfolio_sync_status_summary(
    portfolio: SavedPortfolio | None,
    history: list[dict],
) -> dict:
    """Summarize current holding sync states and latest apply history."""
    holdings = portfolio.holdings if portfolio else []
    counts = {
        "account_synced": 0,
        "manual_or_overseas_protected": 0,
        "kiwoom_domestic_missing": 0,
        "kiwoom_not_configured": 0,
        "toss_missing": 0,
        "toss_not_configured": 0,
        "toss_unavailable": 0,
        "unknown": 0,
    }
    latest_checked_at = ""
    for holding in holdings:
        status = holding.sync_status or "unknown"
        counts[status] = counts.get(status, 0) + 1
        if holding.sync_checked_at and holding.sync_checked_at > latest_checked_at:
            latest_checked_at = holding.sync_checked_at
    last_apply = next((item for item in history if item.get("mode") == "apply"), history[0] if history else None)
    return {
        "holding_count": len(holdings),
        "counts": counts,
        "latest_checked_at": latest_checked_at or None,
        "last_history_created_at": last_apply.get("created_at") if last_apply else None,
        "last_history_checked_at": last_apply.get("checked_at") if last_apply else None,
        "last_history_message": last_apply.get("message") if last_apply else None,
    }
