from typing import Any

import httpx
from pydantic import BaseModel

from app.kiwoom_auth import KiwoomAuthClient
from app.settings import Settings


class KiwoomHolding(BaseModel):
    ticker: str | None = None
    name: str | None = None
    quantity: int | None = None
    available_quantity: int | None = None
    average_price: int | None = None
    current_price: int | None = None
    purchase_amount: int | None = None
    evaluation_amount: int | None = None
    evaluation_profit_loss: int | None = None
    profit_rate: float | None = None


class KiwoomBalanceSummary(BaseModel):
    total_purchase_amount: int | None = None
    total_evaluation_amount: int | None = None
    total_evaluation_profit_loss: int | None = None
    total_profit_rate: float | None = None
    estimated_deposit_asset_amount: int | None = None


class KiwoomBalanceStatus(BaseModel):
    status: str
    base_url: str
    api_id: str
    summary: KiwoomBalanceSummary
    holdings_count: int
    holdings: list[KiwoomHolding]
    cont_yn: str | None = None
    has_next: bool = False
    return_code: int | None = None
    return_msg: str | None = None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    if not text.isdigit():
        return None
    return sign * int(text)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_ticker(value: Any) -> str | None:
    if value is None:
        return None
    ticker = str(value).strip().lstrip("A")
    return ticker or None


class KiwoomBalanceClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_client = KiwoomAuthClient(settings)

    def fetch_balance_raw(self, cont_yn: str = "N", next_key: str = "") -> tuple[dict, dict]:
        token = self.auth_client.issue_access_token()
        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}/api/dostk/acnt",
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token.token}",
                "cont-yn": cont_yn,
                "next-key": next_key,
                "api-id": "kt00018",
            },
            json={
                "qry_tp": "1",
                "dmst_stex_tp": "KRX",
            },
            timeout=10,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json(), {
            "cont_yn": response.headers.get("cont-yn"),
            "next_key": response.headers.get("next-key"),
            "api_id": response.headers.get("api-id"),
        }

    def fetch_balance_status(self) -> KiwoomBalanceStatus:
        raw, headers = self.fetch_balance_raw()
        holdings = [self._normalize_holding(item) for item in raw.get("acnt_evlt_remn_indv_tot", [])]
        cont_yn = headers.get("cont_yn")
        return KiwoomBalanceStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            api_id="kt00018",
            summary=KiwoomBalanceSummary(
                total_purchase_amount=_to_int(raw.get("tot_pur_amt")),
                total_evaluation_amount=_to_int(raw.get("tot_evlt_amt")),
                total_evaluation_profit_loss=_to_int(raw.get("tot_evlt_pl")),
                total_profit_rate=_to_float(raw.get("tot_prft_rt")),
                estimated_deposit_asset_amount=_to_int(raw.get("prsm_dpst_aset_amt")),
            ),
            holdings_count=len(holdings),
            holdings=holdings,
            cont_yn=cont_yn,
            has_next=cont_yn == "Y",
            return_code=raw.get("return_code"),
            return_msg=raw.get("return_msg"),
        )

    def _normalize_holding(self, item: dict) -> KiwoomHolding:
        return KiwoomHolding(
            ticker=_clean_ticker(item.get("stk_cd")),
            name=item.get("stk_nm"),
            quantity=_to_int(item.get("rmnd_qty")),
            available_quantity=_to_int(item.get("trde_able_qty")),
            average_price=_to_int(item.get("pur_pric")),
            current_price=_to_int(item.get("cur_prc")),
            purchase_amount=_to_int(item.get("pur_amt")),
            evaluation_amount=_to_int(item.get("evlt_amt")),
            evaluation_profit_loss=_to_int(item.get("evltv_prft")),
            profit_rate=_to_float(item.get("prft_rt")),
        )
