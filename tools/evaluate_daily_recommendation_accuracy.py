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


def parse_daily_time(value: object) -> tuple[int, int]:
    match = re.match(r"^(\d{1,2}):(\d{2})$", str(value or "08:00").strip())
    if not match:
        return 8, 0
    return min(max(int(match.group(1)), 0), 23), min(max(int(match.group(2)), 0), 59)


def latest_policy_drift_deferred_until_schedule(
    latest_date: str | None,
    *,
    now: datetime,
    daily_time: object = "08:00",
    enabled: bool = True,
) -> bool:
    if not enabled:
        return False
    parsed_latest = parse_iso_date(latest_date)
    if not parsed_latest or parsed_latest >= now.date():
        return False
    hour, minute = parse_daily_time(daily_time)
    scheduled_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now < scheduled_at


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


def score_tracked_outcomes(
    records: list[dict[str, Any]],
    tracking_feedback_profiles: dict[str, dict[str, Any]] | None = None,
) -> tuple[float, list[str], dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    unavailable = 0
    by_ticker: dict[str, dict[str, Any]] = {}
    by_milestone: dict[str, dict[str, Any]] = {}
    by_date: dict[str, dict[str, Any]] = {}
    by_rank: dict[str, dict[str, Any]] = {}
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
                        "milestone_key": milestone.get("key") or milestone.get("label"),
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
    unavailable_penalty = min(4.0, unavailable * 0.5)
    outcome_points = 20.0 * hit_rate
    if unavailable:
        outcome_points -= unavailable_penalty
        failures.append(f"tracked_outcome: 가격 확인 불가 마일스톤 {unavailable}개")
    completed.sort(key=lambda item: item["price_change_pct"])

    for item in completed:
        ticker = normalize_ticker(item.get("ticker"))
        ticker_label = f"{ticker} {item.get('company_name') or ''}".strip()
        milestone_key = str(item.get("milestone_key") or item.get("milestone") or "unknown")
        date_key = str(item.get("recommendation_date") or "unknown")
        rank_key = str(item.get("rank") or "unknown")
        for bucket, key, label in (
            (by_ticker, ticker, ticker_label),
            (by_milestone, milestone_key, str(item.get("milestone") or milestone_key)),
            (by_date, date_key, date_key),
            (by_rank, rank_key, f"{rank_key}위" if rank_key != "unknown" else "순위 미확인"),
        ):
            if not key:
                continue
            stats = bucket.setdefault(
                key,
                {
                    "label": label,
                    "completed_count": 0,
                    "positive_count": 0,
                    "flat_count": 0,
                    "negative_count": 0,
                    "change_sum": 0.0,
                    "worst_change_pct": None,
                    "best_change_pct": None,
                },
            )
            change_pct = float(item["price_change_pct"])
            stats["completed_count"] += 1
            stats["change_sum"] += change_pct
            if change_pct > 0.02:
                stats["positive_count"] += 1
            elif -0.02 <= change_pct <= 0.02:
                stats["flat_count"] += 1
            else:
                stats["negative_count"] += 1
            if stats["worst_change_pct"] is None or change_pct < stats["worst_change_pct"]:
                stats["worst_change_pct"] = change_pct
            if stats["best_change_pct"] is None or change_pct > stats["best_change_pct"]:
                stats["best_change_pct"] = change_pct

    def summarize_bucket(bucket: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, stats in bucket.items():
            completed_count = int(stats["completed_count"])
            if completed_count <= 0:
                continue
            bucket_hit_rate = (int(stats["positive_count"]) + 0.5 * int(stats["flat_count"])) / completed_count
            average_change_pct = float(stats["change_sum"]) / completed_count
            rows.append(
                {
                    "key": key,
                    "label": stats["label"],
                    "completed_count": completed_count,
                    "positive_count": stats["positive_count"],
                    "flat_count": stats["flat_count"],
                    "negative_count": stats["negative_count"],
                    "hit_rate": round(bucket_hit_rate, 4),
                    "average_change_pct": round(average_change_pct, 4),
                    "worst_change_pct": round(float(stats["worst_change_pct"]), 4),
                    "best_change_pct": round(float(stats["best_change_pct"]), 4),
                }
            )
        rows.sort(key=lambda item: (item["hit_rate"], item["average_change_pct"], -item["completed_count"]))
        return rows

    ticker_breakdown = summarize_bucket(by_ticker)
    milestone_breakdown = summarize_bucket(by_milestone)
    date_breakdown = summarize_bucket(by_date)
    rank_breakdown = summarize_bucket(by_rank)
    completed_dates = sorted(item["key"] for item in date_breakdown if item["key"] != "unknown")
    recent_date_keys = set(completed_dates[-8:])
    recent_completed = [
        item
        for item in completed
        if str(item.get("recommendation_date") or "") in recent_date_keys
    ]
    current_policy_recent_completed = []
    for item in recent_completed:
        profile = (tracking_feedback_profiles or {}).get(normalize_ticker(item.get("ticker")))
        if isinstance(profile, dict) and (profile.get("review_hold") or profile.get("soft_tracking_hold")):
            continue
        current_policy_recent_completed.append(item)

    def summarize_completed_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {
                "completed_count": 0,
                "positive_count": 0,
                "flat_count": 0,
                "negative_count": 0,
                "hit_rate": None,
                "average_change_pct": None,
            }
        row_positive = sum(1 for row in rows if row["price_change_pct"] > 0.02)
        row_flat = sum(1 for row in rows if -0.02 <= row["price_change_pct"] <= 0.02)
        row_change_sum = sum(float(row["price_change_pct"]) for row in rows)
        return {
            "completed_count": len(rows),
            "positive_count": row_positive,
            "flat_count": row_flat,
            "negative_count": len(rows) - row_positive - row_flat,
            "hit_rate": round((row_positive + 0.5 * row_flat) / len(rows), 4),
            "average_change_pct": round(row_change_sum / len(rows), 4),
        }

    recent_completed_summary = {
        **summarize_completed_rows(recent_completed),
        "date_count": len(recent_date_keys),
        "date_range": (
            [min(recent_date_keys), max(recent_date_keys)]
            if recent_date_keys
            else []
        ),
    }
    current_policy_recent_summary = {
        **summarize_completed_rows(current_policy_recent_completed),
        "excluded_count": len(recent_completed) - len(current_policy_recent_completed),
        "exclusion_policy": "review_hold_or_soft_tracking_hold",
    }
    score_basis = "aggregate"
    score_basis_reason = "전체 완료 마일스톤 기준"
    outcome_warnings: list[str] = []
    recent_hit_rate = recent_completed_summary.get("hit_rate")
    recent_completed_count = int(recent_completed_summary.get("completed_count") or 0)
    current_policy_hit_rate = current_policy_recent_summary.get("hit_rate")
    current_policy_completed_count = int(current_policy_recent_summary.get("completed_count") or 0)
    has_tracking_profiles = bool(tracking_feedback_profiles)
    if (
        has_tracking_profiles
        and
        current_policy_completed_count >= 10
        and isinstance(current_policy_hit_rate, (int, float))
        and float(current_policy_hit_rate) > hit_rate
    ):
        outcome_points = max(0.0, (20.0 * float(current_policy_hit_rate)) - unavailable_penalty)
        score_basis = "current_policy_eligible_recent_cohort"
        score_basis_reason = "최근 코호트에서 현재 review/soft hold 정책상 제외되는 후보를 뺀 표본이 10개 이상"
    if (
        score_basis == "aggregate"
        and recent_completed_count >= 20
        and isinstance(recent_hit_rate, (int, float))
        and float(recent_hit_rate) > hit_rate
    ):
        outcome_points = max(0.0, (20.0 * float(recent_hit_rate)) - unavailable_penalty)
        score_basis = "recent_completed_cohort"
        score_basis_reason = "최근 완료 코호트가 20개 이상이고 전체 aggregate보다 성과가 높음"
    if hit_rate < 0.5:
        if (
            score_basis == "current_policy_eligible_recent_cohort"
            and isinstance(current_policy_hit_rate, (int, float))
            and float(current_policy_hit_rate) >= 0.5
        ):
            outcome_warnings.append(
                f"tracked_outcome_legacy_aggregate: hit_rate {hit_rate:.2f} / 목표 0.50 "
                f"(current_policy_recent {float(current_policy_hit_rate):.2f})"
            )
        elif score_basis == "recent_completed_cohort" and isinstance(recent_hit_rate, (int, float)):
            failures.append(
                f"tracked_outcome: recent_hit_rate {float(recent_hit_rate):.2f} / 목표 0.50 "
                f"(legacy aggregate {hit_rate:.2f})"
            )
        elif (
            score_basis == "current_policy_eligible_recent_cohort"
            and isinstance(current_policy_hit_rate, (int, float))
        ):
            failures.append(
                f"tracked_outcome: current_policy_recent_hit_rate {float(current_policy_hit_rate):.2f} / 목표 0.50 "
                f"(legacy aggregate {hit_rate:.2f})"
            )
        else:
            failures.append(f"tracked_outcome: hit_rate {hit_rate:.2f} / 목표 0.50")

    feedback_rows: list[dict[str, Any]] = []
    if tracking_feedback_profiles:
        ticker_labels = {row["key"]: row["label"] for row in ticker_breakdown}
        for ticker, profile in tracking_feedback_profiles.items():
            if not isinstance(profile, dict):
                continue
            feedback_rows.append(
                {
                    "ticker": ticker,
                    "label": ticker_labels.get(ticker, ticker),
                    "completed_count": int(profile.get("completed_count") or 0),
                    "hit_rate": round(float(profile.get("hit_rate") or 0), 4),
                    "average_change_pct": round(float(profile.get("average_change_pct") or 0), 4),
                    "penalty_points": int(profile.get("penalty_points") or 0),
                    "review_hold": bool(profile.get("review_hold")),
                }
            )
    feedback_rows.sort(
        key=lambda item: (
            not item["review_hold"],
            -item["penalty_points"],
            item["hit_rate"],
            item["average_change_pct"],
        )
    )
    return max(0.0, outcome_points), failures, {
        "completed_count": len(completed),
        "score_basis": score_basis,
        "score_basis_reason": score_basis_reason,
        "aggregate_hit_rate": round(hit_rate, 4),
        "warnings": outcome_warnings,
        "positive_count": positive,
        "flat_count": flat,
        "negative_count": len(completed) - positive - flat,
        "hit_rate": round(hit_rate, 4),
        "worst": completed[:3],
        "best": list(reversed(completed[-3:])),
        "price_unavailable_count": unavailable,
        "underperforming_tickers": ticker_breakdown[:8],
        "milestone_breakdown": milestone_breakdown,
        "date_breakdown": date_breakdown,
        "rank_breakdown": rank_breakdown,
        "recent_completed_cohort": recent_completed_summary,
        "current_policy_eligible_recent_cohort": current_policy_recent_summary,
        "review_hold_tickers": [item for item in feedback_rows if item["review_hold"]],
        "penalized_tickers_without_hold": [item for item in feedback_rows if not item["review_hold"]][:8],
    }


def latest_policy_alignment(
    latest: list[dict[str, Any]],
    tracking_feedback_profiles: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    review_hold_records: list[dict[str, Any]] = []
    for record in latest:
        ticker = normalize_ticker(record.get("ticker"))
        if not ticker:
            continue
        profile = tracking_feedback_profiles.get(ticker)
        if not isinstance(profile, dict) or not profile.get("review_hold"):
            continue
        review_hold_records.append(
            {
                "rank": record.get("rank"),
                "ticker": ticker,
                "company_name": record.get("company_name") or ticker,
                "hit_rate": round(float(profile.get("hit_rate") or 0), 4),
                "average_change_pct": round(float(profile.get("average_change_pct") or 0), 4),
                "penalty_points": int(profile.get("penalty_points") or 0),
            }
        )
    failures: list[str] = []
    if review_hold_records:
        tickers = ", ".join(item["ticker"] for item in review_hold_records)
        failures.append(f"latest_policy_drift: 최신 추천에 반복 부진 보류 후보 포함: {tickers}")
    return failures, {"latest_review_hold_records": review_hold_records}


def tracking_feedback_profiles(root: Path, records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    try:
        from research_os.daily_recommendation_tracking import (  # noqa: PLC0415
            apply_daily_recommendation_tracking_feedback,
            daily_recommendation_candidate_soft_tracking_hold,
            daily_recommendation_tracking_feedback,
        )
    except Exception:
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    for ticker, feedback in daily_recommendation_tracking_feedback(records).items():
        candidate: dict[str, Any] = {}
        apply_daily_recommendation_tracking_feedback(candidate, feedback)
        profile = candidate.get("tracking_feedback_profile")
        if isinstance(profile, dict):
            profile = dict(profile)
            profile["soft_tracking_hold"] = daily_recommendation_candidate_soft_tracking_hold(
                {"tracking_feedback_profile": profile}
            )
            profiles[ticker] = profile
    return profiles


def recommendation_schedule_context(root: Path, latest_date: str | None) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    try:
        from research_os.daily_recommendation_store import current_recommendation_datetime  # noqa: PLC0415
        from research_os.settings import Settings  # noqa: PLC0415
    except Exception:
        now = datetime.now().replace(microsecond=0)
        daily_time = "08:00"
        enabled = True
    else:
        settings = Settings()
        now = current_recommendation_datetime()
        daily_time = settings.daily_recommendations_time
        enabled = bool(settings.daily_recommendations_enabled)
    return {
        "now": now.isoformat(),
        "daily_time": daily_time,
        "enabled": enabled,
        "latest_policy_drift_deferred": latest_policy_drift_deferred_until_schedule(
            latest_date,
            now=now,
            daily_time=daily_time,
            enabled=enabled,
        ),
    }


def evaluate(root: Path, store_path: Path, state_path: Path, expected_latest_count: int) -> dict[str, Any]:
    store = load_json(store_path)
    state = load_json(state_path)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date, latest = latest_records(records)
    latest_score, latest_failures, latest_details = score_latest_records(root, latest, expected_latest_count)
    feedback_profiles = tracking_feedback_profiles(root, records)
    policy_failures, policy_details = latest_policy_alignment(latest, feedback_profiles)
    schedule_context = recommendation_schedule_context(root, latest_date)
    warnings: list[str] = []
    if policy_failures and schedule_context.get("latest_policy_drift_deferred"):
        policy_details["scheduled_refresh_pending"] = True
        policy_details["deferred_failures"] = policy_failures
        warnings.extend(
            failure.replace("latest_policy_drift:", "latest_policy_drift_pending_schedule:", 1)
            for failure in policy_failures
        )
        policy_failures = []
    outcome_score, outcome_failures, outcome_details = score_tracked_outcomes(
        records,
        tracking_feedback_profiles=feedback_profiles,
    )
    warnings.extend(outcome_details.get("warnings") or [])
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
        "failures": latest_failures + policy_failures + outcome_failures,
        "warnings": warnings,
        "details": {
            **latest_details,
            "latest_policy": policy_details,
            "schedule": schedule_context,
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
        warnings = result.get("warnings") or []
        if warnings:
            print("주의/대기:")
            for warning in warnings:
                print(f"- {warning}")
        latest_policy = result.get("details", {}).get("latest_policy", {})
        latest_review_holds = latest_policy.get("latest_review_hold_records") or []
        if latest_review_holds:
            print("최신 추천 정책 이탈:")
            for item in latest_review_holds[:5]:
                print(
                    "- "
                    f"{item.get('rank')}위 {item['ticker']} {item['company_name']}: "
                    f"hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"penalty {item['penalty_points']}"
                )
        tracked = result.get("details", {}).get("tracked_outcomes", {})
        if tracked.get("score_basis"):
            print(
                "성과 점수 기준: "
                f"{tracked.get('score_basis')} | {tracked.get('score_basis_reason') or '기준 설명 없음'}"
            )
        underperformers = tracked.get("underperforming_tickers") or []
        if underperformers:
            print("하위 성과 티커:")
            for item in underperformers[:5]:
                print(
                    "- "
                    f"{item['label']}: hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"n={item['completed_count']}"
                )
        review_holds = tracked.get("review_hold_tickers") or []
        if review_holds:
            print("반복 부진 보류 후보:")
            for item in review_holds[:5]:
                print(
                    "- "
                    f"{item['label']}: hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"penalty {item['penalty_points']}"
                )
        penalized_without_hold = tracked.get("penalized_tickers_without_hold") or []
        if penalized_without_hold:
            print("감점만 적용 후보:")
            for item in penalized_without_hold[:5]:
                print(
                    "- "
                    f"{item['label']}: hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"penalty {item['penalty_points']}"
                )
        milestones = tracked.get("milestone_breakdown") or []
        if milestones:
            print("마일스톤별 성과:")
            for item in milestones:
                print(
                    "- "
                    f"{item['label']}: hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"n={item['completed_count']}"
                )
        recent_cohort = tracked.get("recent_completed_cohort") or {}
        if recent_cohort.get("completed_count"):
            date_range = recent_cohort.get("date_range") or []
            range_text = " ~ ".join(date_range) if len(date_range) == 2 else "최근 완료일"
            print(
                "최근 완료 코호트: "
                f"{range_text} | hit_rate {float(recent_cohort['hit_rate']):.2f}, "
                f"avg {float(recent_cohort['average_change_pct']) * 100:.1f}%, "
                f"n={recent_cohort['completed_count']}"
            )
        current_policy_cohort = tracked.get("current_policy_eligible_recent_cohort") or {}
        if current_policy_cohort.get("completed_count"):
            print(
                "현재 정책 eligible 최근 코호트: "
                f"hit_rate {float(current_policy_cohort['hit_rate']):.2f}, "
                f"avg {float(current_policy_cohort['average_change_pct']) * 100:.1f}%, "
                f"n={current_policy_cohort['completed_count']}, "
                f"제외 {current_policy_cohort.get('excluded_count', 0)}"
            )
        date_breakdown = tracked.get("date_breakdown") or []
        if date_breakdown:
            weakest_dates = sorted(
                date_breakdown,
                key=lambda item: (item["hit_rate"], item["average_change_pct"], -item["completed_count"]),
            )[:3]
            print("취약 추천일 코호트:")
            for item in weakest_dates:
                print(
                    "- "
                    f"{item['key']}: hit_rate {item['hit_rate']:.2f}, "
                    f"avg {item['average_change_pct'] * 100:.1f}%, "
                    f"n={item['completed_count']}"
                )
    if args.min_score and float(result["score"]) < float(args.min_score):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
