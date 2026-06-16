"""OpenDART corp-code, filings, and financial data provider helpers."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import httpx

from research_os.data_provider_core import FinancialDataProvider
from research_os.data_provider_utils import (
    _is_configured_secret,
    _provider_now,
    _safe_provider_error,
)
from research_os.kis_data_provider import _looks_like_korean_security_code
from research_os.models import DataSourceType, InjectedDataPoint
from research_os.settings import Settings


class OpenDartClient:
    REPORT_CODE_BY_PRIORITY = ["11011", "11014", "11012", "11013"]

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.dart_api_key.strip()
        self.base_url = settings.dart_base_url.rstrip("/")
        self.cache_file = self._resolve_path(settings.dart_corp_code_cache_file)
        self.timeout_seconds = settings.dart_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return _is_configured_secret(self.api_key)

    def _resolve_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[1] / path).resolve()

    def _read_cached_corp_codes(self) -> dict:
        if not self.cache_file.exists():
            return {}
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return payload.get("by_stock_code") or {}
        except Exception:
            return {}

    def _write_cached_corp_codes(self, by_stock_code: dict) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(
                    {
                        "updated_at": _provider_now(),
                        "by_stock_code": by_stock_code,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            return

    def _download_corp_codes(self) -> dict:
        response = httpx.get(
            f"{self.base_url}/corpCode.xml",
            params={"crtfc_key": self.api_key},
            timeout=self.timeout_seconds,
            trust_env=False,
        )
        response.raise_for_status()
        by_stock_code: dict[str, dict] = {}
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            xml_name = archive.namelist()[0]
            root = ET.fromstring(archive.read(xml_name))
        for item in root.findall("list"):
            corp_code = (item.findtext("corp_code") or "").strip()
            corp_name = (item.findtext("corp_name") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip()
            if stock_code and corp_code:
                by_stock_code[stock_code] = {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                }
        self._write_cached_corp_codes(by_stock_code)
        return by_stock_code

    def find_corp_by_stock_code(self, stock_code: str) -> dict | None:
        normalized = stock_code.strip().upper()
        if not _looks_like_korean_security_code(normalized):
            return None
        by_stock_code = self._read_cached_corp_codes()
        if normalized not in by_stock_code:
            by_stock_code = self._download_corp_codes()
        return by_stock_code.get(normalized)

    def fetch_latest_financials(self, stock_code: str) -> tuple[dict, dict]:
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        current_year = datetime.now(timezone.utc).year
        errors: list[str] = []
        for business_year in [current_year - 1, current_year - 2]:
            for report_code in self.REPORT_CODE_BY_PRIORITY:
                try:
                    response = httpx.get(
                        f"{self.base_url}/fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": self.api_key,
                            "corp_code": corp["corp_code"],
                            "bsns_year": str(business_year),
                            "reprt_code": report_code,
                            "fs_div": "CFS",
                        },
                        timeout=self.timeout_seconds,
                        trust_env=False,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("status") == "000" and payload.get("list"):
                        return corp, {
                            "business_year": business_year,
                            "report_code": report_code,
                            "rows": payload["list"],
                        }
                    errors.append(str(payload.get("message") or payload.get("status")))
                except Exception as exc:
                    errors.append(_safe_provider_error(exc))
        raise RuntimeError("; ".join(error for error in errors if error) or "OpenDART financial lookup failed.")

    def fetch_recent_filings(
        self,
        stock_code: str,
        *,
        lookback_days: int = 14,
        page_count: int = 20,
    ) -> tuple[dict, list[dict]]:
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=max(int(lookback_days), 1))
        response = httpx.get(
            f"{self.base_url}/list.json",
            params={
                "crtfc_key": self.api_key,
                "corp_code": corp["corp_code"],
                "bgn_de": start_date.strftime("%Y%m%d"),
                "end_de": end_date.strftime("%Y%m%d"),
                "page_no": "1",
                "page_count": str(max(1, min(int(page_count), 100))),
                "sort": "date",
                "sort_mth": "desc",
            },
            timeout=self.timeout_seconds,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"000", "013"}:
            raise RuntimeError(str(payload.get("message") or payload.get("status")))
        filings = payload.get("list") or []
        normalized = []
        for item in filings:
            if not isinstance(item, dict):
                continue
            rcept_no = str(item.get("rcept_no") or "").strip()
            if not rcept_no:
                continue
            normalized.append(
                {
                    "corp_code": corp.get("corp_code"),
                    "corp_name": item.get("corp_name") or corp.get("corp_name"),
                    "stock_code": corp.get("stock_code") or stock_code,
                    "rcept_no": rcept_no,
                    "report_name": item.get("report_nm") or "",
                    "filer_name": item.get("flr_nm") or "",
                    "receipt_date": item.get("rcept_dt") or "",
                    "remark": item.get("rm") or "",
                    "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                }
            )
        return corp, normalized


class OpenDartFinancialDataProvider(FinancialDataProvider):
    def __init__(self, client: OpenDartClient) -> None:
        self.client = client

    def fetch_financial_snapshot(self, ticker: str) -> list[InjectedDataPoint]:
        if not _looks_like_korean_security_code(ticker):
            return []
        if not self.client.is_configured:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="dart_provider_warning",
                    value="DART_API_KEY가 없어 한국 종목 공시/재무 자동 주입을 건너뜁니다.",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]
        try:
            corp, financials = self.client.fetch_latest_financials(ticker)
            rows = financials["rows"]
            as_of = f"{financials['business_year']}:{financials['report_code']}"
            account_map = {
                str(row.get("account_nm") or "").strip(): row for row in rows
            }

            def amount(*names: str) -> str:
                for name in names:
                    row = account_map.get(name)
                    if row:
                        return str(row.get("thstrm_amount") or row.get("frmtrm_amount") or "n/a")
                return "n/a"

            source_url = f"{self.client.base_url}/fnlttSinglAcntAll.json"
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OFFICIAL_FILING,
                    label="dart_company",
                    value=f"{corp.get('corp_name')}({ticker}) corp_code={corp.get('corp_code')}",
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.94,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_revenue",
                    value=amount("매출액", "수익(매출액)", "영업수익"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_operating_income",
                    value=amount("영업이익", "영업손실"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.9,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_net_income",
                    value=amount("당기순이익", "당기순손실", "분기순이익", "반기순이익"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
                InjectedDataPoint(
                    source_type=DataSourceType.FINANCIAL_DATA,
                    label="dart_total_assets",
                    value=amount("자산총계"),
                    as_of=as_of,
                    source_url=source_url,
                    confidence=0.88,
                ),
            ]
        except Exception as exc:
            return [
                InjectedDataPoint(
                    source_type=DataSourceType.OTHER,
                    label="dart_provider_warning",
                    value=f"OpenDART 재무 데이터 호출 실패: {_safe_provider_error(exc)}",
                    as_of=_provider_now(),
                    confidence=0.5,
                )
            ]