from urllib.parse import urlparse


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
