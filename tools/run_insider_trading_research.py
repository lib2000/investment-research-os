"""Run one insider analysis or a bounded family-wide daily batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.insider_trading import (  # noqa: E402
    InsiderAnalysisRequest,
    analyze_insider_trading,
    run_insider_trading_batch,
)
from research_os.settings import Settings  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="SEC Form 4/OpenDART 내부자거래를 동일한 6축 리서치로 정규화합니다."
    )
    parser.add_argument("--ticker", action="append", default=[], help="단일 또는 반복 티커")
    parser.add_argument("--market", default="AUTO", choices=("AUTO", "US", "KR"))
    parser.add_argument("--source-url", default="")
    parser.add_argument("--source-text", default="")
    parser.add_argument("--max-tickers", type=int, default=8)
    parser.add_argument("--max-filings", type=int, default=24)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if load_dotenv:
        load_dotenv(PROJECT_ROOT / "backend" / ".env", override=False)
    settings = Settings.from_env()
    save_result = not args.no_save

    if len(args.ticker) == 1 and (args.source_url or args.source_text or args.no_fetch):
        result = analyze_insider_trading(
            InsiderAnalysisRequest(
                ticker=args.ticker[0],
                market=args.market,
                source_url=args.source_url or None,
                source_text=args.source_text or None,
                fetch_external=not args.no_fetch,
                save_result=save_result,
                max_filings=max(1, min(args.max_filings, 100)),
            ),
            settings,
        )
    else:
        result = run_insider_trading_batch(
            settings,
            tickers=args.ticker or None,
            max_tickers=max(1, min(args.max_tickers, 100)),
            max_filings=max(1, min(args.max_filings, 100)),
            save_result=save_result,
        )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("summary") or result.get("message") or result.get("status"))
        if result.get("last_run"):
            run = result["last_run"]
            print(f"점검 {run.get('selected_count', 0)}/{run.get('candidate_count', 0)}; 결과 {run.get('counts')}")
    return 0 if result.get("status") in {"success", "warning", "no_events"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
