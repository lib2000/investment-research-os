from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin

import httpx


EMERICS_BUSINESS_URL = "https://www.emerics.org:446/business.es?mid=a10400000000&systemcode=05"
CSF_BUSINESS_URL = "https://csf.kiep.go.kr/consultingInfo.es?mid=a20400000000"
KIEP_REPORTS_URL = (
    "https://www.kiep.go.kr/gallery.es?"
    "mid=a10101010000&bid=0001&cg_code=C03%2CC05%2CC02%2CC13%2CC01%2CC19%2CC17%2CC11%2CC20"
)

DATE_PATTERN = re.compile(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}")
GENERIC_TARGET_KEYWORDS = {
    "ai",
    "kr",
    "korea",
    "etf",
    "미국",
    "한국",
    "중국",
    "플랫폼",
    "성장",
    "기술",
}
SKIP_LINK_TEXTS = {
    "",
    "HOME",
    "검색",
    "URL 복사",
    "닫기",
    "인쇄",
    "첫페이지",
    "이전페이지",
    "다음페이지",
    "마지막페이지",
    "페이스북",
    "트위터",
    "카카오톡",
    "뉴스레터 구독신청",
    "소개",
    "사이트맵",
    "이용안내",
    "공지사항",
    "개인정보처리방침",
    "이메일무단수집거부",
}


@dataclass
class RegionalBusinessSource:
    source_key: str
    provider: str
    source_url: str
    source_scope: str


@dataclass
class RegionalBusinessItem:
    item_id: str
    title: str
    source_provider: str
    source_scope: str
    agency: str
    published_at: str
    detail_url: str
    source_url: str
    category: str = "비즈니스 정보"


REGIONAL_BUSINESS_SOURCES = [
    RegionalBusinessSource(
        source_key="emerics_middle_east_business",
        provider="EMERiCs",
        source_url=EMERICS_BUSINESS_URL,
        source_scope="신흥지역 비즈니스 정보",
    ),
    RegionalBusinessSource(
        source_key="csf_china_business",
        provider="CSF",
        source_url=CSF_BUSINESS_URL,
        source_scope="중국 비즈니스 정보",
    ),
    RegionalBusinessSource(
        source_key="kiep_macro_reports",
        provider="KIEP",
        source_url=KIEP_REPORTS_URL,
        source_scope="대외경제정책연구원 전체보고서",
    ),
]


class _LinkTextParser(HTMLParser):
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
            text = clean_regional_text(" ".join(self._link_text))
            if text:
                self.tokens.append({"type": "link", "text": text, "href": self._link_href})
            self._link_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = clean_regional_text(data)
        if not text:
            return
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self.tokens.append({"type": "text", "text": text})


def clean_regional_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def regional_item_id(provider: str, title: str, published_at: str, detail_url: str) -> str:
    payload = "\n".join([provider, title.strip(), published_at.strip(), detail_url.strip()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_regional_date(value: str | None) -> str:
    match = DATE_PATTERN.search(clean_regional_text(value))
    if not match:
        return ""
    parts = re.split(r"[-./]", match.group(0))
    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"


def _nearby_text(tokens: list[dict], index: int, *, before: int = 4, after: int = 8) -> list[str]:
    start = max(0, index - before)
    end = min(len(tokens), index + after + 1)
    return [clean_regional_text(item.get("text")) for item in tokens[start:end] if clean_regional_text(item.get("text"))]


def _looks_like_list_title(title: str, href: str) -> bool:
    if title in SKIP_LINK_TEXTS or title.isdigit() or len(title) < 8:
        return False
    lowered = title.lower()
    if lowered.endswith((".pdf", ".zip", ".hwp", ".docx")):
        return False
    if href.startswith("#") or href.startswith("javascript"):
        return False
    if "sns" in lowered or "quick" in lowered:
        return False
    return True


def _infer_date_and_agency(tokens: list[dict], index: int, title: str) -> tuple[str, str]:
    candidates = _nearby_text(tokens, index, before=2, after=10)
    published_at = ""
    agency_candidates: list[str] = []
    for text in candidates:
        date_value = normalize_regional_date(text)
        if date_value and not published_at:
            published_at = date_value
            continue
        if text == title or text in SKIP_LINK_TEXTS or text.isdigit():
            continue
        if len(text) > 80 or "전체(" in text or "지역선택" in text:
            continue
        if not DATE_PATTERN.search(text):
            agency_candidates.append(text)
    agency = agency_candidates[-1] if agency_candidates else ""
    return published_at, agency


def parse_regional_business_list(
    html: str,
    *,
    source: RegionalBusinessSource,
    limit: int = 30,
) -> list[dict]:
    parser = _LinkTextParser()
    parser.feed(html or "")
    items: list[RegionalBusinessItem] = []
    seen: set[str] = set()
    for index, token in enumerate(parser.tokens):
        if token.get("type") != "link":
            continue
        title = clean_regional_text(token.get("text"))
        href = clean_regional_text(token.get("href"))
        if not _looks_like_list_title(title, href):
            continue
        published_at, agency = _infer_date_and_agency(parser.tokens, index, title)
        if not published_at:
            continue
        detail_url = urljoin(source.source_url, href)
        item_id = regional_item_id(source.provider, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            RegionalBusinessItem(
                item_id=item_id,
                title=title,
                source_provider=source.provider,
                source_scope=source.source_scope,
                agency=agency or source.provider,
                published_at=published_at,
                detail_url=detail_url,
                source_url=source.source_url,
            )
        )
        if len(items) >= max(1, limit):
            break
    return [asdict(item) for item in items]


def fetch_regional_business_source(
    source: RegionalBusinessSource,
    *,
    limit: int = 30,
    timeout: float = 10.0,
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
) -> dict:
    headers = {"User-Agent": user_agent, "Referer": source.source_url}
    with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
        response = client.get(source.source_url, headers=headers)
        response.raise_for_status()
        return {
            "source_key": source.source_key,
            "provider": source.provider,
            "source_url": source.source_url,
            "status": "success",
            "items": parse_regional_business_list(response.text, source=source, limit=limit),
        }


def fetch_regional_business_sources(
    *,
    limit: int = 30,
    timeout: float = 10.0,
    user_agent: str | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    all_items: list[dict] = []
    warnings: list[str] = []
    source_results: list[dict] = []
    per_source_limit = max(1, int(limit or 30))
    for source in REGIONAL_BUSINESS_SOURCES:
        try:
            result = fetch_regional_business_source(
                source,
                limit=per_source_limit,
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
                    "status": "failed",
                    "error": str(exc),
                }
            )
    deduped = {str(item.get("item_id")): item for item in all_items if item.get("item_id")}
    items = sorted(
        deduped.values(),
        key=lambda item: str(item.get("published_at") or ""),
        reverse=True,
    )
    return items[: max(1, limit)], warnings, source_results


def regional_theme_keywords() -> dict[str, list[str]]:
    return {
        "중국/아시아": ["중국", "홍콩", "대만", "아시아", "차이나", "CSF"],
        "신흥국/중동": ["중동", "아프리카", "유라시아", "중남미", "브라질", "신흥국", "EMERiCs"],
        "세계경제/통상": ["KIEP", "세계경제", "대외경제", "경제안보", "통상", "FTA", "CPTPP"],
        "무역/수출": ["무역", "수출", "수입", "관세", "FTA", "공급망", "통상", "다변화"],
        "전기차/배터리": ["전기차", "EV", "배터리", "자동차", "모빌리티", "충전"],
        "AI/디지털": ["AI", "인공지능", "데이터", "디지털", "플랫폼", "반도체", "GPU"],
        "에너지/원자재": ["에너지", "석유", "가스", "원자재", "태양광", "풍력", "전력"],
        "정책/규제": ["정책", "규제", "안보", "국무원", "표준", "조례", "제재"],
        "소비/결제": ["소비", "결제", "유통", "화장품", "의료", "바이오", "관광"],
    }


def normalize_regional_keywords(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re.split(r"[,;|/#\n]+", value)
    elif isinstance(value, Iterable):
        raw_items = []
        for item in value:
            raw_items.extend(normalize_regional_keywords(item))
        return list(dict.fromkeys(raw_items))
    else:
        raw_items = [str(value)]
    return [item for item in (clean_regional_text(raw) for raw in raw_items) if item]


def _keyword_in_text(keyword: str, text: str) -> bool:
    cleaned = clean_regional_text(keyword).lower()
    if not cleaned:
        return False
    if re.fullmatch(r"[a-z0-9]{1,4}", cleaned):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(cleaned)}(?![a-z0-9])", text))
    return cleaned in text


def _strong_regional_target_hits(keywords: list[str], hit_keywords: list[str], text: str) -> list[str]:
    strong_hits: list[str] = []
    normalized_hits = {clean_regional_text(keyword).lower(): keyword for keyword in hit_keywords}
    for keyword in keywords:
        cleaned = clean_regional_text(keyword)
        lowered = cleaned.lower()
        if lowered not in normalized_hits:
            continue
        if lowered in GENERIC_TARGET_KEYWORDS:
            continue
        if len(cleaned) <= 2 and not re.fullmatch(r"[A-Z0-9]{3,}", cleaned):
            continue
        strong_hits.append(cleaned)
    if strong_hits:
        return strong_hits
    label_like_hits = [
        keyword
        for keyword in hit_keywords
        if len(clean_regional_text(keyword)) >= 6 and clean_regional_text(keyword).lower() in text
    ]
    return label_like_hits


def match_regional_business_items_to_targets(items: list[dict], targets: list[dict]) -> list[dict]:
    theme_map = regional_theme_keywords()
    matched: list[dict] = []
    for item in items:
        text = " ".join(
            [
                clean_regional_text(item.get("title")),
                clean_regional_text(item.get("agency")),
                clean_regional_text(item.get("source_provider")),
                clean_regional_text(item.get("source_scope")),
            ]
        ).lower()
        matched_themes = [
            theme
            for theme, keywords in theme_map.items()
            if any(_keyword_in_text(keyword, text) for keyword in keywords)
        ]
        target_matches = []
        matched_target_keys: set[tuple[str, str, str]] = set()
        score = min(45, len(matched_themes) * 8)
        for target in targets:
            keywords = normalize_regional_keywords(
                [target.get("label"), target.get("ticker"), *(target.get("keywords") or [])]
            )
            hit_keywords = [keyword for keyword in keywords if _keyword_in_text(keyword, text)]
            if not hit_keywords:
                continue
            strong_hits = _strong_regional_target_hits(keywords, hit_keywords, text)
            if not strong_hits:
                continue
            target_key = (
                clean_regional_text(target.get("label")).lower(),
                clean_regional_text(target.get("ticker")).upper(),
                clean_regional_text(target.get("source")).lower(),
            )
            if target_key in matched_target_keys:
                continue
            matched_target_keys.add(target_key)
            score += 18 + min(20, len(strong_hits) * 4)
            target_matches.append(
                {
                    "label": target.get("label"),
                    "ticker": target.get("ticker"),
                    "source": target.get("source"),
                    "matched_keywords": strong_hits[:8],
                }
            )
        enriched = dict(item)
        enriched["matched_themes"] = matched_themes[:8]
        enriched["target_matches"] = target_matches[:8]
        enriched["portfolio_related"] = bool(target_matches)
        enriched["relevance_score"] = min(100, score)
        matched.append(enriched)
    return sorted(matched, key=lambda item: (int(item.get("relevance_score") or 0), str(item.get("published_at") or "")), reverse=True)


def should_refresh_regional_business_cache(cache: dict | None, *, selected_date: date | None = None) -> bool:
    if not isinstance(cache, dict) or not cache:
        return True
    updated_at = clean_regional_text(cache.get("updated_at"))
    if not updated_at:
        return True
    try:
        parsed = datetime.fromisoformat(updated_at)
    except ValueError:
        return True
    today = selected_date or datetime.now(parsed.tzinfo).date()
    if parsed.date() < today:
        return True
    return datetime.now(parsed.tzinfo) - parsed > timedelta(hours=24)


def regional_business_copyright_policy() -> dict:
    return {
        "mode": "metadata_and_derived_signals_only",
        "full_text_stored": False,
        "page_body_stored": False,
        "attachment_downloaded": False,
        "message": "EMERiCs/CSF/KIEP 자료는 제목, 기관, 발행일, 링크, 자체 관련성 분석만 저장하고 원문 본문은 자동 저장하지 않습니다.",
    }
