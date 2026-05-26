"""Small helpers for saved portfolio storage."""

from __future__ import annotations

from re import sub

from research_os.models import SavedPortfolio


def portfolio_store_key(portfolio_name: str) -> str:
    """Return a stable JSON-store key for a user-visible portfolio name."""
    normalized = sub(r"[^\w-]+", "-", portfolio_name.strip().upper()).strip("-_")
    return normalized or "DEFAULT"


def portfolio_name_sort_key(portfolio: SavedPortfolio) -> str:
    """Sort saved portfolios by Korean/user-visible name without touching data."""
    return portfolio.portfolio_name.casefold()
