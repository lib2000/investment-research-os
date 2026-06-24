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

GENERIC_DIRECT_ALIAS_WORDS = {
    "ETF",
    "ETN",
    "KODEX",
    "TIGER",
    "SOL",
    "ACE",
    "PLUS",
    "AI",
    "USD",
    "KRW",
    "CORP",
    "CORPORATION",
    "INC",
    "LTD",
    "CO",
    "GROUP",
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


def _policy_item_search_text(item: dict[str, Any]) -> str:
    target_text = " ".join(
        " ".join(str(target.get(key) or "") for key in ("ticker", "label", "name"))
        for target in item.get("target_matches") or item.get("matched_targets") or []
        if isinstance(target, dict)
    )
    return " ".join(
        str(part or "")
        for part in (
            item.get("title"),
            item.get("summary"),
            item.get("recommended_action"),
            item.get("agency"),
            item.get("source_provider"),
            item.get("source_scope"),
            target_text,
            " ".join(str(value) for value in item.get("related_targets") or []),
        )
    )


def _candidate_direct_aliases(candidate: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    ticker = normalize_policy_ticker(candidate.get("ticker"))
    if ticker and (ticker.isdigit() or len(ticker) >= 3):
        aliases.append(ticker)
    for value in (
        candidate.get("company_name"),
        candidate.get("label"),
        candidate.get("name"),
        candidate.get("display_name"),
    ):
        text = " ".join(str(value or "").replace("(", " ").replace(")", " ").split()).strip()
        if len(text) >= 4:
            aliases.append(text)
        chunks = [
            chunk.strip(".,·-/ ")
            for chunk in re.split(r"\s+|/|,", text)
            if len(chunk.strip(".,·-/ ")) >= 4
        ]
        aliases.extend(
            chunk
            for chunk in chunks
            if chunk.upper() not in GENERIC_DIRECT_ALIAS_WORDS
            and not chunk.upper().endswith(("ETF", "ETN"))
        )
    seen: set[str] = set()
    result: list[str] = []
    for alias in aliases:
        key = alias.casefold()
        if key not in seen:
            seen.add(key)
            result.append(alias)
    return result[:12]


def _alias_in_policy_text(alias: str, text: str) -> bool:
    if not alias:
        return False
    if re.fullmatch(r"[A-Z0-9._-]{2,10}", alias):
        return re.search(rf"(?<![A-Z0-9._-]){re.escape(alias)}(?![A-Z0-9._-])", text.upper()) is not None
    return alias.casefold() in text.casefold()


def _policy_item_matches_candidate_direct_text(item: dict[str, Any], candidate: dict[str, Any]) -> bool:
    search_text = _policy_item_search_text(item)
    return any(_alias_in_policy_text(alias, search_text) for alias in _candidate_direct_aliases(candidate))


def _policy_item_matches_candidate_theme(item: dict[str, Any], candidate_text: str) -> bool:
    item_text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("summary") or ""),
            str(item.get("source_scope") or ""),
        ]
    ).lower()
    for theme in item.get("matched_themes") or []:
        shared_keywords = [
            keyword
            for keyword in THEME_KEYWORDS.get(str(theme), [])
            if keyword.lower() in candidate_text and keyword.lower() in item_text
        ]
        if len(shared_keywords) >= 2:
            return True
    return False


def _policy_item_key(item: dict[str, Any]) -> str:
    return str(item.get("item_id") or item.get("detail_url") or item.get("source_url") or item.get("title") or "")


def _rank_policy_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [item for item in items if isinstance(item, dict)],
        key=lambda item: (
            int(item.get("relevance_score") or 0),
            str(item.get("published_at") or item.get("date") or ""),
        ),
        reverse=True,
    )


def candidate_policy_signal_matches(
    candidate: dict[str, Any],
    policy_signal_index: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    ticker = normalize_policy_ticker(candidate.get("ticker"))
    direct_items = _rank_policy_items(list(((policy_signal_index or {}).get("by_ticker") or {}).get(ticker) or []))
    direct_items = _rank_policy_items(
        [
            *direct_items,
            *[
                item
                for item in (policy_signal_index or {}).get("items") or []
                if isinstance(item, dict)
                and _policy_item_key(item) not in {_policy_item_key(row) for row in direct_items}
                and _policy_item_matches_candidate_direct_text(item, candidate)
            ],
        ]
    )
    direct_keys = {_policy_item_key(item) for item in direct_items}
    candidate_text = _candidate_policy_text(candidate)
    theme_items = _rank_policy_items(
        [
            item
            for item in (policy_signal_index or {}).get("items") or []
            if isinstance(item, dict)
            and _policy_item_key(item) not in direct_keys
            and _policy_item_matches_candidate_theme(item, candidate_text)
        ]
    )
    matched_keys = direct_keys | {_policy_item_key(item) for item in theme_items}
    market_items = _rank_policy_items(
        [
            item
            for item in (policy_signal_index or {}).get("items") or []
            if isinstance(item, dict) and _policy_item_key(item) not in matched_keys
        ]
    )
    return {
        "direct": direct_items[:8],
        "theme": theme_items[:3],
        "market": market_items[:3],
    }


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
    matches = candidate_policy_signal_matches(candidate, policy_signal_index)
    direct_items = matches["direct"]
    theme_items = matches["theme"]
    market_items = matches["market"]
    scored_items = direct_items
    match_level = "direct" if direct_items else "theme" if theme_items else "market" if market_items else ""
    items = scored_items or theme_items or market_items
    if not items:
        return candidate

    support_items = [item for item in items if policy_signal_tone(item) != "risk"]
    risk_items = [item for item in items if policy_signal_tone(item) == "risk"]
    score_divisors = (25, 30) if match_level == "direct" else (45, 60)
    score_caps = (12, 8) if match_level == "direct" else (6, 4)
    support_score = sum(
        max(1, round((int(item.get("relevance_score") or 50) / score_divisors[0]) * policy_signal_freshness_multiplier(item, as_of=as_of)))
        for item in support_items[:3]
    ) if scored_items else 0
    risk_score = sum(
        max(1, round((int(item.get("relevance_score") or 50) / score_divisors[1]) * policy_signal_freshness_multiplier(item, as_of=as_of)))
        for item in risk_items[:3]
    ) if scored_items else 0
    if support_score:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(score_caps[0], support_score),
            "정책 수혜/제도 모멘텀" if match_level == "direct" else "정책 테마 모멘텀",
        )
    if risk_score:
        daily_recommendation_candidates.add_daily_recommendation_penalty(
            candidate,
            "정책·규제 리스크 확인" if match_level == "direct" else "정책 테마 규제 리스크 확인",
            min(score_caps[1], risk_score),
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
    level_label = {"direct": "직접", "theme": "테마", "market": "시장"}.get(match_level, "참고")
    evidence_text = (
        f"정책 신호 {level_label} {len(items)}건"
        if scored_items
        else f"정책 신호 {level_label} 참고 {len(items)}건"
    ) + (f": {theme_text}" if theme_text else "")
    evidence_sources = candidate.setdefault("evidence_sources", [])
    if evidence_text not in evidence_sources:
        evidence_sources.insert(0, evidence_text)
    reason_prefix = "정책/법령/규제 자료가 추천 점수에 반영됨" if scored_items else "정책/법령/규제 자료 참고"
    candidate.setdefault("reasons", []).append(
        f"{reason_prefix}({level_label}): " + compact_policy_signal_text(top_items[0].get("title"), 100)
    )
    if risk_items and scored_items:
        candidate.setdefault("risk_notes", []).append(
            "규제성 정책자료 확인 필요: "
            + compact_policy_signal_text(risk_items[0].get("title"), 100)
        )
    elif risk_items:
        candidate.setdefault("risk_notes", []).append(
            "시장 전반 규제성 정책자료 참고: "
            + compact_policy_signal_text(risk_items[0].get("title"), 100)
        )
    candidate["policy_signal_summary"] = {
        "count": len(items),
        "match_level": match_level,
        "match_level_label": level_label,
        "score_applied": bool(scored_items),
        "direct_count": len(direct_items),
        "theme_count": len(theme_items),
        "market_count": len(market_items),
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


def _policy_score_impact(record: dict[str, Any]) -> dict[str, Any]:
    positive = [
        component
        for component in record.get("score_components") or []
        if isinstance(component, dict)
        and ("정책" in str(component.get("label") or "") or "규제" in str(component.get("label") or ""))
    ]
    penalties = [
        str(item)
        for item in record.get("score_penalties") or []
        if "정책" in str(item) or "규제" in str(item)
    ]
    positive_points = sum(int(component.get("points") or 0) for component in positive)
    penalty_points = 0
    for item in penalties:
        match = re.search(r"\(-(\d+)\)", item)
        if match:
            penalty_points += int(match.group(1))
    return {
        "positive_components": positive,
        "penalties": penalties,
        "positive_points": positive_points,
        "penalty_points": penalty_points,
        "net_points": positive_points - penalty_points,
    }


def _policy_signal_review_status(record: dict[str, Any]) -> tuple[str, str]:
    signal = record.get("policy_signal_summary") if isinstance(record.get("policy_signal_summary"), dict) else {}
    level = str(signal.get("match_level") or "")
    score_applied = bool(signal.get("score_applied"))
    direct_count = int(signal.get("direct_count") or 0)
    theme_count = int(signal.get("theme_count") or 0)
    market_count = int(signal.get("market_count") or 0)
    risk_count = int(signal.get("risk_count") or 0)
    if level == "direct" and direct_count:
        return "ok", "직접 종목 매칭으로 점수 반영"
    if level == "theme" and not score_applied:
        return "info", "테마 참고 신호로 점수 미반영"
    if level == "theme" and theme_count >= 3 and direct_count == 0:
        return "review", "직접 매칭 없이 테마 상위 3건이 점수에 반영됨"
    if level == "theme" and score_applied:
        return "watch", "테마 매칭 점수 반영"
    if level == "market" and not score_applied:
        return "info", "시장 참고 신호로 점수 미반영"
    if risk_count and not score_applied:
        return "watch", "규제성 시장 참고 신호 확인"
    if market_count and not level:
        return "info", "정책 신호 미반영"
    return "info", "정책 신호 없음"


def build_policy_signal_quality_dashboard(recommendation_payload: dict[str, Any]) -> dict[str, Any]:
    records = [
        item
        for item in (
            recommendation_payload.get("latest_records")
            or recommendation_payload.get("today_records")
            or recommendation_payload.get("records")
            or []
        )
        if isinstance(item, dict)
    ]
    rows: list[dict[str, Any]] = []
    level_counts: dict[str, int] = {"direct": 0, "theme": 0, "market": 0, "none": 0}
    score_applied_count = 0
    review_count = 0
    market_reference_count = 0
    total_net_points = 0
    for record in records:
        signal = record.get("policy_signal_summary") if isinstance(record.get("policy_signal_summary"), dict) else {}
        level = str(signal.get("match_level") or "none")
        level_counts[level] = level_counts.get(level, 0) + 1
        if signal.get("score_applied"):
            score_applied_count += 1
        if level == "market":
            market_reference_count += 1
        score_impact = _policy_score_impact(record)
        total_net_points += int(score_impact["net_points"] or 0)
        review_status, review_reason = _policy_signal_review_status(record)
        if review_status == "review":
            review_count += 1
        policy_documents = [
            document
            for document in record.get("evidence_documents") or []
            if isinstance(document, dict)
            and (
                document.get("source_type") == "policy_law"
                or document.get("report_type") == "official_policy_source"
                or document.get("citation_label") == "정책 신호 근거"
            )
        ][:3]
        rows.append(
            {
                "market": record.get("market"),
                "market_label": record.get("market_label"),
                "rank": record.get("rank"),
                "ticker": record.get("ticker"),
                "company_name": record.get("company_name"),
                "score": record.get("score"),
                "policy_signal_summary": signal,
                "match_level": level,
                "match_level_label": signal.get("match_level_label") or {"direct": "직접", "theme": "테마", "market": "시장"}.get(level, "없음"),
                "score_applied": bool(signal.get("score_applied")),
                "score_impact": score_impact,
                "review_status": review_status,
                "review_reason": review_reason,
                "policy_documents": policy_documents,
            }
        )
    review_rows = [row for row in rows if row["review_status"] == "review"]
    return {
        "status": "success",
        "module": "daily_recommendation_policy_signal_quality",
        "recommendation_date": recommendation_payload.get("latest_recommendation_date")
        or recommendation_payload.get("recommendation_date")
        or recommendation_payload.get("today_recommendation_date"),
        "record_count": len(records),
        "level_counts": level_counts,
        "score_applied_count": score_applied_count,
        "market_reference_count": market_reference_count,
        "review_count": review_count,
        "total_policy_net_points": total_net_points,
        "rows": rows,
        "review_rows": review_rows,
        "summary": (
            f"정책 신호 {score_applied_count}/{len(records)}개 추천에 점수 반영, "
            f"검토 필요 {review_count}개, 시장 참고 {market_reference_count}개"
        ),
    }
