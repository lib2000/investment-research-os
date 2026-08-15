from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "check_research_evidence_pipeline.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("check_research_evidence_pipeline", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_earnings_not_applicable_is_expected_but_fallback_is_blocking_data() -> None:
    tool = load_tool()
    summary = tool.summarize_earnings(
        {
            "status": "success",
            "entries": {
                "005930": {"status": "success"},
                "360750": {"status": "not_applicable"},
                "000660": {"status": "fallback_unavailable"},
            },
        }
    )

    assert summary["entry_count"] == 3
    assert summary["success_count"] == 1
    assert summary["not_applicable_count"] == 1
    assert summary["not_applicable_is_expected"] is True
    assert summary["fallback_unavailable_count"] == 1
    assert summary["fallback_unavailable_tickers"] == ["000660"]


def test_ir_failures_are_sanitized_to_error_kinds() -> None:
    tool = load_tool()
    summary = tool.summarize_company_ir(
        {
            "status": "success",
            "item_count": 20,
            "related_count": 20,
            "source_results": [
                {"source_key": "blocked", "status": "failed", "error": "403 Forbidden for https://example.test"},
                {"source_key": "slow", "status": "failed", "error": "The read operation timed out"},
                {"source_key": "ok", "status": "success"},
            ],
        }
    )

    assert summary["failed_source_count"] == 2
    assert summary["failed_sources"] == [
        {"source_key": "blocked", "status": "failed", "error_kind": "http_403"},
        {"source_key": "slow", "status": "failed", "error_kind": "timeout"},
    ]


def test_ir_sec_fallback_is_covered_not_unresolved_failure() -> None:
    tool = load_tool()
    summary = tool.summarize_company_ir(
        {
            "status": "success",
            "item_count": 20,
            "related_count": 20,
            "source_results": [
                {
                    "source_key": "planet_ir_press_releases",
                    "ticker": "PL",
                    "status": "failed",
                    "error": "403 Forbidden",
                    "fallback_status": "success",
                    "fallback_source_key": "planet_sec_submissions",
                    "fallback_provider": "SEC EDGAR",
                    "fallback_source_scope": "sec_company_submissions",
                    "fallback_item_count": 4,
                }
            ],
        }
    )

    assert summary["source_health_status"] == "fallback_covered"
    assert summary["direct_source_failure_count"] == 1
    assert summary["fallback_source_count"] == 1
    assert summary["failed_source_count"] == 0
    assert summary["fallback_sources"] == [
        {
            "source_key": "planet_ir_press_releases",
            "status": "fallback_success",
            "primary_error_kind": "http_403",
            "fallback_source_key": "planet_sec_submissions",
            "fallback_provider": "SEC EDGAR",
            "fallback_source_scope": "sec_company_submissions",
            "fallback_item_count": 4,
        }
    ]


def test_legacy_routes_map_to_authenticated_canonical_contract() -> None:
    tool = load_tool()

    assert tool.LEGACY_ENDPOINT_ALIASES["/api/v1/dart-filings/status"] == "/api/v1/dart/filings/status"
    assert tool.LEGACY_ENDPOINT_ALIASES["/api/v1/company-ir-sources/status"].startswith(
        "/api/v1/company-ir-sources/watch"
    )
