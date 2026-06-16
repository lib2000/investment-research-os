"""HTML article text extraction helpers for web capture."""

from __future__ import annotations

import json
from html import unescape
from html.parser import HTMLParser
from re import DOTALL, IGNORECASE, findall, finditer, search, sub


class WebCaptureTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_stack: list[str] = []
        self._ignore_depth = 0
        self._capture_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.candidate_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attrs_text = " ".join(f"{name}={value or ''}" for name, value in attrs).lower()
        void_tags = {"br", "img", "input", "meta", "link", "hr", "source", "area", "base", "col", "embed", "param", "track", "wbr"}
        chrome_markers = [
            "gnb",
            "lnb",
            "nav",
            "navigation",
            "menu",
            "category",
            "breadcrumb",
            "footer",
            "header",
            "aside",
            "sidebar",
            "share",
            "sns",
            "related",
            "recommend",
            "popular",
            "ranking",
            "comment",
            "reply",
            "advert",
            "ad-",
            "ad_",
        ]
        ignore_tags = {"nav", "header", "footer", "aside", "form", "button", "select", "option"}
        if self._ignore_depth > 0 or tag_name in ignore_tags or any(marker in attrs_text for marker in chrome_markers):
            if tag_name not in void_tags:
                self._ignore_depth += 1
            return
        article_markers = [
            "article",
            "article-view-content",
            "article_view_content",
            "article-view",
            "article_view",
            "article-body",
            "article_body",
            "article-content",
            "article_content",
            "articlebody",
            "article-txt",
            "article_txt",
            "news-body",
            "news_body",
            "news-content",
            "view-content",
            "view_content",
            "content-body",
            "content_body",
            "news_view",
            "news-view",
            "news-article",
            "news_article",
            "view-article",
            "view_article",
            "article-area",
            "article_area",
            "article_wrap",
            "article-wrap",
            "article-text",
            "article_text",
            "newsct_article",
            "newsct_body",
            "articlecont",
            "article-veiw-body",
            "article-view-body",
        ]
        starts_candidate = tag_name in {"article", "main"} or any(
            marker in attrs_text for marker in article_markers
        )
        if self._capture_depth > 0 and tag_name not in void_tags:
            self._capture_depth += 1
        elif starts_candidate:
            self._capture_depth = 1
            self.candidate_parts.append("\n")
        if tag_name in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_stack.append(tag_name)
        if tag_name == "title":
            self._in_title = True
        if tag_name in {"p", "br", "div", "section", "article", "li", "tr", "h1", "h2", "h3"}:
            self.text_parts.append("\n")
            if self._capture_depth > 0:
                self.candidate_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if self._ignore_depth > 0:
            self._ignore_depth -= 1
            return
        if self._skip_stack and self._skip_stack[-1] == tag_name:
            self._skip_stack.pop()
        if tag_name == "title":
            self._in_title = False
        if tag_name in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3"}:
            self.text_parts.append("\n")
            if self._capture_depth > 0:
                self.candidate_parts.append("\n")
        if self._capture_depth > 0:
            self._capture_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_stack or self._ignore_depth > 0:
            return
        cleaned = " ".join(unescape(data).split())
        if not cleaned:
            return
        if self._in_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned)
        if self._capture_depth > 0:
            self.candidate_parts.append(cleaned)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return "\n".join(
            line.strip()
            for line in "".join(self.text_parts).splitlines()
            if line.strip()
        )

    @property
    def candidate_text(self) -> str:
        return "\n".join(
            line.strip()
            for line in "".join(self.candidate_parts).splitlines()
            if line.strip()
        )


def iter_json_ld_values(value: object):
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from iter_json_ld_values(item)
        for key in ["mainEntity", "mainEntityOfPage", "itemListElement"]:
            nested = value.get(key)
            if isinstance(nested, (dict, list)):
                yield from iter_json_ld_values(nested)
    elif isinstance(value, list):
        for item in value:
            yield from iter_json_ld_values(item)


def normalize_json_ld_type(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item).lower() for item in value}
    if value:
        return {str(value).lower()}
    return set()


def extract_json_ld_article_text(html_text: str) -> tuple[str, str]:
    article_types = {"article", "newsarticle", "blogposting", "report", "analysisnewsarticle"}
    best_title = ""
    best_text = ""
    for match in finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html_text or "",
        DOTALL | IGNORECASE,
    ):
        raw_json = unescape(match.group(1) or "").strip()
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except Exception:
            continue
        for item in iter_json_ld_values(payload):
            types = normalize_json_ld_type(item.get("@type"))
            if not (types & article_types):
                continue
            title = str(item.get("headline") or item.get("name") or "").strip()
            parts = [
                item.get("articleBody"),
                item.get("description"),
                item.get("abstract"),
            ]
            section = item.get("articleSection")
            if isinstance(section, list):
                parts.append(" / ".join(str(piece) for piece in section if piece))
            elif section:
                parts.append(str(section))
            text = clean_web_article_text(
                "\n\n".join(str(part) for part in parts if str(part or "").strip())
            )
            if len(text) > len(best_text):
                best_title = title
                best_text = text
    return clean_web_article_title(best_title), best_text


def extract_meta_article_title(html_text: str) -> str:
    candidates = [
        r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']twitter:title[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']title[\"'][^>]+content=[\"'](.*?)[\"']",
    ]
    for pattern in candidates:
        match = search(pattern, html_text or "", IGNORECASE | DOTALL)
        if match:
            return clean_web_article_title(unescape(match.group(1) or ""))
    return ""


def extract_html_paragraph_list_text(html_text: str) -> str:
    parts: list[str] = []
    for match in finditer(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", html_text or "", DOTALL | IGNORECASE):
        fragment = match.group(1) or ""
        fragment = sub(r"<script\b.*?</script>", " ", fragment, flags=DOTALL | IGNORECASE)
        fragment = sub(r"<style\b.*?</style>", " ", fragment, flags=DOTALL | IGNORECASE)
        fragment = sub(r"<br\s*/?>", "\n", fragment, flags=IGNORECASE)
        fragment = sub(r"<[^>]+>", " ", fragment)
        cleaned = " ".join(unescape(fragment).split())
        if cleaned:
            parts.append(cleaned)
    return clean_web_article_text("\n".join(parts))


def extract_html_table_row_text(html_text: str) -> str:
    parts: list[str] = []
    for match in finditer(r"<tr\b[^>]*>(.*?)</tr>", html_text or "", DOTALL | IGNORECASE):
        row_html = match.group(1) or ""
        cells: list[str] = []
        for cell_match in finditer(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row_html, DOTALL | IGNORECASE):
            fragment = cell_match.group(1) or ""
            fragment = sub(r"<script\b.*?</script>", " ", fragment, flags=DOTALL | IGNORECASE)
            fragment = sub(r"<style\b.*?</style>", " ", fragment, flags=DOTALL | IGNORECASE)
            fragment = sub(r"<br\s*/?>", " / ", fragment, flags=IGNORECASE)
            fragment = sub(r"<[^>]+>", " ", fragment)
            cleaned = " ".join(unescape(fragment).split())
            if cleaned:
                cells.append(cleaned)
        row_text = " | ".join(cells)
        if row_text and search(r"\d{2}/\d{2}/\d{2}|\b(?:10-K|10-Q|8-K|ARS|PDF|HTML|XBRL|Annual|Quarterly|Financial)\b", row_text, IGNORECASE):
            parts.append(row_text)
    return clean_web_article_text("\n".join(parts))


def extract_html_result_line_text(html_text: str) -> str:
    parts: list[str] = []
    current_period = ""
    for match in finditer(r"<(h[23]|div)\b([^>]*)>(.*?)</\1>", html_text or "", DOTALL | IGNORECASE):
        tag = (match.group(1) or "").lower()
        attrs = match.group(2) or ""
        fragment = match.group(3) or ""
        plain = sub(r"<script\b.*?</script>", " ", fragment, flags=DOTALL | IGNORECASE)
        plain = sub(r"<style\b.*?</style>", " ", plain, flags=DOTALL | IGNORECASE)
        plain = sub(r"<br\s*/?>", " / ", plain, flags=IGNORECASE)
        plain = sub(r"<[^>]+>", " ", plain)
        cleaned = " ".join(unescape(plain).split())
        if not cleaned:
            continue
        if tag in {"h2", "h3"} and search(r"\b(?:Q[1-4]|20\d{2})\b", cleaned, IGNORECASE):
            current_period = cleaned
            continue
        if "result-line" not in attrs:
            continue
        if not search(r"\b(?:Financial Results|Shareholder Letter|Webcast|10-K|10-Q|PDF|HTML|Audio|Filing)\b", cleaned, IGNORECASE):
            continue
        parts.append(f"{current_period} | {cleaned}" if current_period else cleaned)
    return clean_web_article_text("\n".join(parts))


def web_article_text_score(text: str) -> float:
    cleaned = clean_web_article_text(text)
    if not cleaned:
        return 0.0
    lines = [line for line in cleaned.splitlines() if line.strip()]
    length = len(cleaned)
    sentence_count = len(findall(r"[.!?。！？]|[다요]\.", cleaned))
    number_count = len(findall(r"\d", cleaned))
    structured_separator_count = len(findall(r"\s\|\s", cleaned))
    filing_or_result_rows = len(
        findall(
            r"(?:\d{2}/\d{2}/\d{2}|Q[1-4]\s+20\d{2}).{0,120}(?:10-K|10-Q|8-K|PDF|HTML|XBRL|Financial Results|Shareholder Letter|Webcast|Filing)",
            cleaned,
            IGNORECASE,
        )
    )
    noise_hits = len(
        findall(
            r"(로그인|회원가입|구독|관련기사|많이 본|추천기사|ADVERTISEMENT|Subscribe|Sign in|Copyright)",
            cleaned,
            IGNORECASE,
        )
    )
    return (
        length
        + len(lines) * 35
        + sentence_count * 25
        + number_count * 0.5
        + structured_separator_count * 80
        + filing_or_result_rows * 180
        - noise_hits * 500
    )


def extract_webpage_text(html_text: str) -> tuple[str, str]:
    extractor = WebCaptureTextExtractor()
    try:
        extractor.feed(html_text)
    except Exception:
        return "", ""
    json_title, json_text = extract_json_ld_article_text(html_text)
    candidate_text = clean_web_article_text(extractor.candidate_text)
    paragraph_text = extract_html_paragraph_list_text(html_text)
    table_text = extract_html_table_row_text(html_text)
    result_line_text = extract_html_result_line_text(html_text)
    fallback_text = clean_web_article_text(extractor.text)
    title = clean_web_article_title(
        json_title or extractor.title or extract_meta_article_title(html_text)
    )
    candidates = [json_text, candidate_text, paragraph_text, table_text, result_line_text, fallback_text]
    best_text = max(candidates, key=web_article_text_score)
    return title[:160], clean_web_article_text(best_text)[:30000]


def clean_web_article_title(title: str) -> str:
    cleaned = sub(r"\s+", " ", (title or "").strip())
    for marker in [" < ", " - 디일렉", " | ", " :: ", " - "]:
        if marker in cleaned and len(cleaned.split(marker, 1)[0]) >= 8:
            cleaned = cleaned.split(marker, 1)[0].strip()
            break
    return cleaned


def trim_web_article_body_window(lines: list[str]) -> list[str]:
    if len(lines) < 6:
        return lines
    start = 0
    for idx, line in enumerate(lines[:24]):
        text = line.strip()
        if len(text) >= 36 and (
            search(r"[가-힣].*(다|니다|했다|한다|됐다|된다|라고|며|고)\.?", text)
            or search(r"[A-Za-z].{30,}[.!?]", text)
            or search(r"\d+(?:\.\d+)?\s*(?:%|원|달러|엔|조|억|만|bn|billion|million)", text, IGNORECASE)
        ):
            start = idx
            break
    trimmed = lines[start:]
    if len(trimmed) > 80:
        trimmed = trimmed[:80]
    return trimmed


def clean_web_article_text(text: str) -> str:
    raw_lines = [line.strip() for line in (text or "").replace("\r\n", "\n").split("\n")]
    lines: list[str] = []
    skip_exact = {
        "로그인",
        "회원가입",
        "모바일웹",
        "전체기사",
        "뉴스",
        "기사검색",
        "최신뉴스",
        "동정",
        "전자엔지니어",
        "권글전문",
        "컨콜전문",
        "오피니언",
        "반도체",
        "디스플레이",
        "배터리",
        "바이오",
        "완성품",
        "금융",
        "IT‧게임",
        "ITㆍ게임",
        "IT·게임",
        "중국산업동향",
        "경제",
        "증권",
        "산업",
        "정치",
        "사회",
        "국제",
        "문화",
        "연예",
        "스포츠",
        "날씨",
        "랭킹",
        "구독신청",
        "뉴스레터",
        "팝업 닫기",
        "본문 글자 크기 조정",
        "전문가칼럼",
        "인사동정",
        "회사소개",
        "광고문의",
        "제휴문의",
        "개인정보처리방침",
        "청소년보호정책",
        "이메일무단수집거부",
        "홈",
        "검색",
        "통신",
        "모빌리티",
        "생활경제",
        "헬스케어",
        "부동산",
        "테크",
        "마켓",
        "영상",
        "포토",
        "오늘의 주요뉴스",
        "이 시각 주요뉴스",
        "기사목록",
        "본문듣기",
        "닫기",
        "공유",
        "스크랩",
        "인쇄",
        "메일",
        "글자크기 설정",
        "가",
        "스크롤 이동 상태바",
        "이 기사를 공유합니다",
        "댓글 0",
        "이전 기사보기 다음 기사보기",
        "About",
        "Careers",
        "Contact",
        "Contact Us",
        "Press",
        "Privacy",
        "Privacy Policy",
        "Terms",
        "Terms of Use",
        "Cookie Policy",
        "Subscribe",
        "Sign in",
        "Sign up",
        "Log in",
        "Read more",
        "Related Articles",
        "Recommended",
        "Most Popular",
        "Share this article",
        "All Rights Reserved",
    }
    stop_markers = [
        "저작권자",
        "무단전재",
        "재배포 금지",
        "관련기사",
        "많이 본 뉴스",
        "인기기사",
        "추천기사",
        "댓글삭제",
        "기사제보",
        "전체 메뉴",
        "주요뉴스",
        "섹션뉴스",
        "바로가기",
        "본문 바로가기",
        "뉴스홈",
        "구독",
        "공유하기",
        "Related Articles",
        "Recommended Articles",
        "Most Popular",
        "More from",
        "Read next",
        "Subscribe",
        "Sign up",
        "Sign in",
        "All rights reserved",
        "Copyright",
    ]
    noisy_patterns = [
        r"^(동정|전자엔지니어|권글전문|컨콜전문|오피니언|반도체|디스플레이|배터리|바이오|완성품|금융|통신|모빌리티|생활경제|헬스케어|부동산|테크|마켓|산업IT|중국산업동향)$",
        r"^(많이 본|인기|추천|관련)\s*기사",
        r"^(구독|팔로우|공유|댓글|프린트|목록|닫기|열기|검색|좋아요|북마크|스크랩|폰트|인쇄|메일)$",
        r"^(전체|분야별|많이본|오피니언|포토|영상|그래픽)$",
        r"^(다음|이전)\s*(기사|뉴스)",
        r"^(AD|Advertisement|Sponsored|Promoted)$",
        r"^https?://",
        r"^(copyright|all rights reserved|newsletter|subscribe|sign in|sign up|log in|privacy policy|terms of use|cookie policy)$",
        r"^(facebook|twitter|linkedin|instagram|youtube|x|line|whatsapp)$",
        r"^(share|copy link|print|email|download|listen|back to top)$",
        r"^(기자명|이메일|전화|팩스)\s*[:：]",
        r"^\d+\s*/\s*\d+$",
    ]
    for line in raw_lines:
        if not line:
            continue
        compact = sub(r"\s+", " ", line).strip()
        if not compact or compact in skip_exact:
            continue
        if compact.endswith(" 바로가기") or compact.startswith("메뉴"):
            continue
        if any(search(pattern, compact, IGNORECASE) for pattern in noisy_patterns):
            continue
        if len(compact) <= 12 and not search(r"[가-힣]{3,}.*(다|요|음|것|며|고|로|을|를|은|는)", compact):
            if not search(r"\d{2,}", compact):
                continue
        if search(r"^(페이스북|트위터|카카오톡|URL복사|공유|목록|프린트)$", compact, IGNORECASE):
            continue
        if len(compact) <= 2 and not any(char.isdigit() for char in compact):
            continue
        if any(marker in compact for marker in stop_markers):
            break
        if "기사본문" in compact and "<" in compact:
            continue
        if search(r"^\*+\s*\*+\s*\*+", compact):
            continue
        if search(r"^(입력|업데이트)\s+\d{4}\.\d{2}\.\d{2}", compact):
            lines.append(compact)
            continue
        if "기사의 본문 내용은 이 글자크기로 변경됩니다" in compact:
            continue
        if "[사진=" in compact or "사진=" in compact or "사진 제공" in compact:
            continue
        if compact.startswith("Image:"):
            continue
        lines.append(compact)

    if not lines:
        return ""

    start_index = 0
    for idx, line in enumerate(lines):
        if search(r"^(입력|업데이트)\s+\d{4}\.\d{2}\.\d{2}", line):
            start_index = idx + 1
            break
    if start_index:
        lines = lines[start_index:]

    article_lines: list[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = sub(r"\s+", " ", line)
        if normalized in seen:
            continue
        seen.add(normalized)
        article_lines.append(line)
    article_lines = trim_web_article_body_window(article_lines)
    return "\n".join(article_lines).strip()
