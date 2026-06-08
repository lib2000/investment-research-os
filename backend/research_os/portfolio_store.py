"""Small helpers for saved portfolio storage."""

from __future__ import annotations

from re import sub
from typing import Any

from research_os.models import SavedPortfolio
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
