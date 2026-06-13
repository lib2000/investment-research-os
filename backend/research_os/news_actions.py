"""News inbox item actions and market inference helpers."""

from __future__ import annotations

from typing import Protocol


class NewsActionRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def update_news_inbox_item_action(runtime: NewsActionRuntime, item: dict, action: str) -> dict:
    now = runtime.current_storage_timestamp()
    normalized_action = str(action or "").strip().lower()
    if normalized_action in {"hold", "보류"}:
        item["review_status"] = "보류"
        item["held_at"] = now
        item["updated_at"] = now
        message = "뉴스를 보류 상태로 표시했습니다."
    elif normalized_action in {"restore", "pending", "대기"}:
        item["review_status"] = "대기"
        item["updated_at"] = now
        message = "뉴스를 대기 상태로 되돌렸습니다."
    elif normalized_action in {"market_journal", "market", "시장일지"}:
        item["scope"] = "MARKET"
        item["scope_label"] = runtime.news_scope_label("MARKET")
        item["review_status"] = "시장일지 후보"
        item["market_journal_candidate"] = True
        item["updated_at"] = now
        tags = sorted(set([*(item.get("tags") or []), "market_journal_candidate"]))
        item["tags"] = tags
        message = "뉴스를 시장일지 반영 후보로 표시했습니다."
    else:
        raise runtime.http_exception(status_code=422, detail="지원하지 않는 뉴스 처리 액션입니다.")
    return {
        "status": "success",
        "module": "news_inbox_action",
        "action": normalized_action,
        "message": message,
        "item": item,
    }


def infer_market_from_news_item(item: dict) -> str:
    scope = str(item.get("scope") or "").upper()
    text = " ".join(
        str(value or "")
        for value in [
            item.get("title"),
            item.get("summary"),
            item.get("raw_content"),
            " ".join(item.get("tags") or []),
        ]
    ).upper()
    text_without_translation_markers = text.replace("한국어", "")
    if "KOSPI" in text_without_translation_markers or "KOSDAQ" in text_without_translation_markers or any(
        keyword in text
        for keyword in ["한국 증시", "한국 시장", "국내", "코스피", "코스닥", "원화", "관세청", "수출입", "국내 증시"]
    ):
        return "KR"
    if any(
        keyword in text
        for keyword in ["NASDAQ", "S&P", "NYSE", "DOW", "미국", "연준", "FOMC", "달러"]
    ):
        return "US"
    if scope in {"MARKET-KR", "KR"}:
        return "KR"
    if scope in {"MARKET-US", "US"}:
        return "US"
    return "GLOBAL"
