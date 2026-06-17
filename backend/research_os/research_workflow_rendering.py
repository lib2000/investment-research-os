"""Rendering and signal helpers for research workflow files."""

from __future__ import annotations

from datetime import date


def workflow_material_excerpt(value: str | None, limit: int = 900) -> str:
    compact = " ".join((value or "").split())
    if not compact:
        return "입력 자료 없음"
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


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


def render_earnings_filing_note_markdown(response: dict, storage_date: date) -> str:
    model_updates = "\n".join(
        f"- {item['item']}: {item['model_action']} (근거: {item['signal']})"
        for item in response.get("model_updates", [])
    )
    file_processing = response.get("file_processing") or {}
    file_section = render_file_processing_markdown(file_processing)
    note_sections = "\n\n".join(f"## {section['title']}\n\n{section['body']}" for section in response.get("note_draft", []))
    open_questions = "\n".join(f"- {item}" for item in response.get("open_questions", []))
    next_actions = "\n".join(f"- {item}" for item in response.get("next_actions", []))
    return f"""---
ticker: {response.get('ticker')}
type: earnings-filing-note
date: {storage_date.isoformat()}
module: earnings_filing_note
persona: Buy-Side 모델 업데이트 애널리스트
---

# {response.get('company_name')} 어닝 콜/공시 기반 노트 초안

## 모델 업데이트 항목

{model_updates}

## 첨부 파일 처리

{file_section}

{note_sections}

## 미확인 질문

{open_questions}

## 다음 액션

{next_actions}
"""


def render_lp_report_staging_markdown(response: dict, storage_date: date) -> str:
    valuation = "\n".join(f"- {item}" for item in response.get("valuation_template_output", []))
    valuation_rows = "\n".join(
        f"| {item.get('line_item')} | {item.get('input_status')} | {item.get('model_action')} | {item.get('lp_note')} |"
        for item in response.get("valuation_template_rows", [])
    )
    staging = "\n".join(f"- {item}" for item in response.get("staging_checklist", []))
    risks = "\n".join(f"- {item}" for item in response.get("lp_risk_flags", []))
    draft = "\n\n".join(f"## {section['title']}\n\n{section['body']}" for section in response.get("lp_report_draft", []))
    file_processing = response.get("file_processing") or {}
    file_section = render_file_processing_markdown(file_processing)
    return f"""---
type: lp-report-staging
date: {storage_date.isoformat()}
module: gp_lp_staging
fund_name: {response.get('fund_name')}
---

# {response.get('fund_name')} LP 보고 스테이징

## GP 패키지 요약

{response.get('gp_package_summary')}

## 밸류에이션 템플릿 결과

{valuation}

| 항목 | 입력 상태 | 모델 액션 | LP 보고 메모 |
| --- | --- | --- | --- |
{valuation_rows}

## 첨부 파일 처리

{file_section}

{draft}

## LP 보고 전 리스크 플래그

{risks}

## 스테이징 체크리스트

{staging}
"""
