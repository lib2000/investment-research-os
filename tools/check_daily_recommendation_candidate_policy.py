"""Validate generated daily recommendation candidate policy without saving.

The store eval measures historical outcomes. This guard checks the current
generation policy so severe repeat-underperformers do not re-enter the top
recommendation slots when enough alternatives are available.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def candidate_market(candidate: dict[str, Any]) -> str:
    market = str(candidate.get("market") or "").strip().upper()
    if market in {"KR", "US"}:
        return market
    currency = str(candidate.get("currency") or "").strip().upper()
    ticker = normalize_ticker(candidate.get("ticker"))
    if currency == "KRW" or (ticker.isdigit() and len(ticker) == 6):
        return "KR"
    return "US"


def candidate_soft_tracking_hold(candidate: dict[str, Any]) -> bool:
    try:
        from research_os.daily_recommendation_tracking import daily_recommendation_candidate_soft_tracking_hold  # noqa: PLC0415
    except Exception:
        daily_recommendation_candidate_soft_tracking_hold = None
    if daily_recommendation_candidate_soft_tracking_hold:
        return daily_recommendation_candidate_soft_tracking_hold(candidate)
    profile = candidate.get("tracking_feedback_profile")
    if not isinstance(profile, dict) or profile.get("review_hold"):
        return False
    return (
        int(profile.get("completed_count") or 0) >= 5
        and int(profile.get("penalty_points") or 0) >= 6
        and float(profile.get("hit_rate") or 0) < 0.3
        and float(profile.get("average_change_pct") or 0) < 0
    )


def validate_candidate_policy(
    payload: dict[str, Any],
    *,
    top_limit: int,
    expected_held_tickers: list[str] | None = None,
    require_hold_warning: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    warnings = [str(item).strip() for item in payload.get("warnings", []) if str(item or "").strip()]
    top_candidates: list[dict[str, Any]] = []
    for market in ("KR", "US"):
        market_candidates = [candidate for candidate in candidates if candidate_market(candidate) == market]
        top_candidates.extend(market_candidates[: max(1, top_limit)])
    top_hold_tickers = [
        normalize_ticker(candidate.get("ticker"))
        for candidate in top_candidates
        if isinstance(candidate.get("tracking_feedback_profile"), dict)
        and candidate["tracking_feedback_profile"].get("review_hold")
    ]
    warning_text = "\n".join(warnings)
    expected = [normalize_ticker(ticker) for ticker in expected_held_tickers or [] if normalize_ticker(ticker)]
    missing_expected_warnings = [
        ticker
        for ticker in expected
        if ticker not in warning_text.upper()
    ]
    failures: list[str] = []
    if top_hold_tickers:
        failures.append(f"top{top_limit}_review_hold: {', '.join(top_hold_tickers)}")
    if require_hold_warning and "반복 부진 top3 보류:" not in warning_text:
        failures.append("hold_warning: 반복 부진 top3 보류 경고가 없습니다.")
    if missing_expected_warnings:
        failures.append(f"expected_hold_warning: {', '.join(missing_expected_warnings)}")
    details = {
        "top_limit": top_limit,
        "top_candidates": [
            {
                "rank": candidate.get("rank"),
                "market": candidate_market(candidate),
                "ticker": candidate.get("ticker"),
                "company_name": candidate.get("company_name"),
                "score": candidate.get("score"),
                "review_hold": bool(
                    isinstance(candidate.get("tracking_feedback_profile"), dict)
                    and candidate["tracking_feedback_profile"].get("review_hold")
                ),
                "soft_tracking_hold": candidate_soft_tracking_hold(candidate),
                "tracking_hit_rate": (
                    candidate.get("tracking_feedback_profile", {}).get("hit_rate")
                    if isinstance(candidate.get("tracking_feedback_profile"), dict)
                    else None
                ),
                "tracking_average_change_pct": (
                    candidate.get("tracking_feedback_profile", {}).get("average_change_pct")
                    if isinstance(candidate.get("tracking_feedback_profile"), dict)
                    else None
                ),
                "tracking_penalty_points": (
                    candidate.get("tracking_feedback_profile", {}).get("penalty_points")
                    if isinstance(candidate.get("tracking_feedback_profile"), dict)
                    else None
                ),
            }
            for candidate in top_candidates
        ],
        "warnings": warnings[:10],
    }
    return failures, details


def existing_rag_document_counts_by_ticker(root: Path, tickers: list[str]) -> dict[str, int]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.rag_memory import _document_quality, connect_rag_db, initialize_rag_db  # noqa: PLC0415

    normalized_tickers = sorted({ticker.strip().upper() for ticker in tickers if ticker.strip()})
    if not normalized_tickers:
        return {}
    vault_dir = root / "research_vault"
    initialize_rag_db(vault_dir)
    placeholders = ",".join("?" for _ in normalized_tickers)
    with connect_rag_db(vault_dir) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM research_memory_documents
            WHERE ticker IN ({placeholders})
            """,
            normalized_tickers,
        ).fetchall()
    counts = {ticker: 0 for ticker in normalized_tickers}
    for row in rows:
        payload = dict(row)
        if not _document_quality(payload)["is_injectable"]:
            continue
        ticker = normalize_ticker(payload.get("ticker"))
        counts[ticker] = counts.get(ticker, 0) + 1
    return counts


def saved_portfolio_price_lookup(root: Path) -> dict[str, tuple[float, str]]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.portfolio_store import read_portfolio_store  # noqa: PLC0415
    from research_os.settings import Settings  # noqa: PLC0415

    prices: dict[str, tuple[float, str]] = {}
    store = read_portfolio_store(Settings.from_env())
    for portfolio in (store.get("portfolios") or {}).values():
        if not isinstance(portfolio, dict):
            continue
        for holding in portfolio.get("holdings") or []:
            if not isinstance(holding, dict):
                continue
            ticker = normalize_ticker(holding.get("ticker"))
            if not ticker:
                continue
            try:
                price = float(holding.get("current_price") or 0)
            except (TypeError, ValueError):
                price = 0
            if price > 0:
                prices.setdefault(ticker, (price, "saved_portfolio"))
    return prices


def build_candidate_payload(root: Path, *, candidate_limit: int, skip_rag_backfill: bool = True) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    import research_os_main  # noqa: PLC0415
    from research_os.settings import Settings  # noqa: PLC0415

    if skip_rag_backfill:
        research_os_main.count_research_memory_documents_by_ticker = (
            lambda _vault_dir, tickers, include_low_quality=False: existing_rag_document_counts_by_ticker(root, tickers)
        )
        original_target_consensus_scan = research_os_main.build_target_consensus_scan

        def offline_target_consensus_scan(settings: Any, **kwargs: Any) -> dict[str, Any]:
            kwargs["refresh_missing_prices"] = False
            return original_target_consensus_scan(settings, **kwargs)

        research_os_main.build_target_consensus_scan = offline_target_consensus_scan
        saved_prices = saved_portfolio_price_lookup(root)
        research_os_main.latest_provider_price = (
            lambda ticker, _settings, force_refresh=False: saved_prices.get(normalize_ticker(ticker), (None, None))
        )
    return research_os_main.build_daily_recommendation_candidates(Settings.from_env(), limit=candidate_limit)


def latest_stored_top_records(root: Path, *, top_limit: int) -> list[dict[str, Any]]:
    store_path = root / "research_vault" / "_system" / "daily_recommendations.json"
    if not store_path.exists():
        return []
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    latest_date = str(payload.get("latest_recommendation_date") or "").strip()
    records = [item for item in payload.get("records", []) if isinstance(item, dict)]
    if latest_date:
        records = [item for item in records if str(item.get("recommendation_date") or "") == latest_date]
    result: list[dict[str, Any]] = []
    for market in ("KR", "US"):
        market_records = [
            item for item in records
            if normalize_ticker(item.get("market")) == market and int(item.get("rank") or 0) <= top_limit
        ]
        result.extend(sorted(market_records, key=lambda item: int(item.get("rank") or 0))[:top_limit])
    return [
        {
            "market": normalize_ticker(item.get("market")),
            "rank": item.get("rank"),
            "ticker": item.get("ticker"),
            "company_name": item.get("company_name"),
            "score": item.get("score"),
        }
        for item in result
    ]


def stored_preview_mismatches(stored: list[dict[str, Any]], preview: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    stored_by_slot = {
        (normalize_ticker(item.get("market")), int(item.get("rank") or 0)): item
        for item in stored
    }
    preview_by_slot = {
        (normalize_ticker(item.get("market")), int(item.get("rank") or 0)): item
        for item in preview
    }
    for slot in sorted(set(stored_by_slot) | set(preview_by_slot)):
        stored_item = stored_by_slot.get(slot) or {}
        preview_item = preview_by_slot.get(slot) or {}
        stored_ticker = normalize_ticker(stored_item.get("ticker"))
        preview_ticker = normalize_ticker(preview_item.get("ticker"))
        if stored_ticker != preview_ticker:
            mismatches.append(
                {
                    "market": slot[0],
                    "rank": slot[1],
                    "stored_ticker": stored_ticker,
                    "stored_score": stored_item.get("score"),
                    "preview_ticker": preview_ticker,
                    "preview_score": preview_item.get("score"),
                }
            )
    return mismatches


def candidate_policy_result(
    root: Path,
    payload: dict[str, Any],
    *,
    top_limit: int,
    expected_held_tickers: list[str] | None = None,
    require_hold_warning: bool = False,
) -> dict[str, Any]:
    failures, details = validate_candidate_policy(
        payload,
        top_limit=top_limit,
        expected_held_tickers=expected_held_tickers,
        require_hold_warning=require_hold_warning,
    )
    stored_top_records = latest_stored_top_records(root, top_limit=top_limit)
    preview_mismatches = stored_preview_mismatches(stored_top_records, details["top_candidates"])
    return {
        "status": "failure" if failures else "success",
        "scope_note": "runtime_candidate_preview_only_no_store_write",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
        "stored_top_records": stored_top_records,
        "stored_preview_mismatches": preview_mismatches,
        **details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="오늘 추천 후보 생성 정책 가드")
    parser.add_argument("--top-limit", type=int, default=3, help="review_hold 후보가 들어오면 실패할 상위 N개")
    parser.add_argument("--candidate-limit", type=int, default=10, help="생성할 후보 수")
    parser.add_argument("--expected-held-ticker", action="append", default=[], help="보류 경고에 포함되어야 하는 티커")
    parser.add_argument("--require-hold-warning", action="store_true", help="반복 부진 보류 경고가 없으면 실패")
    parser.add_argument("--allow-rag-backfill", action="store_true", help="후보 재계산 중 RAG 전체 백필을 허용")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과 출력")
    parser.add_argument("--output-json", type=Path, default=None, help="점검 결과 JSON을 파일로 저장")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    candidate_limit = max(args.top_limit, args.candidate_limit, 3)
    payload = build_candidate_payload(root, candidate_limit=candidate_limit, skip_rag_backfill=not args.allow_rag_backfill)
    result = candidate_policy_result(
        root,
        payload,
        top_limit=max(1, args.top_limit),
        expected_held_tickers=args.expected_held_ticker,
        require_hold_warning=args.require_hold_warning,
    )
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("추천 후보 정책 가드:", "실패" if result["failures"] else "정상")
        print("범위: 저장된 최신 추천을 변경하지 않고 현재 런타임 후보 생성 정책만 재계산합니다.")
        if result["stored_preview_mismatches"]:
            mismatch_label = ", ".join(
                f"{item['market']} {item['rank']}위 저장 {item['stored_ticker'] or '-'}"
                f"({item.get('stored_score') or '-'}) / 재계산 {item['preview_ticker'] or '-'}"
                f"({item.get('preview_score') or '-'})"
                for item in result["stored_preview_mismatches"][:6]
            )
            print(f"저장 추천/재계산 차이: {mismatch_label}")
        else:
            print("저장 추천/재계산 차이: 없음")
        for candidate in result["top_candidates"]:
            marker = " | 보류대상" if candidate["review_hold"] else " | 약세추적" if candidate["soft_tracking_hold"] else ""
            tracking_note = ""
            if candidate.get("tracking_penalty_points") is not None:
                tracking_note = (
                    f" | 추적 hit {float(candidate.get('tracking_hit_rate') or 0) * 100:.1f}%"
                    f" / 감점 {candidate.get('tracking_penalty_points')}"
                )
            print(
                f"{candidate.get('market')} {candidate.get('rank')}위 {candidate.get('ticker')} {candidate.get('company_name')} "
                f"| 점수 {candidate.get('score')}{tracking_note}{marker}"
            )
        for warning in result["warnings"][:3]:
            print(f"경고: {warning}")
        if result["failures"]:
            for failure in result["failures"]:
                print(f"실패: {failure}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
