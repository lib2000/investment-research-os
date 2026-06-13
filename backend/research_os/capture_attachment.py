"""Capture attachment rendering and persistence helpers."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from re import split, sub
from typing import Protocol


class CaptureAttachmentRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def enum_or_str_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def prefix_capture_title(title: str, ticker: str, inference: str) -> str:
    labels = {
        "MACRO": "거시 전망",
        "SECTOR": "섹터 전망",
        "MARKET": "전체 시황",
        "POLICY": "정책/규제 전망",
        "RATES": "금리/물가 전망",
        "FLOWS": "수급/자금 흐름",
        "INBOX": "미분류 자료",
    }
    label = labels.get(ticker)
    if not label:
        return title
    cleaned_title = title.strip() or "자동 캡처"
    if cleaned_title.startswith(label):
        return cleaned_title[:80]
    return f"{label}: {cleaned_title}"[:80]


def attachment_keyword_tokens(file_name: str | None) -> list[str]:
    stem = Path(str(file_name or "")).stem
    normalized = sub(r"[_\-\[\]{}()（）·,]+", " ", stem)
    tokens = [
        token.strip()
        for token in split(r"\s+", normalized)
        if len(token.strip()) >= 2
    ]
    return list(dict.fromkeys(tokens))[:20]


def attachment_theme_candidates(text: str) -> list[dict]:
    lowered = text.lower()
    theme_rules = [
        (
            "kosdaq",
            "코스닥",
            ["코스닥", "kosdaq"],
            "코스닥 시장 정책/수급/상장기업 전반에 영향을 줄 수 있는 자료입니다.",
        ),
        (
            "small_mid_cap",
            "중견·중소형주",
            ["중견", "중소", "중소형", "스몰캡", "small cap", "mid cap"],
            "중견·중소형 성장주와 유동성 민감 종목을 우선 점검해야 합니다.",
        ),
        (
            "policy",
            "정책/규제",
            ["정책", "규제", "정부 정책", "거래소 정책", "제도 개선", "policy", "regulation"],
            "정책 변화가 밸류에이션, 거래대금, 상장 유지 요건에 미치는 영향을 확인해야 합니다.",
        ),
        (
            "market_structure",
            "시장 구조/유동성",
            ["옥석", "가리기", "유동성 공급", "상장폐지", "코스닥 활성화", "시장 구조", "market structure"],
            "시장 구조 변화와 종목 선별 강도 변화가 투자 논거에 반영될 수 있습니다.",
        ),
    ]
    matches: list[dict] = []
    for key, label, keywords, implication in theme_rules:
        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword.lower() in lowered
        ]
        if matched_keywords:
            matches.append(
                {
                    "key": key,
                    "label": label,
                    "matched_keywords": matched_keywords[:6],
                    "implication": implication,
                }
            )
    return matches


def render_attachment_signal_context(
    file_name: str | None,
    mime_type: str | None = None,
    extraction_note: str | None = None,
) -> str:
    tokens = attachment_keyword_tokens(file_name)
    theme_candidates = attachment_theme_candidates(
        " ".join(
            value
            for value in [file_name or "", mime_type or "", extraction_note or "", " ".join(tokens)]
            if value
        )
    )
    if not tokens and not theme_candidates:
        return ""
    lines = ["[첨부 신호 컨텍스트]"]
    if file_name:
        lines.append(f"파일명 기반 제목: {Path(file_name).stem}")
    if tokens:
        lines.append(f"파일명 키워드: {', '.join(tokens)}")
    if theme_candidates:
        lines.append(
            "관심 범위 후보: "
            + ", ".join(candidate["label"] for candidate in theme_candidates)
        )
        for candidate in theme_candidates:
            lines.append(f"- {candidate['label']}: {candidate['implication']}")
    if extraction_note:
        lines.append(f"본문 추출 상태: {extraction_note}")
    return "\n".join(lines)


def render_investment_scope_context(scope: dict | None) -> str:
    if not scope:
        return ""
    theme_labels = [
        str(item.get("label"))
        for item in scope.get("theme_candidates", [])
        if item.get("label")
    ]
    interest_names = [
        str(item.get("company_name") or item.get("ticker"))
        for item in scope.get("matched_interest_tickers", [])
    ]
    sector_names = [
        str(item.get("name"))
        for item in scope.get("matched_interest_sectors", [])
        if item.get("name")
    ]
    holding_names = [
        str(item.get("company_name") or item.get("ticker"))
        for item in scope.get("matched_portfolio_holdings", [])
    ]
    if not any([theme_labels, interest_names, sector_names, holding_names]):
        return ""
    lines = ["[투자 반영 추론]"]
    if theme_labels:
        lines.append(f"관심 범위 후보: {', '.join(theme_labels)}")
    if interest_names:
        lines.append(f"관심종목 매칭: {', '.join(list(dict.fromkeys(interest_names))[:10])}")
    if sector_names:
        lines.append(f"관심섹터 매칭: {', '.join(list(dict.fromkeys(sector_names))[:10])}")
    if holding_names:
        lines.append(f"보유종목 매칭: {', '.join(list(dict.fromkeys(holding_names))[:10])}")
    lines.append(f"다음 조치: {scope.get('next_action') or '원문 확인 후 투자 논거에 반영'}")
    return "\n".join(lines)


def render_research_capture_markdown(
    captured_item: CapturedResearchItem,
    raw_content: str,
    storage_date: date,
    attachment_info: dict | None = None,
) -> str:
    tags = ", ".join(captured_item.tags) or "none"
    attachment_section = ""
    if attachment_info:
        attachment_section = f"""
## 첨부 파일

- 파일명: {attachment_info.get("file_name") or "n/a"}
- MIME: {attachment_info.get("mime_type") or "n/a"}
- 크기: {attachment_info.get("size") or 0} bytes
- 저장 경로: {attachment_info.get("relative_path") or "n/a"}
- 텍스트 추출: {attachment_info.get("text_extraction") or "n/a"}
"""
    return f"""---
ticker: {captured_item.ticker}
type: research-capture
date: {storage_date.isoformat()}
module: research_quick_capture
source_type: {enum_or_str_value(captured_item.source_type)}
confidence: {captured_item.confidence}
tags: {tags}
---

# {captured_item.ticker} 투자 정보 캡처: {captured_item.title}

## 요약

{captured_item.summary}

## 출처

- 유형: {enum_or_str_value(captured_item.source_type)}
- URL: {captured_item.source_url or "n/a"}
- 기준 시점: {captured_item.as_of or storage_date.isoformat()}
- 신뢰도: {captured_item.confidence:.0%}
- 태그: {tags}
{attachment_section}

## 원문

{raw_content}
"""


def save_capture_attachment(
    runtime: CaptureAttachmentRuntime,
    vault_dir: Path,
    ticker: str,
    storage_date: date,
    request,
    settings=None,
) -> dict | None:
    file_bytes = runtime.decode_attachment_base64(request.file_content_base64)
    if file_bytes is None:
        return None

    safe_ticker = runtime.normalize_ticker(ticker)
    attachments_dir = vault_dir / safe_ticker / "_attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%H%M%S")
    safe_name = runtime.safe_attachment_file_name(request.file_name)
    attachment_path = attachments_dir / f"{safe_ticker}-research-attachment-{storage_date.isoformat()}-{timestamp}-{safe_name}"
    attachment_path.write_bytes(file_bytes)

    extraction = runtime.extract_uploaded_file_text(
        file_bytes,
        request.file_name,
        request.file_mime_type,
        source_path=attachment_path,
    )
    extracted_text = extraction.get("extracted_text") or ""
    extraction_note = extraction.get("text_extraction") or (
        "본문 텍스트 추출 포함"
        if request.raw_content.strip()
        else "원본 첨부만 저장됨"
    )
    fallback_context = render_attachment_signal_context(
        request.file_name,
        request.file_mime_type,
        extraction_note,
    )
    investment_scope = (
        runtime.infer_capture_investment_scope(
            "\n\n".join(
                value
                for value in [
                    request.raw_content,
                    fallback_context,
                    extracted_text,
                ]
                if value
            ),
            settings,
        )
        if settings is not None
        else {}
    )

    relative_path = attachment_path.relative_to(vault_dir).as_posix()
    return {
        "file_name": request.file_name or safe_name,
        "mime_type": request.file_mime_type or "application/octet-stream",
        "size": len(file_bytes),
        "declared_size": request.file_size,
        "relative_path": relative_path,
        "text_extraction": extraction_note,
        "extracted_text": extracted_text,
        "document_type": extraction.get("document_type"),
        "extraction_quality": extraction.get("extraction_quality"),
        "extraction_char_count": extraction.get("extraction_char_count"),
        "extraction_preview": extraction.get("extraction_preview"),
        "extraction_warnings": extraction.get("extraction_warnings") or [],
        "extraction_profile": extraction.get("extraction_profile") or {},
        "fallback_analysis_context": fallback_context,
        "inferred_investment_scope": investment_scope,
    }


def render_attachment_context(request: AutoResearchCaptureRequest, attachment_info: dict | None) -> str:
    if not attachment_info:
        return ""
    lines = [
        "[첨부 파일]",
        f"파일명: {attachment_info.get('file_name') or request.file_name or 'n/a'}",
        f"MIME: {attachment_info.get('mime_type') or request.file_mime_type or 'n/a'}",
        f"크기: {attachment_info.get('size') or request.file_size or 0} bytes",
        f"저장 경로: {attachment_info.get('relative_path') or 'n/a'}",
        f"문서 유형: {attachment_info.get('document_type') or 'n/a'}",
        f"추출 품질: {attachment_info.get('extraction_quality') or 'n/a'}",
        f"텍스트 추출: {attachment_info.get('text_extraction') or '원본 첨부만 저장됨'}",
    ]
    extraction_profile = attachment_info.get("extraction_profile") or {}
    if extraction_profile:
        lines.extend(
            [
                f"분석 활용도: {extraction_profile.get('analysis_readiness') or 'n/a'}",
                f"추출 구조: 본문 {extraction_profile.get('char_count') or 0}자, 줄 {extraction_profile.get('line_count') or 0}개, 숫자 토큰 {extraction_profile.get('numeric_token_count') or 0}개",
                f"권장 조치: {extraction_profile.get('next_action') or 'n/a'}",
            ]
        )
    fallback_context = (attachment_info.get("fallback_analysis_context") or "").strip()
    if fallback_context:
        lines.extend(["", fallback_context])
    investment_scope_context = render_investment_scope_context(
        attachment_info.get("inferred_investment_scope")
    )
    if investment_scope_context:
        lines.extend(["", investment_scope_context])
    for warning in attachment_info.get("extraction_warnings") or []:
        lines.append(f"추출 경고: {warning}")
    extracted_text = (attachment_info.get("extracted_text") or "").strip()
    if extracted_text:
        lines.extend(["", "[첨부 본문 추출]", extracted_text])
    return "\n".join(lines)


def capture_preview_text(value: str | None, max_chars: int = 4000) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}\n\n[미리보기는 앞부분 {max_chars:,}자만 표시합니다. 전체 원문은 저장 데이터에 보관했습니다.]"
