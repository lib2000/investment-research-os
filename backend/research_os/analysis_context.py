"""Workspace context collection helpers for analysis modules."""

from __future__ import annotations

from pathlib import Path

from .models import DataSourceType, InjectedDataPoint


def collect_workspace_context(
    runtime,
    ticker: str,
    vault_dir: Path,
    provided_data: list[InjectedDataPoint],
) -> list[InjectedDataPoint]:
    ticker_dir = vault_dir / ticker
    saved_reports = []
    if ticker_dir.exists():
        saved_reports = sorted(ticker_dir.glob(f"{ticker}-*.md"))

    workspace_context = [
        InjectedDataPoint(
            source_type="research_memory",
            label="linked_workspace_reports",
            value=f"후속 분석에 연결 가능한 저장 리포트 {len(saved_reports)}개",
            as_of=runtime.current_storage_date().isoformat(),
            confidence=1.0,
        )
    ]
    try:
        thesis_snapshot = runtime.read_ticker_thesis_snapshot(vault_dir, ticker)
    except Exception:
        thesis_snapshot = None
    if thesis_snapshot:
        workspace_context.append(
            InjectedDataPoint(
                source_type=DataSourceType.RESEARCH_MEMORY,
                label="latest_thesis_snapshot",
                value=(
                    f"최신 기준 투자 논거: {thesis_snapshot.get('thesis_summary')} | "
                    f"강세 트리거: {', '.join(thesis_snapshot.get('bull_triggers') or []) or '없음'} | "
                    f"약세 트리거: {', '.join(thesis_snapshot.get('bear_triggers') or []) or '없음'} | "
                    f"무효화 조건: {', '.join(thesis_snapshot.get('invalidation_conditions') or []) or '없음'}"
                ),
                as_of=thesis_snapshot.get("source_date") or runtime.current_storage_date().isoformat(),
                source_url=thesis_snapshot.get("source_relative_path"),
                confidence=float(thesis_snapshot.get("confidence") or 0.8),
            )
        )
    try:
        memory_search = runtime.search_research_memory_documents(
            vault_dir,
            ticker,
            limit=4,
            refresh_index=False,
        )
    except Exception:
        memory_search = {"documents": []}
    for index, document in enumerate(memory_search.get("documents", []), start=1):
        summary = document.get("summary") or document.get("content_excerpt") or ""
        if not summary:
            continue
        workspace_context.append(
            InjectedDataPoint(
                source_type=DataSourceType.RESEARCH_MEMORY,
                label=f"rag_memory_document_{index}",
                value=(
                    f"{document.get('source_date') or '날짜 없음'} "
                    f"{document.get('report_type') or 'research'}: {summary}"
                ),
                as_of=document.get("source_date") or runtime.current_storage_date().isoformat(),
                source_url=document.get("source_relative_path"),
                confidence=float(document.get("confidence") or 0.7),
            )
        )
    for scope_key in ["MARKET", "MACRO", "SECTOR", "POLICY", "RATES", "FLOWS", "CUSTOMS"]:
        if ticker.upper() == scope_key:
            continue
        try:
            scope_search = runtime.search_research_memory_documents(
                vault_dir,
                scope_key,
                limit=1,
                refresh_index=False,
            )
        except Exception:
            scope_search = {"documents": []}
        for document in scope_search.get("documents", [])[:1]:
            summary = document.get("summary") or document.get("content_excerpt") or ""
            if not summary:
                continue
            workspace_context.append(
                InjectedDataPoint(
                    source_type=DataSourceType.RESEARCH_MEMORY,
                    label=f"rag_cross_scope_{scope_key.lower()}",
                    value=(
                        f"{scope_key} 누적 자료 ({document.get('source_date') or '날짜 없음'}): "
                        f"{summary}"
                    ),
                    as_of=document.get("source_date") or runtime.current_storage_date().isoformat(),
                    source_url=document.get("source_relative_path"),
                    confidence=float(document.get("confidence") or 0.7),
                )
            )

    return [*provided_data, *workspace_context]
