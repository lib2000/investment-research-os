"""Automatic research capture orchestration helpers."""

from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException

from research_os.models import AutoResearchCaptureRequest, ResearchCaptureRequest, ResearchCaptureResponse


class AutoCaptureRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while auto capture is split out."""


def auto_capture_research_item(
    runtime: AutoCaptureRuntime,
    request: AutoResearchCaptureRequest,
    settings,
) -> ResearchCaptureResponse:
    raw_content = (request.raw_content or "").strip()
    original_user_raw_content = raw_content
    source_url = (request.source_url or "").strip()
    raw_translation_info = (
        runtime.foreign_text_korean_digest(raw_content, "")
        if raw_content
        else {"status": "empty", "text": "", "language": "unknown", "note": ""}
    )
    if raw_translation_info.get("status") == "local_digest" and raw_translation_info.get("text"):
        raw_content = str(raw_translation_info["text"]).strip()
    url_info = runtime.fetch_capture_source_url(source_url) if source_url else {}
    url_body_context = runtime.render_source_url_body(url_info)
    url_title_context = (
        f"웹사이트 제목: {url_info.get('title')}"
        if source_url and url_info.get("title")
        else ""
    )
    original_input_preview = "\n".join(
        value
        for value in [
            raw_content,
            f"웹사이트 주소: {source_url}" if source_url else "",
        ]
        if value
    )
    if original_user_raw_content != raw_content:
        original_input_preview = "\n\n".join(
            value
            for value in [
                original_user_raw_content,
                "[한국어 분석용 변환본]",
                raw_content,
                f"웹사이트 주소: {source_url}" if source_url else "",
            ]
            if value
        )
    if not raw_content and not request.file_content_base64 and not source_url:
        raise HTTPException(
            status_code=422,
            detail="저장할 텍스트, 웹사이트 주소 또는 파일 내용이 비어 있습니다.",
        )
    url_text_unavailable = (
        source_url
        and runtime.is_unusable_source_url(url_info)
        and not raw_content
        and not request.file_content_base64
    )
    if url_text_unavailable:
        raw_content = runtime.render_url_only_capture_context(source_url, url_info)
        original_input_preview = raw_content

    inference_content = "\n\n".join(
        value for value in [raw_content, url_title_context, url_body_context] if value
    )
    attachment_signal_context = runtime.render_attachment_signal_context(
        request.file_name,
        request.file_mime_type,
    )
    if attachment_signal_context:
        inference_content = "\n\n".join(
            value for value in [inference_content, attachment_signal_context] if value
        )
    if request.file_name:
        inference_content = "\n".join(
            value for value in [inference_content, f"첨부 파일명: {request.file_name}"] if value
        )
    if runtime.is_pdf_attachment(request.file_name, request.file_mime_type) and request.file_content_base64:
        pdf_bytes = runtime.decode_attachment_base64(request.file_content_base64)
        if pdf_bytes:
            pdf_text, pdf_note = runtime.extract_pdf_text(pdf_bytes)
            pdf_inference_context = "\n".join(
                value
                for value in [
                    f"첨부 PDF 텍스트 추출 상태: {pdf_note}",
                    f"첨부 PDF 본문:\n{pdf_text[:20000]}" if pdf_text else "",
                ]
                if value
            )
            inference_content = "\n\n".join(
                value for value in [inference_content, pdf_inference_context] if value
            )

    inferred_ticker, ticker_inference = runtime.infer_capture_ticker(inference_content, settings)
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    attachment_info = (
        runtime.save_capture_attachment(
            vault_dir,
            inferred_ticker,
            runtime.current_storage_date(),
            request,
            settings,
        )
        if request.save_result
        else None
    )
    attachment_context = runtime.render_attachment_context(request, attachment_info)
    if attachment_context and attachment_context not in raw_content:
        raw_content = "\n\n".join(value for value in [raw_content, attachment_context] if value)
    if url_body_context and url_body_context not in raw_content:
        raw_content = "\n\n".join(value for value in [raw_content, url_body_context] if value)
    inferred_investment_scope = runtime.infer_capture_investment_scope(
        "\n\n".join(
            value
            for value in [
                raw_content,
                attachment_signal_context,
                (attachment_info or {}).get("extracted_text"),
            ]
            if value
        ),
        settings,
    )
    investment_scope_context = runtime.render_investment_scope_context(inferred_investment_scope)
    if investment_scope_context and investment_scope_context not in raw_content:
        raw_content = "\n\n".join(value for value in [raw_content, investment_scope_context] if value)
    if attachment_info is not None:
        attachment_info["inferred_investment_scope"] = inferred_investment_scope
    source_type = (
        ticker_inference
        if inferred_ticker in runtime.special_research_keys - {"INBOX"}
        else runtime.infer_capture_source_type(raw_content, request.file_name)
    )
    tags = [f"auto_ticker:{ticker_inference}", "auto_classified"]
    tags = runtime.merge_research_tags(
        tags,
        runtime.classification_system_tags(inferred_ticker, source_type, ticker_inference),
    )
    tags = runtime.infer_capture_tags(raw_content, tags)
    tags.extend(inferred_investment_scope.get("tags") or [])
    if request.file_name:
        tags.append("file_input")
    if source_url:
        tags.append("url_input")
        tags.append("web_capture")
    if url_text_unavailable:
        tags.append("url_text_unavailable")
        tags.append("needs_body_copy")
    if raw_translation_info.get("status") == "local_digest":
        tags.append("foreign_text_converted")
    inferred_title = (
        (url_info.get("title") or "").strip()
        if source_url and not request.file_name
        else ""
    ) or runtime.infer_capture_title(raw_content, request.file_name)
    title = runtime.prefix_capture_title(inferred_title, inferred_ticker, ticker_inference)
    source_url_for_storage = (
        url_info.get("final_url")
        or url_info.get("source_url")
        or source_url
        or None
    )
    auto_request = ResearchCaptureRequest(
        ticker=inferred_ticker,
        title=title,
        raw_content=raw_content,
        source_type=source_type,
        source_url=source_url_for_storage,
        confidence=runtime.infer_capture_confidence(
            source_type,
            bool(request.file_name) or bool(url_info.get("text")),
        ),
        tags=tags,
        run_thesis_impact=request.run_thesis_impact
        and inferred_ticker not in runtime.special_research_keys,
        save_result=request.save_result,
    )
    response = runtime.save_capture_request(
        auto_request,
        settings,
        attachment_info=attachment_info,
        source_url_processing=url_info if source_url else None,
        input_preview_override=original_input_preview,
        document_preview_override=(
            (attachment_info or {}).get("extracted_text")
            or url_info.get("text")
            or (runtime.render_url_only_capture_context(source_url, url_info) if url_text_unavailable else "")
            or url_info.get("note")
        ),
    )
    response.captured_item.tags = sorted(set(response.captured_item.tags + tags))
    if inferred_ticker == "INBOX":
        response.captured_item.summary = (
            f"[티커 미확정: INBOX 저장] {response.captured_item.summary}"
        )
    elif inferred_ticker in runtime.special_research_keys - {"INBOX"}:
        response.captured_item.summary = (
            f"[{inferred_ticker} 자동 분류] {response.captured_item.summary}"
        )
    return response
