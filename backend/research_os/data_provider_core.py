"""Core provider interfaces and lightweight composite implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from research_os.models import DataSourceType, InjectedDataPoint


class DataProviderStatus:
    def __init__(
        self,
        name: str,
        mode: str,
        ready: bool,
        message: str,
        fallback_active: bool = False,
    ) -> None:
        self.name = name
        self.mode = mode
        self.ready = ready
        self.message = message
        self.fallback_active = fallback_active

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mode": self.mode,
            "ready": self.ready,
            "message": self.message,
            "fallback_active": self.fallback_active,
        }


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class FinancialDataProvider(ABC):
    @abstractmethod
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class SupplementalDataProvider(ABC):
    @abstractmethod
    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        raise NotImplementedError


class MockMarketDataProvider(MarketDataProvider):
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        as_of = datetime.now(timezone.utc).isoformat()
        ticker_seed = sum(ord(char) for char in ticker)
        mock_price = round(50 + (ticker_seed % 450) + (ticker_seed % 17) / 10, 2)
        mock_volume = 1_000_000 + (ticker_seed % 900) * 10_000
        mock_volatility = round(0.18 + (ticker_seed % 25) / 100, 2)

        return [
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="last_price",
                value=str(mock_price),
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="average_volume",
                value=str(mock_volume),
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.MARKET_PRICE,
                label="estimated_volatility",
                value=str(mock_volatility),
                as_of=as_of,
                confidence=0.55,
            ),
        ]


class MockFinancialDataProvider(FinancialDataProvider):
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        as_of = datetime.now(timezone.utc).isoformat()
        ticker_seed = sum(ord(char) for char in ticker)
        revenue_growth = round(0.05 + (ticker_seed % 35) / 100, 2)
        gross_margin = round(0.35 + (ticker_seed % 40) / 100, 2)
        free_cash_flow_margin = round(0.08 + (ticker_seed % 22) / 100, 2)
        net_debt_to_ebitda = round((ticker_seed % 30) / 10, 1)

        return [
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="revenue_growth",
                value=f"{revenue_growth:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="gross_margin",
                value=f"{gross_margin:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="free_cash_flow_margin",
                value=f"{free_cash_flow_margin:.0%}",
                as_of=as_of,
                confidence=0.6,
            ),
            InjectedDataPoint(
                source_type=DataSourceType.FINANCIAL_DATA,
                label="net_debt_to_ebitda",
                value=str(net_debt_to_ebitda),
                as_of=as_of,
                confidence=0.55,
            ),
        ]


class EmptyMarketDataProvider(MarketDataProvider):
    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class EmptyFinancialDataProvider(FinancialDataProvider):
    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class EmptySupplementalDataProvider(SupplementalDataProvider):
    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        return []


class CompositeMarketDataProvider(MarketDataProvider):
    def __init__(self, providers: list[MarketDataProvider]) -> None:
        self.providers = providers

    def fetch_market_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_market_snapshot(ticker))
        return data


class CompositeFinancialDataProvider(FinancialDataProvider):
    def __init__(self, providers: list[FinancialDataProvider]) -> None:
        self.providers = providers

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_financial_snapshot(ticker))
        return data


class CompositeSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, providers: list[SupplementalDataProvider]) -> None:
        self.providers = providers

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        data: list[InjectedDataPoint] = []
        for provider in self.providers:
            data.extend(provider.fetch_supplemental_snapshot(ticker))
        return data