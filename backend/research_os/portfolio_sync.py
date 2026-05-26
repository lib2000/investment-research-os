"""Portfolio account-sync calculation helpers."""

from __future__ import annotations

from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.portfolio_import import (
    is_domestic_sync_like_ticker,
    normalize_import_ticker,
    portfolio_currency_for_ticker,
)


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
