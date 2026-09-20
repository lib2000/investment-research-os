"""OpenDART corp-code, filings, and financial data provider helpers."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import threading
from time import perf_counter
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
from research_os.dart_annual_report_lab import (
    DartQuotaExceeded,
    begin_dart_request,
    classify_dart_response,
    complete_dart_request,
)


CORP_CODE_CACHE_MAX_AGE = timedelta(hours=24)
_CORP_CODE_DOWNLOAD_LOCK = threading.Lock()


class OpenDartClient:
    REPORT_CODE_BY_PRIORITY = ["11011", "11014", "11012", "11013"]
    # The annual-report lab stores a deliberately small, normalized subset of
    # these responses.  Keeping the official endpoint registry next to the
    # client avoids parallel standalone DART clients with different error or
    # quota behaviour.
    ANNUAL_REPORT_GOVERNANCE_ENDPOINTS = (
        ("largest_holders", "최대주주 현황", "hyslrSttus.json"),
        ("largest_holder_changes", "최대주주 변동현황", "hyslrChgSttus.json"),
        ("executives", "임원 현황", "exctvSttus.json"),
        ("employees", "직원 현황", "empSttus.json"),
        ("share_structure", "주식의 총수 현황", "stockTotqySttus.json"),
        ("dividends", "배당에 관한 사항", "alotMatter.json"),
        (
            "board_remuneration",
            "이사·감사 전체 보수(주주총회 승인금액)",
            "drctrAdtAllMendngSttusGmtsckConfmAmount.json",
        ),
        (
            "individual_remuneration",
            "이사·감사 개인별 보수(5억원 이상) V2",
            "hmvAuditIndvdlBySttusV2.json",
        ),
    )

    def __init__(self, settings: Settings, *, job_name: str = "opendart_client") -> None:
        self.settings = settings
        self.api_key = settings.dart_api_key.strip()
        self.base_url = settings.dart_base_url.rstrip("/")
        self.cache_file = self._resolve_path(settings.dart_corp_code_cache_file)
        self.timeout_seconds = settings.dart_timeout_seconds
        self.job_name = job_name

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

    def _corp_code_cache_is_fresh(self) -> bool:
        try:
            age_seconds = datetime.now(timezone.utc).timestamp() - self.cache_file.stat().st_mtime
        except OSError:
            return False
        return age_seconds <= CORP_CODE_CACHE_MAX_AGE.total_seconds()

    def _get_json(self, api_name: str, *, params: dict, target: str | None = None) -> dict:
        event_id = begin_dart_request(
            self.settings,
            job_name=self.job_name,
            api_name=api_name,
            target=target,
        )
        started = perf_counter()
        completed = False
        try:
            response = httpx.get(
                f"{self.base_url}/{api_name}",
                params=params,
                timeout=self.timeout_seconds,
                trust_env=False,
            )
            http_status = int(response.status_code)
            try:
                payload = response.json()
            except Exception as exc:
                outcome = "http_err" if not 200 <= http_status < 300 else "invalid_payload"
                complete_dart_request(
                    self.settings,
                    event_id,
                    outcome=outcome,
                    http_status=http_status,
                    message="OpenDART JSON 응답을 해석할 수 없습니다.",
                    duration_ms=round((perf_counter() - started) * 1000),
                    secret=self.api_key,
                )
                completed = True
                response.raise_for_status()
                raise RuntimeError("OpenDART JSON 응답을 해석할 수 없습니다.") from exc
            if not isinstance(payload, dict):
                complete_dart_request(
                    self.settings,
                    event_id,
                    outcome="invalid_payload",
                    http_status=http_status,
                    message="OpenDART JSON 최상위 값이 객체가 아닙니다.",
                    duration_ms=round((perf_counter() - started) * 1000),
                    secret=self.api_key,
                )
                completed = True
                raise RuntimeError("OpenDART JSON 최상위 값이 객체가 아닙니다.")
            dart_status = str(payload.get("status") or "").strip() or None
            outcome = classify_dart_response(http_status=http_status, dart_status=dart_status)
            complete_dart_request(
                self.settings,
                event_id,
                outcome=outcome,
                http_status=http_status,
                dart_status=dart_status,
                message=payload.get("message") or "",
                duration_ms=round((perf_counter() - started) * 1000),
                secret=self.api_key,
            )
            completed = True
            response.raise_for_status()
            return payload
        except DartQuotaExceeded:
            raise
        except Exception as exc:
            if not completed:
                complete_dart_request(
                    self.settings,
                    event_id,
                    outcome="exception",
                    message=exc,
                    duration_ms=round((perf_counter() - started) * 1000),
                    secret=self.api_key,
                )
            raise

    def _get_binary(self, api_name: str, *, params: dict, target: str | None = None) -> bytes:
        event_id = begin_dart_request(
            self.settings,
            job_name=self.job_name,
            api_name=api_name,
            target=target,
        )
        started = perf_counter()
        completed = False
        try:
            response = httpx.get(
                f"{self.base_url}/{api_name}",
                params=params,
                timeout=self.timeout_seconds,
                trust_env=False,
            )
            http_status = int(response.status_code)
            dart_status: str | None = None
            dart_message = ""
            content = bytes(response.content)
            if not content.startswith(b"PK"):
                try:
                    payload = response.json()
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    dart_status = str(payload.get("status") or "").strip() or None
                    dart_message = str(payload.get("message") or "")
                if not dart_status:
                    try:
                        root = ET.fromstring(content)
                        dart_status = (root.findtext("status") or "").strip() or None
                        dart_message = (root.findtext("message") or "").strip()
                    except Exception:
                        pass
            if dart_status:
                outcome = classify_dart_response(http_status=http_status, dart_status=dart_status)
            elif not 200 <= http_status < 300:
                outcome = "http_err"
            elif content.startswith(b"PK"):
                outcome = "ok"
            else:
                outcome = "invalid_payload"
                dart_message = dart_message or "OpenDART 압축 응답 형식을 확인할 수 없습니다."
            complete_dart_request(
                self.settings,
                event_id,
                outcome=outcome,
                http_status=http_status,
                dart_status=dart_status,
                message=dart_message,
                duration_ms=round((perf_counter() - started) * 1000),
                secret=self.api_key,
            )
            completed = True
            response.raise_for_status()
            if outcome != "ok":
                raise RuntimeError(dart_message or dart_status or "OpenDART 바이너리 호출 실패")
            return content
        except DartQuotaExceeded:
            raise
        except Exception as exc:
            if not completed:
                complete_dart_request(
                    self.settings,
                    event_id,
                    outcome="exception",
                    message=exc,
                    duration_ms=round((perf_counter() - started) * 1000),
                    secret=self.api_key,
                )
            raise

    def _download_corp_codes(self) -> dict:
        content = self._get_binary(
            "corpCode.xml",
            params={"crtfc_key": self.api_key},
            target="listed_corporations",
        )
        by_stock_code: dict[str, dict] = {}
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
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
        if normalized in by_stock_code:
            return by_stock_code.get(normalized)
        # A valid, fresh full-corporation cache is also a negative cache.  ETFs
        # and other non-DART securities are absent by design; downloading the
        # complete corpCode archive for every such lookup wastes daily quota.
        if by_stock_code and self._corp_code_cache_is_fresh():
            return None
        # Different console/status requests can reach this branch together on
        # startup.  Recheck inside a process-wide lock before one bounded fetch.
        with _CORP_CODE_DOWNLOAD_LOCK:
            by_stock_code = self._read_cached_corp_codes()
            if normalized in by_stock_code:
                return by_stock_code.get(normalized)
            if by_stock_code and self._corp_code_cache_is_fresh():
                return None
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
                    payload = self._get_json(
                        "fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": self.api_key,
                            "corp_code": corp["corp_code"],
                            "bsns_year": str(business_year),
                            "reprt_code": report_code,
                            "fs_div": "CFS",
                        },
                        target=stock_code,
                    )
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
        detail_type: str | None = None,
        final_reports_only: bool = False,
    ) -> tuple[dict, list[dict]]:
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=max(int(lookback_days), 1))
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp["corp_code"],
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_no": "1",
            "page_count": str(max(1, min(int(page_count), 100))),
            "sort": "date",
            "sort_mth": "desc",
        }
        if detail_type:
            params["pblntf_detail_ty"] = str(detail_type)
        if final_reports_only:
            params["last_reprt_at"] = "Y"
        payload = self._get_json("list.json", params=params, target=stock_code)
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

    def fetch_annual_report_governance(
        self,
        stock_code: str,
        *,
        business_year: int | str,
        report_code: str = "11011",
    ) -> tuple[dict, dict]:
        """Fetch the bounded, annual-report governance API bundle.

        The caller is responsible for normalizing and persisting only its
        public research fields.  Raw response bodies and request parameters
        intentionally remain outside the annual-report ledger.
        """

        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        year = str(business_year).strip()
        if not year.isdigit() or len(year) != 4:
            raise ValueError("business_year는 네 자리 사업연도여야 합니다.")
        normalized_report_code = str(report_code).strip()
        if normalized_report_code != "11011":
            raise ValueError("지배구조 스냅샷은 사업보고서 코드 11011만 허용합니다.")

        endpoints: list[dict] = []
        for key, label, api_name in self.ANNUAL_REPORT_GOVERNANCE_ENDPOINTS:
            try:
                payload = self._get_json(
                    api_name,
                    params={
                        "crtfc_key": self.api_key,
                        "corp_code": corp["corp_code"],
                        "bsns_year": year,
                        "reprt_code": normalized_report_code,
                    },
                    target=stock_code,
                )
            except DartQuotaExceeded:
                raise
            except Exception:
                # The request has already been recorded in the secret-free
                # ledger.  Do not return exception text because a transport
                # library can include a complete request URL in that text.
                endpoints.append(
                    {
                        "key": key,
                        "label": label,
                        "api_name": api_name,
                        "state": "error",
                        "dart_status": None,
                        "rows": [],
                    }
                )
                continue

            dart_status = str(payload.get("status") or "").strip() or None
            rows = payload.get("list")
            normalized_rows = [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
            endpoints.append(
                {
                    "key": key,
                    "label": label,
                    "api_name": api_name,
                    "state": "ok" if dart_status == "000" else "empty" if dart_status == "013" else "error",
                    "dart_status": dart_status,
                    "rows": normalized_rows,
                }
            )
        return corp, {
            "business_year": year,
            "report_code": normalized_report_code,
            "endpoints": endpoints,
        }

    def fetch_insider_ownership(self, stock_code: str) -> tuple[dict, dict]:
        """Return official executive/major-shareholder ownership reports.

        OpenDART's ``elestock`` response does not guarantee a transaction
        price, so callers must keep price/value fields missing when the API
        omits them.
        """
        corp = self.find_corp_by_stock_code(stock_code)
        if not corp:
            raise RuntimeError(f"OpenDART corp_code를 찾지 못했습니다: {stock_code}")
        payload = self._get_json(
            "elestock.json",
            params={
                "crtfc_key": self.api_key,
                "corp_code": corp["corp_code"],
            },
            target=stock_code,
        )
        if payload.get("status") not in {"000", "013"}:
            raise RuntimeError(str(payload.get("message") or payload.get("status")))
        return corp, payload


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
