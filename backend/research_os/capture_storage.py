"""Research capture storage orchestration helpers."""

from __future__ import annotations

from typing import Protocol

from research_os.models import CapturedResearchItem, InjectedDataPoint, ResearchCaptureRequest, ResearchCaptureResponse


class CaptureStorageRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while capture storage is split out."""


def save_thesis_impact_report(
    runtime: CaptureStorageRuntime,
    *,
    impact,
    ticker: str,
    vault_dir,
    linked_capture_file: str | None = None,
):
    storage_date = runtime.current_storage_date()
    manifest_extra = {
        "summary": impact.summary,
        "overall_impact": impact.overall_impact.value,
        "source_count": impact.source_count,
        "findings": [item.model_dump(mode="json") for item in impact.findings],
        "watch_item_signals": [
            item.model_dump(mode="json") for item in impact.watch_item_signals
        ],
        "next_actions": impact.next_actions,
    }
    if linked_capture_file is not None:
        manifest_extra["linked_capture_file"] = linked_capture_file
    impact.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="thesis-impact-review",
        markdown=runtime.render_thesis_impact_markdown(impact, storage_date),
        structured_payload=impact.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, manifest_extra),
        report_date=storage_date,
    )
    return impact


def save_capture_request(
    runtime: CaptureStorageRuntime,
    request: ResearchCaptureRequest,
    settings,
    attachment_info: dict | None = None,
    source_url_processing: dict | None = None,
    input_preview_override: str | None = None,
    document_preview_override: str | None = None,
) -> ResearchCaptureResponse:
    ticker = runtime.ensure_verified_ticker(request.ticker, settings)
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    storage_date = runtime.current_storage_date()
    tags = runtime.merge_research_tags(
        runtime.infer_capture_tags(request.raw_content, request.tags),
        runtime.classification_system_tags(request.ticker, request.source_type),
    )
    raw_content_hash = runtime.content_fingerprint(request.raw_content)
    duplicate_check = runtime.detect_capture_duplicate(
        vault_dir=vault_dir,
        ticker=ticker,
        title=request.title,
        raw_content=request.raw_content,
        source_url=request.source_url,
        content_hash=raw_content_hash,
    )
    captured_item = CapturedResearchItem(
        ticker=ticker,
        title=request.title,
        summary=runtime.summarize_capture(request.raw_content),
        source_type=request.source_type,
        source_url=request.source_url,
        as_of=request.as_of,
        confidence=request.confidence,
        tags=tags,
    )

    linked_impact = None
    if request.run_thesis_impact:
        impact_data = [
            InjectedDataPoint(
                source_type=request.source_type,
                label=request.title,
                value=request.raw_content,
                as_of=request.as_of,
                source_url=request.source_url,
                confidence=request.confidence,
            )
        ]
        theses, watch_items = runtime.extract_manifest_theses_and_watch_items(ticker, vault_dir)
        linked_impact = runtime.evaluate_thesis_impact(ticker, impact_data, theses, watch_items)
        linked_impact.saved_to_research_memory = request.save_result

    quality_status = runtime.capture_quality_status(
        raw_content=request.raw_content,
        attachment_info=attachment_info,
        source_url_processing=source_url_processing,
    )

    response = ResearchCaptureResponse(
        captured_item=captured_item,
        linked_impact=linked_impact,
        saved_to_research_memory=request.save_result,
        attachment=attachment_info,
        source_url_processing=source_url_processing,
        capture_quality=quality_status,
        duplicate_check=duplicate_check,
        input_preview=runtime.capture_preview_text(
            request.raw_content if input_preview_override is None else input_preview_override
        ),
        document_preview=runtime.capture_preview_text(
            (attachment_info or {}).get("extracted_text")
            if document_preview_override is None
            else document_preview_override
        ),
    )

    if request.save_result:
        manifest_extra = {
            "summary": captured_item.summary,
            "source_type": runtime.enum_or_str_value(captured_item.source_type),
            "source_url": captured_item.source_url,
            "confidence": captured_item.confidence,
            "tags": captured_item.tags,
            "attachment": attachment_info,
            "source_url_processing": source_url_processing,
            "capture_quality": quality_status,
            "capture_quality_status": quality_status["status"],
            "content_hash": raw_content_hash,
            "duplicate_check": duplicate_check,
            "linked_impact": linked_impact.model_dump(mode="json")
            if linked_impact
            else None,
        }
        if duplicate_check.get("is_duplicate_suspected"):
            manifest_extra["duplicate_reason"] = duplicate_check.get("reason")
            manifest_extra["duplicate_of"] = duplicate_check.get("matched_relative_path")
        response.storage = runtime.save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="research-capture",
            markdown=runtime.render_research_capture_markdown(
                captured_item,
                request.raw_content,
                storage_date,
                attachment_info,
            ),
            structured_payload={
                **response.model_dump(mode="json"),
                "raw_content": request.raw_content,
                "attachment": attachment_info,
            },
            manifest_entry=runtime.manifest_with_ticker_verification(ticker, manifest_extra),
            report_date=storage_date,
            file_suffix=request.title,
        )
        if response.storage:
            saved_entry = next(
                (
                    entry
                    for entry in runtime.read_manifest(vault_dir)
                    if entry.get("file_name") == response.storage.file_name
                    and str(entry.get("ticker") or "").upper() == ticker
                ),
                None,
            )
            if saved_entry:
                response.rag_document = runtime.upsert_research_memory_document(
                    vault_dir=vault_dir,
                    entry=saved_entry,
                )

        if linked_impact is not None:
            linked_impact = save_thesis_impact_report(
                runtime,
                impact=linked_impact,
                ticker=ticker,
                vault_dir=vault_dir,
                linked_capture_file=response.storage.file_name if response.storage else None,
            )

        if ticker not in runtime.special_research_keys:
            try:
                runtime.synthesize_and_save_dossier(ticker, settings, save_result=True)
            except Exception as exc:
                runtime.append_jsonl(
                    runtime.user_state_dir(settings) / "dossier_refresh_errors.jsonl",
                    {
                        "ticker": ticker,
                        "at": runtime.current_storage_timestamp(),
                        "source": "research_capture",
                        "error": str(exc),
                    },
                )

    return response
