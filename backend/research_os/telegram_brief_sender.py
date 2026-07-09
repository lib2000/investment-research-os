"""Telegram portfolio brief rendering helpers."""

from __future__ import annotations

from typing import Any


DESIGN_NAME = "telegram_brief_sender_v1"
DEFAULT_MAX_MESSAGE_CHARS = 3600
LOW_PRIORITY_MESSAGE_LABELS = [
    "routine_status_ok",
    "dry_run_transport_details",
    "raw_hash_or_storage_paths",
    "empty_reference_sections",
]


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


def _company_label(item: dict[str, Any]) -> str:
    company = _safe_text(item.get("company_name")) or _safe_text(item.get("company")) or "UNKNOWN"
    ticker = _safe_text(item.get("ticker"))
    return f"{company} ({ticker})" if ticker else company


def _format_price(value: Any, currency: Any = "") -> str:
    if value in (None, ""):
        return ""
    currency_text = _safe_text(currency)
    try:
        number = float(value)
    except (TypeError, ValueError):
        price_text = _safe_text(value)
    else:
        if number.is_integer():
            price_text = f"{int(number):,}"
        else:
            price_text = f"{number:,.2f}".rstrip("0").rstrip(".")
    return f"{price_text} {currency_text}".strip()


def _recommendation_sort_key(item: dict[str, Any]) -> tuple[str, int, str]:
    market = _safe_text(item.get("market")) or _safe_text(item.get("market_label"))
    try:
        rank = int(item.get("rank") or 999)
    except (TypeError, ValueError):
        rank = 999
    return market, rank, _safe_text(item.get("ticker"))


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
        return lines
    for item in items[: max(1, limit)]:
        lines.append(f"- {_ticker_label(item)}: {_change_reason(item)}")
    return lines


def _recommendation_section_lines(today_recommendations: list[dict[str, Any]], *, limit_per_market: int = 3) -> list[str]:
    recommendations = [item for item in today_recommendations if isinstance(item, dict)]
    if not recommendations:
        return []
    latest_date = max((_safe_text(item.get("recommendation_date")) for item in recommendations), default="")
    lines = ["Today Recommendations"]
    if latest_date:
        lines.append(f"As of: {latest_date}")
    market_groups: dict[str, list[dict[str, Any]]] = {}
    market_labels: dict[str, str] = {}
    for item in sorted(recommendations, key=_recommendation_sort_key):
        market = _safe_text(item.get("market")) or "UNKNOWN"
        market_groups.setdefault(market, []).append(item)
        market_labels.setdefault(market, _safe_text(item.get("market_label")) or market)
    for market in sorted(market_groups):
        lines.append(f"{market_labels.get(market, market)}")
        for item in market_groups[market][: max(1, limit_per_market)]:
            rank = _safe_text(item.get("rank")) or "?"
            score = _safe_text(item.get("score")) or "n/a"
            price = _format_price(item.get("baseline_price"), item.get("currency"))
            detail = f"score {score}"
            if price:
                detail += f", base {price}"
            lines.append(f"- #{rank} {_company_label(item)}: {detail}")
    return lines


def _report_alert_section_lines(report_alert: dict[str, Any] | None, *, limit: int = 8) -> list[str]:
    if not isinstance(report_alert, dict):
        return []
    reports = [item for item in report_alert.get("reports") or [] if isinstance(item, dict)]
    candidate_count = len(reports)
    if candidate_count <= 0:
        try:
            candidate_count = int(report_alert.get("candidate_count") or 0)
        except (TypeError, ValueError):
            candidate_count = 0
    if candidate_count <= 0:
        return []
    lines = ["Holding Reports"]
    as_of = _safe_text(report_alert.get("as_of"))
    if as_of:
        lines.append(f"As of: {as_of}")
    lines.append(f"New reports/filings: {candidate_count}")
    if not reports:
        return lines
    for item in reports[: max(1, limit)]:
        ticker = _safe_text(item.get("ticker"))
        company = _safe_text(item.get("holding_name") or item.get("company_name"))
        title = _safe_text(item.get("title"))
        published_at = _safe_text(item.get("published_at")) or "date n/a"
        provider = _safe_text(item.get("source_provider") or item.get("category"))
        label = f"{ticker} {company}".strip() or "UNKNOWN"
        detail = " | ".join(part for part in [published_at, provider] if part)
        lines.append(f"- {label}: {title}")
        if detail:
            lines.append(f"  {detail}")
    return lines


def _report_alert_count(report_alert: dict[str, Any] | None) -> int:
    if not isinstance(report_alert, dict):
        return 0
    reports = [item for item in report_alert.get("reports") or [] if isinstance(item, dict)]
    if reports:
        return len(reports)
    try:
        return max(0, int(report_alert.get("candidate_count") or 0))
    except (TypeError, ValueError):
        return 0


def build_priority_filter_summary(
    change_result: dict[str, Any],
    today_recommendations: list[dict[str, Any]] | None = None,
    portfolio_report_alert: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delivered_sections = ["portfolio_health"]
    if today_recommendations:
        delivered_sections.insert(0, "today_recommendations")
    if _report_alert_count(portfolio_report_alert):
        insert_at = 1 if "today_recommendations" in delivered_sections else 0
        delivered_sections.insert(insert_at, "holding_reports")
    if change_result.get("top_movers"):
        delivered_sections.append("top_movers")
    if change_result.get("watch_items"):
        delivered_sections.append("watch_items")
    return {
        "mode": "important_only",
        "delivered_sections": delivered_sections,
        "suppressed_low_priority_count": len(LOW_PRIORITY_MESSAGE_LABELS),
        "suppressed_low_priority_labels": list(LOW_PRIORITY_MESSAGE_LABELS),
    }


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


def render_portfolio_telegram_brief(
    change_result: dict[str, Any],
    *,
    max_items: int = 5,
    today_recommendations: list[dict[str, Any]] | None = None,
    portfolio_report_alert: dict[str, Any] | None = None,
) -> str:
    health = change_result.get("health_score") if isinstance(change_result.get("health_score"), dict) else {}
    counts = change_result.get("change_counts") if isinstance(change_result.get("change_counts"), dict) else {}
    top_movers = [item for item in change_result.get("top_movers") or [] if isinstance(item, dict)]
    watch_items = [item for item in change_result.get("watch_items") or [] if isinstance(item, dict)]
    lines = [
        "Investment Priority Brief",
        *_recommendation_section_lines(today_recommendations or []),
        "",
        *_report_alert_section_lines(portfolio_report_alert, limit=max_items),
        "",
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
    return "\n".join(line for line in lines if line != "").strip()


def build_telegram_brief_payload(
    change_result: dict[str, Any],
    *,
    chat_id: str | None = None,
    max_items: int = 5,
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
    today_recommendations: list[dict[str, Any]] | None = None,
    portfolio_report_alert: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recommendations = [item for item in today_recommendations or [] if isinstance(item, dict)]
    report_count = _report_alert_count(portfolio_report_alert)
    text = render_portfolio_telegram_brief(
        change_result,
        max_items=max_items,
        today_recommendations=recommendations,
        portfolio_report_alert=portfolio_report_alert,
    )
    messages = chunk_telegram_message(text, max_chars=max_message_chars)
    payloads = [
        {
            "chat_id": chat_id or "",
            "text": message,
            "disable_web_page_preview": True,
            "priority": "must_keep",
            "category": "integrated_investment_brief",
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
        "today_recommendation_count": len(recommendations),
        "portfolio_report_alert_count": report_count,
        "priority_filter": build_priority_filter_summary(change_result, recommendations, portfolio_report_alert),
    }
