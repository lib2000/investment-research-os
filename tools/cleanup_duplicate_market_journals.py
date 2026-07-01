"""Preview or soft-archive duplicate market-close journal storage files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MARKET_REPORT_TYPE = "market-close-review"


@dataclass(frozen=True)
class MarketJournalFile:
    key: tuple[str, str]
    ticker: str
    file_name: str
    json_file_name: str
    relative_path: str
    json_relative_path: str
    entry_id: str
    market: str
    session_date: str
    updated_at: str
    source_provider: str
    source_origin: str
    in_manifest: bool
    archived: bool
    protected: bool


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


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def is_archived(entry: dict[str, Any] | None, payload: dict[str, Any] | None) -> bool:
    entry = entry if isinstance(entry, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    tags = [str(tag).lower() for tag in (entry.get("tags") or [])]
    return bool(
        entry.get("is_deleted")
        or payload.get("is_deleted")
        or str(entry.get("status") or "").lower() == "archived"
        or str(payload.get("status") or "").lower() == "archived"
        or "archived" in tags
    )


def normalize_rel(path: str | None) -> str:
    return str(path or "").replace("\\", "/").strip()


def protected_paths(vault: Path) -> set[str]:
    system_dir = vault / "_system"
    protected: set[str] = set()
    for name in ("telegram_market_close_journal_state.json", "naver_market_close_journal_state.json"):
        state = load_json(system_dir / name, {})
        storage = state.get("storage") if isinstance(state, dict) else {}
        if not isinstance(storage, dict):
            continue
        for key in ("relative_path", "json_relative_path"):
            value = normalize_rel(storage.get(key))
            if value:
                protected.add(value)
    return protected


def entry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    entry = payload.get("entry") if isinstance(payload.get("entry"), dict) else {}
    return entry


def candidate_key(entry: dict[str, Any], manifest_entry: dict[str, Any]) -> tuple[str, str] | None:
    market = str(entry.get("market") or manifest_entry.get("market") or "").strip().upper()
    session_date = str(entry.get("session_date") or manifest_entry.get("session_date") or "").strip()
    entry_id = str(entry.get("entry_id") or "").strip()
    if entry_id:
        return ("entry_id", entry_id)
    if market and session_date:
        return (market, session_date)
    return None


def collect_market_journal_files(root: Path) -> list[MarketJournalFile]:
    vault = root / "research_vault"
    manifest = load_json(vault / "manifest.json", [])
    manifest_by_json: dict[str, dict[str, Any]] = {}
    if isinstance(manifest, list):
        for item in manifest:
            if not isinstance(item, dict):
                continue
            rel = normalize_rel(item.get("json_relative_path"))
            if rel:
                manifest_by_json[rel] = item

    protected = protected_paths(vault)
    files: list[MarketJournalFile] = []
    for json_path in sorted(vault.glob("MARKET-*/*market-close-review*.json")):
        md_path = json_path.with_suffix(".md")
        if not md_path.exists():
            continue
        if md_path.stem.endswith("-news-inbox"):
            continue
        payload = load_json(json_path, {})
        if not isinstance(payload, dict):
            continue
        rel = normalize_rel(json_path.relative_to(root).as_posix())
        md_rel = normalize_rel(md_path.relative_to(root).as_posix())
        manifest_entry = manifest_by_json.get(rel, {})
        entry = entry_payload(payload)
        key = candidate_key(entry, manifest_entry)
        if not key:
            continue
        ticker = md_path.parent.name
        files.append(
            MarketJournalFile(
                key=key,
                ticker=ticker,
                file_name=md_path.name,
                json_file_name=json_path.name,
                relative_path=md_rel,
                json_relative_path=rel,
                entry_id=str(entry.get("entry_id") or "").strip(),
                market=str(entry.get("market") or manifest_entry.get("market") or "").strip().upper(),
                session_date=str(entry.get("session_date") or manifest_entry.get("session_date") or "").strip(),
                updated_at=str(entry.get("updated_at") or payload.get("updated_at") or "").strip(),
                source_provider=str(entry.get("source_provider") or manifest_entry.get("source_provider") or "").strip(),
                source_origin=str(entry.get("source_origin") or manifest_entry.get("source_origin") or "").strip(),
                in_manifest=bool(manifest_entry),
                archived=is_archived(manifest_entry, payload),
                protected=md_rel in protected or rel in protected,
            )
        )
    return files


def parse_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def keep_sort_key(item: MarketJournalFile) -> tuple[int, str, str]:
    return (
        1 if item.protected else 0,
        parse_timestamp(item.updated_at),
        item.file_name,
    )


def build_cleanup_plan(root: Path) -> dict[str, Any]:
    files = collect_market_journal_files(root)
    groups: dict[tuple[str, str], list[MarketJournalFile]] = {}
    for item in files:
        if item.archived:
            continue
        groups.setdefault(item.key, []).append(item)

    duplicate_groups: list[dict[str, Any]] = []
    candidates: list[MarketJournalFile] = []
    for key, items in sorted(groups.items()):
        if len(items) <= 1:
            continue
        ordered = sorted(items, key=keep_sort_key, reverse=True)
        keep = ordered[0]
        duplicates = ordered[1:]
        candidates.extend(duplicates)
        duplicate_groups.append(
            {
                "key": list(key),
                "market": keep.market,
                "session_date": keep.session_date,
                "entry_id": keep.entry_id,
                "keep_file": keep.file_name,
                "keep_json_file": keep.json_file_name,
                "keep_protected": keep.protected,
                "duplicate_count": len(duplicates),
                "duplicates": [
                    {
                        "file_name": item.file_name,
                        "json_file_name": item.json_file_name,
                        "relative_path": item.relative_path,
                        "json_relative_path": item.json_relative_path,
                        "in_manifest": item.in_manifest,
                        "protected": item.protected,
                    }
                    for item in duplicates
                ],
            }
        )

    return {
        "status": "success",
        "module": "duplicate_market_journal_cleanup",
        "policy": "soft_archive",
        "scanned_count": len(files),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_candidate_count": len(candidates),
        "groups": duplicate_groups,
    }


def apply_cleanup(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    vault = root / "research_vault"
    manifest_path = vault / "manifest.json"
    manifest = load_json(manifest_path, [])
    if not isinstance(manifest, list):
        raise SystemExit("manifest.json 구조가 배열이 아닙니다.")
    manifest_by_rel = {
        normalize_rel(item.get("relative_path")): item
        for item in manifest
        if isinstance(item, dict) and normalize_rel(item.get("relative_path"))
    }
    now = datetime.now().astimezone().replace(microsecond=0).isoformat()
    reason = "중복 시장일지 보관본이라 삭제하지 않고 소프트 보관 처리했습니다."
    archived: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for group in plan.get("groups", []):
        for duplicate in group.get("duplicates", []):
            rel = normalize_rel(duplicate.get("relative_path"))
            json_rel = normalize_rel(duplicate.get("json_relative_path"))
            md_path = root / rel
            json_path = root / json_rel
            try:
                payload = load_json(json_path, {})
                if isinstance(payload, dict):
                    payload["status"] = "archived"
                    payload["is_deleted"] = True
                    payload["archived_at"] = now
                    payload["archive_reason"] = reason
                    payload["updated_at"] = now
                    write_json(json_path, payload)

                manifest_entry = manifest_by_rel.get(rel)
                if not manifest_entry:
                    manifest_entry = {
                        "ticker": md_path.parent.name,
                        "type": MARKET_REPORT_TYPE,
                        "date": group.get("session_date"),
                        "file_name": md_path.name,
                        "relative_path": rel,
                        "json_file_name": json_path.name if json_path.exists() else None,
                        "json_relative_path": json_rel if json_path.exists() else None,
                    }
                    manifest.append(manifest_entry)
                    manifest_by_rel[rel] = manifest_entry
                manifest_entry["status"] = "archived"
                manifest_entry["is_deleted"] = True
                manifest_entry["archived_at"] = now
                manifest_entry["archive_reason"] = reason
                manifest_entry["updated_at"] = now
                tags = list(dict.fromkeys([*(manifest_entry.get("tags") or []), "archived"]))
                manifest_entry["tags"] = tags
                archived.append({"relative_path": rel, "json_relative_path": json_rel, "archived_at": now})
            except Exception as exc:
                errors.append({"relative_path": rel, "error": str(exc)})

    manifest.sort(key=lambda item: (str(item.get("ticker") or ""), str(item.get("date") or ""), str(item.get("type") or ""), str(item.get("file_name") or "")))
    write_json(manifest_path, manifest)
    return {
        **plan,
        "applied": True,
        "archived_count": len(archived),
        "archived_files": archived,
        "errors": errors,
        "status": "success" if not errors else "partial_success",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="중복 시장일지 보관 파일을 soft archive로 정리합니다.")
    parser.add_argument("--apply", action="store_true", help="dry-run 대신 soft archive 메타데이터를 실제 기록합니다.")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    plan = build_cleanup_plan(root)
    result = apply_cleanup(root, plan) if args.apply else {**plan, "applied": False, "archived_count": 0, "archived_files": [], "errors": []}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        mode = "적용" if args.apply else "dry-run"
        print(f"중복 시장일지 정리 {mode}: 그룹 {result['duplicate_group_count']}개 | 후보 {result['duplicate_candidate_count']}개 | 보관 {result['archived_count']}개")
        for group in result.get("groups", [])[:10]:
            print(f"- {group.get('market')} {group.get('session_date')} keep={group.get('keep_file')} duplicates={group.get('duplicate_count')}")
            for duplicate in group.get("duplicates", [])[:5]:
                print(f"  - {duplicate.get('file_name')} | manifest={duplicate.get('in_manifest')}")
        if result.get("errors"):
            print(f"오류 {len(result['errors'])}개")
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
