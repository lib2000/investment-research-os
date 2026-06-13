"""Build copyright-safe news inbox items from user input and URLs."""

from __future__ import annotations

from typing import Protocol


class NewsBuilderRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def build_news_item_from_payload(runtime: NewsBuilderRuntime, payload: dict, settings) -> dict:
    raw_content = str(payload.get("raw_content") or payload.get("rawContent") or "").strip()
    source_url = str(payload.get("source_url") or payload.get("sourceUrl") or "").strip()
    url_info = runtime.fetch_capture_source_url(source_url) if source_url else {}
    sanitized_url_info = runtime.sanitize_news_source_url_processing(url_info)
    url_title_context = (
        f"웹사이트 제목: {url_info.get('title')}"
        if source_url and url_info.get("title")
        else ""
    )
    url_text_unavailable = bool(source_url and runtime.is_unusable_source_url(url_info))
    safe_user_note = runtime.compact_news_safe_text(raw_content)
    safe_url_excerpt = runtime.compact_news_safe_text(url_info.get("text"), runtime.news_safe_preview_limit)
    url_status_line = (
        f"웹 추출 상태: {url_info.get('status') or '확인 전'}"
        if source_url
        else ""
    )
    url_only_line = (
        "본문 저장 정책: 원문 본문은 저장하지 않고 URL, 제목, 짧은 분석 메모만 보관합니다."
        if source_url
        else ""
    )
    combined_content = "\n\n".join(
        value
        for value in [
            safe_user_note,
            url_title_context,
            f"뉴스 URL: {source_url}" if source_url else "",
            url_status_line,
            url_only_line,
            f"본문 보강 안내: {url_info.get('note')}" if url_text_unavailable and url_info.get("note") else "",
        ]
        if value
    )
    if not combined_content.strip():
        raise runtime.http_exception(status_code=422, detail="저장할 뉴스 본문 또는 웹사이트 주소가 비어 있습니다.")
    inferred_scope, scope_reason = runtime.infer_capture_ticker(combined_content, settings)
    source_type = runtime.infer_capture_source_type(combined_content, None)
    if runtime.enum_or_str_value(source_type) != "news":
        source_type = runtime.data_source_type_news
    title = (
        str(payload.get("title") or "").strip()
        or str(url_info.get("title") or "").strip()
        or runtime.infer_capture_title(combined_content, None)
    )
    source_url_for_storage = (
        url_info.get("final_url")
        or url_info.get("source_url")
        or source_url
        or None
    )
    tags = runtime.infer_capture_tags(
        combined_content,
        ["news_inbox", "auto_classified", f"auto_scope:{scope_reason}"],
    )
    if source_url:
        tags.extend(["url_input", "url_only", "copyright_safe_metadata"])
    if url_text_unavailable:
        tags.extend(["url_text_unavailable", "needs_body_copy"])
    quality_status = runtime.capture_quality_status(
        raw_content=combined_content,
        attachment_info=None,
        source_url_processing=sanitized_url_info if source_url else None,
    )
    if source_url and not safe_user_note:
        quality_status["status"] = "보강 필요"
        quality_status["readiness"] = "원문 링크와 메타데이터만 있어 투자 판단 전 본문 또는 사용자 메모 보강 필요"
        quality_status["warnings"] = sorted(
            set([*(quality_status.get("warnings") or []), "URL-only 저장"])
        )
    fingerprint = runtime.news_item_fingerprint(title, combined_content, source_url_for_storage)
    now = runtime.current_storage_timestamp()
    return {
        "id": fingerprint[:16],
        "fingerprint": fingerprint,
        "title": title,
        "scope": inferred_scope,
        "scope_label": runtime.news_scope_label(inferred_scope),
        "scope_reason": scope_reason,
        "source_type": "news",
        "source_url": source_url_for_storage,
        "raw_content": combined_content,
        "summary": runtime.summarize_capture(combined_content),
        "safe_user_note": safe_user_note,
        "safe_url_excerpt": safe_url_excerpt,
        "copyright_policy": {
            "mode": "metadata_only",
            "full_article_body_stored": False,
            "allowed_fields": ["title", "source_url", "source_title", "short_user_note", "short_excerpt", "analysis_summary"],
            "message": "뉴스/기사 원문 본문은 저장하지 않고 링크와 짧은 자체 분석 메모만 보관합니다.",
        },
        "confidence": float(payload.get("confidence") or 0.78),
        "tags": sorted(set(tags)),
        "capture_quality": quality_status,
        "source_url_processing": sanitized_url_info if source_url else None,
        "input_preview": runtime.capture_preview_text(
            "\n".join(value for value in [raw_content, f"웹사이트 주소: {source_url}" if source_url else ""] if value)
        ),
        "document_preview": runtime.capture_preview_text(safe_url_excerpt or url_info.get("note")),
        "needs_body_copy": bool(url_text_unavailable or (source_url and not safe_user_note)),
        "url_text_unavailable": url_text_unavailable,
        "created_at": now,
        "updated_at": now,
        "promoted": False,
        "promoted_storage": None,
    }
