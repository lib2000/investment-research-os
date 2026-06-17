"""Navigation and recommendation-link helpers for recent activity items."""

from __future__ import annotations

from re import sub


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def recent_activity_item_key(item: dict) -> tuple:
    summary = sub(r"\s+", " ", str(item.get("summary") or "").strip().lower())[:180]
    source_url = str(item.get("source_url") or "").strip()
    source_key = f"url:{source_url}" if source_url else f"summary:{summary}"
    return (
        str(item.get("category") or ""),
        str(item.get("date") or ""),
        _normalize_ticker(item.get("ticker")),
        str(item.get("company_name") or ""),
        str(item.get("report_type") or ""),
        source_key,
    )


def recent_weekly_evidence_path_key(value: object) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("./").lower()


def annotate_recent_weekly_navigation_hints(items: list[dict]) -> None:
    """Attach console navigation hints for stored material and RAG search."""
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        relative_path = str(item.get("relative_path") or item.get("source_relative_path") or "").strip().replace("\\", "/")
        file_name = relative_path.rsplit("/", 1)[-1] if relative_path else ""
        title = str(item.get("title") or item.get("summary") or "").strip()
        company = str(item.get("company_name") or item.get("company") or "").strip()
        query_parts = [
            part
            for part in [ticker, company, title, item.get("recommendation_usage_summary")]
            if str(part or "").strip()
        ]
        if ticker and file_name:
            item["memory_lookup_key"] = ticker
            item["memory_file_name"] = file_name
            item["memory_navigation_hint"] = f"저장 데이터 탭에서 {ticker} 조회 후 {file_name} 열기"
        if query_parts:
            item["rag_search_query"] = " ".join(str(part).strip() for part in query_parts)[:180]


def annotate_recent_weekly_recommendation_links(items: list[dict], evidence_index: dict) -> None:
    """Attach daily recommendation evidence usage metadata to recent weekly items."""
    by_path = evidence_index.get("by_relative_path") if isinstance(evidence_index, dict) else {}
    if not isinstance(by_path, dict):
        by_path = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        keys = {
            recent_weekly_evidence_path_key(item.get("relative_path")),
            recent_weekly_evidence_path_key(item.get("json_relative_path")),
            recent_weekly_evidence_path_key(item.get("source_relative_path")),
        }
        links: list[dict] = []
        seen_records: set[str] = set()
        for key in sorted(key for key in keys if key):
            for link in by_path.get(key, []) or []:
                if not isinstance(link, dict):
                    continue
                record_key = str(link.get("record_id") or "") or f"{link.get('recommendation_date')}:{link.get('rank')}:{link.get('ticker')}"
                if record_key in seen_records:
                    continue
                seen_records.add(record_key)
                links.append({
                    "record_id": link.get("record_id"),
                    "recommendation_date": link.get("recommendation_date"),
                    "rank": link.get("rank"),
                    "ticker": link.get("ticker"),
                    "company_name": link.get("company_name"),
                    "is_latest": bool(link.get("is_latest")),
                })
        latest_links = [link for link in links if link.get("is_latest")]
        if links:
            item["recommendation_links"] = links[:5]
            item["recommendation_link_count"] = len(links)
            item["used_in_recommendation"] = True
            item["used_in_latest_recommendation"] = bool(latest_links)
            item["recommendation_usage_label"] = "오늘 추천 근거" if latest_links else "추천 이력 근거"
            item["recommendation_usage_summary"] = ", ".join(
                f"{link.get('recommendation_date') or '추천일 미확인'} {link.get('rank') or '-'}위 {link.get('company_name') or link.get('ticker') or '종목 미확인'}"
                for link in links[:3]
            )


def dedupe_recent_activity_items(items: list[dict]) -> list[dict]:
    unique_items: list[dict] = []
    seen: set[tuple] = set()
    for item in items:
        key = recent_activity_item_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items
