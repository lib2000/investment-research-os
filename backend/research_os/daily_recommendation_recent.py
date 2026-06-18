"""Recent-weekly evidence helpers for daily recommendations."""

from __future__ import annotations

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence


def normalize_recommendation_ticker(value: object) -> str:
    return daily_recommendation_evidence.normalize_recommendation_ticker(value)


def compact_recommendation_text(value: object, max_length: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 1)].rstrip() + "…"


def daily_recommendation_recent_weekly_index(recent_weekly: dict) -> dict[str, dict[str, list[dict]]]:
    """Index recent weekly items and groups by ticker for daily recommendation scoring."""
    items_by_ticker: dict[str, list[dict]] = {}
    for item in [
        *(recent_weekly.get("important_filings") or []),
        *(recent_weekly.get("display_reports") or []),
        *(recent_weekly.get("public_ir_sec_items") or []),
        *(recent_weekly.get("customs_exports") or []),
    ]:
        if not isinstance(item, dict):
            continue
        key = normalize_recommendation_ticker(item.get("ticker"))
        if key:
            items_by_ticker.setdefault(key, []).append(item)

    groups_by_ticker: dict[str, list[dict]] = {}
    for group in recent_weekly.get("category_groups") or []:
        if not isinstance(group, dict):
            continue
        group_key = str(group.get("key") or "").strip()
        group_label = str(group.get("label") or group_key or "최근 자료").strip()
        visible_items = [item for item in group.get("items") or [] if isinstance(item, dict)]
        linked_tickers = {
            ticker
            for ticker in (normalize_recommendation_ticker(ticker) for ticker in group.get("tickers") or [])
            if ticker
        }
        for item in visible_items:
            key = normalize_recommendation_ticker(item.get("ticker"))
            if key:
                linked_tickers.add(key)
        first_visible_item = visible_items[0] if visible_items else {}
        group_summary = compact_recommendation_text(
            first_visible_item.get("summary")
            or first_visible_item.get("title")
            or group.get("note")
            or group_label,
            90,
        )
        for ticker in sorted(linked_tickers):
            groups_by_ticker.setdefault(ticker, []).append(
                {
                    "key": group_key,
                    "label": group_label,
                    "count": int(group.get("count") or 0),
                    "visible_count": int(group.get("visible_count") or 0),
                    "ticker_count": int(group.get("ticker_count") or 0),
                    "quality_summary": group.get("quality_summary") if isinstance(group.get("quality_summary"), dict) else {},
                    "summary": group_summary,
                }
            )
    return {"items_by_ticker": items_by_ticker, "groups_by_ticker": groups_by_ticker}


def daily_recommendation_recent_item_evidence_document(item: dict) -> dict | None:
    """Convert a recent-weekly item into a stable recommendation evidence document."""
    if not isinstance(item, dict):
        return None
    relative_path = str(
        item.get("relative_path")
        or item.get("source_relative_path")
        or item.get("json_relative_path")
        or ""
    ).strip()
    if not relative_path:
        return None
    title = str(item.get("title") or item.get("summary") or item.get("action") or relative_path).strip()
    category = str(item.get("category") or item.get("report_type") or "recent_weekly").strip()
    claims = [
        str(value).strip()
        for value in (
            item.get("recommendation_usage_summary"),
            item.get("summary"),
            item.get("action"),
        )
        if str(value or "").strip()
    ][:3]
    return {
        "title": compact_recommendation_text(title, 140),
        "source_relative_path": relative_path,
        "source_date": str(item.get("date") or item.get("source_date") or "").strip(),
        "report_type": category,
        "source_type": category,
        "confidence": item.get("confidence"),
        "citation_label": "최근 1주 추천 영향 자료",
        "matched_claims": claims,
    }


def daily_recommendation_weekly_group_evidence_text(group: dict) -> str:
    label = str(group.get("label") or group.get("key") or "자료").strip()
    if not label:
        return ""
    total_count = int(group.get("count") or 0)
    visible_count = int(group.get("visible_count") or 0)
    ticker_count = int(group.get("ticker_count") or 0)
    text = f"{label} {total_count}건"
    details = []
    if visible_count and total_count > visible_count:
        details.append(f"표시 {visible_count}/{total_count}건")
    if ticker_count:
        details.append(f"종목 {ticker_count}개")
    if details:
        text += f"({'/'.join(details)})"
    if str(group.get("key") or "") == "public_ir_sec":
        quality = group.get("quality_summary") if isinstance(group.get("quality_summary"), dict) else {}
        usable = int(quality.get("usable_for_recommendation") or 0)
        blocked = int(quality.get("needs_body_copy") or quality.get("blocked_or_needs_review") or 0)
        provider_counts = (
            quality.get("source_families")
            if isinstance(quality.get("source_families"), dict)
            else quality.get("providers")
            if isinstance(quality.get("providers"), dict)
            else {}
        )
        provider_text = "/".join(
            f"{provider} {count}건"
            for provider, count in list(provider_counts.items())[:2]
            if provider
        )
        reliability_counts = quality.get("reliability_labels") if isinstance(quality.get("reliability_labels"), dict) else {}
        reliability_text = "/".join(
            f"{label} {count}건"
            for label, count in list(reliability_counts.items())[:2]
            if label
        )
        text += f"(추천 가능 {usable}건/본문 보강 {blocked}건"
        if provider_text:
            text += f"/출처 {provider_text}"
        if reliability_text:
            text += f"/품질 {reliability_text}"
        text += ")"
    return text


def apply_daily_recommendation_recent_weekly_evidence(
    candidate: dict,
    recent_items: list[dict],
    weekly_groups: list[dict] | None = None,
) -> dict:
    important_count = sum(1 for item in recent_items if item.get("category") == "filing")
    report_count = sum(1 for item in recent_items if item.get("category") == "report")
    public_ir_sec_items = [item for item in recent_items if item.get("category") == "public_ir_sec"]
    public_ir_sec_count = len(public_ir_sec_items)
    usable_public_ir_sec_count = sum(1 for item in public_ir_sec_items if item.get("usable_for_recommendation"))
    blocked_public_ir_sec_count = public_ir_sec_count - usable_public_ir_sec_count

    if important_count:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(20, important_count * 5),
            "최근 중요 공시 반영",
        )
        candidate.setdefault("reasons", []).append(f"최근 1주 중요 공시 {important_count}건 확인")
        candidate.setdefault("evidence_sources", []).append("최근 1주 공시 브리프 반영")
    if report_count:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(12, report_count * 3),
            "최근 핵심 리포트 반영",
        )
        candidate.setdefault("evidence_sources", []).append(f"최근 1주 핵심 리포트 {report_count}건")
    if usable_public_ir_sec_count:
        daily_recommendation_candidates.add_daily_recommendation_score(
            candidate,
            min(12, usable_public_ir_sec_count * 4),
            "최근 공개 IR/SEC 반영",
        )
        candidate.setdefault("evidence_sources", []).append(f"최근 1주 공개 IR/SEC 자료 {usable_public_ir_sec_count}건")
        candidate.setdefault("reasons", []).append("본문 추출이 확인된 공개 IR/SEC 자료가 최근 1주 브리프와 RAG 근거에 연결됨")
    if blocked_public_ir_sec_count:
        candidate.setdefault("risk_notes", []).append(
            f"공개 IR/SEC URL-only 자료 {blocked_public_ir_sec_count}건은 본문 보강 전 추천 점수 가산에서 제외"
        )
        candidate.setdefault("quality_flags", []).append("공개 IR/SEC 본문 보강 필요")

    for recent_item in recent_items[:8]:
        document = daily_recommendation_recent_item_evidence_document(recent_item)
        if document:
            candidate.setdefault("evidence_documents", []).append(document)

    deduped_weekly_groups = []
    seen_group_keys = set()
    for group in weekly_groups or []:
        group_key = str(group.get("key") or group.get("label") or "")
        if group_key in seen_group_keys:
            continue
        seen_group_keys.add(group_key)
        deduped_weekly_groups.append(group)
    if deduped_weekly_groups:
        candidate["weekly_evidence_groups"] = deduped_weekly_groups[:5]
        weekly_group_text = ", ".join(
            item
            for item in (daily_recommendation_weekly_group_evidence_text(group) for group in deduped_weekly_groups[:4])
            if item
        )
        if weekly_group_text:
            candidate.setdefault("evidence_sources", []).append(f"최근 1주 자료 묶음: {weekly_group_text}")
    return candidate
