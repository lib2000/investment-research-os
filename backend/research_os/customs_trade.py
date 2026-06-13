"""Helpers for Korea Customs trade-data quality policy."""

from __future__ import annotations


CUSTOMS_VALID_STORAGE_POLICY = (
    "실제 수출입 수치가 있는 행만 research_vault/CUSTOMS와 RAG 색인에 저장합니다."
)
CUSTOMS_EMPTY_STORAGE_POLICY = (
    "실제 수출입 수치가 없는 빈 응답과 서비스 상태 메시지는 저장/RAG 반영하지 않습니다."
)


def customs_trade_quality_metadata(has_valid_data: bool, valid_row_count: int = 0) -> dict[str, object]:
    """Return UI/API metadata for deciding whether customs data can be stored."""
    if has_valid_data:
        return {
            "data_quality": "valid_trade_rows",
            "data_quality_label": "수출입 수치 확인",
            "storage_policy": CUSTOMS_VALID_STORAGE_POLICY,
            "storage_skip_expected": False,
            "next_action": "수출주, 재고 부담, 환율 민감 섹터 점검에 보조 신호로 반영하세요.",
        }
    return {
        "data_quality": "no_valid_trade_rows",
        "data_quality_label": "실제 수출입 수치 없음",
        "storage_policy": CUSTOMS_EMPTY_STORAGE_POLICY,
        "storage_skip_expected": True,
        "next_action": (
            "기간, HS코드, 국가 조건을 재확인하고 수출입총괄(GW) 진단의 권한/응답 상태를 확인하세요."
        ),
    }


def save_customs_trade_snapshot(runtime, snapshot: dict, settings) -> dict:
    if not snapshot.get("has_valid_data"):
        return {
            **snapshot,
            "storage_skipped": True,
            "storage_skip_reason": str(
                snapshot.get("storage_policy")
                or "실제 수출입 수치가 없어 저장/RAG 반영을 건너뜁니다."
            ),
        }
    storage_date = runtime.current_storage_date()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    markdown = runtime.render_customs_trade_markdown(snapshot, storage_date)
    summary = (
        f"관세청 수출입 동향 {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}: "
        f"{'; '.join(snapshot.get('key_takeaways', [])[:2]) or '요약 없음'}"
    )
    source_confidence = 0.88 if not snapshot.get("warnings") else 0.72
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker="CUSTOMS",
        report_type="customs-trade-brief",
        markdown=markdown,
        structured_payload=snapshot,
        manifest_entry={
            "summary": summary,
            "source": snapshot.get("source"),
            "source_confidence": source_confidence,
            "tags": ["customs", "trade", "exports", "imports", "inventory", "macro", "sector"],
            "sector_implications": snapshot.get("sector_implications", []),
            "release_schedule": snapshot.get("release_schedule"),
        },
        report_date=storage_date,
        file_suffix=f"{snapshot.get('start_yymm')}-{snapshot.get('end_yymm')}",
    )
    rag_document = runtime.upsert_saved_workflow_rag_document(
        vault_dir=vault_dir,
        storage=storage,
        storage_key="CUSTOMS",
        report_type="customs-trade-brief",
        summary=summary,
        markdown=markdown,
        tags=["customs", "exports", "imports", "inventory", "macro", "sector"],
        source_confidence=source_confidence,
        metadata={
            "source": snapshot.get("source"),
            "source_urls": snapshot.get("source_urls"),
            "release_schedule": snapshot.get("release_schedule"),
            "sector_implications": snapshot.get("sector_implications"),
        },
    )
    return {**snapshot, "storage": storage, "rag_document": rag_document}
