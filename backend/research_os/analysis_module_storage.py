"""Storage orchestration helpers for analysis module reports."""

from __future__ import annotations


def save_sector_opportunity_report(runtime, *, report, research_key: str, vault_dir):
    storage_date = runtime.current_storage_date()
    report.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=research_key,
        report_type="sector-opportunity",
        markdown=runtime.render_sector_opportunity_markdown(report, storage_date),
        structured_payload=report.model_dump(mode="json"),
        manifest_entry={
            "summary": report.macro_summary,
            "period": report.period,
            "region": report.region,
            "style": report.style,
            "top_sectors": [
                item.model_dump(mode="json") for item in report.ranked_sectors[:3]
            ],
            "recommended_companies": [
                item.model_dump(mode="json") for item in report.recommended_companies
            ],
            "sector_trends": [
                item.model_dump(mode="json") for item in report.sector_trends
            ],
            "sector_leaders": [
                item.model_dump(mode="json") for item in report.sector_leaders[:10]
            ],
            "analyst_report": report.analyst_report,
            "watch_items": report.watch_items,
            "key_risks": report.key_risks,
        },
        report_date=storage_date,
    )
    return report


def save_long_term_compounder_report(runtime, *, report, research_key: str, vault_dir):
    storage_date = runtime.current_storage_date()
    report.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=research_key,
        report_type="long-term-compounder",
        markdown=runtime.render_long_term_compounder_markdown(report, storage_date),
        structured_payload=report.model_dump(mode="json"),
        manifest_entry={
            "summary": report.summary,
            "screening_criteria": report.screening_criteria,
            "region": report.region,
            "sector": report.sector,
            "style": report.style,
            "min_market_cap": report.min_market_cap,
            "max_market_cap": report.max_market_cap,
            "candidates": [
                item.model_dump(mode="json") for item in report.candidates
            ],
            "next_actions": report.next_actions,
        },
        report_date=storage_date,
    )
    return report


def save_research_checklist_assessment(runtime, *, assessment, ticker: str, vault_dir):
    storage_date = runtime.current_storage_date()
    assessment.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="research-checklist",
        markdown=runtime.render_checklist_markdown(assessment, storage_date),
        structured_payload=assessment.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, {
            "summary": assessment.readiness_summary,
            "completion_rate": assessment.completion_rate,
            "readiness_level": assessment.readiness_level,
            "source_count": len(assessment.injected_data),
            "next_steps": assessment.next_steps,
        }),
        report_date=storage_date,
    )
    return assessment


def save_collaborative_team_report(
    runtime,
    *,
    report,
    ticker: str,
    vault_dir,
    settings,
    refresh_dossier: bool,
):
    storage_date = runtime.current_storage_date()
    report.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="collaborative-team-report",
        markdown=runtime.render_team_analysis_markdown(report, storage_date),
        structured_payload=report.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, {
            "summary": report.executive_summary,
            "data_quality": report.data_quality.data_quality,
            "source_confidence": report.data_quality.source_confidence,
            "source_count": len(report.injected_data),
            "consensus": report.consensus,
            "conflicts": [item.model_dump(mode="json") for item in report.conflicts],
            "investment_thesis": report.investment_thesis.model_dump(mode="json"),
            "watch_items": [item.model_dump(mode="json") for item in report.watch_items],
            "invalidation_conditions": report.invalidation_conditions,
        }),
        report_date=storage_date,
    )
    saved_entry = next(
        (
            entry
            for entry in runtime.read_manifest(vault_dir)
            if entry.get("file_name") == report.storage.file_name
            and str(entry.get("ticker") or "").upper() == ticker
        ),
        None,
    )
    if saved_entry:
        runtime.upsert_research_memory_document(vault_dir=vault_dir, entry=saved_entry)
    runtime.upsert_ticker_thesis_snapshot(
        vault_dir=vault_dir,
        ticker=ticker,
        company_name=runtime.ticker_company_name(ticker),
        investment_thesis=report.investment_thesis,
        watch_items=report.watch_items,
        source_entry={
            "type": "collaborative-team-report",
            "date": storage_date.isoformat(),
            "file_name": report.storage.file_name if report.storage else None,
            "relative_path": report.storage.relative_path
            if report.storage
            else None,
        },
        confidence=report.data_quality.source_confidence,
    )
    if refresh_dossier:
        try:
            runtime.synthesize_and_save_dossier(ticker, settings, save_result=True)
            report.dossier_refresh_status = "refreshed"
        except Exception as exc:
            report.dossier_refresh_status = "failed"
            runtime.append_jsonl(
                runtime.user_state_dir(settings) / "dossier_refresh_errors.jsonl",
                {
                    "ticker": ticker,
                    "at": runtime.current_storage_timestamp(),
                    "source": "team_report",
                    "error": str(exc),
                },
            )
    else:
        report.dossier_refresh_status = "deferred"
    return report
