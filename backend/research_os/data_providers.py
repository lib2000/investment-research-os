import re

import httpx

from research_os import provider_usage
from research_os import data_provider_status_messages
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings
from research_os.data_provider_core import (
    CompositeFinancialDataProvider,
    CompositeMarketDataProvider,
    CompositeSupplementalDataProvider,
    DataProviderStatus,
    EmptyFinancialDataProvider,
    EmptyMarketDataProvider,
    EmptySupplementalDataProvider,
    FinancialDataProvider,
    MarketDataProvider,
    MockFinancialDataProvider,
    MockMarketDataProvider,
    SupplementalDataProvider,
)
from research_os.data_provider_status import (
    build_dart_financial_status,
    build_financial_datasets_status,
    build_finnhub_market_status,
    build_kis_market_status,
    build_supplemental_provider_statuses,
    build_tiingo_market_status,
)
from research_os.data_provider_utils import (
    _first_value,
    _is_configured_secret,
    _parse_float_value,
    _provider_now,
    _safe_provider_error,
)
from research_os.finnhub_data_provider import (
    FinnhubClient,
    FinnhubMarketDataProvider,
    FinnhubSupplementalDataProvider,
)
from research_os.financial_datasets_data_provider import (
    FinancialDatasetsClient,
    FinancialDatasetsFinancialDataProvider,
)
from research_os.fmp_data_provider import (
    FmpClient,
    FmpFinancialDataProvider,
    FmpMarketDataProvider,
)
from research_os.customs_data_provider import (
    CUSTOMS_DEFAULT_COUNTRY_CODES,
    KoreaCustomsTradeClient,
    fetch_customs_total_trend_status,
    fetch_customs_trade_rows,
    is_valid_customs_trade_row,
    normalize_customs_trade_row,
)
from research_os.nps_data_provider import (
    NpsOdcloudClient,
    fetch_nps_institutional_context,
    fetch_nps_institutional_signal,
    nps_signal_to_data_points,
)
from research_os.kis_data_provider import (
    KIS_US_EXCHANGE_BY_TICKER,
    KisClient,
    KisOverseasMarketDataProvider,
    _kis_candidate_exchange_codes,
    _looks_like_korean_security_code,
)
from research_os.opendart_data_provider import (
    OpenDartClient,
    OpenDartFinancialDataProvider,
)
from research_os.web_search_data_provider import (
    BraveSupplementalDataProvider,
    TavilySupplementalDataProvider,
)


def _resolve_backend_relative_path(path_value: str):
    return provider_usage.resolve_backend_relative_path(path_value)


def _consume_external_provider_quota(
    *,
    provider_name: str,
    usage_file: str,
    daily_limit: int,
    monthly_limit: int,
    units: int = 1,
    unit_label: str = "requests",
) -> tuple[bool, str]:
    return provider_usage.consume_external_provider_quota(
        provider_name=provider_name,
        usage_file=usage_file,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        units=units,
        unit_label=unit_label,
    )


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


class AnalysisDataProvider:
    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        financial_data_provider: FinancialDataProvider,
        mode: str,
        supplemental_data_provider: SupplementalDataProvider | None = None,
        fallback_active: bool = False,
        configured: bool = True,
        financial_configured: bool | None = None,
        financial_status_message: str | None = None,
        extra_statuses: list[DataProviderStatus] | None = None,
    ) -> None:
        self.market_data_provider = market_data_provider
        self.financial_data_provider = financial_data_provider
        self.supplemental_data_provider = supplemental_data_provider or EmptySupplementalDataProvider()
        self.mode = mode
        self.fallback_active = fallback_active
        self.configured = configured
        self.financial_configured = configured if financial_configured is None else financial_configured
        self.financial_status_message = financial_status_message
        self.extra_statuses = extra_statuses or []

    def fetch_analysis_context(self, ticker: str) -> list[InjectedDataPoint]:
        return [
            *self.market_data_provider.fetch_market_snapshot(ticker),
            *self.financial_data_provider.fetch_financial_snapshot(ticker),
            *self.supplemental_data_provider.fetch_supplemental_snapshot(ticker),
        ]

    def status(self) -> list[dict]:
        return [
            DataProviderStatus(
                name="market_data",
                mode=self.mode,
                ready=self.configured,
                message=_provider_status_message(self.mode, self.configured),
                fallback_active=self.fallback_active,
            ).to_dict(),
            DataProviderStatus(
                name="financial_data",
                mode=self.mode,
                ready=self.financial_configured,
                message=self.financial_status_message
                or _provider_status_message(self.mode, self.financial_configured),
                fallback_active=self.fallback_active,
            ).to_dict(),
            *[status.to_dict() for status in self.extra_statuses],
        ]


def get_analysis_data_provider(settings: Settings) -> AnalysisDataProvider:
    kis_client = KisClient(settings)
    dart_client = OpenDartClient(settings)
    financial_datasets_client = FinancialDatasetsClient(settings)
    finnhub_client = FinnhubClient(settings)
    tiingo_market = TiingoMarketDataProvider(settings)
    alpha_supplemental = AlphaVantageSupplementalDataProvider(settings)
    tavily_supplemental = TavilySupplementalDataProvider(settings)
    brave_supplemental = BraveSupplementalDataProvider(settings)
    nps_client = NpsOdcloudClient(settings)
    customs_client = KoreaCustomsTradeClient(settings)

    supplemental_provider = CompositeSupplementalDataProvider(
        [
            FinnhubSupplementalDataProvider(finnhub_client),
            alpha_supplemental,
            tavily_supplemental,
            brave_supplemental,
        ]
    )
    supplemental_statuses = build_supplemental_provider_statuses(
        settings,
        finnhub_client=finnhub_client,
        alpha_supplemental=alpha_supplemental,
        tavily_supplemental=tavily_supplemental,
        brave_supplemental=brave_supplemental,
        nps_client=nps_client,
        customs_client=customs_client,
    )

    mode = settings.data_provider_mode.lower()
    if mode == "fmp":
        client = FmpClient(settings)
        fallback_market = (
            KisOverseasMarketDataProvider(kis_client)
            if kis_client.is_configured
            else EmptyMarketDataProvider()
        )
        fallback_financial = CompositeFinancialDataProvider(
            [
                OpenDartFinancialDataProvider(dart_client),
                FinancialDatasetsFinancialDataProvider(financial_datasets_client),
            ]
        )
        return AnalysisDataProvider(
            market_data_provider=FmpMarketDataProvider(client, fallback_market),
            financial_data_provider=FmpFinancialDataProvider(client, fallback_financial),
            mode=mode,
            supplemental_data_provider=supplemental_provider,
            fallback_active=not client.is_configured,
            configured=client.is_configured,
            extra_statuses=[
                build_kis_market_status(kis_client),
                build_dart_financial_status(dart_client),
                build_financial_datasets_status(financial_datasets_client),
                *supplemental_statuses,
            ],
        )

    if mode == "kis":
        return AnalysisDataProvider(
            market_data_provider=CompositeMarketDataProvider(
                [
                    KisOverseasMarketDataProvider(kis_client)
                    if kis_client.is_configured
                    else EmptyMarketDataProvider(),
                    FinnhubMarketDataProvider(finnhub_client),
                    tiingo_market,
                ]
            ),
            financial_data_provider=CompositeFinancialDataProvider(
                [
                    OpenDartFinancialDataProvider(dart_client),
                    FinancialDatasetsFinancialDataProvider(financial_datasets_client),
                ]
            ),
            mode=mode,
            supplemental_data_provider=supplemental_provider,
            fallback_active=False,
            configured=kis_client.is_configured,
            financial_configured=dart_client.is_configured or financial_datasets_client.is_configured,
            financial_status_message=(
                "KIS 현재가를 기본으로 사용하고, 한국 종목은 OpenDART, 미국 종목은 "
                "Financial Datasets로 재무 데이터를 보강합니다. 설정되지 않은 provider는 건너뜁니다."
            ),
            extra_statuses=[
                build_kis_market_status(kis_client),
                build_dart_financial_status(dart_client),
                build_financial_datasets_status(financial_datasets_client),
                build_finnhub_market_status(finnhub_client),
                build_tiingo_market_status(tiingo_market),
                *supplemental_statuses,
            ],
        )

    return AnalysisDataProvider(
        market_data_provider=MockMarketDataProvider(),
        financial_data_provider=MockFinancialDataProvider(),
        mode=mode,
    )


def _provider_status_message(mode: str, configured: bool) -> str:
    return data_provider_status_messages.provider_status_message(mode, configured)
