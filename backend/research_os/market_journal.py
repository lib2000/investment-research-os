"""Helpers for market-close journal source metadata."""

from __future__ import annotations


NAVER_MARKET_CLOSE_SOURCE_ORIGIN = "naver_research_auto"
NAVER_MARKET_CLOSE_SOURCE_PROVIDER = "naver_finance_research"


def naver_market_close_source_metadata(title: str | None = None) -> dict[str, str]:
    """Return source metadata used when Naver market-close reports feed the journal."""
    return {
        "source_origin": NAVER_MARKET_CLOSE_SOURCE_ORIGIN,
        "source_provider": NAVER_MARKET_CLOSE_SOURCE_PROVIDER,
        "source_title": str(title or ""),
    }
