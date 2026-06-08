"""Offline checks for public IR/SEC research memory records."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_manifest(vault_dir: Path) -> list[dict]:
    path = vault_dir / "manifest.json"
    if not path.exists():
        raise SystemExit(f"manifest 파일을 찾지 못했습니다: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("manifest 최상위 구조가 배열이 아닙니다.")
    return [entry for entry in payload if isinstance(entry, dict)]


def is_public_ir_sec(entry: dict) -> bool:
    return (
        str(entry.get("scope") or "") == "public_ir_sec"
        or str(entry.get("ticker") or "").upper() == "PUBLIC_IR_SEC"
        or str(entry.get("type") or "") == "public-ir-sec"
    )


def is_archived_entry(entry: dict) -> bool:
    return bool(
        entry.get("is_deleted")
        or str(entry.get("status") or "").lower() == "archived"
        or "archived" in {str(tag).lower() for tag in (entry.get("tags") or [])}
    )


def public_ir_entry_body_supplemented(entry: dict, quality: dict) -> bool:
    return bool(
        quality.get("body_supplemented")
        or "body_supplemented" in {str(tag).strip() for tag in (entry.get("tags") or [])}
    )


def source_family(source_url: object) -> str:
    host = (urlparse(str(source_url or "")).hostname or "").lower()
    if host.endswith("sec.gov"):
        return "sec"
    if "benzinga.com" in host:
        return "benzinga"
    if host.startswith("ir.") or "investor" in host:
        return "company_ir"
    return "public_web" if host else "unknown"


def expected_source_type(entry: dict) -> set[str]:
    family = source_family(entry.get("source_url"))
    if family == "sec":
        return {"official_filing"}
    if family == "benzinga":
        return {"earnings_data"}
    if family == "company_ir":
        return {"ir_presentation", "ir_press_release", "other"}
    return {"other", "public_ir_sec"}


def load_rag_paths(vault_dir: Path) -> set[str]:
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return set()
    try:
        with sqlite3.connect(db_path) as con:
            rows = con.execute(
                "select source_relative_path from research_memory_documents where report_type = ?",
                ("public-ir-sec",),
            ).fetchall()
    except sqlite3.Error as exc:
        raise SystemExit(f"RAG DB 확인 실패: {exc}") from exc
    return {str(row[0] or "").replace("\\", "/").strip() for row in rows if row and row[0]}


def is_recommendation_usable(entry: dict, quality: dict) -> bool:
    return bool(public_ir_entry_body_supplemented(entry, quality)) or (
        quality.get("status") == "정상"
        and not quality.get("needs_body_copy")
        and int(quality.get("body_chars") or entry.get("body_chars") or 0) >= 500
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="공개 IR/SEC 저장 품질을 백엔드 없이 점검합니다.")
    parser.add_argument("--require-any", action="store_true", help="최소 1건 이상 저장되어 있어야 함")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault_dir = root / "research_vault"
    all_entries = [entry for entry in load_manifest(vault_dir) if is_public_ir_sec(entry)]
    archived_count = sum(1 for entry in all_entries if is_archived_entry(entry))
    entries = [entry for entry in all_entries if not is_archived_entry(entry)]
    rag_paths = load_rag_paths(vault_dir)
    if args.require_any and not entries:
        raise SystemExit("공개 IR/SEC 저장 자료가 없습니다.")

    errors: list[str] = []
    needs_body = 0
    url_only = 0
    usable_count = 0
    rag_linked_count = 0
    provider_counts: dict[str, int] = {}
    for entry in entries:
        label = entry.get("file_name") or entry.get("source_url") or "공개 IR/SEC 항목"
        if not entry.get("source_url"):
            errors.append(f"source_url 누락: {label}")
        provider = str(entry.get("source_provider") or "").strip()
        source_type = str(entry.get("source_type") or "").strip()
        if not provider:
            errors.append(f"source_provider 누락: {label}")
        else:
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        expected_types = expected_source_type(entry)
        if source_type not in expected_types:
            errors.append(f"source_type 분류 확인 필요: {label} | {source_type or '없음'} / 기대 {', '.join(sorted(expected_types))}")
        tags = {str(tag).strip() for tag in (entry.get("tags") or [])}
        for required_tag in {"public_ir_sec", "rag_candidate"}:
            if required_tag not in tags:
                errors.append(f"필수 태그 누락({required_tag}): {label}")
        confidence = entry.get("source_confidence", entry.get("confidence"))
        if not isinstance(confidence, (int, float)) or float(confidence) <= 0:
            errors.append(f"source_confidence 확인 필요: {label}")
        quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
        source = entry.get("source_url_processing") if isinstance(entry.get("source_url_processing"), dict) else {}
        source_status = str(source.get("status") or quality.get("source_status") or "")
        body_supplemented = public_ir_entry_body_supplemented(entry, quality)
        usable = is_recommendation_usable(entry, quality)
        if usable:
            usable_count += 1
        if quality.get("needs_body_copy") and not body_supplemented:
            needs_body += 1
        if quality.get("url_text_unavailable") or source_status in {"fetch_failed", "invalid", "empty_text"}:
            url_only += 1
            if quality.get("status") != "보강 필요" and not body_supplemented:
                errors.append(f"URL-only 항목 품질 상태가 보강 필요가 아님: {label}")
            if not quality.get("needs_body_copy") and not body_supplemented:
                errors.append(f"URL-only 항목 needs_body_copy 누락: {label}")
        relative_path = str(entry.get("relative_path") or "").replace("\\", "/")
        if not relative_path or not (root / relative_path).exists():
            errors.append(f"Markdown 파일 누락: {label}")
        elif relative_path in rag_paths:
            rag_linked_count += 1
        json_rel = entry.get("json_relative_path")
        if json_rel and not (root / json_rel).exists():
            errors.append(f"JSON 파일 누락: {label}")

    if entries and usable_count == 0:
        errors.append("추천 가산 가능한 공개 IR/SEC 자료가 없습니다.")
    if entries and rag_linked_count != len(entries):
        errors.append(f"RAG 색인 누락: {len(entries) - rag_linked_count}개 / 전체 {len(entries)}개")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        raise SystemExit(1)

    print(f"공개 IR/SEC 저장 자료: {len(entries)}개" + (f" / 보관 {archived_count}개" if archived_count else ""))
    print(f"URL-only/본문 보강: {url_only}개 / needs_body_copy {needs_body}개")
    print(f"추천 가산 가능: {usable_count}개 | RAG 색인 연결: {rag_linked_count}/{len(entries)}개")
    if provider_counts:
        print("출처 분포: " + ", ".join(f"{provider}={count}" for provider, count in sorted(provider_counts.items())))
    for entry in entries[:10]:
        quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
        print(f"- {entry.get('date')} {entry.get('title') or entry.get('file_name')} | {quality.get('status') or entry.get('capture_quality_status')} | {entry.get('source_url')}")
    print("공개 IR/SEC 저장 품질 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
