"""Dossier synthesis payload and Markdown rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from research_os.dossier_text import (
    DOSSIER_FACT_TERMS,
    DOSSIER_NEGATIVE_TERMS,
    DOSSIER_POSITIVE_TERMS,
    add_dossier_signal,
    add_unique_text,
    clean_dossier_signal,
    is_dossier_noise_line,
    latest_verified_entries_for_dossier,
    line_has_any,
    plain_research_lines,
    representative_thesis_line,
)


class DossierSynthesisRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main during Dossier synthesis."""


def build_dossier_payload(runtime: DossierSynthesisRuntime, ticker: str, vault_dir: Path) -> dict:
    storage_date = runtime.current_storage_date()
    company_name = runtime.ticker_company_name(ticker)
    entries, duplicates = latest_verified_entries_for_dossier(
        ticker,
        vault_dir,
        read_manifest_fn=runtime.read_manifest,
        is_verified_manifest_entry_fn=runtime.is_verified_manifest_entry,
    )
    profile_focus = runtime.analysis_focus_for_ticker(ticker, None)
    watch_kpis = runtime.ticker_watch_kpis(ticker)
    consensus_facts: list[str] = []
    bull_thesis: list[str] = []
    bear_thesis: list[str] = []
    latest_changes: list[dict] = []
    confidence_values: list[float] = []
    tags: set[str] = set()

    for entry in entries[:30]:
        summary = str(entry.get("summary") or "")
        text = str(entry.get("_full_text") or summary)
        lines = [
            line
            for line in [summary, *plain_research_lines(text, limit=40)]
            if not is_dossier_noise_line(line)
        ]
        for tag in entry.get("tags") or []:
            tags.add(str(tag))
        confidence_values.append(runtime.clamp_confidence(entry.get("confidence") or entry.get("source_confidence")))
        latest_changes.append(
            {
                "date": entry.get("date"),
                "type": entry.get("type"),
                "file_name": entry.get("file_name"),
                "summary": summary,
                "confidence": entry.get("confidence") or entry.get("source_confidence"),
            }
        )
        for line in lines:
            has_bull_marker = "강세:" in line
            has_bear_marker = "약세:" in line
            if line_has_any(line, DOSSIER_FACT_TERMS) and not (has_bull_marker or has_bear_marker):
                fact = clean_dossier_signal(line, "generic")
                if fact:
                    add_unique_text(consensus_facts, fact, limit=8)
            if has_bull_marker or (line_has_any(line, DOSSIER_POSITIVE_TERMS) and not has_bear_marker):
                add_dossier_signal(bull_thesis, line, "bull", limit=6)
            if has_bear_marker or (line_has_any(line, DOSSIER_NEGATIVE_TERMS) and not has_bull_marker):
                add_dossier_signal(bear_thesis, line, "bear", limit=6)

    if not consensus_facts:
        for entry in entries[:6]:
            add_unique_text(consensus_facts, entry.get("summary"), limit=6)
    if not bull_thesis:
        add_unique_text(
            bull_thesis,
            f"{company_name}의 강세 논거는 {profile_focus}가 실제 수치와 신규 자료에서 반복 확인되는 경우입니다.",
        )
    if not bear_thesis:
        add_unique_text(
            bear_thesis,
            f"{company_name}의 약세 논거는 핵심 KPI 둔화, 마진 훼손, 경쟁 심화 또는 투자 심리 악화가 동시에 나타나는 경우입니다.",
        )

    cruxes = [
        f"{watch_kpis[0] if watch_kpis else '핵심 성장 KPI'}가 다음 데이터에서 개선 추세를 유지하는가?",
        "현재 밸류에이션이 성장률, 마진, 현금흐름 품질을 과도하게 선반영하고 있지 않은가?",
        "최근 입력 자료의 강세/약세 신호 중 실제 숫자로 확인 가능한 항목은 무엇인가?",
    ]
    observables = [
        f"{metric}: 다음 실적/공시/뉴스에서 방향성 확인"
        for metric in watch_kpis[:5]
    ]
    if not observables:
        observables = [
            "매출 성장률: 다음 실적에서 추세 확인",
            "마진 품질: 비용 구조와 가격 결정력 확인",
            "현금흐름: 투자 확대와 현금 소진 균형 확인",
        ]

    confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.65
    bull_summary = representative_thesis_line(
        bull_thesis,
        f"{company_name}의 강세 논거는 {profile_focus}가 실제 수치와 신규 자료에서 반복 확인되는 경우입니다.",
        mode="bull",
    )
    bear_summary = representative_thesis_line(
        bear_thesis,
        f"{company_name}의 약세 논거는 핵심 KPI 둔화, 마진 훼손, 경쟁 심화 또는 투자 심리 악화가 동시에 나타나는 경우입니다.",
        mode="bear",
    )
    thesis_summary = (
        f"{company_name}의 최신 Dossier는 {len(entries)}개 고유 저장 자료를 바탕으로 "
        f"{profile_focus}를 핵심 투자 논거로 추적합니다. "
        f"강세는 {bull_summary} / 약세는 {bear_summary}입니다."
    )
    invalidation_conditions = [
        "핵심 성장 KPI가 2개 분기 연속 약화",
        "기존 강세 논거를 뒷받침하던 수요·마진·현금흐름 지표가 동시에 후퇴",
        "새 자료의 부정 신호가 반복 입력되고 신뢰도 가중 평균이 70% 이상으로 상승",
    ]

    return {
        "ticker": ticker,
        "company_name": company_name,
        "date": storage_date.isoformat(),
        "source_count": len(entries),
        "duplicate_count": len(duplicates),
        "confidence": confidence,
        "tags": sorted(tags),
        "thesis_summary": thesis_summary,
        "consensus_facts": consensus_facts,
        "bull_thesis": bull_thesis,
        "bear_thesis": bear_thesis,
        "cruxes": cruxes,
        "observables": observables,
        "invalidation_conditions": invalidation_conditions,
        "latest_changes": latest_changes[:10],
        "duplicates": duplicates[:10],
    }


def build_insufficient_evidence_result(payload: dict) -> dict:
    """Return a displayable, non-persisted Dossier result when no sources qualify.

    ``build_dossier_payload`` intentionally has useful fallback language so a
    populated Dossier can still name its review questions.  That language must
    never become a saved thesis when the verified-source set is empty.
    """
    source_count = int(payload.get("source_count") or 0)
    if source_count > 0:
        raise ValueError("근거가 있는 Dossier에는 근거 부족 결과를 만들 수 없습니다.")

    return {
        "status": "insufficient_evidence",
        "module": "dossier_synthesis",
        "ticker": payload.get("ticker"),
        "company_name": payload.get("company_name"),
        "date": payload.get("date"),
        "source_count": source_count,
        "duplicate_count": int(payload.get("duplicate_count") or 0),
        "confidence": None,
        "source_status": "insufficient",
        "saved": False,
        "review_gate_effect": "none",
        "summary": "Dossier 합성에 사용할 검증된 리서치 자료가 없습니다.",
        "thesis_summary": None,
        "consensus_facts": [],
        "bull_thesis": [],
        "bear_thesis": [],
        "cruxes": [],
        "observables": [],
        "invalidation_conditions": [],
        "latest_changes": [],
        "duplicates": payload.get("duplicates") or [],
        "missing_requirements": [
            "공식 공시·IR·실적 자료 또는 검증된 리서치 본문을 정보 입력에 저장",
            "티커와 원문 본문 추출 상태를 사람이 확인",
            "최소 1건의 적격 자료가 준비된 뒤 Dossier 합성 재실행",
        ],
        "next_actions": [
            "저장 데이터에서 원문과 티커 인증 상태를 확인하세요.",
            "공식 공시·IR·실적 자료를 정보 입력에 저장하고 본문 품질을 검토하세요.",
            "자료가 준비된 뒤에만 Dossier 합성을 다시 실행하세요.",
        ],
    }


def render_dossier_markdown(payload: dict) -> str:
    def bullet(items: list[str] | list[dict], empty: str = "표시할 항목이 없습니다.") -> str:
        if not items:
            return f"- {empty}"
        lines = []
        for item in items:
            if isinstance(item, dict):
                lines.append(
                    f"- {item.get('date') or '날짜 미확인'} · {item.get('type') or '자료'} · "
                    f"{item.get('summary') or item.get('file_name') or '요약 없음'}"
                )
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    return f"""---
ticker: {payload["ticker"]}
type: dossier-synthesis
date: {payload["date"]}
module: research_dossier_synthesis
---

# {payload["company_name"]} Dossier 합성 보고서

## 요약

{payload["thesis_summary"]}

- 고유 자료: {payload["source_count"]}개
- 중복 제외: {payload["duplicate_count"]}개
- 합성 신뢰도: {payload["confidence"]:.0%}
- 태그: {", ".join(payload["tags"]) or "없음"}

## 합의된 사실

{bullet(payload["consensus_facts"])}

## 강세 논거

{bullet(payload["bull_thesis"])}

## 약세 논거

{bullet(payload["bear_thesis"])}

## 핵심 쟁점

{bullet(payload["cruxes"])}

## 관찰 가능한 트리거

{bullet(payload["observables"])}

## 무효화 조건

{bullet(payload["invalidation_conditions"])}

## 최근 변화

{bullet(payload["latest_changes"])}
"""
