"""Public IR/SEC collection helpers.

This module keeps the collector inside the Investment Research OS backend instead
of running a separate service. It only handles public http/https URLs and stores
safe metadata/extracted text into research memory for RAG reuse.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from re import findall, sub
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl

from research_os.rag_memory import upsert_research_memory_document
from research_os.research_memory import read_manifest, resolve_vault_dir, save_research_markdown
from research_os.web_capture import (
    fetch_capture_source_url,
    is_unusable_source_url,
    render_source_url_body,
    render_source_url_context,
    render_url_only_capture_context,
)

PUBLIC_IR_SEC_KEY = "PUBLIC_IR_SEC"
PUBLIC_IR_SEC_REPORT_TYPE = "public-ir-sec"


class PublicIrSecCollectRequest(BaseModel):
    url: HttpUrl
    target_key: str = Field(default=PUBLIC_IR_SEC_KEY, min_length=1, max_length=64)
    save_result: bool = True
    force: bool = False
    no_screenshot: bool = True
    source_title: str | None = None
    source_provider: str | None = None
    source_type: str | None = None
    source_category: str | None = None
    filing_form: str | None = None
    filing_group: str | None = None
    published_at: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_key(value: str | None, fallback: str = PUBLIC_IR_SEC_KEY) -> str:
    cleaned = sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip().upper()).strip("_")
    return cleaned or fallback


def _safe_title(value: str | None, fallback: str = "공개 IR/SEC 자료") -> str:
    title = " ".join(str(value or "").split())
    return title[:140] or fallback


def _host_label(source_url: str) -> tuple[str, str, list[str]]:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    tags = ["public_ir_sec"]
    if host.endswith("sec.gov"):
        return "SEC EDGAR", "official_filing", [*tags, "sec", "edgar", "official_filing"]
    if "investor" in host or "/ir" in path or "investors" in path:
        return "공개 IR", "ir_presentation", [*tags, "ir", "investor_relations"]
    return host or "공개 웹", "other", tags


def _summary_from_text(
    title: str,
    text: str,
    source_provider: str,
    *,
    extracted_body_available: bool = True,
) -> str:
    compact = " ".join((text or "").split())
    if compact and extracted_body_available:
        return f"{source_provider} 공개 자료 `{title}`에서 추출한 본문 {len(compact):,}자를 저장했습니다. {compact[:260]}"
    return f"{source_provider} 공개 자료 `{title}` URL과 메타데이터를 저장했습니다. 본문은 후속 복사/파일 보강이 필요합니다."


def _capture_quality(
    url_info: dict[str, Any],
    body_text: str,
    *,
    extracted_body_available: bool = True,
) -> dict[str, Any]:
    status = str(url_info.get("status") or "unknown")
    body_chars = len(body_text or "") if extracted_body_available else 0
    url_unavailable = is_unusable_source_url(url_info) or not extracted_body_available
    if url_unavailable:
        quality_status = "보강 필요"
        action = "본문 추출이 제한되었습니다. URL-only 보관 후 원문 복사 또는 파일 첨부로 보강하세요."
    elif body_chars >= 500:
        quality_status = "정상"
        action = "추천/리포트/RAG 근거로 바로 활용 가능합니다."
    elif body_chars:
        quality_status = "보강 필요"
        action = "본문이 짧습니다. 원문 PDF/본문 복사로 보강하면 분석 품질이 올라갑니다."
    else:
        quality_status = "보강 필요"
        action = "본문 추출이 제한되었습니다. URL-only 보관 후 원문 복사 또는 파일 첨부로 보강하세요."
    return {
        "status": quality_status,
        "source_status": status,
        "body_chars": body_chars,
        "url_text_unavailable": url_unavailable,
        "needs_body_copy": url_unavailable or body_chars < 500,
        "recommended_action": action,
    }


def _render_markdown(payload: dict[str, Any], body_text: str) -> str:
    lines = [
        f"# {payload['title']}",
        "",
        "## 공개 IR/SEC 수집 메타데이터",
        f"- 출처: {payload['source_provider']}",
        f"- 원본 URL: {payload['source_url']}",
        f"- 최종 URL: {payload.get('final_url') or payload['source_url']}",
        f"- 처리 상태: {payload['source_url_processing'].get('status')}",
        f"- 본문 글자 수: {payload['body_chars']}",
        f"- 문서 링크 추정: {payload['doc_links']}",
        f"- 저장 정책: {payload['copyright_policy']}",
        f"- 품질 상태: {payload['capture_quality'].get('status')}",
        "",
        "## 요약",
        payload.get("summary") or "요약 없음",
        "",
        "## 후속 활용",
        "- 보유/관심 종목과 직접 연결되는 내용은 최근 1주 자료, RAG 검색, 오늘 추천 근거에 재사용됩니다.",
        "- 본문이 제한된 자료는 URL-only로 남기고, 원문 복사/파일 첨부로 보강하세요.",
        "",
        "## 본문/URL 맥락",
    ]
    if body_text:
        lines.append(body_text[:30000])
    else:
        lines.append(render_url_only_capture_context(payload["source_url"], payload.get("source_url_processing") or {}))
    return "\n".join(lines).strip() + "\n"


def _find_existing_entry(vault_dir, source_url: str, target_key: str) -> dict[str, Any] | None:
    normalized_url = source_url.strip()
    normalized_key = _safe_key(target_key)
    for entry in reversed(read_manifest(vault_dir)):
        if str(entry.get("ticker") or "").upper() != normalized_key:
            continue
        if str(entry.get("source_url") or "").strip() == normalized_url:
            return entry
    return None


def collect_public_ir_sec_url(request: PublicIrSecCollectRequest, settings: Any) -> dict[str, Any]:
    source_url = str(request.url).strip()
    target_key = _safe_key(request.target_key)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    existing_entry = _find_existing_entry(vault_dir, source_url, target_key)
    if existing_entry and not request.force:
        return {
            "status": "skipped_existing",
            "module": "public_ir_sec_collection",
            "message": "이미 같은 URL이 공개 IR/SEC 저장 데이터에 있습니다. force=true로 다시 수집할 수 있습니다.",
            "source_url": source_url,
            "target_key": target_key,
            "existing_entry": existing_entry,
            "storage": {
                "relative_path": existing_entry.get("relative_path"),
                "json_relative_path": existing_entry.get("json_relative_path"),
            },
            "rag_document": None,
        }

    url_info = fetch_capture_source_url(source_url)
    extracted_body_text = render_source_url_body(url_info)
    body_text = extracted_body_text
    extracted_body_available = bool(extracted_body_text) and not is_unusable_source_url(url_info)
    if not body_text and url_info:
        body_text = render_source_url_context(url_info)
    provider, source_type, tags = _host_label(source_url)
    provider = _safe_title(request.source_provider, provider)
    source_type = _safe_key(request.source_type, source_type).lower()
    title = _safe_title(request.source_title or url_info.get("title") or url_info.get("original_title"), provider)
    source_category = _safe_title(request.source_category, "공개 IR/SEC 자료")
    filing_form = _safe_title(request.filing_form, "")
    filing_group = _safe_key(request.filing_group, "").lower()
    published_at = _safe_title(request.published_at, "")
    metadata_tags = [
        value
        for value in [
            source_category,
            filing_form,
            filing_group,
            published_at,
        ]
        if value
    ]
    body_chars = len(extracted_body_text or "")
    context_chars = len(body_text or "")
    doc_links = len(set(findall(r"https?://[^\s)\]]+", body_text or "")))
    quality = _capture_quality(
        url_info,
        extracted_body_text,
        extracted_body_available=extracted_body_available,
    )
    policy = (
        "공개 http/https 자료만 수집합니다. 자동 로그인, 자동 전송, 웹 채팅창 자동 수집은 하지 않으며 "
        "본문 추출 제한 자료는 URL/메타데이터 중심으로 보관합니다."
    )
    payload = {
        "status": "success" if body_chars else "url_only_saved",
        "module": "public_ir_sec_collection",
        "target_key": target_key,
        "source_url": source_url,
        "final_url": url_info.get("final_url") or source_url,
        "source_provider": provider,
        "source_type": source_type,
        "source_category": source_category,
        "filing_form": filing_form,
        "filing_group": filing_group,
        "published_at": published_at,
        "title": title,
        "summary": _summary_from_text(
            title,
            extracted_body_text,
            provider,
            extracted_body_available=extracted_body_available,
        ),
        "body_chars": body_chars,
        "context_chars": context_chars,
        "doc_links": doc_links,
        "collected_at": _utc_now_iso(),
        "no_screenshot": request.no_screenshot,
        "copyright_policy": policy,
        "source_url_processing": url_info,
        "capture_quality": quality,
        "tags": sorted(
            set(
                [
                    *tags,
                    "rag_candidate",
                    "codex_app_source",
                    *metadata_tags,
                    *( ["url_text_unavailable", "needs_body_copy"] if quality.get("needs_body_copy") else [] ),
                ]
            )
        ),
        "storage": None,
        "rag_document": None,
    }
    if not request.save_result:
        return payload

    markdown = _render_markdown(payload, body_text)
    manifest_entry = {
        "title": title,
        "summary": payload["summary"],
        "scope": "public_ir_sec",
        "source_type": source_type,
        "source_url": source_url,
        "final_url": payload["final_url"],
        "source_provider": provider,
        "source_category": source_category,
        "filing_form": filing_form,
        "filing_group": filing_group,
        "published_at": published_at,
        "confidence": 0.84 if body_chars >= 500 else 0.62,
        "source_confidence": 0.84 if body_chars >= 500 else 0.62,
        "tags": payload["tags"],
        "capture_quality": quality,
        "capture_quality_status": quality["status"],
        "source_url_processing": url_info,
        "copyright_policy": policy,
        "body_chars": body_chars,
        "context_chars": context_chars,
        "doc_links": doc_links,
        "collected_at": payload["collected_at"],
    }
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker=target_key,
        report_type=PUBLIC_IR_SEC_REPORT_TYPE,
        markdown=markdown,
        structured_payload={**payload, "extracted_text": body_text[:30000]},
        manifest_entry=manifest_entry,
        report_date=date.today(),
        file_suffix=title,
    )
    payload["storage"] = storage.model_dump(mode="json")
    saved_entry = next(
        (
            entry for entry in read_manifest(vault_dir)
            if entry.get("file_name") == storage.file_name and str(entry.get("ticker") or "").upper() == target_key
        ),
        None,
    )
    if saved_entry:
        payload["rag_document"] = upsert_research_memory_document(
            vault_dir=vault_dir,
            entry=saved_entry,
            full_text=markdown,
        )
    return payload


def public_ir_sec_status_payload(settings: Any, limit: int = 10) -> dict[str, Any]:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    entries = [
        entry for entry in read_manifest(vault_dir)
        if str(entry.get("scope") or "") == "public_ir_sec"
        or str(entry.get("ticker") or "").upper() == PUBLIC_IR_SEC_KEY
        or str(entry.get("type") or "") == PUBLIC_IR_SEC_REPORT_TYPE
    ]
    entries.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("file_name") or "")), reverse=True)
    recent = entries[: max(1, min(limit, 50))]
    needs_body = [entry for entry in entries if (entry.get("capture_quality") or {}).get("needs_body_copy")]
    next_actions = [
        "공개 IR/SEC URL을 입력해 보유/관심 종목과 연결되는 자료를 수집하세요.",
        "URL-only 자료는 원문 링크 확인 또는 파일/본문 복사로 보강하세요.",
        "최근 1주 자료와 오늘 추천 근거에서 공개 IR/SEC 연결 여부를 확인하세요.",
    ]
    empty_state = None if entries else {
        "title": "아직 수집된 공개 IR/SEC 자료가 없습니다.",
        "message": "공개 SEC/IR URL을 수집하면 저장 데이터, 최근 1주 자료, RAG, 오늘 추천 근거에 순서대로 연결됩니다.",
    }
    return {
        "status": "success",
        "module": "public_ir_sec_status",
        "storage_key": PUBLIC_IR_SEC_KEY,
        "entry_count": len(entries),
        "recent_count": len(recent),
        "needs_body_copy_count": len(needs_body),
        "policy": "공개 IR/SEC 자료만 수집하고 제한 자료는 URL/메타데이터 중심으로 보관합니다.",
        "empty_state": empty_state,
        "next_actions": next_actions,
        "recent_entries": recent,
    }
