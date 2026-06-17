"""RAG search result compaction helpers."""

from __future__ import annotations

from typing import Any


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def compact_related_search_documents(
    documents: list[dict[str, Any]],
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Collapse repeated generated reports so search results show the newest useful item first."""

    grouped_types = {
        "dossier-synthesis",
        "daily-briefing",
        "collaborative-team-report",
        "thesis-impact-review",
    }
    visible: list[dict[str, Any]] = []
    by_group: dict[tuple[str, str], dict[str, Any]] = {}
    grouped_count = 0

    for document in documents:
        report_type = _safe_text(document.get("report_type"))
        ticker = _safe_text(document.get("ticker") or "GENERAL")
        group_key = (ticker, report_type)

        if report_type not in grouped_types:
            visible.append(document)
            continue

        existing = by_group.get(group_key)
        if existing is None:
            document["related_version_count"] = 0
            document["related_versions"] = []
            by_group[group_key] = document
            visible.append(document)
            continue

        grouped_count += 1
        related = existing.setdefault("related_versions", [])
        related.append(
            {
                "title": document.get("title"),
                "source_file_name": document.get("source_file_name"),
                "source_relative_path": document.get("source_relative_path"),
                "source_date": document.get("source_date"),
                "quality_score": document.get("quality_score"),
                "relevance_score": document.get("relevance_score"),
                "matched_terms": document.get("matched_terms", []),
                "summary": document.get("summary"),
            }
        )
        existing["related_version_count"] = len(related)

    max_items = max(1, min(limit, 50))
    return visible[:max_items], grouped_count


def match_strength(matched_count: int, term_count: int) -> str:
    if term_count <= 0:
        return "전체"
    if matched_count >= term_count:
        return "완전"
    if matched_count > 0:
        return "부분"
    return "없음"