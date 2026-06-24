"""Policy and regulatory signal helpers for daily recommendations."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence


RISK_KEYWORDS = {
    "규제",
    "제재",
    "조사",
    "과징금",
    "공정화",
    "독점",
    "처벌",
    "위반",
    "제한",
    "강화",
    "안전",
    "사고",
}

SUPPORT_KEYWORDS = {
    "지원",
    "육성",
    "활성화",
    "투자",
    "확대",
    "개선",
    "전략",
    "보급",
    "인프라",
    "수출",
    "세제",
}

THEME_KEYWORDS = {
    "금융/자본시장": ["금융", "자본시장", "증권", "은행", "핀테크", "공시"],
    "공정거래/플랫폼": ["플랫폼", "커머스", "광고", "독점", "소비자", "유통"],
    "산업/통상": ["산업", "통상", "수출", "무역", "공급망", "반도체", "배터리", "자동차"],
    "에너지/원자재": ["에너지", "전력", "원전", "태양광", "풍력", "가스", "정유"],
    "AI/디지털": ["AI", "인공지능", "반도체", "데이터", "클라우드", "소프트웨어", "디지털"],
    "바이오/헬스케어": ["바이오", "제약", "헬스케어", "의료", "임상", "신약"],
    "세제/법령": ["세제", "세법", "법령", "규정", "시행령", "상장"],
    "환경/ESG": ["ESG", "환경", "탄소", "기후", "재활용", "전기차", "EV"],
}


def normalize_policy_ticker(value: object) -> str:
    return daily_recommendation_evidence.normalize_recommendation_ticker(value)


def compact_policy_signal_text(value: object, max_length: int = 150) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 1)].rstrip() + "…"


def _parse_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10])
    except ValueError:
        return None


def policy_signal_age_days(item: dict[str, Any], *, as_of: datetime | None = None) -> int | None:
    parsed = _parse_date(item.get("published_at") or item.get("date") or item.get("created_at"))
    if parsed is None:
        return None
    reference = as_of or datetime.now()
    return max(0, (reference.date() - parsed.date()).days)


def policy_signal_freshness_multiplier(item: dict[str, Any], *, as_of: datetime | None = None) -> float:
    age_days = policy_signal_age_days(item, as_of=as_of)
    if age_days is None:
        return 0.7
    if age_days <= 3:
        return 1.0
    if age_days <= 7:
        return 0.8
    if age_days <= 14:
        return 0.55
    return 0.3


def policy_signal_tone(item: dict[str, Any]) -> str:
    text = " ".join(
        str(item.get(key) or "")
        for key in ("title", "summary", "source_scope", "agency", "source_provider")
    ).lower()
    risk_hits = sum(1 for keyword in RISK_KEYWORDS if keyword.lower() in text)
    support_hits = sum(1 for keyword in SUPPORT_KEYWORDS if keyword.lower() in text)
    if risk_hits > support_hits:
        return "risk"
    if support_hits:
        return "support"
    return "neutral"


def _item_target_tickers(item: dict[str, Any]) -> set[str]:
    tickers: set[str] = set()
    for target in item.get("target_matches") or item.get("matched_targets") or []:
        if not isinstance(target, dict):
            continue
        ticker = normalize_policy_ticker(target.get("ticker"))
        if ticker:
            tickers.add(ticker)
    for value in item.get("related_targets") or []:
        ticker = normalize_policy_ticker(value)
        if ticker and (ticker.isdigit() or re.fullmatch(r"[A-Z][A-Z0-9._-]{1,8}", ticker)):
            tickers.add(ticker)
    return tickers


def _candidate_policy_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("ticker"),
        candidate.get("company_name"),
        *(candidate.get("reasons") or []),
        *(candidate.get("evidence_sources") or []),
        *(candidate.get("portfolio_context") or []),
        *(candidate.get("risk_notes") or []),
    ]
    for component in candidate.get("score_components") or []:
        if isinstance(component, dict):
            parts.append(component.get("label"))
    profile = candidate.get("investment_direction_profile")
    if isinstance(profile, dict):
        parts.extend([profile.get("label"), profile.get("summary"), profile.get("trigger_text")])
    return " ".join(str(part or "") for part in parts).lower()


def _policy_item_matches_candidate_theme(item: dict[str, Any], candidate_text: str) -> bool:
    item_text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("summary") or ""),
            str(item.get("source_scope") or ""),
            " ".join(str(theme) for theme in item.get("matched_themes") or []),
        ]
    ).lower()
    for theme in item.get("matched_themes") or []:
        for keyword in THEME_KEYWORDS.get(str(theme), []):
            if keyword.lower() in candidate_text:
                return True
    return False


def policy_signal_evidence_document(item: dict[str, Any]) -> dict[str, Any] | None:
    title = compact_policy_signal_text(item.get("title"), 140)
    source_url = str(item.get("detail_url") or item.get("source_url") or "").strip()
    if not title and not source_url:
        return None
    return {
        "title": title or source_url,
        "source_relative_path": source_url,
        "source_date": str(item.get("published_at") or item.get("date") or "").strip(),
        "report_type": "official_policy_source",
        "source_type": "policy_law",
        "confidence": 0.82,
        "citation_label": "정책 신호 근거",
        "matched_claims": [
            compact_policy_signal_text(item.get("recommended_action") or item.get("summary") or title, 120)
        ],
    }


def build_policy_signal_index(policy_watch: dict | None, news_inbox: dict | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in (policy_watch or {}).get("related_items") or []:
        if isinstance(item, dict):
            items.append({**item, "policy_signal_source": "policy_sources_watch"})
    for item in (news_inbox or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("scope") != "POLICY" and not item.get("is_policy_law") and not item.get("official_policy_source"):
            continue
        items.append(
            {
                "item_id": item.get("id") or item.get("fingerprint"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source_provider": item.get("source_provider") or "뉴스 인박스",
                "source_scope": item.get("scope_label") or "정책/법령",
                "published_at": item.get("created_at"),
                "detail_url": item.get("source_url"),
                "source_url": item.get("source_url"),
                "matched_themes": item.get("matched_themes") or [],
                "target_matches": item.get("target_matches") or [],
                "relevance_score": item.get("relevance_score") or 0,
                "policy_signal_source": "news_inbox",
            }
        )

    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        for ticker in _item_target_tickers(item):
            by_ticker.setdefault(ticker, []).append(item)

    for ticker, rows in by_ticker.items():
        rows.sort(
            key=lambda item: (
                int(item.get("relevance_score") or 0),
                str(item.get("published_at") or item.get("date") or ""),
            ),
            reverse=True,
        )
        by_ticker[ticker] = rows[:8]
    return {"items": items, "by_ticker": by_ticker}


def apply_daily_recommendation_policy_signals(
    candidate: dict[str, Any],
    policy_signal_index: dict[str, Any] | None,
    *,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    ticker = normalize_policy_ticker(candidate.get("ticker"))
    items = list(((policy_signal_index or {}).get("by_ticker") or {}).get(ticker) or [])
    if not items:
        candidate_text = _candidate_policy_text(candidate)
        items = [
            item
            for item in (policy_signal_index or {}).get("items") or []
            if isinstance(item, dict) and _policy_item_matches_candidate_theme(item, candidate_text)
        ][:6]
    if not items:
        return candidate

    support_items = [item for item in items if policy_signal_tone(item) != "risk"]
    risk_items = [item for item in items if policy_signal_tone(item) == "risk"]
    support_score = sum(
        max(1, round((int(item.get("relevance_score") or 50) / 25) * policy_signal_freshness_multiplier(item, as_of=as_of)))
        for item in support_items[:3]
    )
    risk_score = sum(
        max(1, round((int(item.get("relevance_score") or 50) / 30) * policy_signal_freshness_multiplier(item, as_of=as_of)))
        for item in risk_items[:3]
    )
    if support_score:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(12, support_score),
            "정책 수혜/제도 모멘텀",
        )
    if risk_score:
        daily_recommendation_candidates.add_daily_recommendation_penalty(
            candidate,
            "정책·규제 리스크 확인",
            min(8, risk_score),
        )
        candidate.setdefault("quality_flags", []).append("정책·규제 리스크 확인 필요")

    top_items = items[:3]
    theme_text = ", ".join(
        dict.fromkeys(
            theme
            for item in top_items
            for theme in (item.get("matched_themes") or [])[:3]
            if str(theme or "").strip()
        )
    )
    evidence_text = f"정책 신호 {len(items)}건" + (f": {theme_text}" if theme_text else "")
    evidence_sources = candidate.setdefault("evidence_sources", [])
    if evidence_text not in evidence_sources:
        evidence_sources.insert(0, evidence_text)
    candidate.setdefault("reasons", []).append(
        "정책/법령/규제 자료가 추천 점수에 반영됨: "
        + compact_policy_signal_text(top_items[0].get("title"), 100)
    )
    if risk_items:
        candidate.setdefault("risk_notes", []).append(
            "규제성 정책자료 확인 필요: "
            + compact_policy_signal_text(risk_items[0].get("title"), 100)
        )
    candidate["policy_signal_summary"] = {
        "count": len(items),
        "support_count": len(support_items),
        "risk_count": len(risk_items),
        "top_title": compact_policy_signal_text(top_items[0].get("title"), 120),
        "top_source_url": top_items[0].get("detail_url") or top_items[0].get("source_url"),
        "themes": list(dict.fromkeys(theme for item in top_items for theme in (item.get("matched_themes") or []) if theme))[:6],
    }
    for item in top_items:
        document = policy_signal_evidence_document(item)
        if document:
            candidate.setdefault("evidence_documents", []).append(document)
    return candidate
