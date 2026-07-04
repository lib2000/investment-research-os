"""Candidate shaping helpers for daily recommendations."""

from __future__ import annotations

from datetime import date
from re import fullmatch
from re import search
from typing import Any

from research_os import daily_recommendation_evidence


def _contains_any(value: object, terms: tuple[str, ...]) -> bool:
    text = str(value or "").lower()
    return any(term.lower() in text for term in terms)


def _signal_item(
    *,
    key: str,
    label: str,
    summary: str,
    count: int = 0,
    score_applied: bool = False,
    tone: str = "neutral",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "summary": summary,
        "count": max(0, int(count or 0)),
        "score_applied": bool(score_applied),
        "tone": tone,
    }


def _has_score_component(candidate: dict[str, Any], label: str) -> bool:
    return any(
        isinstance(component, dict)
        and str(component.get("label") or "").strip() == label
        for component in candidate.get("score_components", [])
    )


def _promote_or_insert_text(items: list[str], marker: str, fallback: str) -> list[str]:
    selected = next((item for item in items if marker in item), "")
    promoted = selected or fallback
    return [promoted, *[item for item in items if item != selected and item != promoted]]


def _preserve_scored_public_ir_sec_context(candidate: dict[str, Any]) -> None:
    if _has_score_component(candidate, "최근 핵심 리포트 반영"):
        evidence_sources = daily_recommendation_evidence.unique_text_items(
            candidate.get("evidence_sources"),
            12,
        )
        evidence_sources = _promote_or_insert_text(
            evidence_sources,
            "최근 1주 핵심 리포트",
            "최근 1주 핵심 리포트 확인",
        )
        candidate["evidence_sources"] = daily_recommendation_evidence.unique_text_items(
            evidence_sources,
            8,
        )

    if _has_score_component(candidate, "최근 공개 IR/SEC 반영"):
        evidence_sources = daily_recommendation_evidence.unique_text_items(
            candidate.get("evidence_sources"),
            12,
        )
        evidence_sources = _promote_or_insert_text(
            evidence_sources,
            "최근 1주 공개 IR/SEC",
            "최근 1주 공개 IR/SEC 자료 확인",
        )
        candidate["evidence_sources"] = daily_recommendation_evidence.unique_text_items(
            evidence_sources,
            8,
        )

    quality_flags = [
        str(item).strip()
        for item in candidate.get("quality_flags", [])
        if str(item or "").strip()
    ]
    if any("공개 IR/SEC 본문 보강 필요" in item for item in quality_flags):
        risk_notes = daily_recommendation_evidence.unique_text_items(
            candidate.get("risk_notes"),
            8,
        )
        if not any("본문 보강" in item and "공개 IR/SEC" in item for item in risk_notes):
            risk_notes.insert(0, "공개 IR/SEC 본문 보강 필요: URL-only 자료는 원문 확인 후 추천 근거로 사용하세요.")
        candidate["risk_notes"] = daily_recommendation_evidence.unique_text_items(
            risk_notes,
            5,
        )


def build_recommendation_signal_breakdown(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    components = [
        item
        for item in candidate.get("score_components", [])
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    evidence_sources = [str(item or "").strip() for item in candidate.get("evidence_sources", []) if str(item or "").strip()]
    documents = [
        item
        for item in candidate.get("evidence_documents", [])
        if isinstance(item, dict)
    ]
    component_labels = [str(item.get("label") or "") for item in components]
    market_components = [
        item
        for item in components
        if _contains_any(item.get("label"), ("시장", "목표가", "현재가", "가격", "보유", "포트폴리오", "투자 방향"))
    ]
    filing_documents = [
        item
        for item in documents
        if _contains_any(item.get("source_type"), ("filing", "dart"))
        or _contains_any(item.get("report_type"), ("filing", "dart"))
    ]
    policy_signal = candidate.get("policy_signal_summary") if isinstance(candidate.get("policy_signal_summary"), dict) else {}
    policy_count = int(policy_signal.get("count") or 0)
    policy_level = str(policy_signal.get("match_level_label") or policy_signal.get("match_level") or "참고").strip()
    policy_summary = (
        f"{policy_level} {policy_count}건 · {'점수 반영' if policy_signal.get('score_applied') else '참고만'}"
        if policy_count
        else "직접 정책 신호 없음"
    )
    news_documents = [
        item
        for item in documents
        if item not in filing_documents
        and not _contains_any(item.get("source_type"), ("policy", "filing", "dart"))
        and not _contains_any(item.get("report_type"), ("official_policy", "filing", "dart"))
    ]
    news_sources = [
        item
        for item in evidence_sources
        if _contains_any(item, ("뉴스", "리포트", "자료 묶음", "공개 IR", "SEC", "RAG"))
    ]
    profile = candidate.get("investment_direction_profile") if isinstance(candidate.get("investment_direction_profile"), dict) else {}
    profile_labels: list[str] = []
    if profile:
        for item in (profile.get("matched_directions") or profile.get("directions") or profile.get("labels") or []):
            label = item.get("label") or item.get("name") if isinstance(item, dict) else item
            label_text = str(label or "").strip()
            if label_text:
                profile_labels.append(label_text)
    sentiment_sources = [
        *[label for label in component_labels if _contains_any(label, ("투자 방향", "심리", "센티먼트", "추세"))],
        *[item for item in evidence_sources if _contains_any(item, ("시장일지", "심리", "센티먼트", "투자 방향"))],
        *profile_labels,
    ]
    market_summary = (
        f"{market_components[0].get('label')} +{int(market_components[0].get('points') or 0)}점"
        if market_components
        else "시장/가격 신호는 참고 수준"
    )
    filing_summary = (
        f"최근 공시 {len(filing_documents)}건 연결"
        if filing_documents
        else "직접 공시 근거 없음"
    )
    news_summary = (
        f"뉴스/리포트 근거 {max(len(news_documents), len(news_sources))}건"
        if news_documents or news_sources
        else "뉴스 근거 없음"
    )
    sentiment_summary = (
        " · ".join(dict.fromkeys(sentiment_sources[:3]))
        if sentiment_sources
        else "심리/방향성 신호 없음"
    )
    return [
        _signal_item(
            key="market",
            label="시장",
            summary=market_summary,
            count=len(market_components),
            score_applied=bool(market_components),
            tone="ok" if market_components else "neutral",
        ),
        _signal_item(
            key="filing",
            label="공시",
            summary=filing_summary,
            count=len(filing_documents),
            score_applied=any(_contains_any(label, ("공시", "DART")) for label in component_labels),
            tone="ok" if filing_documents else "neutral",
        ),
        _signal_item(
            key="policy",
            label="정책",
            summary=policy_summary,
            count=policy_count,
            score_applied=bool(policy_signal.get("score_applied")),
            tone="ok" if policy_signal.get("score_applied") else "reference" if policy_count else "neutral",
        ),
        _signal_item(
            key="news",
            label="뉴스",
            summary=news_summary,
            count=max(len(news_documents), len(news_sources)),
            score_applied=any(_contains_any(label, ("리포트", "자료", "RAG")) for label in component_labels),
            tone="ok" if news_documents or news_sources else "neutral",
        ),
        _signal_item(
            key="sentiment",
            label="심리",
            summary=sentiment_summary,
            count=len(sentiment_sources),
            score_applied=bool(sentiment_sources),
            tone="ok" if sentiment_sources else "neutral",
        ),
    ]


def _document_source_family(document: dict[str, Any]) -> str:
    combined = f"{document.get('source_type') or ''} {document.get('report_type') or ''}".lower()
    if "filing" in combined or "dart" in combined:
        return "filing"
    if "policy" in combined or "official" in combined:
        return "policy"
    if "news" in combined:
        return "news"
    if "report" in combined or "dossier" in combined or "rag" in combined:
        return "report"
    return "other"


def _parse_source_date(value: object) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _evidence_quality_guardrail(grade: str) -> dict[str, Any]:
    if grade == "A":
        return {
            "level": "review_priority",
            "label": "검토 우선",
            "action": "추천 근거 품질이 높아 우선 검토 대상으로 유지합니다.",
            "blocks_buy": False,
        }
    if grade == "B":
        return {
            "level": "source_check",
            "label": "원문 1회 확인 후 검토",
            "action": "핵심 원문 1개 이상을 확인한 뒤 검토합니다.",
            "blocks_buy": False,
        }
    if grade == "C":
        return {
            "level": "needs_evidence",
            "label": "보강 후 검토",
            "action": "부족한 근거를 보강한 뒤 검토합니다.",
            "blocks_buy": True,
        }
    return {
        "level": "hold_buy_decision",
        "label": "매수 판단 보류",
        "action": "근거 품질이 낮아 원문 확인 전 매수 판단을 보류합니다.",
        "blocks_buy": True,
    }


def _evidence_repair_task(reason: str) -> dict[str, str]:
    reason_text = str(reason or "").strip()
    lowered = reason_text.lower()
    if "추적" in reason_text or "출처" in reason_text and "다양" not in reason_text:
        return {
            "task_type": "source_trace",
            "label": "출처 추적 보강",
            "next_action": "문서 제목, 저장 경로, 연결 주장을 확인해 근거 추적성을 보강합니다.",
        }
    if "최신" in reason_text or "신선" in reason_text or "recent" in lowered:
        return {
            "task_type": "fresh_evidence",
            "label": "최신 근거 보강",
            "next_action": "최근 7~30일 공시, 뉴스, 리포트 자료를 추가 확인합니다.",
        }
    if "다양" in reason_text:
        return {
            "task_type": "source_diversity",
            "label": "출처 다양성 보강",
            "next_action": "공시, 리포트, 뉴스, 정책 근거가 한쪽으로 쏠리지 않도록 다른 출처를 보강합니다.",
        }
    if "커버리지" in reason_text or "신호" in reason_text:
        return {
            "task_type": "signal_coverage",
            "label": "신호 커버리지 보강",
            "next_action": "시장, 공시, 정책, 뉴스, 심리 신호 중 비어 있는 축을 추가 점검합니다.",
        }
    if "원문" in reason_text or "본문" in reason_text or "OCR" in reason_text:
        return {
            "task_type": "source_body",
            "label": "원문 확인 필요",
            "next_action": "원문 본문, PDF, OCR 또는 직접 붙여넣기로 분석 가능한 내용을 보강합니다.",
        }
    return {
        "task_type": "general_review",
        "label": "근거 품질 보강",
        "next_action": "보강 사유를 확인하고 관련 원천 자료를 추가 수집합니다.",
    }


def _evidence_repair_queue(candidate: dict[str, Any], quality: dict[str, Any]) -> list[dict[str, Any]]:
    if not quality.get("blocks_buy_decision") and str(quality.get("grade") or "").upper() not in {"C", "D"}:
        return []
    reasons = [
        str(item or "").strip()
        for item in quality.get("needs_review_reasons", [])
        if str(item or "").strip()
    ]
    if not reasons:
        reasons = [quality.get("guardrail_label") or "근거 품질 보강 필요"]
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, reason in enumerate(reasons, start=1):
        task = _evidence_repair_task(reason)
        key = task["task_type"]
        if key in seen:
            continue
        seen.add(key)
        queue.append(
            {
                "queue_id": f"{candidate.get('ticker') or 'UNKNOWN'}-{key}",
                "priority": index,
                "ticker": candidate.get("ticker"),
                "company_name": candidate.get("company_name"),
                "grade": quality.get("grade"),
                "score": quality.get("score"),
                "reason": reason,
                **task,
                "status": "queued",
            }
        )
    return queue


def build_recommendation_evidence_quality_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    documents = [
        item
        for item in candidate.get("evidence_documents", [])
        if isinstance(item, dict)
    ]
    signal_items = [
        item
        for item in candidate.get("signal_breakdown", [])
        if isinstance(item, dict)
    ] or build_recommendation_signal_breakdown(candidate)
    source_counts: dict[str, int] = {}
    traced_count = 0
    recent_7d_count = 0
    recent_30d_count = 0
    today = date.today()
    for document in documents:
        family = _document_source_family(document)
        source_counts[family] = source_counts.get(family, 0) + 1
        if (
            str(document.get("source_relative_path") or document.get("json_relative_path") or "").strip()
            and str(document.get("title") or "").strip()
            and (document.get("matched_claims") or document.get("citation_label"))
        ):
            traced_count += 1
        source_date = _parse_source_date(document.get("source_date") or document.get("date"))
        if source_date:
            age_days = max(0, (today - source_date).days)
            if age_days <= 7:
                recent_7d_count += 1
            if age_days <= 30:
                recent_30d_count += 1

    document_count = len(documents)
    source_mix_count = len([count for count in source_counts.values() if count > 0])
    signal_coverage_count = sum(
        1
        for item in signal_items
        if int(item.get("count") or 0) > 0 or bool(item.get("score_applied"))
    )
    quality_flags = [str(item).strip() for item in candidate.get("quality_flags", []) if str(item or "").strip()]
    penalties = [str(item).strip() for item in candidate.get("score_penalties", []) if str(item or "").strip()]
    policy_signal = candidate.get("policy_signal_summary") if isinstance(candidate.get("policy_signal_summary"), dict) else {}
    needs_review_reasons: list[str] = []
    if document_count < 4:
        needs_review_reasons.append("근거 문서 부족")
    if traced_count < min(document_count, 3):
        needs_review_reasons.append("출처 추적 보강")
    if source_mix_count < 2:
        needs_review_reasons.append("출처 다양성 부족")
    if recent_30d_count < min(document_count, 2):
        needs_review_reasons.append("최신 근거 부족")
    if signal_coverage_count < 4:
        needs_review_reasons.append("신호 커버리지 부족")
    if int(policy_signal.get("count") or 0) and not policy_signal.get("score_applied"):
        needs_review_reasons.append("정책 신호 참고 수준")
    needs_review_reasons.extend(quality_flags[:2])

    trace_score = round((traced_count / max(1, document_count)) * 30)
    mix_score = min(20, source_mix_count * 7)
    freshness_score = min(20, recent_7d_count * 5 + max(0, recent_30d_count - recent_7d_count) * 3)
    signal_score = min(20, signal_coverage_count * 4)
    penalty_score = min(20, len(penalties) * 4 + len(quality_flags) * 3 + max(0, len(needs_review_reasons) - 2) * 2)
    score = max(0, min(100, 10 + trace_score + mix_score + freshness_score + signal_score - penalty_score))
    if score >= 85:
        grade, tone, label = "A", "ok", "근거 품질 우수"
    elif score >= 70:
        grade, tone, label = "B", "watch", "근거 품질 양호"
    elif score >= 55:
        grade, tone, label = "C", "warning", "근거 보강 권장"
    else:
        grade, tone, label = "D", "danger", "원문 확인 필요"
    guardrail = _evidence_quality_guardrail(grade)
    summary = (
        f"추적 {traced_count}/{document_count} · 출처 {source_mix_count}종 · "
        f"최근 30일 {recent_30d_count}건 · 신호 {signal_coverage_count}/5"
    )
    quality = {
        "score": score,
        "grade": grade,
        "tone": tone,
        "label": label,
        "guardrail": guardrail,
        "guardrail_label": guardrail["label"],
        "guardrail_action": guardrail["action"],
        "blocks_buy_decision": guardrail["blocks_buy"],
        "summary": summary,
        "document_count": document_count,
        "traced_document_count": traced_count,
        "recent_7d_count": recent_7d_count,
        "recent_30d_count": recent_30d_count,
        "source_mix_count": source_mix_count,
        "source_type_counts": source_counts,
        "signal_coverage_count": signal_coverage_count,
        "needs_review_count": len(needs_review_reasons),
        "needs_review_reasons": needs_review_reasons[:5],
    }
    quality["evidence_repair_queue"] = _evidence_repair_queue(candidate, quality)
    quality["repair_queue_count"] = len(quality["evidence_repair_queue"])
    return {
        **quality,
    }


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    ticker = str(candidate.get("ticker") or "").strip().upper()
    company_name = str(candidate.get("company_name") or candidate.get("name") or ticker).strip()
    reasons = [str(item).strip() for item in candidate.get("reasons", []) if str(item or "").strip()]
    evidence = [str(item).strip() for item in candidate.get("evidence_sources", []) if str(item or "").strip()]
    score_components = [
        item
        for item in candidate.get("score_components", [])
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    normalized = {
        **candidate,
        "ticker": ticker,
        "company_name": company_name,
        "score": int(candidate.get("score") or 0),
        "score_components": score_components,
        "reasons": reasons[:6],
        "evidence_sources": evidence[:8],
        "evidence_documents": daily_recommendation_evidence.normalize_evidence_documents(
            candidate.get("evidence_documents")
        ),
        "score_explanation": candidate.get("score_explanation") or {},
        "score_penalties": [
            str(item).strip()
            for item in candidate.get("score_penalties", [])
            if str(item or "").strip()
        ][:6],
        "quality_flags": [
            str(item).strip()
            for item in candidate.get("quality_flags", [])
            if str(item or "").strip()
        ][:6],
        "investment_direction_profile": candidate.get("investment_direction_profile") or {},
        "overseas_tracking": candidate.get("overseas_tracking") or {},
        "portfolio_risk_connection": candidate.get("portfolio_risk_connection") or {},
        "policy_signal_summary": candidate.get("policy_signal_summary") or {},
        "signal_breakdown": candidate.get("signal_breakdown") or build_recommendation_signal_breakdown(candidate),
    }
    normalized["evidence_quality_summary"] = candidate.get("evidence_quality_summary") or build_recommendation_evidence_quality_summary(normalized)
    return normalized


def daily_recommendation_candidate_is_valid(ticker: str, company_name: str) -> bool:
    if not ticker or ticker in {"CASH", "UNKNOWN"}:
        return False
    if fullmatch(r"\d+", ticker) and not fullmatch(r"\d{6}", ticker):
        return False
    if not company_name or company_name.upper().startswith("UNKNOWN"):
        return False
    return True


def ensure_daily_recommendation_candidate(
    candidates_by_ticker: dict[str, dict[str, Any]],
    ticker: str,
    company_name: str,
) -> dict[str, Any]:
    key = daily_recommendation_evidence.normalize_recommendation_ticker(ticker)
    row = candidates_by_ticker.setdefault(
        key,
        {
            "ticker": key,
            "company_name": company_name,
            "score": 0,
            "reasons": [],
            "evidence_sources": [],
            "risk_notes": [],
            "portfolio_context": [],
            "score_penalties": [],
            "quality_flags": [],
            "portfolio_risk_connection": {},
            "overseas_tracking": {},
            "currency": "KRW" if fullmatch(r"\d{6}", key) else "USD",
            "baseline_price": None,
            "baseline_price_source": None,
            "baseline_price_checked_at": None,
        },
    )
    if company_name and (row.get("company_name") == key or not row.get("company_name")):
        row["company_name"] = company_name
    return row


def add_daily_recommendation_score(candidate: dict[str, Any], points: int | float, label: str) -> None:
    try:
        numeric_points = int(points)
    except (TypeError, ValueError):
        numeric_points = 0
    if numeric_points <= 0:
        return
    candidate["score"] = int(candidate.get("score") or 0) + numeric_points
    candidate.setdefault("score_components", []).append(
        {"label": str(label or "").strip() or "점수", "points": numeric_points}
    )


def add_daily_recommendation_penalty(
    candidate: dict[str, Any],
    label: str,
    points: int | float = 0,
) -> None:
    try:
        numeric_points = abs(int(points))
    except (TypeError, ValueError):
        numeric_points = 0
    text = str(label or "").strip()
    if not text:
        return
    if numeric_points:
        candidate["score"] = int(candidate.get("score") or 0) - numeric_points
        text = f"{text} (-{numeric_points})"
    candidate.setdefault("score_penalties", []).append(text)


def finalize_daily_recommendation_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Normalize recommendation reasons, evidence, risks, and score explanation."""
    if not candidate.get("reasons"):
        candidate.setdefault("reasons", []).append("보유/관심목록과 저장 리서치에 포함된 일일 점검 후보입니다.")
    candidate["reasons"] = daily_recommendation_evidence.unique_text_items(candidate.get("reasons"), 6)
    candidate["evidence_sources"] = daily_recommendation_evidence.unique_text_items(candidate.get("evidence_sources"), 8)
    candidate["evidence_documents"] = daily_recommendation_evidence.normalize_evidence_documents(
        candidate.get("evidence_documents")
    )
    candidate["risk_notes"] = daily_recommendation_evidence.unique_text_items(candidate.get("risk_notes"), 5)
    candidate["score_penalties"] = daily_recommendation_evidence.unique_text_items(candidate.get("score_penalties"), 6)
    candidate["quality_flags"] = daily_recommendation_evidence.unique_text_items(candidate.get("quality_flags"), 6)
    _preserve_scored_public_ir_sec_context(candidate)
    score_components = [
        component
        for component in candidate.get("score_components", [])
        if isinstance(component, dict) and str(component.get("label") or "").strip()
    ]
    candidate["score_components"] = score_components
    positive_points = sum(int(component.get("points") or 0) for component in score_components)
    penalty_points = sum(
        int(match.group(1))
        for item in candidate.get("score_penalties", [])
        for match in [search(r"\(-(\d+)\)", str(item))]
        if match
    )
    if positive_points:
        candidate["score_explanation"] = {
            "positive_points": positive_points,
            "penalty_points": penalty_points,
            "final_score": int(candidate.get("score") or 0),
            "top_component": max(
                score_components,
                key=lambda component: int(component.get("points") or 0),
            ),
            "component_weights": [
                {
                    "label": component.get("label"),
                    "points": int(component.get("points") or 0),
                    "weight_pct": round(int(component.get("points") or 0) / positive_points * 100, 1),
                }
                for component in score_components[:8]
            ],
        }
    candidate["signal_breakdown"] = build_recommendation_signal_breakdown(candidate)
    candidate["evidence_quality_summary"] = build_recommendation_evidence_quality_summary(candidate)
    return candidate
