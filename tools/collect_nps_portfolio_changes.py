"""Collect and save an NPS portfolio-change snapshot from ODCLOUD cache/API rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.nps_portfolio_changes import (  # noqa: E402
    build_nps_portfolio_change_snapshot,
    save_nps_portfolio_change_snapshot,
)
from research_os.settings import Settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="국민연금 포트폴리오 변동 스냅샷을 생성해 시스템에 저장합니다.")
    parser.add_argument("--as-of", required=True, help="기준일 YYYY-MM-DD")
    parser.add_argument("--portfolio-name", default="__all__", help="저장 포트폴리오 이름 또는 __all__")
    parser.add_argument("--no-save", action="store_true", help="파일 저장 없이 분석 결과만 출력")
    parser.add_argument("--json", action="store_true", help="전체 JSON 출력")
    args = parser.parse_args()

    settings = Settings.from_env()
    snapshot = build_nps_portfolio_change_snapshot(
        settings,
        as_of=args.as_of,
        portfolio_name=args.portfolio_name,
    )
    saved = None if args.no_save else save_nps_portfolio_change_snapshot(snapshot, settings)

    if args.json:
        print(json.dumps(saved or snapshot, ensure_ascii=False, indent=2))
    else:
        print(snapshot["summary"])
        print(f"상태: {snapshot['status']}")
        print(f"캐시 갱신: {snapshot.get('cache_updated_at') or '없음'}")
        print(f"최신 대량보유 기준일: {snapshot.get('latest_event_date') or '없음'}")
        print(f"포트폴리오 매칭: {len(snapshot.get('portfolio_matches') or [])}건")
        for warning in snapshot.get("warnings") or []:
            print(f"경고: {warning}")
        for item in (snapshot.get("portfolio_matches") or [])[:8]:
            print(
                f"- {item.get('ticker')} {item.get('holding_name')}: "
                f"{item.get('issuer')} / {item.get('base_date')} / {item.get('holding_ratio')}%"
            )
        if saved:
            print(f"저장: {saved['path']}")
    return 0 if snapshot.get("status") in {"success", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
