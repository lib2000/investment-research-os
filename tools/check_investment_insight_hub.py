"""Validate the integrated investment insight hub from saved local state."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
SYSTEM_DIR = Path("research_vault/_system")
MANIFEST_PATH = Path("research_vault/manifest.json")


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


def console_print(value: str = "") -> None:
    try:
        print(value, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_value = value.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_value, flush=True)


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10])
    except ValueError:
        return None


def manifest_entries(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        raw = manifest.get("items") or manifest.get("records") or []
    else:
        raw = manifest
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def recent_weekly_counts(root: Path, *, days: int) -> dict[str, int]:
    cutoff = datetime.now(LOCAL_TIMEZONE).date() - timedelta(days=max(1, int(days or 7)))
    counts: Counter[str] = Counter()
    for entry in manifest_entries(load_json(root / MANIFEST_PATH, [])):
        entry_date = parse_date(entry.get("date") or entry.get("created_at") or entry.get("updated_at"))
        if entry_date and entry_date.date() < cutoff:
            continue
        tags = {str(tag).lower() for tag in entry.get("tags") or []} if isinstance(entry.get("tags"), list) else set()
        text = " ".join(
            str(entry.get(key) or "").lower()
            for key in ("type", "module", "category", "source", "title", "summary", "relative_path")
        )
        if "filing" in tags or "dart" in text or "공시" in text:
            counts["filing"] += 1
        elif "public_ir_sec" in tags or "sec" in tags or "ir" in tags or "public-ir-sec" in text:
            counts["public_ir_sec"] += 1
        elif "report" in tags or "analyst" in tags or "research" in tags or "보고서" in text:
            counts["report"] += 1
        elif "market" in tags or "market-" in text or "시장" in text:
            counts["market"] += 1
        else:
            counts["other"] += 1
    return dict(counts)


def saved_holdings(root: Path, *, portfolio_name: str) -> tuple[str, list[dict[str, Any]]]:
    payload = load_json(root / SYSTEM_DIR / "user_portfolios.json", {"portfolios": {}})
    portfolios = payload.get("portfolios") if isinstance(payload.get("portfolios"), dict) else {}
    selected: list[dict[str, Any]] = []
    selected_names: list[str] = []
    for key, portfolio in portfolios.items():
        if not isinstance(portfolio, dict):
            continue
        display_name = str(portfolio.get("portfolio_name") or key)
        if portfolio_name not in {"__all__", "*"} and portfolio_name not in {key, display_name}:
            continue
        holdings = [item for item in portfolio.get("holdings") or [] if isinstance(item, dict)]
        if holdings:
            selected.extend(holdings)
            selected_names.append(display_name)
    if portfolio_name in {"__all__", "*"}:
        return (" / ".join(selected_names) if selected_names else "전체 포트폴리오", selected)
    return (selected_names[0] if selected_names else portfolio_name, selected)


def build_dashboard(root: Path, *, portfolio_name: str, days: int, limit: int) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.investment_insight_hub import build_investment_insight_hub
    from research_os.models import PortfolioHolding

    resolved_name, holding_rows = saved_holdings(root, portfolio_name=portfolio_name)
    holdings = [PortfolioHolding(**item) for item in holding_rows]
    system_dir = root / SYSTEM_DIR
    payload = build_investment_insight_hub(
        portfolio_name=resolved_name,
        holdings=holdings,
        market_journal=load_json(system_dir / "market_close_journal.json", {"entries": []}),
        news_inbox=load_json(system_dir / "news_inbox.json", {"items": []}),
        dart_cache=load_json(system_dir / "dart_filing_watch_cache.json", {"entries": {}}),
        recent_weekly={"counts": recent_weekly_counts(root, days=days)},
        generated_at=datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds"),
        today=datetime.now(LOCAL_TIMEZONE).date(),
        days=days,
        limit=limit,
    )
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    families = sorted(
        {
            str(item.get("source_family") or "")
            for item in payload.get("insights") or []
            if isinstance(item, dict) and item.get("source_family")
        }
    )
    payload["readiness"] = {
        "portfolio_holding_count": len(holdings),
        "insight_count": len(payload.get("insights") or []),
        "source_families": families,
        "sentiment_label": payload.get("aggregate_sentiment_label"),
        "coverage_score": coverage_score(coverage),
    }
    return payload


def coverage_score(coverage: dict[str, Any]) -> float:
    required = [
        "market_data_items",
        "market_journal_items",
        "official_filing_items",
        "news_items",
        "policy_law_items",
    ]
    satisfied = sum(1 for key in required if int(coverage.get(key) or 0) > 0)
    return round(satisfied / len(required) * 100.0, 1)


def strict_errors(payload: dict[str, Any], *, min_insights: int, min_coverage_score: float) -> list[str]:
    errors: list[str] = []
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    required_counts = {
        "market_data_items": "시장 데이터",
        "market_journal_items": "시장일지/투자심리",
        "official_filing_items": "공시",
        "news_items": "뉴스",
        "policy_law_items": "정책·법령·규제",
    }
    for key, label in required_counts.items():
        if int(coverage.get(key) or 0) <= 0:
            errors.append(f"{label} 커버리지가 없습니다.")
    if int(readiness.get("insight_count") or 0) < min_insights:
        errors.append(f"인사이트 수가 기준({min_insights}개)보다 적습니다.")
    if float(readiness.get("coverage_score") or 0.0) < min_coverage_score:
        errors.append(f"커버리지 점수가 기준({min_coverage_score:.1f}%)보다 낮습니다.")
    families = set(readiness.get("source_families") or [])
    for family in ["market_data_sentiment", "official_filings", "policy_law_news"]:
        if family not in families:
            errors.append(f"{family} 인사이트 패밀리가 없습니다.")
    if not payload.get("aggregate_sentiment_label"):
        errors.append("종합 투자심리 라벨이 없습니다.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="저장 상태 기반 통합 투자 인사이트 허브를 점검합니다.")
    parser.add_argument("--portfolio-name", default="__all__", help="점검할 포트폴리오 이름. 기본은 전체 합산")
    parser.add_argument("--days", type=int, default=7, help="최근 자료 기준 일수")
    parser.add_argument("--limit", type=int, default=12, help="생성할 최대 인사이트 수")
    parser.add_argument("--min-insights", type=int, default=4)
    parser.add_argument("--min-coverage-score", type=float, default=100.0)
    parser.add_argument("--json", action="store_true", help="전체 payload를 JSON으로 출력")
    parser.add_argument("--strict", action="store_true", help="커버리지 부족을 실패로 처리")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    payload = build_dashboard(root, portfolio_name=args.portfolio_name, days=args.days, limit=args.limit)
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}

    if args.json:
        console_print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        console_print(f"프로젝트 루트: {root}")
        console_print(f"포트폴리오: {payload.get('portfolio_name') or args.portfolio_name}")
        console_print(f"헤드라인: {payload.get('headline') or '미확인'}")
        console_print(
            "커버리지: "
            f"시장 데이터 {int(coverage.get('market_data_items') or 0)} / "
            f"시장일지·심리 {int(coverage.get('market_journal_items') or 0)} / "
            f"공시 {int(coverage.get('official_filing_items') or 0)} / "
            f"뉴스 {int(coverage.get('news_items') or 0)} / "
            f"정책·법령 {int(coverage.get('policy_law_items') or 0)}"
        )
        console_print(
            "인사이트 준비도: "
            f"{float(readiness.get('coverage_score') or 0.0):.1f}% / "
            f"인사이트 {int(readiness.get('insight_count') or 0)}개 / "
            f"패밀리 {', '.join(readiness.get('source_families') or []) or '없음'}"
        )
        for insight in (payload.get("insights") or [])[:5]:
            if isinstance(insight, dict):
                console_print(
                    "- "
                    f"{insight.get('severity') or '미확인'} | "
                    f"{insight.get('source_family') or 'source'} | "
                    f"{insight.get('title') or '제목 없음'}"
                )

    errors = strict_errors(
        payload,
        min_insights=args.min_insights,
        min_coverage_score=args.min_coverage_score,
    )
    if args.strict and errors:
        console_print("통합 투자 인사이트 허브 점검 실패")
        for error in errors:
            console_print(f"- {error}")
        return 1
    console_print("통합 투자 인사이트 허브 점검 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
