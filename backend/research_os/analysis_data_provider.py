"""Analysis data provider composition."""

from __future__ import annotations

import research_os.data_provider_status_messages as data_provider_status_messages
from research_os.alpha_vantage_data_provider import AlphaVantageSupplementalDataProvider
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
from research_os.financial_datasets_data_provider import (
    FinancialDatasetsClient,
    FinancialDatasetsFinancialDataProvider,
)
from research_os.finnhub_data_provider import (
    FinnhubClient,
    FinnhubMarketDataProvider,
    FinnhubSupplementalDataProvider,
)
from research_os.fmp_data_provider import (
    FmpClient,
    FmpFinancialDataProvider,
    FmpMarketDataProvider,
)
from research_os.customs_data_provider import KoreaCustomsTradeClient
from research_os.kis_data_provider import KisClient, KisOverseasMarketDataProvider
from research_os.models import InjectedDataPoint
from research_os.nps_data_provider import NpsOdcloudClient
from research_os.opendart_data_provider import OpenDartClient, OpenDartFinancialDataProvider
from research_os.settings import Settings
from research_os.tiingo_data_provider import TiingoMarketDataProvider
from research_os.web_search_data_provider import (
    BraveSupplementalDataProvider,
    TavilySupplementalDataProvider,
)


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

    def fetch_primary_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        """Return the configured primary quote source without probing fallbacks.

        Full research context intentionally collects every configured provider.
        Portfolio close-price refreshes only need one authoritative quote, so
        probing supplemental market sources adds latency without changing the
        price selected by the caller.
        """
        providers = getattr(self.market_data_provider, "providers", None)
        if isinstance(providers, list) and providers:
            return providers[0].fetch_market_snapshot(ticker)
        return self.market_data_provider.fetch_market_snapshot(ticker)

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
