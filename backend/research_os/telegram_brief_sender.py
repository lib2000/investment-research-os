"""Telegram portfolio brief rendering helpers."""

from __future__ import annotations

from typing import Any


DESIGN_NAME = "telegram_brief_sender_v1"
DEFAULT_MAX_MESSAGE_CHARS = 3600


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _format_number(value: Any, *, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _safe_text(value) or "n/a"
    return f"{number:.{digits}f}"


def _format_delta(value: Any, *, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _safe_text(value) or "n/a"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.{digits}f}"


def _ticker_label(item: dict[str, Any]) -> str:
    ticker = _safe_text(item.get("ticker")) or "UNKNOWN"
    company = _safe_text(item.get("company_name"))
    return f"{ticker} {company}".strip()


def _change_reason(item: dict[str, Any]) -> str:
    event_types = item.get("event_types") if isinstance(item.get("event_types"), list) else []
    if "added" in event_types:
        return "new"
    if "removed" in event_types:
        return "removed"
    parts: list[str] = []
    if "stance_changed" in event_types:
        previous_stance = _safe_text(item.get("previous_stance")) or "n/a"
        current_stance = _safe_text(item.get("current_stance")) or "n/a"
        parts.append(f"stance {previous_stance}->{current_stance}")
    if "confidence_changed" in event_types:
        parts.append(f"confidence {_format_delta(item.get('confidence_delta'))}")
    if "score_changed" in event_types:
        parts.append(f"score {_format_delta(item.get('score_delta'))}")
    return ", ".join(parts) or _safe_text(item.get("stance_direction")) or "changed"


def _section_lines(title: str, items: list[dict[str, Any]], *, limit: int) -> list[str]:
    lines = [title]
    if not items:
        lines.append("- none")
        return lines
    for item in items[: max(1, limit)]:
        lines.append(f"- {_ticker_label(item)}: {_change_reason(item)}")
    return lines


def chunk_telegram_message(text: str, *, max_chars: int = DEFAULT_MAX_MESSAGE_CHARS) -> list[str]:
    max_chars = max(500, int(max_chars or DEFAULT_MAX_MESSAGE_CHARS))
    lines = str(text or "").splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        addition = len(line) + (1 if current else 0)
        if current and current_len + addition > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        if len(line) > max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            for index in range(0, len(line), max_chars):
                chunks.append(line[index : index + max_chars])
            continue
        current.append(line)
        current_len += addition
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def render_portfolio_telegram_brief(change_result: dict[str, Any], *, max_items: int = 5) -> str:
    health = change_result.get("health_score") if isinstance(change_result.get("health_score"), dict) else {}
    counts = change_result.get("change_counts") if isinstance(change_result.get("change_counts"), dict) else {}
    top_movers = [item for item in change_result.get("top_movers") or [] if isinstance(item, dict)]
    watch_items = [item for item in change_result.get("watch_items") or [] if isinstance(item, dict)]
    lines = [
        "Portfolio Health",
        f"As of: {_safe_text(change_result.get('current_as_of')) or 'n/a'}",
        (
            "Score: "
            f"{_format_number(health.get('previous'))} -> {_format_number(health.get('current'))} "
            f"({_safe_text(health.get('direction')) or 'unknown'}, delta {_format_delta(health.get('delta'))})"
        ),
        (
            "Changes: "
            f"{counts.get('changed_count', 0)} changed, "
            f"{counts.get('stance_changed_count', 0)} stance, "
            f"{counts.get('confidence_changed_count', 0)} confidence, "
            f"{counts.get('watch_item_count', 0)} watch"
        ),
        "",
        *_section_lines("Top Movers", top_movers, limit=max_items),
        "",
        *_section_lines("Watch Items", watch_items, limit=max_items),
    ]
    return "\n".join(lines).strip()


def build_telegram_brief_payload(
    change_result: dict[str, Any],
    *,
    chat_id: str | None = None,
    max_items: int = 5,
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
) -> dict[str, Any]:
    text = render_portfolio_telegram_brief(change_result, max_items=max_items)
    messages = chunk_telegram_message(text, max_chars=max_message_chars)
    payloads = [
        {
            "chat_id": chat_id or "",
            "text": message,
            "disable_web_page_preview": True,
        }
        for message in messages
    ]
    return {
        "design": DESIGN_NAME,
        "status": "success",
        "message_count": len(payloads),
        "chat_id_configured": bool(chat_id),
        "messages": payloads,
        "text": text,
    }
