from datetime import datetime, timedelta
import json
from pathlib import Path

import httpx
from pydantic import BaseModel

from research_os.settings import Settings


class KiwoomTokenIssueResult(BaseModel):
    expires_dt: str
    token_type: str
    token: str
    return_code: int | None = None
    return_msg: str | None = None


class KiwoomMaskedTokenStatus(BaseModel):
    status: str
    base_url: str
    source: str | None = None
    token_type: str | None = None
    expires_dt: str | None = None
    masked_token: str | None = None
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
            cached = self._read_cached_access_token()
            if cached:
                return cached
        return self._issue_new_access_token()

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
        result = KiwoomTokenIssueResult.model_validate(response.json())
        self._write_cached_access_token(result)
        return result

    def _resolve_cache_path(self) -> Path:
        path = Path(self.settings.kiwoom_token_cache_file)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[1] / path).resolve()

    def _read_cached_access_token(self) -> KiwoomTokenIssueResult | None:
        try:
            path = self._resolve_cache_path()
            if not path.exists() or not path.is_file():
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("broker") != "KIWOOM" or payload.get("environment") != self._environment:
            return None
        token = str(payload.get("token") or "").strip()
        expires_dt = str(payload.get("expires_dt") or "").strip()
        token_type = str(payload.get("token_type") or "Bearer").strip() or "Bearer"
        if not token or not expires_dt:
            return None
        if self._is_token_expiring(expires_dt):
            return None
        return KiwoomTokenIssueResult(
            expires_dt=expires_dt,
            token_type=token_type,
            token=token,
            return_code=payload.get("return_code"),
            return_msg=payload.get("return_msg"),
        )

    def _write_cached_access_token(self, result: KiwoomTokenIssueResult) -> None:
        try:
            path = self._resolve_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "broker": "KIWOOM",
                        "environment": self._environment,
                        "token_type": result.token_type,
                        "token": result.token,
                        "expires_dt": result.expires_dt,
                        "return_code": result.return_code,
                        "return_msg": result.return_msg,
                        "updated_at": datetime.now().replace(microsecond=0).isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            return

    def _is_token_expiring(self, expires_dt: str) -> bool:
        try:
            expires = datetime.strptime(expires_dt, "%Y%m%d%H%M%S")
        except ValueError:
            return True
        buffer = timedelta(seconds=max(int(self.settings.kiwoom_token_expiry_buffer_seconds or 0), 0))
        return datetime.now() + buffer >= expires

    def issue_masked_token_status(self) -> KiwoomMaskedTokenStatus:
        before = self._read_cached_access_token()
        result = self.issue_access_token()
        return KiwoomMaskedTokenStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            source="cache" if before and before.token == result.token else "rotated",
            token_type=result.token_type,
            expires_dt=result.expires_dt,
            masked_token=_mask_token(result.token),
            return_code=result.return_code,
            return_msg=result.return_msg,
        )
