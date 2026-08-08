"""Repair missing manifest entries for existing RAG query synthesis files.

This is an additive repair: it reads existing SQLite rows and their JSON files,
adds only missing ``rag-query-synthesis`` entries, and never deletes or rewrites
research documents.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPORT_TYPE = "rag-query-synthesis"


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def synthesis_entry(row: sqlite3.Row, root: Path) -> dict[str, Any] | None:
    relative_path = str(row["source_relative_path"] or "").strip()
    json_relative_path = str(row["json_relative_path"] or "").strip()
    if not relative_path or not json_relative_path:
        return None
    markdown_path = (root / relative_path).resolve()
    json_path = (root / json_relative_path).resolve()
    try:
        markdown_path.relative_to(root.resolve())
        json_path.relative_to(root.resolve())
    except ValueError:
        return None
    if not markdown_path.is_file() or not json_path.is_file():
        return None
    payload = load_json(json_path)
    if not payload:
        return None
    ticker = str(row["ticker"] or "SEARCH").strip().upper() or "SEARCH"
    date = str(payload.get("date") or row["source_date"] or "").strip()
    tags = [str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()]
    return {
        "summary": payload.get("summary") or "",
        "source_count": int(payload.get("source_count") or 0),
        "candidate_count": int(payload.get("candidate_count") or 0),
        "grouped_count": int(payload.get("grouped_count") or 0),
        "source_confidence": payload.get("confidence"),
        "tags": list(dict.fromkeys(["rag_query_synthesis", "search", "synthesis", *tags])),
        "tickers": payload.get("tickers") if isinstance(payload.get("tickers"), list) else [],
        "consensus_facts": payload.get("consensus_facts") if isinstance(payload.get("consensus_facts"), list) else [],
        "bull_thesis": payload.get("bull_thesis") if isinstance(payload.get("bull_thesis"), list) else [],
        "bear_thesis": payload.get("bear_thesis") if isinstance(payload.get("bear_thesis"), list) else [],
        "cruxes": payload.get("cruxes") if isinstance(payload.get("cruxes"), list) else [],
        "observables": payload.get("observables") if isinstance(payload.get("observables"), list) else [],
        "query": str(payload.get("query") or "").strip(),
        "ticker": ticker,
        "type": REPORT_TYPE,
        "date": date,
        "file_name": str(row["source_file_name"] or markdown_path.name),
        "relative_path": relative_path,
        "json_file_name": json_path.name,
        "json_relative_path": json_relative_path,
    }


def collect_missing_entries(root: Path, manifest: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    manifest_paths = {
        str(item.get("relative_path") or "").strip()
        for item in manifest
        if str(item.get("type") or item.get("report_type") or "").strip().lower() == REPORT_TYPE
    }
    db_path = root / "research_vault" / "_system" / "research_memory.sqlite3"
    entries: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT ticker, source_file_name, source_relative_path,
                   json_relative_path, source_date
            FROM research_memory_documents
            WHERE report_type = ?
            ORDER BY source_date, source_relative_path
            """,
            (REPORT_TYPE,),
        ).fetchall()
    for row in rows:
        relative_path = str(row["source_relative_path"] or "").strip()
        if not relative_path or relative_path in manifest_paths:
            continue
        entry = synthesis_entry(row, root)
        if entry is not None:
            manifest_paths.add(relative_path)
            entries.append(entry)
    return entries, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="기존 RAG 합성 파일의 누락 manifest 항목을 추가합니다.")
    parser.add_argument("--write", action="store_true", help="누락 항목을 manifest.json에 추가합니다.")
    args = parser.parse_args()
    root = project_root(Path.cwd())
    manifest_path = root / "research_vault" / "manifest.json"
    manifest = read_manifest(manifest_path)
    missing, db_count = collect_missing_entries(root, manifest)
    if args.write and missing:
        next_manifest = [*manifest, *missing]
        next_manifest.sort(
            key=lambda item: (
                str(item.get("ticker") or ""),
                str(item.get("date") or ""),
                str(item.get("type") or ""),
                str(item.get("file_name") or ""),
            )
        )
        manifest_path.write_text(json.dumps(next_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "repaired" if args.write and missing else "dry_run",
                "manifest_path": str(manifest_path),
                "rag_synthesis_db_rows": db_count,
                "missing_entries": len(missing),
                "written": bool(args.write and missing),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
