"""Financial Datasets API provider integration."""

from __future__ import annotations

import httpx

from research_os.data_provider_core import FinancialDataProvider
from research_os.data_provider_utils import _is_configured_secret, _provider_now, _safe_provider_error
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class FinancialDatasetsClient:
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.financial_datasets_api_key.strip()
        self.base_url = settings.financial_datasets_base_url.rstrip("/")
        self.timeout_seconds = settings.financial_datasets_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def get(self, endpoint: str, params: dict) -> dict:
        if not self.is_configured:
            raise RuntimeError("FINANCIAL_DATASETS_API_KEY is not configured.")
        response = httpx.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params=params,
            headers={"X-API-KEY": self.api_key},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


class FinancialDatasetsFinancialDataProvider(FinancialDataProvider):
    def __init__(self, client: FinancialDatasetsClient) -> None:
        self.client = client

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker):
            return []
        if not self.client.is_configured:
            return []
        try:
            payload = self.client.get(
                "financials",
                {"ticker": ticker.upper(), "period": "quarterly", "limit": 1},
            )
            financials = payload.get("financials") or {}
            income = (financials.get("income_statements") or [{}])[0]
            balance = (financials.get("balance_sheets") or [{}])[0]
            cash_flow = (financials.get("cash_flow_statements") or [{}])[0]
            as_of = income.get("report_period") or _provider_now()
            source_url = f"{self.client.base_url}/financials"
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="financial_datasets_revenue",
                    value=str(income.get("revenue") or "n/a"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="financial_datasets_gross_profit",
                    value=str(income.get("gross_profit") or "n/a"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="financial_datasets_operating_income",
                    value=str(income.get("operating_income") or "n/a"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="financial_datasets_cash_and_equivalents",
                    value=str(balance.get("cash_and_equivalents") or "n/a"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.84,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="financial_datasets_free_cash_flow",
                    value=str(cash_flow.get("free_cash_flow") or cash_flow.get("net_cash_flow_from_operations") or "n/a"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.84,
                ),
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="financial_datasets_provider_warning",
                    value=f"Financial Datasets 재무 데이터 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]