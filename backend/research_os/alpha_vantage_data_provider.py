"""Alpha Vantage supplemental data provider."""

from __future__ import annotations

import httpx

from research_os.data_provider_core import SupplementalDataProvider
from research_os.data_provider_utils import _is_configured_secret, _provider_now, _safe_provider_error
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class AlphaVantageSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.alpha_vantage_api_key.strip()
        self.base_url = settings.alpha_vantage_base_url
        self.timeout_seconds = settings.alpha_vantage_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        try:
            response = httpx.get(
                self.base_url,
                params={"function": "OVERVIEW", "symbol": ticker.upper(), "apikey": self.api_key},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            overview = response.json()
            if not isinstance(overview, dict) or not overview.get("Symbol"):
                return []
            as_of = _provider_now()
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="alpha_vantage_company_overview",
                    value=(
                        f"Sector={overview.get('Sector')}; Industry={overview.get('Industry')}; "
                        f"MarketCap={overview.get('MarketCapitalization')}; PERatio={overview.get('PERatio')}; "
                        f"ProfitMargin={overview.get('ProfitMargin')}"
                    ),
                    as_of=as_of,
                    source_url=self.base_url,
                    confidence=0.72,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="alpha_vantage_provider_warning",
                    value=f"Alpha Vantage Overview 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
