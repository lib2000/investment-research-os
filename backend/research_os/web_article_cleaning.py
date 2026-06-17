from __future__ import annotations

from re import IGNORECASE, search, sub


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
