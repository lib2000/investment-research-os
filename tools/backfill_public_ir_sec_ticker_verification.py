"""Backfill server-verified ticker metadata for existing official public IR/SEC entries.

The command is intentionally opt-in: without ``--write`` it only reports what
would be changed.  It never fetches a URL, calls an LLM, sends a message, or
changes a portfolio/review decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_CANDIDATE / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import research_os_main as main  # noqa: E402
from research_os.public_ir_sec import (  # noqa: E402
    backfill_public_ir_sec_ticker_verifications,
)
from research_os.research_memory import resolve_vault_dir  # noqa: E402


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main_entry() -> int:
    parser = argparse.ArgumentParser(
        description="공식 IR/SEC 원문의 서버 티커 인증 메타데이터를 안전하게 보강합니다."
    )
    parser.add_argument("--ticker", action="append", required=True, help="대상 티커. 여러 번 지정할 수 있습니다.")
    parser.add_argument("--write", action="store_true", help="검증 가능한 manifest 항목만 실제로 갱신합니다.")
    parser.add_argument("--json", action="store_true", help="비밀값 없이 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    settings = main.get_settings()
    vault_dir = resolve_vault_dir(settings.research_vault_dir)

    def verification_for(ticker: str) -> dict:
        return main.verify_ticker_symbol_local_cached(ticker, settings).model_dump(mode="json")

    result = backfill_public_ir_sec_ticker_verifications(
        vault_dir,
        ticker_verification_for=verification_for,
        target_tickers={str(value) for value in args.ticker},
        apply=args.write,
    )
    result["local_only"] = True
    result["root"] = str(root)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    action = "갱신" if args.write else "미리보기"
    print(f"공개 IR/SEC 티커 인증 {action}")
    print(f"- 반영: {result['updated_count']}건")
    print(f"- 보류: {result['skipped_count']}건")
    print("- 문서 커버리지/검토 게이트: 변경하지 않음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
