import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel

from app.kiwoom_auth import KiwoomAuthClient
from app.kiwoom_balance import _clean_ticker, _to_float, _to_int
from app.settings import Settings


class KiwoomTradeJournalItem(BaseModel):
    ticker: str | None = None
    name: str | None = None
    buy_average_price: int | None = None
    buy_quantity: int | None = None
    sell_average_price: int | None = None
    sell_quantity: int | None = None
    commission_and_tax: int | None = None
    profit_loss_amount: int | None = None
    sell_amount: int | None = None
    buy_amount: int | None = None
    profit_rate: float | None = None


class KiwoomTradeJournalSummary(BaseModel):
    total_sell_amount: int | None = None
    total_buy_amount: int | None = None
    total_commission_and_tax: int | None = None
    total_execution_amount: int | None = None
    total_profit_loss_amount: int | None = None
    total_profit_rate: float | None = None


class KiwoomTradeJournalStatus(BaseModel):
    status: str
    base_url: str
    api_id: str
    base_date: str
    summary: KiwoomTradeJournalSummary
    items_count: int
    items: list[KiwoomTradeJournalItem]
    cont_yn: str | None = None
    has_next: bool = False
    return_code: int | None = None
    return_msg: str | None = None


class KiwoomTradeJournalClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_client = KiwoomAuthClient(settings)

    def fetch_today_trade_journal_raw(
        self,
        base_date: str = "",
        cont_yn: str = "N",
        next_key: str = "",
    ) -> tuple[dict, dict]:
        token = self.auth_client.issue_access_token()
        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}/api/dostk/acnt",
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token.token}",
                "cont-yn": cont_yn,
                "next-key": next_key,
                "api-id": "ka10170",
            },
            json={
                "base_dt": base_date,
                "ottks_tp": "1",
                "ch_crd_tp": "0",
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

    def fetch_today_trade_journal_status(
        self,
        base_date: str = "",
        max_pages: int = 10,
        page_checkpoint: Callable[[str, int, str], None] | None = None,
    ) -> KiwoomTradeJournalStatus:
        raw, headers = self.fetch_today_trade_journal_raw(base_date=base_date)
        items = [
            item
            for item in (
                self._normalize_item(raw_item)
                for raw_item in raw.get("tdy_trde_diary", [])
            )
            if not self._is_empty_item(item)
        ]
        cont_yn = headers.get("cont_yn")
        next_key = headers.get("next_key") or ""
        pages_read = 1
        if page_checkpoint:
            page_checkpoint("ka10170", pages_read, next_key)
        while cont_yn == "Y" and next_key and pages_read < max_pages:
            if self.settings.kiwoom_page_delay_seconds > 0:
                time.sleep(self.settings.kiwoom_page_delay_seconds)
            next_raw, headers = self.fetch_today_trade_journal_raw(
                base_date=base_date,
                cont_yn="Y",
                next_key=next_key,
            )
            items.extend(
                item
                for item in (
                    self._normalize_item(raw_item)
                    for raw_item in next_raw.get("tdy_trde_diary", [])
                )
                if not self._is_empty_item(item)
            )
            cont_yn = headers.get("cont_yn")
            next_key = headers.get("next_key") or ""
            pages_read += 1
            if page_checkpoint:
                page_checkpoint("ka10170", pages_read, next_key)

        return KiwoomTradeJournalStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            api_id="ka10170",
            base_date=base_date or "TODAY",
            summary=KiwoomTradeJournalSummary(
                total_sell_amount=_to_int(raw.get("tot_sell_amt")),
                total_buy_amount=_to_int(raw.get("tot_buy_amt")),
                total_commission_and_tax=_to_int(raw.get("tot_cmsn_tax")),
                total_execution_amount=_to_int(raw.get("tot_exct_amt")),
                total_profit_loss_amount=_to_int(raw.get("tot_pl_amt")),
                total_profit_rate=_to_float(raw.get("tot_prft_rt")),
            ),
            items_count=len(items),
            items=items,
            cont_yn=cont_yn,
            has_next=cont_yn == "Y" and bool(next_key),
            return_code=raw.get("return_code"),
            return_msg=raw.get("return_msg"),
        )

    def _normalize_item(self, item: dict) -> KiwoomTradeJournalItem:
        return KiwoomTradeJournalItem(
            ticker=_clean_ticker(item.get("stk_cd")),
            name=item.get("stk_nm"),
            buy_average_price=_to_int(item.get("buy_avg_pric")),
            buy_quantity=_to_int(item.get("buy_qty")),
            sell_average_price=_to_int(item.get("sel_avg_pric")),
            sell_quantity=_to_int(item.get("sell_qty")),
            commission_and_tax=_to_int(item.get("cmsn_alm_tax")),
            profit_loss_amount=_to_int(item.get("pl_amt")),
            sell_amount=_to_int(item.get("sell_amt")),
            buy_amount=_to_int(item.get("buy_amt")),
            profit_rate=_to_float(item.get("prft_rt")),
        )

    def _is_empty_item(self, item: KiwoomTradeJournalItem) -> bool:
        return not any(
            [
                item.ticker,
                (item.name or "").strip(),
                item.buy_quantity,
                item.sell_quantity,
                item.buy_amount,
                item.sell_amount,
                item.profit_loss_amount,
            ]
        )
