from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin


KCIF_REPORT_LIST_URL = "https://www.kcif.or.kr/annual/reportList"

_DATE_PATTERN = re.compile(r"20\d{2}\.\d{2}\.\d{2}")
_SKIP_LINK_TEXTS = {
    "",
    "LOGIN",
    "고객지원",
    "ENG",
    "검색",
    "HOME",
    "URL 복사",
    "미리보기",
    "다운로드",
    "프린트",
    "크게보기",
    "작게보기",
    "저작권 정책",
    "이메일주소무단수집 거부",
    "개인정보처리방침",
}
_CATEGORY_HINTS = {
    "국제금융속보",
    "주간보고서",
    "월간보고서",
    "특별일보",
    "영상보고서",
    "외환",
    "채권",
    "주식",
    "자본유출입",
    "원자재",
    "은행",
    "미국",
    "중국",
    "유럽",
    "일본",
    "신흥국",
    "글로벌",
    "해외시각",
}


@dataclass
class KcifReportMeta:
    report_id: str
    title: str
    category: str
    published_at: str
    author: str
    detail_url: str
    file_name: str | None = None
    source: str = "KCIF"
    source_url: str = KCIF_REPORT_LIST_URL


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


class _KcifListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[dict] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_dict = {key.lower(): value or "" for key, value in attrs}
            self._link_href = attrs_dict.get("href") or ""
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._link_href is not None:
            text = clean_text(" ".join(self._link_text))
            if text:
                self.tokens.append({"type": "link", "text": text, "href": self._link_href})
            self._link_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = clean_text(data)
        if not text:
            return
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self.tokens.append({"type": "text", "text": text})


def _report_id(title: str, published_at: str, detail_url: str) -> str:
    payload = "\n".join([title.strip(), published_at.strip(), detail_url.strip()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def keyword_in_text(keyword: str, text: str) -> bool:
    cleaned = clean_text(keyword).lower()
    if not cleaned:
        return False
    if re.fullmatch(r"[a-z0-9]{1,4}", cleaned):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(cleaned)}(?![a-z0-9])", text))
    return cleaned in text


def _nearby_text(tokens: list[dict], index: int, *, before: int = 8, after: int = 18) -> list[str]:
    start = max(0, index - before)
    end = min(len(tokens), index + after + 1)
    return [clean_text(item.get("text")) for item in tokens[start:end] if clean_text(item.get("text"))]


def _infer_category(tokens: list[dict], index: int, title: str) -> str:
    candidates = _nearby_text(tokens, index, before=10, after=3)
    title_text = title.lower()
    for text in reversed(candidates):
        if _DATE_PATTERN.search(text) or "조회수" in text or text.lower().endswith(".pdf"):
            continue
        if text == title:
            continue
        for hint in _CATEGORY_HINTS:
            if hint in text:
                return text[:80]
    for hint in _CATEGORY_HINTS:
        if hint.lower() in title_text:
            return hint
    return "KCIF 보고서"


def _infer_date_and_author(tokens: list[dict], index: int) -> tuple[str, str]:
    candidates = _nearby_text(tokens, index, before=0, after=20)
    for pos, text in enumerate(candidates):
        match = _DATE_PATTERN.search(text)
        if match:
            author_parts = []
            for prior in candidates[max(0, pos - 3) : pos]:
                if prior in _SKIP_LINK_TEXTS or "조회수" in prior or _DATE_PATTERN.search(prior):
                    continue
                if prior.endswith(".pdf"):
                    continue
                author_parts.append(prior)
            return match.group(0), ", ".join(author_parts[-2:])[:80]
    return "", ""


def _infer_file_name(tokens: list[dict], index: int) -> str | None:
    for text in _nearby_text(tokens, index, before=0, after=24):
        if text.lower().endswith(".pdf"):
            return text[:160]
    return None


def parse_kcif_report_list(html: str, *, base_url: str = KCIF_REPORT_LIST_URL, limit: int = 30) -> list[dict]:
    parser = _KcifListParser()
    parser.feed(html or "")
    reports: list[KcifReportMeta] = []
    seen: set[str] = set()
    for index, token in enumerate(parser.tokens):
        if token.get("type") != "link":
            continue
        title = clean_text(token.get("text"))
        if title in _SKIP_LINK_TEXTS or title.startswith("#") or len(title) < 8:
            continue
        href = str(token.get("href") or "")
        if title.lower().endswith((".pdf", ".zip")) or href.startswith("javascript"):
            continue
        published_at, author = _infer_date_and_author(parser.tokens, index)
        if not published_at:
            continue
        detail_url = urljoin(base_url, href)
        report_id = _report_id(title, published_at, detail_url)
        if report_id in seen:
            continue
        seen.add(report_id)
        reports.append(
            KcifReportMeta(
                report_id=report_id,
                title=title,
                category=_infer_category(parser.tokens, index, title),
                published_at=published_at,
                author=author,
                detail_url=detail_url,
                file_name=_infer_file_name(parser.tokens, index),
            )
        )
        if len(reports) >= max(1, limit):
            break
    return [asdict(report) for report in reports]
