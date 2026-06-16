"""National Pension Service ODCLOUD provider client and signal helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading

import httpx

from research_os.data_provider_utils import (
    _compact_company_name,
    _first_value,
    _is_configured_secret,
    _normalize_korean_stock_code,
    _parse_float_value,
    _provider_now,
    _safe_provider_error,
)
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings

_NPS_ODCLOUD_CACHE_LOCK = threading.Lock()
_NPS_ODCLOUD_ROW_CACHE: dict[str, dict] = {}
_NPS_ODCLOUD_MEMORY_TTL_SECONDS = 6 * 60 * 60
_NPS_ODCLOUD_PERSISTENT_TTL_SECONDS = 7 * 24 * 60 * 60


class NpsOdcloudClient:
    DOMESTIC_NAMESPACE = "3070507/v1"
    LARGE_HOLDING_NAMESPACE = "15106890/v1"

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.nps_odcloud_enabled
        self.api_key = settings.nps_odcloud_api_key.strip()
        self.base_url = settings.nps_odcloud_base_url.rstrip("/")
        self.domestic_docs_url = settings.nps_domestic_stock_docs_url
        self.large_holding_docs_url = settings.nps_large_holding_docs_url
        self.domestic_api_url = settings.nps_domestic_stock_api_url.strip()
        self.large_holding_api_url = settings.nps_large_holding_api_url.strip()
        self.timeout_seconds = settings.nps_odcloud_timeout_seconds
        self.max_pages = max(1, settings.nps_odcloud_max_pages)
        vault_dir = (Path(__file__).resolve().parents[1] / settings.research_vault_dir).resolve()
        self.cache_file = vault_dir / "_system" / "nps_odcloud_rows_cache.json"

    @property
    def is_configured(self) -> bool:
        return self.enabled and _is_configured_secret(self.api_key)

    def status_message(self) -> str:
        if not self.enabled:
            return "국민연금 공공데이터포털 연동이 비활성화되어 있습니다."
        if not self.is_configured:
            return "NPS_ODCLOUD_API_KEY가 없어 국민연금 보유/대량보유 데이터를 건너뜁니다."
        return (
            "국민연금 공공데이터포털 API가 설정되었습니다. 국내주식 투자정보(연간)와 "
            "대량보유 보고내역(분기)을 기관 수급 보조 신호로 사용합니다."
        )

    def _candidate_urls(self, explicit_url: str, namespace: str, docs_url: str) -> list[str]:
        urls = []
        if explicit_url:
            urls.append(explicit_url)
            return urls
        namespace = namespace.strip("/")
        urls.extend(
            [
                f"{self.base_url}/{namespace}",
                f"{self.base_url}/{namespace}/",
            ]
        )
        try:
            # 공공데이터포털 계열 API만 시스템 프록시를 타지 않게 고정합니다.
            # 일부 로컬 프록시/보안 도구가 127.0.0.1 차단 포트로 잡혀 있으면 WinError 10061이 발생합니다.
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.get(docs_url)
                response.raise_for_status()
                text = response.text
            for match in re.findall(r"https://api\.odcloud\.kr/api/[^\"'\\\s<>]+", text):
                urls.append(match)
            for match in re.findall(r"(/api/[^\"'\\\s<>]+)", text):
                urls.append("https://api.odcloud.kr" + match)
            for match in re.findall(rf"(/?{re.escape(namespace)}/[^\"'\\\s<>]+)", text):
                urls.append(f"{self.base_url}/{match.lstrip('/')}")
        except Exception:
            pass
        deduped = []
        for url in urls:
            clean = str(url).strip().rstrip("?")
            if clean and clean not in deduped:
                deduped.append(clean)
        return deduped

    def _read_persistent_cache(self, cache_key: str) -> dict | None:
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        cached = payload.get(cache_key)
        if not isinstance(cached, dict):
            return None
        rows = cached.get("rows")
        if not isinstance(rows, list):
            return None
        age = datetime.now(timezone.utc).timestamp() - float(cached.get("ts") or 0)
        if age > _NPS_ODCLOUD_PERSISTENT_TTL_SECONDS:
            return None
        return cached

    def _write_persistent_cache(self, cache_key: str, record: dict) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                json.loads(self.cache_file.read_text(encoding="utf-8"))
                if self.cache_file.exists()
                else {}
            )
            if not isinstance(payload, dict):
                payload = {}
            payload[cache_key] = {
                "ts": record.get("ts"),
                "rows": record.get("rows") or [],
                "used_url": record.get("used_url"),
            }
            self.cache_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def _fetch_rows(self, *, explicit_url: str, namespace: str, docs_url: str) -> tuple[list[dict], list[str], str | None]:
        if not self.is_configured:
            return [], [self.status_message()], None
        cache_key = "|".join([explicit_url, namespace, docs_url, self.api_key[-8:]])
        persistent_cached: dict | None = None
        with _NPS_ODCLOUD_CACHE_LOCK:
            cached = _NPS_ODCLOUD_ROW_CACHE.get(cache_key)
            if cached and (datetime.now(timezone.utc).timestamp() - cached.get("ts", 0)) < _NPS_ODCLOUD_MEMORY_TTL_SECONDS:
                return list(cached.get("rows") or []), list(cached.get("errors") or []), cached.get("used_url")
            persistent_cached = self._read_persistent_cache(cache_key)
        rows: list[dict] = []
        errors: list[str] = []
        used_url: str | None = None
        for url in self._candidate_urls(explicit_url, namespace, docs_url):
            try:
                with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                    for page in range(1, self.max_pages + 1):
                        response = client.get(
                            url,
                            params={
                                "page": page,
                                "perPage": 1000,
                                "returnType": "JSON",
                                "serviceKey": self.api_key,
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()
                        page_rows = payload.get("data") if isinstance(payload, dict) else payload
                        if isinstance(page_rows, dict):
                            page_rows = page_rows.get("data") or page_rows.get("items") or []
                        if not isinstance(page_rows, list):
                            page_rows = []
                        rows.extend([row for row in page_rows if isinstance(row, dict)])
                        used_url = url
                        if len(page_rows) < 1000:
                            break
                if rows:
                    cache_record = {
                        "ts": datetime.now(timezone.utc).timestamp(),
                        "rows": rows,
                        "errors": errors,
                        "used_url": used_url,
                    }
                    with _NPS_ODCLOUD_CACHE_LOCK:
                        _NPS_ODCLOUD_ROW_CACHE[cache_key] = cache_record
                        self._write_persistent_cache(cache_key, cache_record)
                    return rows, errors, used_url
            except Exception as exc:
                errors.append(f"{url}: {_safe_provider_error(exc)}")
        if persistent_cached:
            cached_rows = list(persistent_cached.get("rows") or [])
            cached_url = persistent_cached.get("used_url")
            cached_at = datetime.fromtimestamp(
                float(persistent_cached.get("ts") or 0),
                timezone.utc,
            ).isoformat()
            fallback_errors = errors + [
                f"외부 호출 실패로 마지막 성공 캐시를 사용했습니다. 캐시 시각: {cached_at}"
            ]
            with _NPS_ODCLOUD_CACHE_LOCK:
                _NPS_ODCLOUD_ROW_CACHE[cache_key] = {
                    "ts": datetime.now(timezone.utc).timestamp(),
                    "rows": cached_rows,
                    "errors": fallback_errors,
                    "used_url": cached_url,
                }
            return cached_rows, fallback_errors, cached_url
        with _NPS_ODCLOUD_CACHE_LOCK:
            _NPS_ODCLOUD_ROW_CACHE[cache_key] = {
                "ts": datetime.now(timezone.utc).timestamp(),
                "rows": rows,
                "errors": errors,
                "used_url": used_url,
            }
        return rows, errors, used_url

    def fetch_domestic_stock_rows(self) -> tuple[list[dict], list[str], str | None]:
        return self._fetch_rows(
            explicit_url=self.domestic_api_url,
            namespace=self.DOMESTIC_NAMESPACE,
            docs_url=self.domestic_docs_url,
        )

    def fetch_large_holding_rows(self) -> tuple[list[dict], list[str], str | None]:
        return self._fetch_rows(
            explicit_url=self.large_holding_api_url,
            namespace=self.LARGE_HOLDING_NAMESPACE,
            docs_url=self.large_holding_docs_url,
        )

    def _row_matches(self, row: dict, ticker: str, company_name: str | None) -> bool:
        ticker_code = _normalize_korean_stock_code(ticker)
        candidate_code = _first_value(
            row,
            ["종목코드", "단축코드", "ticker", "stock_code", "isin", "isu_srt_cd"],
        )
        if candidate_code and _normalize_korean_stock_code(str(candidate_code)) == ticker_code:
            return True
        names = [
            _first_value(row, ["종목명", "회사명", "발행기관명", "Company", "Issuer", "corp_nm"]),
        ]
        compact_company = _compact_company_name(company_name or "")
        if not compact_company:
            return False
        return any(_compact_company_name(str(name or "")) == compact_company for name in names if name)

    def find_signal(self, ticker: str, company_name: str | None = None) -> dict:
        domestic_rows, domestic_errors, domestic_url = self.fetch_domestic_stock_rows()
        domestic_match = next(
            (row for row in domestic_rows if self._row_matches(row, ticker, company_name)),
            None,
        )
        large_rows, large_errors, large_url = self.fetch_large_holding_rows()
        large_matches = [
            row for row in large_rows if self._row_matches(row, ticker, company_name)
        ][:5]
        holding_ratio = _parse_float_value(
            _first_value(domestic_match or {}, ["지분율(퍼센트)", "지분율", "Holding"])
        )
        domestic_weight = _parse_float_value(
            _first_value(domestic_match or {}, ["자산군 내 비중(퍼센트)", "비중", "Weight"])
        )
        amount_100m_krw = _parse_float_value(
            _first_value(domestic_match or {}, ["평가액(억 원)", "평가액", "Amount"])
        )
        issuer = (
            _first_value(domestic_match or {}, ["종목명", "회사명", "Company"])
            or _first_value((large_matches[0] if large_matches else {}), ["발행기관명", "Issuer"])
            or company_name
            or ticker
        )
        large_events = []
        for row in large_matches:
            ratio = _parse_float_value(_first_value(row, ["지분율(퍼센트)", "지분율", "Holding"]))
            base_date = _first_value(row, ["보고서 작성기준일", "기준일", "보고일자", "Base date for report"])
            large_events.append(
                {
                    "issuer": _first_value(row, ["발행기관명", "Issuer"]) or issuer,
                    "base_date": str(base_date or ""),
                    "holding_ratio": ratio,
                    "raw": row,
                }
            )
        warnings = domestic_errors + large_errors
        return {
            "ticker": ticker,
            "company_name": str(issuer or ticker),
            "holding_ratio": holding_ratio,
            "domestic_weight": domestic_weight,
            "amount_100m_krw": amount_100m_krw,
            "domestic_match_found": domestic_match is not None,
            "large_holding_events": large_events,
            "source_urls": {
                "domestic_stock": domestic_url or self.domestic_docs_url,
                "large_holding": large_url or self.large_holding_docs_url,
            },
            "warnings": warnings[:4],
            "as_of": _provider_now(),
        }


def nps_signal_to_data_points(signal: dict) -> list[InjectedDataPoint]:
    if not signal:
        return []
    points: list[InjectedDataPoint] = []
    company = signal.get("company_name") or signal.get("ticker")
    ratio = signal.get("holding_ratio")
    weight = signal.get("domestic_weight")
    amount = signal.get("amount_100m_krw")
    if signal.get("domestic_match_found"):
        parts = [f"{company} 국민연금 국내주식 투자정보"]
        if ratio is not None:
            parts.append(f"지분율 {ratio:.2f}%")
        if weight is not None:
            parts.append(f"국내주식 자산군 내 비중 {weight:.2f}%")
        if amount is not None:
            parts.append(f"평가액 {amount:,.0f}억 원")
        parts.append("연도말 기준 데이터이므로 장기 기관 보유 신호로만 해석")
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_domestic_stock_investment",
                value=" | ".join(parts),
                as_of=signal.get("as_of"),
                source_url=(signal.get("source_urls") or {}).get("domestic_stock"),
                confidence=0.84,
            )
        )
    events = signal.get("large_holding_events") or []
    if events:
        event_summaries = []
        for event in events[:3]:
            event_ratio = event.get("holding_ratio")
            event_date = event.get("base_date") or "기준일 미확인"
            if event_ratio is None:
                event_summaries.append(f"{event_date} 대량보유 보고")
            else:
                event_summaries.append(f"{event_date} 지분율 {event_ratio:.2f}%")
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_large_holding_report",
                value=(
                    f"{company} 국민연금 대량보유 보고 이벤트: "
                    + "; ".join(event_summaries)
                    + " | 5% 이상 신규취득 또는 1% 이상 변동 공시 이벤트로 해석"
                ),
                as_of=signal.get("as_of"),
                source_url=(signal.get("source_urls") or {}).get("large_holding"),
                confidence=0.88,
            )
        )
    for warning in signal.get("warnings") or []:
        points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_provider_warning",
                value=f"국민연금 공공데이터포털 호출 경고: {warning}",
                as_of=signal.get("as_of"),
                confidence=0.5,
            )
        )
    return points


def fetch_nps_institutional_signal(
    ticker: str,
    company_name: str | None,
    settings: Settings,
) -> dict:
    return NpsOdcloudClient(settings).find_signal(ticker, company_name)


def fetch_nps_institutional_context(
    ticker: str,
    company_name: str | None,
    settings: Settings,
) -> list[InjectedDataPoint]:
    client = NpsOdcloudClient(settings)
    if not client.is_configured:
        return []
    try:
        return nps_signal_to_data_points(client.find_signal(ticker, company_name))
    except Exception as exc:
        return [
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="nps_provider_warning",
                value=f"국민연금 공공데이터포털 데이터 호출 실패: {_safe_provider_error(exc)}",
                as_of=_provider_now(),
                confidence=0.5,
            )
        ]