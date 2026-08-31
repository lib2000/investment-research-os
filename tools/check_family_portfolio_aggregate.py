#!/usr/bin/env python3
"""Validate the local derived family-aggregate portfolio contract."""

from __future__ import annotations

import argparse
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


def safe_backup_path(store_path: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = store_path.parent / candidate
    try:
        candidate.resolve().relative_to(store_path.parent.resolve())
    except ValueError:
        return None
    return candidate


def verify_legacy_backup(store_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    backup = metadata.get("legacy_backup") if isinstance(metadata.get("legacy_backup"), dict) else None
    if not backup:
        return {"status": "not_applicable", "path": None, "errors": []}
    path = safe_backup_path(store_path, backup.get("path"))
    errors: list[str] = []
    if path is None:
        errors.append("가족-합산 백업 경로가 저장소 범위를 벗어났거나 비어 있습니다.")
    elif not path.exists():
        errors.append("가족-합산 백업 파일을 찾지 못했습니다.")
    else:
        expected_hash = str(backup.get("sha256") or "").lower()
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if not expected_hash or actual_hash != expected_hash:
            errors.append("가족-합산 백업 SHA-256이 메타데이터와 일치하지 않습니다.")
    return {
        "status": "error" if errors else "ok",
        "path": str(path) if path else None,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="개인별 원장 기반 가족-합산의 읽기 전용 무결성을 점검합니다.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="user_portfolios.json 경로")
    parser.add_argument("--state-path", type=Path, default=None, help="점검 상태 JSON 경로")
    parser.add_argument("--write-state", action="store_true", help="점검 결과를 로컬 상태 파일로 저장합니다.")
    parser.add_argument("--strict", action="store_true", help="정적 중복/백업 손상 시 실패 코드로 종료합니다.")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과를 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.portfolio_store import family_aggregate_integrity_report  # noqa: PLC0415

    store_path = args.store if args.store.is_absolute() else root / args.store
    store = load_raw_store(store_path)
    result = family_aggregate_integrity_report(store)
    metadata = store.get("family_aggregate") if isinstance(store.get("family_aggregate"), dict) else {}
    backup = verify_legacy_backup(store_path, metadata)
    errors = [*result.get("errors", []), *backup.get("errors", [])]
    checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
    result.update(
        {
            "status": "error" if errors else "ok",
            "checked_at": checked_at,
            "store_path": str(store_path),
            "legacy_backup_validation": backup,
            "errors": errors,
            "safety": {
                "external_api_called": False,
                "broker_order_endpoint_called": False,
                "automatic_order_submission": False,
            },
        }
    )
    if args.write_state:
        state_path = args.state_path if args.state_path else store_path.parent / "family_portfolio_aggregate_integrity.json"
        if not state_path.is_absolute():
            state_path = root / state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["state_path"] = str(state_path)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"상태: {result['status']}")
        print(f"개인별 포트폴리오: {result['owner_portfolio_count']}개")
        print(f"자동 합산 보유 종목: {result['derived_holding_count']}개")
        print(f"정적 합산 사본: {len(result['legacy_static_entries'])}개")
        if backup.get("path"):
            print(f"레거시 백업: {backup['status']} · {backup['path']}")
        for error in errors:
            print(f"오류: {error}")

    return 1 if args.strict and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
