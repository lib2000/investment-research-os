"""Validate the local daily recommendations store without a running backend."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/daily_recommendations.json")
DEFAULT_STATE = Path("research_vault/_system/daily_recommendations_state.json")
EXPECTED_MILESTONE_DAYS = {"7d": 7, "15d": 15, "1m": 30, "3m": 90, "6m": 180}
EXPECTED_MILESTONES = set(EXPECTED_MILESTONE_DAYS)
EXPECTED_STATE_STATUSES = {"success", "skipped_existing", "tracked", "no_candidates"}
EXPECTED_PENDING_SITUATION = "아직 추적 예정일 전입니다."
REQUIRED_EVIDENCE_CATEGORIES = {
    "저장 품질": ("저장 품질", "활용 가능", "보강 필요"),
    "목표가/리포트": ("목표가/리포트", "리포트 근거", "목표가"),
    "최근 저장/RAG": ("최근 근거 파일", "최근 저장 자료", "RAG 연결"),
    "보유/관심 범위": ("대상 범위", "보유:", "관심:"),
}


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


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"매일 추천 상태 파일을 찾지 못했습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"매일 추천 상태 파일 JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("매일 추천 상태 파일 최상위 구조가 객체가 아닙니다.")
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


def non_empty_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def evidence_category_names(evidence: list[str]) -> set[str]:
    combined = "\n".join(evidence)
    names: set[str] = set()
    for category, tokens in REQUIRED_EVIDENCE_CATEGORIES.items():
        if any(token in combined for token in tokens):
            names.add(category)
    return names


def parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def validate_tracking_milestones(record: dict[str, Any], errors: list[str]) -> None:
    label = record.get("company_name") or record.get("ticker") or record.get("record_id")
    recommendation_date = parse_iso_date(record.get("recommendation_date"))
    if not recommendation_date:
        errors.append(f"{label} 추천일 파싱 실패: {record.get('recommendation_date')}")
        return

    milestones = record.get("tracking_milestones")
    if not isinstance(milestones, list):
        errors.append(f"{label} 추적 마일스톤 구조 확인 필요")
        return

    milestone_by_key = {str(item.get("key") or ""): item for item in milestones if isinstance(item, dict)}
    for key, expected_days in EXPECTED_MILESTONE_DAYS.items():
        milestone = milestone_by_key.get(key)
        if not isinstance(milestone, dict):
            continue
        target_date = parse_iso_date(milestone.get("target_date"))
        expected_target = recommendation_date + timedelta(days=expected_days)
        if target_date != expected_target:
            errors.append(f"{label} {key} 목표일 불일치: {milestone.get('target_date')} / 기대 {expected_target.isoformat()}")
        if milestone.get("days") != expected_days:
            errors.append(f"{label} {key} 추적 일수 불일치: {milestone.get('days')} / 기대 {expected_days}")
        status = str(milestone.get("status") or "").strip()
        if status not in {"pending", "tracked", "missing_price", "error"}:
            errors.append(f"{label} {key} 추적 상태 확인 필요: {status or '미확인'}")
        if status == "pending" and not str(milestone.get("investment_situation") or "").strip():
            errors.append(f"{label} {key} 예정 상태 설명 누락")
        if status == "tracked":
            if milestone.get("price") in (None, ""):
                errors.append(f"{label} {key} 추적 가격 누락")
            if milestone.get("price_checked_at") in (None, ""):
                errors.append(f"{label} {key} 추적 확인 시각 누락")
            if milestone.get("price_change_pct") in (None, ""):
                errors.append(f"{label} {key} 추적 수익률 누락")


def nearest_milestone_label(record: dict[str, Any]) -> str:
    milestones = record.get("tracking_milestones") or []
    pending = []
    for milestone in milestones:
        if not isinstance(milestone, dict) or milestone.get("status") != "pending":
            continue
        target_date = parse_iso_date(milestone.get("target_date"))
        if target_date:
            pending.append((target_date, str(milestone.get("label") or milestone.get("key") or "추적")))
    if not pending:
        return "추적 완료 또는 확인 필요"
    target_date, label = sorted(pending)[0]
    return f"{label} {target_date.isoformat()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="매일 추천 저장 파일을 백엔드 없이 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="daily_recommendations.json 경로")
    parser.add_argument("--state", type=Path, default=None, help="daily_recommendations_state.json 경로")
    parser.add_argument("--date", default=None, help="확인할 추천일. 생략하면 latest_recommendation_date 사용")
    parser.add_argument("--min-latest", type=int, default=3, help="해당 일자에 필요한 최소 추천 수")
    parser.add_argument("--require-milestones", action="store_true", help="1주/15일/1월/3월/6월 추적표 존재 강제")
    parser.add_argument("--require-quality", action="store_true", help="점수, 근거, 리스크, 기준가 등 추천 품질 필드 존재 강제")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store
    state_path = args.state if args.state else root / DEFAULT_STATE
    if not state_path.is_absolute():
        state_path = root / state_path
    data = load_store(store)
    state = load_state(state_path)
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

    status = str(state.get("status") or "").strip()
    last_run_date = str(state.get("last_run_date") or "").strip()
    last_tracking_date = str(state.get("last_tracking_date") or "").strip()
    selected_count = state.get("selected_count")
    if status not in EXPECTED_STATE_STATUSES:
        errors.append(f"매일 추천 스케줄 상태 확인 필요: {status or '미확인'}")
    if last_run_date != latest_date:
        errors.append(f"매일 추천 마지막 실행일 불일치: {last_run_date or '미확인'} / 최신 추천일 {latest_date}")
    if last_tracking_date and last_tracking_date < latest_date:
        errors.append(f"매일 추천 추적일이 최신 추천일보다 이전: {last_tracking_date} / {latest_date}")
    if not isinstance(selected_count, int) or selected_count < args.min_latest:
        errors.append(f"매일 추천 선택 수 확인 필요: {selected_count} / 필요 {args.min_latest}")
    if not str(state.get("last_run_at") or "").strip():
        errors.append("매일 추천 마지막 실행 시각 누락")
    if not str(state.get("last_tracking_at") or "").strip():
        errors.append("매일 추천 마지막 추적 시각 누락")

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
            ticker = str(record.get("ticker") or "").strip().upper()
            generated_at = str(record.get("generated_at") or "")
            checked_at = str(record.get("baseline_price_checked_at") or "")
            record_id = str(record.get("record_id") or "")
            reasons = non_empty_strings(record.get("reasons"))
            evidence = non_empty_strings(record.get("evidence_sources"))
            risk_notes = non_empty_strings(record.get("risk_notes"))
            quality_flags = non_empty_strings(record.get("quality_flags"))
            currency = str(record.get("currency") or "KRW").upper()
            overseas_tracking = record.get("overseas_tracking")
            portfolio_risk = record.get("portfolio_risk_connection")

            if not ticker:
                errors.append(f"{label} 티커 누락")
            if record_id and ticker and not record_id.endswith(ticker):
                errors.append(f"{label} record_id/ticker 불일치: {record_id} / {ticker}")
            if generated_at[:10] != latest_date:
                errors.append(f"{label} 생성일 불일치: {generated_at} / 추천일 {latest_date}")
            if checked_at[:10] != latest_date:
                errors.append(f"{label} 기준가 조회일 불일치 또는 누락: {checked_at}")
            if record.get("baseline_price") in (None, ""):
                errors.append(f"{label} 기준가 누락")
            if not record.get("baseline_price_source"):
                errors.append(f"{label} 기준가 출처 누락")
            if len(reasons) < 2:
                errors.append(f"{label} 추천 사유 부족: {len(reasons)}개")
            if len(evidence) < 2:
                errors.append(f"{label} 근거 출처 부족: {len(evidence)}개")
            evidence_categories = evidence_category_names(evidence)
            missing_evidence_categories = set(REQUIRED_EVIDENCE_CATEGORIES) - evidence_categories
            if missing_evidence_categories:
                errors.append(f"{label} 근거 분산 부족: {', '.join(sorted(missing_evidence_categories))}")
            if len(risk_notes) < 1:
                errors.append(f"{label} 리스크 노트 누락")
            explanation = record.get("score_explanation")
            if not isinstance(explanation, dict) or explanation.get("final_score") in (None, ""):
                errors.append(f"{label} 점수 설명 누락")
            if currency != "KRW":
                if not isinstance(overseas_tracking, dict) or overseas_tracking.get("needs_fx_conversion") is not True:
                    errors.append(f"{label} 해외 종목 환율 추적 플래그 누락")
                if not any("환율" in item or "원화" in item for item in quality_flags):
                    errors.append(f"{label} 해외 종목 환율/원화 확인 문구 누락")
            if isinstance(portfolio_risk, dict) and portfolio_risk.get("linked") is True and not portfolio_risk.get("message"):
                errors.append(f"{label} 포트폴리오 연결 설명 누락")
            validate_tracking_milestones(record, errors)

        latest_sample = latest[: args.min_latest]
        latest_tickers = [str(record.get("ticker") or "").strip().upper() for record in latest_sample]
        latest_companies = [str(record.get("company_name") or "").strip() for record in latest_sample]
        duplicate_tickers = {ticker for ticker in latest_tickers if ticker and latest_tickers.count(ticker) > 1}
        duplicate_companies = {company for company in latest_companies if company and latest_companies.count(company) > 1}
        if duplicate_tickers:
            errors.append(f"최신 추천 티커 중복: {', '.join(sorted(duplicate_tickers))}")
        if duplicate_companies:
            errors.append(f"최신 추천 회사명 중복: {', '.join(sorted(duplicate_companies))}")

    print(f"저장 파일: {store}")
    print(f"상태 파일: {state_path}")
    print(f"스케줄 상태: {state.get('status') or '미확인'} | 마지막 실행 {state.get('last_run_date') or '미확인'} | 마지막 추적 {state.get('last_tracking_date') or '미확인'} | 선택 {state.get('selected_count') or 0}개")
    print(f"전체 추천 기록: {len(records)}개")
    print("일자별 추천 수: " + ", ".join(f"{date}={count}" for date, count in sorted(counts.items())))
    print(f"최신 추천일: {latest_date}")
    for record in latest[: args.min_latest]:
        company = record.get("company_name") or "회사명 확인 필요"
        score = record.get("score", "-")
        milestones = len(record.get("tracking_milestones") or [])
        evidence = non_empty_strings(record.get("evidence_sources"))
        evidence_count = len(evidence)
        evidence_categories = len(evidence_category_names(evidence))
        nearest = nearest_milestone_label(record)
        print(
            f"{record_rank(record)}위 {company} | 점수 {score} | "
            f"근거 {evidence_count}개/{evidence_categories}범주 | 추적 {milestones}개 | 다음 추적 {nearest}"
        )

    if errors:
        for error in errors:
            print(f"오류: {error}", file=sys.stderr)
        return 1
    print("매일 추천 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
