"""Offline checks for public IR/SEC research memory records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def main() -> int:
    parser = argparse.ArgumentParser(description="공개 IR/SEC 저장 품질을 백엔드 없이 점검합니다.")
    parser.add_argument("--require-any", action="store_true", help="최소 1건 이상 저장되어 있어야 함")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault_dir = root / "research_vault"
    all_entries = [entry for entry in load_manifest(vault_dir) if is_public_ir_sec(entry)]
    archived_count = sum(1 for entry in all_entries if is_archived_entry(entry))
    entries = [entry for entry in all_entries if not is_archived_entry(entry)]
    if args.require_any and not entries:
        raise SystemExit("공개 IR/SEC 저장 자료가 없습니다.")

    errors: list[str] = []
    needs_body = 0
    url_only = 0
    for entry in entries:
        label = entry.get("file_name") or entry.get("source_url") or "공개 IR/SEC 항목"
        if not entry.get("source_url"):
            errors.append(f"source_url 누락: {label}")
        quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
        source = entry.get("source_url_processing") if isinstance(entry.get("source_url_processing"), dict) else {}
        source_status = str(source.get("status") or quality.get("source_status") or "")
        body_supplemented = public_ir_entry_body_supplemented(entry, quality)
        if quality.get("needs_body_copy") and not body_supplemented:
            needs_body += 1
        if quality.get("url_text_unavailable") or source_status in {"fetch_failed", "invalid", "empty_text"}:
            url_only += 1
            if quality.get("status") != "보강 필요" and not body_supplemented:
                errors.append(f"URL-only 항목 품질 상태가 보강 필요가 아님: {label}")
            if not quality.get("needs_body_copy") and not body_supplemented:
                errors.append(f"URL-only 항목 needs_body_copy 누락: {label}")
        if not entry.get("relative_path") or not (root / entry["relative_path"]).exists():
            errors.append(f"Markdown 파일 누락: {label}")
        json_rel = entry.get("json_relative_path")
        if json_rel and not (root / json_rel).exists():
            errors.append(f"JSON 파일 누락: {label}")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        raise SystemExit(1)

    print(f"공개 IR/SEC 저장 자료: {len(entries)}개" + (f" / 보관 {archived_count}개" if archived_count else ""))
    print(f"URL-only/본문 보강: {url_only}개 / needs_body_copy {needs_body}개")
    for entry in entries[:10]:
        quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
        print(f"- {entry.get('date')} {entry.get('title') or entry.get('file_name')} | {quality.get('status') or entry.get('capture_quality_status')} | {entry.get('source_url')}")
    print("공개 IR/SEC 저장 품질 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
