"""Storage helpers for portfolio risk analysis reports."""

from __future__ import annotations


def save_reinforcement_portfolio_policy(
    runtime,
    *,
    response,
    portfolio_name: str,
    portfolio_value: float,
    settings,
):
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    report_date = runtime.current_storage_date()
    response.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=runtime.portfolio_store_key(portfolio_name),
        report_type="reinforcement-portfolio-optimizer",
        markdown=runtime.render_reinforcement_policy_markdown(
            response,
            portfolio_value,
            report_date,
        ),
        structured_payload=response.model_dump(mode="json"),
        manifest_entry={
            "summary": (
                f"{portfolio_name} 포트폴리오 정책 최적화: "
                f"{len(response.allocation_adjustments)}개 조정 후보"
            ),
            "portfolio_name": portfolio_name,
            "objective": response.objective,
            "risk_profile": response.risk_profile,
        },
        report_date=report_date,
    )
    return response


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
