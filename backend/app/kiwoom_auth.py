from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

from app.settings import Settings


class KiwoomTokenIssueResult(BaseModel):
    expires_dt: str
    token_type: str
    token: str
    refresh_token: str | None = None
    return_code: int | None = None
    return_msg: str | None = None


class KiwoomMaskedTokenStatus(BaseModel):
    status: str
    base_url: str
    source: str | None = None
    token_type: str | None = None
    expires_dt: str | None = None
    masked_token: str | None = None
    has_refresh_token: bool = False
    return_code: int | None = None
    return_msg: str | None = None


def _ensure_secret_ready(settings: Settings) -> None:
    if settings.brokerage_api_key == "********":
        raise ValueError("KIWOOM_API_KEY is not configured.")
    if settings.brokerage_api_secret == "********":
        raise ValueError("KIWOOM_API_SECRET is not configured.")


def _mask_token(token: str) -> str:
    if not token:
        return "********"
    if len(token) <= 12:
        return "********"
    return f"{token[:6]}****{token[-6:]}"


class KiwoomAuthClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def _environment(self) -> str:
        return "mock" if self.settings.kiwoom_use_mock else "prod"

    def issue_access_token(self, force_refresh: bool = False) -> KiwoomTokenIssueResult:
        if not force_refresh:
            cached_token = self._get_cached_access_token()
            if cached_token:
                return cached_token

        if self.settings.kiwoom_allow_refresh_token:
            refreshed_token = self._refresh_access_token_if_possible()
            if refreshed_token:
                return refreshed_token

        result = self._issue_new_access_token()
        self._save_token(result)
        return result

    def _issue_new_access_token(self) -> KiwoomTokenIssueResult:
        _ensure_secret_ready(self.settings)

        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}/oauth2/token",
            headers={"Content-Type": "application/json;charset=UTF-8"},
            json={
                "grant_type": "client_credentials",
                "appkey": self.settings.brokerage_api_key,
                "secretkey": self.settings.brokerage_api_secret,
            },
            timeout=10,
            trust_env=False,
        )
        response.raise_for_status()
        return KiwoomTokenIssueResult.model_validate(response.json())

    def _refresh_access_token_if_possible(self) -> KiwoomTokenIssueResult | None:
        from app.database import get_brokerage_token

        cached = get_brokerage_token(self.settings, "KIWOOM", self._environment)
        refresh_token = (cached or {}).get("refresh_token")
        if not refresh_token:
            return None

        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}/oauth2/token",
            headers={"Content-Type": "application/json;charset=UTF-8"},
            json={
                "grant_type": "refresh_token",
                "appkey": self.settings.brokerage_api_key,
                "secretkey": self.settings.brokerage_api_secret,
                "refresh_token": refresh_token,
            },
            timeout=10,
            trust_env=False,
        )
        if response.status_code in {400, 401, 403, 404}:
            return None
        response.raise_for_status()
        result = KiwoomTokenIssueResult.model_validate(response.json())
        self._save_token(result)
        return result

    def _get_cached_access_token(self) -> KiwoomTokenIssueResult | None:
        from app.database import get_brokerage_token, init_db

        init_db(self.settings)
        cached = get_brokerage_token(self.settings, "KIWOOM", self._environment)
        if not cached:
            return None
        if self._is_token_expiring(cached["expires_at"]):
            return None
        return KiwoomTokenIssueResult(
            expires_dt=cached["expires_dt"],
            token_type=cached["token_type"],
            token=cached["access_token"],
            refresh_token=cached.get("refresh_token"),
        )

    def _save_token(self, result: KiwoomTokenIssueResult) -> None:
        from app.database import init_db, upsert_brokerage_token

        init_db(self.settings)
        upsert_brokerage_token(
            settings=self.settings,
            broker="KIWOOM",
            environment=self._environment,
            token_type=result.token_type,
            access_token=result.token,
            refresh_token=result.refresh_token,
            expires_dt=result.expires_dt,
            expires_at=_kiwoom_expires_dt_to_iso(result.expires_dt),
        )

    def _is_token_expiring(self, expires_at: str) -> bool:
        expires = datetime.fromisoformat(expires_at)
        buffer = timedelta(seconds=max(self.settings.token_expiry_buffer_seconds, 0))
        return datetime.now() + buffer >= expires

    def issue_masked_token_status(self) -> KiwoomMaskedTokenStatus:
        from app.database import get_brokerage_token, init_db

        init_db(self.settings)
        before = get_brokerage_token(self.settings, "KIWOOM", self._environment)
        result = self.issue_access_token()
        after = get_brokerage_token(self.settings, "KIWOOM", self._environment)
        source = "cache" if before and after and before.get("access_token") == after.get("access_token") else "rotated"
        return KiwoomMaskedTokenStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            source=source,
            token_type=result.token_type,
            expires_dt=result.expires_dt,
            masked_token=_mask_token(result.token),
            has_refresh_token=bool(result.refresh_token),
            return_code=result.return_code,
            return_msg=result.return_msg,
        )


def _kiwoom_expires_dt_to_iso(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").isoformat()
    except ValueError:
        return (datetime.now() + timedelta(hours=20)).isoformat()
