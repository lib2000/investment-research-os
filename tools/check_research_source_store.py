"""Validate cached research source automation state without a running backend."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SYSTEM_DIR = Path("research_vault/_system")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(system_dir: Path, name: str) -> dict[str, Any]:
    path = system_dir / name
    if not path.exists():
        raise SystemExit(f"소스 상태 파일을 찾지 못했습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{name} 최상위 구조가 객체가 아닙니다.")
    return data


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_hours(value: Any) -> float | None:
    parsed = parse_dt(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600


def add_issue(issues: list[str], condition: bool, message: str) -> None:
    if condition:
        issues.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="리서치 소스 캐시/상태 파일을 백엔드 없이 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="경고가 있으면 실패 코드로 종료")
    parser.add_argument("--max-source-age-hours", type=float, default=72.0, help="KCIF/지역 소스 최신성 기준")
    parser.add_argument("--max-registry-age-hours", type=float, default=168.0, help="티커 레지스트리 최신성 기준")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    system_dir = root / SYSTEM_DIR
    issues: list[str] = []

    kcif = load_json(system_dir, "kcif_reports_watch.json")
    kcif_related = len(kcif.get("related_reports") or [])
    kcif_age = age_hours(kcif.get("updated_at"))
    add_issue(issues, kcif.get("source_status") not in {"success", "cached"}, "KCIF source_status 확인 필요")
    add_issue(issues, kcif_related <= 0, "KCIF related_reports가 비어 있음")
    add_issue(issues, kcif_age is None or kcif_age > args.max_source_age_hours, "KCIF 상태 파일 최신성 확인 필요")

    regional = load_json(system_dir, "regional_business_sources_watch.json")
    regional_related = len(regional.get("related_items") or [])
    regional_age = age_hours(regional.get("updated_at"))
    source_results = regional.get("source_results") or []
    failed_sources = [item for item in source_results if isinstance(item, dict) and item.get("status") != "success"]
    add_issue(issues, regional.get("source_status") not in {"success", "cached"}, "지역/중국/대외 소스 source_status 확인 필요")
    add_issue(issues, regional_related <= 0, "지역/중국/대외 소스 related_items가 비어 있음")
    add_issue(issues, bool(failed_sources), f"지역/중국/대외 소스 실패 {len(failed_sources)}건")
    add_issue(issues, regional_age is None or regional_age > args.max_source_age_hours, "지역/중국/대외 소스 상태 파일 최신성 확인 필요")

    registry = load_json(system_dir, "ticker_registry_source_status.json")
    registry_age = age_hours(registry.get("updated_at"))
    add_issue(issues, registry.get("status") != "success", "티커 레지스트리 status가 success가 아님")
    add_issue(issues, int(registry.get("success_count") or 0) < int(registry.get("source_count") or 0), "티커 레지스트리 일부 소스 실패")
    add_issue(issues, int(registry.get("entry_count") or 0) < 10000, "티커 레지스트리 종목 수가 비정상적으로 적음")
    add_issue(issues, registry_age is None or registry_age > args.max_registry_age_hours, "티커 레지스트리 최신성 확인 필요")

    dossier = load_json(system_dir, "dossier_refresh_queue_status.json")
    add_issue(issues, dossier.get("status") != "success", "중복 Dossier 큐 status가 success가 아님")
    add_issue(issues, int(dossier.get("failed_count") or 0) > 0, "중복 Dossier 큐 실패 건 존재")

    print(f"소스 상태 폴더: {system_dir}")
    print(f"KCIF 관련 보고서: {kcif_related}개 | 상태 {kcif.get('source_status')} | 갱신 {kcif.get('updated_at')}")
    print(f"EMERiCs/CSF/KIEP 관련 자료: {regional_related}개 | 실패 소스 {len(failed_sources)}개 | 갱신 {regional.get('updated_at')}")
    print(f"티커 레지스트리: {registry.get('entry_count')}개 | 성공 {registry.get('success_count')}/{registry.get('source_count')} | 갱신 {registry.get('updated_at')}")
    print(f"중복 Dossier 큐: 후보 {dossier.get('candidate_count')}개 | 갱신 {dossier.get('refreshed_count')}개 | 실패 {dossier.get('failed_count')}개")

    if issues:
        for issue in issues:
            print(f"주의: {issue}")
        if args.strict:
            return 1
    else:
        print("리서치 소스 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
