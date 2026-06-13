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


def save_earnings_reaction(runtime, *, reaction, ticker: str, vault_dir):
    storage_date = runtime.current_storage_date()
    reaction.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="earnings-reaction",
        markdown=runtime.render_earnings_reaction_markdown(reaction, storage_date),
        structured_payload=reaction.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, {
            "summary": reaction.headline_assessment,
            "quarter": reaction.quarter,
            "official_latest_quarter": reaction.official_latest_quarter,
            "official_latest_earnings_report_date": reaction.official_latest_earnings_report_date,
            "earnings_calendar_source": reaction.earnings_calendar_source,
            "earnings_reference_status": reaction.earnings_reference_status,
            "earnings_report_date": reaction.earnings_report_date,
            "previous_earnings_date": reaction.previous_earnings_date,
            "previous_earnings_key_takeaways": reaction.previous_earnings_key_takeaways,
            "next_earnings_date": reaction.next_earnings_date,
            "next_earnings_guidance": reaction.next_earnings_guidance,
            "price_reaction": reaction.price_reaction,
            "reaction_type": reaction.reaction_type,
            "sentiment_shift": reaction.sentiment_shift,
            "guidance_assessment": reaction.guidance_assessment,
            "evidence_status": reaction.evidence_status,
            "missing_inputs": reaction.missing_inputs,
            "watch_before_next_earnings": reaction.watch_before_next_earnings,
            "thesis_implications": reaction.thesis_implications,
        }),
        report_date=storage_date,
    )
    return reaction


def save_smart_trade_setup(runtime, *, setup, ticker: str, vault_dir):
    storage_date = runtime.current_storage_date()
    setup.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="smart-trade-setup",
        markdown=runtime.render_smart_trade_markdown(setup, storage_date),
        structured_payload=setup.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, {
            "summary": (
                f"{ticker} 매매 전략: 1차 진입 {setup.entry_zone[0].price:.2f}, "
                f"손절 {setup.stop_loss.price:.2f}, "
                f"1차 목표 {setup.targets[0].price:.2f}"
            ),
            "current_price": setup.current_price,
            "style": setup.style,
            "risk_tolerance": setup.risk_tolerance,
            "market_structure": setup.market_structure,
            "setup_quality": setup.setup_quality,
            "entry_zone": [item.model_dump(mode="json") for item in setup.entry_zone],
            "stop_loss": setup.stop_loss.model_dump(mode="json"),
            "targets": [item.model_dump(mode="json") for item in setup.targets],
            "risk_per_share": setup.risk_per_share,
        }),
        report_date=storage_date,
    )
    return setup


def save_institutional_stock_breakdown(runtime, *, analysis, ticker: str, vault_dir):
    storage_date = runtime.current_storage_date()
    analysis.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="institutional-stock-breakdown",
        markdown=runtime.render_institutional_markdown(analysis, storage_date),
        structured_payload=analysis.model_dump(mode="json"),
        manifest_entry=runtime.manifest_with_ticker_verification(ticker, {
            "summary": analysis.executive_summary,
            "source_count": len(analysis.injected_data),
            "key_risks": analysis.key_risks,
            "watch_items": analysis.bull_case.watch_items
            + analysis.base_case.watch_items
            + analysis.bear_case.watch_items,
        }),
        report_date=storage_date,
    )
    return analysis


def save_naver_chart_analysis(runtime, *, analysis: dict, code: str, settings):
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    storage_date = runtime.current_storage_date()
    latest_indicators = analysis.get("latest_indicators") or {}
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=code,
        report_type="chart-analysis",
        markdown=runtime.render_naver_chart_analysis_markdown(analysis, storage_date),
        structured_payload=analysis,
        manifest_entry=runtime.manifest_with_ticker_verification(code, {
            "summary": (
                f"{code} 차트 분석: "
                f"{analysis.get('overall_signal')}, {analysis.get('trade_bias')}"
            ),
            "company_name": analysis.get("company_name"),
            "as_of": analysis.get("as_of"),
            "overall_signal": analysis.get("overall_signal"),
            "latest_indicators": latest_indicators,
            "support_resistance": analysis.get("support_resistance"),
        }),
        report_date=storage_date,
    )
    analysis["storage"] = storage.model_dump(mode="json")
    return analysis


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
