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
