"""Research-memory OCR reprocessing helpers."""

from __future__ import annotations

import json
from typing import Protocol


class ResearchMemoryOcrRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while OCR handling is split out."""


def attachment_needs_ocr_reprocess(runtime: ResearchMemoryOcrRuntime, attachment: dict | None) -> bool:
    if not isinstance(attachment, dict):
        return False
    file_name = attachment.get("file_name")
    mime_type = attachment.get("mime_type")
    if not (runtime.is_pdf_attachment(file_name, mime_type) or runtime.is_image_attachment(file_name, mime_type)):
        return False
    profile = attachment.get("extraction_profile") if isinstance(attachment.get("extraction_profile"), dict) else {}
    note = str(attachment.get("text_extraction") or "")
    char_count = int(attachment.get("extraction_char_count") or 0)
    if char_count > 0 and attachment.get("extracted_text"):
        return False
    return bool(
        char_count == 0
        or profile.get("ocr_status") in {"unavailable", "error", "empty"}
        or "언어팩" in note
        or "Tesseract" in note
        or "OCR" in note.upper()
    )


def apply_attachment_extraction_result(
    runtime: ResearchMemoryOcrRuntime,
    attachment: dict,
    extraction: dict,
    *,
    settings,
    raw_context: str = "",
) -> dict:
    updated = {**attachment}
    previous_note = updated.get("text_extraction")
    extracted_text = extraction.get("extracted_text") or ""
    extraction_note = extraction.get("text_extraction") or previous_note or "OCR 재처리 결과 없음"
    fallback_context = runtime.render_attachment_signal_context(
        updated.get("file_name"),
        updated.get("mime_type"),
        extraction_note,
    )
    investment_scope = runtime.infer_capture_investment_scope(
        "\n\n".join(
            value
            for value in [raw_context, fallback_context, extracted_text]
            if value
        ),
        settings,
    )
    updated.update(
        {
            "text_extraction": extraction_note,
            "extracted_text": extracted_text,
            "document_type": extraction.get("document_type") or updated.get("document_type"),
            "extraction_quality": extraction.get("extraction_quality"),
            "extraction_char_count": extraction.get("extraction_char_count") or len(extracted_text),
            "extraction_preview": extraction.get("extraction_preview") or extracted_text[:500],
            "extraction_warnings": extraction.get("extraction_warnings") or [],
            "extraction_profile": extraction.get("extraction_profile") or {},
            "fallback_analysis_context": fallback_context,
            "inferred_investment_scope": investment_scope,
            "ocr_reprocessed_at": runtime.current_storage_timestamp(),
            "previous_text_extraction": previous_note,
        }
    )
    return updated


def render_ocr_reprocess_section(runtime: ResearchMemoryOcrRuntime, attachment: dict) -> str:
    profile = attachment.get("extraction_profile") if isinstance(attachment.get("extraction_profile"), dict) else {}
    lines = [
        f"- 파일명: {attachment.get('file_name') or 'n/a'}",
        f"- 처리 상태: {attachment.get('text_extraction') or 'n/a'}",
        f"- 추출 본문: {int(attachment.get('extraction_char_count') or 0):,}자",
        f"- 추출 품질: {attachment.get('extraction_quality') or '미평가'}",
        f"- OCR 상태: {profile.get('ocr_status') or '미확인'}",
        f"- OCR 언어: {profile.get('ocr_language') or 'kor+eng'}",
        f"- 재처리 시각: {attachment.get('ocr_reprocessed_at') or runtime.current_storage_timestamp()}",
    ]
    preview = str(attachment.get("extraction_preview") or "").strip()
    if preview:
        lines.extend(["", "### 추출 미리보기", "", preview[:2000]])
    warnings = attachment.get("extraction_warnings") or []
    if warnings:
        lines.extend(["", "### 경고", *[f"- {warning}" for warning in warnings]])
    return "\n".join(lines)


def reprocess_research_memory_ocr(
    runtime: ResearchMemoryOcrRuntime,
    settings,
    *,
    include_archived: bool = False,
    save_result: bool = True,
    limit: int | None = None,
    force: bool = False,
) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    entries = [entry for entry in runtime.read_manifest(vault_dir) if isinstance(entry, dict)]
    if limit is not None:
        entries = entries[: max(0, int(limit))]
    checked_count = 0
    candidate_count = 0
    reprocessed_count = 0
    skipped_archived_count = 0
    missing_file_count = 0
    failed_count = 0
    rag_updated_count = 0
    samples: list[dict] = []

    for entry in entries:
        if not include_archived and runtime.is_archived_research_entry(entry):
            skipped_archived_count += 1
            continue
        checked_count += 1
        attachment = entry.get("attachment") if isinstance(entry.get("attachment"), dict) else None
        if not attachment:
            continue
        if not force and not attachment_needs_ocr_reprocess(runtime, attachment):
            continue
        if force and not (
            runtime.is_pdf_attachment(attachment.get("file_name"), attachment.get("mime_type"))
            or runtime.is_image_attachment(attachment.get("file_name"), attachment.get("mime_type"))
        ):
            continue
        candidate_count += 1
        attachment_path = runtime.resolve_attachment_file_path(vault_dir, attachment)
        if not attachment_path:
            missing_file_count += 1
            continue
        try:
            file_bytes = attachment_path.read_bytes()
            extraction = runtime.extract_uploaded_file_text(
                file_bytes,
                attachment.get("file_name"),
                attachment.get("mime_type"),
                source_path=attachment_path,
            )
        except Exception as exc:
            failed_count += 1
            samples.append(
                {
                    "ticker": entry.get("ticker"),
                    "file_name": entry.get("file_name"),
                    "attachment_file_name": attachment.get("file_name"),
                    "status": "failed",
                    "error": str(exc),
                }
            )
            continue
        payload = runtime.read_manifest_entry_payload(entry, vault_dir)
        raw_context = "\n\n".join(
            value
            for value in [
                str(entry.get("summary") or ""),
                str(payload.get("raw_content") or "") if isinstance(payload, dict) else "",
            ]
            if value
        )
        updated_attachment = apply_attachment_extraction_result(
            runtime,
            attachment,
            extraction,
            settings=settings,
            raw_context=raw_context,
        )
        updated_entry = {**entry, "attachment": updated_attachment}
        updated_entry["ocr_reprocessed_at"] = updated_attachment.get("ocr_reprocessed_at")
        scope = updated_attachment.get("inferred_investment_scope") or {}
        if scope:
            updated_entry["inferred_investment_scope"] = scope
            updated_entry["tags"] = runtime.merge_research_tags(
                runtime.strip_quality_rebuild_tags(updated_entry.get("tags")),
                scope.get("tags") or [],
            )
        capture_quality = updated_entry.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality = {**capture_quality}
            capture_quality["ocr_reprocessed_at"] = updated_attachment.get("ocr_reprocessed_at")
            capture_quality["ocr_status"] = (updated_attachment.get("extraction_profile") or {}).get("ocr_status")
            if int(updated_attachment.get("extraction_char_count") or 0) > 0:
                capture_quality["status"] = "정상"
                capture_quality["readiness"] = "OCR 본문 반영 완료"
            updated_entry["capture_quality"] = capture_quality

        if save_result:
            runtime.update_manifest(vault_dir=vault_dir, entry=updated_entry)
            json_path = runtime.manifest_entry_json_path(entry, vault_dir)
            if json_path and isinstance(payload, dict):
                updated_payload = {**payload, "attachment": updated_attachment}
                if isinstance(updated_payload.get("capture_quality"), dict):
                    payload_quality = {**updated_payload["capture_quality"]}
                    payload_quality["ocr_reprocessed_at"] = updated_attachment.get("ocr_reprocessed_at")
                    payload_quality["ocr_status"] = (updated_attachment.get("extraction_profile") or {}).get("ocr_status")
                    if int(updated_attachment.get("extraction_char_count") or 0) > 0:
                        payload_quality["status"] = "정상"
                        payload_quality["readiness"] = "OCR 본문 반영 완료"
                    updated_payload["capture_quality"] = payload_quality
                json_path.write_text(
                    json.dumps(updated_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            runtime.upsert_markdown_tail_section(
                runtime.manifest_entry_markdown_path(entry, vault_dir),
                runtime.ocr_reprocess_marker,
                render_ocr_reprocess_section(runtime, updated_attachment),
            )
            runtime.upsert_research_memory_document(
                vault_dir=vault_dir,
                entry=updated_entry,
                full_text="\n\n".join(
                    value
                    for value in [
                        runtime.read_manifest_entry_text(vault_dir, updated_entry),
                        updated_attachment.get("extracted_text"),
                    ]
                    if value
                ),
            )
            rag_updated_count += 1

        reprocessed_count += 1
        if len(samples) < 12:
            samples.append(
                {
                    "ticker": entry.get("ticker"),
                    "file_name": entry.get("file_name"),
                    "attachment_file_name": attachment.get("file_name"),
                    "status": "success",
                    "text_extraction": updated_attachment.get("text_extraction"),
                    "char_count": updated_attachment.get("extraction_char_count"),
                    "ocr_status": (updated_attachment.get("extraction_profile") or {}).get("ocr_status"),
                }
            )

    rag_backfill = runtime.backfill_research_memory_documents_from_manifest(vault_dir) if save_result else None
    return {
        "status": "success",
        "module": "research_memory_ocr_reprocess",
        "save_result": save_result,
        "include_archived": include_archived,
        "force": force,
        "checked_count": checked_count,
        "skipped_archived_count": skipped_archived_count,
        "candidate_count": candidate_count,
        "reprocessed_count": reprocessed_count,
        "missing_file_count": missing_file_count,
        "failed_count": failed_count,
        "rag_updated_count": rag_updated_count,
        "samples": samples,
        "rag_backfill": rag_backfill,
        "ocr_runtime": runtime.ocr_runtime_status(),
        "next_actions": [
            "OCR 본문이 반영된 파일은 저장 데이터/RAG/Dossier에서 다시 활용됩니다.",
            "본문 0자가 남는 PDF는 원본이 이미지 품질이 낮거나 보안/렌더링 제한이 있을 수 있어 원문 텍스트 입력으로 보강하세요.",
        ],
    }
