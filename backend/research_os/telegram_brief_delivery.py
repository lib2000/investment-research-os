"""Safe Telegram delivery and cleanup planning for investment briefs."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx


DESIGN_NAME = "telegram_brief_delivery_v1"
DEFAULT_TELEGRAM_API_BASE_URL = "https://api.telegram.org"
KEEP_MARKERS = ("Investment Priority Brief", "Today Recommendations", "Portfolio Report Alert", "Holding Reports")
IMPORTANT_MARKERS = ("Portfolio Health", "Top Movers", "Watch Items")
LOW_PRIORITY_CATEGORIES = {
    "routine_status_ok",
    "dry_run_transport_details",
    "raw_hash_or_storage_paths",
    "empty_reference_sections",
    "routine_status",
}


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def classify_telegram_message(message: dict[str, Any]) -> dict[str, Any]:
    text = str(message.get("text") or "")
    explicit_priority = _safe_text(message.get("priority"))
    explicit_category = _safe_text(message.get("category"))
    if explicit_priority == "must_keep":
        return {"priority": "must_keep", "category": explicit_category or "explicit_keep"}
    if "Portfolio Report Alert Post-run Check" in text:
        return {"priority": "must_keep", "category": "portfolio_report_alert_postrun"}
    if "Portfolio Report Alert" in text:
        return {"priority": "must_keep", "category": "portfolio_report_alert"}
    if "Investment Priority Brief" in text and "Holding Reports" in text:
        return {"priority": "must_keep", "category": "integrated_investment_brief"}
    if any(marker in text for marker in KEEP_MARKERS):
        return {"priority": "must_keep", "category": "today_recommendations"}
    if any(marker in text for marker in IMPORTANT_MARKERS):
        return {"priority": "important", "category": "portfolio_change"}
    if explicit_category in LOW_PRIORITY_CATEGORIES:
        return {"priority": "low_priority", "category": explicit_category}
    return {"priority": "low_priority", "category": explicit_category or "routine_status"}


def _live_ready(*, enabled: bool, dry_run: bool, bot_token: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if enabled and not dry_run and not bot_token:
        errors.append("TELEGRAM_BOT_TOKEN or MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN is required for live delivery")
    return bool(enabled and not dry_run and bot_token and not errors), errors


def build_telegram_delivery_plan(
    payload: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
    enabled: bool = False,
    dry_run: bool = True,
    cleanup_enabled: bool = False,
    bot_token: str = "",
) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    messages = [item for item in payload.get("messages") or [] if isinstance(item, dict)]
    previous_messages = [
        item
        for item in state.get("sent_messages") or []
        if isinstance(item, dict) and not item.get("deleted_at")
    ]
    live_ready, errors = _live_ready(enabled=enabled, dry_run=dry_run, bot_token=bot_token)

    planned_sends = []
    for index, message in enumerate(messages, start=1):
        classification = classify_telegram_message(message)
        action = "send" if live_ready else ("dry_run_send" if dry_run else "disabled")
        planned_sends.append(
            {
                "index": index,
                "action": action,
                "chat_id_configured": bool(_safe_text(message.get("chat_id"))),
                "text_sha256": _sha256_text(str(message.get("text") or "")),
                "text_chars": len(str(message.get("text") or "")),
                **classification,
            }
        )

    delete_candidates = []
    protected_messages = []
    for item in previous_messages:
        classification = classify_telegram_message(item)
        base = {
            "chat_id": item.get("chat_id"),
            "message_id": item.get("message_id"),
            "text_sha256": item.get("text_sha256") or _sha256_text(str(item.get("text") or "")),
            "sent_at": item.get("sent_at"),
            **classification,
        }
        if classification["priority"] == "must_keep":
            protected_messages.append({**base, "action": "keep"})
            continue
        action = "delete" if live_ready and cleanup_enabled and item.get("message_id") else "dry_run_delete_candidate"
        if not cleanup_enabled:
            action = "cleanup_disabled"
        delete_candidates.append({**base, "action": action})

    return {
        "design": DESIGN_NAME,
        "status": "failure" if errors else "success",
        "enabled": bool(enabled),
        "dry_run": bool(dry_run),
        "cleanup_enabled": bool(cleanup_enabled),
        "bot_token_configured": bool(bot_token),
        "live_ready": live_ready,
        "errors": errors,
        "planned_send_count": len(planned_sends),
        "delete_candidate_count": len(delete_candidates),
        "protected_message_count": len(protected_messages),
        "planned_sends": planned_sends,
        "delete_candidates": delete_candidates,
        "protected_messages": protected_messages,
    }


def execute_telegram_delivery(
    payload: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
    enabled: bool = False,
    dry_run: bool = True,
    cleanup_enabled: bool = False,
    bot_token: str = "",
    api_base_url: str = DEFAULT_TELEGRAM_API_BASE_URL,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    state.setdefault("sent_messages", [])
    plan = build_telegram_delivery_plan(
        payload,
        state=state,
        enabled=enabled,
        dry_run=dry_run,
        cleanup_enabled=cleanup_enabled,
        bot_token=bot_token,
    )
    if plan["status"] != "success" or not plan["live_ready"]:
        return {**plan, "applied_send_count": 0, "applied_delete_count": 0, "updated_state": state}

    messages = [item for item in payload.get("messages") or [] if isinstance(item, dict)]
    applied_send_count = 0
    applied_delete_count = 0
    base_url = str(api_base_url or DEFAULT_TELEGRAM_API_BASE_URL).rstrip("/")
    now = _utc_now()
    with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
        for index, message in enumerate(messages, start=1):
            classification = classify_telegram_message(message)
            response = client.post(
                f"{base_url}/bot{bot_token}/sendMessage",
                json={
                    "chat_id": message.get("chat_id"),
                    "text": message.get("text"),
                    "disable_web_page_preview": bool(message.get("disable_web_page_preview", True)),
                },
            )
            response.raise_for_status()
            body = response.json()
            message_id = ((body.get("result") or {}) if isinstance(body, dict) else {}).get("message_id")
            state["sent_messages"].append(
                {
                    "chat_id": message.get("chat_id"),
                    "message_id": message_id,
                    "text_sha256": _sha256_text(str(message.get("text") or "")),
                    "text_chars": len(str(message.get("text") or "")),
                    "sent_at": now,
                    "delivery_index": index,
                    **classification,
                }
            )
            applied_send_count += 1

        for candidate in plan["delete_candidates"]:
            if candidate.get("action") != "delete":
                continue
            response = client.post(
                f"{base_url}/bot{bot_token}/deleteMessage",
                json={"chat_id": candidate.get("chat_id"), "message_id": candidate.get("message_id")},
            )
            response.raise_for_status()
            applied_delete_count += 1
            for item in state.get("sent_messages") or []:
                if item.get("chat_id") == candidate.get("chat_id") and item.get("message_id") == candidate.get("message_id"):
                    item["deleted_at"] = now
                    item["delete_reason"] = candidate.get("category")
                    break

    return {
        **build_telegram_delivery_plan(
            payload,
            state=state,
            enabled=enabled,
            dry_run=dry_run,
            cleanup_enabled=cleanup_enabled,
            bot_token=bot_token,
        ),
        "applied_send_count": applied_send_count,
        "applied_delete_count": applied_delete_count,
        "updated_state": state,
    }
