"""Inspect manual LLM bridge captures and RAG linkage without a running backend."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("research_vault/manifest.json")
DEFAULT_RAG_DB = Path("research_vault/_system/research_memory.sqlite3")
PROMPT_MARKER = "[원 프롬프트]"
RESPONSE_MARKER = "[LLM 응답]"
LLM_MARKER = "[수동 LLM 분석 응답]"


@dataclass(frozen=True)
class LlmCapture:
    entry: dict[str, Any]
    markdown_path: Path
    json_path: Path
    raw_content: str
    rag_connected: bool

    @property
    def relative_path(self) -> str:
        return str(self.entry.get("relative_path") or "")

    @property
    def json_relative_path(self) -> str:
        return str(self.entry.get("json_relative_path") or "")

    @property
    def file_name(self) -> str:
        return str(self.entry.get("file_name") or self.markdown_path.name)

    @property
    def date(self) -> str:
        return str(self.entry.get("date") or "")

    @property
    def ticker(self) -> str:
        return str(self.entry.get("ticker") or "").strip().upper()

    @property
    def company_name(self) -> str:
        for key in ["company_name", "companyName", "holding_name", "label", "name"]:
            value = self.entry.get(key)
            if value:
                return " ".join(str(value).split())
        return ""

    @property
    def archived(self) -> bool:
        tags = self.entry.get("tags") if isinstance(self.entry.get("tags"), list) else []
        return "archived" in {str(tag).lower() for tag in tags}

    @property
    def has_prompt(self) -> bool:
        return PROMPT_MARKER in self.raw_content

    @property
    def has_response(self) -> bool:
        return RESPONSE_MARKER in self.raw_content

    @property
    def label(self) -> str:
        if self.company_name:
            return self.company_name
        scope_labels = {
            "SECTOR": "섹터/산업 자료",
            "POLICY": "정책/규제 자료",
            "FLOWS": "수급/자금 흐름 자료",
            "MARKET": "시장/시황 자료",
            "MARKET-KR": "국내 시장 자료",
            "MARKET-US": "미국 시장 자료",
            "MARKET-GLOBAL": "글로벌 시장 자료",
            "MACRO": "매크로 자료",
            "RATES": "금리/물가 자료",
            "CUSTOMS": "수출입/관세 자료",
            "INBOX": "미분류 입력 자료",
        }
        return scope_labels.get(self.ticker, self.ticker or "회사명 확인 필요")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_resolve(root: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    candidate = (root / str(relative_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def read_raw_content(root: Path, entry: dict[str, Any]) -> str:
    json_path = safe_resolve(root, entry.get("json_relative_path"))
    if not json_path or not json_path.exists():
        return ""
    payload = load_json(json_path)
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("raw_content") or "")


def rag_relative_paths(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "select source_relative_path from research_memory_documents"
            ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(row[0] or "") for row in rows}


def load_llm_captures(root: Path, manifest_path: Path, rag_db_path: Path) -> list[LlmCapture]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, list):
        raise SystemExit(f"manifest를 읽을 수 없습니다: {manifest_path}")

    rag_paths = rag_relative_paths(rag_db_path)
    captures: list[LlmCapture] = []
    for entry in manifest:
        if not isinstance(entry, dict) or entry.get("type") != "research-capture":
            continue
        raw_content = read_raw_content(root, entry)
        if LLM_MARKER not in raw_content and PROMPT_MARKER not in raw_content:
            continue
        markdown_path = safe_resolve(root, entry.get("relative_path"))
        json_path = safe_resolve(root, entry.get("json_relative_path"))
        captures.append(
            LlmCapture(
                entry=entry,
                markdown_path=markdown_path or Path("__missing_markdown__"),
                json_path=json_path or Path("__missing_json__"),
                raw_content=raw_content,
                rag_connected=str(entry.get("relative_path") or "") in rag_paths,
            )
        )

    captures.sort(key=lambda item: (item.date, item.file_name), reverse=True)
    return captures


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 연동 저장/RAG 상태를 백엔드 없이 점검합니다.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--rag-db", type=Path, default=DEFAULT_RAG_DB)
    parser.add_argument("--min-saved-count", type=int, default=1)
    parser.add_argument("--min-active-count", type=int, default=1)
    parser.add_argument("--min-rag-connected-count", type=int, default=1)
    parser.add_argument("--require-active-rag", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    rag_db_path = args.rag_db if args.rag_db.is_absolute() else root / args.rag_db
    captures = load_llm_captures(root, manifest_path, rag_db_path)
    active = [item for item in captures if not item.archived]
    rag_connected = [item for item in captures if item.rag_connected]
    active_rag_connected = [item for item in active if item.rag_connected]

    failures: list[str] = []
    if len(captures) < args.min_saved_count:
        failures.append(f"LLM 저장 응답 부족: {len(captures)} < {args.min_saved_count}")
    if len(active) < args.min_active_count:
        failures.append(f"활성 LLM 저장 응답 부족: {len(active)} < {args.min_active_count}")
    if len(rag_connected) < args.min_rag_connected_count:
        failures.append(f"RAG 연결 부족: {len(rag_connected)} < {args.min_rag_connected_count}")
    if args.require_active_rag and len(active_rag_connected) < len(active):
        failures.append(f"활성 LLM 응답 RAG 연결 누락: {len(active) - len(active_rag_connected)}개")

    for item in captures:
        if not item.markdown_path.exists():
            failures.append(f"Markdown 파일 누락: {item.relative_path}")
        if not item.json_path.exists():
            failures.append(f"JSON 파일 누락: {item.json_relative_path}")
        if not item.has_prompt:
            failures.append(f"원 프롬프트 누락: {item.relative_path}")
        if not item.has_response:
            failures.append(f"LLM 응답 누락: {item.relative_path}")
        if not item.rag_connected and not item.archived:
            failures.append(f"RAG 연결 누락: {item.relative_path}")

    print(f"manifest: {manifest_path.relative_to(root)}")
    print(f"RAG DB: {rag_db_path.relative_to(root)}")
    print(
        "LLM 저장 응답: "
        f"{len(captures)}개 | 활성 {len(active)}개 | "
        f"RAG 연결 {len(rag_connected)}개 | 활성 RAG {len(active_rag_connected)}개"
    )
    print("최근 저장 항목")
    for item in captures[: max(0, args.limit)]:
        status = "보관" if item.archived else "활성"
        rag_status = "RAG 연결" if item.rag_connected else "RAG 연결 누락"
        print(f"- {item.date} {item.label} · {item.file_name} · {status} · {rag_status}")

    if failures:
        print("LLM/RAG 저장 상태 확인 필요")
        for failure in failures[: max(0, args.limit)]:
            print(f"- {failure}")
        if len(failures) > args.limit:
            print(f"- 추가 문제 {len(failures) - args.limit}개")
        return 1

    print("LLM/RAG 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
