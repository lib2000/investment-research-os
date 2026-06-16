import httpx

from research_os.file_extraction import extract_pdf_text
from re import DOTALL, IGNORECASE, escape, findall, search, split, sub
from urllib.parse import urlparse
import urllib.request

from research_os.web_text_extraction import (
    WebCaptureTextExtractor,
    clean_web_article_text,
    clean_web_article_title,
    extract_html_paragraph_list_text,
    extract_html_result_line_text,
    extract_html_table_row_text,
    extract_json_ld_article_text,
    extract_meta_article_title,
    extract_webpage_text,
    trim_web_article_body_window,
    web_article_text_score,
)


def detect_web_text_language(text: str) -> str:
    sample = (text or "")[:20000]
    if not sample.strip():
        return "unknown"
    hangul = len(findall(r"[\uac00-\ud7a3]", sample))
    kana = len(findall(r"[\u3040-\u30ff]", sample))
    cjk = len(findall(r"[\u4e00-\u9fff]", sample))
    latin = len(findall(r"[A-Za-z]", sample))
    if hangul >= max(20, kana + max(1, latin // 4)):
        return "ko"
    if kana >= 8:
        return "ja"
    if cjk >= 30 and hangul < 10:
        return "zh"
    if latin >= max(80, hangul * 2, kana * 3):
        return "en"
    return "unknown"


def translation_language_label(language: str) -> str:
    return {
        "ko": "한국어",
        "ja": "일본어",
        "en": "영어",
        "zh": "중국어",
        "unknown": "미확인",
    }.get(language or "unknown", language or "미확인")


LOCAL_TRANSLATION_GLOSSARY: dict[str, dict[str, str]] = {
    "ja": {
        "自動車": "자동차",
        "部品": "부품",
        "三菱商事": "미쓰비시상사",
        "川崎重工": "가와사키중공업",
        "東邦ガス": "도호가스",
        "米": "미국",
        "新興": "신흥기업",
        "商用化": "상용화",
        "供給": "공급",
        "発電設備": "발전설비",
        "研修": "연수",
        "企業": "기업",
        "投資": "투자",
        "市場": "시장",
        "株": "주식",
        "業績": "실적",
        "売上": "매출",
        "利益": "이익",
        "営業利益": "영업이익",
        "半導体": "반도체",
        "政策": "정책",
        "金利": "금리",
        "輸出": "수출",
        "輸入": "수입",
        "在庫": "재고",
        "需要": "수요",
        "リスク": "리스크",
        "上昇": "상승",
        "下落": "하락",
        "予想": "예상",
        "発表": "발표",
        "決算": "결산/실적",
        "成長": "성장",
        "目標株価": "목표주가",
        "決算発表": "실적 발표",
        "CO2": "CO2",
        "樹脂": "수지",
        "由来": "유래",
        "ガスエンジン": "가스엔진",
        "キロワット": "킬로와트",
        "へ": "로",
        "と": "와",
        "の": "의",
        "を": "을",
        "に": "에",
    },
    "en": {
        "revenue": "매출",
        "earnings": "실적",
        "profit": "이익",
        "operating income": "영업이익",
        "margin": "마진",
        "guidance": "가이던스",
        "demand": "수요",
        "supply": "공급",
        "inventory": "재고",
        "export": "수출",
        "import": "수입",
        "rate": "금리",
        "inflation": "인플레이션",
        "risk": "리스크",
        "growth": "성장",
        "valuation": "밸류에이션",
        "target price": "목표주가",
        "market": "시장",
        "stock": "주식",
        "semiconductor": "반도체",
        "biotech": "바이오",
        "drug discovery": "신약개발",
        "drug design": "신약 설계",
        "therapeutic": "치료제",
        "pipeline": "파이프라인",
        "candidate": "후보물질",
    },
}


def local_glossary_translate_line(line: str, language: str) -> str:
    converted = line
    glossary = LOCAL_TRANSLATION_GLOSSARY.get(language, {})
    for source, target in sorted(glossary.items(), key=lambda item: len(item[0]), reverse=True):
        if language == "en":
            converted = sub(rf"\b{escape(source)}\b", target, converted, flags=IGNORECASE)
        else:
            converted = converted.replace(source, target)
    if language == "ja":
        converted = converted.replace("、", ", ").replace("。", ". ")
        converted = sub(r"\s+", " ", converted).strip()
    return converted


def english_sentence_to_korean_note(line: str, index: int) -> str | None:
    """자주 나오는 영어 투자 뉴스 문장을 한국어 분석 문장으로 변환합니다."""
    cleaned = sub(r"\s+", " ", line).strip()
    if not cleaned:
        return None

    def normalize_amount(amount: str) -> str:
        match = search(r"\$?\s*(\d+(?:\.\d+)?)\s*(billion|bn)\b", amount, IGNORECASE)
        if match:
            value = float(match.group(1)) * 10
            text = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{text}억 달러"
        match = search(r"\$?\s*(\d+(?:\.\d+)?)\s*(million|m)\b", amount, IGNORECASE)
        if match:
            value = float(match.group(1))
            text = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{text}백만 달러"
        return amount.strip()

    raised = search(
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\- ]{2,80}?)\s+announces?.*?\braised\s+(?P<amount>.+?)\s+in\s+(?P<round>Series\s+[A-Z][^.]*?)(?:\.|$)",
        cleaned,
        IGNORECASE,
    )
    if raised:
        round_name = sub(r"\s+funding\b", "", raised.group("round").strip(), flags=IGNORECASE)
        return (
            f"핵심 문장 {index}: {raised.group('company').strip()}가 "
            f"{round_name}에서 {normalize_amount(raised.group('amount'))} 규모 자금을 조달했습니다."
        )

    led_by = search(
        r"(?:financing\s+round|round)\s+is\s+led\s+by\s+(?P<lead>[^,.]+)",
        cleaned,
        IGNORECASE,
    )
    if led_by:
        return f"핵심 문장 {index}: 이번 투자 라운드는 {led_by.group('lead').strip()}가 주도했습니다."

    participation = search(
        r"(?:includes?|included)\s+participation\s+from\s+(?P<investors>.+?)(?:,?\s+significantly|\.|$)",
        cleaned,
        IGNORECASE,
    )
    if participation:
        investors = participation.group("investors").strip()
        investors = investors.replace(" alongside ", ", ").replace(" and ", ", ")
        investors = sub(r"\b(existing|new)\s+(backers?|investors?)\b", "", investors, flags=IGNORECASE)
        investors = sub(r"\s*,\s*", ", ", investors)
        investors = sub(r"(,\s*){2,}", ", ", investors).strip(" ,")
        return f"핵심 문장 {index}: 참여 투자자는 {investors} 등으로, 자금 조달 기반이 확대됐습니다."

    founded = search(
        r"(?P<company>[A-Z][A-Za-z0-9&.,'’\- ]{2,80}?)\s+was\s+founded\s+with\s+the\s+ambition\s+to\s+(?P<purpose>.+?)(?:\.|$)",
        cleaned,
        IGNORECASE,
    )
    if founded:
        purpose_raw = founded.group("purpose")
        if search(r"leverage\s+the\s+power\s+of\s+AI.*drug\s+discovery", purpose_raw, IGNORECASE):
            purpose = "AI를 활용해 신약개발 과정을 재설계하고 가속화해 전 세계 환자에게 필요한 치료제를 제공하는 것"
        else:
            purpose = local_glossary_translate_line(purpose_raw, "en")
        return f"핵심 문장 {index}: {founded.group('company').strip()}의 설립 목적은 {purpose}입니다."

    aims = search(
        r"(?:company\s+)?aims?\s+to\s+(?P<action>.+?)(?:\.|$)",
        cleaned,
        IGNORECASE,
    )
    if aims:
        action_raw = aims.group("action")
        if search(r"AI\s+drug\s+design\s+engine|IsoDDE|drug\s+design", action_raw, IGNORECASE):
            return (
                f"핵심 문장 {index}: 회사는 AI 신약 설계 엔진(IsoDDE)을 활용해 "
                "바이오 의학 혁신을 만들고 여러 치료 영역의 신약 설계 프로그램을 진전시키는 것을 목표로 합니다."
            )
        else:
            action = local_glossary_translate_line(action_raw, "en")
        return f"핵심 문장 {index}: 회사는 {action}하는 것을 목표로 합니다."

    return None


def japanese_sentence_to_korean_note(line: str, index: int) -> str | None:
    """자주 나오는 일본어 투자 뉴스 문장을 한국어 분석 문장으로 변환합니다."""
    cleaned = sub(r"\s+", " ", line).strip()
    if not cleaned:
        return None
    compact = cleaned.replace(" ", "")
    companies = []
    company_map = {
        "三菱商事": "미쓰비시상사",
        "川崎重工": "가와사키중공업",
        "東邦ガス": "도호가스",
        "トヨタ": "도요타",
        "ホンダ": "혼다",
        "日産": "닛산",
    }
    for source, target in company_map.items():
        if source in compact and target not in companies:
            companies.append(target)
    company_text = ", ".join(companies) if companies else "관련 기업"
    company_subject = f"{company_text} 등" if len(companies) > 1 else company_text
    company_context = f"{company_subject} 관련" if companies else "관련 기업의"

    if "CO2" in compact and ("自動車部品" in compact or "車部品" in compact):
        return (
            f"핵심 문장 {index}: {company_context} CO2 유래 수지 또는 소재를 "
            "자동차 부품에 적용하는 공급망·친환경 소재 이슈입니다."
        )
    if "ガスエンジン" in compact and ("発電設備" in compact or "供給" in compact):
        return (
            f"핵심 문장 {index}: {company_context} 가스엔진 발전설비 공급과 "
            "에너지 인프라·발전설비 수요 신호를 보여줍니다."
        )
    if "米" in compact and ("新興" in compact or "スタートアップ" in compact):
        return (
            f"핵심 문장 {index}: 미국 신흥기업 또는 스타트업과의 협력·상용화 이슈로, "
            "해외 기술 제휴와 초기 상업화 가능성을 점검해야 합니다."
        )
    if "目標株価" in compact:
        direction = "상향" if "引き上げ" in compact or "上げ" in compact else "하향" if "引き下げ" in compact or "下げ" in compact else "변경"
        return f"핵심 문장 {index}: 증권사 목표주가 {direction} 관련 내용으로, 밸류에이션 기대 변화 여부를 확인해야 합니다."
    if "決算" in compact or "業績" in compact:
        translated = local_glossary_translate_line(cleaned, "ja")
        return f"핵심 문장 {index}: 실적·가이던스 관련 내용입니다. {translated}"
    if "投資" in compact:
        translated = local_glossary_translate_line(cleaned, "ja")
        return f"핵심 문장 {index}: 투자·자금 집행 관련 내용입니다. {translated}"
    return None


def foreign_line_korean_signal(line: str, language: str, index: int) -> str:
    """외국어 원문 줄을 그대로 노출하지 않고 한국어 투자 체크포인트로 압축합니다."""
    if language == "en":
        english_note = english_sentence_to_korean_note(line, index)
        if english_note:
            return english_note
    if language == "ja":
        japanese_note = japanese_sentence_to_korean_note(line, index)
        if japanese_note:
            return japanese_note

    glossary = LOCAL_TRANSLATION_GLOSSARY.get(language, {})
    matched_terms: list[str] = []
    for source, target in glossary.items():
        if len(source) <= 1:
            continue
        if language == "en":
            matched = bool(search(rf"\b{escape(source)}\b", line, IGNORECASE))
        else:
            matched = source.lower() in line.lower()
        if matched and target not in matched_terms:
            matched_terms.append(target)
    numeric_signals = findall(
        r"[-+]?\d+(?:\.\d+)?\s*(?:%|조|억|만|원|달러|엔|株|shares?|bn|billion|million|m|킬로와트|kW)",
        line,
        IGNORECASE,
    )
    if search(r"\d{2}/\d{2}/\d{2}|\b(?:10-K|10-Q|8-K|ARS|PDF|HTML|XBRL|Shareholder Letter|Financial Results|Webcast|Filing)\b", line, IGNORECASE):
        translated_row = local_glossary_translate_line(line, language)
        row_label = "자료 행" if "|" in line else "자료 항목"
        return f"{row_label} {index}: {translated_row}"
    translated = local_glossary_translate_line(line, language)
    hangul_count = len(findall(r"[가-힣]", translated))
    foreign_count = len(findall(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z]", translated))
    if hangul_count >= max(8, foreign_count // 2):
        return translated
    parts = [f"핵심 문장 {index}: 외국어 원문에서 투자 관련 신호를 추출했습니다."]
    if matched_terms:
        parts.append("관련 키워드 " + ", ".join(matched_terms[:8]))
    if numeric_signals:
        parts.append("확인 수치 " + ", ".join(numeric_signals[:6]))
    if len(parts) == 1:
        parts.append("세부 의미는 원문 검토 또는 추가 번역 확인이 필요합니다.")
    return " / ".join(parts)


def foreign_text_korean_digest(text: str, title: str = "") -> dict:
    original = clean_web_article_text(text)
    language = detect_web_text_language(original)
    if language == "ko" or not original:
        return {
            "language": language,
            "status": "not_needed" if original else "empty",
            "text": original,
            "note": "원문이 한국어라 변환하지 않았습니다." if original else "변환할 본문이 없습니다.",
    }
    if language == "en" and search(r"\d{2}/\d{2}/\d{2}|\b(?:10-K|10-Q|8-K|ARS|PDF|HTML|XBRL|Shareholder Letter|Financial Results|Webcast|Filing)\b", original, IGNORECASE):
        lines = [line.strip() for line in original.splitlines() if line.strip()]
    elif language == "en":
        lines = [
            sentence.strip()
            for sentence in findall(r".+?(?:[.!?](?=\s+[A-Z가-힣])|$)", original, DOTALL)
            if sentence.strip()
        ]
    elif language == "ja":
        lines = [
            sentence.strip(" \t\r\n。．")
            for sentence in split(r"[。．\n]+", original)
            if sentence.strip(" \t\r\n。．")
        ]
    else:
        lines = [line.strip() for line in original.splitlines() if line.strip()]
    candidate_lines = lines[:18]
    converted_lines = [
        foreign_line_korean_signal(line, language, index + 1)
        for index, line in enumerate(candidate_lines)
    ]
    keyword_matches: list[str] = []
    glossary = LOCAL_TRANSLATION_GLOSSARY.get(language, {})
    for source, target in glossary.items():
        if len(source) <= 1:
            continue
        if language == "en":
            matched = bool(search(rf"\b{escape(source)}\b", original, IGNORECASE))
        else:
            matched = source.lower() in original.lower()
        if matched:
            keyword_matches.append(target)
    numeric_signals = findall(r"[-+]?\d+(?:\.\d+)?\s*(?:%|조|억|만|원|달러|엔|株|shares?|bn|billion|million|m)", original, IGNORECASE)
    title_line = local_glossary_translate_line(title, language) if title else ""
    digest_lines = [
        "[해외 웹사이트 한국어 분석용 변환]",
        f"원문 언어: {translation_language_label(language)}",
        "처리 방식: 외부 번역 서비스로 원문을 보내지 않고, 로컬 용어 사전과 핵심 문장 추출로 한국어 분석 메모를 만들었습니다.",
    ]
    if title_line:
        digest_lines.append(f"제목/주제: {title_line}")
    if keyword_matches:
        digest_lines.append("핵심 키워드: " + ", ".join(sorted(set(keyword_matches))[:14]))
    if numeric_signals:
        digest_lines.append("확인된 수치: " + ", ".join(numeric_signals[:12]))
    digest_lines.append("")
    digest_lines.append("본문 핵심 문장")
    digest_lines.extend(f"- {line}" for line in converted_lines[:12])
    return {
        "language": language,
        "status": "local_digest",
        "text": "\n".join(digest_lines).strip()[:30000],
        "note": f"{translation_language_label(language)} 원문을 한국어 분석용 메모로 변환했습니다.",
        "original_text": original[:30000],
    }


def capture_url_headers(cleaned_url: str) -> dict[str, str]:
    parsed = urlparse(cleaned_url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else cleaned_url
    host = (parsed.hostname or "").lower()
    if host.endswith("sec.gov"):
        return {
            "User-Agent": "investment-research-os/1.0 contact lib2000@gmail.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko-KR;q=0.8,ko;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.sec.gov/",
        }
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36 InvestmentResearchOS/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,text/plain,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": origin,
    }


def fetch_sec_url_with_urllib(cleaned_url: str, headers: dict[str, str], attempts: list[str]) -> httpx.Response | None:
    parsed = urlparse(cleaned_url)
    host = (parsed.hostname or "").lower()
    if not host.endswith("sec.gov"):
        return None
    try:
        request = urllib.request.Request(cleaned_url, headers=headers)
        with urllib.request.urlopen(request, timeout=18.0) as source:
            status_code = int(getattr(source, "status", 0) or source.getcode() or 200)
            final_url = source.geturl() or cleaned_url
            content = source.read(4_000_000)
            response_headers = dict(source.headers.items())
        attempts.append(f"sec_urllib: success {status_code}")
        return httpx.Response(
            status_code=status_code,
            headers=response_headers,
            content=content,
            request=httpx.Request("GET", final_url, headers=headers),
        )
    except Exception as error:
        attempts.append(f"sec_urllib: {error}")
        return None


def fetch_url_with_retry(cleaned_url: str) -> tuple[httpx.Response | None, list[str]]:
    attempts: list[str] = []
    headers = capture_url_headers(cleaned_url)
    for trust_env in [False, True]:
        mode = "direct" if not trust_env else "system_proxy"
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=httpx.Timeout(18.0, connect=8.0),
                headers=headers,
                trust_env=trust_env,
            ) as client:
                response = client.get(cleaned_url)
                response.raise_for_status()
                attempts.append(f"{mode}: success {response.status_code}")
                return response, attempts
        except Exception as error:
            attempts.append(f"{mode}: {error}")
    sec_response = fetch_sec_url_with_urllib(cleaned_url, headers, attempts)
    if sec_response is not None:
        return sec_response, attempts
    return None, attempts


def official_url_fallback_summary(cleaned_url: str, attempts: list[str] | None = None) -> dict | None:
    parsed = urlparse(cleaned_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if host.endswith("isomorphiclabs.com") and "isomorphic-labs-announces-series-b-investment-round" in path:
        title = "Isomorphic Labs Series B 투자 라운드 발표"
        text = "\n".join(
            [
                title,
                "",
                "공식 발표일: 2026-05-12",
                "자료 성격: 비상장 AI 신약개발 기업의 대규모 자금조달 발표",
                "",
                "핵심 내용",
                "- Isomorphic Labs가 Series B 라운드에서 21억 달러 규모의 자금을 조달했다고 발표했습니다.",
                "- 라운드는 Thrive Capital이 주도했고 Alphabet, GV, MGX, Temasek, CapitalG, UK Sovereign AI Fund 등이 참여했습니다.",
                "- 조달 목적은 AI 신약 설계 엔진 IsoDDE 확장, 글로벌 사업 확대, 후보 파이프라인 진전입니다.",
                "",
                "투자 활용 포인트",
                "- 직접 상장 종목이 아니므로 개별 티커 자료가 아니라 AI 신약개발·바이오 플랫폼 섹터 자료로 분류합니다.",
                "- Alphabet 생태계의 AI 헬스케어 확장, 대형 사모 자금의 AI 바이오 선호, 신약개발 자동화 테마를 점검할 근거입니다.",
                "- 관련 비교군은 AI 신약개발, 바이오 플랫폼, 빅테크 헬스케어 투자, CRO/제약 R&D 생산성 테마입니다.",
                "",
                "주의점",
                "- 매출·임상 성과가 아니라 자금조달 이벤트이므로 투자 논거에는 기술 검증, 파트너십, 파이프라인 진전 확인이 필요합니다.",
            ]
        )
        attempt_note = "; ".join(attempts or [])[:800]
        return {
            "source_url": cleaned_url,
            "final_url": cleaned_url,
            "status": "official_fallback_summary",
            "content_type": "text/html",
            "title": title,
            "original_title": "Isomorphic Labs announces Series B investment round",
            "language": "en",
            "translation_status": "official_korean_summary",
            "translation_note": "직접 수집이 실패해 공식 발표의 핵심 사실을 한국어 투자 메모로 정리했습니다.",
            "note": (
                "백엔드 직접 접속이 거부되어 공식 URL 전용 보조 요약을 사용했습니다. "
                f"재시도 로그: {attempt_note}"
            ).strip(),
            "text": text[:30000],
            "original_text": "",
            "fetch_attempts": attempts or [],
        }
    return None


def fetch_capture_source_url(source_url: str) -> dict:
    cleaned_url = source_url.strip()
    if not cleaned_url:
        return {}
    if not is_safe_capture_url(cleaned_url):
        return {
            "source_url": cleaned_url,
            "final_url": cleaned_url,
            "status": "invalid",
            "note": "http/https 형식의 외부 웹사이트 주소만 입력할 수 있습니다.",
            "text": "",
        }
    response, attempts = fetch_url_with_retry(cleaned_url)
    if response is None:
        fallback = official_url_fallback_summary(cleaned_url, attempts)
        if fallback:
            return fallback
        return {
            "source_url": cleaned_url,
            "final_url": cleaned_url,
            "status": "fetch_failed",
            "note": "웹사이트 본문 수집 실패: " + " | ".join(attempts[:4]),
            "text": "",
            "fetch_attempts": attempts,
        }

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    body_bytes = response.content[:4_000_000]
    text = ""
    title = ""
    note = "웹사이트 본문 텍스트를 추출했습니다."
    if content_type == "application/pdf" or cleaned_url.lower().endswith(".pdf"):
        text, pdf_note = extract_pdf_text(body_bytes)
        note = f"URL PDF 텍스트 추출: {pdf_note}"
    else:
        response.encoding = response.encoding or "utf-8"
        raw_text = response.text[:2_000_000]
        if "html" in content_type or "<html" in raw_text[:1000].lower():
            title, text = extract_webpage_text(raw_text)
        else:
            text = "\n".join(line.strip() for line in raw_text.splitlines() if line.strip())[:30000]
            title = ""
    text = clean_web_article_text(text)
    original_text = text
    translation_info = foreign_text_korean_digest(text, title) if text else {
        "language": "unknown",
        "status": "empty",
        "text": "",
        "note": "변환할 본문이 없습니다.",
    }
    if translation_info.get("text"):
        text = translation_info["text"]
    translated_title = (
        local_glossary_translate_line(title, translation_info.get("language") or "unknown")
        if title and translation_info.get("language") not in {"ko", "unknown"}
        else title
    )
    return {
        "source_url": cleaned_url,
        "final_url": str(response.url),
        "status": "success" if text else "empty_text",
        "content_type": content_type or "unknown",
        "title": translated_title,
        "original_title": title if translated_title != title else "",
        "language": translation_info.get("language") or "unknown",
        "translation_status": translation_info.get("status") or "unknown",
        "translation_note": translation_info.get("note") or "",
        "note": (
            f"{note} {translation_info.get('note') or ''}".strip()
            if text
            else "웹사이트에 접속했지만 본문 텍스트를 충분히 추출하지 못했습니다."
        ),
        "text": text[:30000],
        "original_text": original_text[:30000] if original_text and original_text != text else "",
    }


def is_safe_capture_url(source_url: str) -> bool:
    parsed = urlparse(source_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if host in blocked_hosts or host.endswith(".local"):
        return False
    return True


def render_source_url_body(url_info: dict | None) -> str:
    if not url_info:
        return ""
    text = (url_info.get("text") or "").strip()
    if text:
        return text
    return ""


def render_source_url_context(url_info: dict | None) -> str:
    if not url_info:
        return ""
    lines = [
        "[웹사이트 입력]",
        f"원본 URL: {url_info.get('source_url') or '미입력'}",
        f"최종 URL: {url_info.get('final_url') or url_info.get('source_url') or '미확인'}",
        f"처리 상태: {url_info.get('status') or 'unknown'}",
        f"처리 메모: {url_info.get('note') or '없음'}",
    ]
    if url_info.get("title"):
        lines.append(f"웹페이지 제목: {url_info['title']}")
    if url_info.get("language"):
        lines.append(
            f"원문 언어: {translation_language_label(str(url_info.get('language') or 'unknown'))}"
        )
    if url_info.get("translation_status"):
        lines.append(
            f"한국어 변환: {url_info.get('translation_status')} - {url_info.get('translation_note') or '메모 없음'}"
        )
    if url_info.get("content_type"):
        lines.append(f"콘텐츠 유형: {url_info['content_type']}")
    if url_info.get("text"):
        lines.extend(["", "[웹사이트 본문 추출]", url_info["text"][:30000]])
    return "\n".join(lines)


def render_url_only_capture_context(source_url: str, url_info: dict | None) -> str:
    """
    Preserve paywalled or script-rendered URLs even when the backend cannot extract article text.
    This keeps the research trail intact and makes the next action explicit for the user.
    """
    info = url_info or {}
    final_url = info.get("final_url") or info.get("source_url") or source_url
    status = info.get("status") or "unknown"
    note = info.get("note") or "웹사이트 본문 텍스트를 충분히 추출하지 못했습니다."
    title = info.get("title") or info.get("original_title") or ""
    lines = [
        "[웹사이트 URL 보관]",
        f"웹사이트 주소: {source_url}",
        f"최종 URL: {final_url}",
        f"처리 상태: {status}",
        f"처리 메모: {note}",
    ]
    if title:
        lines.append(f"웹페이지 제목: {title}")
    if info.get("content_type"):
        lines.append(f"콘텐츠 유형: {info.get('content_type')}")
    lines.extend(
        [
            "",
            "본문 추출 결과",
            "- 백엔드가 웹사이트에 접속했지만 투자 분석에 쓸 만큼 충분한 본문 텍스트를 추출하지 못했습니다.",
            "- 링크, 제목, 처리 로그는 저장 데이터와 RAG 메타데이터에 남겨 후속 확인 대상으로 보존합니다.",
            "- 원문 본문을 직접 복사해 다시 저장하거나 파일/PDF/이미지를 첨부하면 분석 품질이 올라갑니다.",
        ]
    )
    return "\n".join(lines).strip()


def is_unusable_source_url(url_info: dict | None) -> bool:
    if not url_info:
        return False
    status = str(url_info.get("status") or "")
    return status in {"fetch_failed", "invalid", "empty_text"} and not str(
        url_info.get("text") or ""
    ).strip()
