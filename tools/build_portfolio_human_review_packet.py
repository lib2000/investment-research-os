"""Create a local-only evidence inventory for one portfolio holding.

The tool is intentionally opt-in (`--write`) and never calls a model, broker,
or external API.  It records only data already persisted in the local vault.
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

from research_os.portfolio_review_packet import (  # noqa: E402
    build_portfolio_human_review_packet,
    write_portfolio_human_review_packet,
)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description="저장된 근거만으로 사람 검토 준비 패킷을 만듭니다.")
    parser.add_argument("--ticker", required=True, help="대상 티커")
    parser.add_argument("--vault-dir", type=Path, default=None, help="research_vault 경로")
    parser.add_argument("--portfolio-store", type=Path, default=None, help="user_portfolios.json 경로")
    parser.add_argument("--dart-cache", type=Path, default=None, help="dart_filing_watch_cache.json 경로")
    parser.add_argument("--write", action="store_true", help="로컬 vault에 JSON/Markdown 패킷을 저장합니다.")
    parser.add_argument("--json", action="store_true", help="비밀값 없이 패킷 내용을 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault = args.vault_dir or root / "research_vault"
    portfolio_store_path = args.portfolio_store or vault / "_system" / "user_portfolios.json"
    dart_cache_path = args.dart_cache or vault / "_system" / "dart_filing_watch_cache.json"
    packet = build_portfolio_human_review_packet(
        ticker=args.ticker,
        portfolio_store=load_json(portfolio_store_path, {"portfolios": {}}),
        dart_cache=load_json(dart_cache_path, {}),
        vault_dir=vault,
    )
    result = {
        "status": "review_required",
        "module": "portfolio_human_review_packet",
        "local_only": True,
        "packet": packet,
    }
    if args.write:
        paths = write_portfolio_human_review_packet(packet, vault / str(packet["ticker"]))
        result["paths"] = {key: str(path.relative_to(root)) for key, path in paths.items()}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"사람 검토 준비 패킷: {packet['title']}")
    print(f"- 저장 DART 공시: {len(packet['dart_filings'])}건")
    print(f"- 일일 감시: {'확인됨' if packet['dart_daily_watch']['checked'] else '확인 필요'}")
    print(f"- 수량 확인 필요: {'예' if packet['holding_snapshot']['quantity_confirmation_required'] else '아니오'}")
    print("- 검토 게이트: 변경하지 않음")
    if args.write:
        print(f"- 저장: {result['paths']['markdown']}")
    else:
        print("- 미리보기만 실행했습니다. 저장하려면 --write를 사용하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
