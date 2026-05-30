"""Validate the local daily recommendations store without a running backend."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/daily_recommendations.json")
EXPECTED_MILESTONES = {"7d", "15d", "1m", "3m", "6m"}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"매일 추천 저장 파일을 찾지 못했습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"매일 추천 저장 파일 JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("매일 추천 저장 파일 최상위 구조가 객체가 아닙니다.")
    records = data.get("records")
    if not isinstance(records, list):
        raise SystemExit("매일 추천 저장 파일에 records 배열이 없습니다.")
    return data


def record_date(record: dict[str, Any]) -> str:
    value = record.get("recommendation_date")
    return value if isinstance(value, str) else ""


def record_rank(record: dict[str, Any]) -> int:
    value = record.get("rank")
    return value if isinstance(value, int) else 999


def milestone_keys(record: dict[str, Any]) -> set[str]:
    milestones = record.get("tracking_milestones") or []
    keys: set[str] = set()
    if not isinstance(milestones, list):
        return keys
    for milestone in milestones:
        if not isinstance(milestone, dict):
            continue
        key = milestone.get("key") or milestone.get("horizon") or milestone.get("label")
        if isinstance(key, str):
            keys.add(key)
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description="매일 추천 저장 파일을 백엔드 없이 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="daily_recommendations.json 경로")
    parser.add_argument("--date", default=None, help="확인할 추천일. 생략하면 latest_recommendation_date 사용")
    parser.add_argument("--min-latest", type=int, default=3, help="해당 일자에 필요한 최소 추천 수")
    parser.add_argument("--require-milestones", action="store_true", help="1주/15일/1월/3월/6월 추적표 존재 강제")
    parser.add_argument("--require-quality", action="store_true", help="점수, 근거, 리스크, 기준가 등 추천 품질 필드 존재 강제")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store
    data = load_store(store)
    raw_records = data.get("records") or []
    records = [record for record in raw_records if isinstance(record, dict)]
    if not records:
        raise SystemExit("매일 추천 저장 records가 비어 있습니다.")

    latest_date = args.date or data.get("latest_recommendation_date") or max(record_date(r) for r in records)
    latest = [record for record in records if record_date(record) == latest_date]
    latest.sort(key=record_rank)
    counts = Counter(record_date(record) for record in records)

    errors: list[str] = []
    if len(latest) < args.min_latest:
        errors.append(f"{latest_date} 추천 수 부족: {len(latest)}개 / 필요 {args.min_latest}개")
    if args.require_milestones:
        for record in latest:
            missing = EXPECTED_MILESTONES - milestone_keys(record)
            if missing:
                label = record.get("company_name") or record.get("ticker") or record.get("record_id")
                errors.append(f"{label} 추적 마일스톤 누락: {', '.join(sorted(missing))}")

    if args.require_quality:
        expected_ranks = set(range(1, args.min_latest + 1))
        actual_ranks = {record_rank(record) for record in latest[: args.min_latest]}
        if actual_ranks != expected_ranks:
            errors.append(f"최신 추천 순위 불일치: {sorted(actual_ranks)} / 기대 {sorted(expected_ranks)}")
        quality_fields = (
            ("score_components", list),
            ("reasons", list),
            ("evidence_sources", list),
            ("risk_notes", list),
            ("tracking_milestones", list),
        )
        for record in latest[: args.min_latest]:
            label = record.get("company_name") or record.get("ticker") or record.get("record_id")
            score = record.get("score")
            if not isinstance(score, (int, float)) or score <= 0:
                errors.append(f"{label} 추천 점수 확인 필요: {score}")
            for field, expected_type in quality_fields:
                value = record.get(field)
                if not isinstance(value, expected_type) or len(value) == 0:
                    errors.append(f"{label} {field} 누락")
            if record.get("baseline_price") in (None, ""):
                errors.append(f"{label} 기준가 누락")
            if not record.get("baseline_price_source"):
                errors.append(f"{label} 기준가 출처 누락")
            explanation = record.get("score_explanation")
            if not isinstance(explanation, dict) or explanation.get("final_score") in (None, ""):
                errors.append(f"{label} 점수 설명 누락")

    print(f"저장 파일: {store}")
    print(f"전체 추천 기록: {len(records)}개")
    print("일자별 추천 수: " + ", ".join(f"{date}={count}" for date, count in sorted(counts.items())))
    print(f"최신 추천일: {latest_date}")
    for record in latest[: args.min_latest]:
        company = record.get("company_name") or "회사명 확인 필요"
        score = record.get("score", "-")
        milestones = len(record.get("tracking_milestones") or [])
        evidence_count = len(record.get("evidence_sources") or [])
        print(f"{record_rank(record)}위 {company} | 점수 {score} | 근거 {evidence_count}개 | 추적 {milestones}개")

    if errors:
        for error in errors:
            print(f"오류: {error}", file=sys.stderr)
        return 1
    print("매일 추천 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
