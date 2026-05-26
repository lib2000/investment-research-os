from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin

import httpx


KCIF_REPORT_LIST_URL = "https://www.kcif.or.kr/annual/reportList"
KCIF_LOGIN_URL = "https://www.kcif.or.kr/webUser/login"
KCIF_LOGIN_PROC_URL = "https://www.kcif.or.kr/webUser/loginProc"
KCIF_COPYRIGHT_URL = "https://www.kcif.or.kr/etc/copyright"

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

_NUMERIC_SIGNAL_PATTERN = re.compile(
    r"[-+]?\d+(?:\.\d+)?\s*(?:%|bp|bps|조|억|만|원|달러|엔|위안|배럴|bbl|bn|billion|million|m)",
    re.IGNORECASE,
)


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
            text = _clean_text(" ".join(self._link_text))
            if text:
                self.tokens.append({"type": "link", "text": text, "href": self._link_href})
            self._link_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self.tokens.append({"type": "text", "text": text})


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _report_id(title: str, published_at: str, detail_url: str) -> str:
    payload = "\n".join([title.strip(), published_at.strip(), detail_url.strip()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _keyword_in_text(keyword: str, text: str) -> bool:
    cleaned = _clean_text(keyword).lower()
    if not cleaned:
        return False
    if re.fullmatch(r"[a-z0-9]{1,4}", cleaned):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(cleaned)}(?![a-z0-9])", text))
    return cleaned in text


def _nearby_text(tokens: list[dict], index: int, *, before: int = 8, after: int = 18) -> list[str]:
    start = max(0, index - before)
    end = min(len(tokens), index + after + 1)
    return [_clean_text(item.get("text")) for item in tokens[start:end] if _clean_text(item.get("text"))]


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
        title = _clean_text(token.get("text"))
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


def _extract_visible_text(html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html or "")
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div|li|strong|h[1-6])>", "\n", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    return cleaned.strip()


def _extract_report_focus_text(html: str, report: dict) -> str:
    title = _clean_text(report.get("title"))
    visible = _extract_visible_text(html)
    if not visible:
        return ""
    start = visible.rfind(title) if title else -1
    if start < 0:
        return visible[:4000]
    end_markers = ["목록", "작성자", "관련 보고서", "이전", "다음"]
    sliced = visible[start : start + 5000]
    marker_positions = [sliced.find(marker) for marker in end_markers if sliced.find(marker) > 200]
    if marker_positions:
        sliced = sliced[: min(marker_positions)]
    return sliced.strip()


def analyze_kcif_detail_html(html: str, report: dict) -> dict:
    focus_text = _extract_report_focus_text(html, report)
    title = _clean_text(report.get("title"))
    category = _clean_text(report.get("category"))
    theme_map = kcif_theme_keywords()
    haystack = " ".join([title, category, focus_text]).lower()
    matched_themes = [
        theme
        for theme, keywords in theme_map.items()
        if any(_keyword_in_text(keyword, haystack) for keyword in keywords)
    ]
    numeric_signals = list(dict.fromkeys(_NUMERIC_SIGNAL_PATTERN.findall(focus_text)))[:12]
    numeric_signals = [
        signal
        for signal in (_clean_text(item) for item in numeric_signals)
        if signal and not re.fullmatch(r"\d{2}\.\d{2}\s*조", signal)
    ][:12]
    focus_lines = [
        line.strip(" ㅁ-ㆍ*")
        for line in re.split(r"[\n]+", focus_text)
        if 8 <= len(line.strip()) <= 180
    ]
    source_summary_available = len(focus_text) >= 80
    return {
        "detail_status": "available" if source_summary_available else "metadata_only",
        "source_summary_available": source_summary_available,
        "source_summary_length": len(focus_text),
        "matched_themes": matched_themes[:8],
        "numeric_signals": numeric_signals,
        "derived_points": _derive_kcif_points(focus_lines, matched_themes, numeric_signals),
        "raw_text_stored": False,
        "pdf_downloaded": False,
        "note": "상세 화면에서 투자 판단용 신호만 추출했고 원문/PDF 전문은 저장하지 않았습니다.",
    }


def _derive_kcif_points(lines: list[str], matched_themes: list[str], numeric_signals: list[str]) -> list[str]:
    points: list[str] = []
    if matched_themes:
        points.append("연결 테마: " + ", ".join(matched_themes[:4]))
    if numeric_signals:
        points.append("확인 수치: " + ", ".join(numeric_signals[:6]))
    line_count = len([line for line in lines if line])
    if line_count:
        points.append(f"상세 화면 요약 문장 {line_count}개에서 테마/수치 신호를 추출했습니다.")
    return points[:5]


def _kcif_login(
    client: httpx.Client,
    *,
    username: str,
    password: str,
    login_proc_url: str = KCIF_LOGIN_PROC_URL,
) -> dict:
    response = client.post(
        login_proc_url,
        data={"mem_id": username, "mem_pwd": password},
        headers={"Referer": KCIF_LOGIN_URL},
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("KCIF 로그인 응답을 JSON으로 해석하지 못했습니다.") from exc
    status = _clean_text(payload.get("status"))
    message = _clean_text(payload.get("msg"))
    if status in {"success", "success_tf"}:
        return {"status": "authenticated", "message": message or "KCIF 로그인 성공"}
    if status.startswith("fail_popup"):
        raise RuntimeError(message or "KCIF 계정 휴면/권한 확인이 필요합니다.")
    raise RuntimeError(message or "KCIF 로그인 실패")


def fetch_kcif_report_list_with_status(
    *,
    url: str = KCIF_REPORT_LIST_URL,
    limit: int = 30,
    timeout: float = 12.0,
    username: str = "",
    password: str = "",
    login_proc_url: str = KCIF_LOGIN_PROC_URL,
) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36 InvestmentResearchOS/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    attempts: list[str] = []
    use_login = bool(username and password)
    for trust_env in [False, True]:
        mode = "direct" if not trust_env else "system_proxy"
        try:
            with httpx.Client(
                timeout=httpx.Timeout(timeout, connect=min(timeout, 8.0)),
                follow_redirects=True,
                headers=headers,
                trust_env=trust_env,
            ) as client:
                auth_status = "not_configured"
                if use_login:
                    auth_result = _kcif_login(
                        client,
                        username=username,
                        password=password,
                        login_proc_url=login_proc_url,
                    )
                    auth_status = str(auth_result.get("status") or "authenticated")
                response = client.get(url)
                response.raise_for_status()
            return {
                "reports": parse_kcif_report_list(response.text, base_url=str(response.url or url), limit=limit),
                "auth_status": auth_status,
                "connection_mode": mode,
                "attempts": attempts + [f"{mode}: success {response.status_code}"],
            }
        except Exception as error:
            attempts.append(f"{mode}: {error}")
    raise RuntimeError("KCIF 목록 확인 실패: " + " | ".join(attempts))


def fetch_kcif_detail_analyses(
    reports: list[dict],
    *,
    timeout: float = 12.0,
    username: str = "",
    password: str = "",
    login_proc_url: str = KCIF_LOGIN_PROC_URL,
    max_reports: int = 5,
) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36 InvestmentResearchOS/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    selected_reports = [
        item
        for item in reports[: max(1, max_reports)]
        if isinstance(item, dict) and str(item.get("detail_url") or "").startswith("http")
    ]
    analyses: dict[str, dict] = {}
    attempts: list[str] = []
    use_login = bool(username and password)
    for trust_env in [False, True]:
        mode = "direct" if not trust_env else "system_proxy"
        try:
            with httpx.Client(
                timeout=httpx.Timeout(timeout, connect=min(timeout, 8.0)),
                follow_redirects=True,
                headers=headers,
                trust_env=trust_env,
            ) as client:
                auth_status = "not_configured"
                if use_login:
                    auth_result = _kcif_login(
                        client,
                        username=username,
                        password=password,
                        login_proc_url=login_proc_url,
                    )
                    auth_status = str(auth_result.get("status") or "authenticated")
                for report in selected_reports:
                    try:
                        response = client.get(str(report.get("detail_url")))
                        response.raise_for_status()
                        analyses[str(report.get("report_id"))] = analyze_kcif_detail_html(response.text, report)
                    except Exception as error:
                        analyses[str(report.get("report_id"))] = {
                            "detail_status": "failed",
                            "error": str(error),
                            "raw_text_stored": False,
                            "pdf_downloaded": False,
                        }
                return {
                    "detail_status": "checked",
                    "auth_status": auth_status,
                    "connection_mode": mode,
                    "analyses": analyses,
                    "attempts": attempts + [f"{mode}: success"],
                }
        except Exception as error:
            attempts.append(f"{mode}: {error}")
    return {
        "detail_status": "failed",
        "auth_status": "failed" if use_login else "not_configured",
        "analyses": analyses,
        "attempts": attempts,
    }


def fetch_kcif_report_list(*, url: str = KCIF_REPORT_LIST_URL, limit: int = 30, timeout: float = 12.0) -> list[dict]:
    return fetch_kcif_report_list_with_status(url=url, limit=limit, timeout=timeout).get("reports", [])


def normalize_kcif_keywords(value: object) -> list[str]:
    raw_values: list[str] = []
    if isinstance(value, str):
        raw_values = re.split(r"[,/|·\s]+", value)
    elif isinstance(value, Iterable):
        raw_values = [str(item or "") for item in value]
    keywords = []
    for raw in raw_values:
        cleaned = _clean_text(raw).strip("[](){}")
        if len(cleaned) < 2:
            continue
        if cleaned.upper() in {"ETF", "ETN", "PBC", "INC", "CO", "LTD"}:
            continue
        keywords.append(cleaned)
    return list(dict.fromkeys(keywords))


def build_kcif_watch_targets(portfolio_payload: object, interest_payload: dict | None = None) -> list[dict]:
    targets: list[dict] = []
    portfolios = getattr(portfolio_payload, "portfolios", []) or []
    for portfolio in portfolios:
        for holding in getattr(portfolio, "holdings", []) or []:
            name = _clean_text(getattr(holding, "name", ""))
            ticker = _clean_text(getattr(holding, "ticker", ""))
            tags = list(getattr(holding, "theme_tags", []) or [])
            keywords = normalize_kcif_keywords([name, ticker, *tags])
            if name and keywords:
                targets.append(
                    {
                        "label": name,
                        "ticker": ticker,
                        "source": "portfolio_holding",
                        "keywords": keywords,
                        "weight_hint": float(getattr(holding, "weight", 0) or 0),
                    }
                )
    for item in (interest_payload or {}).get("tickers", []):
        if not isinstance(item, dict):
            continue
        label = _clean_text(
            item.get("companyName")
            or item.get("company_name")
            or (item.get("verification") or {}).get("company_name")
            or item.get("ticker")
        )
        keywords = normalize_kcif_keywords([label, item.get("ticker"), *(item.get("tags") or [])])
        if label and keywords:
            targets.append(
                {
                    "label": label,
                    "ticker": _clean_text(item.get("ticker")),
                    "source": "interest_ticker",
                    "keywords": keywords,
                    "weight_hint": 0,
                }
            )
    for item in (interest_payload or {}).get("sectors", []):
        if not isinstance(item, dict):
            continue
        label = _clean_text(item.get("name"))
        keywords = normalize_kcif_keywords([label, *(item.get("keywords") or []), *(item.get("tags") or [])])
        if label and keywords:
            targets.append(
                {
                    "label": label,
                    "source": "interest_sector",
                    "keywords": keywords,
                    "weight_hint": 0,
                }
            )
    return targets


def kcif_theme_keywords() -> dict[str, list[str]]:
    return {
        "금리/채권": ["금리", "국채", "채권", "fomc", "연준", "fed", "ecb", "boj"],
        "환율/달러": ["환율", "달러", "원화", "엔화", "위안", "외환"],
        "자금 흐름": ["fund flow", "펀드", "자본유출입", "수급", "외국인"],
        "원자재/에너지": ["원자재", "유가", "중동", "에너지", "천연가스", "석유"],
        "AI/반도체": ["인공지능", "생성형 AI", "반도체", "메모리", "전력", "데이터센터", "capex"],
        "은행/금융": ["은행", "대출", "신용", "부동산", "디지털 유로"],
        "글로벌 경기": ["미국", "중국", "유럽", "일본", "신흥국", "성장", "인플레이션"],
    }


def match_kcif_reports_to_targets(reports: list[dict], targets: list[dict]) -> list[dict]:
    theme_map = kcif_theme_keywords()
    enriched: list[dict] = []
    for report in reports:
        haystack = " ".join(
            [
                str(report.get("title") or ""),
                str(report.get("category") or ""),
                str(report.get("file_name") or ""),
            ]
        ).lower()
        matched_targets = []
        for target in targets:
            matched_keywords = [
                keyword
                for keyword in target.get("keywords", [])
                if keyword and _keyword_in_text(keyword, haystack)
            ]
            if matched_keywords:
                matched_targets.append(
                    {
                        "label": target.get("label"),
                        "source": target.get("source"),
                        "ticker": target.get("ticker"),
                        "matched_keywords": matched_keywords[:6],
                        "weight_hint": target.get("weight_hint", 0),
                    }
                )
        matched_themes = [
            theme
            for theme, keywords in theme_map.items()
            if any(_keyword_in_text(keyword, haystack) for keyword in keywords)
        ]
        relevance_score = min(
            100,
            len(matched_targets) * 24
            + len(matched_themes) * 12
            + (10 if "국제금융속보" in str(report.get("category") or "") else 0)
            + (8 if "주간" in str(report.get("category") or "") else 0),
        )
        enriched.append(
            {
                **report,
                "matched_targets": matched_targets[:8],
                "matched_themes": matched_themes[:8],
                "relevance_score": relevance_score,
                "portfolio_related": bool(matched_targets),
                "recommended_action": _recommended_action(matched_targets, matched_themes),
            }
        )
    return sorted(
        enriched,
        key=lambda item: (int(item.get("relevance_score") or 0), item.get("published_at") or ""),
        reverse=True,
    )


def _recommended_action(matched_targets: list[dict], matched_themes: list[str]) -> str:
    if matched_targets:
        labels = ", ".join(dict.fromkeys(str(item.get("label") or "") for item in matched_targets if item.get("label")))
        return f"보유/관심 대상({labels})의 매크로 리스크 메모에 연결하세요."
    if matched_themes:
        return f"{', '.join(matched_themes[:3])} 테마를 시장일지와 매크로 분석에 반영하세요."
    return "제목과 분류만 기록하고 필요 시 사용자가 원문을 직접 확인하세요."


def should_refresh_kcif_cache(cache: dict | None, *, selected_date: date | None = None) -> bool:
    if not isinstance(cache, dict) or not cache.get("updated_at"):
        return True
    today = selected_date or date.today()
    try:
        updated_date = datetime.fromisoformat(str(cache["updated_at"]).replace("Z", "+00:00")).date()
    except ValueError:
        return True
    return updated_date < today


def kcif_copyright_policy() -> dict:
    return {
        "mode": "metadata_only",
        "full_text_stored": False,
        "pdf_auto_download": False,
        "allowed_fields": ["title", "category", "published_at", "author", "detail_url", "file_name", "matched_themes"],
        "source": KCIF_COPYRIGHT_URL,
        "message": "KCIF 보고서 본문/PDF는 자동 저장하지 않고 공개 목록 메타데이터와 자체 관련성 분석만 저장합니다.",
    }
