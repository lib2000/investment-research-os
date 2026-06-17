"""Finnhub market and supplemental data provider integration."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import httpx

from research_os.data_provider_core import MarketDataProvider, SupplementalDataProvider
from research_os.data_provider_utils import _is_configured_secret, _provider_now, _safe_provider_error
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class FinnhubClient:
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.finnhub_api_key.strip()
        self.base_url = settings.finnhub_base_url.rstrip("/")
        self.timeout_seconds = settings.finnhub_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def get(self, endpoint: str, params: dict | None = None) -> dict | list:
        if not self.is_configured:
            raise RuntimeError("FINNHUB_API_KEY is not configured.")
        response = httpx.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params={**(params or {}), "token": self.api_key},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


class FinnhubMarketDataProvider(MarketDataProvider):
    def __init__(self, client: FinnhubClient) -> None:
        self.client = client

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.client.is_configured:
            return []
        try:
            quote = self.client.get("quote", {"symbol": ticker.upper()})
            if not isinstance(quote, dict) or not quote.get("c"):
                return []
            as_of = _provider_now()
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="finnhub_last_price",
                    value=str(quote.get("c")),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/quote",
                    confidence=0.82,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="finnhub_previous_close",
                    value=str(quote.get("pc") or "n/a"),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/quote",
                    confidence=0.78,
                ),
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="finnhub_market_provider_warning",
                    value=f"Finnhub 현재가 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]


class FinnhubSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, client: FinnhubClient) -> None:
        self.client = client

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.client.is_configured:
            return []
        data: list[InjectedDataPoint] = []
        today = datetime.now(timezone.utc).date()
        try:
            earnings = self.client.get(
                "calendar/earnings",
                {
                    "symbol": ticker.upper(),
                    "from": (today.replace(day=1)).isoformat(),
                    "to": (today.replace(year=today.year + 1)).isoformat(),
                },
            )
            events = earnings.get("earningsCalendar") if isinstance(earnings, dict) else []
            if events:
                event = events[0]
                data.append(
                    InjectedDataPoint(
                        source_type=DataSourceType.EARNINGS_RELEASE,
                        label="finnhub_next_earnings_event",
                        value=json.dumps(event, ensure_ascii=False),
                        as_of=str(event.get("date") or today),
                        source_url=f"{self.client.base_url}/calendar/earnings",
                        confidence=0.8,
                    )
                )
        except Exception as exc:
            data.append(
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="finnhub_earnings_provider_warning",
                    value=f"Finnhub 실적 캘린더 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            )
        try:
            news = self.client.get(
                "company-news",
                {
                    "symbol": ticker.upper(),
                    "from": (today.replace(day=1)).isoformat(),
                    "to": today.isoformat(),
                },
            )
            if isinstance(news, list) and news:
                headlines = [
                    f"{item.get('datetime')}: {item.get('headline')}"
                    for item in news[:3]
                    if item.get("headline")
                ]
                if headlines:
                    data.append(
                        InjectedDataPoint(
                            source_type=DataSourceType.NEWS,
                            label="finnhub_recent_news",
                            value=" | ".join(headlines),
                            as_of=today.isoformat(),
                            source_url=f"{self.client.base_url}/company-news",
                            confidence=0.72,
                        )
                    )
        except Exception as exc:
            data.append(
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="finnhub_news_provider_warning",
                    value=f"Finnhub 뉴스 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            )
        return data