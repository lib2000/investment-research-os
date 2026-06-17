"""Financial Modeling Prep data provider helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from research_os.data_provider_core import FinancialDataProvider, MarketDataProvider
from research_os.data_provider_utils import _format_ratio, _safe_provider_error
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class FmpClient:
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.fmp_api_key.strip()
        if self.api_key.lower().startswith("apikey="):
            self.api_key = self.api_key.split("=", 1)[1].strip()
        self.base_url = settings.fmp_base_url.rstrip("/")
        self.timeout_seconds = settings.fmp_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "********")

    def get(self, endpoint: str, params: dict | None = None) -> list[dict] | dict:
        if not self.is_configured:
            raise RuntimeError("FMP_API_KEY is not configured.")

        response = httpx.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params={**(params or {}), "apikey": self.api_key},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("Error Message"):
            raise RuntimeError(payload["Error Message"])
        return payload


class FmpMarketDataProvider(MarketDataProvider):
    def __init__(self, client: FmpClient, fallback: MarketDataProvider) -> None:
        self.client = client
        self.fallback = fallback

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        try:
            quote_payload = self.client.get("quote", {"symbol": ticker})
            if not isinstance(quote_payload, list) or not quote_payload:
                raise RuntimeError("FMP quote response was empty.")

            quote = quote_payload[0]
            as_of = datetime.now(timezone.utc).isoformat()
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="last_price",
                    value=str(quote.get("price", "n/a")),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/quote?symbol={ticker}",
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="market_cap",
                    value=str(quote.get("marketCap", "n/a")),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/quote?symbol={ticker}",
                    confidence=0.85,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="volume",
                    value=str(quote.get("volume", "n/a")),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/quote?symbol={ticker}",
                    confidence=0.85,
                ),
            ]
        except Exception as exc:
            fallback_data = self.fallback.fetch_market_snapshot(ticker)
            if fallback_data:
                return [
                    *fallback_data,
                    InjectedDataPoint(
                        source_type=DataSourceType.OTHER,
                        label="market_data_provider_warning",
                        value=(
                            "FMP 시장 데이터 호출 실패 후 대체 프로바이더를 사용했습니다. "
                            f"사유: {_safe_provider_error(exc)}"
                        ),
                        as_of=datetime.now(timezone.utc).isoformat(),
                        confidence=0.5,
                    ),
                ]
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="market_data_provider_warning",
                    value=(
                        "FMP 시장 데이터 호출 실패로 가격/시총/거래량 자동 주입을 중단했습니다. "
                        f"합성 Mock 숫자는 사용하지 않습니다. 사유: {_safe_provider_error(exc)}"
                    ),
                    as_of=datetime.now(timezone.utc).isoformat(),
                    confidence=0.5,
                ),
            ]


class FmpFinancialDataProvider(FinancialDataProvider):
    def __init__(self, client: FmpClient, fallback: FinancialDataProvider) -> None:
        self.client = client
        self.fallback = fallback

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        try:
            income_payload = self.client.get(
                "income-statement", {"symbol": ticker, "limit": 1}
            )
            ratios_payload = self.client.get("ratios", {"symbol": ticker, "limit": 1})
            if not isinstance(income_payload, list) or not income_payload:
                raise RuntimeError("FMP income statement response was empty.")

            income = income_payload[0]
            ratios = ratios_payload[0] if isinstance(ratios_payload, list) and ratios_payload else {}
            as_of = income.get("date") or datetime.now(timezone.utc).isoformat()
            revenue = income.get("revenue")
            gross_profit = income.get("grossProfit")
            operating_income = income.get("operatingIncome")
            net_income = income.get("netIncome")

            data = [
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="revenue",
                    value=str(revenue or "n/a"),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/income-statement?symbol={ticker}",
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="gross_margin",
                    value=_format_ratio(gross_profit, revenue),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/income-statement?symbol={ticker}",
                    confidence=0.85,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="operating_margin",
                    value=_format_ratio(operating_income, revenue),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/income-statement?symbol={ticker}",
                    confidence=0.85,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="net_margin",
                    value=_format_ratio(net_income, revenue),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/income-statement?symbol={ticker}",
                    confidence=0.85,
                ),
            ]

            pe_ratio = ratios.get("priceEarningsRatio") or ratios.get("peRatio")
            if pe_ratio is not None:
                data.append(
                    InjectedDataPoint(
                        source_type=DataSourceType.FINANCIAL_DATA,
                        label="pe_ratio",
                        value=str(pe_ratio),
                        as_of=as_of,
                        source_url=f"{self.client.base_url}/ratios?symbol={ticker}",
                        confidence=0.8,
                    )
                )

            return data
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="financial_data_provider_warning",
                    value=(
                        "FMP 재무 데이터 호출 실패로 재무 수치 자동 주입을 중단했습니다. "
                        f"합성 Mock 숫자는 사용하지 않습니다. 사유: {_safe_provider_error(exc)}"
                    ),
                    as_of=datetime.now(timezone.utc).isoformat(),
                    confidence=0.5,
                ),
            ]
