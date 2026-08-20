"""Inspect portfolio analysis module coverage without a running backend."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_CANDIDATE / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_analysis_coverage import (  # noqa: E402
    REQUIRED_PORTFOLIO_ANALYSIS_MODULES,
    merge_portfolio_analysis_entries,
    missing_portfolio_analysis_labels,
    normalize_portfolio_analysis_ticker,
    portfolio_analysis_checklist_status,
    portfolio_analysis_entries_for_ticker,
    portfolio_analysis_module_state,
    portfolio_analysis_next_action,
    portfolio_analysis_review_state,
    portfolio_vault_entries,
)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def normalize_ticker(value: Any) -> str:
    return normalize_portfolio_analysis_ticker(value)


def manifest_entries_for_ticker(entries: list[dict[str, Any]], ticker: str) -> list[dict[str, Any]]:
    return portfolio_analysis_entries_for_ticker(entries, ticker)


def module_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    return portfolio_analysis_module_state(entries)


def review_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    return portfolio_analysis_review_state(entries)


def next_action(missing: list[str]) -> str:
    return portfolio_analysis_next_action(missing)


def vault_entries_for_holdings(vault: Path, holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return portfolio_vault_entries(vault, [holding.get("ticker") for holding in holdings])


def merge_manifest_entries(manifest: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return merge_portfolio_analysis_entries(manifest, extra)


def coverage_for_portfolio(portfolio_name: str, holdings: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for holding in holdings:
        ticker = normalize_ticker(holding.get("ticker"))
        if not ticker or ticker in {"CASH", "UNKNOWN"}:
            continue
        entries = manifest_entries_for_ticker(manifest, ticker)
        documented_state = module_state(entries)
        reviewed_state = review_state(entries)
        checklist_status = portfolio_analysis_checklist_status(entries)
        completed = sum(1 for value in documented_state.values() if value)
        reviewed = sum(1 for value in reviewed_state.values() if value)
        missing = missing_portfolio_analysis_labels(documented_state)
        review_missing = missing_portfolio_analysis_labels(reviewed_state)
        latest_date = max((str(entry.get("date") or "") for entry in entries), default="") or None
        rows.append(
            {
                "ticker": ticker,
                "company_name": holding.get("name") or ticker,
                "portfolio_name": portfolio_name,
                "market_value": holding.get("market_value"),
                "module_state": documented_state,
                "review_state": reviewed_state,
                "checklist_status": checklist_status,
                "completed_count": completed,
                "reviewed_count": reviewed,
                "required_count": len(REQUIRED_PORTFOLIO_ANALYSIS_MODULES),
                "completion_rate": round(completed / len(REQUIRED_PORTFOLIO_ANALYSIS_MODULES), 4),
                "review_completion_rate": round(reviewed / len(REQUIRED_PORTFOLIO_ANALYSIS_MODULES), 4),
                "missing_modules": missing,
                "review_missing_modules": review_missing,
                "latest_report_date": latest_date,
                "next_action": next_action(review_missing),
            }
        )
    rows.sort(key=lambda item: (item["completion_rate"], -(float(item.get("market_value") or 0))))
    average = sum(item["completion_rate"] for item in rows) / len(rows) if rows else 0.0
    review_average = sum(item["review_completion_rate"] for item in rows) / len(rows) if rows else 0.0
    ready_count = sum(1 for item in rows if item["completion_rate"] >= 1.0)
    review_ready_count = sum(1 for item in rows if item["review_completion_rate"] >= 1.0)
    return {
        "portfolio_name": portfolio_name,
        "holding_count": len(rows),
        "ready_count": ready_count,
        "documented_ready_count": ready_count,
        "review_ready_count": review_ready_count,
        "average_completion": round(average, 4),
        "average_review_completion": round(review_average, 4),
        "items": rows,
    }


def unique_holdings_from_portfolios(portfolios: dict[str, Any]) -> list[dict[str, Any]]:
    by_ticker: dict[str, dict[str, Any]] = {}
    for portfolio_name, portfolio in portfolios.items():
        if not isinstance(portfolio, dict):
            continue
        holdings = (
            portfolio.get("holdings")
            if isinstance(portfolio.get("holdings"), list)
            else []
        )
        for holding in holdings:
            ticker = normalize_ticker(holding.get("ticker"))
            if not ticker or ticker in {"CASH", "UNKNOWN"}:
                continue
            current = by_ticker.setdefault(
                ticker,
                {
                    **holding,
                    "ticker": ticker,
                    "name": holding.get("name") or ticker,
                    "market_value": 0,
                    "portfolios": [],
                },
            )
            try:
                current["market_value"] = float(current.get("market_value") or 0) + float(
                    holding.get("market_value") or 0
                )
            except (TypeError, ValueError):
                pass
            if portfolio_name not in current["portfolios"]:
                current["portfolios"].append(portfolio_name)
            if not current.get("name") or current.get("name") == ticker:
                current["name"] = holding.get("name") or ticker
    return list(by_ticker.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="포트폴리오 분석 모듈 커버리지를 백엔드 없이 점검합니다.")
    parser.add_argument("--portfolio", default="이형주")
    parser.add_argument("--all-portfolios", action="store_true")
    parser.add_argument("--min-average-completion", type=float, default=0.0)
    parser.add_argument("--min-ready-count", type=int, default=0)
    parser.add_argument("--min-average-review-completion", type=float, default=0.0)
    parser.add_argument("--min-review-ready-count", type=int, default=0)
    parser.add_argument("--write-backlog", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault = root / "research_vault"
    manifest = load_json(vault / "manifest.json", [])
    if not isinstance(manifest, list):
        manifest = manifest.get("items") if isinstance(manifest, dict) else []
    if not isinstance(manifest, list):
        manifest = []
    store = load_json(vault / "_system" / "user_portfolios.json", {"portfolios": {}})
    portfolios = store.get("portfolios") if isinstance(store.get("portfolios"), dict) else {}
    if args.all_portfolios:
        holdings = unique_holdings_from_portfolios(portfolios)
        manifest = merge_manifest_entries(manifest, vault_entries_for_holdings(vault, holdings))
        result = coverage_for_portfolio("전체 포트폴리오", holdings, manifest)
        result["portfolio_names"] = sorted(portfolios)
    else:
        selected = portfolios.get(args.portfolio)
        if not isinstance(selected, dict):
            raise SystemExit(f"포트폴리오를 찾지 못했습니다: {args.portfolio}")
        holdings = (
            selected.get("holdings")
            if isinstance(selected.get("holdings"), list)
            else []
        )
        manifest = merge_manifest_entries(manifest, vault_entries_for_holdings(vault, holdings))
        result = coverage_for_portfolio(args.portfolio, holdings, manifest)
    result["module"] = "portfolio_analysis_coverage"
    result["generated_at"] = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    result["thresholds"] = {
        "min_average_completion": args.min_average_completion,
        "min_ready_count": args.min_ready_count,
        "min_average_review_completion": args.min_average_review_completion,
        "min_review_ready_count": args.min_review_ready_count,
    }

    if args.write_backlog:
        out = vault / "_system" / "portfolio_analysis_backlog.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["backlog_path"] = str(out.relative_to(root))

    average = float(result["average_completion"])
    review_average = float(result["average_review_completion"])
    ready = int(result["ready_count"])
    review_ready = int(result["review_ready_count"])
    ok = (
        average >= args.min_average_completion
        and ready >= args.min_ready_count
        and review_average >= args.min_average_review_completion
        and review_ready >= args.min_review_ready_count
    )
    result["status"] = "ok" if ok else "warning"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else (1 if args.strict else 0)

    print(f"프로젝트 루트: {root}")
    print(
        f"포트폴리오: {result['portfolio_name']} | 보유 {result['holding_count']}개 "
        f"| 문서 완료 {ready}개 | 문서 커버리지 {average:.1%} "
        f"| 검토 게이트 통과 {review_ready}개 | 검토 충족률 {review_average:.1%}"
    )
    for item in result["items"][: max(0, args.limit)]:
        missing = ", ".join(item["missing_modules"]) if item["missing_modules"] else "문서 누락 없음"
        review_missing = ", ".join(item["review_missing_modules"]) if item["review_missing_modules"] else "검토 게이트 통과"
        checklist = item["checklist_status"]
        checklist_text = (
            f"체크 {checklist['completion_rate']:.0%}"
            if checklist.get("completion_rate") is not None
            else "체크 미작성"
        )
        print(
            f"- {item['company_name']} ({item['ticker']}): 문서 {item['completion_rate']:.0%} "
            f"| 검토 {item['review_completion_rate']:.0%} | {checklist_text} "
            f"| 문서 부족: {missing} | 검토 보강: {review_missing} | 다음: {item['next_action']}"
        )
    if args.write_backlog:
        print(f"보강 큐 저장: {result['backlog_path']}")

    if ok:
        print("포트폴리오 분석 커버리지 점검 정상")
        return 0
    print("포트폴리오 분석 커버리지 보강 필요")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
