from __future__ import annotations

import email.utils
import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx


FSC_PRESS_RSS_URL = "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111"
KOREA_POLICY_BRIEFING_URL = "https://www.korea.kr/briefing/pressReleaseList.do"
FTC_PRESS_URL = "https://www.ftc.go.kr/www/sub.do?key=12"
MOTIE_PRESS_URL = "https://www.motie.go.kr/kor/article/ATCL3f49a5a8c"
FSS_DART_PRESS_URL = "https://dart.fss.or.kr/info/searchBodo.do"

DATE_PATTERN = re.compile(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}")
GENERIC_TARGET_KEYWORDS = {
    "ai",
    "kr",
    "korea",
    "us",
    "usa",
    "etf",
    "한국",
    "미국",
    "투자",
    "성장",
    "정책",
    "시장",
}
SKIP_LINK_TEXTS = {
    "",
    "HOME",
    "검색",
    "본문 바로가기",
    "메뉴",
    "로그인",
    "회원가입",
    "RSS",
    "이전페이지",
    "다음페이지",
    "첫페이지",
    "마지막페이지",
    "목록",
    "상세검색",
    "페이스북",
    "트위터",
    "인쇄",
    "공유",
    "닫기",
}


@dataclass
class PolicySource:
    source_key: str
    provider: str
    source_url: str
    source_scope: str
    parser: str = "html"


@dataclass
class PolicySourceItem:
    item_id: str
    title: str
    source_provider: str
    source_scope: str
    agency: str
    published_at: str
    detail_url: str
    source_url: str
    category: str = "공식 정책자료"


POLICY_SOURCES = [
    PolicySource(
        source_key="fsc_press_rss",
        provider="금융위원회",
        source_url=FSC_PRESS_RSS_URL,
        source_scope="금융정책 보도자료 RSS",
        parser="rss",
    ),
    PolicySource(
        source_key="korea_policy_briefing",
        provider="대한민국 정책브리핑",
        source_url=KOREA_POLICY_BRIEFING_URL,
        source_scope="정부 부처 보도자료",
    ),
    PolicySource(
        source_key="ftc_press",
        provider="공정거래위원회",
        source_url=FTC_PRESS_URL,
        source_scope="공정거래·플랫폼 규제 보도자료",
    ),
    PolicySource(
        source_key="motie_press",
        provider="산업통상자원부",
        source_url=MOTIE_PRESS_URL,
        source_scope="산업·통상·에너지 정책자료",
    ),
    PolicySource(
        source_key="fss_dart_press",
        provider="금융감독원/DART",
        source_url=FSS_DART_PRESS_URL,
        source_scope="공시·자본시장 보도자료",
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
            text = clean_policy_text(" ".join(self._link_text))
            if text:
                self.tokens.append({"type": "link", "text": text, "href": self._link_href})
            self._link_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = clean_policy_text(data)
        if not text:
            return
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self.tokens.append({"type": "text", "text": text})


def clean_policy_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def compact_policy_title(value: object, *, max_length: int = 180) -> str:
    title = clean_policy_text(value)
    if len(title) <= max_length:
        return title
    for marker in [" 담당 부서", " 붙임", " □ ", " ○ ", "▷", "※"]:
        index = title.find(marker, 40)
        if 40 <= index <= max_length:
            return title[:index].strip(" -·")
    sentence_match = re.match(r"^(.{40,180}?[.!?。]|.{40,180}?다\.)", title)
    if sentence_match:
        return sentence_match.group(1).strip()
    return f"{title[: max_length - 1].rstrip()}…"


def policy_item_id(provider: str, title: str, published_at: str, detail_url: str) -> str:
    payload = "\n".join([provider, title.strip(), published_at.strip(), detail_url.strip()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_policy_date(value: object) -> str:
    text = clean_policy_text(value)
    match = DATE_PATTERN.search(text)
    if match:
        parts = re.split(r"[-./]", match.group(0))
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    try:
        parsed = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date().isoformat()


def _looks_like_policy_title(title: str, href: str) -> bool:
    if title in SKIP_LINK_TEXTS or title.isdigit() or len(title) < 8:
        return False
    lowered = title.lower()
    if lowered.endswith((".pdf", ".zip", ".hwp", ".docx", ".xls", ".xlsx")):
        return False
    if href.startswith("#") or href.startswith("javascript"):
        return False
    if "sns" in lowered or "captcha" in lowered:
        return False
    return True


def _nearby_text(tokens: list[dict], index: int, *, before: int = 4, after: int = 8) -> list[str]:
    start = max(0, index - before)
    end = min(len(tokens), index + after + 1)
    return [clean_policy_text(item.get("text")) for item in tokens[start:end] if clean_policy_text(item.get("text"))]


def _infer_date_and_agency(tokens: list[dict], index: int, title: str, provider: str) -> tuple[str, str]:
    candidates = _nearby_text(tokens, index, before=3, after=10)
    published_at = ""
    agency_candidates: list[str] = []
    for text in candidates:
        date_value = normalize_policy_date(text)
        if date_value and not published_at:
            published_at = date_value
            continue
        if text == title or text in SKIP_LINK_TEXTS or text.isdigit():
            continue
        if len(text) > 80 or "전체" in text or "검색" in text:
            continue
        if not DATE_PATTERN.search(text):
            agency_candidates.append(text)
    return published_at, agency_candidates[-1] if agency_candidates else provider


def parse_policy_source_html_list(html: str, *, source: PolicySource, limit: int = 30) -> list[dict]:
    parser = _LinkTextParser()
    parser.feed(html or "")
    items: list[PolicySourceItem] = []
    seen: set[str] = set()
    for index, token in enumerate(parser.tokens):
        if token.get("type") != "link":
            continue
        title = compact_policy_title(token.get("text"))
        href = clean_policy_text(token.get("href"))
        if not _looks_like_policy_title(title, href):
            continue
        published_at, agency = _infer_date_and_agency(parser.tokens, index, title, source.provider)
        if not published_at:
            continue
        detail_url = urljoin(source.source_url, href)
        item_id = policy_item_id(source.provider, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            PolicySourceItem(
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


def _rss_text(element: ElementTree.Element, tag: str) -> str:
    value = element.findtext(tag)
    return clean_policy_text(value)


def parse_policy_source_rss(xml_text: str, *, source: PolicySource, limit: int = 30) -> list[dict]:
    root = ElementTree.fromstring(xml_text or "")
    items: list[PolicySourceItem] = []
    seen: set[str] = set()
    for item in root.findall(".//item"):
        title = compact_policy_title(_rss_text(item, "title"))
        detail_url = _rss_text(item, "link")
        published_at = normalize_policy_date(_rss_text(item, "pubDate") or _rss_text(item, "date"))
        if not title or not detail_url:
            continue
        item_id = policy_item_id(source.provider, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            PolicySourceItem(
                item_id=item_id,
                title=title,
                source_provider=source.provider,
                source_scope=source.source_scope,
                agency=source.provider,
                published_at=published_at,
                detail_url=detail_url,
                source_url=source.source_url,
            )
        )
        if len(items) >= max(1, limit):
            break
    return [asdict(item) for item in items]


def parse_policy_source_items(raw_text: str, *, source: PolicySource, limit: int = 30) -> list[dict]:
    if source.parser == "rss":
        return parse_policy_source_rss(raw_text, source=source, limit=limit)
    return parse_policy_source_html_list(raw_text, source=source, limit=limit)


def fetch_policy_source(
    source: PolicySource,
    *,
    limit: int = 30,
    timeout: float = 12.0,
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
            "items": parse_policy_source_items(response.text, source=source, limit=limit),
        }


def fetch_policy_sources(
    *,
    limit: int = 40,
    timeout: float = 12.0,
    user_agent: str | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    all_items: list[dict] = []
    warnings: list[str] = []
    source_results: list[dict] = []
    per_source_limit = max(1, int(limit or 40))
    for source in POLICY_SOURCES:
        try:
            result = fetch_policy_source(
                source,
                limit=per_source_limit,
                timeout=timeout,
                user_agent=user_agent
                or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            )
            source_results.append({key: value for key, value in result.items() if key != "items"})
            all_items.extend(result.get("items") or [])
        except Exception as exc:
            warnings.append(f"{source.provider} 정책자료 확인 실패: {exc}")
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
    items = sorted(deduped.values(), key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return items[: max(1, limit)], warnings, source_results


def policy_theme_keywords() -> dict[str, list[str]]:
    return {
        "금융/자본시장": ["금융", "자본시장", "공시", "회계", "상장", "공매도", "증권", "DART", "금융위"],
        "공정거래/플랫폼": ["공정거래", "플랫폼", "독점", "담합", "하도급", "가맹", "소비자", "FTC"],
        "산업/통상": ["산업", "통상", "무역", "수출", "관세", "공급망", "FTA", "반도체", "배터리"],
        "에너지/원자재": ["에너지", "전력", "원전", "석유", "가스", "재생", "태양광", "풍력"],
        "AI/디지털": ["AI", "인공지능", "디지털", "데이터", "클라우드", "소프트웨어", "보안"],
        "바이오/헬스케어": ["바이오", "제약", "의료", "헬스케어", "임상", "식약", "의약"],
        "세제/법령": ["세법", "세제", "법령", "시행령", "개정안", "입법", "규정", "고시"],
        "환경/ESG": ["환경", "탄소", "ESG", "배출권", "기후", "재활용", "순환경제"],
    }


def normalize_policy_keywords(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = re.split(r"[,;|/#\n]+", value)
    elif isinstance(value, Iterable):
        raw_items = []
        for item in value:
            raw_items.extend(normalize_policy_keywords(item))
        return list(dict.fromkeys(raw_items))
    else:
        raw_items = [str(value)]
    return [item for item in (clean_policy_text(raw) for raw in raw_items) if item]


def _keyword_in_text(keyword: str, text: str) -> bool:
    cleaned = clean_policy_text(keyword).lower()
    if not cleaned:
        return False
    if re.fullmatch(r"[a-z0-9]{1,4}", cleaned):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(cleaned)}(?![a-z0-9])", text))
    return cleaned in text


def _strong_policy_target_hits(keywords: list[str], hit_keywords: list[str]) -> list[str]:
    strong_hits: list[str] = []
    normalized_hits = {clean_policy_text(keyword).lower(): keyword for keyword in hit_keywords}
    for keyword in keywords:
        cleaned = clean_policy_text(keyword)
        lowered = cleaned.lower()
        if lowered not in normalized_hits:
            continue
        if lowered in GENERIC_TARGET_KEYWORDS:
            continue
        if len(cleaned) <= 2 and not re.fullmatch(r"[A-Z0-9]{3,}", cleaned):
            continue
        strong_hits.append(cleaned)
    return strong_hits or [keyword for keyword in hit_keywords if len(clean_policy_text(keyword)) >= 6]


def match_policy_items_to_targets(items: list[dict], targets: list[dict]) -> list[dict]:
    theme_map = policy_theme_keywords()
    matched: list[dict] = []
    for item in items:
        text = " ".join(
            [
                clean_policy_text(item.get("title")),
                clean_policy_text(item.get("agency")),
                clean_policy_text(item.get("source_provider")),
                clean_policy_text(item.get("source_scope")),
                clean_policy_text(item.get("category")),
            ]
        ).lower()
        matched_themes = [
            theme
            for theme, keywords in theme_map.items()
            if any(_keyword_in_text(keyword, text) for keyword in keywords)
        ]
        target_matches = []
        matched_target_keys: set[tuple[str, str, str]] = set()
        score = min(50, len(matched_themes) * 9)
        for target in targets:
            keywords = normalize_policy_keywords(
                [target.get("label"), target.get("ticker"), *(target.get("keywords") or [])]
            )
            hit_keywords = [keyword for keyword in keywords if _keyword_in_text(keyword, text)]
            if not hit_keywords:
                continue
            strong_hits = _strong_policy_target_hits(keywords, hit_keywords)
            if not strong_hits:
                continue
            target_key = (
                clean_policy_text(target.get("label")).lower(),
                clean_policy_text(target.get("ticker")).upper(),
                clean_policy_text(target.get("source")).lower(),
            )
            if target_key in matched_target_keys:
                continue
            matched_target_keys.add(target_key)
            score += 20 + min(24, len(strong_hits) * 4)
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
        enriched["recommended_action"] = (
            "원문 링크에서 정책 시행 범위와 적용 시점을 확인한 뒤 관련 보유/관심 종목 투자 메모에 반영하세요."
            if score > 0
            else "정책 방향성만 참고하고 직접 투자 판단에는 추가 근거를 확인하세요."
        )
        matched.append(enriched)
    return sorted(matched, key=lambda item: (int(item.get("relevance_score") or 0), str(item.get("published_at") or "")), reverse=True)


def should_refresh_policy_sources_cache(
    cache: dict | None,
    *,
    selected_date: date | None = None,
    refresh_hours: float = 12.0,
) -> bool:
    if not isinstance(cache, dict) or not cache:
        return True
    updated_at = clean_policy_text(cache.get("updated_at"))
    if not updated_at:
        return True
    try:
        parsed = datetime.fromisoformat(updated_at)
    except ValueError:
        return True
    today = selected_date or datetime.now(parsed.tzinfo).date()
    if parsed.date() < today:
        return True
    return datetime.now(parsed.tzinfo) - parsed > timedelta(hours=max(1.0, float(refresh_hours or 12.0)))


def policy_sources_copyright_policy() -> dict:
    return {
        "mode": "official_policy_metadata_only",
        "full_text_stored": False,
        "page_body_stored": False,
        "attachment_downloaded": False,
        "message": "공식 정책자료는 제목, 기관, 발행일, 링크, 정책/법령 분류와 자체 관련성 분석만 저장하고 원문 본문은 자동 저장하지 않습니다.",
    }
