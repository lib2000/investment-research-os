"""Search-oriented supplemental data providers."""

from __future__ import annotations

import httpx

from research_os.data_provider_core import SupplementalDataProvider
from research_os.data_provider_utils import _is_configured_secret, _provider_now, _safe_provider_error
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.provider_usage import consume_external_provider_quota
from research_os.settings import Settings


class TavilySupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.tavily_api_key.strip()
        self.base_url = settings.tavily_base_url.rstrip("/")
        self.timeout_seconds = settings.tavily_timeout_seconds
        self.daily_credit_limit = settings.tavily_daily_credit_limit
        self.monthly_credit_limit = settings.tavily_monthly_credit_limit
        self.usage_file = settings.provider_usage_file

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        allowed, quota_message = consume_external_provider_quota(
            provider_name="tavily",
            usage_file=self.usage_file,
            daily_limit=self.daily_credit_limit,
            monthly_limit=self.monthly_credit_limit,
            units=1,
            unit_label="credits",
        )
        if not allowed:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="tavily_quota_guard",
                    value=quota_message,
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            response = httpx.post(
                f"{self.base_url}/search",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "query": f"{ticker} stock latest earnings guidance valuation investor relations",
                    "topic": "finance",
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            snippets = []
            if payload.get("answer"):
                snippets.append(str(payload["answer"]))
            for item in payload.get("results") or []:
                title = item.get("title") or item.get("url") or ""
                content = item.get("content") or ""
                if title or content:
                    snippets.append(f"{title}: {content}")
            if not snippets:
                return []
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.NEWS,
                    label="tavily_finance_search_context",
                    value=" | ".join(snippets[:4]),
                    as_of=_provider_now(),
                    source_url=f"{self.base_url}/search",
                    confidence=0.68,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="tavily_provider_warning",
                    value=f"Tavily 검색 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]


class BraveSupplementalDataProvider(SupplementalDataProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.brave_api_key.strip()
        self.base_url = settings.brave_base_url.rstrip("/")
        self.timeout_seconds = settings.brave_timeout_seconds
        self.daily_request_limit = settings.brave_daily_request_limit
        self.monthly_request_limit = settings.brave_monthly_request_limit
        self.usage_file = settings.provider_usage_file

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def fetch_supplemental_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if _looks_like_korean_security_code(ticker) or not self.is_configured:
            return []
        allowed, quota_message = consume_external_provider_quota(
            provider_name="brave",
            usage_file=self.usage_file,
            daily_limit=self.daily_request_limit,
            monthly_limit=self.monthly_request_limit,
            units=1,
            unit_label="requests",
        )
        if not allowed:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="brave_quota_guard",
                    value=quota_message,
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            response = httpx.get(
                f"{self.base_url}/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
                params={
                    "q": f"{ticker} stock earnings guidance valuation",
                    "count": 5,
                    "search_lang": "en",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            results = (payload.get("web") or {}).get("results") or []
            snippets = [
                f"{item.get('title')}: {item.get('description')}"
                for item in results[:4]
                if item.get("title") or item.get("description")
            ]
            if not snippets:
                payload_keys = ", ".join(sorted(payload.keys())) or "none"
                return [
                    InjectedDataPoint(
                        source_type=DataSourceType.OTHER,
                        label="brave_provider_warning",
                        value=(
                            "Brave 검색 호출은 성공했지만 사용 가능한 web.results가 없었습니다. "
                            f"응답 키: {payload_keys}. Brave 플랜/검색 권한 또는 쿼리 제한을 확인하세요."
                        ),
                        as_of=_provider_now(),
                        source_url=f"{self.base_url}/web/search",
                        confidence=0.5,
                    )
                ]
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.NEWS,
                    label="brave_search_context",
                    value=" | ".join(snippets),
                    as_of=_provider_now(),
                    source_url=f"{self.base_url}/web/search",
                    confidence=0.64,
                )
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="brave_provider_warning",
                    value=f"Brave 검색 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
