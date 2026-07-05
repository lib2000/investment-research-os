"""Portfolio holding report alert payloads for Telegram delivery."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any


DESIGN_NAME = "portfolio_report_alert_v1"
REPORT_ALERT_TITLE = "Portfolio Report Alert"
REPORT_KEYWORDS = (
    "report",
    "리포트",
    "공시",
    "filing",
    "sec",
    "dart",
    "ir",
    "earnings",
)
EXCLUDED_REPORT_CATEGORIES = ("rag-query-synthesis", "recommendation")


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _upper_ticker(value: Any) -> str:
    return _safe_text(value).upper()


def _parse_date(value: Any) -> date | None:
    text = _safe_text(value)[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _sha256_short(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def load_holding_universe(portfolios: dict[str, Any]) -> dict[str, dict[str, Any]]:
    holdings: dict[str, dict[str, Any]] = {}
    for portfolio in (portfolios.get("portfolios") or {}).values():
        if not isinstance(portfolio, dict):
            continue
        portfolio_name = _safe_text(portfolio.get("portfolio_name"))
        for holding in portfolio.get("holdings") or []:
            if not isinstance(holding, dict):
                continue
            ticker = _upper_ticker(holding.get("ticker"))
            if not ticker:
                continue
            current = holdings.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "name": _safe_text(holding.get("name") or holding.get("company_name")),
                    "portfolio_names": [],
                    "market_value": 0.0,
                    "currency": _safe_text(holding.get("currency")),
                },
            )
            if portfolio_name and portfolio_name not in current["portfolio_names"]:
                current["portfolio_names"].append(portfolio_name)
            try:
                current["market_value"] += float(holding.get("market_value") or 0)
            except (TypeError, ValueError):
                pass
            if not current.get("name"):
                current["name"] = _safe_text(holding.get("name") or holding.get("company_name"))
            if not current.get("currency"):
                current["currency"] = _safe_text(holding.get("currency"))
    return holdings


def _entry_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("type", "module", "category", "source_type", "source_scope", "summary", "title", "report_name"):
        parts.append(_safe_text(entry.get(key)).lower())
    tags = entry.get("tags")
    if isinstance(tags, list):
        parts.extend(_safe_text(tag).lower() for tag in tags)
    return " ".join(part for part in parts if part)


def is_report_like(entry: dict[str, Any]) -> bool:
    text = _entry_text(entry)
    if any(excluded in text for excluded in EXCLUDED_REPORT_CATEGORIES):
        return False
    return any(keyword in text for keyword in REPORT_KEYWORDS)


def normalize_report_item(entry: dict[str, Any], *, source_family: str) -> dict[str, Any] | None:
    ticker = _upper_ticker(entry.get("ticker") or ((entry.get("ticker_verification") or {}).get("official_symbol") if isinstance(entry.get("ticker_verification"), dict) else ""))
    if not ticker:
        return None
    title = _safe_text(entry.get("title") or entry.get("summary") or entry.get("report_name") or entry.get("file_name"))
    if not title:
        return None
    published_at = _safe_text(entry.get("published_at") or entry.get("date") or entry.get("created_at"))
    detail_url = _safe_text(entry.get("detail_url") or entry.get("source_url") or entry.get("url"))
    relative_path = _safe_text(entry.get("relative_path") or ((entry.get("storage") or {}).get("relative_path") if isinstance(entry.get("storage"), dict) else ""))
    item_id = _safe_text(entry.get("item_id") or entry.get("rcept_no") or entry.get("file_name"))
    stable_source = "|".join(
        [
            source_family,
            ticker,
            title,
            published_at,
            detail_url,
            item_id,
        ]
    )
    return {
        "item_id": _safe_text(entry.get("item_id") or entry.get("rcept_no")) or _sha256_short(stable_source),
        "ticker": ticker,
        "company_name": _safe_text(entry.get("company_name") or ((entry.get("ticker_verification") or {}).get("company_name") if isinstance(entry.get("ticker_verification"), dict) else "")),
        "title": title,
        "published_at": published_at,
        "source_provider": _safe_text(entry.get("source_provider") or entry.get("module") or entry.get("source_type") or source_family),
        "source_family": source_family,
        "category": _safe_text(entry.get("category") or entry.get("source_type") or entry.get("type")),
        "detail_url": detail_url,
        "relative_path": relative_path,
        "importance": _safe_text(entry.get("importance")),
        "report_key": _sha256_short(stable_source),
    }


def manifest_entries(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        rows = manifest.get("items") or manifest.get("records") or []
    else:
        rows = manifest
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def collect_report_items(*, manifest: Any, company_ir_sources: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entry in manifest_entries(manifest):
        if not is_report_like(entry):
            continue
        item = normalize_report_item(entry, source_family="research_vault_manifest")
        if item:
            candidates.append(item)
    for entry in company_ir_sources.get("items") or []:
        if not isinstance(entry, dict):
            continue
        item = normalize_report_item(entry, source_family="company_ir_sources_watch")
        if item:
            candidates.append(item)

    deduped: dict[str, dict[str, Any]] = {}
    for item in candidates:
        deduped.setdefault(item["report_key"], item)
    return sorted(
        deduped.values(),
        key=lambda item: (item.get("published_at") or "", item.get("ticker") or "", item.get("title") or ""),
        reverse=True,
    )


def select_new_holding_reports(
    *,
    portfolios: dict[str, Any],
    manifest: Any,
    company_ir_sources: dict[str, Any],
    state: dict[str, Any] | None = None,
    today: date | None = None,
    lookback_days: int = 3,
    max_items: int = 12,
    include_previously_sent: bool = False,
) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    holdings = load_holding_universe(portfolios)
    sent_keys = set(str(item) for item in state.get("sent_report_keys") or [])
    today = today or date.today()
    cutoff = today.toordinal() - max(0, int(lookback_days or 0))
    selected: list[dict[str, Any]] = []
    for item in collect_report_items(manifest=manifest, company_ir_sources=company_ir_sources):
        ticker = item.get("ticker")
        if ticker not in holdings:
            continue
        published_date = _parse_date(item.get("published_at"))
        if published_date and published_date.toordinal() < cutoff:
            continue
        if not include_previously_sent and item["report_key"] in sent_keys:
            continue
        holding = holdings[ticker]
        selected.append(
            {
                **item,
                "holding_name": holding.get("name") or item.get("company_name"),
                "portfolio_names": holding.get("portfolio_names") or [],
                "holding_market_value": holding.get("market_value"),
                "holding_currency": holding.get("currency"),
            }
        )
        if len(selected) >= max_items:
            break
    return {
        "design": DESIGN_NAME,
        "status": "success",
        "holding_count": len(holdings),
        "candidate_count": len(selected),
        "lookback_days": lookback_days,
        "reports": selected,
    }


def render_report_alert_text(result: dict[str, Any], *, max_items: int = 8) -> str:
    reports = [item for item in result.get("reports") or [] if isinstance(item, dict)]
    lines = [
        REPORT_ALERT_TITLE,
        f"As of: {_safe_text(result.get('as_of')) or datetime.now().isoformat(timespec='seconds')}",
        f"Holdings scanned: {result.get('holding_count', 0)}",
        f"New holding reports: {len(reports)}",
    ]
    if not reports:
        lines.append("No new holding reports found.")
        return "\n".join(lines)
    lines.append("")
    for index, item in enumerate(reports[: max(1, max_items)], start=1):
        ticker = _safe_text(item.get("ticker"))
        company = _safe_text(item.get("holding_name") or item.get("company_name"))
        title = _safe_text(item.get("title"))
        published_at = _safe_text(item.get("published_at")) or "date n/a"
        provider = _safe_text(item.get("source_provider") or item.get("category"))
        url = _safe_text(item.get("detail_url") or item.get("relative_path"))
        lines.append(f"{index}. {ticker} {company}")
        lines.append(f"- {published_at} | {provider}")
        lines.append(f"- {title}")
        if url:
            lines.append(f"- {url}")
    return "\n".join(lines).strip()


def chunk_text(text: str, *, max_chars: int) -> list[str]:
    max_chars = max(500, int(max_chars or 3600))
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in str(text or "").splitlines():
        addition = len(line) + (1 if current else 0)
        if current and current_len + addition > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += addition
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def build_report_alert_payload(
    result: dict[str, Any],
    *,
    chat_id: str = "",
    max_message_chars: int = 3600,
    max_items: int = 8,
    send_empty: bool = False,
) -> dict[str, Any]:
    reports = [item for item in result.get("reports") or [] if isinstance(item, dict)]
    should_send = bool(reports or send_empty)
    text = render_report_alert_text(result, max_items=max_items) if should_send else ""
    messages = [
        {
            "chat_id": chat_id or "",
            "text": chunk,
            "disable_web_page_preview": True,
            "priority": "must_keep",
            "category": "portfolio_report_alert",
        }
        for chunk in chunk_text(text, max_chars=max_message_chars)
        if chunk
    ]
    return {
        "design": DESIGN_NAME,
        "status": "success",
        "message_type": "portfolio_report_alert",
        "send_time": "07:00",
        "target_bot": "@lib20_bot",
        "chat_id_configured": bool(chat_id),
        "message_count": len(messages),
        "candidate_count": len(reports),
        "messages": messages,
        "text": text,
        "report_keys": [item.get("report_key") for item in reports if item.get("report_key")],
    }


def state_after_plan(state: dict[str, Any], payload: dict[str, Any], *, delivered: bool) -> dict[str, Any]:
    previous_keys = list(dict.fromkeys(str(item) for item in state.get("sent_report_keys") or [] if item))
    new_keys = [str(item) for item in payload.get("report_keys") or [] if item]
    sent_keys = list(dict.fromkeys([*previous_keys, *new_keys])) if delivered else previous_keys
    return {
        **state,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "target_bot": "@lib20_bot",
        "send_time": "07:00",
        "last_plan": {
            "candidate_count": payload.get("candidate_count"),
            "message_count": payload.get("message_count"),
            "chat_id_configured": payload.get("chat_id_configured"),
            "delivered": delivered,
        },
        "sent_report_keys": sent_keys,
    }
