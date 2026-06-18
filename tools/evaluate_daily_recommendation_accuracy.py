"""Evaluate daily recommendation accuracy readiness and tracked outcomes.

This is a read-only eval for the daily recommendation store. It complements the
strict store checks by producing a single score plus actionable bottlenecks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/daily_recommendations.json")
DEFAULT_STATE = Path("research_vault/_system/daily_recommendations_state.json")
REQUIRED_EVIDENCE_TOKENS = {
    "target_scope": ("대상 범위", "보유:", "관심:"),
    "report_or_target": ("목표가/리포트", "리포트 근거", "목표가"),
    "recent_or_rag": ("최근 근거 파일", "최근 저장 자료", "RAG 연결"),
    "quality": ("저장 품질", "활용 가능", "검증 저장자료"),
}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"JSON을 읽지 못했습니다: {path} / {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON 최상위 구조가 객체가 아닙니다: {path}")
    return payload


def parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def non_empty_strings(value: object) -> list[str]:
    return [str(item).strip() for item in value if str(item or "").strip()] if isinstance(value, list) else []


def component_points(record: dict[str, Any]) -> tuple[int, int]:
    positive = 0
    for component in record.get("score_components") or []:
        if not isinstance(component, dict):
            continue
        try:
            positive += int(component.get("points", component.get("score", component.get("value"))) or 0)
        except (TypeError, ValueError):
            continue
    penalty = 0
    for penalty_item in record.get("score_penalties") or []:
        if isinstance(penalty_item, dict):
            try:
                penalty += abs(int(penalty_item.get("points") or 0))
            except (TypeError, ValueError):
                continue
            continue
        match = re.search(r"\(-\s*(\d+)\s*\)", str(penalty_item or ""))
        if match:
            penalty += int(match.group(1))
            continue
    explanation = record.get("score_explanation") if isinstance(record.get("score_explanation"), dict) else {}
    if not penalty and isinstance(explanation.get("penalty_points"), (int, float)):
        penalty = abs(int(explanation.get("penalty_points") or 0))
    return positive, penalty


def evidence_categories(record: dict[str, Any]) -> set[str]:
    combined = "\n".join(non_empty_strings(record.get("evidence_sources")) + non_empty_strings(record.get("reasons")))
    return {
        category
        for category, tokens in REQUIRED_EVIDENCE_TOKENS.items()
        if any(token in combined for token in tokens)
    }


def citation_path_exists(root: Path, item: dict[str, Any]) -> bool:
    relative_path = str(item.get("source_relative_path") or "").strip()
    if not relative_path:
        return False
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return path.is_file()


def latest_records(records: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    dates = [str(record.get("recommendation_date") or "") for record in records if record.get("recommendation_date")]
    latest_date = max(dates) if dates else ""
    latest = [record for record in records if record.get("recommendation_date") == latest_date]
    latest.sort(key=lambda item: int(item.get("rank") or 999))
    return latest_date, latest


def score_latest_records(root: Path, latest: list[dict[str, Any]], expected_count: int) -> tuple[float, list[str], dict[str, Any]]:
    failures: list[str] = []
    points = 0.0
    max_points = 80.0
    if len(latest) == expected_count:
        points += 8
    else:
        failures.append(f"latest_count: 최신 추천 {len(latest)}개 / 기대 {expected_count}개")
    ranks = [int(record.get("rank") or 999) for record in latest]
    tickers = [normalize_ticker(record.get("ticker")) for record in latest]
    if ranks == list(range(1, len(latest) + 1)) and len(tickers) == len(set(tickers)):
        points += 7
    else:
        failures.append(f"rank_integrity: 순위 또는 티커 중복 확인 필요 ranks={ranks} tickers={tickers}")

    record_summaries: list[dict[str, Any]] = []
    per_record_max = 65.0 / max(1, expected_count)
    for record in latest[:expected_count]:
        label = f"{record.get('rank')}위 {record.get('company_name') or record.get('ticker')}"
        record_points = 0.0
        categories = evidence_categories(record)
        evidence = non_empty_strings(record.get("evidence_sources"))
        reasons = non_empty_strings(record.get("reasons"))
        risk_notes = non_empty_strings(record.get("risk_notes"))
        citations = [item for item in record.get("evidence_documents") or [] if isinstance(item, dict)]
        usable_citations = sum(1 for item in citations if citation_path_exists(root, item))
        components = [item for item in record.get("score_components") or [] if isinstance(item, dict)]
        positive, penalty = component_points(record)
        expected_score = positive - penalty
        stored_score = record.get("score")

        if len(components) >= 8:
            record_points += 3
        else:
            failures.append(f"{label}: score_component_count {len(components)}개 / 최소 8개")
        if isinstance(stored_score, (int, float)) and int(stored_score) == expected_score:
            record_points += 4
        else:
            failures.append(f"{label}: score_alignment 저장 {stored_score} / 구성 {expected_score}")
        if len(evidence) >= 6:
            record_points += 4
        else:
            failures.append(f"{label}: evidence_source_count {len(evidence)}개 / 최소 6개")
        if len(categories) >= 4:
            record_points += 5
        else:
            failures.append(f"{label}: evidence_category_coverage {sorted(categories)} / 최소 4범주")
        if usable_citations >= 1:
            record_points += 4
        else:
            failures.append(f"{label}: usable_citation_count {usable_citations}개 / 최소 1개")
        if len(reasons) >= 4:
            record_points += 2
        else:
            failures.append(f"{label}: reason_count {len(reasons)}개 / 최소 4개")
        if risk_notes:
            record_points += 2
        else:
            failures.append(f"{label}: risk_note 누락")
        if record.get("baseline_price") not in (None, "") and record.get("baseline_price_checked_at"):
            record_points += 2
        else:
            failures.append(f"{label}: baseline_price 또는 checked_at 누락")
        if len(record.get("tracking_milestones") or []) >= 5:
            record_points += 1.6667
        else:
            failures.append(f"{label}: tracking_milestones 부족")
        if record.get("portfolio_context"):
            record_points += 1.0
        else:
            failures.append(f"{label}: portfolio_context 누락")

        points += min(per_record_max, record_points)
        record_summaries.append(
            {
                "rank": record.get("rank"),
                "ticker": record.get("ticker"),
                "company_name": record.get("company_name"),
                "score": stored_score,
                "component_count": len(components),
                "evidence_count": len(evidence),
                "evidence_categories": sorted(categories),
                "usable_citation_count": usable_citations,
                "record_points": round(record_points, 2),
            }
        )
    return points / max_points * 80.0, failures, {"latest_records": record_summaries}


def score_tracked_outcomes(records: list[dict[str, Any]]) -> tuple[float, list[str], dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    unavailable = 0
    for record in records:
        for milestone in record.get("tracking_milestones") or []:
            if not isinstance(milestone, dict):
                continue
            status = str(milestone.get("status") or "")
            if status == "complete":
                try:
                    change_pct = float(milestone.get("price_change_pct") or 0)
                except (TypeError, ValueError):
                    change_pct = 0.0
                completed.append(
                    {
                        "ticker": record.get("ticker"),
                        "company_name": record.get("company_name"),
                        "rank": record.get("rank"),
                        "recommendation_date": record.get("recommendation_date"),
                        "milestone": milestone.get("label") or milestone.get("key"),
                        "price_change_pct": change_pct,
                    }
                )
            elif status == "price_unavailable":
                unavailable += 1
    failures: list[str] = []
    if not completed:
        failures.append("tracked_outcome: 완료된 추적 마일스톤이 없어 성과 기반 정확도는 중립 처리")
        return 10.0, failures, {"completed_count": 0, "price_unavailable_count": unavailable}
    positive = sum(1 for item in completed if item["price_change_pct"] > 0.02)
    flat = sum(1 for item in completed if -0.02 <= item["price_change_pct"] <= 0.02)
    hit_rate = (positive + 0.5 * flat) / len(completed)
    outcome_points = 20.0 * hit_rate
    if unavailable:
        outcome_points -= min(4.0, unavailable * 0.5)
        failures.append(f"tracked_outcome: 가격 확인 불가 마일스톤 {unavailable}개")
    if hit_rate < 0.5:
        failures.append(f"tracked_outcome: hit_rate {hit_rate:.2f} / 목표 0.50")
    completed.sort(key=lambda item: item["price_change_pct"])
    return max(0.0, outcome_points), failures, {
        "completed_count": len(completed),
        "positive_count": positive,
        "flat_count": flat,
        "negative_count": len(completed) - positive - flat,
        "hit_rate": round(hit_rate, 4),
        "worst": completed[:3],
        "best": list(reversed(completed[-3:])),
        "price_unavailable_count": unavailable,
    }


def evaluate(root: Path, store_path: Path, state_path: Path, expected_latest_count: int) -> dict[str, Any]:
    store = load_json(store_path)
    state = load_json(state_path)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date, latest = latest_records(records)
    latest_score, latest_failures, latest_details = score_latest_records(root, latest, expected_latest_count)
    outcome_score, outcome_failures, outcome_details = score_tracked_outcomes(records)
    score = round(min(100.0, latest_score + outcome_score), 2)
    counts_by_date = Counter(str(record.get("recommendation_date") or "") for record in records)
    return {
        "status": "success" if score >= 90 else "needs_improvement",
        "score": score,
        "max_score": 100,
        "latest_recommendation_date": latest_date,
        "record_count": len(records),
        "latest_count": len(latest),
        "date_count": dict(sorted(counts_by_date.items())),
        "state": {
            "status": state.get("status"),
            "last_run_date": state.get("last_run_date"),
            "last_tracking_date": state.get("last_tracking_date"),
            "selected_count": state.get("selected_count"),
        },
        "subscores": {
            "latest_quality": round(latest_score, 2),
            "tracked_outcomes": round(outcome_score, 2),
        },
        "failures": latest_failures + outcome_failures,
        "details": {
            **latest_details,
            "tracked_outcomes": outcome_details,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="매일 추천 정확도/추적 품질 eval")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--expected-latest-count", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store_path = args.store if args.store.is_absolute() else root / args.store
    state_path = args.state if args.state.is_absolute() else root / args.state
    result = evaluate(root, store_path, state_path, args.expected_latest_count)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"추천 정확도 eval 점수: {result['score']:.2f}/100")
        print(
            "세부 점수: "
            + ", ".join(f"{key}={value}" for key, value in result["subscores"].items())
        )
        print(
            f"최신 추천일: {result['latest_recommendation_date']} | 최신 추천 {result['latest_count']}개 | 전체 {result['record_count']}개"
        )
        failures = result.get("failures") or []
        if failures:
            print("실패/병목:")
            for failure in failures:
                print(f"- {failure}")
        else:
            print("실패/병목: 없음")
    if args.min_score and float(result["score"]) < float(args.min_score):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
