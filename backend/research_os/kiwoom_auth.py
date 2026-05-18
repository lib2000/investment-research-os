from pydantic import BaseModel
import httpx

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

    def issue_access_token(self) -> KiwoomTokenIssueResult:
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
        )
        response.raise_for_status()
        return KiwoomTokenIssueResult.model_validate(response.json())

    def issue_masked_token_status(self) -> KiwoomMaskedTokenStatus:
        result = self.issue_access_token()
        return KiwoomMaskedTokenStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            token_type=result.token_type,
            expires_dt=result.expires_dt,
            masked_token=_mask_token(result.token),
            return_code=result.return_code,
            return_msg=result.return_msg,
        )
