"""Run the safe pension rebalancing review from a Windows task or terminal.

The runner reads only local portfolio state and writes review artifacts.  It
does not call broker order endpoints or submit trades.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.pension_rebalancing import (  # noqa: E402
    build_pension_rebalancing_status,
    due_pension_rebalancing_periods,
    initialize_pension_rebalancing_config,
    load_pension_rebalancing_config,
    read_pension_rebalancing_state,
    write_pension_rebalancing_run,
)
from research_os.settings import Settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="연금계좌 수동 검토용 리밸런싱 파이프라인")
    parser.add_argument("--initialize", action="store_true", help="목표 비중이 비어 있는 안전한 초안 config를 만듭니다.")
    parser.add_argument("--due-only", action="store_true", help="월간/분기 체크가 도래했을 때만 보고서를 만듭니다.")
    parser.add_argument("--force", action="store_true", help="도래 여부와 관계없이 안전한 검토 보고서를 만듭니다.")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력합니다.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    if args.initialize:
        config = initialize_pension_rebalancing_config(settings)
        result: dict[str, object] = {
            "status": "initialized",
            "portfolio_name": config.get("portfolio_name"),
            "target_status": config.get("status"),
            "execution_mode": "manual_review_only",
            "broker_order_endpoint_called": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    config = load_pension_rebalancing_config(settings)
    state = read_pension_rebalancing_state(settings)
    due_periods = due_pension_rebalancing_periods(config, state)
    if args.due_only and not args.force and not due_periods:
        result = {
            "status": "not_due",
            "due_periods": [],
            "execution_mode": "manual_review_only",
            "broker_order_endpoint_called": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.due_only and not args.force:
        readiness = build_pension_rebalancing_status(settings)
        if readiness.get("status") in {
            "needs_configuration",
            "needs_portfolio_import",
            "needs_holdings_value",
            "draft_needs_confirmation",
        }:
            result = {
                "status": "waiting_for_safe_configuration",
                "review_status": readiness.get("status"),
                "due_periods": due_periods,
                "execution_mode": "manual_review_only",
                "broker_order_endpoint_called": False,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

    result = write_pension_rebalancing_run(settings, due_periods=due_periods)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        snapshot = result["snapshot"]
        print(
            "상태={status}; 포트폴리오={portfolio}; 검토항목={review_count}; 주문호출={order_called}".format(
                status=snapshot.get("status"),
                portfolio=snapshot.get("portfolio_name"),
                review_count=snapshot.get("review_required_count"),
                order_called=result.get("broker_order_endpoint_called"),
            )
        )
        for report_path in result.get("report_paths") or []:
            print(f"보고서: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
