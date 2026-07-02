"""Firecrawl Monitor event normalization and storage helpers."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any
from urllib.parse import urlparse

from research_os.state_store import (
    current_storage_timestamp,
    firecrawl_monitor_events_path,
    firecrawl_monitor_webhook_status_path,
    read_json_store,
    write_json_store,
)

DESIGN_NAME = "firecrawl_monitor_events_v1"
MAX_STORED_EVENTS = 500
MAX_RECENT_EVENTS = 50
MONITOR_PAGE_EVENT = "monitor.page"
MONITOR_CHECK_COMPLETED_EVENT = "monitor.check.completed"


def _settings_str(settings: Any, name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or "").strip()


def _compact_text(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _payload_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return _list_of_dicts(data)
    if isinstance(data, dict):
        return [data]
    if isinstance(payload.get("pages"), list):
        return _list_of_dicts(payload["pages"])
    return [payload]


def _event_type(payload: dict[str, Any], item: dict[str, Any]) -> str:
    return str(
        item.get("type")
        or item.get("event")
        or payload.get("type")
        or payload.get("event")
        or MONITOR_PAGE_EVENT
    ).strip()


def _monitor_id(payload: dict[str, Any], item: dict[str, Any]) -> str:
    monitor = item.get("monitor") if isinstance(item.get("monitor"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return _compact_text(
        item.get("monitorId")
        or item.get("monitor_id")
        or monitor.get("id")
        or payload.get("monitorId")
        or payload.get("monitor_id")
        or metadata.get("monitorId")
        or metadata.get("monitor_id"),
        120,
    )


def _check_id(payload: dict[str, Any], item: dict[str, Any]) -> str:
    return _compact_text(
        item.get("checkId")
        or item.get("check_id")
        or payload.get("checkId")
        or payload.get("check_id")
        or payload.get("id"),
        120,
    )


def _source_url(item: dict[str, Any]) -> str:
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    return _compact_text(item.get("url") or item.get("sourceUrl") or source.get("url"), 500)


def firecrawl_monitor_event_id(
    *,
    event_type: str,
    monitor_id: str,
    check_id: str,
    url: str,
    status: str,
    diff_text: str = "",
) -> str:
    seed = "|".join([event_type, monitor_id, check_id, url, status, diff_text[:220]])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def route_hint_for_monitor_event(event: dict[str, Any]) -> dict[str, Any]:
    url = str(event.get("url") or "")
    host = (urlparse(url).hostname or "").lower()
    haystack = " ".join(
        str(value or "")
        for value in [
            host,
            url,
            event.get("title"),
            event.get("summary"),
            event.get("diff_text"),
            event.get("status"),
        ]
    ).lower()
    if any(token in haystack for token in ["fsc.go.kr", "fss.or.kr", "korea.kr", "law.go.kr", "ftc.go.kr"]):
        return {
            "target": "policy_news_inbox_candidate",
            "scope": "POLICY",
            "reason": "policy_or_regulatory_source",
            "next_action": "정책/법령 변경 후보로 뉴스 인박스 검토 대상에 올리세요.",
        }
    if any(token in haystack for token in ["sec.gov", "investor", "investors", "ir.", "press-release", "10-k", "8-k"]):
        return {
            "target": "public_ir_sec_candidate",
            "scope": "PUBLIC_IR_SEC",
            "reason": "public_ir_or_sec_source",
            "next_action": "공개 IR/SEC 수집 후보로 저장하고 보유/관심 종목 연결 여부를 확인하세요.",
        }
    if event.get("is_meaningful") or event.get("status") in {"new", "changed"}:
        return {
            "target": "market_journal_candidate",
            "scope": "MARKET",
            "reason": "meaningful_monitor_change",
            "next_action": "시장 일지 또는 오늘 추천 근거 후보로 검토하세요.",
        }
    return {
        "target": "monitor_archive",
        "scope": "SYSTEM",
        "reason": "monitor_event_record",
        "next_action": "변경 이력으로 보관하고 필요 시 수동 검토하세요.",
    }


def _meaningful_changes(judgment: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    changes = (
        judgment.get("meaningfulChanges")
        or judgment.get("meaningful_changes")
        or item.get("meaningfulChanges")
        or item.get("meaningful_changes")
    )
    normalized: list[dict[str, Any]] = []
    for change in _list_of_dicts(changes):
        normalized.append(
            {
                "type": _compact_text(change.get("type") or change.get("kind"), 80),
                "summary": _compact_text(change.get("summary") or change.get("after") or change.get("text"), 260),
            }
        )
    return normalized[:10]


def _normalize_page_event(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    judgment = item.get("judgment") if isinstance(item.get("judgment"), dict) else {}
    diff = item.get("diff") if isinstance(item.get("diff"), dict) else {}
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    snapshot = item.get("snapshot") if isinstance(item.get("snapshot"), dict) else {}
    event_type = _event_type(payload, item)
    monitor_id = _monitor_id(payload, item)
    check_id = _check_id(payload, item)
    url = _source_url(item)
    status = _compact_text(item.get("status") or item.get("changeStatus") or "unknown", 40).lower()
    diff_text = _compact_text(diff.get("text") or item.get("diffText") or item.get("diff_text"), 1200)
    changes = _meaningful_changes(judgment, item)
    is_meaningful = bool(
        item.get("isMeaningful")
        or item.get("is_meaningful")
        or judgment.get("meaningful")
        or changes
    )
    summary = _compact_text(
        judgment.get("reason")
        or item.get("summary")
        or (changes[0]["summary"] if changes else "")
        or diff_text,
        360,
    )
    event = {
        "event_id": firecrawl_monitor_event_id(
            event_type=event_type,
            monitor_id=monitor_id,
            check_id=check_id,
            url=url,
            status=status,
            diff_text=diff_text,
        ),
        "event_type": event_type,
        "monitor_id": monitor_id,
        "check_id": check_id,
        "url": url,
        "status": status,
        "title": _compact_text(metadata.get("title") or item.get("title"), 180),
        "summary": summary,
        "is_meaningful": is_meaningful,
        "judgment": {
            "meaningful": is_meaningful,
            "confidence": _compact_text(judgment.get("confidence"), 80),
            "reason": _compact_text(judgment.get("reason"), 360),
        },
        "meaningful_changes": changes,
        "diff_text": diff_text,
        "previous_scrape_id": _compact_text(item.get("previousScrapeId") or item.get("previous_scrape_id"), 120),
        "current_scrape_id": _compact_text(item.get("currentScrapeId") or item.get("current_scrape_id"), 120),
        "snapshot_json": snapshot.get("json") if isinstance(snapshot.get("json"), dict) else None,
        "error": _compact_text(item.get("error") or item.get("errorMessage"), 500),
        "received_at": current_storage_timestamp(),
    }
    event["route_hint"] = route_hint_for_monitor_event(event)
    return event


def _normalize_check_event(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    event_type = _event_type(payload, item)
    monitor_id = _monitor_id(payload, item)
    check_id = _check_id(payload, item)
    summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
    status = _compact_text(item.get("status") or summary.get("status") or "completed", 40).lower()
    event = {
        "event_id": firecrawl_monitor_event_id(
            event_type=event_type,
            monitor_id=monitor_id,
            check_id=check_id,
            url="",
            status=status,
        ),
        "event_type": event_type,
        "monitor_id": monitor_id,
        "check_id": check_id,
        "url": "",
        "status": status,
        "title": _compact_text(item.get("name") or "Firecrawl monitor check completed", 180),
        "summary": _compact_text(summary.get("message") or item.get("message") or "Monitor check completed", 360),
        "is_meaningful": bool(summary.get("changed") or summary.get("new") or summary.get("errors")),
        "judgment": {"meaningful": bool(summary.get("changed") or summary.get("new") or summary.get("errors"))},
        "meaningful_changes": [],
        "diff_text": "",
        "counts": {
            "pages": int(summary.get("pages") or item.get("pages") or 0),
            "new": int(summary.get("new") or 0),
            "changed": int(summary.get("changed") or 0),
            "removed": int(summary.get("removed") or 0),
            "errors": int(summary.get("errors") or 0),
        },
        "error": _compact_text(item.get("error") or summary.get("error"), 500),
        "received_at": current_storage_timestamp(),
    }
    event["route_hint"] = route_hint_for_monitor_event(event)
    return event


def normalize_firecrawl_monitor_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Firecrawl Monitor payload must be a JSON object.")
    events: list[dict[str, Any]] = []
    items = _payload_items(payload)
    default_type = str(payload.get("type") or payload.get("event") or "").strip()
    for item in items:
        event_type = _event_type(payload, item)
        if event_type == MONITOR_CHECK_COMPLETED_EVENT or default_type == MONITOR_CHECK_COMPLETED_EVENT:
            events.append(_normalize_check_event(payload, item))
        else:
            events.append(_normalize_page_event(payload, item))
    return {
        "status": "success",
        "module": DESIGN_NAME,
        "event_count": len(events),
        "meaningful_count": sum(1 for event in events if event.get("is_meaningful")),
        "events": events,
    }


def read_firecrawl_monitor_event_store(settings: Any) -> dict[str, Any]:
    return read_json_store(
        firecrawl_monitor_events_path(settings),
        {"module": DESIGN_NAME, "updated_at": None, "events": [], "summary": {}},
    )


def _store_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_route: dict[str, int] = {}
    for event in events:
        status = str(event.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        route = event.get("route_hint") if isinstance(event.get("route_hint"), dict) else {}
        target = str(route.get("target") or "unknown")
        by_route[target] = by_route.get(target, 0) + 1
    return {
        "event_count": len(events),
        "meaningful_count": sum(1 for event in events if event.get("is_meaningful")),
        "error_count": sum(1 for event in events if event.get("error") or event.get("status") == "error"),
        "by_status": by_status,
        "by_route": by_route,
        "latest_received_at": events[0].get("received_at") if events else None,
    }


def upsert_firecrawl_monitor_events(settings: Any, events: list[dict[str, Any]]) -> dict[str, Any]:
    store = read_firecrawl_monitor_event_store(settings)
    existing = [item for item in store.get("events", []) if isinstance(item, dict)]
    by_id: dict[str, dict[str, Any]] = {}
    for event in existing:
        event_id = str(event.get("event_id") or "")
        if event_id:
            by_id[event_id] = event
    saved_count = 0
    for event in events:
        event_id = str(event.get("event_id") or "")
        if not event_id:
            continue
        if event_id not in by_id:
            saved_count += 1
        by_id[event_id] = event
    merged = sorted(
        by_id.values(),
        key=lambda item: str(item.get("received_at") or ""),
        reverse=True,
    )[:MAX_STORED_EVENTS]
    next_store = {
        "module": DESIGN_NAME,
        "updated_at": current_storage_timestamp(),
        "events": merged,
        "summary": _store_summary(merged),
    }
    write_json_store(firecrawl_monitor_events_path(settings), next_store)
    return {**next_store, "saved_count": saved_count}


def summarize_firecrawl_monitor_event_store(settings: Any, limit: int = 20) -> dict[str, Any]:
    store = read_firecrawl_monitor_event_store(settings)
    events = [item for item in store.get("events", []) if isinstance(item, dict)]
    summary = store.get("summary") if isinstance(store.get("summary"), dict) else {}
    if "event_count" not in summary:
        summary = _store_summary(events)
    safe_limit = max(1, min(limit, MAX_RECENT_EVENTS))
    recent_events = []
    for event in events[:safe_limit]:
        recent_events.append(
            {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "monitor_id": event.get("monitor_id"),
                "check_id": event.get("check_id"),
                "url": event.get("url"),
                "status": event.get("status"),
                "title": event.get("title"),
                "summary": event.get("summary"),
                "is_meaningful": event.get("is_meaningful"),
                "route_hint": event.get("route_hint"),
                "received_at": event.get("received_at"),
            }
        )
    return {
        "status": "success",
        "module": DESIGN_NAME,
        "storage_path": str(firecrawl_monitor_events_path(settings)),
        "updated_at": store.get("updated_at"),
        **summary,
        "recent_events": recent_events,
    }


def ingest_firecrawl_monitor_payload(
    payload: dict[str, Any],
    settings: Any,
    *,
    save_result: bool = True,
) -> dict[str, Any]:
    normalized = normalize_firecrawl_monitor_payload(payload)
    store = upsert_firecrawl_monitor_events(settings, normalized["events"]) if save_result else None
    return {
        **normalized,
        "saved": bool(save_result),
        "saved_count": int(store.get("saved_count") or 0) if store else 0,
        "store_summary": summarize_firecrawl_monitor_event_store(settings) if save_result else None,
    }


def read_firecrawl_monitor_webhook_status(settings: Any) -> dict[str, Any]:
    return read_json_store(
        firecrawl_monitor_webhook_status_path(settings),
        {
            "module": "firecrawl_monitor_webhook_status",
            "updated_at": None,
            "webhook_ready": False,
            "last_webhook_received_at": None,
            "last_webhook_error": None,
            "last_webhook_status": None,
            "accepted_count": 0,
            "rejected_count": 0,
        },
    )


def record_firecrawl_monitor_webhook_status(
    settings: Any,
    *,
    status: str,
    reason: str | None = None,
    payload: dict[str, Any] | None = None,
    saved_count: int = 0,
) -> dict[str, Any]:
    current = read_firecrawl_monitor_webhook_status(settings)
    payload_hash = None
    if isinstance(payload, dict):
        seed = repr(
            {
                "type": payload.get("type") or payload.get("event"),
                "data_type": type(payload.get("data")).__name__,
                "keys": sorted(str(key) for key in payload.keys())[:20],
            }
        )
        payload_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
    accepted = status == "accepted"
    next_status = {
        **current,
        "module": "firecrawl_monitor_webhook_status",
        "updated_at": current_storage_timestamp(),
        "webhook_ready": bool(_settings_str(settings, "firecrawl_monitor_webhook_secret")),
        "last_webhook_received_at": current_storage_timestamp(),
        "last_webhook_error": None if accepted else (reason or status),
        "last_webhook_status": status,
        "last_payload_type": _compact_text(payload.get("type") or payload.get("event"), 80) if isinstance(payload, dict) else "",
        "last_payload_hash": payload_hash,
        "last_saved_count": int(saved_count or 0),
        "accepted_count": int(current.get("accepted_count") or 0) + (1 if accepted else 0),
        "rejected_count": int(current.get("rejected_count") or 0) + (0 if accepted else 1),
    }
    write_json_store(firecrawl_monitor_webhook_status_path(settings), next_status)
    return next_status


def build_firecrawl_monitor_webhook_status(settings: Any) -> dict[str, Any]:
    status = read_firecrawl_monitor_webhook_status(settings)
    return {
        **status,
        "webhook_ready": bool(_settings_str(settings, "firecrawl_monitor_webhook_secret")),
        "secret_configured": bool(_settings_str(settings, "firecrawl_monitor_webhook_secret")),
        "storage_path": str(firecrawl_monitor_webhook_status_path(settings)),
    }


def verify_firecrawl_monitor_webhook_secret(settings: Any, provided_secrets: list[str | None]) -> tuple[bool, str]:
    expected = _settings_str(settings, "firecrawl_monitor_webhook_secret")
    if not expected:
        return False, "webhook_secret_not_configured"
    for provided in provided_secrets:
        cleaned = str(provided or "").strip()
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()
        if cleaned and hmac.compare_digest(cleaned, expected):
            return True, "verified"
    return False, "webhook_secret_mismatch"


def handle_firecrawl_monitor_webhook(
    payload: dict[str, Any],
    settings: Any,
    *,
    provided_secrets: list[str | None],
) -> dict[str, Any]:
    verified, reason = verify_firecrawl_monitor_webhook_secret(settings, provided_secrets)
    if not verified:
        status = record_firecrawl_monitor_webhook_status(
            settings,
            status="rejected",
            reason=reason,
            payload=payload if isinstance(payload, dict) else None,
        )
        return {
            "status": "rejected",
            "module": "firecrawl_monitor_webhook",
            "reason": reason,
            "saved_count": 0,
            "webhook_status": status,
        }
    result = ingest_firecrawl_monitor_payload(payload, settings, save_result=True)
    status = record_firecrawl_monitor_webhook_status(
        settings,
        status="accepted",
        payload=payload,
        saved_count=int(result.get("saved_count") or 0),
    )
    return {
        "status": "accepted",
        "module": "firecrawl_monitor_webhook",
        "saved_count": int(result.get("saved_count") or 0),
        "event_count": int(result.get("event_count") or 0),
        "webhook_status": status,
        "store_summary": result.get("store_summary"),
    }
