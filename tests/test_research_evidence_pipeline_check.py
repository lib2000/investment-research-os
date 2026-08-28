from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


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


def test_dart_refresh_timeout_is_recovered_only_after_complete_canonical_status() -> None:
    tool = load_tool()

    def fake_request(_base_url, path, _token, *, method="GET", **_kwargs):
        if path == tool.CANONICAL_ENDPOINTS["dart_refresh"]:
            raise tool.PipelineRequestError(f"{method} {path} failed: timed out")
        if path == tool.CANONICAL_ENDPOINTS["earnings_status"]:
            return {"status": "success", "entries": {"005930": {"status": "success"}}}
        if path == tool.CANONICAL_ENDPOINTS["dart_status"]:
            return {
                "status": "success",
                "enabled": True,
                "configured": True,
                "updated_at": "2026-08-28T23:28:28+09:00",
                "daily_check": {
                    "status": "complete",
                    "due": False,
                    "coverage_rate": 1.0,
                    "checked_count": 2,
                    "current_target_count": 2,
                    "failure_count": 0,
                },
            }
        if path == tool.CANONICAL_ENDPOINTS["company_ir_status"]:
            return {"status": "success", "item_count": 1, "related_count": 1, "source_results": []}
        if path == tool.CANONICAL_ENDPOINTS["public_ir_sec_status"]:
            return {"status": "success"}
        if path == tool.CANONICAL_ENDPOINTS["automation_status"]:
            return {"status": "success", "dossier_refresh_queue": {"status": "success"}}
        if path == tool.CANONICAL_ENDPOINTS["dossier_review_status"]:
            return {"status": "success"}
        return {"status": "success"}

    with patch.object(tool, "request_json", side_effect=fake_request):
        result = tool.collect_pipeline_status("http://example.test", "token", refresh=True)

    assert result["status"] == "warning"
    assert result["blocking_issues"] == []
    assert result["refresh_results"]["dart"]["status"] == "recovered_after_timeout"
    assert result["refresh_results"]["dart"]["postcondition_verified"] is True


def test_dart_refresh_timeout_stays_blocking_when_canonical_coverage_is_incomplete() -> None:
    tool = load_tool()

    def fake_request(_base_url, path, _token, *, method="GET", **_kwargs):
        if path == tool.CANONICAL_ENDPOINTS["dart_refresh"]:
            raise tool.PipelineRequestError(f"{method} {path} failed: timed out")
        if path == tool.CANONICAL_ENDPOINTS["earnings_status"]:
            return {"status": "success", "entries": {"005930": {"status": "success"}}}
        if path == tool.CANONICAL_ENDPOINTS["dart_status"]:
            return {
                "status": "success",
                "enabled": True,
                "configured": True,
                "updated_at": "2026-08-28T23:28:28+09:00",
                "daily_check": {
                    "status": "complete",
                    "due": False,
                    "coverage_rate": 0.5,
                    "checked_count": 1,
                    "current_target_count": 2,
                    "failure_count": 0,
                },
            }
        if path == tool.CANONICAL_ENDPOINTS["company_ir_status"]:
            return {"status": "success", "item_count": 1, "related_count": 1, "source_results": []}
        if path == tool.CANONICAL_ENDPOINTS["public_ir_sec_status"]:
            return {"status": "success"}
        if path == tool.CANONICAL_ENDPOINTS["automation_status"]:
            return {"status": "success", "dossier_refresh_queue": {"status": "success"}}
        if path == tool.CANONICAL_ENDPOINTS["dossier_review_status"]:
            return {"status": "success"}
        return {"status": "success"}

    with patch.object(tool, "request_json", side_effect=fake_request):
        result = tool.collect_pipeline_status("http://example.test", "token", refresh=True)

    assert result["status"] == "error"
    assert result["refresh_results"]["dart"]["status"] == "error"
    assert any("timed out" in issue for issue in result["blocking_issues"])


def test_dart_due_before_daily_operations_slot_is_a_warning_when_prior_day_completed() -> None:
    tool = load_tool()

    def fake_request(_base_url, path, _token, **_kwargs):
        if path == tool.CANONICAL_ENDPOINTS["earnings_status"]:
            return {"status": "success", "entries": {"005930": {"status": "success"}}}
        if path == tool.CANONICAL_ENDPOINTS["dart_status"]:
            return {
                "status": "success",
                "enabled": True,
                "configured": True,
                "updated_at": "2026-08-28T23:36:15+09:00",
                "entry_count": 93,
                "daily_check": {
                    "status": "due",
                    "due": True,
                    "last_checked_date": "2026-08-28",
                    "last_checked_at": "2026-08-28T23:36:15+09:00",
                    "current_target_count": 93,
                    "checked_count": 0,
                    "coverage_rate": 0.0,
                    "failure_count": 0,
                },
            }
        if path == tool.CANONICAL_ENDPOINTS["company_ir_status"]:
            return {"status": "success", "item_count": 1, "related_count": 1, "source_results": []}
        if path == tool.CANONICAL_ENDPOINTS["public_ir_sec_status"]:
            return {"status": "success"}
        if path == tool.CANONICAL_ENDPOINTS["automation_status"]:
            return {"status": "success", "dossier_refresh_queue": {"status": "success"}}
        if path == tool.CANONICAL_ENDPOINTS["dossier_review_status"]:
            return {"status": "success"}
        raise AssertionError(path)

    with patch.object(tool, "request_json", side_effect=fake_request):
        result = tool.collect_pipeline_status(
            "http://example.test",
            "token",
            now=datetime(2026, 8, 29, 9, 0, tzinfo=tool.KST),
        )

    assert result["status"] == "warning"
    assert result["blocking_issues"] == []
    assert result["dart_scheduled_refresh_pending"] is True


def test_dart_due_after_daily_operations_slot_stays_blocking() -> None:
    tool = load_tool()

    def fake_request(_base_url, path, _token, **_kwargs):
        if path == tool.CANONICAL_ENDPOINTS["earnings_status"]:
            return {"status": "success", "entries": {"005930": {"status": "success"}}}
        if path == tool.CANONICAL_ENDPOINTS["dart_status"]:
            return {
                "status": "success",
                "enabled": True,
                "configured": True,
                "updated_at": "2026-08-28T23:36:15+09:00",
                "entry_count": 93,
                "daily_check": {
                    "status": "due",
                    "due": True,
                    "last_checked_date": "2026-08-28",
                    "last_checked_at": "2026-08-28T23:36:15+09:00",
                    "current_target_count": 93,
                    "checked_count": 0,
                    "coverage_rate": 0.0,
                    "failure_count": 0,
                },
            }
        if path == tool.CANONICAL_ENDPOINTS["company_ir_status"]:
            return {"status": "success", "item_count": 1, "related_count": 1, "source_results": []}
        if path == tool.CANONICAL_ENDPOINTS["public_ir_sec_status"]:
            return {"status": "success"}
        if path == tool.CANONICAL_ENDPOINTS["automation_status"]:
            return {"status": "success", "dossier_refresh_queue": {"status": "success"}}
        if path == tool.CANONICAL_ENDPOINTS["dossier_review_status"]:
            return {"status": "success"}
        raise AssertionError(path)

    with patch.object(tool, "request_json", side_effect=fake_request):
        result = tool.collect_pipeline_status(
            "http://example.test",
            "token",
            now=datetime(2026, 8, 29, 19, 0, tzinfo=tool.KST),
        )

    assert result["status"] == "error"
    assert result["dart_scheduled_refresh_pending"] is False
    assert any("DART daily check incomplete" in issue for issue in result["blocking_issues"])
