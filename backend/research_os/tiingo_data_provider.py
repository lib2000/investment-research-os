"""Tiingo market data provider."""

from __future__ import annotations

import httpx

from research_os.data_provider_core import MarketDataProvider
from research_os.data_provider_utils import _is_configured_secret, _provider_now, _safe_provider_error
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class TiingoMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.tiingo_api_key.strip()
        self.base_url = settings.tiingo_base_url.rstrip("/")
        self.timeout_seconds = settings.tiingo_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        try:
            response = httpx.get(
                f"{self.base_url}/tiingo/daily/{ticker.upper()}/prices",
                params={"token": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                return []
            quote = payload[0]
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="tiingo_last_price",
                    value=str(quote.get("close") or "n/a"),
                    as_of=str(quote.get("date") or _provider_now()),
                    source_url=f"{self.base_url}/tiingo/daily/{ticker.upper()}/prices",
                    confidence=0.78,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="tiingo_market_provider_warning",
                    value=f"Tiingo 가격 데이터 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
