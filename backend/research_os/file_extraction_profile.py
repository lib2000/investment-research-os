"""Attachment text extraction quality profile helpers."""

from __future__ import annotations

from re import findall, search


def build_file_extraction_profile(
    document_type: str,
    extracted_text: str,
    extraction_note: str,
    warnings: list[str],
) -> dict:
    text = (extracted_text or "").strip()
    note = extraction_note or ""
    char_count = len(text)
    lines = [line for line in text.splitlines() if line.strip()]
    line_count = len(lines)
    numeric_token_count = len(findall(r"[-+]?\d[\d,]*(?:\.\d+)?%?", text))
    table_like_line_count = sum(
        1
        for line in lines
        if "\t" in line or "|" in line or line.count(",") >= 3
    )
    used_ocr = "OCR" in note.upper()
    truncated = "앞부분" in text or "앞부분" in note
    warning_count = len([warning for warning in warnings if warning])
    has_korean = bool(search(r"[가-힣]", text))
    has_english = bool(search(r"[A-Za-z]", text))
    quality_drivers: list[str] = []

    if char_count >= 2_000 and warning_count == 0:
        readiness = "높음"
        use_case = "본문을 투자 논거, RAG 검색, 리포트 합성에 바로 사용할 수 있습니다."
        quality = 0.92
        quality_drivers.append("본문 길이 충분")
    elif char_count >= 600:
        readiness = "보통"
        use_case = "핵심 문장 중심으로 분석 가능하며, 표·숫자 누락 여부를 확인하면 좋습니다."
        quality = 0.78
        quality_drivers.append("본문 일부 확보")
    elif char_count > 0:
        readiness = "낮음"
        use_case = "요약 신호로만 제한 활용하고 원문 확인 또는 추가 입력을 병행하세요."
        quality = 0.55
        quality_drivers.append("본문 짧음")
    else:
        readiness = "본문 없음"
        use_case = "파일명과 메타데이터만 분류에 사용됩니다."
        quality = 0.35
        quality_drivers.append("본문 없음")

    if document_type == "Excel 문서" and table_like_line_count:
        quality = max(quality, 0.86)
        readiness = "높음" if char_count >= 600 else "보통"
        use_case = "표 형태의 수치와 항목을 추출했으므로 피어 비교, 포트폴리오, KPI 정리에 활용할 수 있습니다."
        quality_drivers.append("표형 데이터 감지")
    elif document_type == "텍스트/표 문서" and table_like_line_count >= 2:
        quality = max(quality, 0.74)
        readiness = "보통" if char_count >= 40 else readiness
        use_case = "짧은 표형 텍스트라도 수치·보유종목·KPI 후보 추출에 활용할 수 있습니다."
        quality_drivers.append("표형 텍스트 감지")
    elif document_type in {"Word 문서", "PowerPoint 문서"} and char_count >= 600:
        use_case = "문장형 리서치 메모와 발표자료 요약, 핵심 논거 추출에 활용할 수 있습니다."
        quality_drivers.append("문장형 문서")
    elif document_type in {"Word 문서", "PowerPoint 문서"} and char_count >= 50 and numeric_token_count >= 2:
        quality = max(quality, 0.68)
        readiness = "보통"
        use_case = "짧은 문서지만 핵심 문장과 수치가 있어 투자 메모 초안과 체크포인트 생성에 활용할 수 있습니다."
        quality_drivers.append("짧은 문장형 KPI 메모")
    elif document_type == "PDF" and char_count >= 600:
        quality_drivers.append("PDF 본문 추출")
    elif document_type in {"PDF", "텍스트/표 문서", "Word 문서", "PowerPoint 문서"} and char_count >= 120 and has_korean:
        quality = max(quality, 0.64)
        readiness = "보통"
        use_case = "짧은 본문이지만 종목·산업 메모로 활용 가능하며, 추가 수치가 있으면 리포트 논거로 확장할 수 있습니다."
        quality_drivers.append("짧은 문장형 투자 메모")
    if numeric_token_count >= 5:
        quality_drivers.append("수치 신호 충분")
    if used_ocr and quality > 0.82:
        quality = 0.82
        quality_drivers.append("OCR 결과라 보수 판정")
    if truncated:
        quality = min(quality, 0.82)
        quality_drivers.append("본문 길이 제한")
    if warning_count:
        quality = min(quality, 0.72)
        quality_drivers.append("추출 경고 존재")

    quality_label = "좋음" if quality >= 0.85 else "보통" if quality >= 0.6 else "확인 필요"
    next_action = "바로 저장/RAG 반영 가능"
    if warning_count or char_count < 600:
        next_action = "원문 미리보기에서 핵심 수치·표·본문 누락 여부 확인"
    if not char_count:
        next_action = "OCR 가능 파일 또는 본문 텍스트를 추가 입력"

    return {
        "quality_label": quality_label,
        "analysis_readiness": readiness,
        "use_case": use_case,
        "next_action": next_action,
        "char_count": char_count,
        "line_count": line_count,
        "numeric_token_count": numeric_token_count,
        "table_like_line_count": table_like_line_count,
        "has_korean": has_korean,
        "has_english": has_english,
        "used_ocr": used_ocr,
        "truncated": truncated,
        "warning_count": warning_count,
        "quality_drivers": quality_drivers,
        "recommended_quality": round(quality, 2),
    }