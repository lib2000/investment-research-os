from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from research_os.models import InvestmentThesis, WatchItem
from research_os.research_memory import read_manifest


SCHEMA_VERSION = 2


def rag_db_path(vault_dir: Path) -> Path:
    return vault_dir / "_system" / "research_memory.sqlite3"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_load_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _json_load_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


def _safe_float(value: Any, fallback: float = 0.7) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def _document_id_from_entry(entry: dict[str, Any]) -> str:
    relative_path = _safe_text(entry.get("relative_path"))
    if relative_path:
        return relative_path
    return "|".join(
        [
            _safe_text(entry.get("ticker"), "UNKNOWN"),
            _safe_text(entry.get("type") or entry.get("report_type"), "unknown"),
            _safe_text(entry.get("date"), "undated"),
            _safe_text(entry.get("file_name"), "missing-file"),
        ]
    )


def _resolve_manifest_file(vault_dir: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    candidate = (vault_dir.parent / relative_path).resolve()
    try:
        candidate.relative_to(vault_dir.parent.resolve())
    except ValueError:
        return None
    return candidate


def _read_manifest_text(
    vault_dir: Path,
    entry: dict[str, Any],
    max_chars: int = 12000,
) -> str:
    path = _resolve_manifest_file(vault_dir, entry.get("relative_path"))
    if path and path.exists() and path.is_file():
        try:
            return path.read_text(encoding="utf-8")[:max_chars]
        except OSError:
            pass
    return _safe_text(entry.get("summary") or entry.get("title") or "")


def _entry_tags(entry: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for key in ("tags", "theme_tags", "categories"):
        value = entry.get(key)
        if isinstance(value, list):
            tags.extend(_safe_text(item) for item in value if _safe_text(item))
    for key in ("type", "report_type", "source_type"):
        value = _safe_text(entry.get(key))
        if value:
            tags.append(value)
    return sorted(set(tags))


def _document_quality(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = _json_load_dict(payload.get("metadata_json"))

    text = " ".join(
        [
            _safe_text(payload.get("summary")),
            _safe_text(payload.get("content_excerpt")),
            _safe_text(metadata.get("reaction_type")),
            _safe_text(metadata.get("evidence_status")),
        ]
    )
    flags: list[str] = []
    score = int(round(_safe_float(payload.get("confidence"), 0.7) * 100))

    if metadata.get("data_quality") == "low":
        score -= 10
        flags.append("low_data_quality")

    missing_inputs = metadata.get("missing_inputs")
    if isinstance(missing_inputs, list) and missing_inputs:
        score -= min(25, 8 * len(missing_inputs))
        flags.append("missing_inputs")

    if "입력 데이터가 부족" in text or "데이터 부족" in text:
        score -= 35
        flags.append("insufficient_data")

    if "판정 보류" in text:
        score -= 20
        flags.append("deferred_judgement")

    if metadata.get("evidence_status") == "충분":
        score += 25
        flags.append("sufficient_evidence")

    if metadata.get("is_deleted") or _safe_text(metadata.get("status")).lower() == "archived":
        score -= 80
        flags.append("archived")

    report_type = _safe_text(payload.get("report_type"))
    if report_type == "earnings-reaction":
        if metadata.get("earnings_report_date"):
            score += 8
        else:
            score -= 15
            flags.append("missing_earnings_date")
        if _safe_text(metadata.get("price_reaction")):
            score += 8
        else:
            score -= 10
            flags.append("missing_price_reaction")
        if _safe_text(metadata.get("next_earnings_guidance")) and "입력되지 않았습니다" not in _safe_text(
            metadata.get("next_earnings_guidance")
        ):
            score += 8
        else:
            score -= 10
            flags.append("missing_next_guidance")

    return {
        "quality_score": max(0, min(150, score)),
        "quality_flags": sorted(set(flags)),
        "is_injectable": score >= 55 and "insufficient_data" not in flags and "archived" not in flags,
    }


def _connect(vault_dir: Path) -> sqlite3.Connection:
    path = rag_db_path(vault_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def connect_rag_db(vault_dir: Path) -> Iterator[sqlite3.Connection]:
    connection = _connect(vault_dir)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_rag_db(vault_dir: Path) -> None:
    with connect_rag_db(vault_dir) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ticker_thesis_snapshots (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                thesis_summary TEXT NOT NULL,
                investment_thesis_json TEXT NOT NULL,
                bull_triggers_json TEXT NOT NULL,
                bear_triggers_json TEXT NOT NULL,
                invalidation_conditions_json TEXT NOT NULL,
                watch_kpis_json TEXT NOT NULL,
                watch_items_json TEXT NOT NULL,
                source_report_type TEXT,
                source_file_name TEXT,
                source_relative_path TEXT,
                source_date TEXT,
                source_updated_at TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.8,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research_memory_documents (
                document_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'ticker',
                report_type TEXT,
                title TEXT,
                summary TEXT,
                content_excerpt TEXT,
                full_text TEXT,
                source_type TEXT,
                source_file_name TEXT,
                source_relative_path TEXT,
                json_file_name TEXT,
                json_relative_path TEXT,
                source_date TEXT,
                confidence REAL NOT NULL DEFAULT 0.7,
                tags_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rag_docs_ticker_date
            ON research_memory_documents(ticker, source_date DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_rag_docs_type
            ON research_memory_documents(report_type)
            """
        )
        connection.execute(
            """
            INSERT INTO rag_schema_meta(key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )


def upsert_ticker_thesis_snapshot(
    *,
    vault_dir: Path,
    ticker: str,
    company_name: str | None,
    investment_thesis: InvestmentThesis,
    watch_items: list[WatchItem] | None = None,
    source_entry: dict[str, Any] | None = None,
    confidence: float = 0.8,
) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    normalized_ticker = ticker.strip().upper()
    source_entry = source_entry or {}
    watch_items = watch_items or []
    now = _utc_now_iso()
    thesis_payload = investment_thesis.model_dump(mode="json")
    watch_payload = [item.model_dump(mode="json") for item in watch_items]

    row = {
        "ticker": normalized_ticker,
        "company_name": company_name,
        "thesis_summary": investment_thesis.thesis,
        "investment_thesis_json": _json_dump(thesis_payload),
        "bull_triggers_json": _json_dump(investment_thesis.bull_triggers),
        "bear_triggers_json": _json_dump(investment_thesis.bear_triggers),
        "invalidation_conditions_json": _json_dump(
            investment_thesis.invalidation_conditions
        ),
        "watch_kpis_json": _json_dump(investment_thesis.watch_kpis),
        "watch_items_json": _json_dump(watch_payload),
        "source_report_type": source_entry.get("type") or source_entry.get("report_type"),
        "source_file_name": source_entry.get("file_name"),
        "source_relative_path": source_entry.get("relative_path"),
        "source_date": source_entry.get("date") or investment_thesis.last_updated,
        "source_updated_at": source_entry.get("updated_at") or now,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "updated_at": now,
    }

    with connect_rag_db(vault_dir) as connection:
        connection.execute(
            """
            INSERT INTO ticker_thesis_snapshots (
                ticker,
                company_name,
                thesis_summary,
                investment_thesis_json,
                bull_triggers_json,
                bear_triggers_json,
                invalidation_conditions_json,
                watch_kpis_json,
                watch_items_json,
                source_report_type,
                source_file_name,
                source_relative_path,
                source_date,
                source_updated_at,
                confidence,
                updated_at
            )
            VALUES (
                :ticker,
                :company_name,
                :thesis_summary,
                :investment_thesis_json,
                :bull_triggers_json,
                :bear_triggers_json,
                :invalidation_conditions_json,
                :watch_kpis_json,
                :watch_items_json,
                :source_report_type,
                :source_file_name,
                :source_relative_path,
                :source_date,
                :source_updated_at,
                :confidence,
                :updated_at
            )
            ON CONFLICT(ticker) DO UPDATE SET
                company_name = excluded.company_name,
                thesis_summary = excluded.thesis_summary,
                investment_thesis_json = excluded.investment_thesis_json,
                bull_triggers_json = excluded.bull_triggers_json,
                bear_triggers_json = excluded.bear_triggers_json,
                invalidation_conditions_json = excluded.invalidation_conditions_json,
                watch_kpis_json = excluded.watch_kpis_json,
                watch_items_json = excluded.watch_items_json,
                source_report_type = excluded.source_report_type,
                source_file_name = excluded.source_file_name,
                source_relative_path = excluded.source_relative_path,
                source_date = excluded.source_date,
                source_updated_at = excluded.source_updated_at,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            row,
        )
    return row


def read_ticker_thesis_snapshot(vault_dir: Path, ticker: str) -> dict[str, Any] | None:
    initialize_rag_db(vault_dir)
    normalized_ticker = ticker.strip().upper()
    with connect_rag_db(vault_dir) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM ticker_thesis_snapshots
            WHERE ticker = ?
            """,
            (normalized_ticker,),
        ).fetchone()
    if row is None:
        return None

    payload = dict(row)
    try:
        payload["investment_thesis"] = json.loads(payload["investment_thesis_json"])
    except json.JSONDecodeError:
        payload["investment_thesis"] = None
    payload["bull_triggers"] = _json_load_list(payload.get("bull_triggers_json"))
    payload["bear_triggers"] = _json_load_list(payload.get("bear_triggers_json"))
    payload["invalidation_conditions"] = _json_load_list(
        payload.get("invalidation_conditions_json")
    )
    payload["watch_kpis"] = _json_load_list(payload.get("watch_kpis_json"))
    payload["watch_items"] = _json_load_list(payload.get("watch_items_json"))
    return payload


def read_ticker_thesis_context(
    vault_dir: Path,
    ticker: str,
) -> tuple[list[InvestmentThesis], list[WatchItem]]:
    snapshot = read_ticker_thesis_snapshot(vault_dir, ticker)
    if not snapshot or not snapshot.get("investment_thesis"):
        return [], []

    thesis = InvestmentThesis(**snapshot["investment_thesis"])
    watch_items = [
        WatchItem(**item)
        for item in snapshot.get("watch_items", [])
        if isinstance(item, dict)
    ]
    return [thesis], watch_items


def backfill_thesis_snapshots_from_manifest(vault_dir: Path) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    latest_by_ticker: dict[str, dict[str, Any]] = {}
    for entry in read_manifest(vault_dir):
        ticker = str(entry.get("ticker") or "").strip().upper()
        if not ticker or not isinstance(entry.get("investment_thesis"), dict):
            continue
        existing = latest_by_ticker.get(ticker)
        current_key = (
            str(entry.get("date") or ""),
            str(entry.get("file_name") or ""),
        )
        existing_key = (
            str(existing.get("date") or "") if existing else "",
            str(existing.get("file_name") or "") if existing else "",
        )
        if existing is None or current_key >= existing_key:
            latest_by_ticker[ticker] = entry

    updated = []
    for ticker, entry in latest_by_ticker.items():
        thesis = InvestmentThesis(**entry["investment_thesis"])
        watch_items = [
            WatchItem(**item)
            for item in entry.get("watch_items", [])
            if isinstance(item, dict)
        ]
        upsert_ticker_thesis_snapshot(
            vault_dir=vault_dir,
            ticker=ticker,
            company_name=entry.get("company_name"),
            investment_thesis=thesis,
            watch_items=watch_items,
            source_entry=entry,
            confidence=float(entry.get("source_confidence") or 0.8),
        )
        updated.append(ticker)

    return {
        "status": "success",
        "updated_count": len(updated),
        "tickers": sorted(updated),
    }


def upsert_research_memory_document(
    *,
    vault_dir: Path,
    entry: dict[str, Any],
    full_text: str | None = None,
) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    ticker = _safe_text(entry.get("ticker"), "GENERAL").upper()
    report_type = _safe_text(entry.get("type") or entry.get("report_type"), "research")
    text = full_text if full_text is not None else _read_manifest_text(vault_dir, entry)
    summary = _safe_text(entry.get("summary"))
    if not summary:
        summary = " ".join(text.split())[:360]
    title = _safe_text(entry.get("title") or entry.get("file_name") or report_type)
    now = _utc_now_iso()

    row = {
        "document_id": _document_id_from_entry(entry),
        "ticker": ticker,
        "scope": _safe_text(entry.get("scope"), "ticker"),
        "report_type": report_type,
        "title": title,
        "summary": summary,
        "content_excerpt": text[:1600],
        "full_text": text,
        "source_type": _safe_text(entry.get("source_type")),
        "source_file_name": _safe_text(entry.get("file_name")),
        "source_relative_path": _safe_text(entry.get("relative_path")),
        "json_file_name": _safe_text(entry.get("json_file_name")),
        "json_relative_path": _safe_text(entry.get("json_relative_path")),
        "source_date": _safe_text(entry.get("date")),
        "confidence": _safe_float(
            entry.get("source_confidence") or entry.get("confidence"),
            0.7,
        ),
        "tags_json": _json_dump(_entry_tags(entry)),
        "metadata_json": _json_dump(
            {
                key: value
                for key, value in entry.items()
                if key
                not in {
                    "investment_thesis",
                    "watch_items",
                    "summary",
                    "title",
                }
            }
        ),
        "updated_at": now,
    }

    with connect_rag_db(vault_dir) as connection:
        connection.execute(
            """
            INSERT INTO research_memory_documents (
                document_id,
                ticker,
                scope,
                report_type,
                title,
                summary,
                content_excerpt,
                full_text,
                source_type,
                source_file_name,
                source_relative_path,
                json_file_name,
                json_relative_path,
                source_date,
                confidence,
                tags_json,
                metadata_json,
                updated_at
            )
            VALUES (
                :document_id,
                :ticker,
                :scope,
                :report_type,
                :title,
                :summary,
                :content_excerpt,
                :full_text,
                :source_type,
                :source_file_name,
                :source_relative_path,
                :json_file_name,
                :json_relative_path,
                :source_date,
                :confidence,
                :tags_json,
                :metadata_json,
                :updated_at
            )
            ON CONFLICT(document_id) DO UPDATE SET
                ticker = excluded.ticker,
                scope = excluded.scope,
                report_type = excluded.report_type,
                title = excluded.title,
                summary = excluded.summary,
                content_excerpt = excluded.content_excerpt,
                full_text = excluded.full_text,
                source_type = excluded.source_type,
                source_file_name = excluded.source_file_name,
                source_relative_path = excluded.source_relative_path,
                json_file_name = excluded.json_file_name,
                json_relative_path = excluded.json_relative_path,
                source_date = excluded.source_date,
                confidence = excluded.confidence,
                tags_json = excluded.tags_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            row,
        )
    return row


def backfill_research_memory_documents_from_manifest(vault_dir: Path) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    updated: list[str] = []
    tickers: set[str] = set()
    for entry in read_manifest(vault_dir):
        if not isinstance(entry, dict):
            continue
        row = upsert_research_memory_document(vault_dir=vault_dir, entry=entry)
        updated.append(row["document_id"])
        tickers.add(row["ticker"])

    return {
        "status": "success",
        "updated_count": len(updated),
        "tickers": sorted(tickers),
        "documents": updated,
    }


def _row_to_document(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["tags"] = _json_load_list(payload.pop("tags_json", None))
    payload["metadata"] = _json_load_dict(payload.pop("metadata_json", None))
    payload.update(_document_quality(payload))
    payload.pop("full_text", None)
    return payload


def _compact_related_search_documents(
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


def _match_strength(matched_count: int, term_count: int) -> str:
    if term_count <= 0:
        return "전체"
    if matched_count >= term_count:
        return "완전"
    if matched_count > 0:
        return "부분"
    return "없음"


def search_research_memory_documents(
    vault_dir: Path,
    key: str,
    query: str | None = None,
    limit: int = 5,
    include_low_quality: bool = False,
) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    # Opportunistic backfill keeps the DB useful even when new reports were saved
    # before the document index existed.
    backfill_research_memory_documents_from_manifest(vault_dir)

    normalized_key = key.strip().upper()
    normalized_query = (query or "").strip().lower()
    terms = [term for term in normalized_query.split() if term]
    with connect_rag_db(vault_dir) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM research_memory_documents
            WHERE ticker = ?
            ORDER BY source_date DESC, updated_at DESC
            """,
            (normalized_key,),
        ).fetchall()

    scored: list[tuple[int, int, sqlite3.Row]] = []
    for row in rows:
        payload = dict(row)
        quality = _document_quality(payload)
        if not include_low_quality and not quality["is_injectable"]:
            continue
        haystack = " ".join(
            _safe_text(row[key])
            for key in ("title", "summary", "content_excerpt", "report_type", "source_type")
        ).lower()
        score = sum(1 for term in terms if term in haystack)
        if terms and score == 0:
            continue
        scored.append((score, int(quality["quality_score"]), row))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
            _safe_text(item[2]["source_date"]),
            _safe_text(item[2]["updated_at"]),
        ),
        reverse=True,
    )
    documents = []
    for score, _, row in scored[: max(1, min(limit * 3, 50))]:
        document = _row_to_document(row)
        document["match_strength"] = _match_strength(score, len(terms))
        documents.append(document)
    documents, grouped = _compact_related_search_documents(documents, limit=limit)
    return {
        "status": "success",
        "module": "rag_memory_search",
        "key": normalized_key,
        "query": query,
        "include_low_quality": include_low_quality,
        "count": len(documents),
        "grouped_count": grouped,
        "documents": documents,
    }


def search_all_research_memory_documents(
    vault_dir: Path,
    query: str,
    limit: int = 12,
    include_low_quality: bool = False,
) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    backfill_research_memory_documents_from_manifest(vault_dir)

    normalized_query = (query or "").strip().lower()
    terms = [term for term in normalized_query.split() if term]
    if not terms:
        return {
            "status": "success",
            "module": "rag_memory_global_search",
            "query": query,
            "include_low_quality": include_low_quality,
            "count": 0,
            "documents": [],
        }

    with connect_rag_db(vault_dir) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM research_memory_documents
            ORDER BY source_date DESC, updated_at DESC
            LIMIT 2500
            """
        ).fetchall()

    scored: list[tuple[int, int, str, str, sqlite3.Row, list[str]]] = []
    for row in rows:
        payload = dict(row)
        quality = _document_quality(payload)
        if not include_low_quality and not quality["is_injectable"]:
            continue

        tags = _json_load_list(payload.get("tags_json"))
        metadata = _json_load_dict(payload.get("metadata_json"))
        haystack = " ".join(
            [
                _safe_text(payload.get("ticker")),
                _safe_text(payload.get("title")),
                _safe_text(payload.get("summary")),
                _safe_text(payload.get("content_excerpt")),
                _safe_text(payload.get("report_type")),
                _safe_text(payload.get("source_type")),
                _safe_text(metadata.get("company_name")),
                _safe_text(metadata.get("source_url")),
                " ".join(_safe_text(tag) for tag in tags),
            ]
        ).lower()
        matched_terms = [term for term in terms if term in haystack]
        if not matched_terms:
            continue

        all_terms_bonus = 20 if len(matched_terms) == len(terms) else 0
        title_bonus = sum(
            8
            for term in matched_terms
            if term in _safe_text(payload.get("title")).lower()
        )
        ticker_bonus = 10 if normalized_query == _safe_text(payload.get("ticker")).lower() else 0
        relevance_score = len(matched_terms) * 12 + all_terms_bonus + title_bonus + ticker_bonus
        scored.append(
            (
                relevance_score,
                int(quality["quality_score"]),
                _safe_text(payload.get("source_date")),
                _safe_text(payload.get("updated_at")),
                row,
                matched_terms,
            )
        )

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    documents = []
    for relevance_score, _, _, _, row, matched_terms in scored[: max(1, min(limit * 3, 80))]:
        document = _row_to_document(row)
        document["relevance_score"] = relevance_score
        document["matched_terms"] = matched_terms
        document["match_strength"] = _match_strength(len(matched_terms), len(terms))
        documents.append(document)
    documents, grouped = _compact_related_search_documents(documents, limit=limit)

    return {
        "status": "success",
        "module": "rag_memory_global_search",
        "query": query,
        "include_low_quality": include_low_quality,
        "count": len(documents),
        "grouped_count": grouped,
        "documents": documents,
    }


def count_research_memory_documents_by_ticker(
    vault_dir: Path,
    tickers: list[str],
    include_low_quality: bool = False,
) -> dict[str, int]:
    initialize_rag_db(vault_dir)
    backfill_research_memory_documents_from_manifest(vault_dir)
    normalized_tickers = sorted({ticker.strip().upper() for ticker in tickers if ticker.strip()})
    if not normalized_tickers:
        return {}

    placeholders = ",".join("?" for _ in normalized_tickers)
    with connect_rag_db(vault_dir) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM research_memory_documents
            WHERE ticker IN ({placeholders})
            """,
            normalized_tickers,
        ).fetchall()

    counts = {ticker: 0 for ticker in normalized_tickers}
    for row in rows:
        payload = dict(row)
        quality = _document_quality(payload)
        if not include_low_quality and not quality["is_injectable"]:
            continue
        ticker = _safe_text(row["ticker"]).upper()
        counts[ticker] = counts.get(ticker, 0) + 1
    return counts


def rag_memory_status(vault_dir: Path) -> dict[str, Any]:
    initialize_rag_db(vault_dir)
    with connect_rag_db(vault_dir) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS snapshot_count, MAX(updated_at) AS latest_updated_at
            FROM ticker_thesis_snapshots
            """
        ).fetchone()
        document_row = connection.execute(
            """
            SELECT COUNT(*) AS document_count, MAX(updated_at) AS latest_document_updated_at
            FROM research_memory_documents
            """
        ).fetchone()
    return {
        "status": "success",
        "schema_version": SCHEMA_VERSION,
        "db_path": str(rag_db_path(vault_dir)),
        "snapshot_count": int(row["snapshot_count"] if row else 0),
        "document_count": int(
            document_row["document_count"] if document_row else 0
        ),
        "latest_updated_at": row["latest_updated_at"] if row else None,
        "latest_document_updated_at": (
            document_row["latest_document_updated_at"] if document_row else None
        ),
    }
