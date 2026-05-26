from abc import ABC, abstractmethod
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

_PROVIDER_USAGE_LOCK = threading.Lock()
_NPS_ODCLOUD_CACHE_LOCK = threading.Lock()
_NPS_ODCLOUD_ROW_CACHE: dict[str, dict] = {}
_NPS_ODCLOUD_MEMORY_TTL_SECONDS = 6 * 60 * 60
_NPS_ODCLOUD_PERSISTENT_TTL_SECONDS = 7 * 24 * 60 * 60
_CUSTOMS_TRADE_CACHE_LOCK = threading.Lock()
_CUSTOMS_TRADE_MEMORY_CACHE: dict[str, dict] = {}
_CUSTOMS_TRADE_MEMORY_TTL_SECONDS = 6 * 60 * 60
CUSTOMS_DEFAULT_COUNTRY_CODES = ["US", "CN", "JP", "VN", "HK", "TW", "SG", "DE", "IN"]


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


class DataProviderStatus:
    def __init__(
        self,
        name: str,
        mode: str,
        ready: bool,
        message: str,
        fallback_active: bool = False,
    ) -> None:
        self.name = name
        self.mode = mode
        self.ready = ready
        self.message = message
        self.fallback_active = fallback_active

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mode": self.mode,
            "ready": self.ready,
            "message": self.message,
            "fallback_active": self.fallback_active,
        }


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class FinancialDataProvider(ABC):
    @abstractmethod
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class SupplementalDataProvider(ABC):
    @abstractmethod
    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class MockMarketDataProvider(MarketDataProvider):
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        as_of = datetime.now(timezone.utc).isoformat()
        ticker_seed = sum(ord(char) for char in ticker)
        mock_price = round(50 + (ticker_seed % 450) + (ticker_seed % 17) / 10, 2)
        mock_volume = 1_000_000 + (ticker_seed % 900) * 10_000
        mock_volatility = round(0.18 + (ticker_seed % 25) / 100, 2)

        return [
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="last_price",
                value=str(mock_price),
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="average_volume",
                value=str(mock_volume),
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="estimated_volatility",
                value=str(mock_volatility),
                as_of=as_of,
                confidence=0.55,
            ),
        ]


class MockFinancialDataProvider(FinancialDataProvider):
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        as_of = datetime.now(timezone.utc).isoformat()
        ticker_seed = sum(ord(char) for char in ticker)
        revenue_growth = round(0.05 + (ticker_seed % 35) / 100, 2)
        gross_margin = round(0.35 + (ticker_seed % 40) / 100, 2)
        free_cash_flow_margin = round(0.08 + (ticker_seed % 22) / 100, 2)
        net_debt_to_ebitda = round((ticker_seed % 30) / 10, 1)

        return [
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="revenue_growth",
                value=f"{revenue_growth:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="gross_margin",
                value=f"{gross_margin:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="free_cash_flow_margin",
                value=f"{free_cash_flow_margin:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="net_debt_to_ebitda",
                value=str(net_debt_to_ebitda),
                as_of=as_of,
                confidence=0.55,
            ),
        ]


class EmptyMarketDataProvider(MarketDataProvider):
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class EmptyFinancialDataProvider(FinancialDataProvider):
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class EmptySupplementalDataProvider(SupplementalDataProvider):
    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class CompositeMarketDataProvider(MarketDataProvider):
    def __init__(self, providers: list[MarketDataProvider]) -> None:
        self.providers = providers

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_market_snapshot(ticker))
        return data


class CompositeFinancialDataProvider(FinancialDataProvider):
    def __init__(self, providers: list[FinancialDataProvider]) -> None:
        self.providers = providers

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_financial_snapshot(ticker))
        return data


class CompositeSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, providers: list[SupplementalDataProvider]) -> None:
        self.providers = providers

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_supplemental_snapshot(ticker))
        return data


KIS_US_EXCHANGE_BY_TICKER = {
    "AAPL": "NAS",
    "AMZN": "NAS",
    "GOOGL": "NAS",
    "META": "NAS",
    "MSFT": "NAS",
    "NVDA": "NAS",
    "PL": "NYS",
    "PLTR": "NYS",
    "TSLA": "NAS",
    "XOM": "NYS",
    "JNJ": "NYS",
}

_KIS_MEMORY_TOKEN_CACHE: dict[str, str] = {}


def _kis_candidate_exchange_codes(ticker: str) -> list[str]:
    mapped_exchange = KIS_US_EXCHANGE_BY_TICKER.get(ticker.upper())
    if mapped_exchange:
        return [mapped_exchange]
    return ["NAS", "NYS", "AMS"]


def _looks_like_korean_security_code(ticker: str) -> bool:
    normalized = ticker.strip().upper()
    return len(normalized) == 6 and any(char.isdigit() for char in normalized)


class KisClient:
    def __init__(self, settings: Settings) -> None:
        self.app_key = settings.kis_app_key.strip()
        self.app_secret = settings.kis_app_secret.strip()
        self.base_url = settings.kis_api_base_url.rstrip("/")
        self.allow_token_issue = settings.kis_allow_token_issue
        self.configured_access_token = settings.kis_access_token.strip()
        self.access_token_file = settings.kis_access_token_file.strip()
        self.token_cache_file = settings.kis_token_cache_file.strip()
        self.timeout_seconds = settings.kis_timeout_seconds
        self._access_token: str | None = None

    @property
    def is_configured(self) -> bool:
        return self.has_access_token or self.can_issue_token

    @property
    def can_issue_token(self) -> bool:
        return (
            self.allow_token_issue
            and
            bool(self.app_key and self.app_key != "********")
            and bool(self.app_secret and self.app_secret != "********")
        )

    @property
    def has_access_token(self) -> bool:
        return bool(self.configured_access_token) or bool(self._read_access_token_file())

    @property
    def uses_external_token(self) -> bool:
        return self.has_access_token

    def _normalize_token(self, token: str) -> str:
        stripped = token.strip()
        if not stripped:
            return ""
        if stripped.lower().startswith("bearer "):
            return stripped
        return f"Bearer {stripped}"

    def _token_cache_key(self) -> str:
        return f"{self.base_url}|{self.app_key[-8:] if self.app_key else ''}"

    def _resolve_token_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[1] / path).resolve()

    def _read_token_from_path(self, path_value: str) -> str:
        if not path_value:
            return ""
        try:
            path = self._resolve_token_path(path_value)
            if not path.exists() or not path.is_file():
                return ""
            raw_value = path.read_text(encoding="utf-8").strip()
            if not raw_value:
                return ""
            if raw_value.startswith("{"):
                payload = json.loads(raw_value)
                return str(
                    payload.get("access_token")
                    or payload.get("authorization")
                    or payload.get("token")
                    or ""
                ).strip()
            return raw_value
        except Exception:
            return ""

    def _read_access_token_file(self) -> str:
        return self._read_token_from_path(self.access_token_file) or self._read_token_from_path(
            self.token_cache_file
        )

    def _write_token_cache(self, payload: dict) -> None:
        if not self.token_cache_file:
            return
        try:
            path = self._resolve_token_path(self.token_cache_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def issue_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        memory_token = _KIS_MEMORY_TOKEN_CACHE.get(self._token_cache_key())
        if memory_token:
            self._access_token = memory_token
            return self._access_token
        if self.configured_access_token:
            self._access_token = self._normalize_token(self.configured_access_token)
            _KIS_MEMORY_TOKEN_CACHE[self._token_cache_key()] = self._access_token
            return self._access_token

        file_token = self._read_access_token_file()
        if file_token:
            self._access_token = self._normalize_token(file_token)
            _KIS_MEMORY_TOKEN_CACHE[self._token_cache_key()] = self._access_token
            return self._access_token

        if not self.can_issue_token:
            raise RuntimeError(
                "KIS 토큰 신규 발급은 비활성화되어 있습니다. "
                "자동매매 시스템과 충돌하지 않도록 KIS_ACCESS_TOKEN 또는 "
                "KIS_ACCESS_TOKEN_FILE을 설정하거나, 명시적으로 KIS_ALLOW_TOKEN_ISSUE=true를 설정하세요."
            )

        response = httpx.post(
            f"{self.base_url}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            headers={"content-type": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("KIS token response did not include access_token.")
        self._access_token = f"Bearer {token}"
        _KIS_MEMORY_TOKEN_CACHE[self._token_cache_key()] = self._access_token
        self._write_token_cache(payload)
        return self._access_token

    def get(self, endpoint: str, tr_id: str, params: dict) -> dict:
        token = self.issue_access_token()
        response = httpx.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params=params,
            headers={
                "content-type": "application/json; charset=utf-8",
                "authorization": token,
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        rt_cd = payload.get("rt_cd")
        if rt_cd not in (None, "0"):
            message = payload.get("msg1") or payload.get("msg_cd") or "KIS API error"
            raise RuntimeError(message)
        return payload


class KisOverseasMarketDataProvider(MarketDataProvider):
    def __init__(self, client: KisClient) -> None:
        self.client = client

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker):
            return self._fetch_domestic_market_snapshot(ticker)
        return self._fetch_overseas_market_snapshot(ticker)

    def _fetch_domestic_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        try:
            payload = self.client.get(
                "uapi/domestic-stock/v1/quotations/inquire-price",
                "FHKST01010100",
                {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": ticker.upper(),
                },
            )
            output = payload.get("output") or {}
            last_price = output.get("stck_prpr")
            if not last_price or str(last_price).lower() == "n/a":
                raise RuntimeError(
                    f"KIS domestic quote returned no usable price for {ticker.upper()}."
                )
            as_of = datetime.now(timezone.utc).isoformat()
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="last_price",
                    value=str(last_price),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
                    confidence=0.86,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="volume",
                    value=str(output.get("acml_vol") or "n/a"),
                    as_of=as_of,
                    source_url=f"{self.client.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
                    confidence=0.78,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.MARKET_PRICE,
                    label="kis_exchange_code",
                    value="KRX",
                    as_of=as_of,
                    source_url="KIS domestic quotation",
                    confidence=0.9,
                ),
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="kis_market_data_provider_warning",
                    value=(
                        "KIS 국내주식 현재가 호출 실패로 가격 자동 주입을 중단했습니다. "
                        f"사유: {_safe_provider_error(exc)}"
                    ),
                    as_of=datetime.now(timezone.utc).isoformat(),
                    confidence=0.5,
                )
            ]

    def _fetch_overseas_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        try:
            last_error: Exception | None = None
            for exchange_code in _kis_candidate_exchange_codes(ticker):
                try:
                    payload = self.client.get(
                        "uapi/overseas-price/v1/quotations/price",
                        "HHDFS00000300",
                        {"AUTH": "", "EXCD": exchange_code, "SYMB": ticker.upper()},
                    )
                    output = payload.get("output") or {}
                    last_price = output.get("last") or output.get("base")
                    if not last_price or str(last_price).lower() == "n/a":
                        raise RuntimeError(
                            f"KIS quote returned no usable price for {ticker.upper()} "
                            f"on {exchange_code}."
                        )
                    as_of = datetime.now(timezone.utc).isoformat()
                    return [
                        InjectedDataPoint(
                            source_type=DataSourceType.MARKET_PRICE,
                            label="last_price",
                            value=str(last_price),
                            as_of=as_of,
                            source_url=f"{self.client.base_url}/uapi/overseas-price/v1/quotations/price",
                            confidence=0.82,
                        ),
                        InjectedDataPoint(
                            source_type=DataSourceType.MARKET_PRICE,
                            label="volume",
                            value=str(output.get("tvol") or output.get("pvol") or "n/a"),
                            as_of=as_of,
                            source_url=f"{self.client.base_url}/uapi/overseas-price/v1/quotations/price",
                            confidence=0.78,
                        ),
                        InjectedDataPoint(
                            source_type=DataSourceType.MARKET_PRICE,
                            label="kis_exchange_code",
                            value=exchange_code,
                            as_of=as_of,
                            source_url="KIS overseas quotation",
                            confidence=0.9,
                        ),
                    ]
                except Exception as error:
                    last_error = error
            raise last_error or RuntimeError("KIS quote lookup failed.")
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="kis_market_data_provider_warning",
                    value=(
                        "KIS 해외주식 현재가 호출 실패로 가격 자동 주입을 중단했습니다. "
                        f"사유: {_safe_provider_error(exc)}"
                    ),
                    as_of=datetime.now(timezone.utc).isoformat(),
                    confidence=0.5,
                )
            ]


def _is_configured_secret(value: str) -> bool:
    return bool(value and value.strip() and value.strip() != "********")


def _provider_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_value(row: dict, keys: list[str]) -> object | None:
    normalized = {
        str(key).strip().lower().replace(" ", "").replace("_", ""): value
        for key, value in row.items()
    }
    for key in keys:
        wanted = key.strip().lower().replace(" ", "").replace("_", "")
        if wanted in normalized and normalized[wanted] not in (None, ""):
            return normalized[wanted]
    return None


def _parse_float_value(value: object | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "").replace("▲", "").replace("▼", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_korean_stock_code(value: str) -> str:
    text = str(value or "").strip().upper()
    text = text.removesuffix(".KS").removesuffix(".KQ")
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits and len(digits) <= 6 else text


def _compact_company_name(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or "").lower())
    for suffix in ["주식회사", "(주)", "㈜", "보통주", "우선주", "corporation", "corp.", "corp", "inc.", "inc"]:
        text = text.replace(suffix.lower(), "")
    return text


class NpsOdcloudClient:
    DOMESTIC_NAMESPACE = "3070507/v1"
    LARGE_HOLDING_NAMESPACE = "15106890/v1"

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.nps_odcloud_enabled
        self.api_key = settings.nps_odcloud_api_key.strip()
        self.base_url = settings.nps_odcloud_base_url.rstrip("/")
        self.domestic_docs_url = settings.nps_domestic_stock_docs_url
        self.large_holding_docs_url = settings.nps_large_holding_docs_url
        self.domestic_api_url = settings.nps_domestic_stock_api_url.strip()
        self.large_holding_api_url = settings.nps_large_holding_api_url.strip()
        self.timeout_seconds = settings.nps_odcloud_timeout_seconds
        self.max_pages = max(1, settings.nps_odcloud_max_pages)
        vault_dir = (Path(__file__).resolve().parents[1] / settings.research_vault_dir).resolve()
        self.cache_file = vault_dir / "_system" / "nps_odcloud_rows_cache.json"

    @property
    def is_configured(self) -> bool:
        return self.enabled and _is_configured_secret(self.api_key)

    def status_message(self) -> str:
        if not self.enabled:
            return "국민연금 공공데이터포털 연동이 비활성화되어 있습니다."
        if not self.is_configured:
            return "NPS_ODCLOUD_API_KEY가 없어 국민연금 보유/대량보유 데이터를 건너뜁니다."
        return (
            "국민연금 공공데이터포털 API가 설정되었습니다. 국내주식 투자정보(연간)와 "
            "대량보유 보고내역(분기)을 기관 수급 보조 신호로 사용합니다."
        )

    def _candidate_urls(self, explicit_url: str, namespace: str, docs_url: str) -> list[str]:
        urls = []
        if explicit_url:
            urls.append(explicit_url)
            return urls
        namespace = namespace.strip("/")
        urls.extend(
            [
                f"{self.base_url}/{namespace}",
                f"{self.base_url}/{namespace}/",
            ]
        )
        try:
            # 공공데이터포털 계열 API만 시스템 프록시를 타지 않게 고정합니다.
            # 일부 로컬 프록시/보안 도구가 127.0.0.1 차단 포트로 잡혀 있으면 WinError 10061이 발생합니다.
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.get(docs_url)
                response.raise_for_status()
                text = response.text
            for match in re.findall(r"https://api\.odcloud\.kr/api/[^\"'\\\s<>]+", text):
                urls.append(match)
            for match in re.findall(r"(/api/[^\"'\\\s<>]+)", text):
                urls.append("https://api.odcloud.kr" + match)
            for match in re.findall(rf"(/?{re.escape(namespace)}/[^\"'\\\s<>]+)", text):
                urls.append(f"{self.base_url}/{match.lstrip('/')}")
        except Exception:
            pass
        deduped = []
        for url in urls:
            clean = str(url).strip().rstrip("?")
            if clean and clean not in deduped:
                deduped.append(clean)
        return deduped

    def _read_persistent_cache(self, cache_key: str) -> dict | None:
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        cached = payload.get(cache_key)
        if not isinstance(cached, dict):
            return None
        rows = cached.get("rows")
        if not isinstance(rows, list):
            return None
        age = datetime.now(timezone.utc).timestamp() - float(cached.get("ts") or 0)
        if age > _NPS_ODCLOUD_PERSISTENT_TTL_SECONDS:
            return None
        return cached

    def _write_persistent_cache(self, cache_key: str, record: dict) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                json.loads(self.cache_file.read_text(encoding="utf-8"))
                if self.cache_file.exists()
                else {}
            )
            if not isinstance(payload, dict):
                payload = {}
            payload[cache_key] = {
                "ts": record.get("ts"),
                "rows": record.get("rows") or [],
                "used_url": record.get("used_url"),
            }
            self.cache_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def _fetch_rows(self, *, explicit_url: str, namespace: str, docs_url: str) -> tuple[list[dict], list[str], str | None]:
        if not self.is_configured:
            return [], [self.status_message()], None
        cache_key = "|".join([explicit_url, namespace, docs_url, self.api_key[-8:]])
        persistent_cached: dict | None = None
        with _NPS_ODCLOUD_CACHE_LOCK:
            cached = _NPS_ODCLOUD_ROW_CACHE.get(cache_key)
            if cached and (datetime.now(timezone.utc).timestamp() - cached.get("ts", 0)) < _NPS_ODCLOUD_MEMORY_TTL_SECONDS:
                return list(cached.get("rows") or []), list(cached.get("errors") or []), cached.get("used_url")
            persistent_cached = self._read_persistent_cache(cache_key)
        rows: list[dict] = []
        errors: list[str] = []
        used_url: str | None = None
        for url in self._candidate_urls(explicit_url, namespace, docs_url):
            try:
                with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                    for page in range(1, self.max_pages + 1):
                        response = client.get(
                            url,
                            params={
                                "page": page,
                                "perPage": 1000,
                                "returnType": "JSON",
                                "serviceKey": self.api_key,
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()
                        page_rows = payload.get("data") if isinstance(payload, dict) else payload
                        if isinstance(page_rows, dict):
                            page_rows = page_rows.get("data") or page_rows.get("items") or []
                        if not isinstance(page_rows, list):
                            page_rows = []
                        rows.extend([row for row in page_rows if isinstance(row, dict)])
                        used_url = url
                        if len(page_rows) < 1000:
                            break
                if rows:
                    cache_record = {
                        "ts": datetime.now(timezone.utc).timestamp(),
                        "rows": rows,
                        "errors": errors,
                        "used_url": used_url,
                    }
                    with _NPS_ODCLOUD_CACHE_LOCK:
                        _NPS_ODCLOUD_ROW_CACHE[cache_key] = cache_record
                        self._write_persistent_cache(cache_key, cache_record)
                    return rows, errors, used_url
            except Exception as exc:
                errors.append(f"{url}: {_safe_provider_error(exc)}")
        if persistent_cached:
            cached_rows = list(persistent_cached.get("rows") or [])
            cached_url = persistent_cached.get("used_url")
            cached_at = datetime.fromtimestamp(
                float(persistent_cached.get("ts") or 0),
                timezone.utc,
            ).isoformat()
            fallback_errors = errors + [
                f"외부 호출 실패로 마지막 성공 캐시를 사용했습니다. 캐시 시각: {cached_at}"
            ]
            with _NPS_ODCLOUD_CACHE_LOCK:
                _NPS_ODCLOUD_ROW_CACHE[cache_key] = {
                    "ts": datetime.now(timezone.utc).timestamp(),
                    "rows": cached_rows,
                    "errors": fallback_errors,
                    "used_url": cached_url,
                }
            return cached_rows, fallback_errors, cached_url
        with _NPS_ODCLOUD_CACHE_LOCK:
            _NPS_ODCLOUD_ROW_CACHE[cache_key] = {
                "ts": datetime.now(timezone.utc).timestamp(),
                "rows": rows,
                "errors": errors,
                "used_url": used_url,
            }
        return rows, errors, used_url

    def fetch_domestic_stock_rows(self) -> tuple[list[dict], list[str], str | None]:
        return self._fetch_rows(
            explicit_url=self.domestic_api_url,
            namespace=self.DOMESTIC_NAMESPACE,
            docs_url=self.domestic_docs_url,
        )

    def fetch_large_holding_rows(self) -> tuple[list[dict], list[str], str | None]:
        return self._fetch_rows(
            explicit_url=self.large_holding_api_url,
            namespace=self.LARGE_HOLDING_NAMESPACE,
            docs_url=self.large_holding_docs_url,
        )

    def _row_matches(self, row: dict, ticker: str, company_name: str | None) -> bool:
        ticker_code = _normalize_korean_stock_code(ticker)
        candidate_code = _first_value(
            row,
            ["종목코드", "단축코드", "ticker", "stock_code", "isin", "isu_srt_cd"],
        )
        if candidate_code and _normalize_korean_stock_code(str(candidate_code)) == ticker_code:
            return True
        names = [
            _first_value(row, ["종목명", "회사명", "발행기관명", "Company", "Issuer", "corp_nm"]),
        ]
        compact_company = _compact_company_name(company_name or "")
        if not compact_company:
            return False
        return any(_compact_company_name(str(name or "")) == compact_company for name in names if name)

    def find_signal(self, ticker: str, company_name: str | None = None) -> dict:
        domestic_rows, domestic_errors, domestic_url = self.fetch_domestic_stock_rows()
        domestic_match = next(
            (row for row in domestic_rows if self._row_matches(row, ticker, company_name)),
            None,
        )
        large_rows, large_errors, large_url = self.fetch_large_holding_rows()
        large_matches = [
            row for row in large_rows if self._row_matches(row, ticker, company_name)
        ][:5]
        holding_ratio = _parse_float_value(
            _first_value(domestic_match or {}, ["지분율(퍼센트)", "지분율", "Holding"])
        )
        domestic_weight = _parse_float_value(
            _first_value(domestic_match or {}, ["자산군 내 비중(퍼센트)", "비중", "Weight"])
        )
        amount_100m_krw = _parse_float_value(
            _first_value(domestic_match or {}, ["평가액(억 원)", "평가액", "Amount"])
        )
        issuer = (
            _first_value(domestic_match or {}, ["종목명", "회사명", "Company"])
            or _first_value((large_matches[0] if large_matches else {}), ["발행기관명", "Issuer"])
            or company_name
            or ticker
        )
        large_events = []
        for row in large_matches:
            ratio = _parse_float_value(_first_value(row, ["지분율(퍼센트)", "지분율", "Holding"]))
            base_date = _first_value(row, ["보고서 작성기준일", "기준일", "보고일자", "Base date for report"])
            large_events.append(
                {
                    "issuer": _first_value(row, ["발행기관명", "Issuer"]) or issuer,
                    "base_date": str(base_date or ""),
                    "holding_ratio": ratio,
                    "raw": row,
                }
            )
        warnings = domestic_errors + large_errors
        return {
            "ticker": ticker,
            "company_name": str(issuer or ticker),
            "holding_ratio": holding_ratio,
            "domestic_weight": domestic_weight,
            "amount_100m_krw": amount_100m_krw,
            "domestic_match_found": domestic_match is not None,
            "large_holding_events": large_events,
            "source_urls": {
                "domestic_stock": domestic_url or self.domestic_docs_url,
                "large_holding": large_url or self.large_holding_docs_url,
            },
            "warnings": warnings[:4],
            "as_of": _provider_now(),
        }


def nps_signal_to_data_points(signal: dict) -> list[InjectedDataPoint]:
    if not signal:
        return []
    points: list[InjectedDataPoint] = []
    company = signal.get("company_name") or signal.get("ticker")
    ratio = signal.get("holding_ratio")
    weight = signal.get("domestic_weight")
    amount = signal.get("amount_100m_krw")
    if signal.get("domestic_match_found"):
        parts = [f"{company} 국민연금 국내주식 투자정보"]
        if ratio is not None:
            parts.append(f"지분율 {ratio:.2f}%")
        if weight is not None:
            parts.append(f"국내주식 자산군 내 비중 {weight:.2f}%")
        if amount is not None:
            parts.append(f"평가액 {amount:,.0f}억 원")
        parts.append("연도말 기준 데이터이므로 장기 기관 보유 신호로만 해석")
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_domestic_stock_investment",
                value=" | ".join(parts),
                as_of=signal.get("as_of"),
                source_url=(signal.get("source_urls") or {}).get("domestic_stock"),
                confidence=0.84,
            )
        )
    events = signal.get("large_holding_events") or []
    if events:
        event_summaries = []
        for event in events[:3]:
            event_ratio = event.get("holding_ratio")
            event_date = event.get("base_date") or "기준일 미확인"
            if event_ratio is None:
                event_summaries.append(f"{event_date} 대량보유 보고")
            else:
                event_summaries.append(f"{event_date} 지분율 {event_ratio:.2f}%")
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_large_holding_report",
                value=(
                    f"{company} 국민연금 대량보유 보고 이벤트: "
                    + "; ".join(event_summaries)
                    + " | 5% 이상 신규취득 또는 1% 이상 변동 공시 이벤트로 해석"
                ),
                as_of=signal.get("as_of"),
                source_url=(signal.get("source_urls") or {}).get("large_holding"),
                confidence=0.88,
            )
        )
    for warning in signal.get("warnings") or []:
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_provider_warning",
                value=f"국민연금 공공데이터포털 호출 경고: {warning}",
                as_of=signal.get("as_of"),
                confidence=0.5,
            )
        )
    return points


class KoreaCustomsTradeClient:
    """
    관세청 품목별 국가별 수출입실적(GW) 공공데이터포털 client.
    API 문서상 XML 응답이 기본이라 XML/JSON을 모두 느슨하게 파싱한다.
    """

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.customs_trade_enabled
        self.api_key = settings.customs_trade_api_key.strip()
        self.api_url = settings.customs_trade_api_url.strip()
        self.total_api_url = settings.customs_trade_total_api_url.strip()
        self.total_docs_url = settings.customs_trade_total_docs_url.strip()
        self.timeout_seconds = settings.customs_trade_timeout_seconds
        self.max_rows = max(1, settings.customs_trade_max_rows)

    @property
    def is_configured(self) -> bool:
        return self.enabled and _is_configured_secret(self.api_key) and bool(self.api_url)

    @property
    def is_total_trend_configured(self) -> bool:
        return self.enabled and _is_configured_secret(self.api_key) and bool(self.total_api_url)

    def status_message(self) -> str:
        if not self.enabled:
            return "관세청 수출입 실적 공공데이터 연동이 비활성화되어 있습니다."
        if not self.is_configured:
            return "CUSTOMS_TRADE_API_KEY가 없어 관세청 품목·국가별 수출입 실적을 건너뜁니다."
        return (
            "관세청 품목별 국가별 수출입실적 API가 설정되었습니다. "
            "1일·11일·21일 발표 자료를 수출주/섹터/재고 부담 참고자료로 활용합니다."
        )

    def total_trend_status_message(self) -> str:
        if not self.enabled:
            return "관세청 수출입 총괄/잠정 동향 공공데이터 연동이 비활성화되어 있습니다."
        if not _is_configured_secret(self.api_key):
            return "CUSTOMS_TRADE_API_KEY가 없어 관세청 수출입 총괄/잠정 동향을 건너뜁니다."
        if not self.total_api_url:
            return "CUSTOMS_TRADE_TOTAL_API_URL이 없어 1일·11일·21일 잠정 수출입동향을 별도 확인할 수 없습니다."
        return (
            "관세청 수출입총괄(GW) API URL이 설정되었습니다. "
            "호출이 403이면 data.go.kr에서 해당 서비스 활용 신청/승인 상태를 확인하세요."
        )

    def _parse_payload_rows(self, response: httpx.Response) -> list[dict]:
        content_type = response.headers.get("content-type", "").lower()
        text = response.text
        if "json" in content_type or text.lstrip().startswith(("{", "[")):
            payload = response.json()
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
            if isinstance(payload, dict):
                data = payload.get("data") or payload.get("items") or payload.get("item")
                body = payload.get("response", {}).get("body", {}) if isinstance(payload.get("response"), dict) else {}
                data = data or body.get("items") or body.get("item")
                if isinstance(data, dict):
                    data = data.get("item") or data.get("data") or [data]
                return [row for row in (data or []) if isinstance(row, dict)]

        try:
            root = ET.fromstring(text.encode("utf-8"))
        except Exception:
            return []
        candidates = root.findall(".//item")
        if not candidates:
            candidates = [
                node
                for node in root.iter()
                if list(node) and any(child.text for child in list(node))
            ]
        rows: list[dict] = []
        for node in candidates:
            row = {
                re.sub(r"^\{.*\}", "", child.tag): (child.text or "").strip()
                for child in list(node)
            }
            if row:
                rows.append(row)
        return rows

    def fetch_item_trade_rows(
        self,
        *,
        start_yymm: str,
        end_yymm: str,
        item_code: str = "",
        country_code: str = "",
    ) -> tuple[list[dict], list[str], str | None]:
        if not self.is_configured:
            return [], [self.status_message()], None
        cache_key = "|".join([start_yymm, end_yymm, item_code, country_code, self.api_key[-8:]])
        with _CUSTOMS_TRADE_CACHE_LOCK:
            cached = _CUSTOMS_TRADE_MEMORY_CACHE.get(cache_key)
            if cached and datetime.now(timezone.utc).timestamp() - cached.get("ts", 0) < _CUSTOMS_TRADE_MEMORY_TTL_SECONDS:
                return list(cached.get("rows") or []), list(cached.get("warnings") or []), cached.get("used_url")

        params = {
            "serviceKey": self.api_key,
            "numOfRows": self.max_rows,
            "pageNo": 1,
            "strtYymm": start_yymm,
            "endYymm": end_yymm,
        }
        if item_code:
            params["hsSgn"] = item_code
        if country_code:
            params["cntyCd"] = country_code
        warnings: list[str] = []
        rows: list[dict] = []
        used_url: str | None = self.api_url
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.get(self.api_url, params=params)
                response.raise_for_status()
                rows = self._parse_payload_rows(response)
        except Exception as exc:
            warnings.append(f"관세청 수출입 실적 호출 실패: {_safe_provider_error(exc)}")
        with _CUSTOMS_TRADE_CACHE_LOCK:
            _CUSTOMS_TRADE_MEMORY_CACHE[cache_key] = {
                "ts": datetime.now(timezone.utc).timestamp(),
                "rows": rows,
                "warnings": warnings,
                "used_url": used_url,
            }
        return rows, warnings, used_url

    def fetch_total_trend_status(
        self,
        *,
        start_yymm: str,
        end_yymm: str,
    ) -> dict:
        if not self.is_total_trend_configured:
            next_action = (
                "CUSTOMS_TRADE_API_KEY와 CUSTOMS_TRADE_TOTAL_API_URL을 backend\\.env에 설정한 뒤 "
                "백엔드를 재시작하세요."
            )
            return {
                "status": "warning",
                "configured": self.is_total_trend_configured,
                "authorized": False,
                "http_status_code": None,
                "source_url": self.total_api_url or None,
                "docs_url": self.total_docs_url or None,
                "row_count": 0,
                "rows": [],
                "warnings": [self.total_trend_status_message()],
                "message": self.total_trend_status_message(),
                "next_action": next_action,
            }

        params = {
            "serviceKey": self.api_key,
            "numOfRows": self.max_rows,
            "pageNo": 1,
            "strtYymm": start_yymm,
            "endYymm": end_yymm,
        }
        rows: list[dict] = []
        warnings: list[str] = []
        status_code: int | None = None
        response_preview = ""
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.get(self.total_api_url, params=params)
                status_code = response.status_code
                response_preview = (response.text or "")[:240].replace(self.api_key, "[masked]")
                if status_code == 403:
                    warnings.append(
                        "관세청 수출입총괄(GW) API가 403 Forbidden을 반환했습니다. "
                        "data.go.kr에서 해당 서비스 활용 신청/승인 또는 키 권한을 확인하세요."
                    )
                elif status_code >= 400:
                    warnings.append(f"관세청 수출입총괄(GW) 호출 실패: HTTP {status_code}")
                else:
                    rows = self._parse_payload_rows(response)
        except Exception as exc:
            warnings.append(f"관세청 수출입총괄(GW) 호출 실패: {_safe_provider_error(exc)}")

        if status_code is not None and status_code < 400 and not rows:
            warnings.append("관세청 수출입총괄(GW) 응답에서 표시할 수출입 행을 찾지 못했습니다.")

        authorized = status_code is not None and status_code < 400
        if authorized and rows:
            next_action = "수출입총괄(GW) 수치가 확인되었습니다. 시장일지와 수출주 점검에 반영할 수 있습니다."
        elif status_code == 403:
            next_action = "data.go.kr에서 관세청_수출입총괄(GW) 활용 신청/승인 상태와 인증키 권한을 확인하세요."
        elif authorized:
            next_action = "API 권한은 확인됐지만 행이 비어 있습니다. 발표 기간과 조회 파라미터를 확인하세요."
        else:
            next_action = "관세청 수출입총괄(GW) API URL, 네트워크, 인증키 설정을 확인하세요."
        return {
            "status": "success" if authorized and rows else "warning",
            "configured": self.is_total_trend_configured,
            "authorized": authorized,
            "http_status_code": status_code,
            "source_url": self.total_api_url,
            "docs_url": self.total_docs_url or None,
            "start_yymm": start_yymm,
            "end_yymm": end_yymm,
            "row_count": len(rows),
            "rows": rows[: self.max_rows],
            "warnings": warnings,
            "response_preview": response_preview,
            "message": (
                "관세청 수출입총괄(GW) API 호출 가능"
                if authorized
                else "관세청 수출입총괄(GW) API 권한 또는 연결 확인 필요"
            ),
            "next_action": next_action,
        }


def normalize_customs_trade_row(row: dict) -> dict:
    export_value = _parse_float_value(
        _first_value(row, ["expDlr", "expUsd", "수출금액", "수출액", "EXP_DLR", "EXP_AMT"])
    )
    import_value = _parse_float_value(
        _first_value(row, ["impDlr", "impUsd", "수입금액", "수입액", "IMP_DLR", "IMP_AMT"])
    )
    export_weight = _parse_float_value(
        _first_value(row, ["expWgt", "수출중량", "EXP_WGT"])
    )
    import_weight = _parse_float_value(
        _first_value(row, ["impWgt", "수입중량", "IMP_WGT"])
    )
    balance = None
    if export_value is not None or import_value is not None:
        balance = (export_value or 0) - (import_value or 0)
    reported_balance = _parse_float_value(
        _first_value(row, ["balPayments", "무역수지", "BAL_PAYMENTS"])
    )
    if reported_balance is not None:
        balance = reported_balance
    return {
        "period": str(_first_value(row, ["year", "yymm", "기간", "기준년월", "TRD_YM"]) or ""),
        "hs_code": str(_first_value(row, ["hsCd", "hsSgn", "HS코드", "품목코드", "HS_SGN"]) or ""),
        "item_name": str(_first_value(row, ["statKor", "hsSgnNm", "품목명", "ITEM_NM"]) or ""),
        "country_code": str(_first_value(row, ["statCd", "cntyCd", "국가코드", "CNTY_CD"]) or ""),
        "country_name": str(_first_value(row, ["statCdCntnKor1", "cntyNm", "국가명", "COUNTRY_NM"]) or ""),
        "export_value_usd": export_value,
        "import_value_usd": import_value,
        "trade_balance_usd": balance,
        "export_weight": export_weight,
        "import_weight": import_weight,
        "raw": row,
    }


def is_valid_customs_trade_row(row: dict) -> bool:
    has_identifier = any(
        str(row.get(field) or "").strip()
        for field in ["period", "hs_code", "item_name", "country_code", "country_name"]
    )
    has_measurement = any(
        row.get(field) is not None
        for field in [
            "export_value_usd",
            "import_value_usd",
            "trade_balance_usd",
            "export_weight",
            "import_weight",
        ]
    )
    return has_identifier and has_measurement


def fetch_customs_trade_rows(
    settings: Settings,
    *,
    start_yymm: str,
    end_yymm: str,
    item_code: str = "",
    country_code: str = "",
) -> dict:
    client = KoreaCustomsTradeClient(settings)
    rows: list[dict] = []
    warnings: list[str] = []
    used_url: str | None = None
    query_country_codes = [country_code.strip().upper()] if country_code.strip() else CUSTOMS_DEFAULT_COUNTRY_CODES
    for query_country_code in query_country_codes:
        fetched_rows, fetched_warnings, fetched_url = client.fetch_item_trade_rows(
            start_yymm=start_yymm,
            end_yymm=end_yymm,
            item_code=item_code,
            country_code=query_country_code,
        )
        rows.extend(fetched_rows)
        warnings.extend(fetched_warnings)
        used_url = used_url or fetched_url
    normalized = [
        row
        for row in (normalize_customs_trade_row(raw_row) for raw_row in rows)
        if is_valid_customs_trade_row(row)
    ]
    if rows and not normalized:
        warnings.append(
            "관세청 API가 정상 응답했지만 실제 수출입 행 데이터가 비어 있습니다. "
            "발표 기간, HS코드, 국가 조건 또는 잠정 수출입 동향 전용 API를 확인하세요."
        )
    detail_rows = [
        row
        for row in normalized
        if row.get("period") != "총계" and str(row.get("hs_code") or "").strip() not in {"", "-"}
    ]
    if detail_rows:
        normalized = detail_rows
    normalized.sort(
        key=lambda item: abs(float(item.get("trade_balance_usd") or 0)),
        reverse=True,
    )
    return {
        "configured": client.is_configured,
        "status_message": client.status_message(),
        "source_url": used_url or settings.customs_trade_api_url,
        "start_yymm": start_yymm,
        "end_yymm": end_yymm,
        "item_code": item_code,
        "country_code": country_code or ",".join(query_country_codes),
        "row_count": len(normalized),
        "warnings": list(dict.fromkeys(warnings))[:8],
        "rows": normalized[: settings.customs_trade_max_rows],
    }


def fetch_customs_total_trend_status(
    settings: Settings,
    *,
    start_yymm: str,
    end_yymm: str,
) -> dict:
    client = KoreaCustomsTradeClient(settings)
    return client.fetch_total_trend_status(start_yymm=start_yymm, end_yymm=end_yymm)


def fetch_nps_institutional_signal(
    ticker: str,
    company_name: str | None,
    settings: Settings,
) -> dict:
    return NpsOdcloudClient(settings).find_signal(ticker, company_name)


def fetch_nps_institutional_context(
    ticker: str,
    company_name: str | None,
    settings: Settings,
) -> list[InjectedDataPoint]:
    client = NpsOdcloudClient(settings)
    if not client.is_configured:
        return []
    try:
        return nps_signal_to_data_points(client.find_signal(ticker, company_name))
    except Exception as exc:
        return [
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_provider_warning",
                value=f"국민연금 공공데이터포털 데이터 호출 실패: {_safe_provider_error(exc)}",
                as_of=_provider_now(),
                confidence=0.5,
            )
        ]


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


def _format_ratio(numerator: float | int | None, denominator: float | int | None) -> str:
    if not numerator or not denominator:
        return "n/a"
    return f"{(numerator / denominator):.1%}"


def _safe_provider_error(error: Exception) -> str:
    text = str(error)
    if "apikey=" in text:
        text = text.split("apikey=", 1)[0] + "apikey=****"
    if "serviceKey=" in text:
        text = text.split("serviceKey=", 1)[0] + "serviceKey=****"
    if "402" in text or "Payment Required" in text:
        if "financialdatasets" in text.lower():
            return (
                "Financial Datasets API의 현재 플랜/쿼터 제한(402 Payment Required)입니다. "
                "해당 데이터는 합성하지 않고 경고로만 표시합니다."
            )
        return (
            "FMP 무료 플랜 제한(402 Payment Required)입니다. "
            "유료 업그레이드는 사용하지 않고, 가격 데이터는 KIS로 대체하는 구성이 권장됩니다."
        )
    return text


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
