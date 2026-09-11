from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_sync import apply_toss_holdings_to_portfolio
from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.settings import Settings
from research_os.toss_invest import TossClient, normalize_toss_holding, normalize_toss_order


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        toss_client_id="client-id",
        toss_client_secret="client-secret",
        toss_account_seq="7",
        toss_token_cache_file=str(tmp_path / "toss-token.json"),
        toss_timeout_seconds=1,
        toss_max_retries=0,
    )


def test_normalize_toss_holding_maps_official_schema() -> None:
    result = normalize_toss_holding(
        {
            "symbol": "005930",
            "name": "삼성전자",
            "marketCountry": "KR",
            "currency": "KRW",
            "quantity": "10",
            "lastPrice": "72000",
            "averagePurchasePrice": "65000",
            "marketValue": {"purchaseAmount": "650000", "amount": "720000"},
            "profitLoss": {"amount": "70000", "rate": "0.1077"},
        }
    )
    assert result["ticker"] == "005930"
    assert result["quantity"] == 10
    assert result["average_cost"] == 65000
    assert result["market_value"] == 720000
    assert result["unrealized_return"] == 0.1077
    assert result["currency"] == "KRW"


def test_toss_client_fetches_and_caches_read_only_holdings(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    token_response = httpx.Response(
        200,
        json={"access_token": "token-value", "token_type": "Bearer", "expires_in": 3600},
    )
    holdings_response = httpx.Response(
        200,
        json={
            "result": {
                "items": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "marketCountry": "US",
                        "currency": "USD",
                        "quantity": "2",
                        "lastPrice": "178.5",
                        "averagePurchasePrice": "155.3",
                        "marketValue": {"purchaseAmount": "310.6", "amount": "357"},
                        "profitLoss": {"amount": "46.4", "rate": "0.1494"},
                    }
                ]
            }
        },
    )
    with patch("research_os.toss_invest.httpx.post", return_value=token_response) as token_call:
        with patch("research_os.toss_invest.httpx.request", return_value=holdings_response) as api_call:
            result = TossClient(settings).fetch_holdings()

    assert result["account_seq"] == "7"
    assert result["holdings"][0]["ticker"] == "AAPL"
    assert result["holdings"][0]["currency"] == "USD"
    token_call.assert_called_once()
    api_call.assert_called_once()
    assert api_call.call_args.kwargs["headers"]["X-Tossinvest-Account"] == "7"
    assert Path(settings.toss_token_cache_file).exists()


def test_apply_toss_holdings_preserves_missing_and_reports_remote_new() -> None:
    portfolio = SavedPortfolio(
        portfolio_name="가족",
        holdings=[
            PortfolioHolding(ticker="005930", name="삼성전자", quantity=1, currency="KRW"),
            PortfolioHolding(ticker="AAPL", name="Apple Inc.", quantity=1, currency="USD"),
        ],
    )
    synced, summary = apply_toss_holdings_to_portfolio(
        portfolio,
        {
            "account_seq": "7",
            "holdings": [
                {
                    "ticker": "005930",
                    "name": "삼성전자",
                    "quantity": 2,
                    "average_cost": 65000,
                    "current_price": 72000,
                    "market_value": 144000,
                    "cost_basis": 130000,
                    "unrealized_gain": 14000,
                    "unrealized_return": 0.1077,
                    "currency": "KRW",
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft",
                    "quantity": 3,
                    "market_value": 1000,
                    "currency": "USD",
                },
            ],
        },
        checked_at="2026-08-12T18:00:00+09:00",
    )
    assert synced.holdings[0].quantity == 2
    assert synced.holdings[0].sync_source == "toss_holdings"
    assert synced.holdings[1].sync_status == "toss_missing"
    assert summary["updated_count"] == 1
    assert summary["skipped_count"] == 1
    assert summary["untracked_remote"][0]["ticker"] == "MSFT"


def test_apply_toss_holdings_imports_owner_positions_and_preserves_other_sources() -> None:
    portfolio = SavedPortfolio(
        portfolio_name="이형주",
        holdings=[
            PortfolioHolding(
                ticker="JOBY",
                name="Joby Aviation",
                quantity=10,
                average_cost=9,
                current_price=8,
                market_value=116800,
                cost_basis=131400,
                unrealized_gain=-14600,
                currency="USD",
                sync_source="toss_holdings",
            ),
            PortfolioHolding(ticker="005930", name="삼성전자", quantity=3, sync_source="kis_holdings"),
        ],
    )
    synced, summary = apply_toss_holdings_to_portfolio(
        portfolio,
        {
            "holdings": [
                {
                    "ticker": "JOBY",
                    "name": "Joby Aviation",
                    "quantity": 12,
                    "average_cost": 9.5,
                    "current_price": 8.5,
                    "market_value": 102,
                    "cost_basis": 114,
                    "unrealized_gain": -12,
                    "unrealized_return": -0.1053,
                    "currency": "USD",
                },
                {
                    "ticker": "300080",
                    "name": "플리토",
                    "quantity": 279,
                    "average_cost": 8590,
                    "current_price": 8640,
                    "market_value": 2410560,
                    "currency": "KRW",
                },
            ]
        },
        checked_at="2026-08-13T16:10:00+09:00",
        import_untracked=True,
        preserve_non_toss_holdings=True,
    )

    holdings = {item.ticker: item for item in synced.holdings}
    assert holdings["JOBY"].quantity == 12
    assert holdings["JOBY"].current_price == 8.5
    assert holdings["JOBY"].market_value == 148920
    assert holdings["JOBY"].cost_basis == 166440
    assert holdings["JOBY"].unrealized_gain == -17520
    assert holdings["300080"].sync_source == "toss_holdings"
    assert holdings["300080"].sync_status == "account_synced"
    assert holdings["005930"].quantity == 3
    assert holdings["005930"].sync_source == "kis_holdings"
    assert summary["imported_count"] == 1
    assert summary["applied_fx_rates"] == {"JOBY": 1460.0}
    assert summary["imported_remote"][0]["ticker"] == "300080"
    assert summary["untracked_remote"] == []
    assert any(item["reason"] == "non_toss_holding_preserved" for item in summary["skipped"])


def test_apply_toss_holdings_uses_portfolio_fx_for_new_us_position() -> None:
    portfolio = SavedPortfolio(
        portfolio_name="이형주",
        holdings=[
            PortfolioHolding(
                ticker="AAPL",
                name="Apple",
                quantity=2,
                average_cost=100,
                current_price=120,
                market_value=350400,
                cost_basis=292000,
                currency="USD",
            )
        ],
    )

    synced, summary = apply_toss_holdings_to_portfolio(
        portfolio,
        {
            "holdings": [
                {
                    "ticker": "MSFT",
                    "name": "Microsoft",
                    "quantity": 1,
                    "average_cost": 300,
                    "current_price": 320,
                    "market_value": 320,
                    "cost_basis": 300,
                    "unrealized_gain": 20,
                    "unrealized_return": 0.0667,
                    "currency": "USD",
                }
            ]
        },
        checked_at="2026-09-11T08:00:00+09:00",
        import_untracked=True,
        preserve_non_toss_holdings=True,
    )

    holdings = {item.ticker: item for item in synced.holdings}
    assert holdings["MSFT"].current_price == 320
    assert holdings["MSFT"].market_value == 467200
    assert holdings["MSFT"].cost_basis == 438000
    assert holdings["MSFT"].unrealized_gain == 29200
    assert summary["applied_fx_rates"] == {"MSFT": 1460.0}
    assert summary["status"] == "success"


def test_apply_toss_holdings_does_not_mix_native_usd_without_fx_basis() -> None:
    portfolio = SavedPortfolio(
        portfolio_name="이형주",
        holdings=[
            PortfolioHolding(
                ticker="JOBY",
                name="Joby Aviation",
                quantity=50,
                average_cost=9.6386,
                current_price=6.28,
                market_value=314,
                cost_basis=481.93,
                currency="USD",
                sync_source="toss_holdings",
            )
        ],
    )

    synced, summary = apply_toss_holdings_to_portfolio(
        portfolio,
        {
            "holdings": [
                {
                    "ticker": "JOBY",
                    "name": "Joby Aviation",
                    "quantity": 60,
                    "average_cost": 9.5,
                    "current_price": 7,
                    "market_value": 420,
                    "cost_basis": 570,
                    "currency": "USD",
                }
            ]
        },
        checked_at="2026-09-11T08:00:00+09:00",
    )

    holding = synced.holdings[0]
    assert holding.quantity == 50
    assert holding.market_value == 314
    assert holding.cost_basis == 481.93
    assert holding.sync_status == "toss_fx_unavailable"
    assert summary["status"] == "warning"
    assert summary["skipped"][0]["reason"] == "toss_fx_unavailable"


def test_normalize_toss_order_masks_id_and_keeps_execution_summary() -> None:
    result = normalize_toss_order(
        {
            "orderId": "abcdefghijklmnop",
            "symbol": "300080",
            "side": "BUY",
            "orderType": "LIMIT",
            "status": "CANCELED",
            "quantity": "279",
            "price": "8590",
            "orderedAt": "2026-08-12T12:38:11+09:00",
            "execution": {
                "filledQuantity": "236",
                "averageFilledPrice": "8590",
                "filledAmount": "2027240",
            },
        }
    )
    assert result["order_id_masked"] == "abcd****mnop"
    assert result["symbol"] == "300080"
    assert result["execution"]["filled_quantity"] == 236
    assert result["execution"]["filled_amount"] == 2027240


def test_toss_client_fetches_order_history_without_mutating_api(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    token_response = httpx.Response(
        200,
        json={"access_token": "order-token", "token_type": "Bearer", "expires_in": 3600},
    )
    orders_response = httpx.Response(
        200,
        json={"result": {"orders": [], "nextCursor": None, "hasNext": False}},
    )
    with patch("research_os.toss_invest.httpx.post", return_value=token_response):
        with patch("research_os.toss_invest.httpx.request", return_value=orders_response) as api_call:
            result = TossClient(settings).fetch_orders(
                status="CLOSED", date_from="2026-08-12", date_to="2026-08-12"
            )
    assert result["status"] == "success"
    assert result["query"]["from"] == "2026-08-12"
    assert api_call.call_args.args[0] == "GET"
    assert api_call.call_args.args[1].endswith("/api/v1/orders")
