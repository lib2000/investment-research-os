"""Storage helpers for RAG query synthesis reports."""

from __future__ import annotations

from re import sub


_NON_TICKER_STORAGE_KEYS = {"SEARCH", "MARKET", "GENERAL", "UNKNOWN"}


def _query_file_suffix(query: str, max_length: int = 96) -> str:
    safe = sub(r"[^A-Za-z0-9._-]+", "-", str(query or "").strip().lower()).strip("-")
    if not safe:
        return "search"
    return safe[:max_length].rstrip("-") or "search"


def build_rag_query_synthesis_manifest_extra(*, query: str, payload: dict) -> dict:
    return {
        "summary": payload["summary"],
        "query": query,
        "source_count": payload["source_count"],
        "candidate_count": payload["candidate_count"],
        "grouped_count": payload["grouped_count"],
        "source_confidence": payload["confidence"],
        "tags": ["rag_query_synthesis", "search", "synthesis", *payload["tags"][:10]],
        "tickers": payload["tickers"],
        "consensus_facts": payload["consensus_facts"],
        "bull_thesis": payload["bull_thesis"],
        "bear_thesis": payload["bear_thesis"],
        "cruxes": payload["cruxes"],
        "observables": payload["observables"],
    }


def save_rag_query_synthesis_result(runtime, *, vault_dir, query: str, payload: dict) -> dict:
    storage_key = runtime.rag_synthesis_storage_key(payload["source_documents"])
    storage_date = runtime.current_storage_date()
    thesis = None
    watch_items = []
    manifest_extra = build_rag_query_synthesis_manifest_extra(query=query, payload=payload)
    if storage_key not in _NON_TICKER_STORAGE_KEYS:
        thesis, watch_items = runtime.build_rag_query_synthesis_thesis(
            storage_key,
            payload,
            watch_kpis=runtime.ticker_watch_kpis(storage_key),
        )
        manifest_extra["investment_thesis"] = thesis.model_dump(mode="json")
        manifest_extra["watch_items"] = [item.model_dump(mode="json") for item in watch_items]

    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=storage_key,
        report_type="rag-query-synthesis",
        markdown=runtime.render_rag_query_synthesis_markdown(payload),
        structured_payload=payload,
        manifest_entry=manifest_extra,
        report_date=storage_date,
        file_suffix=_query_file_suffix(query),
    )
    rag_document = None
    thesis_snapshot = None
    if storage:
        saved_entry = next(
            (
                entry
                for entry in runtime.read_manifest(vault_dir)
                if entry.get("file_name") == storage.file_name
                and str(entry.get("ticker") or "").upper() == storage_key
            ),
            None,
        )
        if saved_entry:
            rag_document = runtime.upsert_research_memory_document(
                vault_dir=vault_dir,
                entry=saved_entry,
            )
    if thesis is not None and storage is not None:
        thesis_snapshot = runtime.upsert_ticker_thesis_snapshot(
            vault_dir=vault_dir,
            ticker=storage_key,
            company_name=runtime.ticker_company_name(storage_key),
            investment_thesis=thesis,
            watch_items=watch_items,
            source_entry={
                "type": "rag-query-synthesis",
                "date": payload["date"],
                "file_name": storage.file_name,
                "relative_path": storage.relative_path,
            },
            confidence=payload["confidence"],
        )

    return {
        "storage_key": storage_key,
        "storage": storage,
        "rag_document": rag_document,
        "thesis_snapshot": thesis_snapshot,
    }
