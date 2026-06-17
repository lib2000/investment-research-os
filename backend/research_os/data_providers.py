from datetime import datetime, timezone, timedelta
import json
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
from research_os.data_provider_utils import (
    _first_value,
    _format_ratio,
    _is_configured_secret,
    _parse_float_value,
    _provider_now,
    _safe_provider_error,
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
    supplemental_statuses = [
        DataProviderStatus(
            name="finnhub_events_news",
            mode="finnhub",
            ready=finnhub_client.is_configured,
            message=_external_provider_status_message(
                "Finnhub 실적 캘린더/회사 뉴스", finnhub_client.is_configured
            ),
        ),
        DataProviderStatus(
            name="alpha_vantage_overview",
            mode="alpha_vantage",
            ready=alpha_supplemental.is_configured,
            message=_external_provider_status_message(
                "Alpha Vantage 회사 개요", alpha_supplemental.is_configured
            ),
        ),
        DataProviderStatus(
            name="tavily_finance_search",
            mode="tavily",
            ready=tavily_supplemental.is_configured,
            message=(
                "Tavily 금융 검색/RAG 후보 프로바이더가 설정되었습니다. "
                f"무료 한도 보호: 일 {settings.tavily_daily_credit_limit} credits, "
                f"월 {settings.tavily_monthly_credit_limit} credits."
                if tavily_supplemental.is_configured
                else "Tavily 금융 검색/RAG 후보 API 키가 없어 해당 보강 데이터를 건너뜁니다."
            ),
        ),
        DataProviderStatus(
            name="brave_search",
            mode="brave",
            ready=brave_supplemental.is_configured,
            message=(
                "Brave 웹 검색/RAG 후보 프로바이더가 설정되었습니다. "
                f"무료 한도 보호: 일 {settings.brave_daily_request_limit} requests, "
                f"월 {settings.brave_monthly_request_limit} requests."
                if brave_supplemental.is_configured
                else "Brave 웹 검색/RAG 후보 API 키가 없어 해당 보강 데이터를 건너뜁니다."
            ),
        ),
        DataProviderStatus(
            name="naver_finance_korea_indices",
            mode="naver_finance",
            ready=settings.naver_finance_enabled,
            message=(
                "네이버 증권 KOSPI/KOSDAQ 보조 수집이 활성화되었습니다. "
                "공식 API가 아니므로 실패 시 분석을 중단하지 않고 경고만 표시합니다."
                if settings.naver_finance_enabled
                else "NAVER_FINANCE_ENABLED=false로 네이버 증권 보조 수집을 비활성화했습니다."
            ),
        ),
        DataProviderStatus(
            name="nps_odcloud_institutional_flow",
            mode="odcloud",
            ready=nps_client.is_configured,
            message=nps_client.status_message(),
        ),
        DataProviderStatus(
            name="korea_customs_trade",
            mode="data_go_kr",
            ready=customs_client.is_configured,
            message=customs_client.status_message(),
        ),
        DataProviderStatus(
            name="korea_customs_trade_total_trend",
            mode="data_go_kr",
            ready=customs_client.is_total_trend_configured,
            message=customs_client.total_trend_status_message(),
        ),
    ]

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
                DataProviderStatus(
                    name="kis_overseas_market_data",
                    mode="kis",
                    ready=kis_client.is_configured,
                    message=_kis_status_message(kis_client),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="dart_official_filing",
                    mode="dart",
                    ready=dart_client.is_configured,
                    message=_external_provider_status_message(
                        "OpenDART 한국 공시/재무", dart_client.is_configured
                    ),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="financial_datasets_financials",
                    mode="financial_datasets",
                    ready=financial_datasets_client.is_configured,
                    message=_external_provider_status_message(
                        "Financial Datasets 미국 재무제표", financial_datasets_client.is_configured
                    ),
                    fallback_active=False,
                ),
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
                DataProviderStatus(
                    name="kis_overseas_market_data",
                    mode="kis",
                    ready=kis_client.is_configured,
                    message=_kis_status_message(kis_client),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="dart_official_filing",
                    mode="dart",
                    ready=dart_client.is_configured,
                    message=_external_provider_status_message(
                        "OpenDART 한국 공시/재무", dart_client.is_configured
                    ),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="financial_datasets_financials",
                    mode="financial_datasets",
                    ready=financial_datasets_client.is_configured,
                    message=_external_provider_status_message(
                        "Financial Datasets 미국 재무제표", financial_datasets_client.is_configured
                    ),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="finnhub_market_data",
                    mode="finnhub",
                    ready=finnhub_client.is_configured,
                    message=_external_provider_status_message(
                        "Finnhub 미국 현재가/전일종가 보조", finnhub_client.is_configured
                    ),
                    fallback_active=False,
                ),
                DataProviderStatus(
                    name="tiingo_market_data",
                    mode="tiingo",
                    ready=tiingo_market.is_configured,
                    message=_external_provider_status_message(
                        "Tiingo 미국 종가 보조", tiingo_market.is_configured
                    ),
                    fallback_active=False,
                ),
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


def _external_provider_status_message(label: str, configured: bool) -> str:
    return data_provider_status_messages.external_provider_status_message(label, configured)


def _kis_status_message(client: KisClient) -> str:
    return data_provider_status_messages.kis_status_message(client)
