"""Evidence-first insider-trading research for US SEC Form 4 and Korea OpenDART.

The module deliberately separates source facts, deterministic calculations, and
interpretation.  Missing source fields stay missing; they are never estimated.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import ipaddress
import math
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from research_os.daily_family_top_pick import build_family_candidate_scope
from research_os.opendart_data_provider import OpenDartClient
from research_os.rag_memory import upsert_research_memory_document
from research_os.research_memory import read_manifest, resolve_vault_dir, save_research_markdown
from research_os.settings import Settings
from research_os.state_store import (
    current_storage_date,
    current_storage_timestamp,
    read_json_store,
    user_state_dir,
    write_json_store,
)
from research_os.web_fetch import capture_url_headers


INSIDER_REPORT_TYPE = "insider-trading"
INSIDER_STATE_VERSION = 1
PRIMARY_SOURCE_HOSTS = {
    "sec.gov",
    "www.sec.gov",
    "data.sec.gov",
    "dart.fss.or.kr",
    "opendart.fss.or.kr",
}
SECONDARY_SOURCE_HOSTS = {
    "secform4.com",
    "www.secform4.com",
    "marketbeat.com",
    "www.marketbeat.com",
}
SEC_FORM_TYPES = {"4", "4/A"}
OPEN_MARKET_CODES = {"P", "S"}


class PriceBar(BaseModel):
    date: date
    close: float
    high: float | None = None
    low: float | None = None
    open: float | None = None
    volume: float | None = None


class InsiderTransaction(BaseModel):
    ticker: str
    market: str
    company_name: str | None = None
    insider_name: str | None = None
    title: str | None = None
    relationship: str | None = None
    tx_date: date
    filing_date: date | None = None
    tx_code: str
    acquired_disposed: str | None = None
    shares: float | None = None
    avg_price: float | None = None
    transaction_value: float | None = None
    post_shares: float | None = None
    security_title: str | None = None
    direct_or_indirect: str | None = None
    is_10b5_1: bool | None = None
    source_type: str
    source_url: str | None = None
    accession_number: str | None = None
    source_fields: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class InsiderAnalysisRequest(BaseModel):
    ticker: str = ""
    market: str = "AUTO"
    company_name: str | None = None
    insider_name: str | None = None
    title: str | None = None
    relationship: str | None = None
    tx_date: date | None = None
    filing_date: date | None = None
    tx_type: str | None = None
    shares: float | None = None
    avg_price: float | None = None
    post_shares: float | None = None
    is_10b5_1: bool | None = None
    source_url: str | None = None
    source_text: str | None = None
    price_history: list[PriceBar] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    valuation_context: str | None = None
    fetch_external: bool = True
    save_result: bool = True
    max_filings: int = Field(default=24, ge=1, le=100)


class InsiderBatchRequest(BaseModel):
    tickers: list[str] | None = None
    max_tickers: int = Field(default=8, ge=1, le=100)
    max_filings: int = Field(default=24, ge=1, le=100)
    save_result: bool = True


def insider_state_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "insider_trading_research.json"


def insider_event_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "insider_trading_event_cache.json"


def sec_company_tickers_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "sec_company_tickers.json"


def _clean_text(value: Any, limit: int = 600) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "").replace("$", "").replace("원", "")
    if not text or text.lower() in {"none", "null", "n/a", "nan", "-"}:
        return None
    try:
        result = float(text)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _safe_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "").strip()
    if not text:
        return None
    digits = re.sub(r"[^0-9]", "", text)
    candidates = [text[:10], f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}" if len(digits) >= 8 else ""]
    for candidate in candidates:
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def normalize_market(ticker: str, market: str = "AUTO") -> str:
    requested = _clean_text(market, 12).upper()
    if requested in {"KR", "KOREA", "KOSPI", "KOSDAQ"}:
        return "KR"
    if requested in {"US", "USA", "NASDAQ", "NYSE", "AMEX"}:
        return "US"
    return "KR" if re.fullmatch(r"\d{6}", _clean_text(ticker, 32)) else "US"


def normalize_ticker(ticker: str) -> str:
    value = _clean_text(ticker, 32).upper().lstrip("$")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,15}", value):
        raise ValueError("티커는 영문·숫자·점·하이픈만 사용할 수 있습니다.")
    return value


def classify_source_url(source_url: str, *, allow_secondary: bool = True) -> dict[str, str]:
    cleaned = _clean_text(source_url, 2000)
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() != "https":
        raise ValueError("공시 URL은 HTTPS 주소만 사용할 수 있습니다.")
    if parsed.username or parsed.password:
        raise ValueError("자격증명이 포함된 URL은 사용할 수 없습니다.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("공시 URL의 호스트를 확인할 수 없습니다.")
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("로컬 주소는 공시 URL로 사용할 수 없습니다.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ValueError("사설·로컬 IP 주소는 공시 URL로 사용할 수 없습니다.")
    if host in PRIMARY_SOURCE_HOSTS:
        return {"url": cleaned, "host": host, "source_tier": "primary", "provider": "SEC" if host.endswith("sec.gov") else "OpenDART"}
    if allow_secondary and host in SECONDARY_SOURCE_HOSTS:
        return {"url": cleaned, "host": host, "source_tier": "secondary", "provider": "secondary_insider_source"}
    raise ValueError("지원하는 SEC·OpenDART·검증 대상 보조 사이트 URL이 아닙니다.")


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _direct_child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in list(element):
        if _local_name(child) == name:
            return child
    return None


def _descendant(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element.iter():
        if _local_name(child) == name:
            return child
    return None


def _path_text(element: ET.Element | None, *names: str) -> str:
    current = element
    for name in names:
        current = _direct_child(current, name)
        if current is None:
            return ""
    return _clean_text(current.text)


def _desc_text(element: ET.Element | None, name: str) -> str:
    found = _descendant(element, name)
    return _clean_text(found.text if found is not None else "")


def _truthy_xml(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def parse_sec_form4_xml(
    xml_text: str,
    *,
    source_url: str,
    filing_date: date | None = None,
    accession_number: str | None = None,
) -> list[InsiderTransaction]:
    """Parse SEC ownership XML without guessing omitted values."""
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff\n\r\t "))
    except ET.ParseError as exc:
        raise ValueError(f"SEC Form 4 XML을 해석할 수 없습니다: {exc}") from exc
    if _local_name(root) != "ownershipDocument":
        candidate = _descendant(root, "ownershipDocument")
        if candidate is None:
            raise ValueError("SEC Form 4 ownershipDocument를 찾지 못했습니다.")
        root = candidate

    ticker = normalize_ticker(_desc_text(root, "issuerTradingSymbol"))
    company_name = _desc_text(root, "issuerName") or None
    owner = _descendant(root, "reportingOwner")
    insider_name = _desc_text(owner, "rptOwnerName") or None
    relationship_node = _descendant(owner, "reportingOwnerRelationship")
    title = _desc_text(relationship_node, "officerTitle") or None
    relationships: list[str] = []
    relation_names = (
        ("isDirector", "이사"),
        ("isOfficer", "임원"),
        ("isTenPercentOwner", "10% 주주"),
        ("isOther", "기타"),
    )
    for field_name, label in relation_names:
        if _truthy_xml(_desc_text(relationship_node, field_name)) is True:
            relationships.append(label)
    other_text = _desc_text(relationship_node, "otherText")
    if other_text:
        relationships.append(other_text)
    relationship = ", ".join(dict.fromkeys(relationships)) or None

    all_text = " ".join(_clean_text(item.text, 1200) for item in root.iter() if item.text)
    if re.search(r"(?:not|아님|아닌)\s+(?:made\s+)?(?:pursuant\s+to\s+)?(?:a\s+)?(?:rule\s+)?10b5\s*[-–]?\s*1", all_text, re.IGNORECASE):
        document_10b5 = False
    else:
        document_10b5 = True if re.search(r"10b5\s*[-–]?\s*1", all_text, re.IGNORECASE) else None
    for item in root.iter():
        if "10b5" in _local_name(item).lower():
            explicit = _truthy_xml(_clean_text(item.text))
            if explicit is not None:
                document_10b5 = explicit

    events: list[InsiderTransaction] = []
    for transaction in root.iter():
        local = _local_name(transaction)
        if local not in {"nonDerivativeTransaction", "derivativeTransaction"}:
            continue
        tx_date = _safe_date(_path_text(transaction, "transactionDate", "value"))
        tx_code = _path_text(transaction, "transactionCoding", "transactionCode").upper()
        if not tx_date or not tx_code:
            continue
        shares = _safe_float(_path_text(transaction, "transactionAmounts", "transactionShares", "value"))
        avg_price = _safe_float(_path_text(transaction, "transactionAmounts", "transactionPricePerShare", "value"))
        acquired_disposed = _path_text(
            transaction,
            "transactionAmounts",
            "transactionAcquiredDisposedCode",
            "value",
        ).upper() or None
        post_shares = _safe_float(
            _path_text(transaction, "postTransactionAmounts", "sharesOwnedFollowingTransaction", "value")
        )
        security_title = _path_text(transaction, "securityTitle", "value") or None
        direct_or_indirect = _path_text(
            transaction, "ownershipNature", "directOrIndirectOwnership", "value"
        ).upper() or None
        transaction_value = shares * avg_price if shares is not None and avg_price is not None else None
        notes: list[str] = []
        if local == "derivativeTransaction":
            notes.append("파생증권 거래")
        if avg_price is None:
            notes.append("거래단가 확인 필요")
        events.append(
            InsiderTransaction(
                ticker=ticker,
                market="US",
                company_name=company_name,
                insider_name=insider_name,
                title=title,
                relationship=relationship,
                tx_date=tx_date,
                filing_date=filing_date,
                tx_code=tx_code,
                acquired_disposed=acquired_disposed,
                shares=shares,
                avg_price=avg_price,
                transaction_value=transaction_value,
                post_shares=post_shares,
                security_title=security_title,
                direct_or_indirect=direct_or_indirect,
                is_10b5_1=document_10b5,
                source_type="sec_form4",
                source_url=source_url,
                accession_number=accession_number,
                source_fields={"document_type": local},
                notes=notes,
            )
        )
    return events


def parse_dart_elestock_payload(
    payload: dict[str, Any],
    *,
    ticker: str,
    corp: dict[str, Any],
) -> list[InsiderTransaction]:
    status = str(payload.get("status") or "")
    if status not in {"000", "013", ""}:
        raise RuntimeError(str(payload.get("message") or status))
    events: list[InsiderTransaction] = []
    for row in payload.get("list") or []:
        if not isinstance(row, dict):
            continue
        tx_date = _safe_date(row.get("rcept_dt"))
        receipt_no = _clean_text(row.get("rcept_no"), 32)
        change = _safe_float(row.get("sp_stock_lmp_irds_cnt"))
        post_shares = _safe_float(row.get("sp_stock_lmp_cnt"))
        if not tx_date or change is None:
            continue
        direction = "A" if change > 0 else "D" if change < 0 else None
        tx_code = "ACQUIRE" if change > 0 else "DISPOSE" if change < 0 else "NO_CHANGE"
        source_url = (
            f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_no}" if receipt_no else None
        )
        title = _clean_text(row.get("isu_exctv_ofcps")) or None
        relationship_bits = []
        if _clean_text(row.get("isu_exctv_rgist_at")):
            relationship_bits.append(f"등기여부 {_clean_text(row.get('isu_exctv_rgist_at'))}")
        if _clean_text(row.get("isu_main_shrholdr")):
            relationship_bits.append(f"주요주주 {_clean_text(row.get('isu_main_shrholdr'))}")
        events.append(
            InsiderTransaction(
                ticker=normalize_ticker(ticker),
                market="KR",
                company_name=_clean_text(row.get("corp_name") or corp.get("corp_name")) or None,
                insider_name=_clean_text(row.get("repror")) or None,
                title=title,
                relationship=", ".join(relationship_bits) or None,
                tx_date=tx_date,
                filing_date=tx_date,
                tx_code=tx_code,
                acquired_disposed=direction,
                shares=abs(change),
                avg_price=None,
                transaction_value=None,
                post_shares=post_shares,
                security_title="보통주/보고대상 주식",
                direct_or_indirect=None,
                is_10b5_1=None,
                source_type="opendart_elestock",
                source_url=source_url,
                accession_number=receipt_no or None,
                source_fields={key: value for key, value in row.items() if key not in {"crtfc_key"}},
                notes=["OpenDART 소유보고 API에는 거래단가가 없어 금액은 확인 필요"],
            )
        )
    return events


def parse_insider_summary_text(text: str, *, ticker_hint: str = "", market: str = "AUTO") -> InsiderTransaction | None:
    cleaned = _clean_text(text, 5000)
    if not cleaned:
        return None
    ticker_match = re.search(r"\$([A-Za-z][A-Za-z0-9.\-]{0,15})\b", cleaned)
    kr_ticker_match = re.search(r"(?<!\d)(\d{6})(?!\d)", cleaned)
    ticker_value = ticker_hint or (ticker_match.group(1) if ticker_match else "") or (
        kr_ticker_match.group(1) if kr_ticker_match else ""
    )
    if not ticker_value:
        return None
    tx_date_match = re.search(r"(20\d{2}[-./]\d{1,2}[-./]\d{1,2})", cleaned)
    tx_date = _safe_date(tx_date_match.group(1)) if tx_date_match else None
    if not tx_date:
        return None
    shares_match = re.search(r"([\d,]+(?:\.\d+)?)\s*주", cleaned)
    price_match = re.search(r"(?:평균\s*단가|단가|주당|,|:)\s*\$\s*([\d,]+(?:\.\d+)?)", cleaned, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", cleaned)
    post_match = re.search(r"거래\s*후\s*보유(?:량)?\s*([\d,]+(?:\.\d+)?)\s*주?", cleaned)
    tx_word = "매수" if "매수" in cleaned or re.search(r"\bpurchase", cleaned, re.IGNORECASE) else (
        "매도" if "매도" in cleaned or re.search(r"\bsale", cleaned, re.IGNORECASE) else ""
    )
    tx_code = "P" if tx_word == "매수" else "S" if tx_word == "매도" else "UNKNOWN"
    title_match = re.search(r"\b(CEO|CFO|COO|CTO|CMO|이사|대표이사|사장|부사장|전무|상무)\b", cleaned, re.IGNORECASE)
    insider_match = re.search(
        r"(?:내부자명|보고자|insider\s+name)\s*[:：]\s*([A-Za-z가-힣][A-Za-z가-힣 .'-]{1,60}?)(?=\s*[,;]|$)",
        cleaned,
        re.IGNORECASE,
    )
    shares = _safe_float(shares_match.group(1)) if shares_match else None
    avg_price = _safe_float(price_match.group(1)) if price_match else None
    return InsiderTransaction(
        ticker=normalize_ticker(ticker_value),
        market=normalize_market(ticker_value, market),
        insider_name=_clean_text(insider_match.group(1), 80) if insider_match else None,
        title=_clean_text(title_match.group(1).upper(), 80) if title_match else None,
        relationship="텍스트 요약 입력",
        tx_date=tx_date,
        filing_date=tx_date,
        tx_code=tx_code,
        acquired_disposed="A" if tx_code == "P" else "D" if tx_code == "S" else None,
        shares=shares,
        avg_price=avg_price,
        transaction_value=shares * avg_price if shares is not None and avg_price is not None else None,
        post_shares=_safe_float(post_match.group(1)) if post_match else None,
        is_10b5_1=True if re.search(r"10b5\s*[-–]?\s*1", cleaned, re.IGNORECASE) else None,
        source_type="manual_summary",
        notes=["사용자 입력 요약에서 파싱됨 — 공식 원문 대조 필요"],
    )


def transaction_from_request(request: InsiderAnalysisRequest) -> InsiderTransaction | None:
    if not request.ticker or not request.tx_date or not request.tx_type:
        return None
    ticker = normalize_ticker(request.ticker)
    tx_code = _clean_text(request.tx_type, 20).upper()
    if tx_code in {"BUY", "PURCHASE", "매수"}:
        tx_code = "P"
    elif tx_code in {"SELL", "SALE", "매도"}:
        tx_code = "S"
    shares = abs(request.shares) if request.shares is not None else None
    return InsiderTransaction(
        ticker=ticker,
        market=normalize_market(ticker, request.market),
        company_name=request.company_name,
        insider_name=request.insider_name,
        title=request.title,
        relationship=request.relationship or "구조화 입력",
        tx_date=request.tx_date,
        filing_date=request.filing_date or request.tx_date,
        tx_code=tx_code,
        acquired_disposed="A" if tx_code in {"P", "ACQUIRE"} else "D" if tx_code in {"S", "DISPOSE"} else None,
        shares=shares,
        avg_price=request.avg_price,
        transaction_value=shares * request.avg_price if shares is not None and request.avg_price is not None else None,
        post_shares=request.post_shares,
        is_10b5_1=request.is_10b5_1,
        source_type="manual_structured",
        source_url=request.source_url,
        notes=["사용자 구조화 입력 — 공식 원문 대조 필요"],
    )


def _transaction_key(event: InsiderTransaction) -> str:
    return "|".join(
        [
            event.ticker,
            event.tx_date.isoformat(),
            event.insider_name or "",
            event.tx_code,
            str(event.shares if event.shares is not None else ""),
            event.security_title or "",
            event.accession_number or "",
        ]
    )


def merge_transactions(*event_groups: list[InsiderTransaction]) -> list[InsiderTransaction]:
    merged: dict[str, InsiderTransaction] = {}
    for group in event_groups:
        for event in group:
            merged.setdefault(_transaction_key(event), event)
    return sorted(
        merged.values(),
        key=lambda item: (item.tx_date, item.filing_date or item.tx_date, item.accession_number or ""),
        reverse=True,
    )


def _http_get(url: str, *, timeout: float = 15.0) -> httpx.Response:
    source = classify_source_url(url)
    if source["source_tier"] != "primary":
        raise ValueError("보조 사이트는 자동 원문 수집 대상이 아닙니다. 공식 공시를 재조회합니다.")
    with httpx.Client(
        headers=capture_url_headers(url),
        follow_redirects=False,
        timeout=httpx.Timeout(timeout, connect=min(timeout, 8.0)),
        trust_env=False,
    ) as client:
        current_url = source["url"]
        for _ in range(5):
            current_source = classify_source_url(current_url)
            if current_source["source_tier"] != "primary":
                raise ValueError("공식 공시 호스트 밖으로 이동한 응답은 사용하지 않습니다.")
            response = client.get(current_url)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("위치 정보가 없는 공시 리디렉션은 사용할 수 없습니다.")
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            return response
    raise ValueError("공시 URL 리디렉션 횟수가 허용 범위를 초과했습니다.")


def _load_sec_ticker_map(settings: Settings) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    path = sec_company_tickers_cache_path(settings)
    cached = read_json_store(path, {})
    updated = _safe_date(str(cached.get("updated_at") or "")[:10])
    rows = cached.get("tickers") if isinstance(cached.get("tickers"), dict) else {}
    if rows and updated and (current_storage_date() - updated).days <= 7:
        return rows, {"source": "cache", "updated_at": cached.get("updated_at")}
    response = _http_get("https://www.sec.gov/files/company_tickers.json", timeout=20.0)
    payload = response.json()
    normalized: dict[str, dict[str, Any]] = {}
    for row in payload.values() if isinstance(payload, dict) else []:
        if not isinstance(row, dict):
            continue
        ticker = _clean_text(row.get("ticker"), 24).upper()
        cik = row.get("cik_str")
        if ticker and cik is not None:
            normalized[ticker] = {
                "ticker": ticker,
                "cik": str(cik).zfill(10),
                "company_name": _clean_text(row.get("title"), 180),
            }
    write_json_store(path, {"updated_at": current_storage_timestamp(), "tickers": normalized})
    return normalized, {"source": "sec_company_tickers", "updated_at": current_storage_timestamp()}


def _cached_events(settings: Settings, ticker: str) -> tuple[list[InsiderTransaction], dict[str, Any]]:
    store = read_json_store(insider_event_cache_path(settings), {"version": INSIDER_STATE_VERSION, "tickers": {}})
    record = (store.get("tickers") or {}).get(ticker, {})
    events: list[InsiderTransaction] = []
    for row in record.get("events") or []:
        try:
            events.append(InsiderTransaction.model_validate(row))
        except Exception:
            continue
    return events, record


def _save_cached_events(
    settings: Settings,
    ticker: str,
    events: list[InsiderTransaction],
    *,
    source_status: dict[str, Any],
) -> None:
    path = insider_event_cache_path(settings)
    store = read_json_store(path, {"version": INSIDER_STATE_VERSION, "tickers": {}})
    tickers = store.setdefault("tickers", {})
    tickers[ticker] = {
        "updated_at": current_storage_timestamp(),
        "source_status": source_status,
        "events": [event.model_dump(mode="json") for event in events[:600]],
    }
    store["version"] = INSIDER_STATE_VERSION
    store["updated_at"] = current_storage_timestamp()
    write_json_store(path, store)


def fetch_sec_form4_events(
    ticker: str,
    settings: Settings,
    *,
    lookback_days: int = 730,
    max_filings: int = 24,
) -> tuple[list[InsiderTransaction], dict[str, Any]]:
    ticker = normalize_ticker(ticker)
    cached, cache_record = _cached_events(settings, ticker)
    ticker_map, map_status = _load_sec_ticker_map(settings)
    company = ticker_map.get(ticker)
    if not company:
        raise RuntimeError(f"SEC company_tickers에서 {ticker} CIK를 찾지 못했습니다.")
    cik = company["cik"]
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    payload = _http_get(submissions_url, timeout=20.0).json()
    cutoff = current_storage_date() - timedelta(days=max(1, lookback_days))
    candidates: list[dict[str, Any]] = []
    def add_candidate_rows(rows: dict[str, Any]) -> None:
        forms = rows.get("form") or []
        filing_dates = rows.get("filingDate") or []
        accessions = rows.get("accessionNumber") or []
        primary_docs = rows.get("primaryDocument") or []
        for index, form in enumerate(forms):
            filing_day = _safe_date(filing_dates[index] if index < len(filing_dates) else None)
            accession = _clean_text(accessions[index] if index < len(accessions) else "", 32)
            primary_doc = _clean_text(primary_docs[index] if index < len(primary_docs) else "", 300)
            if str(form).upper() not in SEC_FORM_TYPES or not filing_day or filing_day < cutoff or not accession or not primary_doc:
                continue
            candidates.append({"form": str(form).upper(), "filing_date": filing_day, "accession": accession, "primary_doc": primary_doc})

    filings_payload = payload.get("filings") or {}
    add_candidate_rows(filings_payload.get("recent") or {})
    old_submission_files: list[str] = []
    for file_row in filings_payload.get("files") or []:
        if not isinstance(file_row, dict):
            continue
        file_to = _safe_date(file_row.get("filingTo"))
        name = _clean_text(file_row.get("name"), 160)
        if name and file_to and file_to >= cutoff:
            old_submission_files.append(name)
    old_file_errors: list[dict[str, str]] = []
    for name in old_submission_files:
        old_url = f"https://data.sec.gov/submissions/{name}"
        try:
            old_payload = _http_get(old_url, timeout=20.0).json()
            if isinstance(old_payload, dict):
                add_candidate_rows(old_payload)
        except Exception as exc:
            old_file_errors.append({"file": name, "error": _clean_text(exc, 240)})
        time.sleep(0.12)
    candidates = list({candidate["accession"]: candidate for candidate in candidates}.values())
    candidates.sort(key=lambda item: (item["filing_date"], item["accession"]), reverse=True)

    seen_accessions = {event.accession_number for event in cached if event.accession_number}
    missing = [candidate for candidate in candidates if candidate["accession"] not in seen_accessions]
    fetched_events: list[InsiderTransaction] = []
    fetch_errors: list[dict[str, str]] = list(old_file_errors)
    for candidate in missing[: max(1, min(max_filings, 100))]:
        accession_compact = candidate["accession"].replace("-", "")
        # submissions may expose an XSL-rendering path such as
        # ``xslF345X06/wk-form4_....xml``.  The raw ownership XML lives at the
        # accession root and is the reproducible parser input.
        raw_document_name = candidate["primary_doc"].rsplit("/", 1)[-1]
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_compact}/{raw_document_name}"
        )
        try:
            response = _http_get(source_url, timeout=20.0)
            fetched_events.extend(
                parse_sec_form4_xml(
                    response.text,
                    source_url=source_url,
                    filing_date=candidate["filing_date"],
                    accession_number=candidate["accession"],
                )
            )
        except Exception as exc:
            fetch_errors.append({"accession": candidate["accession"], "error": _clean_text(exc, 240)})
        time.sleep(0.12)
    merged = merge_transactions(fetched_events, cached)
    remaining = max(0, len(missing) - min(len(missing), max_filings)) + len(fetch_errors)
    status = {
        "provider": "SEC EDGAR",
        "source_tier": "primary",
        "ticker": ticker,
        "cik": cik,
        "company_name": company.get("company_name") or payload.get("name"),
        "lookback_days": lookback_days,
        "candidate_filing_count": len(candidates),
        "old_submission_file_count": len(old_submission_files),
        "new_filing_attempt_count": min(len(missing), max_filings),
        "new_event_count": len(fetched_events),
        "cached_event_count": len(merged),
        "remaining_filing_count": remaining,
        "coverage_complete": remaining == 0,
        "errors": fetch_errors[:10],
        "submissions_url": submissions_url,
        "ticker_map": map_status,
    }
    _save_cached_events(settings, ticker, merged, source_status=status)
    return merged, status


def fetch_dart_insider_events(
    ticker: str,
    settings: Settings,
) -> tuple[list[InsiderTransaction], dict[str, Any]]:
    ticker = normalize_ticker(ticker)
    client = OpenDartClient(settings)
    if not client.is_configured:
        raise RuntimeError("DART_API_KEY가 설정되지 않았습니다.")
    corp, payload = client.fetch_insider_ownership(ticker)
    events = parse_dart_elestock_payload(payload, ticker=ticker, corp=corp)
    status = {
        "provider": "OpenDART",
        "source_tier": "primary",
        "ticker": ticker,
        "corp_code": corp.get("corp_code"),
        "company_name": corp.get("corp_name"),
        "candidate_filing_count": len(payload.get("list") or []),
        "cached_event_count": len(events),
        "remaining_filing_count": 0,
        "coverage_complete": True,
        "api": "elestock.json",
    }
    _save_cached_events(settings, ticker, events, source_status=status)
    return events, status


def fetch_price_history(ticker: str, market: str, settings: Settings, *, lookback_days: int = 800) -> tuple[list[PriceBar], dict[str, Any]]:
    end = current_storage_date()
    start = end - timedelta(days=max(370, lookback_days))
    if market == "KR":
        url = f"{settings.naver_finance_base_url.rstrip('/')}/api/stock/{ticker}/price"
        response = httpx.get(
            url,
            params={"pageSize": "600", "page": "1"},
            headers={"User-Agent": settings.ticker_registry_user_agent},
            timeout=settings.naver_finance_timeout_seconds,
            follow_redirects=True,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        raw_rows = payload if isinstance(payload, list) else payload.get("priceInfos") or payload.get("data") or []
        bars: list[PriceBar] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            bar_date = _safe_date(row.get("localTradedAt") or row.get("date") or row.get("tradingDate"))
            close = _safe_float(row.get("closePrice") or row.get("close"))
            if bar_date and close is not None:
                bars.append(
                    PriceBar(
                        date=bar_date,
                        close=close,
                        high=_safe_float(row.get("highPrice") or row.get("high")),
                        low=_safe_float(row.get("lowPrice") or row.get("low")),
                        open=_safe_float(row.get("openPrice") or row.get("open")),
                        volume=_safe_float(row.get("accumulatedTradingVolume") or row.get("volume")),
                    )
                )
        return sorted(bars, key=lambda item: item.date), {"provider": "Naver Finance", "source_url": url, "configured": True}

    api_key = settings.tiingo_api_key.strip()
    if not api_key:
        return [], {"provider": "Tiingo", "configured": False, "reason": "TIINGO_API_KEY 확인 필요"}
    url = f"{settings.tiingo_base_url.rstrip('/')}/tiingo/daily/{ticker}/prices"
    response = httpx.get(
        url,
        params={
            "token": api_key,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "resampleFreq": "daily",
        },
        timeout=settings.tiingo_timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    )
    response.raise_for_status()
    payload = response.json()
    bars = []
    for row in payload if isinstance(payload, list) else []:
        bar_date = _safe_date(row.get("date"))
        close = _safe_float(row.get("adjClose") or row.get("close"))
        if bar_date and close is not None:
            bars.append(
                PriceBar(
                    date=bar_date,
                    close=close,
                    high=_safe_float(row.get("adjHigh") or row.get("high")),
                    low=_safe_float(row.get("adjLow") or row.get("low")),
                    open=_safe_float(row.get("adjOpen") or row.get("open")),
                    volume=_safe_float(row.get("adjVolume") or row.get("volume")),
                )
            )
    return sorted(bars, key=lambda item: item.date), {"provider": "Tiingo", "source_url": url, "configured": True}


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    return (current / previous - 1.0) * 100.0


def build_price_context(price_rows: list[PriceBar | dict[str, Any]], event_date: date) -> dict[str, Any]:
    bars: list[PriceBar] = []
    for row in price_rows:
        try:
            bars.append(row if isinstance(row, PriceBar) else PriceBar.model_validate(row))
        except Exception:
            continue
    bars.sort(key=lambda item: item.date)
    if not bars:
        return {
            "status": "unavailable",
            "message": "가격 이력 확인 필요",
            "latest_close": None,
            "week52_percentile": None,
            "volatility": {"one_month_avg_abs_daily_pct": None, "three_month_avg_abs_daily_pct": None},
            "representative_moves": [],
        }

    returns: list[dict[str, Any]] = []
    for previous, current in zip(bars, bars[1:]):
        change = _pct_change(current.close, previous.close)
        if change is not None:
            returns.append({"date": current.date.isoformat(), "return_pct": change})
    latest = bars[-1]
    week52 = [bar for bar in bars if bar.date >= latest.date - timedelta(days=370)]
    highs = [bar.high if bar.high is not None else bar.close for bar in week52]
    lows = [bar.low if bar.low is not None else bar.close for bar in week52]
    week52_high = max(highs) if highs else None
    week52_low = min(lows) if lows else None
    percentile = None
    if week52_high is not None and week52_low is not None and week52_high > week52_low:
        percentile = (latest.close - week52_low) / (week52_high - week52_low) * 100.0

    event_index = next((i for i, bar in enumerate(bars) if bar.date >= event_date), None)
    event_bar = bars[event_index] if event_index is not None else None
    event_previous = bars[event_index - 1] if event_index is not None and event_index > 0 else None
    event_change = _pct_change(event_bar.close if event_bar else None, event_previous.close if event_previous else None)
    one_month = returns[-21:]
    three_month = returns[-63:]
    avg_abs = lambda rows: (sum(abs(item["return_pct"]) for item in rows) / len(rows)) if rows else None
    representative = sorted(returns[-63:], key=lambda item: abs(item["return_pct"]), reverse=True)[:3]
    return {
        "status": "available",
        "as_of": latest.date.isoformat(),
        "latest_close": latest.close,
        "week52_low": week52_low,
        "week52_high": week52_high,
        "week52_percentile": percentile,
        "event_session_date": event_bar.date.isoformat() if event_bar else None,
        "event_close": event_bar.close if event_bar else None,
        "event_previous_close": event_previous.close if event_previous else None,
        "event_day_change_pct": event_change,
        "volatility": {
            "one_month_avg_abs_daily_pct": avg_abs(one_month),
            "three_month_avg_abs_daily_pct": avg_abs(three_month),
            "method": "daily close-to-close absolute return average",
        },
        "representative_moves": representative,
        "bar_count": len(bars),
    }


def _signed_direction(event: InsiderTransaction) -> int:
    code = event.tx_code.upper()
    disposition = (event.acquired_disposed or "").upper()
    if code in {"P", "ACQUIRE"} or disposition == "A":
        return 1
    if code in {"S", "DISPOSE"} or disposition == "D":
        return -1
    return 0


def build_flow_history(
    events: list[InsiderTransaction],
    *,
    as_of: date,
    coverage_complete: bool,
    focus_insider: str | None = None,
) -> dict[str, Any]:
    windows: dict[str, Any] = {}
    for months, days in ((6, 183), (12, 366), (24, 731)):
        rows = [event for event in events if as_of - timedelta(days=days) <= event.tx_date <= as_of]
        acquired_shares = sum((event.shares or 0.0) for event in rows if _signed_direction(event) > 0)
        disposed_shares = sum((event.shares or 0.0) for event in rows if _signed_direction(event) < 0)
        acquired_value = sum((event.transaction_value or 0.0) for event in rows if _signed_direction(event) > 0)
        disposed_value = sum((event.transaction_value or 0.0) for event in rows if _signed_direction(event) < 0)
        known_value_count = sum(1 for event in rows if event.transaction_value is not None)
        open_market_rows = [event for event in rows if event.tx_code.upper() in OPEN_MARKET_CODES]
        open_market_acquired = sum((event.shares or 0.0) for event in open_market_rows if event.tx_code.upper() == "P")
        open_market_disposed = sum((event.shares or 0.0) for event in open_market_rows if event.tx_code.upper() == "S")
        open_market_buy_value = sum((event.transaction_value or 0.0) for event in open_market_rows if event.tx_code.upper() == "P")
        open_market_sell_value = sum((event.transaction_value or 0.0) for event in open_market_rows if event.tx_code.upper() == "S")
        open_market_known_value_count = sum(1 for event in open_market_rows if event.transaction_value is not None)
        windows[f"{months}m"] = {
            "event_count": len(rows),
            "acquired_shares": acquired_shares,
            "disposed_shares": disposed_shares,
            "net_shares": acquired_shares - disposed_shares,
            "known_acquired_value": acquired_value if known_value_count else None,
            "known_disposed_value": disposed_value if known_value_count else None,
            "known_net_value": acquired_value - disposed_value if known_value_count else None,
            "known_value_event_count": known_value_count,
            "open_market_event_count": len(open_market_rows),
            "open_market_acquired_shares": open_market_acquired,
            "open_market_disposed_shares": open_market_disposed,
            "open_market_net_shares": open_market_acquired - open_market_disposed,
            "known_open_market_net_value": (
                open_market_buy_value - open_market_sell_value if open_market_known_value_count else None
            ),
            "non_open_market_event_count": len(rows) - len(open_market_rows),
            "coverage_complete": coverage_complete,
            "coverage_note": None if coverage_complete else "일부 공시만 수집됨 — 완전한 기간 합계 확인 필요",
        }
    normalized_focus = _clean_text(focus_insider, 120).casefold()
    same_insider = [
        event for event in events
        if normalized_focus and _clean_text(event.insider_name, 120).casefold() == normalized_focus
    ]
    same_insider_rows = [
        {
            "tx_date": event.tx_date.isoformat(),
            "tx_code": event.tx_code,
            "shares": event.shares,
            "avg_price": event.avg_price,
            "post_shares": event.post_shares,
            "is_10b5_1": event.is_10b5_1,
            "source_url": event.source_url,
        }
        for event in same_insider[:20]
    ]
    buy_prices = [event.avg_price for event in same_insider if event.tx_code.upper() == "P" and event.avg_price is not None]
    sell_prices = [event.avg_price for event in same_insider if event.tx_code.upper() == "S" and event.avg_price is not None]
    return {
        "windows": windows,
        "event_count": len(events),
        "coverage_complete": coverage_complete,
        "same_insider_history": same_insider_rows,
        "same_insider_price_pattern": {
            "lowest_known_buy_price": min(buy_prices) if buy_prices else None,
            "highest_known_sell_price": max(sell_prices) if sell_prices else None,
            "interpretation": (
                "같은 내부자의 확인된 매수·매도 단가가 모두 있어 고가 매도/저가 매수 패턴을 비교할 수 있습니다."
                if buy_prices and sell_prices
                else "같은 내부자의 매수·매도 단가 표본이 부족해 고가 매도/저가 매수 패턴은 확인 필요입니다."
            ),
        },
    }


def build_signal_strength(event: InsiderTransaction, price_context: dict[str, Any]) -> dict[str, Any]:
    direction = _signed_direction(event)
    code = event.tx_code.upper()
    contributions: list[dict[str, Any]] = []
    score = 10
    if code in OPEN_MARKET_CODES:
        points = 35 if code == "P" else 25
        score += points
        contributions.append({"rule": "open_market", "points": points, "evidence": f"Form 4 거래코드 {code}"})
    else:
        contributions.append({"rule": "non_open_market", "points": 0, "evidence": f"거래코드 {code}; 장내 재량거래로 단정 불가"})
    if event.is_10b5_1 is True:
        score -= 20
        contributions.append({"rule": "planned_trade", "points": -20, "evidence": "10b5-1 계획 표시/각주"})
    elif event.is_10b5_1 is None:
        contributions.append({"rule": "plan_unknown", "points": 0, "evidence": "10b5-1 여부 확인 필요"})

    percentile = _safe_float(price_context.get("week52_percentile"))
    vol = _safe_float((price_context.get("volatility") or {}).get("three_month_avg_abs_daily_pct"))
    if direction > 0 and percentile is not None and percentile <= 30:
        score += 15
        contributions.append({"rule": "low_price_zone", "points": 15, "evidence": f"52주 범위 {percentile:.1f}%ile"})
    if vol is not None and vol >= 2.5:
        score += 8
        contributions.append({"rule": "high_volatility", "points": 8, "evidence": f"3개월 평균 절대 일등락 {vol:.2f}%"})
    if event.transaction_value is not None:
        points = 15 if event.transaction_value >= 1_000_000 else 8 if event.transaction_value >= 100_000 else 0
        if points:
            score += points
            contributions.append({"rule": "absolute_trade_size", "points": points, "evidence": f"확인 거래금액 {event.transaction_value:,.0f}"})
    ownership_change_pct = None
    if event.shares is not None and event.post_shares not in {None, 0}:
        before = event.post_shares - event.shares if direction > 0 else event.post_shares + event.shares
        if before and before > 0:
            ownership_change_pct = event.shares / before * 100.0
            if ownership_change_pct >= 10:
                score += 12
                contributions.append({"rule": "meaningful_holding_change", "points": 12, "evidence": f"거래 전 보유량 대비 {ownership_change_pct:.1f}%"})
    combo = (
        direction > 0
        and code == "P"
        and event.is_10b5_1 is not True
        and percentile is not None
        and percentile <= 30
        and vol is not None
        and vol >= 2.5
        and event.transaction_value is not None
        and event.transaction_value >= 100_000
    )
    if combo:
        score += 10
        contributions.append({"rule": "discretionary_buy_combo", "points": 10, "evidence": "저가 구간 + 고변동성 + 대규모 재량 매수 조건 충족"})
    score = max(0, min(score, 100))
    strength = "강함" if score >= 70 else "보통" if score >= 45 else "약함"
    direction_label = "긍정" if direction > 0 else "부정" if direction < 0 else "중립"
    missing = []
    if event.avg_price is None:
        missing.append("거래단가")
    if event.is_10b5_1 is None:
        missing.append("10b5-1 여부")
    if percentile is None:
        missing.append("52주 가격 위치")
    return {
        "score": score,
        "strength": strength,
        "direction": direction_label,
        "signal_label": f"{direction_label}·{strength}",
        "ownership_change_pct": ownership_change_pct,
        "contributions": contributions,
        "missing_inputs": missing,
        "calibration_note": "규칙 기반 상대 비교 점수이며 백테스트된 매매 확률이 아닙니다.",
    }


def _forward_return(bars: list[PriceBar], event_date: date, trading_days: int) -> dict[str, Any] | None:
    start_index = next((index for index, bar in enumerate(bars) if bar.date >= event_date), None)
    if start_index is None or start_index + trading_days >= len(bars):
        return None
    start = bars[start_index]
    end = bars[start_index + trading_days]
    return {
        "start_date": start.date.isoformat(),
        "end_date": end.date.isoformat(),
        "return_pct": _pct_change(end.close, start.close),
    }


def build_historical_reactions(
    events: list[InsiderTransaction],
    price_rows: list[PriceBar | dict[str, Any]],
    current_event: InsiderTransaction,
) -> dict[str, Any]:
    bars = sorted(
        [row if isinstance(row, PriceBar) else PriceBar.model_validate(row) for row in price_rows],
        key=lambda item: item.date,
    ) if price_rows else []
    if not bars:
        return {"status": "unavailable", "message": "가격 이력 확인 필요", "cases": [], "summary": {"sample_size": 0}}
    direction = _signed_direction(current_event)
    comparable = [event for event in events if event.tx_date < current_event.tx_date and _signed_direction(event) == direction]
    cases = []
    for event in comparable[:20]:
        one_month = _forward_return(bars, event.filing_date or event.tx_date, 21)
        three_month = _forward_return(bars, event.filing_date or event.tx_date, 63)
        if one_month or three_month:
            cases.append(
                {
                    "tx_date": event.tx_date.isoformat(),
                    "filing_date": (event.filing_date or event.tx_date).isoformat(),
                    "insider_name": event.insider_name,
                    "tx_code": event.tx_code,
                    "one_month": one_month,
                    "three_month": three_month,
                    "source_url": event.source_url,
                }
            )
    def average(period: str) -> float | None:
        values = [case[period]["return_pct"] for case in cases if case.get(period) and case[period].get("return_pct") is not None]
        return sum(values) / len(values) if values else None
    return {
        "status": "available" if cases else "insufficient_sample",
        "cases": cases,
        "summary": {
            "sample_size": len(cases),
            "average_one_month_return_pct": average("one_month"),
            "average_three_month_return_pct": average("three_month"),
            "warning": "소표본·사후선택 편향이 있어 인과관계나 재현 확률로 해석하지 않습니다." if cases else "비교 가능한 과거 사례 확인 필요",
        },
    }


def _research_checkpoints(settings: Settings, ticker: str, request: InsiderAnalysisRequest) -> dict[str, Any]:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    entries = [
        entry for entry in read_manifest(vault_dir)
        if str(entry.get("ticker") or "").upper() == ticker and str(entry.get("type") or "") != INSIDER_REPORT_TYPE
    ]
    entries.sort(key=lambda item: (str(item.get("date") or ""), str(item.get("file_name") or "")), reverse=True)
    evidence = []
    for entry in entries[:6]:
        evidence.append(
            {
                "date": entry.get("date"),
                "type": entry.get("type"),
                "title": entry.get("title") or entry.get("file_name"),
                "summary": _clean_text(entry.get("summary"), 360) or "요약 확인 필요",
                "source_url": entry.get("source_url") or entry.get("final_url"),
            }
        )
    catalysts = [_clean_text(value, 240) for value in request.catalysts if _clean_text(value, 240)]
    if not catalysts:
        catalysts = [row["summary"] for row in evidence[:3] if row.get("summary") != "요약 확인 필요"]
    return {
        "valuation_band": request.valuation_context or "확인 필요 — 최신 주가와 공식 재무지표 기반 밸류에이션 밴드 입력 필요",
        "fundamental_catalysts": catalysts or ["확인 필요 — 최근 실적·제품·M&A·규제 촉매 근거 보강 필요"],
        "linked_research": evidence,
        "risk_management": [
            "내부자 거래 한 건을 단독 투자 판단 근거로 사용하지 않기",
            "거래 목적·보상 구조·10b5-1 각주를 공식 원문에서 재확인하기",
            "가격 변동성에 맞춘 손실 허용 범위는 별도의 포트폴리오 규칙으로 검토하기",
        ],
    }


def _value_or_review(value: Any, *, number: bool = False) -> Any:
    if value is None or value == "":
        return "확인 필요"
    if number and isinstance(value, (int, float)):
        return round(float(value), 4)
    return value


def build_insider_report(
    *,
    event: InsiderTransaction,
    events: list[InsiderTransaction],
    price_rows: list[PriceBar | dict[str, Any]],
    source_status: dict[str, Any],
    checkpoints: dict[str, Any],
) -> dict[str, Any]:
    event_anchor = event.filing_date or event.tx_date
    price_context = build_price_context(price_rows, event_anchor)
    flow = build_flow_history(
        events,
        as_of=current_storage_date(),
        coverage_complete=bool(source_status.get("coverage_complete")),
        focus_insider=event.insider_name,
    )
    signal = build_signal_strength(event, price_context)
    history = build_historical_reactions(events, price_rows, event)
    facts_complete = sum(
        value is not None for value in (event.insider_name, event.title, event.shares, event.avg_price, event.post_shares)
    )
    evidence_strength = "높음" if event.source_type in {"sec_form4", "opendart_elestock"} and facts_complete >= 4 else "보통" if event.source_type in {"sec_form4", "opendart_elestock"} else "낮음"
    transaction_code_notes = {
        "sec_form4": "SEC Form 4 원문 코드",
        "opendart_elestock": "OpenDART 주식수 증감 정규화 코드",
        "manual_summary": "텍스트 요약에서 추출 — 공식 원문 확인 필요",
        "manual_structured": "구조화 입력 — 공식 원문 확인 필요",
    }
    source_summary_labels = {
        "sec_form4": "SEC Form 4 원문",
        "opendart_elestock": "OpenDART 소유보고 원문",
        "manual_summary": "사용자 입력 요약",
        "manual_structured": "사용자 구조화 입력",
    }
    transaction_context = {
        "insider_name": _value_or_review(event.insider_name),
        "title": _value_or_review(event.title),
        "relationship": _value_or_review(event.relationship),
        "transaction_date": event.tx_date.isoformat(),
        "filing_date": event.filing_date.isoformat() if event.filing_date else "확인 필요",
        "transaction_code": event.tx_code,
        "transaction_code_note": transaction_code_notes.get(event.source_type, "입력 자료에서 정규화 — 공식 원문 확인 필요"),
        "shares": _value_or_review(event.shares, number=True),
        "average_price": _value_or_review(event.avg_price, number=True),
        "transaction_value": _value_or_review(event.transaction_value, number=True),
        "post_transaction_shares": _value_or_review(event.post_shares, number=True),
        "security_title": _value_or_review(event.security_title),
        "direct_or_indirect": _value_or_review(event.direct_or_indirect),
        "source_url": event.source_url or "확인 필요",
    }
    price_axis = {
        "latest_close": _value_or_review(price_context.get("latest_close"), number=True),
        "as_of": price_context.get("as_of") or "확인 필요",
        "event_day_change_pct": _value_or_review(price_context.get("event_day_change_pct"), number=True),
        "week52_low": _value_or_review(price_context.get("week52_low"), number=True),
        "week52_high": _value_or_review(price_context.get("week52_high"), number=True),
        "week52_percentile": _value_or_review(price_context.get("week52_percentile"), number=True),
        "one_month_avg_abs_daily_pct": _value_or_review((price_context.get("volatility") or {}).get("one_month_avg_abs_daily_pct"), number=True),
        "three_month_avg_abs_daily_pct": _value_or_review((price_context.get("volatility") or {}).get("three_month_avg_abs_daily_pct"), number=True),
        "representative_moves": price_context.get("representative_moves") or [],
        "status": price_context.get("status"),
    }
    missing = list(signal.get("missing_inputs") or [])
    if not source_status.get("coverage_complete"):
        missing.append("6/12/24개월 공시 전체 범위")
    if not checkpoints.get("linked_research"):
        missing.append("기존 실적·밸류에이션 리서치")
    return {
        "status": "success",
        "module": "insider_trading_research",
        "generated_at": current_storage_timestamp(),
        "ticker": event.ticker,
        "market": event.market,
        "company_name": event.company_name or event.ticker,
        "framework": "CELH-compatible-six-axis-v1",
        "summary": (
            f"{event.ticker} {event.tx_code} 내부자거래를 "
            f"{source_summary_labels.get(event.source_type, '입력 자료')} 기준으로 정규화했습니다. "
            f"신호 평가는 {signal['signal_label']}이며 미확인 항목을 별도 표시합니다."
        ),
        "evidence": {
            "strength": evidence_strength,
            "confidence": round(0.9 if evidence_strength == "높음" else 0.72 if evidence_strength == "보통" else 0.48, 2),
            "source_status": source_status,
            "source_type": event.source_type,
            "notes": event.notes,
        },
        "axes": {
            "transaction_context": transaction_context,
            "price_and_volatility": price_axis,
            "insider_flow_history": flow,
            "signal_strength": signal,
            "historical_pattern": history,
            "investment_checkpoints": checkpoints,
        },
        "facts": transaction_context,
        "interpretation": {
            "signal": signal["signal_label"],
            "reason": [item["evidence"] for item in signal["contributions"] if item.get("points")],
            "limitations": missing or ["공식 원문과 최신 재무 근거의 사람 검토 필요"],
        },
        "thesis_impact": "강화" if signal["direction"] == "긍정" and signal["strength"] == "강함" else "약화" if signal["direction"] == "부정" and signal["strength"] == "강함" else "혼합" if signal["direction"] in {"긍정", "부정"} else "중립",
        "next_actions": [
            "공식 공시 원문의 직함·거래코드·각주·거래 후 보유량을 사람 검토",
            "미확인 거래단가·10b5-1 여부·밸류에이션을 공식 근거로 보강",
            "내부자 거래 외 실적·현금흐름·촉매·포트폴리오 위험을 함께 검토",
        ],
        "safety": {"orders": False, "messages": False, "account_changes": False},
        "disclaimer": "투자 리서치용 비교 자료이며 매수·매도 지시나 자동 주문 신호가 아닙니다.",
    }


def render_insider_report_markdown(report: dict[str, Any]) -> str:
    axes = report["axes"]
    tx = axes["transaction_context"]
    price = axes["price_and_volatility"]
    flow = axes["insider_flow_history"]["windows"]
    signal = axes["signal_strength"]
    history = axes["historical_pattern"]
    checkpoints = axes["investment_checkpoints"]
    lines = [
        f"# {report['company_name']} ({report['ticker']}) 내부자거래 리서치",
        "",
        f"- 생성: {report['generated_at']}",
        f"- 시장: {report['market']}",
        f"- 근거 강도: {report['evidence']['strength']} / 신뢰도 {report['evidence']['confidence']:.0%}",
        f"- 투자 논거 영향: {report['thesis_impact']}",
        "",
        "## 1. 거래 맥락",
        "",
        f"- 내부자: {tx['insider_name']} / {tx['title']} / {tx['relationship']}",
        f"- 거래일·공시일: {tx['transaction_date']} / {tx['filing_date']}",
        f"- 코드: {tx['transaction_code']} ({tx['transaction_code_note']})",
        f"- 주식수·평균단가·금액: {tx['shares']} / {tx['average_price']} / {tx['transaction_value']}",
        f"- 거래 후 보유량: {tx['post_transaction_shares']}",
        f"- 원문: {tx['source_url']}",
        "",
        "## 2. 가격·변동성 위치",
        "",
        f"- 최근 종가: {price['latest_close']} ({price['as_of']})",
        f"- 공시 기준 일등락: {price['event_day_change_pct']}%",
        f"- 52주 범위·위치: {price['week52_low']} ~ {price['week52_high']} / {price['week52_percentile']}%ile",
        f"- 1·3개월 평균 절대 일등락: {price['one_month_avg_abs_daily_pct']}% / {price['three_month_avg_abs_daily_pct']}%",
        "",
        "## 3. 내부자 수급 히스토리",
        "",
    ]
    for window in ("6m", "12m", "24m"):
        row = flow[window]
        lines.append(
            f"- {window}: {row['event_count']}건, 보고상 순변동 {row['net_shares']:,.0f}주, 장내 P/S 순변동 {row['open_market_net_shares']:,.0f}주, 장내 P/S 알려진 순금액 {row['known_open_market_net_value'] if row['known_open_market_net_value'] is not None else '확인 필요'}, 범위 {'완전' if row['coverage_complete'] else '부분'}"
        )
    same_history = flow.get("same_insider_history") or []
    same_pattern = flow.get("same_insider_price_pattern") or {}
    lines.append(
        "- 동일 내부자 이력: "
        + (
            " · ".join(
                f"{row['tx_date']} {row['tx_code']} {row.get('shares') if row.get('shares') is not None else '확인 필요'}주 @ {row.get('avg_price') if row.get('avg_price') is not None else '확인 필요'}"
                for row in same_history[:10]
            )
            if same_history
            else "확인 필요"
        )
    )
    lines.append(f"- 고가 매도/저가 매수 패턴: {same_pattern.get('interpretation') or '확인 필요'}")
    lines.extend(
        [
            "",
            "## 4. 신호 강도 평가",
            "",
            f"- 판정: {signal['signal_label']} ({signal['score']}/100)",
            *[f"- {item['evidence']} ({item['points']:+d})" for item in signal["contributions"]],
            f"- 보정: {signal['calibration_note']}",
            "",
            "## 5. 역사적 패턴",
            "",
            f"- 비교 사례: {history['summary']['sample_size']}건",
            f"- 평균 1개월 반응: {history['summary'].get('average_one_month_return_pct') if history['summary'].get('average_one_month_return_pct') is not None else '확인 필요'}%",
            f"- 평균 3개월 반응: {history['summary'].get('average_three_month_return_pct') if history['summary'].get('average_three_month_return_pct') is not None else '확인 필요'}%",
            f"- 주의: {history['summary'].get('warning')}",
            "",
            "## 6. 투자 체크포인트",
            "",
            f"- 밸류에이션: {checkpoints['valuation_band']}",
            *[f"- 촉매: {item}" for item in checkpoints["fundamental_catalysts"]],
            *[f"- 위험관리: {item}" for item in checkpoints["risk_management"]],
            "",
            "## 사실·해석·영향 구분",
            "",
            f"- 사실: {tx['insider_name']}의 {tx['transaction_code']} 거래, {tx['shares']}주, 공시일 {tx['filing_date']}",
            f"- 해석: {report['interpretation']['signal']}; {'; '.join(report['interpretation']['reason']) or '확인 가능한 가중 근거 부족'}",
            f"- 투자 논거 영향: {report['thesis_impact']}",
            *[f"- 확인 필요: {item}" for item in report["interpretation"]["limitations"]],
            "",
            f"> {report['disclaimer']}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _save_report(report: dict[str, Any], settings: Settings) -> dict[str, Any]:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    event = report["axes"]["transaction_context"]
    source_url = event.get("source_url") if event.get("source_url") != "확인 필요" else None
    markdown = render_insider_report_markdown(report)
    suffix = "-".join(
        part for part in [str(event.get("transaction_date") or ""), str(event.get("transaction_code") or ""), _clean_text(event.get("insider_name"), 40)] if part and part != "확인 필요"
    )
    manifest_entry = {
        "title": f"{report['company_name']} 내부자거래 6축 분석",
        "summary": report["summary"],
        "scope": "insider_trading",
        "source_type": report["evidence"]["source_type"],
        "source_url": source_url,
        "source_confidence": report["evidence"]["confidence"],
        "confidence": report["evidence"]["confidence"],
        "thesis_impact": report["thesis_impact"],
        "tags": ["insider_trading", "ownership", report["market"].lower(), "six_axis"],
        "generated_at": report["generated_at"],
    }
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker=report["ticker"],
        report_type=INSIDER_REPORT_TYPE,
        markdown=markdown,
        structured_payload=report,
        manifest_entry=manifest_entry,
        report_date=current_storage_date(),
        file_suffix=suffix,
        overwrite_existing=True,
    )
    saved_entry = next(
        (entry for entry in read_manifest(vault_dir) if entry.get("file_name") == storage.file_name and str(entry.get("ticker") or "").upper() == report["ticker"]),
        None,
    )
    rag = upsert_research_memory_document(vault_dir=vault_dir, entry=saved_entry, full_text=markdown) if saved_entry else None
    return {"storage": storage.model_dump(mode="json"), "rag_document": rag}


def analyze_insider_trading(request: InsiderAnalysisRequest, settings: Settings) -> dict[str, Any]:
    ticker_hint = normalize_ticker(request.ticker) if request.ticker else ""
    source_metadata = None
    warnings: list[str] = []
    if request.source_url:
        source_metadata = classify_source_url(request.source_url)
        if source_metadata["source_tier"] == "secondary":
            warnings.append("보조 사이트 URL은 참고 링크로만 보존하고 공식 SEC/OpenDART를 재조회했습니다.")

    manual_event = transaction_from_request(request)
    text_event = parse_insider_summary_text(request.source_text or "", ticker_hint=ticker_hint, market=request.market)
    if not ticker_hint:
        ticker_hint = manual_event.ticker if manual_event else text_event.ticker if text_event else ""
    direct_events: list[InsiderTransaction] = []
    if source_metadata and source_metadata["provider"] == "SEC" and request.source_url:
        if urlparse(request.source_url).path.lower().endswith(".xml"):
            response = _http_get(request.source_url, timeout=20.0)
            direct_events = parse_sec_form4_xml(
                response.text,
                source_url=request.source_url,
                filing_date=request.filing_date,
            )
            mismatches = [event.ticker for event in direct_events if ticker_hint and event.ticker != ticker_hint]
            if mismatches:
                raise ValueError(
                    f"입력 티커 {ticker_hint}와 SEC 원문 티커 {mismatches[0]}가 일치하지 않습니다."
                )
            if not ticker_hint and direct_events:
                ticker_hint = direct_events[0].ticker
    if not ticker_hint:
        raise ValueError(
            "티커 또는 티커가 포함된 입력 요약이 필요합니다. SEC 원본 XML URL은 티커 없이도 사용할 수 있습니다."
        )
    market = normalize_market(ticker_hint, request.market)
    official_events: list[InsiderTransaction] = []
    source_status: dict[str, Any] = {
        "provider": "manual",
        "source_tier": source_metadata.get("source_tier") if source_metadata else "manual",
        "coverage_complete": False,
        "message": "공식 공시 자동 조회를 사용하지 않았습니다.",
    }
    if request.fetch_external:
        try:
            if market == "US":
                official_events, source_status = fetch_sec_form4_events(
                    ticker_hint, settings, max_filings=request.max_filings
                )
            else:
                official_events, source_status = fetch_dart_insider_events(ticker_hint, settings)
        except Exception as exc:
            warnings.append(f"공식 공시 조회 실패: {_clean_text(exc, 300)}")
            cached, cache_record = _cached_events(settings, ticker_hint)
            official_events = cached
            source_status = {
                "provider": "cached_event_store" if cached else "unavailable",
                "source_tier": "primary-cache" if cached else "unavailable",
                "coverage_complete": bool((cache_record.get("source_status") or {}).get("coverage_complete")),
                "message": _clean_text(exc, 300),
            }
    events = merge_transactions(
        [event for event in (manual_event, text_event) if event is not None],
        direct_events,
        official_events,
    )
    if not events:
        no_event_status = (
            "source_unavailable"
            if str(source_status.get("provider") or "") in {"unavailable", "cached_event_store"}
            and not official_events
            else "no_events"
        )
        return {
            "status": no_event_status,
            "module": "insider_trading_research",
            "ticker": ticker_hint,
            "market": market,
            "generated_at": current_storage_timestamp(),
            "message": "분석할 내부자 거래 공시가 없습니다.",
            "source_status": source_status,
            "warnings": warnings,
            "next_actions": ["공식 공시 URL 또는 거래일·거래코드가 포함된 요약을 입력하세요."],
        }
    preferred = manual_event or text_event
    event = preferred or events[0]
    if request.source_url and event.source_url is None:
        event = event.model_copy(update={"source_url": request.source_url})
        events = merge_transactions([event], events)
    price_rows = request.price_history
    price_status: dict[str, Any] = {"provider": "request", "configured": bool(price_rows)}
    if not price_rows and request.fetch_external:
        try:
            price_rows, price_status = fetch_price_history(ticker_hint, market, settings)
        except Exception as exc:
            warnings.append(f"가격 이력 조회 실패: {_clean_text(exc, 300)}")
            price_rows = []
            price_status = {"provider": "unavailable", "configured": False, "reason": _clean_text(exc, 300)}
    checkpoints = _research_checkpoints(settings, ticker_hint, request)
    report = build_insider_report(
        event=event,
        events=events,
        price_rows=price_rows,
        source_status=source_status,
        checkpoints=checkpoints,
    )
    report["warnings"] = warnings
    report["source_url_metadata"] = source_metadata
    report["price_source"] = price_status
    report["event_count"] = len(events)
    report["storage"] = None
    report["rag_document"] = None
    if request.save_result:
        saved = _save_report(report, settings)
        report.update(saved)
    return report


def read_insider_trading_status(settings: Settings) -> dict[str, Any]:
    state = read_json_store(insider_state_path(settings), {})
    cache = read_json_store(insider_event_cache_path(settings), {"tickers": {}})
    ticker_rows = state.get("ticker_results") if isinstance(state.get("ticker_results"), dict) else {}
    return {
        "status": "success",
        "module": "insider_trading_status",
        "updated_at": state.get("updated_at"),
        "last_run": state.get("last_run"),
        "candidate_scope": state.get("candidate_scope"),
        "cursor": state.get("cursor", 0),
        "processed_ticker_count": len(ticker_rows),
        "cached_ticker_count": len(cache.get("tickers") or {}),
        "ticker_results": ticker_rows,
        "recent_reports": state.get("recent_reports") or [],
        "errors": state.get("errors") or [],
        "automation": {
            "schedule": "기존 InvestmentJournalApp Daily Research Operations 루틴",
            "delivery": "없음",
            "orders": "없음",
            "mode": "가족 전체 보유·관심종목 순환 점검",
        },
    }


def run_insider_trading_batch(
    settings: Settings,
    *,
    tickers: list[str] | None = None,
    max_tickers: int = 8,
    max_filings: int = 24,
    save_result: bool = True,
) -> dict[str, Any]:
    scope = build_family_candidate_scope(settings)
    raw_candidates = tickers or (scope.get("holding_tickers") or []) + (scope.get("interest_tickers") or [])
    candidate_set: set[str] = set()
    skipped_candidates: list[dict[str, str]] = []
    for raw_candidate in raw_candidates:
        if not raw_candidate or str(raw_candidate).strip().upper() == "CASH":
            continue
        try:
            candidate_set.add(normalize_ticker(str(raw_candidate)))
        except ValueError as exc:
            skipped_candidates.append(
                {
                    "ticker": _clean_text(raw_candidate, 32) or "확인 필요",
                    "reason": _clean_text(exc, 160),
                }
            )
    candidates = sorted(candidate_set)
    state = read_json_store(insider_state_path(settings), {})
    cursor = 0 if tickers else int(state.get("cursor") or 0)
    limit = max(1, min(int(max_tickers), 100))
    if not candidates:
        selected: list[str] = []
        next_cursor = 0
    elif tickers:
        selected = candidates[:limit]
        next_cursor = 0
    else:
        selected = [candidates[(cursor + offset) % len(candidates)] for offset in range(min(limit, len(candidates)))]
        next_cursor = (cursor + len(selected)) % len(candidates)

    ticker_results = state.get("ticker_results") if isinstance(state.get("ticker_results"), dict) else {}
    recent_reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    counts = {
        "success": 0,
        "no_events": 0,
        "source_unavailable": 0,
        "not_applicable": len(skipped_candidates),
    }
    for ticker in selected:
        try:
            result = analyze_insider_trading(
                InsiderAnalysisRequest(
                    ticker=ticker,
                    market="AUTO",
                    fetch_external=True,
                    save_result=save_result,
                    max_filings=max_filings,
                ),
                settings,
            )
            status = str(result.get("status") or "source_unavailable")
            if status == "success":
                counts["success"] += 1
                recent_reports.append(
                    {
                        "ticker": ticker,
                        "company_name": result.get("company_name"),
                        "summary": result.get("summary"),
                        "signal": ((result.get("axes") or {}).get("signal_strength") or {}).get("signal_label"),
                        "source_url": ((result.get("axes") or {}).get("transaction_context") or {}).get("source_url"),
                        "storage": result.get("storage"),
                    }
                )
            elif status == "no_events":
                counts["no_events"] += 1
            elif status == "not_applicable":
                counts["not_applicable"] += 1
            else:
                counts["source_unavailable"] += 1
            ticker_results[ticker] = {
                "status": status,
                "checked_at": current_storage_timestamp(),
                "market": result.get("market"),
                "message": result.get("message") or result.get("summary"),
                "source_status": result.get("source_status") or (result.get("evidence") or {}).get("source_status"),
            }
        except Exception as exc:
            message = _clean_text(exc, 300)
            counts["source_unavailable"] += 1
            errors.append({"ticker": ticker, "error": message})
            ticker_results[ticker] = {"status": "source_unavailable", "checked_at": current_storage_timestamp(), "message": message}

    payload = {
        "status": "success" if not errors else "warning",
        "module": "insider_trading_batch",
        "updated_at": current_storage_timestamp(),
        "last_run": {
            "selected_tickers": selected,
            "selected_count": len(selected),
            "candidate_count": len(candidates),
            "counts": counts,
            "error_count": len(errors),
            "skipped_candidate_count": len(skipped_candidates),
            "save_result": save_result,
        },
        "candidate_scope": {
            "label": scope.get("label"),
            "member_portfolio_count": scope.get("member_portfolio_count"),
            "holding_count": scope.get("holding_count"),
            "unique_holding_count": scope.get("unique_holding_count"),
            "interest_count": scope.get("interest_count"),
            "candidate_scope_count": len(candidates),
            "scope_fingerprint": scope.get("scope_fingerprint"),
        },
        "cursor": next_cursor,
        "ticker_results": ticker_results,
        "recent_reports": recent_reports[:20],
        "errors": errors[:20],
        "skipped_candidates": skipped_candidates[:20],
        "safety": {"orders": False, "messages": False, "account_changes": False},
    }
    write_json_store(insider_state_path(settings), payload)
    return payload
