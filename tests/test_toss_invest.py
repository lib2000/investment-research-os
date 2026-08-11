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
from research_os.toss_invest import TossClient, normalize_toss_holding


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
