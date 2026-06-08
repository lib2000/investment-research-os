"""Small helpers for saved portfolio storage."""

from __future__ import annotations

from re import sub
from typing import Any

from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.settings import Settings
from research_os.state_store import portfolio_store_path, read_json_store


def portfolio_store_key(portfolio_name: str) -> str:
    """Return a stable JSON-store key for a user-visible portfolio name."""
    normalized = sub(r"[^\w-]+", "-", portfolio_name.strip().upper()).strip("-_")
    return normalized or "DEFAULT"


def portfolio_name_sort_key(portfolio: SavedPortfolio) -> str:
    """Sort saved portfolios by Korean/user-visible name without touching data."""
    return portfolio.portfolio_name.casefold()


def read_portfolio_store(settings: Settings) -> dict[str, Any]:
    """Read the saved portfolio JSON store with a stable default shape."""
    return read_json_store(portfolio_store_path(settings), {"portfolios": {}})


def infer_holding_fx_rate(holding: PortfolioHolding) -> float:
    """Infer the KRW conversion rate from a saved USD holding when possible."""
    if holding.currency.upper() != "USD":
        return 1.0
    if (
        holding.cost_basis
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
    ):
        inferred = holding.cost_basis / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    if (
        holding.market_value
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
        and holding.current_price is None
    ):
        inferred = holding.market_value / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    return 1.0
