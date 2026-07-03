"""Kiwoom REST interest group helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from research_os.kiwoom_auth import KiwoomAuthClient
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


GROUP_LIST_API_ID = "ka01300"
GROUP_DETAIL_API_ID = "ka01301"


def _current_history_timestamp() -> str:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))
    return datetime.now(korea_timezone).isoformat(timespec="seconds")


def kiwoom_interest_sync_history_path(settings: Settings) -> Path:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "kiwoom_interest_sync_history.jsonl"


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
    raw = str(value or "").strip().upper()
    return raw[1:] if raw.startswith("A") and raw[1:].isdigit() else raw


def _ticker_key(value: Any) -> str:
    return _clean_ticker(value)


def is_standard_domestic_stock_ticker(value: Any) -> bool:
    ticker = _ticker_key(value)
    if ticker in {"", "UNKNOWN", "CASH"}:
        return False
    return bool(re.fullmatch(r"[0-9A-Z]{6}", ticker)) and any(ch.isdigit() for ch in ticker)


def is_kiwoom_buy_interest_group(value: Any) -> bool:
    group_name = str(value or "").strip()
    if not group_name:
        return False
    return "매수" in group_name and "매도" not in group_name


def _resolved_company_name(
    ticker: str,
    fallback: str,
    resolver: Callable[[str], Any] | None,
) -> str:
    if not ticker or not resolver:
        return fallback
    try:
        resolved = resolver(ticker)
    except Exception:
        return fallback
    if isinstance(resolved, tuple) and len(resolved) >= 2:
        resolved = resolved[1]
    if isinstance(resolved, dict):
        return str(resolved.get("company_name") or fallback).strip()
    return str(getattr(resolved, "company_name", "") or fallback).strip()


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
            "gcod",
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
    ticker = _first_value(row, ["stk_cd", "stkCd", "cod2", "code", "ticker", "종목코드"])
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
            body["arn_grp_id"] = group_id
        return self._post(GROUP_DETAIL_API_ID, body)


def normalize_kiwoom_interest_groups(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _candidate_rows(
        raw,
        [
            "atn_stk_grp",
            "nofi",
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
            "nofj",
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


def build_kiwoom_interest_sync_preview(
    status_payload: dict[str, Any],
    interest_payload: dict[str, Any] | None,
    *,
    ticker_resolver: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Compare Kiwoom interest details with the local interest list without writing changes."""

    existing_tickers = {
        _ticker_key(item.get("ticker"))
        for item in (interest_payload or {}).get("tickers", [])
        if isinstance(item, dict) and _ticker_key(item.get("ticker"))
    }
    candidates: list[dict[str, Any]] = []
    seen_candidate_keys: set[str] = set()
    for detail in status_payload.get("details") or []:
        if not isinstance(detail, dict):
            continue
        group_id = str(detail.get("group_id") or "").strip()
        group_name = str(detail.get("group_name") or "").strip()
        for item in detail.get("items") or []:
            if not isinstance(item, dict):
                continue
            ticker = _ticker_key(item.get("ticker"))
            company_name = _resolved_company_name(
                ticker,
                str(item.get("company_name") or "").strip(),
                ticker_resolver,
            )
            candidate_key = ticker or company_name.lower()
            if not candidate_key or candidate_key in seen_candidate_keys:
                continue
            seen_candidate_keys.add(candidate_key)
            already_tracked = bool(ticker and ticker in existing_tickers)
            standard_domestic_stock = is_standard_domestic_stock_ticker(ticker)
            buy_group = is_kiwoom_buy_interest_group(group_name)
            if not standard_domestic_stock:
                action = "needs_review"
                reason = "키움 국내 6자리 종목/상품 코드 형식이 아니라 자동 저장 전 확인이 필요합니다."
            elif not buy_group:
                action = "needs_review"
                reason = "매수 관심그룹이 아니라 자동 저장 대상에서 제외했습니다."
            elif already_tracked:
                action = "already_tracked"
                reason = "이미 로컬 관심종목에 등록되어 있습니다."
            else:
                action = "add_candidate"
                reason = "키움 매수 관심그룹에는 있으나 로컬 관심종목에는 없어 추가 후보입니다."
            candidates.append(
                {
                    "ticker": ticker,
                    "company_name": company_name,
                    "group_id": group_id,
                    "group_name": group_name,
                    "ticker_quality": (
                        "kiwoom_domestic_instrument"
                        if standard_domestic_stock
                        else "needs_review"
                    ),
                    "buy_group": buy_group,
                    "sync_eligible": action == "add_candidate",
                    "action": action,
                    "reason": reason,
                }
            )
    add_candidates = [item for item in candidates if item.get("action") == "add_candidate"]
    already_tracked = [item for item in candidates if item.get("action") == "already_tracked"]
    needs_review = [item for item in candidates if item.get("action") == "needs_review"]
    outside_buy_group = [item for item in candidates if not item.get("buy_group")]
    return {
        "status": "success",
        "module": "kiwoom_interest_sync_preview",
        "write_mode": "preview_only",
        "existing_local_ticker_count": len(existing_tickers),
        "kiwoom_candidate_count": len(candidates),
        "add_candidate_count": len(add_candidates),
        "already_tracked_count": len(already_tracked),
        "needs_review_count": len(needs_review),
        "outside_buy_group_count": len(outside_buy_group),
        "candidates": candidates,
        "next_action": (
            "추가 후보를 검토한 뒤 /api/v1/interests/tickers 또는 콘솔 관심종목 저장으로 반영하세요."
            if add_candidates
            else "비표준 코드는 확인 필요로 분리했습니다. 저장할 신규 키움 국내 종목/상품 후보는 없습니다."
            if needs_review
            else "키움 관심그룹과 로컬 관심종목의 티커 기준 차이가 없습니다."
        ),
    }


def append_kiwoom_interest_sync_history(
    settings: Settings,
    *,
    summary: dict[str, Any],
) -> None:
    path = kiwoom_interest_sync_history_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": _current_history_timestamp(),
        "broker": "KIWOOM",
        "module": summary.get("module") or "kiwoom_interest_sync",
        "mode": "dry_run" if summary.get("dry_run") else "apply",
        "write_mode": summary.get("write_mode"),
        "requested_count": summary.get("requested_count", 0),
        "prepared_count": summary.get("prepared_count", 0),
        "skipped_count": summary.get("skipped_count", 0),
        "interest_ticker_count": summary.get("interest_ticker_count", 0),
        "prepared_tickers": summary.get("prepared_tickers", []),
        "skipped": summary.get("skipped", []),
        "message": summary.get("next_action"),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def read_kiwoom_interest_sync_history(settings: Settings, *, limit: int = 10) -> list[dict[str, Any]]:
    path = kiwoom_interest_sync_history_path(settings)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
        if len(records) >= limit:
            break
    return records
