"""Ticker registry source refresh helpers.

The app keeps a small hand-curated registry for high-touch names, then extends it
with cached exchange symbol directories so company-name input can resolve before
falling back to provider quote APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
from re import sub
from typing import Any

import httpx
from bs4 import BeautifulSoup


US_EXCHANGE_LABELS = {
    "A": "NYSE American",
    "N": "NYSE",
    "P": "NYSE Arca",
    "Q": "NASDAQ",
    "V": "IEX",
    "Z": "Cboe BZX",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _normalize_symbol(value: object) -> str:
    return sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip().upper()).strip("-")


def _normalize_kr_code(value: object) -> str:
    digits = sub(r"\D+", "", str(value or ""))
    return digits.zfill(6) if digits else ""


def _company_aliases(name: str) -> list[str]:
    cleaned = _safe_text(name)
    if not cleaned:
        return []
    aliases = {cleaned}
    security_clean = cleaned
    for suffix in [
        " Common Stock",
        " Ordinary Shares",
        " Class A",
        " ADR",
        " ADS",
    ]:
        security_clean = security_clean.replace(suffix, "")
    security_clean = _safe_text(security_clean)
    if security_clean and security_clean != cleaned:
        aliases.add(security_clean)
    no_suffix = security_clean or cleaned
    for suffix in [
        " Inc.",
        " Inc",
        " Incorporated",
        " Corporation",
        " Corp.",
        " Corp",
        " PBC",
        " 주식회사",
        "(주)",
    ]:
        no_suffix = no_suffix.replace(suffix, "")
    no_suffix = _safe_text(no_suffix)
    if no_suffix and no_suffix != cleaned:
        aliases.add(no_suffix)
    compact = cleaned.replace(",", "").replace(".", "")
    if compact and compact != cleaned:
        aliases.add(compact)
    return sorted(aliases)


def _profile(
    *,
    symbol: str,
    company_name: str,
    exchange: str,
    country: str,
    source: str,
    asset_type: str = "equity",
    sector: str | None = None,
    industry: str | None = None,
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "company_name": company_name,
        "aliases": sorted(set([*(aliases or []), *_company_aliases(company_name)])),
        "exchange": exchange,
        "country": country,
        "asset_type": asset_type,
        "sector": sector,
        "industry": industry,
        "business_context": f"{company_name} ({symbol}) 상장 종목 기본 식별 정보입니다.",
        "analysis_focus": "사업 모델, 실적 추세, 밸류에이션, 수급, 공시와 리스크",
        "watch_kpis": ["매출", "영업이익", "마진", "현금흐름", "가이던스"],
        "verification_source": source,
        "updated_at": _utc_now_iso(),
    }


def parse_nasdaq_listed_symbols(text: str, source: str = "nasdaq_trader_nasdaqlisted") -> dict[str, dict]:
    """Parse Nasdaq Trader nasdaqlisted.txt pipe-delimited content."""

    registry: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    for row in reader:
        symbol = _normalize_symbol(row.get("Symbol"))
        name = _safe_text(row.get("Security Name"))
        if not symbol or not name or symbol == "FILE":
            continue
        if _safe_text(row.get("Test Issue")).upper() == "Y":
            continue
        registry[symbol] = _profile(
            symbol=symbol,
            company_name=name,
            exchange="NASDAQ",
            country="US",
            source=source,
            asset_type="etf" if _safe_text(row.get("ETF")).upper() == "Y" else "equity",
        )
    return registry


def parse_nasdaq_other_symbols(text: str, source: str = "nasdaq_trader_otherlisted") -> dict[str, dict]:
    """Parse Nasdaq Trader otherlisted.txt pipe-delimited content."""

    registry: dict[str, dict] = {}
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    for row in reader:
        symbol = _normalize_symbol(row.get("ACT Symbol") or row.get("CQS Symbol"))
        name = _safe_text(row.get("Security Name"))
        if not symbol or not name or symbol == "FILE":
            continue
        if _safe_text(row.get("Test Issue")).upper() == "Y":
            continue
        exchange_code = _safe_text(row.get("Exchange")).upper()
        registry[symbol] = _profile(
            symbol=symbol,
            company_name=name,
            exchange=US_EXCHANGE_LABELS.get(exchange_code, exchange_code or "US"),
            country="US",
            source=source,
            asset_type="etf" if _safe_text(row.get("ETF")).upper() == "Y" else "equity",
        )
    return registry


def parse_kind_krx_list(text: str, source: str = "kind_krx_corp_list") -> dict[str, dict]:
    """Parse KRX/KIND listed-company HTML tables or delimited exports."""

    registry: dict[str, dict] = {}
    soup = BeautifulSoup(text, "html.parser")
    rows: list[list[str]] = []
    for table_row in soup.find_all("tr"):
        cells = [_safe_text(cell.get_text(" ")) for cell in table_row.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        reader = csv.reader(io.StringIO(text))
        rows = [[_safe_text(cell) for cell in row] for row in reader if row]
    if not rows:
        return registry

    headers = [header.lower() for header in rows[0]]
    for row in rows[1:]:
        values = {headers[index]: value for index, value in enumerate(row[: len(headers)])}
        name = (
            values.get("회사명")
            or values.get("종목명")
            or values.get("한글 종목명")
            or values.get("name")
            or ""
        )
        code = (
            values.get("종목코드")
            or values.get("단축코드")
            or values.get("code")
            or values.get("ticker")
            or ""
        )
        symbol = _normalize_kr_code(code)
        company_name = _safe_text(name)
        if not symbol or not company_name:
            continue
        market = (
            values.get("시장구분")
            or values.get("시장")
            or values.get("market")
            or "KRX"
        )
        exchange = "KOSDAQ" if "코스닥" in market.upper() else "KOSPI" if "유가" in market or "코스피" in market.upper() else "KRX"
        registry[symbol] = _profile(
            symbol=symbol,
            company_name=company_name,
            exchange=exchange,
            country="KR",
            source=source,
            sector=values.get("업종") or values.get("업종명") or None,
            industry=values.get("주요제품") or values.get("업종") or None,
        )
    return registry


def source_status_path(vault_dir: Path) -> Path:
    return vault_dir / "_system" / "ticker_registry_source_status.json"


def write_source_status(vault_dir: Path, payload: dict[str, Any]) -> None:
    path = source_status_path(vault_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_source_status(vault_dir: Path) -> dict[str, Any]:
    path = source_status_path(vault_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def fetch_ticker_registry_sources(
    *,
    vault_dir: Path,
    krx_url: str,
    nasdaq_listed_url: str,
    nasdaq_other_url: str,
    timeout_seconds: float,
    user_agent: str,
) -> tuple[dict[str, dict], dict[str, Any]]:
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,text/plain,text/csv,*/*",
    }
    sources = [
        ("krx_kind", krx_url, parse_kind_krx_list),
        ("nasdaq_listed", nasdaq_listed_url, parse_nasdaq_listed_symbols),
        ("nasdaq_other", nasdaq_other_url, parse_nasdaq_other_symbols),
    ]
    registry: dict[str, dict] = {}
    source_results: list[dict[str, Any]] = []
    with httpx.Client(timeout=max(timeout_seconds, 3.0), follow_redirects=True, trust_env=False) as client:
        for source_key, url, parser in sources:
            try:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                if source_key == "krx_kind":
                    response.encoding = response.encoding or "euc-kr"
                parsed = parser(response.text)
                registry.update(parsed)
                source_results.append(
                    {
                        "source": source_key,
                        "status": "success",
                        "url": url,
                        "count": len(parsed),
                        "fetched_at": _utc_now_iso(),
                    }
                )
            except Exception as exc:
                source_results.append(
                    {
                        "source": source_key,
                        "status": "failed",
                        "url": url,
                        "count": 0,
                        "message": str(exc),
                        "fetched_at": _utc_now_iso(),
                    }
                )
    status = {
        "status": "success" if registry else "failed",
        "module": "ticker_registry_source_refresh",
        "updated_at": _utc_now_iso(),
        "source_count": len(sources),
        "success_count": sum(1 for item in source_results if item.get("status") == "success"),
        "entry_count": len(registry),
        "sources": source_results,
    }
    write_source_status(vault_dir, status)
    return registry, status
