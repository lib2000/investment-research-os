"""Storage helpers for portfolio risk analysis reports."""

from __future__ import annotations


def save_portfolio_risk_scan(
    runtime,
    *,
    scan,
    portfolio_name: str,
    portfolio_value: float,
    risk_score: int,
    top_five_weight: float,
    settings,
):
    storage_date = runtime.current_storage_date()
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    portfolio_key = runtime.normalize_ticker(portfolio_name)
    scan.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=portfolio_key,
        report_type="portfolio-risk-scan",
        markdown=runtime.render_portfolio_risk_markdown(scan, storage_date),
        structured_payload=scan.model_dump(mode="json"),
        manifest_entry={
            "summary": (
                f"{portfolio_name} 리스크 점수 {risk_score}/100, "
                f"상위 5개 비중 {top_five_weight:.0%}"
            ),
            "portfolio_value": round(portfolio_value, 2),
            "risk_score": risk_score,
            "top_five_weight": top_five_weight,
            "sector_concentration": [
                item.model_dump(mode="json") for item in scan.sector_concentration
            ],
            "theme_concentration": [
                item.model_dump(mode="json") for item in scan.theme_concentration
            ],
            "warnings": [item.model_dump(mode="json") for item in scan.warnings],
        },
        report_date=storage_date,
    )
    return scan
