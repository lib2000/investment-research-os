from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import re
import threading
import xml.etree.ElementTree as ET
import zipfile

import httpx

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

_PROVIDER_USAGE_LOCK = threading.Lock()


def _resolve_backend_relative_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[1] / path).resolve()


def _consume_external_provider_quota(
    *,
    provider_name: str,
    usage_file: str,
    daily_limit: int,
    monthly_limit: int,
    units: int = 1,
    unit_label: str = "requests",
) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    today_key = now.date().isoformat()
    month_key = f"{now.year:04d}-{now.month:02d}"
    path = _resolve_backend_relative_path(usage_file)
    with _PROVIDER_USAGE_LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        usage = payload.get(provider_name)
        if not isinstance(usage, dict):
            usage = {}
        if usage.get("day") != today_key:
            usage["day"] = today_key
            usage["day_count"] = 0
        if usage.get("month") != month_key:
            usage["month"] = month_key
            usage["month_count"] = 0
        day_count = int(usage.get("day_count") or 0)
        month_count = int(usage.get("month_count") or 0)
        if daily_limit >= 0 and day_count + units > daily_limit:
            return (
                False,
                f"{provider_name} 무료 한도 보호: 오늘 {day_count}/{daily_limit} {unit_label}를 이미 사용해 추가 호출을 건너뜁니다.",
            )
        if monthly_limit >= 0 and month_count + units > monthly_limit:
            return (
                False,
                f"{provider_name} 무료 한도 보호: 이번 달 {month_count}/{monthly_limit} {unit_label}를 이미 사용해 추가 호출을 건너뜁니다.",
            )
        usage["day_count"] = day_count + units
        usage["month_count"] = month_count + units
        usage["last_used_at"] = now.isoformat()
        payload[provider_name] = usage
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return (
        True,
        f"{provider_name} 사용량 기록: 오늘 {day_count + units}/{daily_limit}, 이번 달 {month_count + units}/{monthly_limit} {unit_label}.",
    )


class OpenDartClient:
    REPORT_CODE_BY_PRIORITY = ["11011", "11014", "11012", "11013"]

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.dart_api_key.strip()
        self.base_url = settings.dart_base_url.rstrip("/")
        self.cache_file = self._resolve_path(settings.dart_corp_code_cache_file)
        self.timeout_seconds = settings.dart_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def _resolve_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[1] / path).resolve()

    def _read_cached_corp_codes(self) -> dict:
        if not self.cache_file.exists():
            return {}
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return payload.get("by_stock_code") or {}
        except Exception:
            return {}

    def _write_cached_corp_codes(self, by_stock_code: dict) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(
                    {
                        "updated_at": _provider_now(),
                        "by_stock_code": by_stock_code,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            return

    def _download_corp_codes(self) -> dict:
        response = httpx.get(
            f"{self.base_url}/corpCode.xml",
            params={"crtfc_key": self.api_key},
            timeout=self.timeout_seconds,
            trust_env=False,
        )
        response.raise_for_status()
        by_stock_code: dict[str, dict] = {}
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            xml_name = archive.namelist()[0]
            root = ET.fromstring(archive.read(xml_name))
        for item in root.findall("list"):
            corp_code = (item.findtext("corp_code") or "").strip()
            corp_name = (item.findtext("corp_name") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip()
            if stock_code and corp_code:
                by_stock_code[stock_code] = {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                }
        self._write_cached_corp_codes(by_stock_code)
        return by_stock_code

    def find_corp_by_stock_code(self, stock_code: str) -> dict | None:
        normalized = stock_code.strip().upper()
        if not _looks_like_korean_security_code(normalized):
            return None
        by_stock_code = self._read_cached_corp_codes()
        if normalized not in by_stock_code:
            by_stock_code = self._download_corp_codes()
        return by_stock_code.get(normalized)

    def fetch_latest_financials(self, stock_code: str) -> tuple[dict, dict]:
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        current_year = datetime.now(timezone.utc).year
        errors: list[str] = []
        for business_year in [current_year - 1, current_year - 2]:
            for report_code in self.REPORT_CODE_BY_PRIORITY:
                try:
                    response = httpx.get(
                        f"{self.base_url}/fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": self.api_key,
                            "corp_code": corp["corp_code"],
                            "bsns_year": str(business_year),
                            "reprt_code": report_code,
                            "fs_div": "CFS",
                        },
                        timeout=self.timeout_seconds,
                        trust_env=False,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("status") == "000" and payload.get("list"):
                        return corp, {
                            "business_year": business_year,
                            "report_code": report_code,
                            "rows": payload["list"],
                        }
                    errors.append(str(payload.get("message") or payload.get("status")))
                except Exception as exc:
                    errors.append(_safe_provider_error(exc))
        raise RuntimeError("; ".join(error for error in errors if error) or "OpenDART financial lookup failed.")

    def fetch_recent_filings(
        self,
        stock_code: str,
        *,
        lookback_days: int = 14,
        page_count: int = 20,
    ) -> tuple[dict, list[dict]]:
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=max(int(lookback_days), 1))
        response = httpx.get(
            f"{self.base_url}/list.json",
            params={
                "crtfc_key": self.api_key,
                "corp_code": corp["corp_code"],
                "bgn_de": start_date.strftime("%Y%m%d"),
                "end_de": end_date.strftime("%Y%m%d"),
                "page_no": "1",
                "page_count": str(max(1, min(int(page_count), 100))),
                "sort": "date",
                "sort_mth": "desc",
            },
            timeout=self.timeout_seconds,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"000", "013"}:
            raise RuntimeError(str(payload.get("message") or payload.get("status")))
        filings = payload.get("list") or []
        normalized = []
        for item in filings:
            if not isinstance(item, dict):
                continue
            rcept_no = str(item.get("rcept_no") or "").strip()
            if not rcept_no:
                continue
            normalized.append(
                {
                    "corp_code": corp.get("corp_code"),
                    "corp_name": item.get("corp_name") or corp.get("corp_name"),
                    "stock_code": corp.get("stock_code") or stock_code,
                    "rcept_no": rcept_no,
                    "report_name": item.get("report_nm") or "",
                    "filer_name": item.get("flr_nm") or "",
                    "receipt_date": item.get("rcept_dt") or "",
                    "remark": item.get("rm") or "",
                    "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                }
            )
        return corp, normalized


class OpenDartFinancialDataProvider(FinancialDataProvider):
    def __init__(self, client: OpenDartClient) -> None:
        self.client = client

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if not _looks_like_korean_security_code(ticker):
            return []
        if not self.client.is_configured:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="dart_provider_warning",
                    value="DART_API_KEY가 없어 한국 종목 공시/재무 자동 주입을 건너뜁니다.",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            corp, financials = self.client.fetch_latest_financials(ticker)
            rows = financials["rows"]
            as_of = f"{financials['business_year']}:{financials['report_code']}"
            account_map = {
                str(row.get("account_nm") or "").strip(): row for row in rows
            }

            def amount(*names: str) -> str:
                for name in names:
                    row = account_map.get(name)
                    if row:
                        return str(row.get("thstrm_amount") or row.get("frmtrm_amount") or "n/a")
                return "n/a"

            source_url = f"{self.client.base_url}/fnlttSinglAcntAll.json"
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OFFICIAL_FILING,
                    label="dart_company",
                    value=f"{corp.get('corp_name')}({ticker}) corp_code={corp.get('corp_code')}",
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.94,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_revenue",
                    value=amount("매출액", "수익(매출액)", "영업수익"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_operating_income",
                    value=amount("영업이익", "영업손실"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_net_income",
                    value=amount("당기순이익", "당기순손실", "분기순이익", "반기순이익"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_total_assets",
                    value=amount("자산총계"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="dart_provider_warning",
                    value=f"OpenDART 재무 데이터 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]


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


class TavilySupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.tavily_api_key.strip()
        self.base_url = settings.tavily_base_url.rstrip("/")
        self.timeout_seconds = settings.tavily_timeout_seconds
        self.daily_credit_limit = settings.tavily_daily_credit_limit
        self.monthly_credit_limit = settings.tavily_monthly_credit_limit
        self.usage_file = settings.provider_usage_file

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        allowed, quota_message = _consume_external_provider_quota(
            provider_name="tavily",
            usage_file=self.usage_file,
            daily_limit=self.daily_credit_limit,
            monthly_limit=self.monthly_credit_limit,
            units=1,
            unit_label="credits",
        )
        if not allowed:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="tavily_quota_guard",
                    value=quota_message,
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            response = httpx.post(
                f"{self.base_url}/search",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "query": f"{ticker} stock latest earnings guidance valuation investor relations",
                    "topic": "finance",
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            snippets = []
            if payload.get("answer"):
                snippets.append(str(payload["answer"]))
            for item in payload.get("results") or []:
                title = item.get("title") or item.get("url") or ""
                content = item.get("content") or ""
                if title or content:
                    snippets.append(f"{title}: {content}")
            if not snippets:
                return []
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.NEWS,
                    label="tavily_finance_search_context",
                    value=" | ".join(snippets[:4]),
                    as_of=_provider_now(),
                    source_url=f"{self.base_url}/search",
                    confidence=0.68,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="tavily_provider_warning",
                    value=f"Tavily 검색 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]


class BraveSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.brave_api_key.strip()
        self.base_url = settings.brave_base_url.rstrip("/")
        self.timeout_seconds = settings.brave_timeout_seconds
        self.daily_request_limit = settings.brave_daily_request_limit
        self.monthly_request_limit = settings.brave_monthly_request_limit
        self.usage_file = settings.provider_usage_file

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        allowed, quota_message = _consume_external_provider_quota(
            provider_name="brave",
            usage_file=self.usage_file,
            daily_limit=self.daily_request_limit,
            monthly_limit=self.monthly_request_limit,
            units=1,
            unit_label="requests",
        )
        if not allowed:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="brave_quota_guard",
                    value=quota_message,
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            response = httpx.get(
                f"{self.base_url}/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
                params={
                    "q": f"{ticker} stock earnings guidance valuation",
                    "count": 5,
                    "search_lang": "en",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            results = (payload.get("web") or {}).get("results") or []
            snippets = [
                f"{item.get('title')}: {item.get('description')}"
                for item in results[:4]
                if item.get("title") or item.get("description")
            ]
            if not snippets:
                payload_keys = ", ".join(sorted(payload.keys())) or "none"
                return [
                    InjectedDataPoint(
                        source_type=DataSourceType.OTHER,
                        label="brave_provider_warning",
                        value=(
                            "Brave 검색 호출은 성공했지만 사용 가능한 web.results가 없었습니다. "
                            f"응답 키: {payload_keys}. Brave 플랜/검색 권한 또는 쿼리 제한을 확인하세요."
                        ),
                        as_of=_provider_now(),
                        source_url=f"{self.base_url}/web/search",
                        confidence=0.5,
                    )
                ]
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.NEWS,
                    label="brave_search_context",
                    value=" | ".join(snippets),
                    as_of=_provider_now(),
                    source_url=f"{self.base_url}/web/search",
                    confidence=0.64,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="brave_provider_warning",
                    value=f"Brave 검색 호출 실패: {_safe_provider_error(exc)}",
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
    if mode == "fmp" and configured:
        return "FMP 무료 API 프로바이더가 설정되었습니다. 무료 플랜에서 막히는 가격/재무 엔드포인트는 합성 숫자 없이 경고만 표시하고, 가능하면 KIS 현재가를 보조로 사용합니다."
    if mode == "fmp":
        return "FMP 모드가 선택되었지만 FMP_API_KEY가 없어 실제 데이터 자동 주입을 중단합니다."
    if mode == "kis" and configured:
        return "KIS 해외주식 현재가 프로바이더가 활성화되었습니다. FMP 유료 엔드포인트는 호출하지 않습니다."
    if mode == "kis":
        return "KIS 모드가 선택되었지만 KIS_APP_KEY/KIS_APP_SECRET 또는 접근 토큰이 없어 현재가 자동 주입을 중단합니다."
    return "Mock 데이터 프로바이더가 활성화되어 있습니다."


def _external_provider_status_message(label: str, configured: bool) -> str:
    if configured:
        return f"{label} 프로바이더가 설정되었습니다."
    return f"{label} API 키가 없어 해당 보강 데이터를 건너뜁니다."


def _kis_status_message(client: KisClient) -> str:
    if client.uses_external_token:
        return "KIS 해외주식 현재가 프로바이더가 기존 접근 토큰 재사용 모드로 설정되었습니다. tokenP 신규 발급을 호출하지 않습니다."
    if client.can_issue_token:
        return "KIS 해외주식 현재가 프로바이더가 tokenP 발급 허용 모드로 설정되었습니다."
    if client.app_key and client.app_key != "********" and client.app_secret and client.app_secret != "********":
        return "KIS 키는 있으나 tokenP 신규 발급이 비활성화되어 있습니다. 자동매매 보호를 위해 KIS_ACCESS_TOKEN 또는 KIS_ACCESS_TOKEN_FILE을 설정하세요."
    return "KIS_APP_KEY/KIS_APP_SECRET 또는 기존 접근 토큰이 없어 KIS 해외주식 현재가 대체 조회를 건너뜁니다."
