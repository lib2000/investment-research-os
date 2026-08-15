from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_company_ir_direct_failure_uses_successful_sec_source() -> None:
    from research_os import company_ir_sources
    from research_os.company_ir_sources import CompanyIrSource

    direct = CompanyIrSource(
        source_key="planet_ir_press_releases",
        ticker="PL",
        company_name="Planet Labs PBC",
        provider="Planet Labs IR",
        source_url="https://investors.planet.com/news/default.aspx",
    )
    sec = CompanyIrSource(
        source_key="planet_sec_submissions",
        ticker="PL",
        company_name="Planet Labs PBC",
        provider="SEC EDGAR",
        source_url="https://data.sec.gov/submissions/CIK0001836833.json",
        source_scope="sec_company_submissions",
    )

    def fake_fetch(source: CompanyIrSource, **_kwargs):
        if source.source_scope != "sec_company_submissions":
            raise RuntimeError("403 Forbidden")
        return {
            "source_key": source.source_key,
            "provider": source.provider,
            "source_url": source.source_url,
            "ticker": source.ticker,
            "company_name": source.company_name,
            "source_scope": source.source_scope,
            "status": "success",
            "items": [{"item_id": "sec-1", "ticker": "PL", "published_at": "2026-08-15"}],
        }

    with patch.object(company_ir_sources, "fetch_company_ir_source", side_effect=fake_fetch):
        items, warnings, results = company_ir_sources.fetch_company_ir_sources(sources=[direct, sec])

    by_key = {item["source_key"]: item for item in results}
    fallback = by_key["planet_ir_press_releases"]
    assert warnings == []
    assert len(items) == 1
    assert fallback["primary_status"] == "failed"
    assert fallback["status"] == "fallback_success"
    assert fallback["fallback_status"] == "success"
    assert fallback["fallback_source_key"] == "planet_sec_submissions"
    assert fallback["fallback_source_scope"] == "sec_company_submissions"
    assert fallback["fallback_item_count"] == 1


def test_company_ir_failure_without_sec_fallback_remains_unresolved() -> None:
    from research_os import company_ir_sources
    from research_os.company_ir_sources import CompanyIrSource

    direct = CompanyIrSource(
        source_key="unknown_ir_press_releases",
        ticker="UNKNOWN",
        company_name="Unknown",
        provider="Unknown IR",
        source_url="https://example.test/ir",
    )

    with patch.object(company_ir_sources, "fetch_company_ir_source", side_effect=RuntimeError("timed out")):
        items, warnings, results = company_ir_sources.fetch_company_ir_sources(sources=[direct])

    assert items == []
    assert results[0]["status"] == "failed"
    assert "fallback_status" not in results[0]
    assert len(warnings) == 1
