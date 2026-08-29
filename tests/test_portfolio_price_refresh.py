from pathlib import Path
from types import SimpleNamespace

import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_latest_provider_price_uses_market_snapshot_only(monkeypatch) -> None:
    import research_os_main as main

    calls: list[str] = []

    class MarketProvider:
        def fetch_market_snapshot(self, ticker: str):
            calls.append(ticker)
            return [
                SimpleNamespace(
                    label="last_price",
                    value="27180",
                    source_url="https://example.test/quote/005930",
                )
            ]

    class AnalysisProvider:
        def fetch_primary_market_snapshot(self, ticker: str):
            return MarketProvider().fetch_market_snapshot(ticker)

    monkeypatch.setattr(
        main,
        "get_analysis_data_provider",
        lambda settings: AnalysisProvider(),
    )

    def fail_if_full_analysis_collection_is_used(*args, **kwargs):
        raise AssertionError("price refresh must not collect full analysis context")

    monkeypatch.setattr(main, "collect_analysis_input_data", fail_if_full_analysis_collection_is_used)
    main.PORTFOLIO_PRICE_CACHE.pop("005930", None)

    price, source = main.latest_provider_price("005930", SimpleNamespace(), force_refresh=True)

    assert calls == ["005930"]
    assert price == 27180.0
    assert source == "https://example.test/quote/005930"


def test_primary_market_snapshot_does_not_probe_composite_fallbacks() -> None:
    from research_os.analysis_data_provider import AnalysisDataProvider
    from research_os.data_provider_core import (
        CompositeMarketDataProvider,
        EmptyFinancialDataProvider,
        EmptySupplementalDataProvider,
        MarketDataProvider,
    )

    calls: list[str] = []

    class Provider(MarketDataProvider):
        def __init__(self, name: str) -> None:
            self.name = name

        def fetch_market_snapshot(self, ticker: str):
            calls.append(self.name)
            return []

    provider = AnalysisDataProvider(
        market_data_provider=CompositeMarketDataProvider([Provider("primary"), Provider("fallback")]),
        financial_data_provider=EmptyFinancialDataProvider(),
        supplemental_data_provider=EmptySupplementalDataProvider(),
        mode="kis",
    )

    assert provider.fetch_primary_market_snapshot("005930") == []
    assert calls == ["primary"]
