"""Source URL preview response builder for the research console."""

from __future__ import annotations

from research_os.web_capture import (
    clean_web_article_text,
    fetch_capture_source_url,
    render_source_url_context,
)


def build_source_url_preview_response(source_url: str) -> dict:
    """Fetch a URL and return the console preview payload without saving data."""
    url_info = fetch_capture_source_url(source_url)
    text = str(url_info.get("text") or "").strip()
    original_text = str(url_info.get("original_text") or "").strip()
    preview = clean_web_article_text(text)[:12000]
    original_preview = clean_web_article_text(original_text)[:12000] if original_text else ""
    return {
        "status": "success",
        "module": "source_url_preview",
        "source_url_processing": url_info,
        "source_url": source_url,
        "final_url": url_info.get("final_url") or source_url,
        "title": url_info.get("title") or "",
        "original_title": url_info.get("original_title") or "",
        "language": url_info.get("language") or "unknown",
        "translation_status": url_info.get("translation_status") or "unknown",
        "translation_note": url_info.get("translation_note") or "",
        "content_type": url_info.get("content_type") or "unknown",
        "preview": preview,
        "analysis_preview": preview,
        "original_preview": original_preview,
        "context": render_source_url_context(url_info),
        "text_length": len(preview),
        "note": url_info.get("note") or "",
    }
