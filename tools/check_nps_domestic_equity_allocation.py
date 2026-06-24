"""Check saved portfolio domestic-equity weight against the NPS 14% policy target."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.nps_allocation_monitor import (  # noqa: E402
    DEFAULT_NPS_DOMESTIC_EQUITY_TARGET,
    DEFAULT_NPS_DOMESTIC_EQUITY_TOLERANCE,
    build_nps_domestic_equity_monitor_from_saved_portfolios,
    select_saved_portfolios_for_nps_allocation,
)


DEFAULT_STORE = Path("research_vault/_system/user_portfolios.json")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_portfolios(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"포트폴리오 저장 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"포트폴리오 저장 파일 JSON 파싱 실패: {exc}") from exc
    portfolios = payload.get("portfolios") if isinstance(payload, dict) else None
    if not isinstance(portfolios, dict):
        raise SystemExit("포트폴리오 저장 파일에 portfolios 객체가 없습니다.")
    return portfolios


def main() -> int:
    parser = argparse.ArgumentParser(description="국민연금 국내주식 14% 기준 대비 저장 포트폴리오 비중을 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="user_portfolios.json 경로")
    parser.add_argument("--portfolio-name", default="__all__", help="포트폴리오 이름, 키 또는 __all__")
    parser.add_argument("--target-weight", type=float, default=DEFAULT_NPS_DOMESTIC_EQUITY_TARGET, help="목표 국내주식 비중")
    parser.add_argument("--warn-tolerance", type=float, default=DEFAULT_NPS_DOMESTIC_EQUITY_TOLERANCE, help="허용 오차")
    parser.add_argument("--fail-on-breach", action="store_true", help="목표 허용 범위를 벗어나면 종료 코드 2 반환")
    parser.add_argument("--json", action="store_true", help="전체 JSON 출력")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store

    portfolios = load_portfolios(store)
    selected_name, selected = select_saved_portfolios_for_nps_allocation(portfolios, args.portfolio_name)
    if not selected:
        raise SystemExit(f"포트폴리오를 찾지 못했습니다: {args.portfolio_name}")
    monitor = build_nps_domestic_equity_monitor_from_saved_portfolios(
        selected,
        portfolio_name=selected_name,
        target_weight=args.target_weight,
        warn_tolerance=args.warn_tolerance,
        checked_at=datetime.now().isoformat(timespec="seconds"),
    )

    if args.json:
        print(json.dumps(monitor, ensure_ascii=False, indent=2))
    else:
        print(monitor["summary"])
        print(f"상태: {monitor['status']} / 심각도: {monitor['severity']}")
        print(
            "금액: 국내주식 "
            f"{monitor['domestic_equity_value']:,.0f} / 전체 {monitor['total_portfolio_value']:,.0f}"
        )
        print(f"차이: {monitor['gap_pct_points']:+.2f}%p / {monitor['gap_value']:+,.0f}")
        print(f"조치: {monitor['recommended_action']}")
        print("상위 국내주식:")
        for item in monitor["top_domestic_equity_holdings"][:8]:
            print(f"- {item['ticker']} {item.get('holding_name') or ''}: {item['market_value']:,.0f} ({item['reason']})")
        print("상위 제외 항목:")
        for item in monitor["top_excluded_holdings"][:8]:
            print(f"- {item['ticker']} {item.get('holding_name') or ''}: {item['market_value']:,.0f} ({item['reason']})")

    if args.fail_on_breach and monitor["status"] in {"below_target", "above_target", "needs_data"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
