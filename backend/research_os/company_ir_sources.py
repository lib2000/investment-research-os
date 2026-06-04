from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx


JOBY_IR_PRESS_RELEASES_URL = "https://ir.jobyaviation.com/news-events/press-releases"
PL_IR_PRESS_RELEASES_URL = "https://investors.planet.com/news/default.aspx"
CHPT_IR_PRESS_RELEASES_URL = "https://investors.chargepoint.com/news/default.aspx"
ABSI_IR_PRESS_RELEASES_URL = "https://investors.absci.com/news-and-events/news-releases/"
RXRX_IR_PRESS_RELEASES_URL = "https://ir.recursion.com/news-events/press-releases"
OTLY_IR_PRESS_RELEASES_URL = "https://investors.oatly.com/news-events/press-releases"
CPSH_IR_PRESS_RELEASES_URL = "https://cpstechnologysolutions.com/investor-overview/press-releases/"
GOTU_IR_PRESS_RELEASES_URL = "https://ir.gaotu.cn/home"
ABSI_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001672688.json"
RXRX_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001601830.json"
OTLY_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001843586.json"
CPSH_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000814676.json"
SEC_INTERESTING_FORMS = {"8-K", "10-Q", "10-K", "20-F", "6-K", "SD", "SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A"}
DATE_PATTERN = re.compile(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}|20\d{2}[-./]\d{1,2}[-./]\d{1,2}", re.IGNORECASE)
SKIP_LINK_TEXTS = {
    "",
    "home",
    "news & events",
    "press releases",
    "email alerts",
    "contacts",
    "investors",
    "overview",
    "financials",
    "sec filings",
    "governance",
    "stock information",
    "events & presentations",
    "to chargepoint.com",
    "chevron_left back to jobyaviation.com",
}


@dataclass
class CompanyIrSource:
    source_key: str
    ticker: str
    company_name: str
    provider: str
    source_url: str
    source_scope: str = "company_ir_press_releases"


@dataclass
class CompanyIrItem:
    item_id: str
    ticker: str
    company_name: str
    title: str
    source_provider: str
    source_scope: str
    published_at: str
    detail_url: str
    source_url: str
    category: str = "IR 보도자료"
    filing_form: str = ""
    filing_group: str = ""


COMPANY_IR_SOURCES = [
    CompanyIrSource(
        source_key="joby_ir_press_releases",
        ticker="JOBY",
        company_name="Joby Aviation",
        provider="Joby Aviation IR",
        source_url=JOBY_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="planet_ir_press_releases",
        ticker="PL",
        company_name="Planet Labs PBC",
        provider="Planet Labs IR",
        source_url=PL_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="chargepoint_ir_press_releases",
        ticker="CHPT",
        company_name="ChargePoint Holdings",
        provider="ChargePoint IR",
        source_url=CHPT_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="absci_ir_press_releases",
        ticker="ABSI",
        company_name="Absci Corporation",
        provider="Absci IR",
        source_url=ABSI_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="recursion_ir_press_releases",
        ticker="RXRX",
        company_name="Recursion Pharmaceuticals",
        provider="Recursion IR",
        source_url=RXRX_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="oatly_ir_press_releases",
        ticker="OTLY",
        company_name="Oatly Group",
        provider="Oatly IR",
        source_url=OTLY_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="cpsh_ir_press_releases",
        ticker="CPSH",
        company_name="CPS Technologies",
        provider="CPS Technologies IR",
        source_url=CPSH_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="gaotu_ir_press_releases",
        ticker="GOTU",
        company_name="Gaotu Techedu",
        provider="Gaotu IR",
        source_url=GOTU_IR_PRESS_RELEASES_URL,
    ),
    CompanyIrSource(
        source_key="absci_sec_submissions",
        ticker="ABSI",
        company_name="Absci Corporation",
        provider="SEC EDGAR",
        source_url=ABSI_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="recursion_sec_submissions",
        ticker="RXRX",
        company_name="Recursion Pharmaceuticals",
        provider="SEC EDGAR",
        source_url=RXRX_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="oatly_sec_submissions",
        ticker="OTLY",
        company_name="Oatly Group",
        provider="SEC EDGAR",
        source_url=OTLY_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="cpsh_sec_submissions",
        ticker="CPSH",
        company_name="CPS Technologies",
        provider="SEC EDGAR",
        source_url=CPSH_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
]


def _source_from_mapping(item: dict, index: int) -> CompanyIrSource | None:
    source_url = clean_ir_text(item.get("source_url") or item.get("url"))
    ticker = clean_ir_text(item.get("ticker") or item.get("target_key")).upper()
    company_name = clean_ir_text(item.get("company_name") or item.get("company") or ticker)
    if not source_url or not ticker or not source_url.startswith(("http://", "https://")):
        return None
    source_key = clean_ir_text(item.get("source_key") or item.get("key"))
    if not source_key:
        source_key = re.sub(r"[^a-z0-9_]+", "_", f"{ticker.lower()}_ir_{index}").strip("_")
    provider = clean_ir_text(item.get("provider") or f"{company_name} IR")
    source_scope = clean_ir_text(item.get("source_scope") or "company_ir_press_releases")
    return CompanyIrSource(
        source_key=source_key,
        ticker=ticker,
        company_name=company_name,
        provider=provider,
        source_url=source_url,
        source_scope=source_scope,
    )


def configured_company_ir_sources(config_json: str | None = None) -> list[CompanyIrSource]:
    sources = list(COMPANY_IR_SOURCES)
    text = clean_ir_text(config_json)
    if not text:
        return sources
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return sources
    if isinstance(payload, dict):
        payload = payload.get("sources") or []
    if not isinstance(payload, list):
        return sources
    seen = {(source.ticker, source.source_url) for source in sources}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        source = _source_from_mapping(item, index)
        if not source or (source.ticker, source.source_url) in seen:
            continue
        seen.add((source.ticker, source.source_url))
        sources.append(source)
    return sources


class _CompanyIrParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[dict] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_dict = {key.lower(): value or "" for key, value in attrs}
            self._href = attrs_dict.get("href") or ""
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = clean_ir_text(" ".join(self._link_text))
            if text:
                self.tokens.append({"type": "link", "text": text, "href": self._href})
            self._href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = clean_ir_text(data)
        if not text:
            return
        if self._href is not None:
            self._link_text.append(text)
        else:
            self.tokens.append({"type": "text", "text": text})


def clean_ir_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def company_ir_item_id(source: CompanyIrSource, title: str, published_at: str, detail_url: str) -> str:
    payload = "\n".join([source.source_key, source.ticker, title.strip(), published_at.strip(), detail_url.strip()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_ir_date(value: str | None) -> str:
    text = clean_ir_text(value)
    match = DATE_PATTERN.search(text)
    if not match:
        return ""
    raw = match.group(0)
    if re.match(r"20\d{2}[-./]", raw):
        parts = re.split(r"[-./]", raw)
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _looks_like_press_release(title: str, href: str, source: CompanyIrSource | None = None) -> bool:
    cleaned = clean_ir_text(title)
    lowered = cleaned.lower()
    href_lower = clean_ir_text(href).lower()
    if lowered in SKIP_LINK_TEXTS or len(cleaned) < 12:
        return False
    if href_lower.startswith("#") or href_lower.startswith("javascript") or href_lower.startswith("mailto:"):
        return False
    detail_markers = [
        "/press-releases/detail/",
        "news-events/press-releases/detail",
        "/news/news-details/",
        "/news-releases/news-release-details/",
        "/news-and-events/news-releases/",
        "/investor-overview/press-releases/",
    ]
    if any(part in href_lower for part in detail_markers):
        return True
    generic_href_markers = [
        "/events",
        "/financials",
        "/quarterly-results",
        "/investor-faq",
        "/sec-filings",
        "/stock",
        "/governance",
        "/overview",
        "/contact",
        "/email-alert",
        "/presentations",
    ]
    if any(part in href_lower for part in generic_href_markers):
        return False
    likely_detail_markers = [
        "/news/",
        "/press/",
        "/release/",
        "/releases/",
        "/202",
        "detail",
    ]
    if not any(part in href_lower for part in likely_detail_markers):
        return False
    signal_keywords = [
        "reports",
        "announces",
        "financial results",
        "quarter",
        "fiscal",
        "earnings",
        "investor",
        "conference",
        "business update",
        "press release",
        "webcast",
    ]
    return any(keyword in lowered for keyword in signal_keywords)


def _nearby_text(tokens: list[dict], index: int, *, before: int = 4, after: int = 10) -> list[str]:
    start = max(0, index - before)
    end = min(len(tokens), index + after + 1)
    return [clean_ir_text(item.get("text")) for item in tokens[start:end] if clean_ir_text(item.get("text"))]


def _date_from_nearby_text(tokens: list[dict], index: int) -> str:
    for text in _nearby_text(tokens, index):
        date_value = normalize_ir_date(text)
        if date_value:
            return date_value
    return ""


def _sec_cik_from_submissions_url(url: str) -> str:
    match = re.search(r"CIK0*(\d+)\.json", url or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _sec_archive_url(source: CompanyIrSource, accession_number: str, primary_document: str) -> str:
    cik = _sec_cik_from_submissions_url(source.source_url)
    accession = re.sub(r"[^0-9]", "", accession_number or "")
    document = clean_ir_text(primary_document)
    if not cik or not accession or not document:
        return source.source_url
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"


def classify_sec_filing(form: str, description: str = "") -> tuple[str, str]:
    form_key = clean_ir_text(form).upper()
    description_key = clean_ir_text(description).lower()
    if form_key in {"10-Q", "10-K", "20-F"}:
        return "SEC 실적 공시", "financial_report"
    if form_key == "8-K" and any(
        keyword in description_key
        for keyword in ["financial result", "earnings", "press release", "exhibit 99.1", "results"]
    ):
        return "SEC 실적/보도자료", "financial_release"
    if form_key in {"SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A"}:
        return "SEC 지분 공시", "ownership_filing"
    if form_key == "6-K":
        return "SEC 해외발행사 공시", "foreign_issuer_filing"
    if form_key == "SD":
        return "SEC 공급망/지속가능 공시", "specialized_disclosure"
    return "SEC 중요 공시", "material_filing"


def parse_sec_company_submissions(
    payload: dict | str,
    *,
    source: CompanyIrSource,
    limit: int = 30,
) -> list[dict]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict):
        return []
    recent = ((payload.get("filings") or {}).get("recent") or {}) if isinstance(payload.get("filings"), dict) else {}
    forms = list(recent.get("form") or [])
    filing_dates = list(recent.get("filingDate") or [])
    report_dates = list(recent.get("reportDate") or [])
    accessions = list(recent.get("accessionNumber") or [])
    documents = list(recent.get("primaryDocument") or [])
    descriptions = list(recent.get("primaryDocDescription") or [])
    items: list[CompanyIrItem] = []
    seen: set[str] = set()
    for index, form_value in enumerate(forms):
        form = clean_ir_text(form_value).upper()
        if form not in SEC_INTERESTING_FORMS:
            continue
        filing_date = clean_ir_text(filing_dates[index] if index < len(filing_dates) else "")
        report_date = clean_ir_text(report_dates[index] if index < len(report_dates) else "")
        accession = clean_ir_text(accessions[index] if index < len(accessions) else "")
        document = clean_ir_text(documents[index] if index < len(documents) else "")
        description = clean_ir_text(descriptions[index] if index < len(descriptions) else "")
        title_detail = description if description and description.upper() != form else "SEC filing"
        title = f"{source.company_name} {form} {title_detail}"
        filing_category, filing_group = classify_sec_filing(form, title_detail)
        detail_url = _sec_archive_url(source, accession, document)
        published_at = normalize_ir_date(filing_date) or filing_date or normalize_ir_date(report_date) or report_date
        item_id = company_ir_item_id(source, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            CompanyIrItem(
                item_id=item_id,
                ticker=source.ticker,
                company_name=source.company_name,
                title=title,
                source_provider=source.provider,
                source_scope=source.source_scope,
                published_at=published_at,
                detail_url=detail_url,
                source_url=source.source_url,
                category=filing_category,
                filing_form=form,
                filing_group=filing_group,
            )
        )
        if len(items) >= max(1, limit):
            break
    return [asdict(item) for item in items]


def parse_company_ir_press_releases(
    html: str,
    *,
    source: CompanyIrSource,
    limit: int = 30,
) -> list[dict]:
    parser = _CompanyIrParser()
    parser.feed(html or "")
    items: list[CompanyIrItem] = []
    seen: set[str] = set()
    for index, token in enumerate(parser.tokens):
        if token.get("type") != "link":
            continue
        title = clean_ir_text(token.get("text"))
        href = clean_ir_text(token.get("href"))
        if not _looks_like_press_release(title, href, source):
            continue
        detail_url = urljoin(source.source_url, href)
        published_at = _date_from_nearby_text(parser.tokens, index)
        item_id = company_ir_item_id(source, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            CompanyIrItem(
                item_id=item_id,
                ticker=source.ticker,
                company_name=source.company_name,
                title=title,
                source_provider=source.provider,
                source_scope=source.source_scope,
                published_at=published_at,
                detail_url=detail_url,
                source_url=source.source_url,
            )
        )
        if len(items) >= max(1, limit):
            break
    return [asdict(item) for item in items]


def fetch_company_ir_source(
    source: CompanyIrSource,
    *,
    limit: int = 30,
    timeout: float = 10.0,
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
) -> dict:
    headers = {"User-Agent": user_agent, "Referer": source.source_url}
    with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
        response = client.get(source.source_url, headers=headers)
        response.raise_for_status()
        if source.source_scope == "sec_company_submissions" or "data.sec.gov/submissions/" in source.source_url:
            items = parse_sec_company_submissions(response.text, source=source, limit=limit)
        else:
            items = parse_company_ir_press_releases(response.text, source=source, limit=limit)
        return {
            "source_key": source.source_key,
            "provider": source.provider,
            "source_url": source.source_url,
            "ticker": source.ticker,
            "company_name": source.company_name,
            "source_scope": source.source_scope,
            "status": "success",
            "items": items,
        }


def fetch_company_ir_sources(
    *,
    limit: int = 30,
    timeout: float = 10.0,
    user_agent: str | None = None,
    sources: list[CompanyIrSource] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    all_items: list[dict] = []
    warnings: list[str] = []
    source_results: list[dict] = []
    for source in (sources or COMPANY_IR_SOURCES):
        try:
            result = fetch_company_ir_source(
                source,
                limit=limit,
                timeout=timeout,
                user_agent=user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            )
            source_results.append({key: value for key, value in result.items() if key != "items"})
            all_items.extend(result.get("items") or [])
        except Exception as exc:
            warnings.append(f"{source.provider} 목록 확인 실패: {exc}")
            source_results.append(
                {
                    "source_key": source.source_key,
                    "provider": source.provider,
                    "source_url": source.source_url,
                    "ticker": source.ticker,
                    "company_name": source.company_name,
                    "source_scope": source.source_scope,
                    "status": "failed",
                    "error": str(exc),
                }
            )
    deduped = {str(item.get("item_id")): item for item in all_items if item.get("item_id")}
    items = sorted(deduped.values(), key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return items[: max(1, limit)], warnings, source_results


def should_refresh_company_ir_cache(cache: dict | None, *, refresh_hours: float = 24.0) -> bool:
    if not isinstance(cache, dict) or not cache.get("updated_at"):
        return True
    try:
        updated_at = datetime.fromisoformat(str(cache.get("updated_at")).replace("Z", "+00:00"))
    except ValueError:
        return True
    if updated_at.tzinfo is not None:
        updated_at = updated_at.replace(tzinfo=None)
    return datetime.now() - updated_at >= timedelta(hours=max(float(refresh_hours or 24), 1.0))


def company_ir_copyright_policy() -> str:
    return "상장사 공개 IR/보도자료 URL과 핵심 메타데이터를 수집하고, 보유/관심 종목과 연결되는 공개 본문만 RAG 근거로 저장합니다."
