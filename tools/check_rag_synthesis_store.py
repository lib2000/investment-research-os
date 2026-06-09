"""Validate saved RAG query synthesis reports and RAG reuse linkage offline."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("research_vault/manifest.json")
DEFAULT_RAG_DB = Path("research_vault/_system/research_memory.sqlite3")
REPORT_TYPE = "rag-query-synthesis"


@dataclass(frozen=True)
class RagSynthesisEntry:
    entry: dict[str, Any]
    markdown_path: Path
    json_path: Path | None
    payload: dict[str, Any]
    rag_connected: bool

    @property
    def date(self) -> str:
        return str(self.entry.get("date") or "")

    @property
    def ticker(self) -> str:
        return str(self.entry.get("ticker") or "").strip().upper()

    @property
    def file_name(self) -> str:
        return str(self.entry.get("file_name") or self.markdown_path.name)

    @property
    def relative_path(self) -> str:
        return str(self.entry.get("relative_path") or "")

    @property
    def query(self) -> str:
        return str(self.entry.get("query") or self.payload.get("query") or "").strip()

    @property
    def source_count(self) -> int:
        value = self.entry.get("source_count", self.payload.get("source_count", 0))
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def has_next_actions(self) -> bool:
        actions = self.payload.get("next_actions")
        return isinstance(actions, list) and any(str(item).strip() for item in actions)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_resolve(root: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    candidate = (root / str(relative_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def rag_relative_paths(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "select source_relative_path from research_memory_documents where report_type = ?",
                (REPORT_TYPE,),
            ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(row[0] or "") for row in rows}


def rag_document_count(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(db_path) as conn:
            return int(
                conn.execute(
                    "select count(*) from research_memory_documents where report_type = ?",
                    (REPORT_TYPE,),
                ).fetchone()[0]
            )
    except sqlite3.Error:
        return 0


def manifest_entries(manifest: Any) -> list[dict[str, Any]]:
    if not isinstance(manifest, list):
        return []
    return [item for item in manifest if isinstance(item, dict)]


def load_synthesis_entries(root: Path, manifest_path: Path, rag_db_path: Path) -> list[RagSynthesisEntry]:
    rag_paths = rag_relative_paths(rag_db_path)
    entries: list[RagSynthesisEntry] = []
    for entry in manifest_entries(load_json(manifest_path, [])):
        if str(entry.get("type") or entry.get("report_type") or "").strip().lower() != REPORT_TYPE:
            continue
        markdown_path = safe_resolve(root, entry.get("relative_path"))
        json_path = safe_resolve(root, entry.get("json_relative_path"))
        payload = load_json(json_path, {}) if json_path else {}
        if not isinstance(payload, dict):
            payload = {}
        entries.append(
            RagSynthesisEntry(
                entry=entry,
                markdown_path=markdown_path or Path("__missing_markdown__"),
                json_path=json_path,
                payload=payload,
                rag_connected=str(entry.get("relative_path") or "") in rag_paths,
            )
        )
    entries.sort(key=lambda item: (item.date, item.file_name), reverse=True)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 검색 합성 저장/RAG 재활용 상태를 백엔드 없이 점검합니다.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--rag-db", type=Path, default=DEFAULT_RAG_DB)
    parser.add_argument("--min-saved-count", type=int, default=1)
    parser.add_argument("--min-rag-connected-count", type=int, default=1)
    parser.add_argument("--min-source-count", type=int, default=1)
    parser.add_argument("--require-latest-rag", action="store_true")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    rag_db_path = args.rag_db if args.rag_db.is_absolute() else root / args.rag_db
    entries = load_synthesis_entries(root, manifest_path, rag_db_path)
    rag_count = rag_document_count(rag_db_path)
    connected = [item for item in entries if item.rag_connected]
    latest = entries[0] if entries else None

    failures: list[str] = []
    warnings: list[str] = []
    if len(entries) < args.min_saved_count:
        failures.append(f"RAG 합성 저장 manifest 항목 부족: {len(entries)} < {args.min_saved_count}")
    if len(connected) < args.min_rag_connected_count:
        failures.append(f"RAG 합성 manifest-RAG 연결 부족: {len(connected)} < {args.min_rag_connected_count}")
    if rag_count > len(entries):
        warnings.append(f"레거시 DB-only RAG 합성 문서 {rag_count - len(entries)}개가 있습니다.")
    if latest and args.require_latest_rag and not latest.rag_connected:
        failures.append(f"최신 RAG 합성 RAG 연결 누락: {latest.relative_path}")

    for item in entries:
        if not item.markdown_path.exists():
            failures.append(f"Markdown 파일 누락: {item.relative_path}")
        if item.json_path is None or not item.json_path.exists():
            failures.append(f"JSON 파일 누락: {item.entry.get('json_relative_path') or item.relative_path}")
        if not item.query:
            failures.append(f"검색어 누락: {item.relative_path}")
        if item.source_count < args.min_source_count:
            failures.append(f"원천 문서 부족: {item.relative_path} | {item.source_count} < {args.min_source_count}")
        if not item.has_next_actions:
            failures.append(f"다음 액션 누락: {item.relative_path}")
        if not item.rag_connected:
            failures.append(f"RAG 연결 누락: {item.relative_path}")

    print(f"manifest: {manifest_path.relative_to(root)}")
    print(f"RAG DB: {rag_db_path.relative_to(root)}")
    print(
        "RAG 합성 저장: "
        f"manifest {len(entries)}개 | RAG 문서 {rag_count}개 | "
        f"manifest-RAG 연결 {len(connected)}개"
    )
    print("최근 RAG 합성 항목")
    for item in entries[: max(0, args.limit)]:
        rag_status = "RAG 연결" if item.rag_connected else "RAG 연결 누락"
        print(
            f"- {item.date} {item.ticker or 'SEARCH'} · {item.file_name} · "
            f"원천 {item.source_count}개 · {rag_status} · query={item.query[:80]}"
        )
    for warning in warnings:
        print(f"참고: {warning}")

    if failures:
        print("RAG 합성 저장 상태 확인 필요")
        for failure in failures[: max(0, args.limit)]:
            print(f"- {failure}")
        if len(failures) > args.limit:
            print(f"- 추가 문제 {len(failures) - args.limit}개")
        return 1

    print("RAG 합성 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
