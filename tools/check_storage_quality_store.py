"""Inspect stored research quality markers without a running backend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BODY_TAGS = {"needs_body_copy", "url_text_unavailable"}
OCR_MARKERS = {"ocr_needed", "ocr_required", "ocr_unavailable", "needs_ocr"}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def tags_from(item: dict[str, Any]) -> set[str]:
    captured = item.get("captured_item") if isinstance(item.get("captured_item"), dict) else {}
    tags = captured.get("tags") or item.get("tags") or []
    if not isinstance(tags, list):
        return set()
    return {str(tag) for tag in tags}


def is_supplemented(item: dict[str, Any]) -> bool:
    quality = item.get("capture_quality") if isinstance(item.get("capture_quality"), dict) else {}
    supplements = item.get("body_supplements") or []
    return bool(quality.get("body_supplemented") or item.get("body_supplemented_at") or supplements)


def is_indexed_or_stored(item: dict[str, Any]) -> bool:
    storage = item.get("storage")
    rag = item.get("rag_document")
    # saved_to_research_memory alone is retained as an advisory signal because
    # older URL-only captures can be present in memory while excluded from active
    # storage/RAG quality dashboards.
    return bool(storage or rag)


def main() -> int:
    parser = argparse.ArgumentParser(description="저장 자료 품질 플래그를 백엔드 없이 점검합니다.")
    parser.add_argument("--max-active-body-missing", type=int, default=0)
    parser.add_argument("--max-active-ocr-needed", type=int, default=0)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault = root / "research_vault"
    body_missing: list[Path] = []
    ocr_needed: list[Path] = []
    advisory_body: list[Path] = []

    for path in vault.glob("*/*.json"):
        item = load_json(path)
        if not isinstance(item, dict):
            continue
        tags = tags_from(item)
        text = json.dumps(item, ensure_ascii=False).lower()
        has_body_issue = bool(tags & BODY_TAGS) or "needs_body_copy" in text or "url_text_unavailable" in text
        has_ocr_issue = bool(tags & OCR_MARKERS) or any(marker in text for marker in OCR_MARKERS)
        active = is_indexed_or_stored(item)
        if has_body_issue and not is_supplemented(item):
            if active:
                body_missing.append(path)
            else:
                advisory_body.append(path)
        if has_ocr_issue and active:
            ocr_needed.append(path)

    print(f"저장소: {vault}")
    print(f"활성 본문 보강 필요: {len(body_missing)}개")
    print(f"활성 OCR 확인 필요: {len(ocr_needed)}개")
    print(f"비활성/미색인/메모리-only URL-only 참고 항목: {len(advisory_body)}개")
    for label, rows in [("본문 보강", body_missing), ("OCR 확인", ocr_needed), ("참고", advisory_body)]:
        for path in rows[: max(0, args.limit)]:
            print(f"{label}: {path.relative_to(root)}")

    ok = len(body_missing) <= args.max_active_body_missing and len(ocr_needed) <= args.max_active_ocr_needed
    if ok:
        print("오프라인 저장 품질 상태 정상")
        return 0
    print("오프라인 저장 품질 확인 필요")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
