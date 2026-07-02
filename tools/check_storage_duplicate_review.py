"""Validate storage duplicate review state without a backend."""

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


def load_duplicate_review(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"중복 리뷰 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"중복 리뷰 JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("중복 리뷰 최상위 구조가 객체가 아닙니다.")
    return payload


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
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


def existing_relative_path(root: Path, entry: dict[str, Any]) -> bool:
    relative_path = str(entry.get("relative_path") or "").strip()
    return bool(relative_path) and (root / relative_path).exists()


def summarize_duplicate_review(root: Path) -> dict[str, Any]:
    payload = load_duplicate_review(root / SYSTEM_DIR / "storage_duplicate_review.json")
    groups = [group for group in (payload.get("groups") or []) if isinstance(group, dict)]
    duplicate_entry_count = sum(len(group.get("duplicates") or []) for group in groups)
    representative_missing = []
    duplicate_missing = []
    for group in groups:
        representative = group.get("representative") if isinstance(group.get("representative"), dict) else {}
        if representative and not existing_relative_path(root, representative):
            representative_missing.append(representative.get("relative_path") or representative.get("title") or group.get("group_id"))
        for duplicate in [item for item in (group.get("duplicates") or []) if isinstance(item, dict)]:
            if not existing_relative_path(root, duplicate):
                duplicate_missing.append(duplicate.get("relative_path") or duplicate.get("title") or group.get("group_id"))
    ticker_breakdown = [
        row for row in (payload.get("ticker_breakdown") or []) if isinstance(row, dict)
    ]
    return {
        "status": payload.get("status"),
        "as_of": payload.get("as_of"),
        "age_hours": age_hours(payload.get("as_of")),
        "checked_count": int(payload.get("checked_count") or 0),
        "unique_representative_count": int(payload.get("unique_representative_count") or 0),
        "duplicate_group_count": int(payload.get("duplicate_group_count") or 0),
        "duplicate_entry_count": int(payload.get("duplicate_entry_count") or 0),
        "calculated_duplicate_entry_count": duplicate_entry_count,
        "representative_policy": payload.get("representative_policy") if isinstance(payload.get("representative_policy"), dict) else {},
        "dossier_usage_summary": payload.get("dossier_usage_summary") if isinstance(payload.get("dossier_usage_summary"), dict) else {},
        "groups": groups,
        "ticker_breakdown": ticker_breakdown,
        "representative_missing": representative_missing,
        "duplicate_missing": duplicate_missing,
    }


def strict_errors(status: dict[str, Any], *, max_age_hours: float = 168.0) -> list[str]:
    errors: list[str] = []
    if status.get("status") != "success":
        errors.append("중복 리뷰 상태가 success가 아닙니다.")
    age = status.get("age_hours")
    if age is None or float(age) > max_age_hours:
        errors.append("중복 리뷰 최신성 확인이 필요합니다.")
    if status.get("duplicate_entry_count") != status.get("calculated_duplicate_entry_count"):
        errors.append("중복 항목 수와 그룹 상세 합계가 일치하지 않습니다.")
    if status.get("duplicate_group_count") != len(status.get("groups") or []):
        errors.append("중복 그룹 수와 그룹 상세 개수가 일치하지 않습니다.")
    policy = status.get("representative_policy") if isinstance(status.get("representative_policy"), dict) else {}
    if policy.get("dossier_usage") != "representative_only":
        errors.append("Dossier 사용 정책이 representative_only가 아닙니다.")
    if policy.get("duplicate_usage") != "excluded_from_dossier":
        errors.append("중복 자료 제외 정책이 excluded_from_dossier가 아닙니다.")
    if policy.get("hard_delete_allowed") is not False:
        errors.append("중복 자료 hard delete 금지 정책이 아닙니다.")
    summary = status.get("dossier_usage_summary") if isinstance(status.get("dossier_usage_summary"), dict) else {}
    if int(summary.get("duplicate_excluded_count") or 0) != int(status.get("duplicate_entry_count") or 0):
        errors.append("Dossier 제외 중복 수가 중복 항목 수와 일치하지 않습니다.")
    if status.get("representative_missing"):
        errors.append("대표 자료 파일 경로 누락: " + ", ".join(map(str, status["representative_missing"][:3])))
    if status.get("duplicate_missing"):
        errors.append("중복 자료 파일 경로 누락: " + ", ".join(map(str, status["duplicate_missing"][:3])))
    return errors


def duplicate_preview_lines(group: dict[str, Any], *, limit: int = 3) -> list[str]:
    duplicates = [item for item in (group.get("duplicates") or []) if isinstance(item, dict)]
    lines: list[str] = []
    for duplicate in duplicates[: max(0, limit)]:
        title = duplicate.get("title") or duplicate.get("relative_path") or duplicate.get("file_name") or "중복 후보 미확인"
        reason = duplicate.get("duplicate_reason") or "중복 사유 미확인"
        similarity = duplicate.get("similarity")
        similarity_text = ""
        if isinstance(similarity, (int, float)):
            similarity_text = f" | 유사도 {similarity:.2f}"
        source = duplicate.get("source_url") or duplicate.get("relative_path") or ""
        source_text = f" | {source}" if source else ""
        lines.append(f"  - 후보 {title} | {reason}{similarity_text}{source_text}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="저장 자료 중복 리뷰 상태를 백엔드 없이 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="운영 품질 문제가 있으면 실패 코드로 종료")
    parser.add_argument("--max-age-hours", type=float, default=168.0, help="중복 리뷰 최신성 기준")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    status = summarize_duplicate_review(root)
    print(
        "저장 자료 중복 리뷰: "
        f"상태 {status['status'] or '미확인'} | "
        f"검사 {status['checked_count']}개 | "
        f"대표 {status['unique_representative_count']}개 | "
        f"중복 그룹 {status['duplicate_group_count']}개 | "
        f"중복 항목 {status['duplicate_entry_count']}개",
        flush=True,
    )
    if status.get("as_of"):
        age = status.get("age_hours")
        age_label = f"{age:.1f}시간 전" if isinstance(age, (int, float)) else "경과 미확인"
        print(f"업데이트: {status['as_of']} ({age_label})", flush=True)
    policy = status["representative_policy"]
    print(
        "정책: "
        f"Dossier={policy.get('dossier_usage') or '미확인'}, "
        f"중복={policy.get('duplicate_usage') or '미확인'}, "
        f"hard_delete_allowed={policy.get('hard_delete_allowed')}",
        flush=True,
    )
    for group in status["groups"][:5]:
        representative = group.get("representative") if isinstance(group.get("representative"), dict) else {}
        print(
            f"- {group.get('ticker') or 'UNKNOWN'} | 중복 {group.get('duplicate_count') or len(group.get('duplicates') or [])}개 | "
            f"대표 {representative.get('title') or representative.get('relative_path') or '미확인'}",
            flush=True,
        )
        for line in duplicate_preview_lines(group):
            print(line, flush=True)
    errors = strict_errors(status, max_age_hours=args.max_age_hours)
    if errors:
        print("점검 오류:", flush=True)
        for error in errors:
            print(f"- {error}", flush=True)
    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
