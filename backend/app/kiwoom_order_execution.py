import time
from collections.abc import Callable

import httpx
from pydantic import BaseModel

from app.kiwoom_auth import KiwoomAuthClient
from app.kiwoom_balance import _clean_ticker, _to_int
from app.settings import Settings


class KiwoomOrderExecution(BaseModel):
    order_no: str | None = None
    original_order_no: str | None = None
    ticker: str | None = None
    name: str | None = None
    trade_side_name: str | None = None
    order_type_name: str | None = None
    order_status: str | None = None
    order_time: str | None = None
    confirm_time: str | None = None
    order_price: int | None = None
    order_quantity: int | None = None
    filled_price: int | None = None
    filled_quantity: int | None = None
    remaining_quantity: int | None = None
    stop_price: int | None = None
    exchange_type: str | None = None


class KiwoomOrderExecutionStatus(BaseModel):
    status: str
    base_url: str
    api_id: str
    executions_count: int
    executions: list[KiwoomOrderExecution]
    cont_yn: str | None = None
    has_next: bool = False
    return_code: int | None = None
    return_msg: str | None = None


class KiwoomOrderExecutionClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_client = KiwoomAuthClient(settings)

    def fetch_order_executions_raw(
        self,
        order_date: str = "",
        ticker: str = "",
        query_type: str = "4",
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
                "api-id": "kt00007",
            },
            json={
                "ord_dt": order_date,
                "qry_tp": query_type,
                "stk_bond_tp": "0",
                "sell_tp": "0",
                "stk_cd": ticker,
                "fr_ord_no": "",
                "dmst_stex_tp": "%",
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

    def fetch_order_execution_status(
        self,
        order_date: str = "",
        ticker: str = "",
        query_type: str = "4",
        max_pages: int = 10,
        page_checkpoint: Callable[[str, int, str], None] | None = None,
    ) -> KiwoomOrderExecutionStatus:
        raw, headers = self.fetch_order_executions_raw(
            order_date=order_date,
            ticker=ticker,
            query_type=query_type,
        )
        executions = [
            self._normalize_execution(item)
            for item in raw.get("acnt_ord_cntr_prps_dtl", [])
        ]
        cont_yn = headers.get("cont_yn")
        next_key = headers.get("next_key") or ""
        pages_read = 1
        if page_checkpoint:
            page_checkpoint("kt00007", pages_read, next_key)
        while cont_yn == "Y" and next_key and pages_read < max_pages:
            if self.settings.kiwoom_page_delay_seconds > 0:
                time.sleep(self.settings.kiwoom_page_delay_seconds)
            next_raw, headers = self.fetch_order_executions_raw(
                order_date=order_date,
                ticker=ticker,
                query_type=query_type,
                cont_yn="Y",
                next_key=next_key,
            )
            executions.extend(
                self._normalize_execution(item)
                for item in next_raw.get("acnt_ord_cntr_prps_dtl", [])
            )
            cont_yn = headers.get("cont_yn")
            next_key = headers.get("next_key") or ""
            pages_read += 1
            if page_checkpoint:
                page_checkpoint("kt00007", pages_read, next_key)

        return KiwoomOrderExecutionStatus(
            status="success",
            base_url=self.settings.kiwoom_api_base_url,
            api_id="kt00007",
            executions_count=len(executions),
            executions=executions,
            cont_yn=cont_yn,
            has_next=cont_yn == "Y" and bool(next_key),
            return_code=raw.get("return_code"),
            return_msg=raw.get("return_msg"),
        )

    def _normalize_execution(self, item: dict) -> KiwoomOrderExecution:
        return KiwoomOrderExecution(
            order_no=item.get("ord_no"),
            original_order_no=item.get("ori_ord"),
            ticker=_clean_ticker(item.get("stk_cd")),
            name=item.get("stk_nm"),
            trade_side_name=item.get("io_tp_nm") or item.get("trde_tp"),
            order_type_name=item.get("trde_tp"),
            order_status=item.get("acpt_tp"),
            order_time=item.get("ord_tm"),
            confirm_time=item.get("cnfm_tm"),
            order_price=_to_int(item.get("ord_uv")),
            order_quantity=_to_int(item.get("ord_qty")),
            filled_price=_to_int(item.get("cntr_uv")),
            filled_quantity=_to_int(item.get("cntr_qty")),
            remaining_quantity=_to_int(item.get("ord_remnq")),
            stop_price=_to_int(item.get("cond_uv")),
            exchange_type=item.get("dmst_stex_tp"),
        )
