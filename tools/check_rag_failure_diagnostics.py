"""Diagnose why stored research may fail to become useful RAG evidence.

This check is backend-free and read-only. It combines the research vault
manifest with the SQLite RAG index so operations can see whether a document is
stored, indexed, searchable, and backed by enough classification metadata.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("research_vault/manifest.json")
DEFAULT_RAG_DB = Path("research_vault/_system/research_memory.sqlite3")
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
    "MARKET-CALENDAR",
}
BODY_ISSUE_MARKERS = {"needs_body_copy", "url_text_unavailable"}
OCR_ISSUE_MARKERS = {"ocr_needed", "ocr_required", "ocr_unavailable", "needs_ocr"}
MIN_SEARCHABLE_CHARS = 400


@dataclass(frozen=True)
class RagDocument:
    document_id: str
    source_relative_path: str
    ticker: str
    source_date: str
    full_text_length: int


@dataclass(frozen=True)
class DiagnosticIssue:
    code: str
    severity: str
    relative_path: str
    title: str
    next_action: str


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
    except (OSError, json.JSONDecodeError):
        return default


def safe_resolve(root: Path, relative_path: Any) -> Path | None:
    if not relative_path:
        return None
    candidate = (root / str(relative_path)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def tags_from(entry: dict[str, Any]) -> set[str]:
    tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
    return {str(tag).strip() for tag in tags if str(tag).strip()}


def is_archived(entry: dict[str, Any]) -> bool:
    tags = {tag.lower() for tag in tags_from(entry)}
    return bool(entry.get("archived") or entry.get("status") == "archived" or "archived" in tags)


def is_research_entry(entry: dict[str, Any]) -> bool:
    return bool(
        entry.get("type") == "research-capture"
        or entry.get("module") == "research_quick_capture"
        or entry.get("rag_document")
        or entry.get("storage")
    )


def is_body_supplemented(entry: dict[str, Any]) -> bool:
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    return bool(
        quality.get("body_supplemented")
        or entry.get("body_supplemented_at")
        or entry.get("body_supplements")
    )


def entry_title(entry: dict[str, Any]) -> str:
    for key in ("title", "company_name", "file_name", "relative_path"):
        value = entry.get(key)
        if value:
            return " ".join(str(value).split())
    return "제목 없음"


def entry_relative_path(entry: dict[str, Any]) -> str:
    return str(entry.get("relative_path") or entry.get("json_relative_path") or entry.get("file_name") or "")


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path, [])
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def load_rag_documents(db_path: Path) -> dict[str, RagDocument]:
    if not db_path.exists():
        return {}
    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error:
        return {}
    try:
        rows = connection.execute(
            """
            SELECT document_id, source_relative_path, ticker, source_date, full_text
            FROM research_memory_documents
            """
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        connection.close()
    documents: dict[str, RagDocument] = {}
    for document_id, source_relative_path, ticker, source_date, full_text in rows:
        relative = str(source_relative_path or document_id or "")
        documents[relative] = RagDocument(
            document_id=str(document_id or ""),
            source_relative_path=relative,
            ticker=str(ticker or ""),
            source_date=str(source_date or ""),
            full_text_length=len(str(full_text or "")),
        )
    return documents


def markdown_length(root: Path, entry: dict[str, Any]) -> int:
    path = safe_resolve(root, entry.get("relative_path"))
    if not path or not path.exists() or not path.is_file():
        return 0
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def has_classification_reason(entry: dict[str, Any], tags: set[str]) -> bool:
    if any(tag.startswith("auto_scope:") or tag.startswith("auto_ticker:") for tag in tags):
        return True
    if entry.get("classification_rationale") or entry.get("classification_reason"):
        return True
    return False


def diagnose_entry(root: Path, entry: dict[str, Any], rag_docs: dict[str, RagDocument]) -> list[DiagnosticIssue]:
    issues: list[DiagnosticIssue] = []
    relative = entry_relative_path(entry)
    title = entry_title(entry)
    tags = tags_from(entry)
    ticker = str(entry.get("ticker") or "").upper()
    text = json.dumps(entry, ensure_ascii=False).lower()
    rag_doc = rag_docs.get(relative)

    md_path = safe_resolve(root, entry.get("relative_path"))
    json_path = safe_resolve(root, entry.get("json_relative_path"))
    if entry.get("relative_path") and (not md_path or not md_path.exists()):
        issues.append(
            DiagnosticIssue("missing_markdown", "error", relative, title, "Markdown 저장 파일을 복구합니다.")
        )
    if entry.get("json_relative_path") and (not json_path or not json_path.exists()):
        issues.append(DiagnosticIssue("missing_json", "error", relative, title, "JSON 원본 저장 파일을 복구합니다."))

    if not rag_doc:
        issues.append(
            DiagnosticIssue("missing_rag_document", "error", relative, title, "RAG 색인을 재생성하거나 문서를 재색인합니다.")
        )
    else:
        searchable = max(rag_doc.full_text_length, markdown_length(root, entry))
        if searchable < MIN_SEARCHABLE_CHARS:
            issues.append(
                DiagnosticIssue(
                    "low_search_text",
                    "warning",
                    relative,
                    title,
                    "본문 추출/요약을 보강해 검색 가능한 텍스트를 늘립니다.",
                )
            )

    body_issue = any(marker in tags for marker in BODY_ISSUE_MARKERS) or any(marker in text for marker in BODY_ISSUE_MARKERS)
    if body_issue and not is_body_supplemented(entry):
        issues.append(
            DiagnosticIssue("body_unavailable", "error", relative, title, "원문 본문 보강 전까지 추천 근거 반영을 제한합니다.")
        )

    ocr_issue = any(marker in tags for marker in OCR_ISSUE_MARKERS) or any(marker in text for marker in OCR_ISSUE_MARKERS)
    if ocr_issue:
        issues.append(
            DiagnosticIssue("ocr_needed", "warning", relative, title, "OCR 또는 대체 텍스트 추출 결과를 확인합니다.")
        )

    if ticker in SPECIAL_RESEARCH_KEYS:
        scope_tag = f"research_scope:{ticker.lower()}"
        if ticker not in {"INBOX", "MARKET-CALENDAR"} and scope_tag not in tags:
            issues.append(
                DiagnosticIssue("weak_scope_tag", "warning", relative, title, "섹터/매크로 범위 태그를 보강합니다.")
            )
    elif not ticker:
        issues.append(
            DiagnosticIssue("missing_ticker_or_scope", "warning", relative, title, "회사/티커 또는 자료 범위를 명확히 지정합니다.")
        )

    if ("auto_classified" in tags or "auto_ingested" in tags) and not has_classification_reason(entry, tags):
        issues.append(
            DiagnosticIssue(
                "missing_classification_reason",
                "warning",
                relative,
                title,
                "자동 분류 근거 태그 또는 설명을 남깁니다.",
            )
        )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="저장/RAG 실패 원인을 백엔드 없이 진단합니다.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--rag-db", type=Path, default=DEFAULT_RAG_DB)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--max-errors", type=int, default=0)
    parser.add_argument("--max-warnings", type=int, default=999)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    rag_db_path = args.rag_db if args.rag_db.is_absolute() else root / args.rag_db
    manifest = load_manifest(manifest_path)
    rag_docs = load_rag_documents(rag_db_path)
    active = [entry for entry in manifest if is_research_entry(entry) and not is_archived(entry)]

    issues: list[DiagnosticIssue] = []
    for entry in active:
        issues.extend(diagnose_entry(root, entry, rag_docs))

    by_code = Counter(issue.code for issue in issues)
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity != "error"]
    linked_count = sum(1 for entry in active if entry_relative_path(entry) in rag_docs)
    score = 100.0
    if active:
        score -= len(errors) / len(active) * 70.0
        score -= len(warnings) / len(active) * 20.0
    score = max(0.0, min(100.0, score))

    print(f"프로젝트 루트: {root}")
    print(f"manifest: {manifest_path.relative_to(root)}")
    print(f"RAG DB: {rag_db_path.relative_to(root)}")
    print(f"활성 리서치 문서: {len(active)}개 | RAG 연결 {linked_count}개 | RAG 문서 {len(rag_docs)}개")
    print(f"저장/RAG 진단 점수: {score:.1f}%")
    print(f"오류 {len(errors)}개 | 경고 {len(warnings)}개")
    if by_code:
        print("문제 유형:")
        for code, count in by_code.most_common():
            print(f"- {code}: {count}개")
    else:
        print("문제 유형: 없음")

    print("우선 조치 항목")
    for issue in issues[: max(0, args.limit)]:
        label = "오류" if issue.severity == "error" else "경고"
        print(f"- [{label}] {issue.code} | {issue.relative_path} | {issue.title}")
        print(f"  다음 조치: {issue.next_action}")
    if len(issues) > args.limit:
        print(f"- 추가 진단 항목 {len(issues) - args.limit}개")

    ok = len(errors) <= args.max_errors and len(warnings) <= args.max_warnings
    if args.strict and not ok:
        print("저장/RAG 실패 진단 확인 필요")
        return 1
    print("저장/RAG 실패 진단 정상" if ok else "저장/RAG 실패 진단 경고")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
