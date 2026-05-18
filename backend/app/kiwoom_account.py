from typing import Any

import httpx
from pydantic import BaseModel

from app.kiwoom_auth import KiwoomAuthClient
from app.privacy import account_ref, mask_account
from app.settings import Settings


class KiwoomMaskedAccountsStatus(BaseModel):
    status: str
    base_url: str
    api_id: str
    masked_accounts: list[str]
    account_refs: list[dict]
    raw_response_keys: list[str]
    return_code: int | None = None
    return_msg: str | None = None


def _mask_account_no(account_no: str) -> str:
    return mask_account(account_no)


def _collect_account_numbers(value: Any) -> list[str]:
    account_keys = {
        "acctNo",
        "acct_no",
        "account_no",
        "acnt_no",
        "acntNo",
        "accno",
        "계좌번호",
    }
    found: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key in account_keys and item:
                found.append(str(item))
            found.extend(_collect_account_numbers(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_account_numbers(item))

    return found


class KiwoomAccountClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_client = KiwoomAuthClient(settings)

    def fetch_accounts_raw(self) -> dict:
        token = self.auth_client.issue_access_token()
        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}/api/dostk/acnt",
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token.token}",
                "cont-yn": "N",
                "next-key": "",
                "api-id": "ka00001",
            },
            json={},
            timeout=10,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json()

    def fetch_masked_accounts_status(self) -> KiwoomMaskedAccountsStatus:
        raw = self.fetch_accounts_raw()
        accounts = _collect_account_numbers(raw)
        refs_by_hash = {
            account_ref(account, self.settings.secret_salt)["account_hash"]: account_ref(
                account,
                self.settings.secret_salt,
            )
            for account in accounts
        }
        account_refs = sorted(
            refs_by_hash.values(),
            key=lambda item: item["masked_account"],
        )
        return KiwoomMaskedAccountsStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            api_id="ka00001",
            masked_accounts=[item["masked_account"] for item in account_refs],
            account_refs=account_refs,
            raw_response_keys=sorted(raw.keys()),
            return_code=raw.get("return_code"),
            return_msg=raw.get("return_msg"),
        )
