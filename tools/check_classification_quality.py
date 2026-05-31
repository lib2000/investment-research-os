"""Validate auto-classification tags, rationale, and RAG coverage.

This script is intentionally read-only. It checks the research vault manifest and
RAG SQLite store for the system tags that make automatic classification auditable
in the console: source_type, research_scope, and auto_scope/auto_ticker reasons.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPECIAL_RESEARCH_KEYS = {
    "INBOX",
    "MACRO",
    "SECTOR",
    "MARKET",
    "MARKET-US",
    "MARKET-KR",
    "MARKET-GLOBAL",
    "POLICY",
    "RATES",
    "FLOWS",
    "CUSTOMS",
}


def load_manifest(vault_dir: Path) -> list[dict]:
    path = vault_dir / "manifest.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def is_archived(entry: dict) -> bool:
    tags = {str(tag).lower() for tag in (entry.get("tags") or [])}
    return bool(entry.get("archived") or entry.get("status") == "archived" or "archived" in tags)


def is_classified_entry(entry: dict) -> bool:
    tags = {str(tag) for tag in (entry.get("tags") or [])}
    return bool(
        "auto_classified" in tags
        or "auto_ingested" in tags
        or entry.get("module") == "research_quick_capture"
        or entry.get("type") == "research-capture"
    )


def entry_file_exists(root: Path, entry: dict) -> bool:
    relative = entry.get("relative_path")
    if not relative:
        return False
    return (root / str(relative)).exists()


def load_rag_document_ids(vault_dir: Path) -> set[str]:
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return set()
    try:
        with sqlite3.connect(db_path) as connection:
            rows = connection.execute("SELECT document_id FROM research_memory_documents").fetchall()
    except sqlite3.OperationalError as exc:
        if "readonly" not in str(exc).lower():
            raise
        uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
        with sqlite3.connect(uri, uri=True) as connection:
            rows = connection.execute("SELECT document_id FROM research_memory_documents").fetchall()
    return {str(row[0]) for row in rows if row and row[0]}


def document_id(entry: dict) -> str:
    return str(entry.get("relative_path") or entry.get("file_name") or "")


def evaluate(vault_dir: Path, *, strict: bool = False) -> int:
    manifest = load_manifest(vault_dir)
    active = [entry for entry in manifest if not is_archived(entry)]
    classified = [entry for entry in active if is_classified_entry(entry)]
    rag_ids = load_rag_document_ids(vault_dir)

    missing_tags: list[dict] = []
    missing_source_type_tag: list[dict] = []
    missing_source_type_field: list[dict] = []
    missing_confidence: list[dict] = []
    missing_scope_tag: list[dict] = []
    missing_reason_tag: list[dict] = []
    missing_files: list[dict] = []
    missing_rag: list[dict] = []
    tag_counter: Counter[str] = Counter()

    for entry in classified:
        tags = [str(tag) for tag in (entry.get("tags") or []) if str(tag).strip()]
        tag_set = set(tags)
        tag_counter.update(tags)
        ticker = str(entry.get("ticker") or "").upper()
        source_type = str(entry.get("source_type") or "").strip()
        if not tags:
            missing_tags.append(entry)
        if not source_type:
            # Dossier and old derived reports can inherit auto tags from source material.
            if entry.get("type") == "research-capture" or entry.get("module") == "research_quick_capture":
                missing_source_type_field.append(entry)
        if source_type and not any(tag.startswith("source_type:") for tag in tags):
            missing_source_type_tag.append(entry)
        if entry.get("confidence") is None and entry.get("source_confidence") is None:
            missing_confidence.append(entry)
        if ticker in SPECIAL_RESEARCH_KEYS and ticker != "INBOX" and not any(tag == f"research_scope:{ticker.lower()}" for tag in tags):
            missing_scope_tag.append(entry)
        if ("auto_classified" in tag_set or "auto_ingested" in tag_set) and not any(
            tag.startswith("auto_ticker:") or tag.startswith("auto_scope:") for tag in tags
        ):
            missing_reason_tag.append(entry)
        if not entry_file_exists(PROJECT_ROOT, entry):
            missing_files.append(entry)
        if entry.get("type") == "research-capture" and document_id(entry) not in rag_ids:
            missing_rag.append(entry)

    print(f"manifest: {len(manifest)}개 | active: {len(active)}개 | classified: {len(classified)}개")
    print(f"RAG 문서: {len(rag_ids)}개")
    print(f"태그 상위: {', '.join(f'{tag}={count}' for tag, count in tag_counter.most_common(12))}")
    checks = [
        ("태그 누락", missing_tags),
        ("source_type 필드 누락", missing_source_type_field),
        ("source_type:* 태그 누락", missing_source_type_tag),
        ("신뢰도 누락", missing_confidence),
        ("research_scope:* 태그 누락", missing_scope_tag),
        ("auto_scope/auto_ticker 근거 태그 누락", missing_reason_tag),
        ("저장 파일 누락", missing_files),
        ("RAG 문서 누락", missing_rag),
    ]
    failed = False
    for label, items in checks:
        print(f"{label}: {len(items)}개")
        for entry in items[:5]:
            print(
                f"  - {entry.get('ticker') or 'UNKNOWN'} | {entry.get('file_name') or entry.get('title') or '제목 없음'} | "
                f"{entry.get('date') or '날짜 없음'} | tags={entry.get('tags') or []}"
            )
        if items:
            failed = True

    if strict and failed:
        print("자동 분류 품질 점검 실패")
        return 1
    print("자동 분류 품질 점검 정상" if not failed else "자동 분류 품질 점검 경고")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check classification tags and RAG coverage")
    parser.add_argument("--vault-dir", default=str(PROJECT_ROOT / "research_vault"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    raise SystemExit(evaluate(Path(args.vault_dir), strict=args.strict))


if __name__ == "__main__":
    main()
