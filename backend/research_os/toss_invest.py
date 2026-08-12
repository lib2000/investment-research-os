"""Read-only Toss Securities Open API client.

The client intentionally covers OAuth, account discovery, and holdings only.
Order and conditional-order endpoints are kept out of the integration so a
portfolio refresh cannot create a live-trading side effect.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from research_os.settings import Settings


class TossTokenIssueResult(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    expires_at: float


class TossMaskedTokenStatus(BaseModel):
    status: str
    base_url: str
    account_seq: str | None = None
    source: str | None = None
    token_type: str | None = None
    expires_at: str | None = None
    masked_token: str | None = None


class TossApiError(RuntimeError):
    """Safe, non-secret summary of a Toss API failure."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _mask_token(token: str) -> str:
    if not token:
        return "********"
    if len(token) <= 12:
        return "********"
    return f"{token[:6]}****{token[-6:]}"


def _parse_decimal(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_toss_holding(item: dict[str, Any]) -> dict[str, Any]:
    """Map the official holdings schema to the portfolio-sync schema."""
    market_value = item.get("marketValue") if isinstance(item.get("marketValue"), dict) else {}
    profit_loss = item.get("profitLoss") if isinstance(item.get("profitLoss"), dict) else {}
    currency = str(item.get("currency") or ("KRW" if item.get("marketCountry") == "KR" else "USD")).upper()
    ticker = str(item.get("symbol") or "").strip().upper()
    average_cost = _parse_decimal(item.get("averagePurchasePrice"))
    quantity = _parse_decimal(item.get("quantity"))
    market_value_amount = _parse_decimal(market_value.get("amount"))
    cost_basis = _parse_decimal(market_value.get("purchaseAmount"))
    unrealized_gain = _parse_decimal(profit_loss.get("amount"))
    unrealized_return = _parse_decimal(profit_loss.get("rate"))
    return {
        "ticker": ticker,
        "name": str(item.get("name") or "").strip() or None,
        "quantity": quantity,
        "average_cost": average_cost,
        "current_price": _parse_decimal(item.get("lastPrice")),
        "market_value": market_value_amount,
        "cost_basis": cost_basis,
        "unrealized_gain": unrealized_gain,
        "unrealized_return": unrealized_return,
        "currency": currency,
        "market_country": str(item.get("marketCountry") or "").strip().upper() or None,
        "price_source": "toss_holdings",
    }


def _mask_order_id(order_id: object) -> str | None:
    value = str(order_id or "").strip()
    if not value:
        return None
    if len(value) <= 10:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def normalize_toss_order(item: dict[str, Any]) -> dict[str, Any]:
    """Return a secret-free, stable order-history record."""
    execution = item.get("execution") if isinstance(item.get("execution"), dict) else {}
    return {
        "order_id_masked": _mask_order_id(item.get("orderId")),
        "symbol": str(item.get("symbol") or "").strip().upper(),
        "side": str(item.get("side") or "").strip().upper() or None,
        "order_type": str(item.get("orderType") or "").strip().upper() or None,
        "time_in_force": str(item.get("timeInForce") or "").strip().upper() or None,
        "status": str(item.get("status") or "").strip().upper() or None,
        "currency": str(item.get("currency") or "").strip().upper() or None,
        "quantity": _parse_decimal(item.get("quantity")),
        "price": _parse_decimal(item.get("price")),
        "order_amount": _parse_decimal(item.get("orderAmount")),
        "ordered_at": item.get("orderedAt"),
        "canceled_at": item.get("canceledAt"),
        "execution": {
            "filled_quantity": _parse_decimal(execution.get("filledQuantity")),
            "average_filled_price": _parse_decimal(execution.get("averageFilledPrice")),
            "filled_amount": _parse_decimal(execution.get("filledAmount")),
            "commission": _parse_decimal(execution.get("commission")),
            "tax": _parse_decimal(execution.get("tax")),
            "filled_at": execution.get("filledAt"),
            "settlement_date": execution.get("settlementDate"),
        },
    }


class TossClient:
    """Small, read-only wrapper around the Toss Securities Open API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client_id = settings.toss_client_id.strip()
        self.client_secret = settings.toss_client_secret.strip()
        self.base_url = settings.toss_base_url.rstrip("/")
        self.account_seq = settings.toss_account_seq.strip()
        self.timeout_seconds = max(float(settings.toss_timeout_seconds or 10), 1.0)

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and self.client_id != "********"
            and self.client_secret != "********"
        )

    def _ensure_secret_ready(self) -> None:
        if not self.is_configured:
            raise ValueError("TOSS_CLIENT_ID와 TOSS_CLIENT_SECRET을 설정하세요.")

    def _resolve_cache_path(self) -> Path:
        path = Path(self.settings.toss_token_cache_file)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[1] / path).resolve()

    def _read_cached_access_token(self) -> TossTokenIssueResult | None:
        try:
            path = self._resolve_cache_path()
            if not path.exists() or not path.is_file():
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("broker") != "TOSS":
            return None
        cached_client_id = str(payload.get("client_id") or "").strip()
        if cached_client_id and cached_client_id != self.client_id:
            return None
        token = str(payload.get("access_token") or "").strip()
        expires_at = float(payload.get("expires_at") or 0)
        if not token or expires_at <= time.time() + max(int(self.settings.toss_token_expiry_buffer_seconds or 0), 0):
            return None
        return TossTokenIssueResult(
            access_token=token,
            token_type=str(payload.get("token_type") or "Bearer"),
            expires_in=max(0, int(expires_at - time.time())),
            expires_at=expires_at,
        )

    def _write_cached_access_token(self, result: TossTokenIssueResult) -> None:
        try:
            path = self._resolve_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "broker": "TOSS",
                        "client_id": self.client_id,
                        "token_type": result.token_type,
                        "access_token": result.access_token,
                        "expires_at": result.expires_at,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            return

    def issue_access_token(self, *, force_refresh: bool = False) -> TossTokenIssueResult:
        if not force_refresh:
            cached = self._read_cached_access_token()
            if cached:
                return cached
        self._ensure_secret_ready()
        response = httpx.post(
            f"{self.base_url}/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout_seconds,
            trust_env=False,
        )
        if response.is_error:
            raise self._api_error(response, "토스증권 OAuth 토큰 발급에 실패했습니다.")
        payload = response.json()
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise TossApiError("토스증권 OAuth 응답에 access_token이 없습니다.", status_code=response.status_code)
        expires_in = max(1, int(payload.get("expires_in") or 0))
        result = TossTokenIssueResult(
            access_token=token,
            token_type=str(payload.get("token_type") or "Bearer"),
            expires_in=expires_in,
            expires_at=time.time() + expires_in,
        )
        self._write_cached_access_token(result)
        return result

    def issue_masked_token_status(self) -> TossMaskedTokenStatus:
        before = self._read_cached_access_token()
        result = self.issue_access_token()
        expires_at = datetime.fromtimestamp(result.expires_at, tz=timezone.utc).isoformat()
        return TossMaskedTokenStatus(
            status="success",
            base_url=self.base_url,
            account_seq=self.account_seq or None,
            source="cache" if before and before.access_token == result.access_token else "issued",
            token_type=result.token_type,
            expires_at=expires_at,
            masked_token=_mask_token(result.access_token),
        )

    @staticmethod
    def _api_error(response: httpx.Response, fallback: str) -> TossApiError:
        code = None
        message = fallback
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                code = str(error.get("code") or "").strip() or None
                message = str(error.get("message") or message).strip() or message
            elif isinstance(payload, dict):
                code = str(payload.get("error") or "").strip() or None
                message = str(payload.get("error_description") or message).strip() or message
        except (ValueError, TypeError):
            pass
        suffix = f" ({code})" if code else ""
        return TossApiError(f"{message}{suffix}", status_code=response.status_code, code=code)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        account_seq: str | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = self.issue_access_token()
        headers = {"Authorization": f"{token.token_type} {token.access_token}"}
        resolved_account = str(account_seq or self.account_seq or "").strip()
        if resolved_account:
            headers["X-Tossinvest-Account"] = resolved_account
        retries = max(0, int(self.settings.toss_max_retries or 0))
        for attempt in range(retries + 1):
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                params=params,
                timeout=self.timeout_seconds,
                trust_env=False,
            )
            if response.status_code == 429 and attempt < retries:
                retry_after = _parse_decimal(response.headers.get("Retry-After"))
                delay = retry_after if retry_after is not None else float(self.settings.toss_retry_backoff_seconds or 1) * (2**attempt)
                time.sleep(min(max(delay, 0.1), 30.0))
                continue
            if response.is_error:
                raise self._api_error(response, f"토스증권 API 요청에 실패했습니다: {path}")
            payload = response.json()
            if not isinstance(payload, dict):
                raise TossApiError("토스증권 API 응답 형식이 올바르지 않습니다.", status_code=response.status_code)
            return payload
        raise TossApiError("토스증권 API 재시도 한도를 초과했습니다.", status_code=429, code="rate-limit-exceeded")

    def fetch_accounts(self) -> list[dict[str, Any]]:
        payload = self._request_json("GET", "/api/v1/accounts")
        result = payload.get("result")
        return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []

    def resolve_account_seq(self) -> str:
        if self.account_seq:
            return self.account_seq
        accounts = self.fetch_accounts()
        for account in accounts:
            if str(account.get("accountType") or "").upper() == "BROKERAGE" and account.get("accountSeq") is not None:
                return str(account["accountSeq"])
        if accounts and accounts[0].get("accountSeq") is not None:
            return str(accounts[0]["accountSeq"])
        raise ValueError("토스증권 계좌 목록에 종합매매 계좌가 없습니다.")

    def fetch_holdings(self, *, account_seq: str | None = None) -> dict[str, Any]:
        resolved_account = self.resolve_account_seq() if not (account_seq or self.account_seq) else str(account_seq or self.account_seq)
        payload = self._request_json("GET", "/api/v1/holdings", account_seq=resolved_account)
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        raw_items = result.get("items") if isinstance(result.get("items"), list) else []
        holdings = [normalize_toss_holding(item) for item in raw_items if isinstance(item, dict)]
        return {
            "status": "success",
            "broker": "TOSS",
            "account_seq": resolved_account,
            "api_path": "/api/v1/holdings",
            "holdings": [item for item in holdings if item.get("ticker")],
            "summary": result,
        }

    def fetch_orders(
        self,
        *,
        status: str,
        date_from: str | None = None,
        date_to: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Read order history only; this method never creates or mutates orders."""
        normalized_status = str(status or "").strip().upper()
        if normalized_status not in {"OPEN", "CLOSED"}:
            raise ValueError("토스 주문 이력 status는 OPEN 또는 CLOSED여야 합니다.")
        params: dict[str, str] = {"status": normalized_status}
        if date_from:
            params["from"] = str(date_from)
        if date_to:
            params["to"] = str(date_to)
        if symbol:
            params["symbol"] = str(symbol).strip().upper()
        if normalized_status == "CLOSED":
            params["limit"] = str(max(1, min(int(limit or 100), 100)))
            if cursor:
                params["cursor"] = str(cursor)
        resolved_account = self.resolve_account_seq()
        payload = self._request_json("GET", "/api/v1/orders", account_seq=resolved_account, params=params)
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        raw_orders = result.get("orders") if isinstance(result.get("orders"), list) else []
        return {
            "status": "success",
            "broker": "TOSS",
            "account_seq": resolved_account,
            "query": {"status": normalized_status, **{key: value for key, value in params.items() if key != "status"}},
            "orders": [normalize_toss_order(item) for item in raw_orders if isinstance(item, dict)],
            "next_cursor": result.get("nextCursor"),
            "has_next": bool(result.get("hasNext")),
        }
