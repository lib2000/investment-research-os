"""Preview or soft-archive byte-identical duplicate DART filing storage pairs."""

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

from research_os.dart_filing_cleanup import (  # noqa: E402
    apply_dart_filing_duplicate_cleanup,
    build_dart_filing_duplicate_cleanup_plan,
    recent_dart_manifest_tickers,
    write_dart_filing_duplicate_cleanup_state,
)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="같은 DART 접수번호의 완전 동일 저장본만 soft archive로 정리합니다. 파일은 삭제하지 않습니다."
    )
    parser.add_argument("--apply", action="store_true", help="dry-run 대신 JSON/매니페스트/RAG 보관 상태를 실제 반영합니다.")
    parser.add_argument("--write-state", action="store_true", help="결과를 research_vault/_system에 저장합니다.")
    parser.add_argument("--ticker", action="append", default=[], help="특정 종목코드만 점검합니다. 여러 번 지정할 수 있습니다.")
    parser.add_argument("--all", action="store_true", help="최근 갱신 범위 대신 전체 DART 저장소를 점검합니다. 오래 걸릴 수 있습니다.")
    parser.add_argument(
        "--recent-tickers-hours",
        type=float,
        default=36.0,
        help="기본 범위: 최근 이 시간 안에 갱신된 active DART manifest 종목만 점검합니다.",
    )
    parser.add_argument(
        "--max-recent-tickers",
        type=int,
        default=12,
        help="기본 최근 범위에서 한 번에 처리할 종목 수 상한입니다. 전체 이력 스캔을 방지합니다.",
    )
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력합니다.")
    args = parser.parse_args()
    if args.all and args.ticker:
        parser.error("--all과 --ticker는 함께 사용할 수 없습니다.")

    root = project_root(Path.cwd())
    vault = root / "research_vault"
    explicit_tickers = {str(value).strip().upper() for value in args.ticker if str(value).strip()}
    if args.all:
        tickers = None
        scope = {"mode": "all", "ticker_count": None}
    elif explicit_tickers:
        tickers = explicit_tickers
        scope = {"mode": "explicit", "ticker_count": len(tickers), "tickers": sorted(tickers)}
    else:
        tickers = recent_dart_manifest_tickers(
            vault,
            hours=args.recent_tickers_hours,
            max_tickers=max(args.max_recent_tickers, 0),
        )
        scope = {
            "mode": "recent_manifest",
            "ticker_count": len(tickers),
            "recent_tickers_hours": args.recent_tickers_hours,
            "max_recent_tickers": max(args.max_recent_tickers, 0),
            "tickers": sorted(tickers),
        }
    plan = build_dart_filing_duplicate_cleanup_plan(vault, tickers=tickers)
    plan["scope"] = scope
    result = apply_dart_filing_duplicate_cleanup(vault, plan) if args.apply else {**plan, "applied": False}
    if args.write_state:
        result["state_path"] = str(write_dart_filing_duplicate_cleanup_state(vault, result).relative_to(root))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        mode = "적용" if args.apply else "dry-run"
        print(
            f"DART 공시 중복 정리 {mode}: 활성 쌍 {result['scanned_active_file_pair_count']}개 | "
            f"그룹 {result['duplicate_group_count']}개 | 후보 {result['duplicate_candidate_count']}개 | "
            f"보관 {result.get('archived_count', 0)}개 | 검토 보류 {result['skipped_group_count']}개"
        )
        for group in result.get("groups", [])[:10]:
            print(
                f"- {group['ticker']} {group['rcept_no']}: "
                f"대표={group['canonical']['file_name']} | 중복={len(group['duplicates'])}"
            )
        if result.get("errors"):
            print(f"오류 {len(result['errors'])}개")
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
