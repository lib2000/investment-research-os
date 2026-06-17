"""Thesis impact scoring and rendering helpers."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from . import thesis_signal_words
from .models import (
    InjectedDataPoint,
    InvestmentThesis,
    ThesisImpact,
    ThesisImpactFinding,
    ThesisImpactResponse,
    WatchItem,
    WatchItemSignal,
)


def translate_impact_label(impact: ThesisImpact) -> str:
    labels = {
        ThesisImpact.STRENGTHENS: "강화",
        ThesisImpact.WEAKENS: "약화",
        ThesisImpact.MIXED: "혼합",
        ThesisImpact.NEUTRAL: "중립",
        ThesisImpact.INSUFFICIENT_DATA: "데이터 부족",
    }
    return labels.get(impact, impact.value)


def translate_quality_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def translate_priority_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def translate_severity_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def extract_manifest_theses_and_watch_items(
    runtime: SimpleNamespace,
    ticker: str,
    vault_dir,
) -> tuple[list[InvestmentThesis], list[WatchItem]]:
    try:
        db_theses, db_watch_items = runtime.read_ticker_thesis_context(vault_dir, ticker)
        if db_theses:
            return db_theses, db_watch_items
    except Exception:
        pass

    entries = [
        entry for entry in runtime.read_manifest(vault_dir) if entry.get("ticker") == ticker
    ]
    theses = [
        InvestmentThesis(**entry["investment_thesis"])
        for entry in entries
        if entry.get("investment_thesis")
    ]
    watch_items = [
        WatchItem(**watch_item)
        for entry in entries
        for watch_item in entry.get("watch_items", [])
        if isinstance(watch_item, dict)
    ]
    return theses, watch_items

def clamp_confidence(value: float | None) -> float:
    if value is None:
        return 0.7
    return max(0.0, min(1.0, float(value)))


def average_source_confidence(new_data: list[InjectedDataPoint]) -> float:
    if not new_data:
        return 0.0
    return round(
        sum(clamp_confidence(item.confidence) for item in new_data) / len(new_data),
        2,
    )


def confidence_weight_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "높은 가중치"
    if confidence >= 0.7:
        return "보통 이상의 가중치"
    if confidence >= 0.5:
        return "제한적 가중치"
    return "낮은 가중치"


def confidence_prompt_instruction(confidence: float) -> str:
    pct = confidence * 100
    if confidence >= 0.85:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거와 비교할 때 "
            "상대적으로 높은 가중치를 두고, 강세/약세 시나리오 변화 가능성을 적극 반영하세요."
        )
    if confidence >= 0.7:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거와 비교할 때 "
            "의미 있는 가중치를 두되, 추가 확인이 필요한 부분은 별도로 표시하세요."
        )
    if confidence >= 0.5:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거 평가에 반영하되 "
            "결론은 부분 가중치로 제한하고 교차 검증 필요성을 함께 제시하세요."
        )
    return (
        f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거를 바로 바꾸기보다 "
        "관찰 신호로만 취급하고, 결론의 확신도를 낮게 유지하세요."
    )


def format_weighted_evidence(item: InjectedDataPoint) -> str:
    confidence = clamp_confidence(item.confidence)
    return (
        f"[신뢰도 {confidence:.0%} · {confidence_weight_label(confidence)}] "
        f"{item.label}: {item.value}"
    )


def confidence_adjusted_finding_confidence(
    impact: ThesisImpact,
    source_confidence: float,
) -> float:
    if impact == ThesisImpact.INSUFFICIENT_DATA:
        return round(min(0.45, max(0.25, source_confidence * 0.55)), 2)
    if impact == ThesisImpact.NEUTRAL:
        base = 0.52
    elif impact == ThesisImpact.MIXED:
        base = 0.64
    else:
        base = 0.72
    return round(max(0.25, min(0.92, base * (0.55 + source_confidence * 0.55))), 2)


def evaluate_thesis_impact(
    ticker: str,
    new_data: list[InjectedDataPoint],
    theses: list[InvestmentThesis],
    watch_items: list[WatchItem],
) -> ThesisImpactResponse:
    source_confidence = average_source_confidence(new_data)
    prompt_instruction = confidence_prompt_instruction(source_confidence)
    evidence = [format_weighted_evidence(item) for item in new_data]
    combined_text = " ".join(evidence)
    has_positive = thesis_signal_words.text_has_any(combined_text, thesis_signal_words.POSITIVE_SIGNAL_WORDS)
    has_negative = thesis_signal_words.text_has_any(combined_text, thesis_signal_words.NEGATIVE_SIGNAL_WORDS)

    if not new_data or not theses:
        overall_impact = ThesisImpact.INSUFFICIENT_DATA
    elif source_confidence < 0.45:
        overall_impact = ThesisImpact.NEUTRAL
    elif has_positive and has_negative:
        overall_impact = ThesisImpact.MIXED
    elif has_positive:
        overall_impact = ThesisImpact.STRENGTHENS
    elif has_negative:
        overall_impact = ThesisImpact.WEAKENS
    else:
        overall_impact = ThesisImpact.NEUTRAL

    if not theses:
        findings = [
            ThesisImpactFinding(
                impact=ThesisImpact.INSUFFICIENT_DATA,
                thesis_reference="저장된 투자 논거 없음",
                evidence=evidence,
                reasoning=(
                    f"{prompt_instruction} 저장된 투자 논거가 없어 새 정보와 비교할 기준이 부족합니다."
                ),
                confidence=confidence_adjusted_finding_confidence(
                    ThesisImpact.INSUFFICIENT_DATA,
                    source_confidence,
                ),
            )
        ]
    else:
        findings = [
            ThesisImpactFinding(
                impact=overall_impact,
                thesis_reference=thesis.thesis,
                evidence=evidence,
                reasoning=(
                    f"{prompt_instruction} 새 데이터의 긍정/부정 신호를 기존 강세/약세 촉발 조건과 비교했습니다. "
                    f"출처 평균 신뢰도는 {source_confidence:.0%}이며, 이 가중치를 반영해 결론 확신도를 조정했습니다."
                ),
                confidence=confidence_adjusted_finding_confidence(
                    overall_impact,
                    source_confidence,
                ),
            )
            for thesis in theses
        ]

    watch_item_signals = []
    for watch_item in watch_items:
        metric_match = watch_item.metric.lower() in combined_text.lower()
        watch_item_signals.append(
            WatchItemSignal(
                metric=watch_item.metric,
                matched=metric_match,
                signal=(
                    f"'{watch_item.metric}' 관련 새 정보가 감지되었습니다."
                    if metric_match
                    else "직접 매칭된 신호 없음"
                ),
                action=watch_item.action if metric_match else "계속 모니터링",
                priority=watch_item.priority,
            )
        )

    next_actions = [
        "팀 리포트를 재실행해 강세/기준/약세 시나리오를 업데이트",
        "영향도가 약화 또는 혼합이면 무효화 조건과 포지션 사이즈를 재검토",
        "영향도가 강화이면 밸류에이션과 진입 조건을 별도로 업데이트",
    ]
    if source_confidence < 0.7 and new_data:
        next_actions.insert(0, "신뢰도가 제한적인 정보이므로 공식 공시, 실적 자료, 가격 데이터로 교차 검증")
    if overall_impact == ThesisImpact.INSUFFICIENT_DATA:
        next_actions = [
            "먼저 7개 스킬 팀 리포트를 생성해 기준 투자 논거를 저장",
            "공식 실적/재무/가격 데이터를 추가 데이터로 주입",
        ]

    return ThesisImpactResponse(
        ticker=ticker,
        overall_impact=overall_impact,
        summary=(
            f"새 데이터는 평균 신뢰도 {source_confidence:.0%} 가중치를 반영해 "
            f"기존 {ticker} 투자 논거에 대해 '{translate_impact_label(overall_impact)}'로 분류되었습니다."
        ),
        findings=findings,
        watch_item_signals=watch_item_signals,
        next_actions=next_actions,
        source_count=len(new_data),
    )


def render_thesis_impact_markdown(
    impact: ThesisImpactResponse,
    storage_date: date,
) -> str:
    findings = "\n\n".join(
        "\n".join(
            [
                f"### 판단: {item.impact.value}",
                f"- 투자 논거: {item.thesis_reference}",
                f"- 판단 이유: {item.reasoning}",
                f"- 확신도: {item.confidence:.0%}",
                "- 근거:",
                *[f"  - {evidence}" for evidence in item.evidence],
            ]
        )
        for item in impact.findings
    )
    watch_signals = "\n".join(
        f"- {item.metric}: {item.signal} -> {item.action} ({translate_priority_label(item.priority)})"
        for item in impact.watch_item_signals
    )
    next_actions = "\n".join(f"- {item}" for item in impact.next_actions)

    return f"""---
ticker: {impact.ticker}
type: thesis-impact-review
date: {storage_date.isoformat()}
module: {impact.module}
overall_impact: {impact.overall_impact.value}
---

# {impact.ticker} 투자 논거 영향도 분석

## 요약

{impact.summary}

## 판단 근거

{findings}

## 추적 항목 신호

{watch_signals}

## 다음 액션

{next_actions}
"""
