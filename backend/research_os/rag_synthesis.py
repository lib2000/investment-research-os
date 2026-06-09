"""Helpers for search-wide RAG synthesis reports.

The FastAPI route owns authentication, persistence, and DB updates; this module
keeps the query synthesis text shaping pure and backend-testable.
"""

from __future__ import annotations

from datetime import date
from re import DOTALL, IGNORECASE, findall, sub
from typing import Any

from research_os.models import InvestmentThesis, WatchItem


REPORT_TYPE = "rag-query-synthesis"


def _unique_text(values: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    for value in values:
        cleaned = " ".join(str(value or "").split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append(cleaned)
        if len(selected) >= limit:
            break
    return selected


def _clean_text(value: Any) -> str:
    cleaned = str(value or "")
    cleaned = sub(r"---.*?---", " ", cleaned, flags=DOTALL)
    cleaned = sub(r"이 문장은 중복 감지와 RAG 즉시 색인 테스트용이다[:：]?.*?(?=(?:[.!?。]|$))", " ", cleaned)
    cleaned = sub(r"자동화 검증 메모[:：]?", " ", cleaned)
    cleaned = sub(r"처리:\s*PDF 파일은 서버에서 본문 텍스트 추출을 시도하고,? 원본 PDF도 함께 저장합니다\.?", " ", cleaned)
    cleaned = sub(r"처리:\s*파일은 서버에서 본문 텍스트 추출을 시도하고,? 원본 PDF도 함께 저장합니다\.?", " ", cleaned)
    cleaned = sub(r"강세는\s+강세는", "강세는", cleaned)
    cleaned = sub(r"약세는\s+약세는", "약세는", cleaned)
    cleaned = sub(r"#+\s*", " ", cleaned)
    cleaned = sub(r"\b(md|pdf|json)\b\s*", " ", cleaned, flags=IGNORECASE)
    cleaned = sub(r"\b(OTHER|OFFICIAL_FILING|RESEARCH_MEMORY)\s*/\s*[^:]+:\s*", " ", cleaned)
    cleaned = sub(r"\bDataSourceType\.[A-Za-z_]+", " ", cleaned)
    cleaned = sub(r"\[첨부 파일\]\s*", " ", cleaned)
    cleaned = sub(r"파일명:\s*[^.。!?\\n\\r]{1,120}", " ", cleaned)
    cleaned = sub(r"MIME:\s*[^\\n\\r]+", " ", cleaned)
    cleaned = sub(r"크기:\s*\d+\s*bytes", " ", cleaned)
    cleaned = sub(r"저장 경로:\s*\S+", " ", cleaned)
    cleaned = sub(r"tags:\s*[^\\n\\r]+", " ", cleaned, flags=IGNORECASE)
    cleaned = sub(r"\s+", " ", cleaned).strip(" -·")
    return cleaned


def _skip_sentence(value: str) -> bool:
    lowered = str(value or "").casefold()
    skip_terms = [
        "테스트용",
        "rag 즉시 색인 테스트",
        "중복 감지",
        "syntax",
        "placeholder",
        "본문 텍스트 추출",
        "원본 pdf",
        "저장 경로",
        "mime:",
        "파일명:",
        "직접 매칭된 신호 없음",
        "계속 모니터링",
        "추적 항목 신호",
        "판단 근거 판단:",
        "확신도:",
        "latest_thesis_snapshot",
        "주입된 데이터 컨텍스트",
        "리서치 메모리 /",
        "연결 가능한 저장 리포트",
        "매매 전략:",
        "손절",
        "목표가",
        "분할 진입",
    ]
    return any(term in lowered for term in skip_terms)


def _compact_sentence(text: Any, max_len: int = 180) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    pieces = [piece.strip() for piece in findall(r"[^.!?。]+[.!?。]?", cleaned) if piece.strip()]
    for piece in pieces:
        if _skip_sentence(piece):
            continue
        if 35 <= len(piece) <= max_len:
            return piece
    return f"{cleaned[: max_len - 3]}..."


def _document_text(document: dict[str, Any]) -> str:
    summary = _clean_text(document.get("summary"))
    excerpt = _clean_text(document.get("content_excerpt"))
    title = _clean_text(document.get("title") or document.get("source_file_name"))
    pieces = [summary, excerpt if len(summary) < 90 else "", title if not summary else ""]
    return " ".join(piece for piece in pieces if piece)


def _select_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded_report_types = {
        REPORT_TYPE,
        "smart-trade-setup",
        "research-checklist",
        "chart-analysis",
        "portfolio-risk-scan",
        "reinforcement-portfolio-optimizer",
        "thesis-impact-review",
    }
    source_documents = [
        document
        for document in documents
        if str(document.get("report_type") or "").strip().lower() not in excluded_report_types
    ]
    if source_documents:
        documents = source_documents
    full_matches = [
        document
        for document in documents
        if str(document.get("match_strength") or "").strip() in {"완전", "전체"}
    ]
    if len(full_matches) < 2:
        return documents
    focus_tickers = {
        str(document.get("ticker") or "").upper()
        for document in full_matches
        if str(document.get("ticker") or "").upper() not in {"", "GENERAL", "MARKET", "SEARCH"}
    }
    if not focus_tickers:
        return full_matches
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for document in documents:
        ticker = str(document.get("ticker") or "").upper()
        report_type = str(document.get("report_type") or "").lower()
        if ticker not in focus_tickers or report_type == REPORT_TYPE:
            continue
        key = str(document.get("document_id") or document.get("source_relative_path") or document.get("source_file_name"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(document)
    return selected or full_matches


def _extract_lines(documents: list[dict[str, Any]], query_terms: list[str]) -> list[str]:
    lines: list[str] = []
    for document in documents:
        text = _document_text(document)
        for part in findall(r"[^.!?\n\r。]+[.!?。]?", text):
            cleaned = _clean_text(" ".join(part.split()))
            if len(cleaned) < 12 or _skip_sentence(cleaned):
                continue
            if query_terms and not any(term in cleaned.casefold() for term in query_terms):
                continue
            ticker = document.get("ticker") or "범위 미확인"
            lines.append(f"{ticker}: {_compact_sentence(cleaned, 180)}")
    return _unique_text(lines, 10)


def _filter_theme_lines(
    documents: list[dict[str, Any]],
    keywords: list[str],
    *,
    limit: int = 6,
    query_terms: list[str] | None = None,
) -> list[str]:
    selected: list[str] = []
    lowered_keywords = [keyword.casefold() for keyword in keywords]
    for document in documents:
        text = _document_text(document)
        if _skip_sentence(text):
            continue
        for part in findall(r"[^.!?\n\r。]+[.!?。]?", text):
            cleaned = _clean_text(part)
            if len(cleaned) < 12 or _skip_sentence(cleaned):
                continue
            lowered = cleaned.casefold()
            if not any(keyword in lowered for keyword in lowered_keywords):
                continue
            if query_terms and not any(term in lowered for term in query_terms):
                continue
            selected.append(f"{document.get('ticker') or '범위 미확인'}: {_compact_sentence(cleaned, 190)}")
    return _unique_text(selected, limit)


def rag_synthesis_storage_key(documents: list[dict[str, Any]]) -> str:
    tickers = [
        str(document.get("ticker") or "").upper()
        for document in documents
        if str(document.get("ticker") or "").upper() not in {"", "GENERAL", "MARKET", "SEARCH"}
    ]
    unique_tickers = sorted(set(tickers))
    if len(unique_tickers) == 1:
        return unique_tickers[0]
    if not unique_tickers:
        return "MARKET"
    return "SEARCH"


def build_rag_query_synthesis_payload(*, query: str, search_result: dict[str, Any], report_date: date) -> dict[str, Any]:
    candidate_documents = [
        document
        for document in list(search_result.get("documents") or [])
        if str(document.get("report_type") or "").lower() != REPORT_TYPE
    ]
    documents = _select_documents(candidate_documents)
    query_terms = [term.casefold() for term in findall(r"[A-Za-z0-9가-힣]{2,}", query)][:8]
    tickers = sorted(
        {
            str(document.get("ticker") or "GENERAL").upper()
            for document in documents
            if str(document.get("ticker") or "GENERAL").upper() not in {"UNKNOWN"}
        }
    )
    tags = _unique_text(
        [str(tag) for document in documents for tag in (document.get("tags") or []) if str(tag).strip()],
        14,
    )
    confidence_values = [float(document.get("source_confidence") or document.get("confidence") or 0.7) for document in documents]
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    consensus_facts = _extract_lines(documents, query_terms)
    if len(consensus_facts) < 3:
        consensus_facts = _unique_text(
            [
                f"{document.get('ticker') or '범위 미확인'}: {_compact_sentence(_clean_text(_document_text(document)), 180)}"
                for document in documents[:8]
            ],
            8,
        )
    bull_thesis = _filter_theme_lines(
        documents,
        ["성장", "수요", "매출", "마진", "개선", "강세", "상회", "수출", "계약", "positive", "bull"],
        query_terms=query_terms,
    )
    bear_thesis = _filter_theme_lines(
        documents,
        ["리스크", "둔화", "압박", "하락", "약세", "비용", "경쟁", "감소", "불확실", "risk", "bear"],
        query_terms=query_terms,
    )
    cruxes = _unique_text(
        [
            f"{query} 판단을 좌우하는 쟁점: {_compact_sentence(_document_text(document), 160)}"
            for document in documents[:6]
            if not _skip_sentence(_document_text(document))
            and any(term in _document_text(document).casefold() for term in query_terms)
        ],
        6,
    )
    observable_keywords = ["매출", "수출", "마진", "환율", "수요", "실적", "가이던스", "수급", "가격", "금리", "계약", "리스크"]
    observables = _unique_text(
        [keyword + " 변화 추적" for keyword in observable_keywords if any(keyword in _document_text(document) for document in documents)],
        8,
    )
    next_actions = [
        "가장 관련도 높은 문서를 열어 원문 수치와 날짜를 확인하세요.",
        "공통 사실과 반대 논거가 충돌하는 지점을 팀 리포트 또는 매매 전략에 반영하세요.",
        "관찰 가능한 KPI가 새로 들어오면 같은 검색어로 합성을 다시 실행해 변화만 비교하세요.",
    ]
    summary = (
        f"'{query}' 검색 후보 {len(candidate_documents)}개 중 관련도가 높은 {len(documents)}개를 합성했습니다. "
        f"주요 범위는 {', '.join(tickers[:6]) if tickers else '시장/섹터 자료'}이며, "
        "공통 사실과 강세/약세 논거를 분리해 후속 투자 판단에 사용할 수 있습니다."
    )
    source_documents = [
        {
            "ticker": document.get("ticker") or "GENERAL",
            "title": document.get("title") or document.get("source_file_name"),
            "report_type": document.get("report_type"),
            "source_file_name": document.get("source_file_name"),
            "source_relative_path": document.get("source_relative_path"),
            "source_date": document.get("source_date"),
            "quality_score": document.get("quality_score"),
            "relevance_score": document.get("relevance_score"),
            "match_strength": document.get("match_strength"),
            "summary": _clean_text(document.get("summary") or document.get("content_excerpt") or ""),
        }
        for document in documents
    ]
    return {
        "query": query,
        "date": report_date.isoformat(),
        "source_count": len(documents),
        "candidate_count": len(candidate_documents),
        "grouped_count": min(int(search_result.get("grouped_count") or len(documents)), len(documents)),
        "tickers": tickers,
        "tags": tags,
        "confidence": max(0.0, min(confidence, 1.0)),
        "summary": summary,
        "consensus_facts": consensus_facts,
        "bull_thesis": bull_thesis,
        "bear_thesis": bear_thesis,
        "cruxes": cruxes,
        "observables": observables or ["다음 자료 입력 때 확인할 KPI를 자동 추출할 수 있도록 관련 수치가 포함된 메모를 추가하세요."],
        "next_actions": next_actions,
        "source_documents": source_documents,
    }


def render_rag_query_synthesis_markdown(payload: dict[str, Any]) -> str:
    def bullet(items: list[str], empty: str = "표시할 항목이 없습니다.") -> str:
        if not items:
            return f"- {empty}"
        return "\n".join(f"- {item}" for item in items)

    source_lines = [
        f"- {item.get('ticker') or 'GENERAL'} · {item.get('source_date') or '날짜 없음'} · "
        f"{item.get('report_type') or '자료'} · {item.get('title') or item.get('source_file_name') or '제목 없음'}"
        for item in payload.get("source_documents", [])[:15]
    ]
    return f"""---
ticker: {rag_synthesis_storage_key(payload.get("source_documents", []))}
type: {REPORT_TYPE}
date: {payload["date"]}
module: rag_query_synthesis
query: {payload["query"]}
---

# 저장 데이터 검색 합성 보고서

## 검색어

{payload["query"]}

## 요약

{payload["summary"]}

- 원천 문서: {payload["source_count"]}개
- 검색 후보: {payload.get("candidate_count", payload["source_count"])}개
- 중복 묶음 반영 후: {payload["grouped_count"]}개
- 합성 신뢰도: {payload["confidence"]:.0%}
- 관련 범위: {", ".join(payload["tickers"]) or "시장/섹터"}
- 태그: {", ".join(payload["tags"]) or "없음"}

## 합의된 사실

{bullet(payload["consensus_facts"])}

## 강세 논거

{bullet(payload["bull_thesis"])}

## 약세 논거

{bullet(payload["bear_thesis"])}

## 핵심 쟁점

{bullet(payload["cruxes"])}

## 앞으로 확인할 관찰 지표

{bullet(payload["observables"])}

## 다음 액션

{bullet(payload["next_actions"])}

## 사용한 저장 데이터

{chr(10).join(source_lines) if source_lines else "- 사용한 저장 데이터가 없습니다."}
"""


def build_rag_query_synthesis_thesis(
    ticker: str,
    payload: dict[str, Any],
    *,
    watch_kpis: list[str],
) -> tuple[InvestmentThesis, list[WatchItem]]:
    thesis = InvestmentThesis(
        ticker=ticker,
        thesis=payload["summary"],
        time_horizon="저장 데이터 검색 합성 기반 상시 업데이트",
        bull_triggers=payload.get("bull_thesis", [])[:8],
        bear_triggers=payload.get("bear_thesis", [])[:8],
        invalidation_conditions=payload.get("cruxes", [])[:8],
        watch_kpis=watch_kpis,
        valuation_assumptions={
            "method": "저장 데이터 검색 합성",
            "query": payload.get("query"),
            "confidence": payload.get("confidence"),
            "source_count": payload.get("source_count"),
            "candidate_count": payload.get("candidate_count"),
        },
        last_updated=payload.get("date"),
    )
    watch_items = [
        WatchItem(
            ticker=ticker,
            metric=str(item).split(":")[0].replace(" 변화 추적", "").strip() or "관찰 지표",
            condition=str(item),
            action="정보 입력, 시장일지, 실적 분석에서 새 자료가 들어오면 같은 검색어로 재합성",
            priority="medium",
        )
        for item in payload.get("observables", [])[:6]
    ]
    return thesis, watch_items
