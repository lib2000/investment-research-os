"""Kiwoom REST interest group helpers."""

from __future__ import annotations

from typing import Any

import httpx

from research_os.kiwoom_auth import KiwoomAuthClient
from research_os.settings import Settings


GROUP_LIST_API_ID = "ka01300"
GROUP_DETAIL_API_ID = "ka01301"


def _first_value(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _candidate_rows(payload: Any, keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _candidate_rows(value, keys)
            if nested:
                return nested
    for value in payload.values():
        nested = _candidate_rows(value, keys)
        if nested:
            return nested
    return []


def _clean_ticker(value: Any) -> str:
    return str(value or "").strip().upper().lstrip("A")


def _normalize_group(row: dict[str, Any]) -> dict[str, Any]:
    group_id = _first_value(
        row,
        [
            "grp_no",
            "grpNo",
            "group_no",
            "groupNo",
            "grp_id",
            "group_id",
            "관심그룹번호",
            "관심종목그룹번호",
        ],
    )
    group_name = _first_value(
        row,
        [
            "grp_nm",
            "grpName",
            "group_name",
            "groupName",
            "name",
            "관심그룹명",
            "관심종목그룹명",
        ],
    )
    return {
        "group_id": str(group_id or "").strip(),
        "group_name": str(group_name or "").strip() or "관심그룹명 확인 필요",
        "raw": row,
    }


def _normalize_item(row: dict[str, Any]) -> dict[str, Any]:
    ticker = _first_value(row, ["stk_cd", "stkCd", "code", "ticker", "종목코드"])
    name = _first_value(row, ["stk_nm", "stkNm", "name", "company_name", "종목명"])
    return {
        "ticker": _clean_ticker(ticker),
        "company_name": str(name or "").strip(),
        "raw": row,
    }


class KiwoomInterestClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_client = KiwoomAuthClient(settings)

    def _post(self, api_id: str, body: dict[str, Any]) -> dict[str, Any]:
        token = self.auth_client.issue_access_token()
        response = httpx.post(
            f"{self.settings.kiwoom_api_base_url}{self.settings.kiwoom_interest_endpoint_path}",
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {token.token}",
                "cont-yn": "N",
                "next-key": "",
                "api-id": api_id,
            },
            json=body,
            timeout=10,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"raw": payload}

    def fetch_group_list_raw(self) -> dict[str, Any]:
        return self._post(GROUP_LIST_API_ID, {})

    def fetch_group_detail_raw(self, group_id: str, request_body: dict[str, Any] | None = None) -> dict[str, Any]:
        body = dict(request_body or {})
        if group_id and not body:
            body["grp_no"] = group_id
        return self._post(GROUP_DETAIL_API_ID, body)


def normalize_kiwoom_interest_groups(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _candidate_rows(
        raw,
        [
            "atn_stk_grp",
            "atn_stk_grplist",
            "atn_stk_group",
            "grp_list",
            "group_list",
            "groups",
            "list",
            "output",
        ],
    )
    return [_normalize_group(row) for row in rows]


def normalize_kiwoom_interest_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _candidate_rows(
        raw,
        [
            "atn_stk",
            "atn_stk_list",
            "stk_list",
            "item_list",
            "items",
            "list",
            "output",
        ],
    )
    return [
        item
        for item in (_normalize_item(row) for row in rows)
        if item["ticker"] or item["company_name"]
    ]


def build_kiwoom_interest_groups_status(
    settings: Settings,
    *,
    include_details: bool = False,
    max_groups: int = 20,
) -> dict[str, Any]:
    client = KiwoomInterestClient(settings)
    raw_groups = client.fetch_group_list_raw()
    groups = normalize_kiwoom_interest_groups(raw_groups)
    selected_groups = groups[: max(0, min(int(max_groups or 20), 100))]
    details = []
    if include_details:
        for group in selected_groups:
            group_id = group.get("group_id") or ""
            raw_detail = client.fetch_group_detail_raw(group_id)
            details.append(
                {
                    "group_id": group_id,
                    "group_name": group.get("group_name"),
                    "item_count": len(normalize_kiwoom_interest_items(raw_detail)),
                    "items": normalize_kiwoom_interest_items(raw_detail),
                    "raw_response_keys": sorted(raw_detail.keys()),
                }
            )
    return {
        "status": "success",
        "module": "kiwoom_interest_groups",
        "api_ids": [GROUP_LIST_API_ID, GROUP_DETAIL_API_ID],
        "base_url": settings.kiwoom_api_base_url,
        "endpoint_path": settings.kiwoom_interest_endpoint_path,
        "include_details": include_details,
        "group_count": len(groups),
        "groups": selected_groups,
        "details": details,
        "raw_response_keys": sorted(raw_groups.keys()),
    }
