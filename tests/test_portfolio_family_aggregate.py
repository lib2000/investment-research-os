from __future__ import annotations

from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def source_store() -> dict:
    return {
        "portfolios": {
            "가족-합산": {
                "portfolio_name": "가족 합산",
                "holdings": [
                    {
                        "ticker": "005930",
                        "name": "정적 사본",
                        "quantity": 999,
                        "average_cost": 1,
                        "current_price": 1,
                        "market_value": 999,
                        "cost_basis": 999,
                        "currency": "KRW",
                    }
                ],
                "portfolio_value": 999,
                "max_single_position_weight": 0.15,
                "notes": "기존 합산 설정",
                "created_at": "2026-08-01T18:30:00+09:00",
            },
            "이형주": {
                "portfolio_name": "이형주",
                "holdings": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "quantity": 2,
                        "average_cost": 10_000,
                        "current_price": 12_000,
                        "market_value": 24_000,
                        "cost_basis": 20_000,
                        "currency": "KRW",
                        "sector": "IT",
                        "theme_tags": ["AI"],
                        "price_checked_at": "2026-08-30T18:30:00+09:00",
                        "sync_checked_at": "2026-08-30T18:30:00+09:00",
                    }
                ],
                "portfolio_value": 24_000,
                "updated_at": "2026-08-30T18:30:00+09:00",
                "created_at": "2026-08-01T18:30:00+09:00",
            },
            "이지원": {
                "portfolio_name": "이지원",
                "holdings": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "quantity": 1,
                        "average_cost": 8_000,
                        "current_price": 12_000,
                        "market_value": 12_000,
                        "cost_basis": 8_000,
                        "currency": "KRW",
                        "sector": "IT",
                        "theme_tags": ["AI", "반도체"],
                        "price_checked_at": "2026-08-29T18:30:00+09:00",
                        "sync_checked_at": "2026-08-29T18:30:00+09:00",
                    },
                    {
                        "ticker": "JOBY",
                        "name": "Joby Aviation",
                        "quantity": 5,
                        "average_cost": 10,
                        "current_price": 12,
                        "market_value": 60_000,
                        "cost_basis": 50_000,
                        "currency": "USD",
                    },
                ],
                "portfolio_value": 72_000,
                "updated_at": "2026-08-29T18:30:00+09:00",
                "created_at": "2026-08-02T18:30:00+09:00",
            },
        }
    }


def test_derived_family_aggregate_uses_individual_records_not_static_copy() -> None:
    from research_os.portfolio_store import derive_family_aggregate_portfolio

    aggregate = derive_family_aggregate_portfolio(source_store())

    assert aggregate is not None
    assert aggregate.is_derived is True
    assert set(aggregate.derived_from_portfolios) == {"이형주", "이지원"}
    assert aggregate.holding_count == 2
    samsung = next(holding for holding in aggregate.holdings if holding.ticker == "005930")
    assert samsung.quantity == 3
    assert samsung.market_value == 36_000
    assert samsung.cost_basis == 28_000
    assert samsung.average_cost == pytest.approx(28_000 / 3)
    assert samsung.current_price == 12_000
    assert samsung.unrealized_gain == 8_000
    assert samsung.theme_tags == ["AI", "반도체"]
    assert samsung.sync_status == "derived_read_only"
    assert aggregate.portfolio_value == 96_000
    assert aggregate.updated_at == "2026-08-29T18:30:00+09:00"
    assert aggregate.max_single_position_weight == 0.15


def test_read_model_replaces_static_family_record_and_write_model_preserves_snapshot() -> None:
    from research_os.portfolio_store import (
        FAMILY_AGGREGATE_PORTFOLIO_KEY,
        prepare_portfolio_store_for_write,
        with_derived_family_aggregate,
    )

    original = source_store()
    read_model = with_derived_family_aggregate(original)
    assert read_model["portfolios"][FAMILY_AGGREGATE_PORTFOLIO_KEY]["is_derived"] is True
    assert read_model["portfolios"][FAMILY_AGGREGATE_PORTFOLIO_KEY]["holdings"][0]["quantity"] != 999

    write_model = prepare_portfolio_store_for_write(read_model)
    assert FAMILY_AGGREGATE_PORTFOLIO_KEY not in write_model["portfolios"]
    assert write_model["family_aggregate"]["mode"] == "derived_read_only"
    # The original source object is untouched; no legacy data is silently lost.
    assert original["portfolios"][FAMILY_AGGREGATE_PORTFOLIO_KEY]["holdings"][0]["quantity"] == 999


def test_integrity_audit_requires_static_duplicate_to_be_migrated() -> None:
    from research_os.portfolio_store import (
        family_aggregate_integrity_report,
        prepare_portfolio_store_for_write,
    )

    before = family_aggregate_integrity_report(source_store())
    after = family_aggregate_integrity_report(prepare_portfolio_store_for_write(source_store()))

    assert before["status"] == "error"
    assert before["legacy_static_entries"] == ["가족-합산"]
    assert after["status"] == "ok"
    assert set(after["owner_portfolios"]) == {"이형주", "이지원"}


def test_family_aggregate_save_is_rejected_before_any_store_write(tmp_path: Path) -> None:
    from fastapi import HTTPException
    from research_os.models import PortfolioSaveRequest
    from research_os.settings import Settings
    import research_os_main as main

    with pytest.raises(HTTPException) as exc_info:
        main.save_portfolio(
            "가족 합산",
            PortfolioSaveRequest(portfolio_name="가족 합산", holdings=[]),
            Settings(research_vault_dir=str(tmp_path / "vault")),
        )

    assert exc_info.value.status_code == 409
    assert "읽기 전용" in str(exc_info.value.detail)


def test_console_and_scheduled_runner_keep_aggregate_read_only() -> None:
    console = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
    daily_runner = (PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1").read_text(encoding="utf-8")
    catchup_runner = (PROJECT_ROOT / "tools" / "run_investment_research_catchup.ps1").read_text(encoding="utf-8")

    assert "setPortfolioDerivedReadOnlyState" in console
    assert "개인별 원장 자동 합산 · 읽기 전용" in console
    assert "check_family_portfolio_aggregate.py --write-state --strict --json" in daily_runner
    assert "family_portfolio_aggregate_integrity" in catchup_runner
