"""Research workflow attachment and file-processing helpers."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from research_os.research_memory import ResearchStorageInfo


def workflow_material_excerpt(value: str | None, limit: int = 900) -> str:
    compact = " ".join((value or "").split())
    if not compact:
        return "입력 자료 없음"
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


def prepare_workflow_attachment(
    runtime,
    *,
    vault_dir: Path,
    storage_key: str,
    payload: dict,
    storage_date: date,
) -> dict | None:
    file_bytes = runtime.decode_attachment_base64(payload.get("file_content_base64"))
    if file_bytes is None:
        return None
    safe_key = runtime.normalize_ticker(storage_key) or "WORKFLOW"
    attachments_dir = vault_dir / safe_key / "_attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    safe_name = runtime.safe_attachment_file_name(payload.get("file_name"))
    timestamp = datetime.now().strftime("%H%M%S")
    attachment_path = attachments_dir / f"{safe_key}-workflow-attachment-{storage_date.isoformat()}-{timestamp}-{safe_name}"
    attachment_path.write_bytes(file_bytes)
    extraction = runtime.extract_uploaded_file_text(
        file_bytes,
        payload.get("file_name"),
        payload.get("file_mime_type"),
        source_path=attachment_path,
    )
    return {
        "file_name": payload.get("file_name") or safe_name,
        "mime_type": payload.get("file_mime_type") or "application/octet-stream",
        "size": len(file_bytes),
        "relative_path": attachment_path.relative_to(vault_dir).as_posix(),
        "text_extraction": extraction.get("text_extraction"),
        "extracted_text": extraction.get("extracted_text") or "",
        "document_type": extraction.get("document_type"),
        "extraction_quality": extraction.get("extraction_quality"),
        "extraction_char_count": extraction.get("extraction_char_count"),
        "extraction_preview": extraction.get("extraction_preview"),
        "extraction_warnings": extraction.get("extraction_warnings") or [],
        "extraction_profile": extraction.get("extraction_profile") or {},
    }


def upsert_saved_workflow_rag_document(
    runtime,
    *,
    vault_dir: Path,
    storage: ResearchStorageInfo,
    storage_key: str,
    report_type: str,
    summary: str,
    markdown: str,
    tags: list[str] | None = None,
    source_confidence: float = 0.85,
    metadata: dict | None = None,
) -> dict:
    entry = {
        "ticker": runtime.normalize_ticker(storage_key) or "GENERAL",
        "type": report_type,
        "date": runtime.current_storage_date().isoformat(),
        "file_name": storage.file_name,
        "relative_path": storage.relative_path,
        "json_file_name": storage.json_file_name,
        "json_relative_path": storage.json_relative_path,
        "summary": summary,
        "title": storage.file_name,
        "source_confidence": source_confidence,
        "tags": tags or [],
        **(metadata or {}),
    }
    return runtime.upsert_research_memory_document(
        vault_dir=vault_dir,
        entry=entry,
        full_text=markdown,
    )


def infer_model_update_items(material_text: str) -> list[dict]:
    text = material_text.lower()
    rules = [
        ("매출", ["revenue", "sales", "매출", "수요", "주문"], "매출 성장률과 다음 분기 가이던스 가정을 재점검"),
        ("마진", ["margin", "gross margin", "operating margin", "마진", "원가"], "매출총이익률/영업이익률 가정 업데이트"),
        ("CAPEX", ["capex", "투자", "설비", "데이터센터", "전력"], "CAPEX와 감가상각, 관련 수혜/부담 항목 반영"),
        ("현금흐름", ["cash flow", "fcf", "현금흐름", "현금 소진", "free cash"], "FCF, 운전자본, 현금 소진 속도 업데이트"),
        ("가이던스", ["guidance", "outlook", "가이던스", "전망"], "회사 가이던스와 컨센서스 차이를 모델에 반영"),
        ("리스크", ["risk", "lawsuit", "regulation", "리스크", "규제", "소송"], "할인율, 목표 멀티플, 약세 시나리오 확률 조정"),
    ]
    updates = []
    for label, keywords, action in rules:
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            updates.append({
                "item": label,
                "signal": ", ".join(matched[:4]),
                "model_action": action,
                "status": "업데이트 필요",
            })
    if not updates:
        updates.append({
            "item": "핵심 가정",
            "signal": "명시적 수치 신호 부족",
            "model_action": "어닝 콜/공시 원문에서 매출, 마진, 현금흐름, 가이던스 수치를 보강",
            "status": "보강 필요",
        })
    return updates


def render_file_processing_markdown(file_processing: dict | None) -> str:
    if not file_processing:
        return "- 첨부 파일 없음"
    profile = file_processing.get("extraction_profile") or {}
    lines = [
        f"- 파일명: {file_processing.get('file_name')}",
        f"- 문서 유형: {file_processing.get('document_type') or '미확인'}",
        f"- 저장 경로: {file_processing.get('relative_path')}",
        f"- 추출 상태: {file_processing.get('text_extraction')}",
        f"- 추출 품질: {file_processing.get('extraction_quality') or '미평가'}",
        f"- 추출 본문 길이: {file_processing.get('extraction_char_count') or 0}자",
    ]
    if profile:
        lines.extend(
            [
                f"- 분석 활용도: {profile.get('analysis_readiness') or '미평가'}",
                f"- 구조 신호: 줄 {profile.get('line_count') or 0}개, 숫자 토큰 {profile.get('numeric_token_count') or 0}개, 표형 줄 {profile.get('table_like_line_count') or 0}개",
                f"- 권장 조치: {profile.get('next_action') or '미평가'}",
            ]
        )
        if profile.get("image_size") or profile.get("ocr_available") is not None:
            ocr_state = "사용 가능" if profile.get("ocr_available") else "사용 불가"
            lines.append(f"- 이미지/OCR: {profile.get('image_size') or '크기 미확인'} · OCR {ocr_state}")
        if profile.get("ocr_language"):
            lines.append(f"- OCR 언어: {profile.get('ocr_language')}")
    lines.extend(
        f"- 추출 경고: {warning}"
        for warning in (file_processing.get("extraction_warnings") or [])
    )
    return "\n".join(lines)
