from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin

import httpx

from research_os import company_ir_config
from research_os import company_ir_sec


JOBY_IR_PRESS_RELEASES_URL = "https://ir.jobyaviation.com/news-events/press-releases"
PL_IR_PRESS_RELEASES_URL = "https://investors.planet.com/news/default.aspx"
CHPT_IR_PRESS_RELEASES_URL = "https://investors.chargepoint.com/news/default.aspx"
ABSI_IR_PRESS_RELEASES_URL = "https://investors.absci.com/news-and-events/news-releases/"
RXRX_IR_PRESS_RELEASES_URL = "https://ir.recursion.com/news-events/press-releases"
OTLY_IR_PRESS_RELEASES_URL = "https://investors.oatly.com/news-events/press-releases"
CPSH_IR_PRESS_RELEASES_URL = "https://cpstechnologysolutions.com/investor-overview/press-releases/"
GOTU_IR_PRESS_RELEASES_URL = "https://ir.gaotu.cn/home"
KRX_ETF_DETAIL_ENDPOINT = "https://kind.krx.co.kr/disclosure/etfisudetail.do"
ABSI_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001672688.json"
RXRX_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001601830.json"
OTLY_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001843586.json"
CPSH_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000814676.json"
PL_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001836833.json"
CHPT_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001777393.json"
GOTU_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001768259.json"
OPTT_SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0001378140.json"
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


def krx_etf_product_summary_url(ticker: str) -> str:
    """Return the public KRX product-summary URL for one listed ETF.

    KIND uses the six-character KRX ticker without its final check character
    for this endpoint, including non-numeric codes such as ``0117V0``.
    """
    normalized = re.sub(r"\s+", " ", str(ticker or "")).strip().upper()
    if len(normalized) < 2:
        raise ValueError("KRX ETF 종목코드를 확인할 수 없습니다.")
    query = urlencode(
        {
            "method": "searchEtfIsuSummary",
            "strIsurCd": normalized[:-1],
        }
    )
    return f"{KRX_ETF_DETAIL_ENDPOINT}?{query}"


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
    CompanyIrSource(
        source_key="planet_sec_submissions",
        ticker="PL",
        company_name="Planet Labs PBC",
        provider="SEC EDGAR",
        source_url=PL_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="chargepoint_sec_submissions",
        ticker="CHPT",
        company_name="ChargePoint Holdings",
        provider="SEC EDGAR",
        source_url=CHPT_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="gaotu_sec_submissions",
        ticker="GOTU",
        company_name="Gaotu Techedu",
        provider="SEC EDGAR",
        source_url=GOTU_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="ocean_power_sec_submissions",
        ticker="OPTT",
        company_name="Ocean Power Technologies",
        provider="SEC EDGAR",
        source_url=OPTT_SEC_SUBMISSIONS_URL,
        source_scope="sec_company_submissions",
    ),
    CompanyIrSource(
        source_key="krx_tiger_us_sp500_product",
        ticker="360750",
        company_name="TIGER 미국S&P500 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("360750"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_kodex_ai_semiconductor_product",
        ticker="395160",
        company_name="KODEX AI반도체 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("395160"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_tiger_korea_ai_power_product",
        ticker="0117V0",
        company_name="TIGER 코리아AI전력기기TOP3플러스 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("0117V0"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_sol_climate_solution_product",
        ticker="404650",
        company_name="SOL KRX기후변화솔루션 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("404650"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_tiger_china_star50_product",
        ticker="414780",
        company_name="TIGER 차이나과창판STAR50(합성) ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("414780"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_kiwoom_india_nifty50_product",
        ticker="200250",
        company_name="KIWOOM 인도Nifty50(합성) ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("200250"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_tiger_semiconductor_top10_product",
        ticker="396500",
        company_name="TIGER 반도체TOP10",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("396500"),
        source_scope="krx_etf_product",
    ),
    CompanyIrSource(
        source_key="krx_kodex_construction_product",
        ticker="117700",
        company_name="KODEX 건설",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("117700"),
        source_scope="krx_etf_product",
    ),
]


def configured_company_ir_sources(config_json: str | None = None) -> list[CompanyIrSource]:
    return company_ir_config.configured_company_ir_sources(
        COMPANY_IR_SOURCES,
        config_json,
        CompanyIrSource,
    )


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


class _KrxEtfProductParser(HTMLParser):
    """Read the small, public KIND ETF-product form without a browser."""

    def __init__(self) -> None:
        super().__init__()
        self.hidden: dict[str, str] = {}
        self._active_cell: str | None = None
        self._cell_parts: list[str] = []
        self._row_cells: list[tuple[str, str]] = []
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag_name == "input" and attributes.get("type", "").lower() == "hidden":
            name = clean_ir_text(attributes.get("name"))
            value = clean_ir_text(attributes.get("value"))
            if name and value:
                self.hidden[name] = value
        if tag_name in {"th", "td"}:
            self._active_cell = tag_name
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_cell is not None:
            text = clean_ir_text(data)
            if text:
                self._cell_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in {"th", "td"} and self._active_cell == tag_name:
            self._row_cells.append((tag_name, clean_ir_text(" ".join(self._cell_parts))))
            self._active_cell = None
            self._cell_parts = []
        if tag_name == "tr" and self._row_cells:
            for index in range(0, len(self._row_cells) - 1, 2):
                label_kind, label = self._row_cells[index]
                value_kind, value = self._row_cells[index + 1]
                if label_kind == "th" and value_kind == "td" and label and value:
                    self.fields[label] = value
            self._row_cells = []


def _parse_krx_etf_product_page(html: str) -> tuple[dict[str, str], dict[str, str]]:
    parser = _KrxEtfProductParser()
    parser.feed(html or "")
    parser.close()
    return parser.hidden, parser.fields


def _krx_etf_detail_url(*, isu_code: str, is_synthetic: str) -> str:
    query = urlencode(
        {
            "method": "searchEftIsuDetail",
            "isuCd": isu_code,
            "menuIndex": "0",
            "isSynthEtf": is_synthetic or "N",
        }
    )
    return f"{KRX_ETF_DETAIL_ENDPOINT}?{query}"


def fetch_krx_etf_product_source(
    source: CompanyIrSource,
    *,
    client: httpx.Client,
) -> dict:
    """Fetch one public KRX ETF product page and verify its ticker binding.

    KIND's landing page supplies the ISIN needed for its product-detail GET.
    The saved evidence is explicitly labelled as a daily observed product
    snapshot; it is not treated as an issuer earnings release.
    """
    landing_response = client.get(source.source_url)
    landing_response.raise_for_status()
    hidden, _ = _parse_krx_etf_product_page(landing_response.text)
    isu_code = clean_ir_text(hidden.get("isuCd"))
    if not isu_code:
        raise RuntimeError("KRX ETF 상품의 표준코드를 찾지 못했습니다.")
    detail_url = _krx_etf_detail_url(
        isu_code=isu_code,
        is_synthetic=clean_ir_text(hidden.get("isSynthEtf")) or "N",
    )
    detail_response = client.get(detail_url)
    detail_response.raise_for_status()
    _, fields = _parse_krx_etf_product_page(detail_response.text)
    returned_ticker = clean_ir_text(fields.get("종목코드")).upper()
    expected_ticker = clean_ir_text(source.ticker).upper()
    if returned_ticker != expected_ticker:
        raise RuntimeError(
            f"KRX ETF 상품코드 불일치: 기대값 {expected_ticker}, 반환값 {returned_ticker or '없음'}"
        )
    index_name = clean_ir_text(fields.get("기초지수명"))
    title = f"{source.company_name} KRX 공식 ETF 상품개요"
    if index_name:
        title = f"{title} · {index_name}"
    observed_at = datetime.now().date().isoformat()
    item = CompanyIrItem(
        item_id=company_ir_item_id(source, title, observed_at, detail_url),
        ticker=expected_ticker,
        company_name=source.company_name,
        title=title,
        source_provider=source.provider,
        source_scope=source.source_scope,
        published_at=observed_at,
        detail_url=detail_url,
        source_url=source.source_url,
        category="KRX 공식 ETF 상품개요(일일 확인)",
        filing_form="ETF 상품개요",
        filing_group="fund_structure",
    )
    return {
        "source_key": source.source_key,
        "provider": source.provider,
        "source_url": source.source_url,
        "ticker": source.ticker,
        "company_name": source.company_name,
        "source_scope": source.source_scope,
        "status": "success",
        "items": [asdict(item)],
    }


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


def classify_sec_filing(form: str, description: str = "") -> tuple[str, str]:
    return company_ir_sec.classify_sec_filing(form, description)


def parse_sec_company_submissions(
    payload: dict | str,
    *,
    source: CompanyIrSource,
    limit: int = 30,
) -> list[dict]:
    return company_ir_sec.parse_sec_company_submissions(
        payload,
        source=source,
        item_factory=CompanyIrItem,
        item_id_factory=company_ir_item_id,
        normalize_date=normalize_ir_date,
        limit=limit,
    )


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
    with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False, headers=headers) as client:
        if source.source_scope == "krx_etf_product":
            return fetch_krx_etf_product_source(source, client=client)
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
            source_summary = {key: value for key, value in result.items() if key != "items"}
            source_summary["item_count"] = len(result.get("items") or [])
            source_results.append(source_summary)
            all_items.extend(result.get("items") or [])
        except Exception as exc:
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
    successful_sec_sources = {
        str(result.get("ticker") or "").upper(): result
        for result in source_results
        if result.get("status") == "success"
        and result.get("source_scope") == "sec_company_submissions"
    }
    for result in source_results:
        if result.get("status") != "failed":
            continue
        ticker = str(result.get("ticker") or "").upper()
        fallback = successful_sec_sources.get(ticker)
        if fallback and result.get("source_scope") != "sec_company_submissions":
            result["primary_status"] = "failed"
            result["status"] = "fallback_success"
            result["fallback_status"] = "success"
            result["fallback_source_key"] = fallback.get("source_key")
            result["fallback_provider"] = fallback.get("provider") or "SEC EDGAR"
            result["fallback_source_scope"] = fallback.get("source_scope") or "sec_company_submissions"
            result["fallback_source_url"] = fallback.get("source_url")
            result["fallback_item_count"] = int(fallback.get("item_count") or 0)
            continue
        warnings.append(
            f"{result.get('provider') or '회사 IR'} 목록 확인 실패: {result.get('error') or '알 수 없는 오류'}"
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
