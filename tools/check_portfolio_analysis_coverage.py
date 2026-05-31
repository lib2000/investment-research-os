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
    missing_portfolio_analysis_labels,
    portfolio_analysis_module_state,
    portfolio_analysis_next_action,
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
    return str(value or "").strip().upper()


def manifest_entries_for_ticker(entries: list[dict[str, Any]], ticker: str) -> list[dict[str, Any]]:
    normalized = normalize_ticker(ticker)
    return [entry for entry in entries if normalize_ticker(entry.get("ticker")) == normalized]


def module_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    return portfolio_analysis_module_state(entries)


def next_action(missing: list[str]) -> str:
    return portfolio_analysis_next_action(missing)


def coverage_for_portfolio(portfolio_name: str, holdings: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for holding in holdings:
        ticker = normalize_ticker(holding.get("ticker"))
        if not ticker or ticker in {"CASH", "UNKNOWN"}:
            continue
        entries = manifest_entries_for_ticker(manifest, ticker)
        state = module_state(entries)
        completed = sum(1 for value in state.values() if value)
        missing = missing_portfolio_analysis_labels(state)
        latest_date = max((str(entry.get("date") or "") for entry in entries), default="") or None
        rows.append(
            {
                "ticker": ticker,
                "company_name": holding.get("name") or ticker,
                "portfolio_name": portfolio_name,
                "market_value": holding.get("market_value"),
                "module_state": state,
                "completed_count": completed,
                "required_count": len(REQUIRED_PORTFOLIO_ANALYSIS_MODULES),
                "completion_rate": round(completed / len(REQUIRED_PORTFOLIO_ANALYSIS_MODULES), 4),
                "missing_modules": missing,
                "latest_report_date": latest_date,
                "next_action": next_action(missing),
            }
        )
    rows.sort(key=lambda item: (item["completion_rate"], -(float(item.get("market_value") or 0))))
    average = sum(item["completion_rate"] for item in rows) / len(rows) if rows else 0.0
    ready_count = sum(1 for item in rows if item["completion_rate"] >= 1.0)
    return {
        "portfolio_name": portfolio_name,
        "holding_count": len(rows),
        "ready_count": ready_count,
        "average_completion": round(average, 4),
        "items": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="포트폴리오 분석 모듈 커버리지를 백엔드 없이 점검합니다.")
    parser.add_argument("--portfolio", default="이형주")
    parser.add_argument("--min-average-completion", type=float, default=0.0)
    parser.add_argument("--min-ready-count", type=int, default=0)
    parser.add_argument("--write-backlog", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
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
    selected = portfolios.get(args.portfolio)
    if not isinstance(selected, dict):
        raise SystemExit(f"포트폴리오를 찾지 못했습니다: {args.portfolio}")
    holdings = selected.get("holdings") if isinstance(selected.get("holdings"), list) else []
    result = coverage_for_portfolio(args.portfolio, holdings, manifest)
    result["module"] = "portfolio_analysis_coverage"
    result["generated_at"] = datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()
    result["thresholds"] = {
        "min_average_completion": args.min_average_completion,
        "min_ready_count": args.min_ready_count,
    }

    if args.write_backlog:
        out = vault / "_system" / "portfolio_analysis_backlog.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["backlog_path"] = str(out.relative_to(root))

    average = float(result["average_completion"])
    ready = int(result["ready_count"])
    print(f"프로젝트 루트: {root}")
    print(f"포트폴리오: {args.portfolio} | 보유 {result['holding_count']}개 | 준비 완료 {ready}개 | 평균 완료율 {average:.1%}")
    for item in result["items"][: max(0, args.limit)]:
        missing = ", ".join(item["missing_modules"]) if item["missing_modules"] else "누락 없음"
        print(f"- {item['company_name']} ({item['ticker']}): {item['completion_rate']:.0%} | 부족: {missing} | 다음: {item['next_action']}")
    if args.write_backlog:
        print(f"보강 큐 저장: {result['backlog_path']}")

    ok = average >= args.min_average_completion and ready >= args.min_ready_count
    if ok:
        print("포트폴리오 분석 커버리지 점검 정상")
        return 0
    print("포트폴리오 분석 커버리지 보강 필요")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
