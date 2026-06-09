"""Validate recent weekly materials and recommendation evidence linkage offline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT_MARKERS = ("backend/research_os_main.py", "research_vault/manifest.json")
LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
DEFAULT_MANIFEST = Path("research_vault/manifest.json")
DEFAULT_PORTFOLIOS = Path("research_vault/_system/user_portfolios.json")
DEFAULT_INTERESTS = Path("research_vault/_system/interest_list.json")
DEFAULT_RECOMMENDATIONS = Path("research_vault/_system/daily_recommendations.json")
RECENT_ACTIVITY_IMPORTS = (
    "compact_recent_manifest_entry",
    "compact_recent_public_ir_sec_entry",
    "is_public_ir_sec_manifest_entry",
    "recent_filing_priority",
    "recent_ownership_filing_items",
    "recent_report_display_priority",
    "build_recent_weekly_category_groups",
)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if all((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON 파싱 실패: {path} | {exc}") from exc


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def path_key(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return ""
    marker = "research_vault/"
    if marker in text:
        return marker + text.split(marker, 1)[1].lstrip("/")
    return text.lstrip("./")


def add_ticker(tickers: set[str], ticker_names: dict[str, str], ticker: Any, name: Any = "") -> None:
    symbol = str(ticker or "").strip().upper()
    if not symbol or symbol == "UNKNOWN":
        return
    tickers.add(symbol)
    label = str(name or "").strip()
    if label:
        ticker_names.setdefault(symbol, label)


def build_target_terms(portfolios: dict[str, Any], interests: dict[str, Any]) -> dict[str, Any]:
    tickers: set[str] = set()
    ticker_names: dict[str, str] = {}
    names: set[str] = set()
    sectors: set[str] = set()

    for portfolio in (portfolios.get("portfolios") or {}).values():
        if not isinstance(portfolio, dict):
            continue
        for holding in portfolio.get("holdings") or []:
            if not isinstance(holding, dict):
                continue
            name = holding.get("name") or holding.get("company_name")
            add_ticker(tickers, ticker_names, holding.get("ticker"), name)
            if name:
                names.add(str(name).strip())
            sector = holding.get("sector")
            if sector:
                sectors.add(str(sector).strip())
            for tag in holding.get("theme_tags") or []:
                if tag:
                    sectors.add(str(tag).strip())

    for item in interests.get("tickers") or []:
        if not isinstance(item, dict):
            continue
        verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
        name = item.get("company_name") or verification.get("company_name") or item.get("name")
        add_ticker(tickers, ticker_names, item.get("ticker") or verification.get("official_symbol"), name)
        if name:
            names.add(str(name).strip())
    for item in interests.get("sectors") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("sector")
        if name:
            sectors.add(str(name).strip())

    names.update(value for value in ticker_names.values() if value)
    return {
        "tickers": sorted(tickers),
        "ticker_set": tickers,
        "ticker_names": ticker_names,
        "names": sorted(names),
        "sectors": sorted(sectors),
    }


def manifest_entries(manifest: Any) -> list[dict[str, Any]]:
    if isinstance(manifest, dict):
        raw = manifest.get("items") or manifest.get("records") or []
    else:
        raw = manifest
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def latest_recommendation_records(store: dict[str, Any]) -> list[dict[str, Any]]:
    records = [item for item in store.get("records") or [] if isinstance(item, dict)]
    dates = sorted({str(item.get("recommendation_date") or "")[:10] for item in records if item.get("recommendation_date")})
    if not dates:
        return []
    latest = dates[-1]
    latest_records = [item for item in records if str(item.get("recommendation_date") or "")[:10] == latest]
    return sorted(latest_records, key=lambda item: int(item.get("rank") or 999))


def recommendation_path_index(records: list[dict[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for record in records:
        for document in record.get("evidence_documents") or []:
            if not isinstance(document, dict):
                continue
            for key in ("source_relative_path", "relative_path", "json_relative_path"):
                value = path_key(document.get(key))
                if value:
                    paths.add(value)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="최근 1주 자료와 오늘 추천 근거 연결을 오프라인으로 점검합니다.")
    parser.add_argument("--days", type=int, default=7, help="최근 자료 기준 일수")
    parser.add_argument("--min-total", type=int, default=1, help="최근 자료 최소 건수")
    parser.add_argument("--min-category-groups", type=int, default=4, help="표시 가능한 자료 묶음 최소 수")
    parser.add_argument("--min-recommendation-documents", type=int, default=3, help="최신 추천 근거 문서 최소 수")
    parser.add_argument("--min-linked-recent-items", type=int, default=1, help="최근 1주 자료와 추천 근거 경로가 직접 만나는 최소 건수")
    parser.add_argument("--strict", action="store_true", help="경고가 있으면 실패 코드로 종료")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    sys.path.insert(0, str(root / "backend"))
    recent_activity = __import__("research_os.recent_activity", fromlist=list(RECENT_ACTIVITY_IMPORTS))

    target_terms = build_target_terms(
        load_json(root / DEFAULT_PORTFOLIOS, {"portfolios": {}}),
        load_json(root / DEFAULT_INTERESTS, {"tickers": [], "sectors": []}),
    )
    cutoff = (datetime.now(LOCAL_TIMEZONE).date() - timedelta(days=max(1, args.days))).isoformat()
    recent_items: list[dict[str, Any]] = []
    for entry in manifest_entries(load_json(root / DEFAULT_MANIFEST, [])):
        entry_date = parse_date(entry.get("date"))
        if not entry_date or entry_date.date().isoformat() < cutoff:
            continue
        if recent_activity.is_public_ir_sec_manifest_entry(entry):
            item = recent_activity.compact_recent_public_ir_sec_entry(entry, target_terms)
        else:
            item = recent_activity.compact_recent_manifest_entry(entry, target_terms)
        if item:
            recent_items.append(item)

    filings = [item for item in recent_items if item.get("category") == "filing"]
    reports = [item for item in recent_items if item.get("category") == "report"]
    public_ir = [item for item in recent_items if item.get("category") == "public_ir_sec"]
    customs = [item for item in recent_items if item.get("category") == "customs_export"]
    market = [item for item in recent_items if item.get("category") == "market_context"]
    important_filings = sorted(
        [item for item in filings if recent_activity.recent_filing_priority(item) >= 50],
        key=lambda item: (recent_activity.recent_filing_priority(item), item.get("date") or ""),
        reverse=True,
    )
    ownership = recent_activity.recent_ownership_filing_items(important_filings)
    display_reports = sorted(
        [{**item, "display_priority": recent_activity.recent_report_display_priority(item)} for item in reports if recent_activity.recent_report_display_priority(item) > 0],
        key=lambda item: (int(item.get("display_priority") or 0), item.get("date") or ""),
        reverse=True,
    )
    groups = recent_activity.build_recent_weekly_category_groups(
        ownership_filings=ownership,
        important_filings=important_filings,
        display_reports=display_reports,
        public_ir_sec_items=public_ir,
        customs_exports=customs,
        market_context=market,
    )
    visible_groups = [group for group in groups if int(group.get("count") or 0) > 0]

    latest_records = latest_recommendation_records(load_json(root / DEFAULT_RECOMMENDATIONS, {"records": []}))
    evidence_paths = recommendation_path_index(latest_records)
    existing_evidence = [path for path in evidence_paths if (root / path).exists()]
    recent_paths = {path_key(item.get("relative_path")) for item in recent_items if path_key(item.get("relative_path"))}
    linked_recent_paths = sorted(recent_paths & evidence_paths)
    linked_recent_items = [
        item
        for item in recent_items
        if path_key(item.get("relative_path")) in evidence_paths
    ]
    impact_counts = Counter(
        "강화" if path_key(item.get("relative_path")) in evidence_paths else "후보"
        for item in recent_items
        if item.get("category") in {"filing", "report", "public_ir_sec", "customs_export"}
    )

    issues: list[str] = []
    warnings: list[str] = []
    if len(recent_items) < args.min_total:
        issues.append(f"최근 {args.days}일 자료 부족: {len(recent_items)}개 / 최소 {args.min_total}개")
    if len(visible_groups) < args.min_category_groups:
        issues.append(f"최근 1주 자료 묶음 부족: {len(visible_groups)}개 / 최소 {args.min_category_groups}개")
    if len(existing_evidence) < args.min_recommendation_documents:
        issues.append(f"최신 추천 근거 문서 부족: {len(existing_evidence)}개 / 최소 {args.min_recommendation_documents}개")
    if len(linked_recent_paths) == 0:
        warnings.append("최근 1주 자료와 오늘 추천 근거 직접 연결 0건")
    elif len(linked_recent_paths) < args.min_linked_recent_items:
        warnings.append(f"최근 1주 자료와 최신 추천 근거 직접 연결 적음: {len(linked_recent_paths)}개 / 기준 {args.min_linked_recent_items}개")
    if public_ir and not any(item.get("usable_for_recommendation") for item in public_ir):
        warnings.append("최근 공개 IR/SEC 자료가 있으나 추천 가산 가능한 본문 추출 항목이 없습니다.")

    print(f"프로젝트 루트: {root}")
    print(f"기간: 최근 {args.days}일 | 기준 시작일 {cutoff}")
    print(f"대상 범위: 티커 {len(target_terms['tickers'])}개 | 회사명 {len(target_terms['names'])}개 | 섹터 {len(target_terms['sectors'])}개")
    print(
        "최근 자료: "
        f"전체 {len(recent_items)}개 | 공시 {len(filings)}개 | 중요 공시 {len(important_filings)}개 | "
        f"수급/대량보유 {len(ownership)}개 | 리포트 {len(display_reports)}/{len(reports)}개 | "
        f"공개 IR/SEC {len(public_ir)}개 | 수출입 {len(customs)}개 | 시장자료 {len(market)}개"
    )
    print(f"표시 자료 묶음: {len(visible_groups)}개 | " + ", ".join(f"{group.get('label')}={group.get('count')}" for group in visible_groups))
    latest_date = latest_records[0].get("recommendation_date") if latest_records else "미확인"
    print(f"최신 추천일: {latest_date} | 추천 {len(latest_records)}개 | 근거 문서 {len(existing_evidence)}/{len(evidence_paths)}개")
    print(f"최근 1주-추천 근거 직접 연결: {len(linked_recent_paths)}개")
    print(
        "추천 영향 요약: "
        f"강화 {impact_counts.get('강화', 0)}개 | "
        f"후보 {impact_counts.get('후보', 0)}개 | "
        f"연결 항목 {len(linked_recent_items)}개"
    )

    for warning in warnings:
        print(f"경고: {warning}")
    for issue in issues:
        print(f"오류: {issue}")
    if issues or (warnings and args.strict):
        print("최근 1주 자료/추천 근거 연결 확인 필요")
        return 1
    print("최근 1주 자료/추천 근거 연결 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
