"""Evidence document helpers for daily recommendations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


RAG_REPORT_TYPE_PRIORITY = {
    "public-ir-sec": 95,
    "earnings-filing-note": 92,
    "dart-filing-watch": 90,
    "official_filing": 88,
    "thesis-impact-review": 82,
    "collaborative-team-report": 78,
    "dossier-synthesis": 76,
    "research-capture": 72,
    "earnings-reaction": 70,
    "research-checklist": 65,
    "smart-trade-setup": 62,
}


def normalize_recommendation_ticker(value: object) -> str:
    text = str(value or "").strip().upper()
    return "".join(char for char in text if char.isalnum() or char in {".", "-", "_"})


def normalize_evidence_documents(value: object, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("source_relative_path") or item.get("relative_path") or "").strip()
        title = str(item.get("title") or item.get("source_file_name") or relative_path or "").strip()
        if not relative_path and not title:
            continue
        key = relative_path or title
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": title,
                "source_relative_path": relative_path,
                "source_date": str(item.get("source_date") or item.get("date") or "").strip(),
                "report_type": str(item.get("report_type") or "").strip(),
                "source_type": str(item.get("source_type") or "").strip(),
                "confidence": item.get("confidence"),
                "citation_label": str(item.get("citation_label") or "근거 문서").strip(),
                "matched_claims": [
                    str(claim).strip()
                    for claim in item.get("matched_claims", [])
                    if str(claim or "").strip()
                ][:3],
            }
        )
    return rows[: max(1, min(limit, 10))]


def unique_text_items(values: list | tuple | None, limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for value in values or []:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text, None)
    return list(seen.keys())[:limit]


def safe_float(value: object, default: float = 0.7) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def json_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def evidence_document_claims(document: dict[str, Any], claims: list[str]) -> list[str]:
    report_type = str(document.get("report_type") or "").lower()
    source_type = str(document.get("source_type") or "").lower()
    haystack = " ".join(
        str(document.get(key) or "")
        for key in ("title", "summary", "content_excerpt", "source_file_name", "source_relative_path")
    ).lower()
    matched: list[str] = []
    for claim in claims:
        claim_text = str(claim or "").strip()
        if not claim_text:
            continue
        claim_lower = claim_text.lower()
        if "공개 ir/sec" in claim_lower and ("public-ir-sec" in report_type or "sec" in source_type):
            matched.append(claim_text)
        elif "공시" in claim_lower and ("filing" in source_type or "dart" in report_type):
            matched.append(claim_text)
        elif "목표가" in claim_lower or "리포트" in claim_lower:
            if report_type in {"thesis-impact-review", "collaborative-team-report", "dossier-synthesis", "research-capture"}:
                matched.append(claim_text)
        elif "최근 근거 파일" in claim_lower and str(document.get("source_relative_path") or "").split("/")[-1].lower() in claim_lower:
            matched.append(claim_text)
        elif "rag 연결" in claim_lower:
            matched.append(claim_text)
        else:
            tokens = [token for token in claim_lower.replace("/", " ").replace(":", " ").split() if len(token) >= 4]
            if tokens and any(token in haystack for token in tokens[:8]):
                matched.append(claim_text)
    return list(dict.fromkeys(matched))[:3]


def _rank_evidence_rows(rows: list[Any], claims: list[str], limit: int) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        payload = dict(row)
        tags = [str(tag) for tag in json_list(payload.get("tags_json"))]
        if "archived" in {tag.lower() for tag in tags}:
            continue
        report_type = str(payload.get("report_type") or "")
        source_type = str(payload.get("source_type") or "")
        matched_claims = evidence_document_claims(payload, claims)
        priority = RAG_REPORT_TYPE_PRIORITY.get(report_type, RAG_REPORT_TYPE_PRIORITY.get(source_type, 55))
        confidence = safe_float(payload.get("confidence"), 0.7)
        claim_bonus = len(matched_claims) * 12
        text_length_bonus = min(len(str(payload.get("content_excerpt") or "")) / 400, 6)
        score = priority + (confidence * 10) + claim_bonus + text_length_bonus
        scored.append(
            (
                score,
                {
                    "title": str(payload.get("title") or payload.get("source_file_name") or "").strip(),
                    "source_relative_path": str(payload.get("source_relative_path") or "").strip(),
                    "json_relative_path": str(payload.get("json_relative_path") or "").strip(),
                    "source_date": str(payload.get("source_date") or "").strip(),
                    "report_type": report_type,
                    "source_type": source_type,
                    "confidence": confidence,
                    "citation_label": "RAG 근거 문서",
                    "matched_claims": matched_claims,
                },
            )
        )
    scored.sort(key=lambda item: (item[0], item[1].get("source_date") or ""), reverse=True)
    return normalize_evidence_documents([item for _, item in scored], limit=limit)


def build_daily_recommendation_evidence_documents(
    vault_dir: Path,
    ticker: str,
    evidence_sources: list[str] | tuple[str, ...] | None,
    reasons: list[str] | tuple[str, ...] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return representative RAG documents that support a recommendation record."""
    normalized_ticker = normalize_recommendation_ticker(ticker)
    if not normalized_ticker:
        return []
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path, timeout=30) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 30000")
            rows = connection.execute(
                """
                SELECT ticker, report_type, title, summary, content_excerpt, source_type,
                       source_file_name, source_relative_path, json_relative_path,
                       source_date, confidence, tags_json, updated_at
                FROM research_memory_documents
                WHERE upper(ticker) = ?
                ORDER BY source_date DESC, updated_at DESC
                LIMIT 80
                """,
                (normalized_ticker,),
            ).fetchall()
    except sqlite3.Error:
        return []

    claims = [str(item).strip() for item in [*(evidence_sources or []), *(reasons or [])] if str(item or "").strip()]
    return _rank_evidence_rows(rows, claims, limit)


def build_daily_recommendation_evidence_documents_batch(
    vault_dir: Path,
    requests: dict[str, tuple[list[str] | tuple[str, ...] | None, list[str] | tuple[str, ...] | None]],
    limit: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Load RAG evidence for many recommendation candidates with one SQLite read."""
    normalized_requests = {
        normalize_recommendation_ticker(ticker): (evidence_sources, reasons)
        for ticker, (evidence_sources, reasons) in requests.items()
        if normalize_recommendation_ticker(ticker)
    }
    if not normalized_requests:
        return {}
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return {ticker: [] for ticker in normalized_requests}
    tickers = sorted(normalized_requests)
    placeholders = ",".join("?" for _ in tickers)
    rows_by_ticker: dict[str, list[Any]] = {ticker: [] for ticker in tickers}
    try:
        with sqlite3.connect(db_path, timeout=30) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 30000")
            # Ticker values are normalized to uppercase when documents are stored.
            # Keep the predicate sargable so SQLite can use idx_rag_docs_ticker_date;
            # the window limit also avoids loading every historical document for a
            # ticker when the ranking only needs the same latest 80 rows as the
            # single-ticker query.
            rows = connection.execute(
                f"""
                SELECT ticker, report_type, title, summary, content_excerpt, source_type,
                       source_file_name, source_relative_path, json_relative_path,
                       source_date, confidence, tags_json, updated_at
                FROM (
                    SELECT ticker, report_type, title, summary, content_excerpt, source_type,
                           source_file_name, source_relative_path, json_relative_path,
                           source_date, confidence, tags_json, updated_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY ticker
                               ORDER BY source_date DESC, updated_at DESC
                           ) AS row_number
                    FROM research_memory_documents
                    WHERE ticker IN ({placeholders})
                )
                WHERE row_number <= 80
                ORDER BY ticker, source_date DESC, updated_at DESC
                """,
                tickers,
            ).fetchall()
    except sqlite3.Error:
        return {ticker: [] for ticker in normalized_requests}
    for row in rows:
        ticker = normalize_recommendation_ticker(row["ticker"])
        if ticker in rows_by_ticker and len(rows_by_ticker[ticker]) < 80:
            rows_by_ticker[ticker].append(row)
    results: dict[str, list[dict[str, Any]]] = {}
    for ticker, (evidence_sources, reasons) in normalized_requests.items():
        claims = [
            str(item).strip()
            for item in [*(evidence_sources or []), *(reasons or [])]
            if str(item or "").strip()
        ]
        results[ticker] = _rank_evidence_rows(rows_by_ticker[ticker], claims, limit)
    return results
