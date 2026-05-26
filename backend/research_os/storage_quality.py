"""Storage quality and soft-archive classification helpers."""

from __future__ import annotations


def is_archived_research_entry(manifest_entry: dict | None, json_payload: dict | None = None) -> bool:
    """Return True when a research-memory record is soft archived."""
    payload = json_payload if isinstance(json_payload, dict) else {}
    entry = manifest_entry if isinstance(manifest_entry, dict) else {}
    return bool(
        entry.get("is_deleted")
        or payload.get("is_deleted")
        or str(entry.get("status") or "").lower() == "archived"
        or str(payload.get("status") or "").lower() == "archived"
    )


def research_memory_legacy_policy(
    *,
    ticker: str | None = None,
    legacy_file_count: int = 0,
    archived_file_count: int = 0,
) -> dict:
    return {
        "policy": "soft_archive",
        "hard_delete_allowed": False,
        "default_visibility": "collapsed_legacy_group",
        "archive_behavior": "레거시 파일은 삭제하지 않고 status=archived, is_deleted=true 메타데이터로 기본 목록과 자동 주입 후보에서 숨깁니다.",
        "restore_behavior": "보관 문서 포함 옵션으로 다시 표시하고 개별 파일을 복원할 수 있습니다.",
        "decision": "공식 인증 리포트를 새 판단 기준으로 사용하고, 레거시 파일은 원문 추적/감사용으로 보관합니다.",
        "ticker": ticker,
        "legacy_file_count": legacy_file_count,
        "archived_file_count": archived_file_count,
        "recommended_action": (
            "공식 인증 파일이 충분하면 레거시 일괄 보관을 실행하세요."
            if legacy_file_count
            else "현재 기본 목록에 보관할 레거시 파일이 없습니다."
        ),
    }


def research_memory_entry_quality_metadata(
    manifest_entry: dict | None,
    json_payload: dict | None = None,
    captured_item: dict | None = None,
) -> dict:
    payload = json_payload if isinstance(json_payload, dict) else {}
    entry = manifest_entry if isinstance(manifest_entry, dict) else {}
    captured = captured_item if isinstance(captured_item, dict) else {}
    if not captured and isinstance(payload.get("captured_item"), dict):
        captured = payload["captured_item"]

    tag_values: list[str] = []
    for candidate in (entry.get("tags"), captured.get("tags"), payload.get("tags")):
        if isinstance(candidate, list):
            tag_values.extend(str(tag).strip() for tag in candidate if str(tag or "").strip())
    tags = list(dict.fromkeys(tag_values))

    source_url_processing = (
        entry.get("source_url_processing")
        if isinstance(entry.get("source_url_processing"), dict)
        else payload.get("source_url_processing")
        if isinstance(payload.get("source_url_processing"), dict)
        else None
    )
    capture_quality = (
        entry.get("capture_quality")
        if isinstance(entry.get("capture_quality"), dict)
        else payload.get("capture_quality")
        if isinstance(payload.get("capture_quality"), dict)
        else None
    )
    source_status = str((source_url_processing or {}).get("status") or "")
    url_text_unavailable = bool(
        "url_text_unavailable" in tags
        or source_status in {"fetch_failed", "invalid", "empty_text"}
    )
    body_supplemented = bool(
        "body_supplemented" in tags
        or payload.get("body_supplemented_at")
        or (isinstance(payload.get("body_supplements"), list) and payload["body_supplements"])
        or (isinstance(capture_quality, dict) and capture_quality.get("body_supplemented"))
    )
    needs_body_copy = bool(("needs_body_copy" in tags or url_text_unavailable) and not body_supplemented)
    data_quality_status = (
        str((capture_quality or {}).get("status") or "").strip()
        or ("본문 미확보" if url_text_unavailable else None)
    )
    return {
        "tags": tags,
        "source_url_processing": source_url_processing,
        "capture_quality": capture_quality,
        "data_quality_status": data_quality_status,
        "needs_body_copy": needs_body_copy,
        "url_text_unavailable": url_text_unavailable,
    }


def storage_quality_entry_needs_ocr(entry: dict) -> bool:
    """Classify only actual OCR problem states as OCR-needed."""
    tags = {str(tag).strip().lower() for tag in (entry.get("tags") or [])}
    needs_tags = {"ocr_needed", "ocr_unavailable", "ocr_error", "ocr_not_connected", "ocr_required"}
    if tags.intersection(needs_tags):
        return True
    attachment = entry.get("attachment") if isinstance(entry.get("attachment"), dict) else {}
    profile = attachment.get("extraction_profile") if isinstance(attachment.get("extraction_profile"), dict) else {}
    capture_quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    error_statuses = {"unavailable", "error", "ocr_unavailable", "ocr_error", "ocr_not_connected"}
    if attachment.get("ocr_required") is True or attachment.get("ocr_available") is False:
        return True
    for payload in (attachment, profile, capture_quality):
        if str(payload.get("ocr_status") or "").strip().lower() in error_statuses:
            return True
    return False


def storage_quality_entry_needs_body(entry: dict) -> bool:
    """Classify URL-only or failed body extraction records that need manual body notes."""
    tags = set(entry.get("tags") or [])
    capture_quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    return bool(
        "needs_body_copy" in tags
        or "url_text_unavailable" in tags
        or capture_quality.get("status") in {"보강 필요", "실패"}
    )


def compact_storage_quality_entry(entry: dict, *, include_ocr_status: bool = False) -> dict:
    """Return a compact, UI-safe storage quality row."""
    payload = {
        "ticker": entry.get("ticker"),
        "date": entry.get("date"),
        "file_name": entry.get("file_name"),
        "relative_path": entry.get("relative_path"),
        "summary": entry.get("summary"),
        "tags": entry.get("tags") or [],
    }
    if include_ocr_status:
        payload["ocr_status"] = ((entry.get("attachment") or {}).get("extraction_profile") or {}).get("ocr_status")
    else:
        payload["quality_status"] = (entry.get("capture_quality") or {}).get("status")
    return payload


def build_storage_quality_dashboard_payload(
    *,
    manifest_entries: list[dict],
    news_payload: dict,
    duplicate_count: int,
    as_of: str,
) -> dict:
    """Build the storage quality dashboard payload from already-loaded inputs."""
    active_entries = [entry for entry in manifest_entries if not is_archived_research_entry(entry)]
    news_counts = news_payload.get("filter_counts") or {}
    archived_count = sum(
        1
        for entry in manifest_entries
        if entry.get("archived") or entry.get("status") == "archived" or "archived" in (entry.get("tags") or [])
    )
    body_missing_entries = [
        entry
        for entry in active_entries
        if storage_quality_entry_needs_body(entry)
    ]
    ocr_needed_entries = [
        entry
        for entry in active_entries
        if storage_quality_entry_needs_ocr(entry)
    ]
    body_missing_count = len(body_missing_entries)
    ocr_needed_count = len(ocr_needed_entries)
    normal_count = max(0, len(manifest_entries) - archived_count - body_missing_count - ocr_needed_count)
    next_actions = []
    if body_missing_count or news_counts.get("needs_body"):
        next_actions.append("본문 보강 필요 자료는 원문 링크를 열어 사용자가 직접 요약/메모를 추가하세요.")
    if news_counts.get("unpromoted"):
        next_actions.append("미승격 뉴스는 투자 논거 반영, 시장일지 반영, 보류, 삭제 중 하나로 분류하세요.")
    if duplicate_count:
        next_actions.append("중복 의심 저장 데이터는 대표 자료만 Dossier 합성에 사용하세요.")
    if ocr_needed_count:
        next_actions.append("OCR 필요 자료는 Tesseract 연결 또는 텍스트/CSV 재업로드로 보강하세요.")
    if not next_actions:
        next_actions.append("저장 데이터 품질 경고가 낮습니다. 새 자료 유입 시 필터별로 점검하세요.")
    return {
        "status": "success",
        "module": "storage_quality_dashboard",
        "as_of": as_of,
        "manifest_count": len(manifest_entries),
        "normal_count": normal_count,
        "body_missing_count": body_missing_count,
        "ocr_needed_count": ocr_needed_count,
        "body_missing_items": [
            compact_storage_quality_entry(entry)
            for entry in body_missing_entries[:10]
        ],
        "ocr_needed_items": [
            compact_storage_quality_entry(entry, include_ocr_status=True)
            for entry in ocr_needed_entries[:10]
        ],
        "archived_count": archived_count,
        "legacy_or_duplicate_count": duplicate_count,
        "news_filter_counts": news_counts,
        "news_quality_issue_count": news_payload.get("quality_issue_count", 0),
        "news_unpromoted_count": news_payload.get("unpromoted_count", 0),
        "policy": {
            "news_body_storage": "metadata_only",
            "message": "뉴스/기사 원문 본문은 저장하지 않고 제목, 링크, 출처, 짧은 사용자 메모, 자체 분석만 저장합니다.",
        },
        "next_actions": next_actions[:6],
    }
