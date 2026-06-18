"""Data provider status row builders."""

from __future__ import annotations

from typing import Any

from research_os import data_provider_status_messages
from research_os.data_provider_core import DataProviderStatus
from research_os.settings import Settings


def _external_provider_status_message(label: str, configured: bool) -> str:
    return data_provider_status_messages.external_provider_status_message(label, configured)


def build_supplemental_provider_statuses(
    settings: Settings,
    *,
    finnhub_client: Any,
    alpha_supplemental: Any,
    tavily_supplemental: Any,
    brave_supplemental: Any,
    nps_client: Any,
    customs_client: Any,
) -> list[DataProviderStatus]:
    return [
        DataProviderStatus(
            name="finnhub_events_news",
            mode="finnhub",
            ready=finnhub_client.is_configured,
            message=_external_provider_status_message(
                "Finnhub 실적 캘린더/회사 뉴스", finnhub_client.is_configured
            ),
        ),
        DataProviderStatus(
            name="alpha_vantage_overview",
            mode="alpha_vantage",
            ready=alpha_supplemental.is_configured,
            message=_external_provider_status_message(
                "Alpha Vantage 회사 개요", alpha_supplemental.is_configured
            ),
        ),
        DataProviderStatus(
            name="tavily_finance_search",
            mode="tavily",
            ready=tavily_supplemental.is_configured,
            message=(
                "Tavily 금융 검색/RAG 후보 프로바이더가 설정되었습니다. "
                f"무료 한도 보호: 일 {settings.tavily_daily_credit_limit} credits, "
                f"월 {settings.tavily_monthly_credit_limit} credits."
                if tavily_supplemental.is_configured
                else "Tavily 금융 검색/RAG 후보 API 키가 없어 해당 보강 데이터를 건너뜁니다."
            ),
        ),
        DataProviderStatus(
            name="brave_search",
            mode="brave",
            ready=brave_supplemental.is_configured,
            message=(
                "Brave 웹 검색/RAG 후보 프로바이더가 설정되었습니다. "
                f"무료 한도 보호: 일 {settings.brave_daily_request_limit} requests, "
                f"월 {settings.brave_monthly_request_limit} requests."
                if brave_supplemental.is_configured
                else "Brave 웹 검색/RAG 후보 API 키가 없어 해당 보강 데이터를 건너뜁니다."
            ),
        ),
        DataProviderStatus(
            name="naver_finance_korea_indices",
            mode="naver_finance",
            ready=settings.naver_finance_enabled,
            message=(
                "네이버 증권 KOSPI/KOSDAQ 보조 수집이 활성화되었습니다. "
                "공식 API가 아니므로 실패 시 분석을 중단하지 않고 경고만 표시합니다."
                if settings.naver_finance_enabled
                else "NAVER_FINANCE_ENABLED=false로 네이버 증권 보조 수집을 비활성화했습니다."
            ),
        ),
        DataProviderStatus(
            name="nps_odcloud_institutional_flow",
            mode="odcloud",
            ready=nps_client.is_configured,
            message=nps_client.status_message(),
        ),
        DataProviderStatus(
            name="korea_customs_trade",
            mode="data_go_kr",
            ready=customs_client.is_configured,
            message=customs_client.status_message(),
        ),
        DataProviderStatus(
            name="korea_customs_trade_total_trend",
            mode="data_go_kr",
            ready=customs_client.is_total_trend_configured,
            message=customs_client.total_trend_status_message(),
        ),
    ]


def build_kis_market_status(kis_client: Any) -> DataProviderStatus:
    return DataProviderStatus(
        name="kis_overseas_market_data",
        mode="kis",
        ready=kis_client.is_configured,
        message=data_provider_status_messages.kis_status_message(kis_client),
        fallback_active=False,
    )


def build_dart_financial_status(dart_client: Any) -> DataProviderStatus:
    return DataProviderStatus(
        name="dart_official_filing",
        mode="dart",
        ready=dart_client.is_configured,
        message=_external_provider_status_message("OpenDART 한국 공시/재무", dart_client.is_configured),
        fallback_active=False,
    )


def build_financial_datasets_status(financial_datasets_client: Any) -> DataProviderStatus:
    return DataProviderStatus(
        name="financial_datasets_financials",
        mode="financial_datasets",
        ready=financial_datasets_client.is_configured,
        message=_external_provider_status_message(
            "Financial Datasets 미국 재무제표", financial_datasets_client.is_configured
        ),
        fallback_active=False,
    )


def build_finnhub_market_status(finnhub_client: Any) -> DataProviderStatus:
    return DataProviderStatus(
        name="finnhub_market_data",
        mode="finnhub",
        ready=finnhub_client.is_configured,
        message=_external_provider_status_message(
            "Finnhub 미국 현재가/전일종가 보조", finnhub_client.is_configured
        ),
        fallback_active=False,
    )


def build_tiingo_market_status(tiingo_market: Any) -> DataProviderStatus:
    return DataProviderStatus(
        name="tiingo_market_data",
        mode="tiingo",
        ready=tiingo_market.is_configured,
        message=_external_provider_status_message("Tiingo 미국 종가 보조", tiingo_market.is_configured),
        fallback_active=False,
    )
