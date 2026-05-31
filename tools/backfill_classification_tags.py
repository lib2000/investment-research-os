"""Backfill auditable classification system tags into stored research entries.

This is a non-destructive metadata migration: it updates manifest tags and the
matching JSON payload tags, then refreshes RAG document metadata for changed
entries. It does not edit the original markdown body or delete data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.rag_memory import upsert_research_memory_document  # noqa: E402

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


def normalize_tag_value(value: object) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


def merge_tags(*groups: object) -> list[str]:
    tags: list[str] = []
    for group in groups:
        if group is None:
            continue
        if isinstance(group, str):
            candidates = [group]
        elif isinstance(group, (list, tuple, set)):
            candidates = list(group)
        else:
            candidates = [group]
        for tag in candidates:
            cleaned = str(tag or "").strip()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
    return tags


def category_tag(tags: list[str], prefix: str) -> str:
    for tag in tags:
        if str(tag).startswith(prefix):
            return str(tag).split(":", 1)[1]
    return "unknown"


def classification_reason(entry: dict, tags: list[str]) -> str:
    ticker = str(entry.get("ticker") or "").upper()
    if "naver_research" in tags:
        category = category_tag(tags, "naver_category:")
        if ticker not in SPECIAL_RESEARCH_KEYS and re.fullmatch(r"\d{6}", ticker):
            return "naver_kr_symbol_code"
        if category == "산업분석":
            return "naver_industry_research"
        if category in {"시황정보", "투자정보"}:
            return "naver_market_research"
        return "naver_research_auto_scope"
    if "shinhan_research" in tags:
        category = category_tag(tags, "shinhan_category:")
        if ticker not in SPECIAL_RESEARCH_KEYS:
            return "shinhan_symbol_match"
        return f"shinhan_{category}"
    if "auto_classified" in tags:
        return "historical_auto_classified"
    if "auto_ingested" in tags:
        return "historical_auto_ingested"
    return ""


def standard_tags(entry: dict) -> list[str]:
    ticker = str(entry.get("ticker") or "").strip().upper()
    source_type = normalize_tag_value(entry.get("source_type"))
    tags = [str(tag) for tag in (entry.get("tags") or []) if str(tag).strip()]
    additions: list[str] = []
    if ticker in SPECIAL_RESEARCH_KEYS and ticker != "INBOX":
        additions.append(f"research_scope:{ticker.lower()}")
        if ticker.startswith("MARKET-"):
            additions.append("research_scope:market")
    if source_type:
        additions.append(f"source_type:{source_type}")
    if ("auto_classified" in tags or "auto_ingested" in tags) and not any(
        tag.startswith("auto_ticker:") or tag.startswith("auto_scope:") for tag in tags
    ):
        reason = normalize_tag_value(classification_reason(entry, tags))
        if reason:
            additions.append(f"auto_scope:{reason}")
    return additions


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_payload_tags(payload: object, tags: list[str]) -> bool:
    if not isinstance(payload, dict):
        return False
    changed = False
    captured = payload.get("captured_item")
    if isinstance(captured, dict):
        merged = merge_tags(captured.get("tags") or [], tags)
        if merged != (captured.get("tags") or []):
            captured["tags"] = merged
            changed = True
    if isinstance(payload.get("tags"), list):
        merged = merge_tags(payload.get("tags") or [], tags)
        if merged != payload.get("tags"):
            payload["tags"] = merged
            changed = True
    return changed


def backfill(vault_dir: Path, *, dry_run: bool = False) -> int:
    manifest_path = vault_dir / "manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, list):
        raise SystemExit(f"manifest를 읽을 수 없습니다: {manifest_path}")

    changed_entries = 0
    changed_payloads = 0
    rag_refreshed = 0
    for entry in manifest:
        if not isinstance(entry, dict):
            continue
        additions = standard_tags(entry)
        if not additions:
            continue
        merged = merge_tags(entry.get("tags") or [], additions)
        if merged == (entry.get("tags") or []):
            continue
        entry["tags"] = merged
        changed_entries += 1

        json_relative = entry.get("json_relative_path")
        if json_relative:
            json_path = PROJECT_ROOT / str(json_relative)
            payload = load_json(json_path)
            if update_payload_tags(payload, additions):
                changed_payloads += 1
                if not dry_run:
                    write_json(json_path, payload)
        if not dry_run and entry.get("type") == "research-capture":
            try:
                upsert_research_memory_document(vault_dir=vault_dir, entry=entry)
                rag_refreshed += 1
            except Exception as exc:  # noqa: BLE001
                print(f"RAG 갱신 경고: {entry.get('file_name')} | {exc}")

    if changed_entries and not dry_run:
        write_json(manifest_path, manifest)
    print(f"분류 태그 백필 대상: {changed_entries}개")
    print(f"JSON payload 갱신: {changed_payloads}개")
    print(f"RAG 메타데이터 갱신: {rag_refreshed}개")
    print("dry-run" if dry_run else "분류 태그 백필 완료")
    return changed_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill classification system tags")
    parser.add_argument("--vault-dir", default=str(PROJECT_ROOT / "research_vault"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill(Path(args.vault_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
