"""Validate generated daily recommendation candidate policy without saving.

The store eval measures historical outcomes. This guard checks the current
generation policy so severe repeat-underperformers do not re-enter the top
recommendation slots when enough alternatives are available.
"""

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


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def validate_candidate_policy(
    payload: dict[str, Any],
    *,
    top_limit: int,
    expected_held_tickers: list[str] | None = None,
    require_hold_warning: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    warnings = [str(item).strip() for item in payload.get("warnings", []) if str(item or "").strip()]
    top_candidates = candidates[: max(1, top_limit)]
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
                "ticker": candidate.get("ticker"),
                "company_name": candidate.get("company_name"),
                "score": candidate.get("score"),
                "review_hold": bool(
                    isinstance(candidate.get("tracking_feedback_profile"), dict)
                    and candidate["tracking_feedback_profile"].get("review_hold")
                ),
            }
            for candidate in top_candidates
        ],
        "warnings": warnings[:10],
    }
    return failures, details


def build_candidate_payload(root: Path, *, candidate_limit: int) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    import research_os_main  # noqa: PLC0415
    from research_os.settings import Settings  # noqa: PLC0415

    return research_os_main.build_daily_recommendation_candidates(Settings(), limit=candidate_limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="오늘 추천 후보 생성 정책 가드")
    parser.add_argument("--top-limit", type=int, default=3, help="review_hold 후보가 들어오면 실패할 상위 N개")
    parser.add_argument("--candidate-limit", type=int, default=10, help="생성할 후보 수")
    parser.add_argument("--expected-held-ticker", action="append", default=[], help="보류 경고에 포함되어야 하는 티커")
    parser.add_argument("--require-hold-warning", action="store_true", help="반복 부진 보류 경고가 없으면 실패")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과 출력")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    candidate_limit = max(args.top_limit, args.candidate_limit, 3)
    payload = build_candidate_payload(root, candidate_limit=candidate_limit)
    failures, details = validate_candidate_policy(
        payload,
        top_limit=max(1, args.top_limit),
        expected_held_tickers=args.expected_held_ticker,
        require_hold_warning=args.require_hold_warning,
    )
    result = {
        "status": "failure" if failures else "success",
        "failures": failures,
        **details,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("추천 후보 정책 가드:", "실패" if failures else "정상")
        for candidate in details["top_candidates"]:
            marker = " | 보류대상" if candidate["review_hold"] else ""
            print(
                f"{candidate.get('rank')}위 {candidate.get('ticker')} {candidate.get('company_name')} "
                f"| 점수 {candidate.get('score')}{marker}"
            )
        for warning in details["warnings"][:3]:
            print(f"경고: {warning}")
        if failures:
            for failure in failures:
                print(f"실패: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
