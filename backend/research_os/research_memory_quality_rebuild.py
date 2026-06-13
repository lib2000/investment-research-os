"""Research-memory quality metadata rebuild orchestration."""

from __future__ import annotations

import json
from typing import Protocol


class ResearchMemoryQualityRebuildRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while quality rebuild is split out."""


def rebuild_research_memory_quality_metadata(
    runtime: ResearchMemoryQualityRebuildRuntime,
    settings,
    *,
    include_archived: bool = False,
    save_result: bool = True,
    limit: int | None = None,
) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    entries = [entry for entry in runtime.read_manifest(vault_dir) if isinstance(entry, dict)]
    if limit is not None:
        entries = entries[: max(0, int(limit))]
    rebuilt_at = runtime.current_storage_timestamp()
    checked_count = 0
    enriched_count = 0
    attachment_count = 0
    markdown_updated_count = 0
    sidecar_updated_count = 0
    rag_updated_count = 0
    skipped_archived_count = 0
    cleaned_count = 0
    themes: dict[str, int] = {}
    matched_interest_count = 0
    matched_holding_count = 0
    samples: list[dict] = []

    for entry in entries:
        if not include_archived and runtime.is_archived_research_entry(entry):
            skipped_archived_count += 1
            continue
        checked_count += 1
        payload = runtime.read_manifest_entry_payload(entry, vault_dir)
        markdown_text = runtime.read_manifest_entry_text(vault_dir, entry)
        context, attachment, attachment_context = runtime.build_quality_rebuild_context(entry, payload, markdown_text)
        markdown_path = runtime.manifest_entry_markdown_path(entry, vault_dir)
        has_previous_quality = bool(
            entry.get("quality_rebuild_version")
            or (isinstance(payload, dict) and payload.get("quality_rebuild_version"))
            or (runtime.quality_rebuild_marker in markdown_text)
        )
        scope = runtime.infer_capture_investment_scope(context, settings)
        scope_context = runtime.render_investment_scope_context(scope)
        scope_tags = scope.get("tags") or []
        has_scope = bool(
            scope.get("theme_candidates")
            or scope.get("matched_interest_tickers")
            or scope.get("matched_interest_sectors")
            or scope.get("matched_portfolio_holdings")
        )
        if attachment:
            attachment_count += 1
        if not has_scope and not attachment_context and not has_previous_quality:
            continue

        updated_entry = {**entry}
        updated_payload = dict(payload) if isinstance(payload, dict) else {}
        updated_attachment = dict(attachment) if isinstance(attachment, dict) else None
        if updated_attachment is not None:
            updated_attachment["fallback_analysis_context"] = attachment_context
            if has_scope:
                updated_attachment["inferred_investment_scope"] = scope
            else:
                updated_attachment.pop("inferred_investment_scope", None)
            updated_entry["attachment"] = updated_attachment
            updated_payload["attachment"] = updated_attachment

        if has_scope:
            updated_entry["inferred_investment_scope"] = scope
        else:
            updated_entry.pop("inferred_investment_scope", None)
        updated_entry["quality_rebuilt_at"] = rebuilt_at
        updated_entry["quality_rebuild_version"] = "attachment-scope-v1"
        updated_entry["tags"] = runtime.merge_research_tags(
            runtime.strip_quality_rebuild_tags(entry.get("tags")),
            scope_tags,
        )
        base_summary = runtime.strip_quality_scope_from_summary(entry.get("summary"))
        if has_scope:
            updated_entry["summary"] = runtime.compact_representative_sentence(
                " ".join(
                    value
                    for value in [
                        base_summary,
                        scope_context.replace("\n", " "),
                    ]
                    if value
                ),
                360,
            )
        elif has_previous_quality and base_summary:
            updated_entry["summary"] = base_summary

        capture_quality = updated_entry.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality = {**capture_quality}
            capture_quality["metadata_enriched"] = True
            capture_quality["quality_rebuilt_at"] = rebuilt_at
            if capture_quality.get("status") == "실패" and has_scope:
                capture_quality["status"] = "보강 필요"
                capture_quality["readiness"] = "본문은 부족하지만 파일명/관심 범위 추론으로 제한 활용 가능"
            updated_entry["capture_quality"] = capture_quality

        if updated_payload:
            if has_scope:
                updated_payload["inferred_investment_scope"] = scope
            else:
                updated_payload.pop("inferred_investment_scope", None)
            updated_payload["quality_rebuilt_at"] = rebuilt_at
            updated_payload["quality_rebuild_version"] = "attachment-scope-v1"
            captured_item = updated_payload.get("captured_item")
            if isinstance(captured_item, dict):
                captured_item = {**captured_item}
                captured_item["tags"] = runtime.merge_research_tags(
                    runtime.strip_quality_rebuild_tags(captured_item.get("tags")),
                    scope_tags,
                )
                captured_summary = runtime.strip_quality_scope_from_summary(captured_item.get("summary"))
                if has_scope and captured_item.get("summary"):
                    captured_item["summary"] = runtime.compact_representative_sentence(
                        f"{captured_summary} {scope_context.replace(chr(10), ' ')}",
                        360,
                    )
                elif has_previous_quality and captured_summary:
                    captured_item["summary"] = captured_summary
                updated_payload["captured_item"] = captured_item
            payload_quality = updated_payload.get("capture_quality")
            if isinstance(payload_quality, dict):
                payload_quality = {**payload_quality}
                payload_quality["metadata_enriched"] = True
                payload_quality["quality_rebuilt_at"] = rebuilt_at
                updated_payload["capture_quality"] = payload_quality

        if save_result:
            runtime.update_manifest(vault_dir=vault_dir, entry=updated_entry)
            json_path = runtime.manifest_entry_json_path(entry, vault_dir)
            if json_path and updated_payload:
                json_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(
                    json.dumps(updated_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                sidecar_updated_count += 1
            section_body = "\n".join(
                value
                for value in [
                    attachment_context if attachment_context or has_scope else "",
                    scope_context,
                    f"재점검 시각: {rebuilt_at}" if attachment_context or has_scope else "",
                ]
                if value
            )
            section_changed = runtime.upsert_quality_rebuild_section(
                markdown_path,
                section_body,
            )
            if section_changed:
                markdown_updated_count += 1
            markdown_for_rag = runtime.read_manifest_entry_text(vault_dir, updated_entry)
            runtime.upsert_research_memory_document(
                vault_dir=vault_dir,
                entry=updated_entry,
                full_text="\n\n".join(
                    value
                    for value in [
                        markdown_for_rag,
                        attachment_context,
                        scope_context,
                    ]
                    if value
                ),
            )
            rag_updated_count += 1

        if has_scope or attachment_context:
            enriched_count += 1
        else:
            cleaned_count += 1
        for candidate in scope.get("theme_candidates", []):
            label = str(candidate.get("label") or candidate.get("key") or "").strip()
            if label:
                themes[label] = themes.get(label, 0) + 1
        if scope.get("matched_interest_tickers") or scope.get("matched_interest_sectors"):
            matched_interest_count += 1
        if scope.get("matched_portfolio_holdings"):
            matched_holding_count += 1
        if len(samples) < 12:
            samples.append(
                {
                    "ticker": updated_entry.get("ticker"),
                    "type": updated_entry.get("type"),
                    "file_name": updated_entry.get("file_name"),
                    "attachment_file_name": (updated_attachment or {}).get("file_name"),
                    "theme_candidates": [
                        item.get("label")
                        for item in scope.get("theme_candidates", [])
                        if item.get("label")
                    ],
                    "matched_interests": [
                        item.get("company_name") or item.get("name") or item.get("ticker")
                        for item in [
                            *(scope.get("matched_interest_tickers") or []),
                            *(scope.get("matched_interest_sectors") or []),
                        ]
                    ][:8],
                    "matched_holdings": [
                        item.get("company_name") or item.get("ticker")
                        for item in scope.get("matched_portfolio_holdings", [])
                    ][:8],
                }
            )

    rag_backfill = runtime.backfill_research_memory_documents_from_manifest(vault_dir) if save_result else None
    thesis_backfill = runtime.backfill_thesis_snapshots_from_manifest(vault_dir) if save_result else None

    return {
        "status": "success",
        "module": "research_memory_quality_rebuild",
        "save_result": save_result,
        "include_archived": include_archived,
        "checked_count": checked_count,
        "skipped_archived_count": skipped_archived_count,
        "enriched_count": enriched_count,
        "attachment_count": attachment_count,
        "markdown_updated_count": markdown_updated_count,
        "sidecar_updated_count": sidecar_updated_count,
        "rag_updated_count": rag_updated_count,
        "cleaned_count": cleaned_count,
        "matched_interest_count": matched_interest_count,
        "matched_holding_count": matched_holding_count,
        "theme_counts": dict(sorted(themes.items(), key=lambda item: item[1], reverse=True)),
        "samples": samples,
        "rag_backfill": rag_backfill,
        "thesis_backfill": thesis_backfill,
        "rebuilt_at": rebuilt_at,
        "next_actions": [
            "저장 데이터 품질 필터에서 본문 보강 필요/OCR 보강 항목을 우선 확인하세요.",
            "관심 범위 후보가 붙은 문서는 RAG 검색과 Dossier 합성에서 다시 활용됩니다.",
            "본문 0자 PDF는 OCR 언어팩 연결 후 다시 업로드하거나 본문을 직접 보강하면 정확도가 더 올라갑니다.",
        ],
    }
