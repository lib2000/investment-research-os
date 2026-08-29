from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def active_config() -> dict:
    from research_os.pension_rebalancing import default_pension_rebalancing_config

    config = default_pension_rebalancing_config()
    config.update(
        {
            "status": "active",
            "portfolio_name": "개인연금",
            "target_allocation": {
                "global_equity": 0.6,
                "bond": 0.3,
                "cash": 0.1,
            },
            "asset_class_by_ticker": {
                "ETF": "global_equity",
                "BOND": "bond",
                "CASH": "cash",
            },
            "rebalance_threshold_pct_points": 5.0,
        }
    )
    return config


def test_allocation_gap_returns_manual_review_only() -> None:
    from research_os.pension_rebalancing import build_pension_rebalancing_snapshot

    snapshot = build_pension_rebalancing_snapshot(
        active_config(),
        portfolio={
            "portfolio_name": "개인연금",
            "portfolio_value": 1_000_000,
            "holdings": [
                {"ticker": "ETF", "market_value": 500_000},
                {"ticker": "BOND", "market_value": 300_000},
                {"ticker": "CASH", "market_value": 200_000},
            ],
        },
        checked_at="2026-08-29T19:00:00+09:00",
    )

    rows = {row["asset_class"]: row for row in snapshot["allocation_rows"]}
    assert snapshot["status"] == "review_required"
    assert rows["global_equity"]["current_weight"] == 0.5
    assert rows["global_equity"]["review_status"] == "increase_review"
    assert rows["cash"]["review_status"] == "reduction_review"
    assert snapshot["manual_review_packet"]["automatic_order_submission"] is False
    assert snapshot["manual_review_packet"]["broker_order_endpoint_called"] is False


def test_empty_target_fails_closed_without_inventing_allocation() -> None:
    from research_os.pension_rebalancing import (
        build_pension_rebalancing_snapshot,
        default_pension_rebalancing_config,
    )

    snapshot = build_pension_rebalancing_snapshot(
        default_pension_rebalancing_config(),
        portfolio={"portfolio_name": "개인연금", "holdings": []},
    )

    assert snapshot["status"] == "needs_configuration"
    assert snapshot["allocation_rows"] == []
    assert any("목표 자산배분" in item for item in snapshot["validation"]["errors"])


def test_calendar_plan_keeps_monthly_and_quarterly_series_and_correct_end_time() -> None:
    from research_os.pension_rebalancing import build_pension_rebalancing_calendar_plan

    config = active_config()
    config["monthly_schedule"]["time"] = "19:45"
    plan = build_pension_rebalancing_calendar_plan(
        config,
        start_date=datetime(2026, 7, 1).date(),
        months_ahead=3,
    )

    monthly = next(item for item in plan["events"] if item["event_type"] == "monthly")
    quarterly = next(item for item in plan["events"] if item["event_type"] == "quarterly")
    assert monthly["start"] == "2026-07-01T19:45:00"
    assert monthly["end"] == "2026-07-01T20:15:00"
    assert quarterly["sync_key"] == "pension-rebalancing-quarterly-2026-07-01"
    assert plan["sync_status"] == "calendar_sync_not_enabled"


def test_due_period_ledger_catches_up_after_a_missed_month() -> None:
    from research_os.pension_rebalancing import due_pension_rebalancing_periods

    due = due_pension_rebalancing_periods(
        active_config(),
        {"last_completed_periods": {"monthly": "2026-06", "quarterly": "2026-Q1"}},
        now=datetime(2026, 7, 15, 19, 0),
    )

    assert {item["event_type"] for item in due} == {"monthly", "quarterly"}
    assert {item["period"] for item in due} == {"2026-07", "2026-Q3"}


def test_runner_writes_local_reports_and_never_routes_an_order(tmp_path) -> None:
    from research_os.pension_rebalancing import (
        save_pension_rebalancing_config,
        write_pension_rebalancing_run,
    )
    from research_os.portfolio_store import portfolio_store_key
    from research_os.settings import Settings
    from research_os.state_store import portfolio_store_path, write_json_store

    settings = Settings(research_vault_dir=str(tmp_path / "vault"))
    save_pension_rebalancing_config(settings, active_config())
    write_json_store(
        portfolio_store_path(settings),
        {
            "portfolios": {
                portfolio_store_key("개인연금"): {
                    "portfolio_name": "개인연금",
                    "portfolio_value": 1_000_000,
                    "holdings": [
                        {"ticker": "ETF", "market_value": 600_000},
                        {"ticker": "BOND", "market_value": 300_000},
                        {"ticker": "CASH", "market_value": 100_000},
                    ],
                }
            }
        },
    )

    result = write_pension_rebalancing_run(settings, due_periods=[{"event_type": "monthly", "period": "2026-08"}])

    assert result["snapshot"]["status"] == "within_rebalance_band"
    assert result["broker_order_endpoint_called"] is False
    assert result["drive_delivery"]["status"] == "sync_directory_not_configured"
    assert all(Path(path).exists() for path in result["report_paths"])
    runner_source = (PROJECT_ROOT / "tools" / "run_pension_rebalancing.py").read_text(encoding="utf-8")
    assert "/api/order" not in runner_source
    assert "submit_order" not in runner_source


def test_console_contract_exposes_safe_pension_review_button() -> None:
    api_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "api.js").read_text(encoding="utf-8")
    console_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
    html = (PROJECT_ROOT / "mobile_app" / "research_console" / "index.html").read_text(encoding="utf-8")
    backend_source = (PROJECT_ROOT / "backend" / "research_os_main.py").read_text(encoding="utf-8")

    assert '"/api/v1/pension-rebalancing/status"' in api_source
    assert '"/api/v1/pension-rebalancing/run"' in api_source
    assert "portfolioPensionRebalanceButton" in console_source
    assert "주문 엔드포인트 호출 없음" in console_source
    assert 'id="portfolioPensionRebalanceButton"' in html
    assert '"/api/v1/pension-rebalancing/status"' in backend_source
    assert '"/api/v1/pension-rebalancing/run"' in backend_source
