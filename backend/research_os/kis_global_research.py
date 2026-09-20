"""Copyright-safe ingestion helpers for Korea Investment Securities global research.

The source page is a public listing, but individual reports may require a KIS
login and are protected by the publisher's copyright notice.  This module only
reads the listing metadata needed to identify a report.  It deliberately does
not collect descriptions, full text, PDFs, or authenticated detail pages.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any

import httpx


KIS_GLOBAL_RESEARCH_DEFAULT_LIST_URL = (
    "https://securities.koreainvestment.com/main/research/research/Strategy.jsp?jkGubun=7"
)


def clean_kis_global_research_text(value: Any) -> str:
    """Normalize public listing metadata without retaining source body text."""

    text = unescape(str(value or ""))
    text = text.replace("\u200b", "").replace("\ufeff", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_kis_global_research_date(value: Any) -> str | None:
    text = clean_kis_global_research_text(value)
    match = re.search(r"(?<!\d)(20\d{2})[./-](\d{1,2})[./-](\d{1,2})(?!\d)", text)
    if not match:
        return None
    year, month, day = match.groups()
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return None


def _listing_item_id(*, category: str, title: str, published_at: str | None) -> str:
    fingerprint = "|".join(
        [
            clean_kis_global_research_text(category),
            clean_kis_global_research_text(title),
            clean_kis_global_research_text(published_at),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]


def _class_tokens(attrs: list[tuple[str, str | None]]) -> set[str]:
    return {
        token.strip().lower()
        for name, value in attrs
        if name.lower() == "class"
        for token in str(value or "").split()
        if token.strip()
    }


def _attribute(attrs: list[tuple[str, str | None]], name: str) -> str:
    lowered_name = name.lower()
    for key, value in attrs:
        if key.lower() == lowered_name:
            return str(value or "")
    return ""


class _KisGlobalResearchListingParser(HTMLParser):
    """Extract only title/category/date/byline from public KIS listing rows."""

    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.items: list[dict[str, str | None]] = []
        self._stack: list[tuple[str, set[str]]] = []
        self._listing_depths: list[int] = []
        self._row: dict[str, str] | None = None
        self._row_depth: int | None = None
        self._active_field: str | None = None
        self._active_depth: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        class_tokens = _class_tokens(attrs)
        self._stack.append((tag.lower(), class_tokens))
        depth = len(self._stack)

        if tag.lower() == "ul" and {"view_area", "line"}.issubset(class_tokens):
            self._listing_depths.append(depth)
            return

        if (
            tag.lower() == "li"
            and self._listing_depths
            and depth == self._listing_depths[-1] + 1
        ):
            self._row = {"category": "", "title": "", "byline": ""}
            self._row_depth = depth
            self._active_field = None
            self._active_depth = None
            return

        if self._row is None:
            return
        if {"head", "blue"}.issubset(class_tokens):
            self._active_field = "category"
            self._active_depth = depth
        elif "body_tit" in class_tokens:
            self._active_field = "title"
            self._active_depth = depth
        elif "tit_info" in class_tokens:
            self._active_field = "byline"
            self._active_depth = depth

        # `body_sub` is intentionally not selected.  It can contain publisher
        # commentary; retaining it would exceed this listing-metadata scope.
        _ = _attribute(attrs, "onclick")

    def handle_data(self, data: str) -> None:
        if self._row is None or self._active_field is None:
            return
        self._row[self._active_field] = (
            f"{self._row.get(self._active_field, '')} {data}"
        ).strip()

    def handle_endtag(self, tag: str) -> None:
        depth = len(self._stack)
        normalized_tag = tag.lower()
        if self._row is not None and self._row_depth == depth and normalized_tag == "li":
            category = clean_kis_global_research_text(self._row.get("category"))
            title = clean_kis_global_research_text(self._row.get("title"))
            byline = clean_kis_global_research_text(self._row.get("byline"))
            if title:
                published_at = normalize_kis_global_research_date(byline)
                author = clean_kis_global_research_text(
                    re.sub(r"(?<!\d)20\d{2}[./-]\d{1,2}[./-]\d{1,2}(?!\d)", " ", byline)
                )
                item = {
                    "item_id": _listing_item_id(
                        category=category,
                        title=title,
                        published_at=published_at,
                    ),
                    "title": title,
                    "category": category or "독점 글로벌 리서치",
                    "author": author or None,
                    "published_at": published_at,
                    "source": "korea_investment_securities",
                    "source_url": self.source_url,
                    "access_scope": "listing_metadata_only",
                }
                self.items.append(item)
            self._row = None
            self._row_depth = None
            self._active_field = None
            self._active_depth = None
        elif self._active_depth == depth:
            self._active_field = None
            self._active_depth = None

        if self._listing_depths and self._listing_depths[-1] == depth and normalized_tag == "ul":
            self._listing_depths.pop()
        if self._stack:
            self._stack.pop()


def parse_kis_global_research_listing_html(
    html: str,
    *,
    source_url: str = KIS_GLOBAL_RESEARCH_DEFAULT_LIST_URL,
    limit: int | None = None,
) -> list[dict[str, str | None]]:
    """Return de-duplicated public listing metadata in page order.

    The parser intentionally has no fallback that scans arbitrary page text:
    that prevents accidental capture of report snippets or unrelated content.
    """

    parser = _KisGlobalResearchListingParser(source_url)
    parser.feed(html)
    parser.close()
    seen: set[str] = set()
    items: list[dict[str, str | None]] = []
    for item in parser.items:
        item_id = str(item.get("item_id") or "")
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        items.append(item)
        if limit is not None and len(items) >= max(1, int(limit)):
            break
    return items


def fetch_kis_global_research_items(
    *,
    list_url: str = KIS_GLOBAL_RESEARCH_DEFAULT_LIST_URL,
    timeout_seconds: float = 12.0,
    user_agent: str,
    limit: int = 10,
) -> tuple[list[dict[str, str | None]], list[str]]:
    """Fetch only the public listing page; no login or report-file request."""

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5",
    }
    with httpx.Client(
        timeout=max(float(timeout_seconds), 1.0),
        follow_redirects=True,
    ) as client:
        response = client.get(list_url, headers=headers)
        response.raise_for_status()
        # The page declares UTF-8 in HTML but does not reliably advertise it
        # in the response header, so httpx may otherwise decode Korean titles
        # as ISO-8859-1 on some runs.
        response.encoding = "utf-8"
    items = parse_kis_global_research_listing_html(
        response.text,
        source_url=list_url,
        limit=max(1, int(limit)),
    )
    warnings: list[str] = []
    if not items:
        warnings.append(
            "한국투자증권 공개 목록에서 리서치 메타데이터를 찾지 못했습니다. "
            "페이지 구조 또는 공개 범위를 확인하세요."
        )
    return items, warnings


def should_refresh_kis_global_research_cache(
    cache: dict[str, Any] | None,
    *,
    refresh_hours: float = 24.0,
    now: datetime | None = None,
) -> bool:
    if not isinstance(cache, dict):
        return True
    raw_updated_at = str(cache.get("updated_at") or "").strip()
    if not raw_updated_at:
        return True
    try:
        updated_at = datetime.fromisoformat(raw_updated_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    comparison_now = now or datetime.now(timezone.utc)
    if comparison_now.tzinfo is None:
        comparison_now = comparison_now.replace(tzinfo=timezone.utc)
    return comparison_now.astimezone(timezone.utc) - updated_at.astimezone(timezone.utc) >= timedelta(
        hours=max(float(refresh_hours), 1.0)
    )


def kis_global_research_copyright_policy() -> dict[str, Any]:
    """Machine-readable storage boundary shown in status/UI APIs."""

    return {
        "mode": "listing_metadata_and_derived_signals_only",
        "full_text_stored": False,
        "pdf_auto_downloaded": False,
        "login_bypass": False,
        "allowed_fields": [
            "title",
            "category",
            "author",
            "published_at",
            "source_url",
            "local_classification",
        ],
        "source_url": KIS_GLOBAL_RESEARCH_DEFAULT_LIST_URL,
    }
