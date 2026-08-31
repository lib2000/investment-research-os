#!/usr/bin/env python3
"""Archive a static family aggregate and enable the derived read-only view."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/user_portfolios.json")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_raw_store(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"포트폴리오 저장 파일을 찾지 못했습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"포트폴리오 저장 파일 JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("portfolios"), dict):
        raise SystemExit("포트폴리오 저장 파일에 portfolios 객체가 없습니다.")
    return payload


def legacy_entry(store: dict[str, Any], is_family_aggregate_portfolio_name) -> tuple[str | None, dict[str, Any] | None]:
    portfolios = store.get("portfolios") if isinstance(store.get("portfolios"), dict) else {}
    for key, payload in portfolios.items():
        if not isinstance(payload, dict):
            continue
        if is_family_aggregate_portfolio_name(str(key)) or is_family_aggregate_portfolio_name(
            str(payload.get("portfolio_name") or "")
        ):
            return str(key), payload
    metadata = store.get("family_aggregate") if isinstance(store.get("family_aggregate"), dict) else {}
    snapshot = metadata.get("legacy_snapshot")
    return None, snapshot if isinstance(snapshot, dict) else None


def build_metadata(
    store: dict[str, Any],
    legacy: dict[str, Any],
    *,
    backup: dict[str, Any],
    migrated_at: str,
) -> dict[str, Any]:
    current = store.get("family_aggregate") if isinstance(store.get("family_aggregate"), dict) else {}
    settings = current.get("settings") if isinstance(current.get("settings"), dict) else {}
    settings = dict(settings)
    for key in ("max_single_position_weight", "max_sector_weight", "max_theme_weight", "notes", "created_at"):
        if key not in settings and legacy.get(key) is not None:
            settings[key] = legacy.get(key)
    return {
        **{key: value for key, value in current.items() if key not in {"legacy_snapshot", "legacy_backup", "settings"}},
        "schema_version": 1,
        "mode": "derived_read_only",
        "portfolio_name": "가족 합산",
        "settings": settings,
        "migrated_at": migrated_at,
        "legacy_backup": backup,
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.family-aggregate-migration.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def result_json(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"상태: {result['status']}")
    print(f"저장소: {result['store_path']}")
    print(f"기존 합산 보유 종목: {result.get('legacy_holding_count', 0)}개")
    if result.get("backup_path"):
        print(f"백업: {result['backup_path']}")
    print(result["message"])


def main() -> int:
    parser = argparse.ArgumentParser(description="정적 가족-합산 포트폴리오를 로컬 백업 후 읽기 전용 계산 보기로 전환합니다.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="user_portfolios.json 경로")
    parser.add_argument("--backup-dir", type=Path, default=None, help="로컬 백업 디렉터리 (기본: 저장소 _system/backups)")
    parser.add_argument("--apply", action="store_true", help="실제로 백업하고 활성 정적 합산 사본을 제거합니다.")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과를 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.portfolio_store import (  # noqa: PLC0415
        FAMILY_AGGREGATE_PORTFOLIO_KEY,
        family_aggregate_integrity_report,
        is_family_aggregate_portfolio_name,
    )

    store_path = args.store if args.store.is_absolute() else root / args.store
    store = load_raw_store(store_path)
    legacy_key, legacy = legacy_entry(store, is_family_aggregate_portfolio_name)
    if legacy is None:
        report = family_aggregate_integrity_report(store)
        result = {
            "status": "already_migrated" if report["status"] == "ok" else "not_ready",
            "store_path": str(store_path),
            "legacy_holding_count": 0,
            "backup_path": None,
            "message": "활성 정적 가족-합산 사본이 없어 변경하지 않았습니다.",
            "integrity": report,
        }
        result_json(result, args.json)
        return 0 if report["status"] == "ok" else 1

    holding_count = len(legacy.get("holdings") or []) if isinstance(legacy.get("holdings"), list) else 0
    dry_run = {
        "status": "migration_required",
        "store_path": str(store_path),
        "legacy_key": legacy_key,
        "legacy_holding_count": holding_count,
        "backup_path": None,
        "message": "정적 가족-합산 사본을 발견했습니다. --apply로 날짜별 로컬 백업 후 계산 보기로 전환합니다.",
    }
    if not args.apply:
        result_json(dry_run, args.json)
        return 0

    original_bytes = store_path.read_bytes()
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    backup_dir = args.backup_dir if args.backup_dir else store_path.parent / "backups"
    if not backup_dir.is_absolute():
        backup_dir = root / backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"user_portfolios.pre-family-aggregate-derivation.{timestamp}.json"
    backup_path.write_bytes(original_bytes)
    backup_hash = hashlib.sha256(original_bytes).hexdigest()
    if hashlib.sha256(backup_path.read_bytes()).hexdigest() != backup_hash:
        raise SystemExit("생성한 가족-합산 백업의 SHA-256 검증에 실패했습니다.")

    next_store = copy.deepcopy(store)
    next_portfolios = next_store.get("portfolios")
    if not isinstance(next_portfolios, dict):
        raise SystemExit("포트폴리오 저장소 구조가 변경되어 마이그레이션을 중단했습니다.")
    removed_keys = [
        key
        for key, payload in next_portfolios.items()
        if is_family_aggregate_portfolio_name(str(key))
        or (isinstance(payload, dict) and is_family_aggregate_portfolio_name(str(payload.get("portfolio_name") or "")))
    ]
    for key in removed_keys:
        next_portfolios.pop(key, None)

    try:
        relative_backup_path = backup_path.relative_to(store_path.parent)
        backup_reference = str(relative_backup_path).replace("\\", "/")
    except ValueError:
        backup_reference = str(backup_path)
    next_store["family_aggregate"] = build_metadata(
        next_store,
        legacy,
        backup={
            "path": backup_reference,
            "sha256": backup_hash,
            "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "legacy_holding_count": holding_count,
        },
        migrated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    atomic_write_json(store_path, next_store)
    verification = family_aggregate_integrity_report(load_raw_store(store_path))
    if verification["status"] != "ok":
        raise SystemExit("백업은 보존했지만 가족-합산 마이그레이션 검증에 실패했습니다. 활성 데이터를 자동 복원하지 않았습니다.")
    result = {
        "status": "migrated",
        "store_path": str(store_path),
        "legacy_key": legacy_key,
        "legacy_holding_count": holding_count,
        "removed_active_keys": removed_keys,
        "backup_path": str(backup_path),
        "backup_sha256": backup_hash,
        "message": "정적 가족-합산 사본을 백업하고 개인별 원장 기반의 읽기 전용 합산 보기로 전환했습니다.",
        "integrity": verification,
    }
    result_json(result, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
