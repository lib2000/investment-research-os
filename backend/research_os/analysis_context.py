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


def collect_analysis_input_data(
    runtime,
    *,
    ticker: str,
    provided_data: list[InjectedDataPoint],
    auto_inject_data: bool,
    settings,
) -> list[InjectedDataPoint]:
    profile_points: list[InjectedDataPoint] = []
    verification = runtime.verify_ticker_symbol(ticker, settings)
    profile = None
    if verification.verified:
        profile = runtime.build_ticker_profile(ticker, settings, refresh_external=False)
        profile_points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="official_company_profile",
                value=(
                    f"{profile.company_name} ({profile.exchange}) | "
                    f"사업 맥락: {profile.business_context or 'n/a'} | "
                    f"핵심 KPI: {', '.join(profile.watch_kpis) or 'n/a'}"
                ),
                as_of=runtime.current_storage_date().isoformat(),
                source_url=verification.verification_source,
                confidence=0.95,
            )
        )
        latest_earnings = runtime.latest_earnings_profile_for_ticker(
            ticker,
            settings,
            refresh_external=False,
        )
        if latest_earnings:
            profile_points.append(
                InjectedDataPoint(
                    source_type=DataSourceType.EARNINGS_RELEASE,
                    label="official_latest_earnings_profile",
                    value=runtime.latest_earnings_profile_summary(latest_earnings),
                    as_of=latest_earnings.get("earnings_report_date"),
                    source_url=latest_earnings.get("source_url"),
                    confidence=0.9,
                )
            )
    if not auto_inject_data or not settings.auto_inject_analysis_data:
        return [*profile_points, *provided_data]

    if not verification.verified:
        return [*profile_points, *provided_data]

    provider = runtime.get_analysis_data_provider(settings)
    provider_data = provider.fetch_analysis_context(ticker)
    if verification.verified and profile:
        provider_data.extend(
            runtime.fetch_nps_institutional_context(ticker, profile.company_name, settings) or []
        )
    if settings.data_provider_mode == "mock":
        provider_data.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="data_provider_limitation",
                value="현재 시장/재무 데이터 프로바이더가 mock 모드입니다. 가격과 재무 수치는 실제 투자 판단에 사용하지 마세요.",
                as_of=runtime.current_storage_date().isoformat(),
                confidence=0.4,
            )
        )
    return [*profile_points, *provider_data, *provided_data]
