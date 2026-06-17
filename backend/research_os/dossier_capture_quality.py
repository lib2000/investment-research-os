"""Capture failure and quality classification helpers for Dossier inputs."""

from __future__ import annotations


def is_failed_capture_manifest_entry(entry: dict) -> bool:
    summary = str(entry.get("summary") or "")
    relative_path = str(entry.get("relative_path") or "")
    source_processing = entry.get("source_url_processing") or {}
    failed_statuses = {"fetch_failed", "invalid", "empty_text"}
    return (
        "WinError 10061" in summary
        or "웹사이트 본문을 추출하지 못했습니다" in summary
        or "winerror-10061" in relative_path.lower()
        or str(source_processing.get("status") or "") in failed_statuses
    )


def capture_quality_status(
    *,
    raw_content: str,
    attachment_info: dict | None = None,
    source_url_processing: dict | None = None,
) -> dict:
    url_status = str((source_url_processing or {}).get("status") or "")
    url_text = str((source_url_processing or {}).get("text") or "")
    attachment_text = str((attachment_info or {}).get("extracted_text") or "")
    text_length = max(len(raw_content or ""), len(url_text), len(attachment_text))
    warnings: list[str] = []
    if url_status in {"fetch_failed", "invalid", "empty_text"}:
        warnings.append("웹사이트 본문 추출 실패")
    attachment_profile = (attachment_info or {}).get("extraction_profile") or {}
    if attachment_profile.get("ocr_status") == "unavailable":
        warnings.append("이미지 OCR 미연결")
    if attachment_info and not attachment_text and not (attachment_info or {}).get("extraction_char_count"):
        warnings.append(
            "첨부 파일 본문 추출 확인 필요"
            if attachment_profile.get("ocr_status") != "unavailable"
            else "이미지 원본은 저장됐지만 OCR 미연결로 본문 분석은 제외"
        )
    if text_length >= 1000 and not warnings:
        status = "정상"
    elif text_length >= 250:
        status = "보강 필요" if warnings else "정상"
    else:
        status = "실패" if warnings else "보강 필요"
    return {
        "status": status,
        "text_length": text_length,
        "warnings": warnings,
        "url_status": url_status or None,
        "readiness": (
            "분석에 바로 활용 가능"
            if status == "정상"
            else "추가 본문/원문 확인 후 활용"
            if status == "보강 필요"
            else "분석 반영 제외 권장"
        ),
    }