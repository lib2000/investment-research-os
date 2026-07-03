"""Validate policy signal quality for the latest daily recommendations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def latest_recommendation_payload(system_dir: Path) -> dict[str, Any]:
    store = load_json(system_dir / "daily_recommendations.json", {"records": []})
    records = store.get("records") if isinstance(store.get("records"), list) else []
    dated_records = [record for record in records if isinstance(record, dict) and record.get("recommendation_date")]
    if not dated_records:
        return {"latest_records": [], "latest_recommendation_date": ""}
    latest_date = max(str(record.get("recommendation_date") or "") for record in dated_records)
    latest_records = [record for record in dated_records if str(record.get("recommendation_date") or "") == latest_date]
    return {
        "latest_recommendation_date": latest_date,
        "latest_records": latest_records,
    }


def dashboard_for_latest(root: Path) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.daily_recommendation_policy import build_policy_signal_quality_dashboard

    payload = latest_recommendation_payload(root / "research_vault" / "_system")
    return build_policy_signal_quality_dashboard(payload)


def strict_errors(dashboard: dict[str, Any], *, fail_on_review: bool, require_metadata: bool) -> list[str]:
    errors: list[str] = []
    record_count = int(dashboard.get("record_count") or 0)
    score_applied_count = int(dashboard.get("score_applied_count") or 0)
    review_count = int(dashboard.get("review_count") or 0)
    rows = dashboard.get("rows") if isinstance(dashboard.get("rows"), list) else []
    missing_metadata = [
        row
        for row in rows
        if isinstance(row, dict) and not isinstance(row.get("policy_signal_summary"), dict)
    ]
    if not record_count:
        errors.append("최신 추천 기록이 없습니다.")
    if require_metadata and missing_metadata:
        errors.append(f"정책 신호 메타데이터 누락 {len(missing_metadata)}개")
    level_counts = dashboard.get("level_counts") if isinstance(dashboard.get("level_counts"), dict) else {}
    direct_count = int(level_counts.get("direct") or 0)
    if record_count and direct_count and score_applied_count == 0:
        errors.append("직접 정책 신호가 있는데 점수 반영이 없습니다.")
    if fail_on_review and review_count:
        errors.append(f"정책 신호 검토 필요 {review_count}개")
    return errors


def build_result(dashboard: dict[str, Any], *, fail_on_review: bool, require_metadata: bool) -> dict[str, Any]:
    errors = strict_errors(
        dashboard,
        fail_on_review=fail_on_review,
        require_metadata=require_metadata,
    )
    return {
        "status": "warning" if errors else "ok",
        "errors": errors,
        "recommendation_date": dashboard.get("recommendation_date") or "",
        "record_count": int(dashboard.get("record_count") or 0),
        "score_applied_count": int(dashboard.get("score_applied_count") or 0),
        "review_count": int(dashboard.get("review_count") or 0),
        "total_policy_net_points": int(dashboard.get("total_policy_net_points") or 0),
        "level_counts": dashboard.get("level_counts") if isinstance(dashboard.get("level_counts"), dict) else {},
        "rows": dashboard.get("rows") if isinstance(dashboard.get("rows"), list) else [],
        "review_rows": dashboard.get("review_rows") if isinstance(dashboard.get("review_rows"), list) else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="최신 매일 추천의 정책 신호 품질을 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="최신 추천/정책 점수 반영 누락을 실패로 처리합니다.")
    parser.add_argument("--fail-on-review", action="store_true", help="검토 필요 항목이 있으면 실패로 처리합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument(
        "--allow-missing-metadata",
        action="store_true",
        help="정책 신호 메타데이터 누락을 strict 실패로 보지 않습니다.",
    )
    args = parser.parse_args()

    root = project_root(Path.cwd())
    dashboard = dashboard_for_latest(root)
    result = build_result(
        dashboard,
        fail_on_review=args.fail_on_review,
        require_metadata=not args.allow_missing_metadata,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.strict and result["errors"] else 0

    level_counts = dashboard.get("level_counts") if isinstance(dashboard.get("level_counts"), dict) else {}
    rows = dashboard.get("rows") if isinstance(dashboard.get("rows"), list) else []
    review_rows = dashboard.get("review_rows") if isinstance(dashboard.get("review_rows"), list) else []

    print(f"프로젝트 루트: {root}")
    print(f"추천일: {dashboard.get('recommendation_date') or '미확인'}")
    print(
        "정책 신호 품질: "
        f"추천 {int(dashboard.get('record_count') or 0)}개, "
        f"점수 반영 {int(dashboard.get('score_applied_count') or 0)}개, "
        f"검토 필요 {int(dashboard.get('review_count') or 0)}개, "
        f"순 정책 점수 {int(dashboard.get('total_policy_net_points') or 0)}"
    )
    print(
        "매칭 수준: "
        f"직접 {int(level_counts.get('direct') or 0)} / "
        f"테마 {int(level_counts.get('theme') or 0)} / "
        f"시장 {int(level_counts.get('market') or 0)} / "
        f"없음 {int(level_counts.get('none') or 0)}"
    )
    for row in rows[:8]:
        if not isinstance(row, dict):
            continue
        impact = row.get("score_impact") if isinstance(row.get("score_impact"), dict) else {}
        print(
            "- "
            f"{row.get('market') or '?'}#{row.get('rank') or '?'} {row.get('ticker') or ''} "
            f"{row.get('company_name') or ''} | {row.get('match_level_label') or '미확인'} | "
            f"점수반영 {bool(row.get('score_applied'))} | "
            f"검토 {row.get('review_status') or 'info'} | "
            f"net {int(impact.get('net_points') or 0)}"
        )
    if review_rows:
        print("검토 필요:")
        for row in review_rows[:8]:
            if isinstance(row, dict):
                print(f"  - {row.get('ticker') or ''}: {row.get('review_reason') or '확인 필요'}")

    errors = result["errors"]
    if args.strict and errors:
        print("정책 신호 품질 점검 실패")
        for error in errors:
            print(f"- {error}")
        return 1
    print("정책 신호 품질 점검 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
