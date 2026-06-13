"""News inbox listing, filtering, and copyright-safe views."""

from __future__ import annotations

from re import sub
from typing import Protocol


class NewsInboxRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def read_news_inbox(runtime: NewsInboxRuntime, settings) -> dict:
    payload = runtime.read_json_store(runtime.news_inbox_path(settings), {"items": [], "updated_at": None})
    if not isinstance(payload, dict):
        return {"items": [], "updated_at": None}
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def write_news_inbox(runtime: NewsInboxRuntime, settings, payload: dict) -> None:
    payload["updated_at"] = runtime.current_storage_timestamp()
    runtime.write_json_store(runtime.news_inbox_path(settings), payload)


def find_news_inbox_item(items: list[dict], item_id: str) -> dict | None:
    return next((entry for entry in items if str(entry.get("id") or "") == item_id), None)


def news_item_fingerprint(
    runtime: NewsInboxRuntime,
    title: str,
    raw_content: str,
    source_url: str | None = None,
) -> str:
    if source_url:
        return runtime.content_fingerprint(f"url::{source_url.strip().lower()}")
    return runtime.content_fingerprint("\n".join([title.strip().lower(), raw_content.strip()]))


def news_scope_label(scope: str) -> str:
    return {
        "INBOX": "일반 뉴스",
        "MACRO": "거시/경제",
        "SECTOR": "섹터/산업",
        "MARKET": "시장 흐름",
        "POLICY": "정책/규제",
        "RATES": "금리/환율",
        "FLOWS": "수급/자금 흐름",
    }.get(scope, scope)


NEWS_SAFE_TEXT_LIMIT = 900
NEWS_SAFE_PREVIEW_LIMIT = 420


def compact_news_safe_text(value: object, max_length: int = NEWS_SAFE_TEXT_LIMIT) -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_length:
        return text
    return f"{text[:max_length].rstrip()}..."


def news_item_safe_view(item: dict) -> dict:
    safe_item = dict(item or {})
    source_url_processing = sanitize_news_source_url_processing(safe_item.get("source_url_processing"))
    if source_url_processing:
        safe_item["source_url_processing"] = source_url_processing
    raw_content = compact_news_safe_text(safe_item.get("safe_user_note") or safe_item.get("raw_content"))
    safe_item["safe_user_note"] = raw_content
    safe_item["raw_content"] = raw_content or "\n".join(
        value for value in [
            f"뉴스 URL: {safe_item.get('source_url')}" if safe_item.get("source_url") else "",
            "본문 저장 정책: 원문 본문은 저장하지 않고 URL, 제목, 짧은 분석 메모만 보관합니다.",
        ] if value
    )
    safe_item["summary"] = compact_news_safe_text(
        safe_item.get("summary") or safe_item["raw_content"],
        NEWS_SAFE_PREVIEW_LIMIT,
    )
    safe_item["document_preview"] = compact_news_safe_text(
        safe_item.get("document_preview")
        or source_url_processing.get("short_excerpt")
        or source_url_processing.get("note"),
        NEWS_SAFE_PREVIEW_LIMIT,
    )
    safe_item["copyright_policy"] = {
        "mode": "metadata_only",
        "full_article_body_stored": False,
        "allowed_fields": ["title", "source_url", "source_title", "short_user_note", "short_excerpt", "analysis_summary"],
        "message": "뉴스/기사 원문 본문은 저장하지 않고 링크와 짧은 자체 분석 메모만 보관합니다.",
    }
    tags = sorted(set([*(safe_item.get("tags") or []), "copyright_safe_metadata"]))
    if safe_item.get("source_url"):
        tags.append("url_only")
    safe_item["tags"] = sorted(set(tags))
    return safe_item


def sanitize_news_source_url_processing(url_info: dict | None) -> dict:
    if not isinstance(url_info, dict):
        return {}
    sanitized = {
        key: value
        for key, value in url_info.items()
        if key not in {"text", "original_text", "analysis_text", "raw_text"}
    }
    text = compact_news_safe_text(url_info.get("text"), NEWS_SAFE_PREVIEW_LIMIT)
    if text:
        sanitized["short_excerpt"] = text
        sanitized["full_text_stored"] = False
    return sanitized


def news_filter_key(runtime: NewsInboxRuntime, item: dict) -> set[str]:
    tags = {str(tag).lower() for tag in (item.get("tags") or [])}
    quality_status = str((item.get("capture_quality") or {}).get("status") or "")
    review_status = str(item.get("review_status") or "")
    policy_url_only = runtime.storage_quality_entry_is_policy_url_only(item)
    promoted_storage_handled = bool(item.get("promoted") and item.get("promoted_storage"))
    keys = {"all"}
    if not item.get("promoted"):
        keys.add("unpromoted")
    if item.get("source_url") and ("url_only" in tags or not str(item.get("safe_user_note") or "").strip()):
        keys.add("url_only")
    if not (policy_url_only or promoted_storage_handled) and (
        "needs_body_copy" in tags
        or "url_text_unavailable" in tags
        or quality_status in {"보강 필요", "실패"}
    ):
        keys.add("needs_body")
    if not (policy_url_only or promoted_storage_handled) and quality_status not in {None, "", "정상"}:
        keys.add("quality_issue")
    if item.get("market_journal_candidate") or "시장일지" in review_status:
        keys.add("market_journal")
    if review_status == "보류":
        keys.add("held")
    return keys


def filter_news_inbox_items(runtime: NewsInboxRuntime, items: list[dict], filter_key: str) -> list[dict]:
    normalized = str(filter_key or "all").strip().lower()
    if normalized in {"", "all", "전체"}:
        return items
    aliases = {
        "body_missing": "needs_body",
        "body": "needs_body",
        "본문": "needs_body",
        "url": "url_only",
        "pending": "unpromoted",
        "시장일지": "market_journal",
        "quality": "quality_issue",
    }
    normalized = aliases.get(normalized, normalized)
    return [item for item in items if normalized in news_filter_key(runtime, item)]


def news_filter_counts(runtime: NewsInboxRuntime, items: list[dict]) -> dict:
    keys = ["all", "unpromoted", "needs_body", "url_only", "quality_issue", "market_journal", "held"]
    return {
        key: sum(1 for item in items if key in news_filter_key(runtime, item))
        for key in keys
    }


def build_news_inbox_payload(runtime: NewsInboxRuntime, settings, limit: int = 30, filter_key: str = "all") -> dict:
    payload = read_news_inbox(runtime, settings)
    items = [
        item
        for item in payload.get("items", [])
        if isinstance(item, dict)
    ]
    items = sorted(
        items,
        key=lambda item: item.get("created_at") or item.get("updated_at") or "",
        reverse=True,
    )
    counts = news_filter_counts(runtime, items)
    filtered_items = filter_news_inbox_items(runtime, items, filter_key)
    safe_filtered_items = [news_item_safe_view(item) for item in filtered_items]
    return {
        "status": "success",
        "module": "news_inbox_list",
        "updated_at": payload.get("updated_at"),
        "count": len(items),
        "unpromoted_count": sum(1 for item in items if not item.get("promoted")),
        "quality_issue_count": sum(
            1
            for item in items
            if not runtime.storage_quality_entry_is_policy_url_only(item)
            and not bool(item.get("promoted") and item.get("promoted_storage"))
            and (item.get("capture_quality") or {}).get("status") not in {None, "정상"}
        ),
        "filter": filter_key or "all",
        "filter_counts": counts,
        "filtered_count": len(filtered_items),
        "items": safe_filtered_items[: max(1, min(int(limit or 30), 100))],
    }
