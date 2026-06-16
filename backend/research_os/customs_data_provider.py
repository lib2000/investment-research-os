"""Korea Customs trade API client and row normalization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import re
import threading
import xml.etree.ElementTree as ET

import httpx

from research_os.data_provider_utils import (
    _first_value,
    _is_configured_secret,
    _parse_float_value,
    _safe_provider_error,
)
from research_os.settings import Settings

_CUSTOMS_TRADE_CACHE_LOCK = threading.Lock()
_CUSTOMS_TRADE_MEMORY_CACHE: dict[str, dict] = {}
_CUSTOMS_TRADE_MEMORY_TTL_SECONDS = 6 * 60 * 60
CUSTOMS_DEFAULT_COUNTRY_CODES = ["US", "CN", "JP", "VN", "HK", "TW", "SG", "DE", "IN"]


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