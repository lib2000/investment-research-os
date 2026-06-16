"""KIS quotation client and market data provider helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import httpx

from research_os.data_provider_core import MarketDataProvider
from research_os.data_provider_utils import _safe_provider_error
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


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