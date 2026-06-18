import httpx

from research_os import web_capture_translation
from research_os.file_extraction import extract_pdf_text
from re import DOTALL, IGNORECASE, escape, findall, search, split, sub
from urllib.parse import urlparse
import urllib.request

from research_os.web_capture_fallbacks import official_url_fallback_summary
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
    return web_capture_translation.detect_web_text_language(text)


def translation_language_label(language: str) -> str:
    return web_capture_translation.translation_language_label(language)


LOCAL_TRANSLATION_GLOSSARY = web_capture_translation.LOCAL_TRANSLATION_GLOSSARY


def local_glossary_translate_line(line: str, language: str) -> str:
    return web_capture_translation.local_glossary_translate_line(line, language)


def english_sentence_to_korean_note(line: str, index: int) -> str | None:
    return web_capture_translation.english_sentence_to_korean_note(line, index)


def japanese_sentence_to_korean_note(line: str, index: int) -> str | None:
    return web_capture_translation.japanese_sentence_to_korean_note(line, index)


def foreign_line_korean_signal(line: str, language: str, index: int) -> str:
    return web_capture_translation.foreign_line_korean_signal(line, language, index)


def foreign_text_korean_digest(text: str, title: str = "") -> dict:
    return web_capture_translation.foreign_text_korean_digest(text, title)

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
