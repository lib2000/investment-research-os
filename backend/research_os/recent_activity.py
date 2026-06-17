"""Recent activity compaction helpers for the research OS.

The FastAPI entrypoint still orchestrates the weekly brief, but small source-
specific compaction rules live here so scoring and UI payloads share the same
quality semantics.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from re import fullmatch, sub

from research_os import recent_activity_groups
from research_os import recent_activity_public_ir


def _parse_iso_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()



def compact_recent_manifest_entry(entry: dict, target_terms: dict) -> dict | None:
    entry_date = _parse_iso_date(entry.get("date"))
    if not entry_date:
        return None
    ticker = _normalize_ticker(str(entry.get("ticker") or ""))
    tags = [str(tag) for tag in (entry.get("tags") or []) if isinstance(tag, str)]
    text = " ".join(
        str(entry.get(key) or "")
        for key in ["summary", "source_url", "file_name", "relative_path", "type", "source_type"]
    )
    text += " " + " ".join(tags)
    related_targets: list[str] = []
    ticker_names = target_terms.get("ticker_names") or {}
    if ticker and ticker in (target_terms.get("ticker_set") or set(target_terms.get("tickers") or [])):
        related_targets.append(ticker_names.get(ticker) or ticker)
    for name in target_terms.get("names") or []:
        if name and name in text and name not in related_targets:
            related_targets.append(name)
    for sector in target_terms.get("sectors") or []:
        if sector and sector in text and sector not in related_targets:
            related_targets.append(sector)
    report_type = str(entry.get("type") or entry.get("report_type") or "")
    source_type = str(entry.get("source_type") or "")
    is_market_context = (
        report_type in {"customs-trade-brief", "daily-dossier-brief", "market-close-review"}
        or any(tag in {"customs", "export"} for tag in tags)
    )
    if not related_targets and not is_market_context:
        return None
    category = "report"
    if report_type == "customs-trade-brief" or "customs" in tags:
        category = "customs_export"
    elif source_type == "official_filing" or report_type == "dart-filing-watch":
        category = "filing"
    elif report_type in {"daily-dossier-brief", "market-close-review"}:
        category = "market_context"
    return {
        "category": category,
        "date": entry_date.isoformat(),
        "ticker": ticker,
        "company_name": ticker_names.get(ticker) or (related_targets[0] if related_targets else "시장/섹터 공통"),
        "report_type": report_type or "research",
        "source_type": source_type,
        "summary": entry.get("summary") or entry.get("file_name") or "요약 없음",
        "relative_path": entry.get("relative_path"),
        "source_url": entry.get("source_url"),
        "related_targets": related_targets or ["시장/섹터 공통"],
        "tags": tags[:12],
    }


def recent_report_display_priority(item: dict) -> int:
    report_type = str(item.get("report_type") or "")
    tags = {str(tag) for tag in (item.get("tags") or [])}
    if item.get("category") != "report":
        return 0
    if tags.intersection({"auto_operational_note", "coverage_backfill_note"}):
        return 0
    if report_type in {"research-checklist", "smart-trade-setup"}:
        return 0
    if report_type in {"broker-report", "naver-research-report", "shinhan-research-report"}:
        return 90
    if report_type in {"earnings-filing-note", "earnings-reaction"}:
        return 80
    if report_type in {"collaborative-team-report", "dossier-synthesis"}:
        return 70
    if report_type in {"source-url-capture", "research-capture"}:
        return 60
    if tags.intersection({"earnings", "filing", "valuation", "growth", "risk", "institution"}):
        return 55
    return 30


def recent_filing_priority(item: dict) -> int:
    importance = str(item.get("importance") or "")
    tags = {str(tag) for tag in (item.get("tags") or [])}
    summary = str(item.get("summary") or "")
    score = {"높음": 100, "중간": 70, "보통": 30}.get(importance, 30)
    if tags.intersection({"ownership", "flows"}) or any(keyword in summary for keyword in ["대량보유", "주요주주", "소유상황"]):
        score += 20
    if tags.intersection({"earnings", "financials"}) or any(keyword in summary for keyword in ["사업보고서", "반기보고서", "분기보고서"]):
        score += 20
    if tags.intersection({"event", "risk", "financing", "dilution"}):
        score += 25
    return score


def recent_ownership_filing_items(filings: list[dict]) -> list[dict]:
    ownership_keywords = ("대량보유", "주요주주", "소유상황", "5%")
    ownership_items = []
    for item in filings:
        tags = {str(tag) for tag in (item.get("tags") or [])}
        summary = str(item.get("summary") or "")
        if tags.intersection({"ownership", "flows", "institution"}) or any(
            keyword in summary for keyword in ownership_keywords
        ):
            ownership_items.append({**item, "filing_priority": recent_filing_priority(item)})
    ownership_items.sort(
        key=lambda item: (int(item.get("filing_priority") or 0), item.get("date") or ""),
        reverse=True,
    )
    return ownership_items


def recent_watch_summary(daily_watch: dict, counts: dict) -> dict:
    dart = daily_watch.get("dart") if isinstance(daily_watch.get("dart"), dict) else {}
    schedules = daily_watch.get("source_schedule") if isinstance(daily_watch.get("source_schedule"), list) else []
    due_sources = [item for item in schedules if isinstance(item, dict) and item.get("due")]
    failed_sources = [
        item for item in schedules
        if isinstance(item, dict) and str(item.get("source_status") or "").lower() in {"error", "failed", "failure"}
    ]
    return {
        "status": "점검 완료" if not dart.get("due") and not due_sources and not failed_sources else "확인 필요",
        "dart_message": dart.get("reliability_message") or dart.get("status") or "DART 상태 미확인",
        "dart_coverage_rate": dart.get("coverage_rate"),
        "due_source_count": len(due_sources),
        "failed_source_count": len(failed_sources),
        "recent_signal_count": (
            int(counts.get("filings") or 0)
            + int(counts.get("reports") or 0)
            + int(counts.get("public_ir_sec") or 0)
            + int(counts.get("customs_exports") or 0)
        ),
        "due_sources": [item.get("label") or item.get("key") for item in due_sources[:5]],
        "failed_sources": [item.get("label") or item.get("key") for item in failed_sources[:5]],
    }


def recent_activity_target_terms(runtime, settings) -> dict:
    tickers: set[str] = set()
    names: set[str] = set()
    sectors: set[str] = set()
    ticker_names: dict[str, str] = {}
    try:
        store = runtime.read_portfolio_store(settings)
        for portfolio in (store.get("portfolios") or {}).values():
            if not isinstance(portfolio, dict):
                continue
            for holding in portfolio.get("holdings") or []:
                if not isinstance(holding, dict):
                    continue
                ticker = runtime.normalize_ticker(str(holding.get("ticker") or ""))
                if ticker and ticker not in {"CASH", "UNKNOWN"}:
                    tickers.add(ticker)
                name = str(holding.get("name") or holding.get("company_name") or "").strip()
                if name:
                    names.add(name)
                    if ticker:
                        ticker_names[ticker] = name
    except Exception:
        pass
    try:
        interests = runtime.read_interest_list(settings)
        for item in interests.get("tickers", []):
            if not isinstance(item, dict):
                continue
            ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
            if ticker and ticker not in {"CASH", "UNKNOWN"}:
                tickers.add(ticker)
            verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
            name = str(
                item.get("name")
                or item.get("company_name")
                or verification.get("company_name")
                or ""
            ).strip()
            if name:
                names.add(name)
                if ticker:
                    ticker_names[ticker] = name
        for item in interests.get("sectors", []):
            if not isinstance(item, dict):
                continue
            sector = str(item.get("name") or item.get("sector") or "").strip()
            if sector:
                sectors.add(sector)
    except Exception:
        pass
    return {
        "tickers": sorted(tickers),
        "names": sorted(names),
        "sectors": sorted(sectors),
        "ticker_names": ticker_names,
        "ticker_set": set(tickers),
    }

def build_recent_weekly_research_brief(runtime, settings, days: int = 7, refresh_if_due: bool = True) -> dict:
    normalized_days = max(1, min(int(days or 7), 30))
    cutoff = recent_activity_cutoff(runtime.current_storage_date(), normalized_days)
    target_terms = runtime.recent_activity_target_terms(settings)
    if refresh_if_due and settings.dart_filing_auto_refresh and settings.dart_api_key:
        cache = runtime.read_dart_filing_cache(settings)
        if runtime.dart_daily_check_status(cache, settings).get("due"):
            try:
                runtime.refresh_dart_filing_watch(settings, force=False, save_result=True)
            except Exception:
                pass
    dart_cache = runtime.read_dart_filing_cache(settings)
    dart_items = []
    for entry in (dart_cache.get("entries") or {}).values():
        item = compact_recent_dart_entry(entry if isinstance(entry, dict) else {})
        item_date = _parse_iso_date(item.get("date")) if item else None
        if item and item_date and item_date >= cutoff:
            dart_items.append(item)
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    manifest_items = []
    for entry in runtime.read_manifest(vault_dir):
        if not isinstance(entry, dict):
            continue
        if is_public_ir_sec_manifest_entry(entry):
            item = compact_recent_public_ir_sec_entry(entry, target_terms)
        else:
            item = compact_recent_manifest_entry(entry, target_terms)
        item_date = _parse_iso_date(item.get("date")) if item else None
        if item and item_date and item_date >= cutoff:
            if item.get("category") == "filing" and item.get("source_type") == "official_filing":
                continue
            manifest_items.append(item)
    all_items = dedupe_recent_activity_items(dart_items + manifest_items)
    all_items.sort(key=lambda item: (item.get("date") or "", item.get("category") or ""), reverse=True)
    recommendation_evidence_index = runtime.daily_recommendation_evidence_link_index(settings)
    annotate_recent_weekly_recommendation_links(all_items, recommendation_evidence_index)
    annotate_recent_weekly_navigation_hints(all_items)
    filings = [item for item in all_items if item.get("category") == "filing"]
    reports = [item for item in all_items if item.get("category") == "report"]
    customs_exports = [item for item in all_items if item.get("category") == "customs_export"]
    market_context = [item for item in all_items if item.get("category") == "market_context"]
    public_ir_sec_items = [item for item in all_items if item.get("category") == "public_ir_sec"]
    usable_public_ir_sec_items = [item for item in public_ir_sec_items if item.get("usable_for_recommendation")]
    blocked_public_ir_sec_items = [item for item in public_ir_sec_items if item.get("needs_body_copy") or not item.get("usable_for_recommendation")]
    important_filings = sorted(
        [item for item in filings if recent_filing_priority(item) >= 50],
        key=lambda item: (recent_filing_priority(item), item.get("date") or ""),
        reverse=True,
    )
    ownership_filings = recent_ownership_filing_items(important_filings)
    display_reports = sorted(
        [
            {**item, "display_priority": recent_report_display_priority(item)}
            for item in reports
            if recent_report_display_priority(item) > 0
        ],
        key=lambda item: (int(item.get("display_priority") or 0), item.get("date") or ""),
        reverse=True,
    )
    recommendation_linked_items = sorted(
        [item for item in all_items if item.get("used_in_recommendation")],
        key=lambda item: (1 if item.get("used_in_latest_recommendation") else 0, item.get("date") or "", item.get("ticker") or ""),
        reverse=True,
    )
    counts = {
        "filings": len(filings),
        "important_filings": len(important_filings),
        "ownership_filings": len(ownership_filings),
        "reports": len(reports),
        "display_reports": len(display_reports),
        "hidden_low_signal_reports": max(0, len(reports) - len(display_reports)),
        "customs_exports": len(customs_exports),
        "market_context": len(market_context),
        "public_ir_sec": len(public_ir_sec_items),
        "public_ir_sec_usable": len(usable_public_ir_sec_items),
        "public_ir_sec_blocked": len(blocked_public_ir_sec_items),
        "public_ir_sec_needs_body": sum(1 for item in public_ir_sec_items if item.get("needs_body_copy")),
        "recommendation_evidence_linked": sum(1 for item in all_items if item.get("used_in_recommendation")),
        "latest_recommendation_evidence_linked": sum(1 for item in all_items if item.get("used_in_latest_recommendation")),
        "total": len(all_items),
    }
    category_groups = build_recent_weekly_category_groups(
        ownership_filings=ownership_filings,
        important_filings=important_filings,
        display_reports=display_reports,
        public_ir_sec_items=public_ir_sec_items,
        customs_exports=customs_exports,
        market_context=market_context,
    )
    target_digest = build_recent_weekly_target_digest(
        sources=[
            ("filing", important_filings),
            ("report", display_reports),
            ("public_ir_sec", public_ir_sec_items),
            ("customs", customs_exports),
            ("market", market_context),
        ]
    )
    daily_watch = {
        "dart": runtime.dart_daily_check_status(dart_cache, settings),
        "source_schedule": runtime.build_external_source_schedule_status(settings),
    }
    payload = {
        "status": "success",
        "module": "recent_weekly_research_brief",
        "as_of": runtime.current_storage_timestamp(),
        "period_days": normalized_days,
        "period_start": cutoff.isoformat(),
        "period_end": runtime.current_storage_date().isoformat(),
        "target_scope": {
            "holding_and_interest_ticker_count": len(target_terms.get("tickers") or []),
            "company_names": target_terms.get("names") or [],
            "sectors": target_terms.get("sectors") or [],
        },
        "daily_watch": daily_watch,
        "watch_summary": recent_watch_summary(daily_watch, counts),
        "recommendation_evidence_summary": {
            "latest_recommendation_date": recommendation_evidence_index.get("latest_recommendation_date"),
            "linked_record_count": recommendation_evidence_index.get("linked_record_count"),
            "latest_linked_record_count": recommendation_evidence_index.get("latest_linked_record_count"),
            "recent_weekly_linked_item_count": counts.get("recommendation_evidence_linked"),
            "latest_recent_weekly_linked_item_count": counts.get("latest_recommendation_evidence_linked"),
        },
        "counts": counts,
        "category_groups": category_groups,
        "target_digest": target_digest,
        "recommendation_linked_items": recommendation_linked_items[:12],
        "important_filings": important_filings[:15],
        "ownership_filings": ownership_filings[:10],
        "filings": filings[:30],
        "display_reports": display_reports[:20],
        "reports": reports[:30],
        "public_ir_sec_items": public_ir_sec_items[:20],
        "customs_exports": customs_exports[:20],
        "market_context": market_context[:20],
        "items": all_items[:80],
        "next_actions": [
            "DART 점검 필요 상태이면 공시 재점검을 실행하세요.",
            "최근 리포트는 보유/관심 종목과 연결된 항목만 우선 검토하세요.",
            "공개 IR/SEC 자료는 본문 추출이 정상인 보유/관심 종목 연결 항목만 추천 점수에 반영하세요.",
            "URL-only 공개 IR/SEC 자료는 최근 1주 화면에 표시하되 본문 보강 전에는 추천 점수 가산에서 제외됩니다.",
            "관세청 수출입 자료는 실제 수치가 있는 경우에만 저장/RAG에 반영됩니다.",
        ],
    }
    return runtime.repair_mojibake_payload(payload)

def recent_activity_cutoff(current_date: date, days: int) -> date:
    return current_date - timedelta(days=max(1, int(days or 7)) - 1)


def compact_recent_dart_entry(entry: dict) -> dict | None:
    filing = entry.get("filing") if isinstance(entry.get("filing"), dict) else {}
    receipt = str(filing.get("receipt_date") or filing.get("rcept_dt") or "")
    if not fullmatch(r"\d{8}", receipt):
        return None
    try:
        entry_date = datetime.strptime(receipt, "%Y%m%d").date()
    except ValueError:
        return None
    ticker = _normalize_ticker(entry.get("ticker") or filing.get("stock_code"))
    return {
        "category": "filing",
        "date": entry_date.isoformat(),
        "ticker": ticker,
        "company_name": filing.get("corp_name") or entry.get("corp_name") or ticker,
        "report_type": "dart-filing-watch",
        "source_type": "official_filing",
        "summary": filing.get("report_name") or filing.get("report_nm") or "DART 공시",
        "importance": entry.get("importance"),
        "action": entry.get("action"),
        "relative_path": ((entry.get("storage") or {}).get("relative_path") if isinstance(entry.get("storage"), dict) else None),
        "source_url": filing.get("source_url") or (
            f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={filing.get('rcept_no')}"
            if filing.get("rcept_no")
            else None
        ),
        "related_targets": [filing.get("corp_name") or ticker],
        "tags": entry.get("tags") or [],
    }


def recent_activity_item_key(item: dict) -> tuple:
    summary = sub(r"\s+", " ", str(item.get("summary") or "").strip().lower())[:180]
    source_url = str(item.get("source_url") or "").strip()
    source_key = f"url:{source_url}" if source_url else f"summary:{summary}"
    return (
        str(item.get("category") or ""),
        str(item.get("date") or ""),
        _normalize_ticker(item.get("ticker")),
        str(item.get("company_name") or ""),
        str(item.get("report_type") or ""),
        source_key,
    )


def recent_weekly_evidence_path_key(value: object) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("./").lower()


def annotate_recent_weekly_navigation_hints(items: list[dict]) -> None:
    """Attach console navigation hints for stored material and RAG search."""
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        relative_path = str(item.get("relative_path") or item.get("source_relative_path") or "").strip().replace("\\", "/")
        file_name = relative_path.rsplit("/", 1)[-1] if relative_path else ""
        title = str(item.get("title") or item.get("summary") or "").strip()
        company = str(item.get("company_name") or item.get("company") or "").strip()
        query_parts = [
            part
            for part in [ticker, company, title, item.get("recommendation_usage_summary")]
            if str(part or "").strip()
        ]
        if ticker and file_name:
            item["memory_lookup_key"] = ticker
            item["memory_file_name"] = file_name
            item["memory_navigation_hint"] = f"저장 데이터 탭에서 {ticker} 조회 후 {file_name} 열기"
        if query_parts:
            item["rag_search_query"] = " ".join(str(part).strip() for part in query_parts)[:180]


def annotate_recent_weekly_recommendation_links(items: list[dict], evidence_index: dict) -> None:
    """Attach daily recommendation evidence usage metadata to recent weekly items."""
    by_path = evidence_index.get("by_relative_path") if isinstance(evidence_index, dict) else {}
    if not isinstance(by_path, dict):
        by_path = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        keys = {
            recent_weekly_evidence_path_key(item.get("relative_path")),
            recent_weekly_evidence_path_key(item.get("json_relative_path")),
            recent_weekly_evidence_path_key(item.get("source_relative_path")),
        }
        links: list[dict] = []
        seen_records: set[str] = set()
        for key in sorted(key for key in keys if key):
            for link in by_path.get(key, []) or []:
                if not isinstance(link, dict):
                    continue
                record_key = str(link.get("record_id") or "") or f"{link.get('recommendation_date')}:{link.get('rank')}:{link.get('ticker')}"
                if record_key in seen_records:
                    continue
                seen_records.add(record_key)
                links.append({
                    "record_id": link.get("record_id"),
                    "recommendation_date": link.get("recommendation_date"),
                    "rank": link.get("rank"),
                    "ticker": link.get("ticker"),
                    "company_name": link.get("company_name"),
                    "is_latest": bool(link.get("is_latest")),
                })
        latest_links = [link for link in links if link.get("is_latest")]
        if links:
            item["recommendation_links"] = links[:5]
            item["recommendation_link_count"] = len(links)
            item["used_in_recommendation"] = True
            item["used_in_latest_recommendation"] = bool(latest_links)
            item["recommendation_usage_label"] = "오늘 추천 근거" if latest_links else "추천 이력 근거"
            item["recommendation_usage_summary"] = ", ".join(
                f"{link.get('recommendation_date') or '추천일 미확인'} {link.get('rank') or '-'}위 {link.get('company_name') or link.get('ticker') or '종목 미확인'}"
                for link in links[:3]
            )


def dedupe_recent_activity_items(items: list[dict]) -> list[dict]:
    unique_items: list[dict] = []
    seen: set[tuple] = set()
    for item in items:
        key = recent_activity_item_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items

def is_public_ir_sec_manifest_entry(entry: dict) -> bool:
    return recent_activity_public_ir.is_public_ir_sec_manifest_entry(entry)


def public_ir_sec_entry_is_usable_for_recommendation(entry: dict) -> bool:
    return recent_activity_public_ir.public_ir_sec_entry_is_usable_for_recommendation(entry)


def compact_recent_public_ir_sec_entry(entry: dict, target_terms: dict) -> dict | None:
    return recent_activity_public_ir.compact_recent_public_ir_sec_entry(entry, target_terms)

def recent_weekly_source_family(provider: str) -> str:
    return recent_activity_groups.recent_weekly_source_family(provider)


def recent_weekly_category_group(label: str, key: str, items: list[dict], *, limit: int = 8, note: str = "") -> dict:
    return recent_activity_groups.recent_weekly_category_group(label, key, items, limit=limit, note=note)


def build_recent_weekly_category_groups(
    *,
    ownership_filings: list[dict],
    important_filings: list[dict],
    display_reports: list[dict],
    public_ir_sec_items: list[dict],
    customs_exports: list[dict],
    market_context: list[dict],
) -> list[dict]:
    return recent_activity_groups.build_recent_weekly_category_groups(
        ownership_filings=ownership_filings,
        important_filings=important_filings,
        display_reports=display_reports,
        public_ir_sec_items=public_ir_sec_items,
        customs_exports=customs_exports,
        market_context=market_context,
    )


def build_recent_weekly_target_digest(*, sources: list[tuple[str, list[dict]]], limit: int = 20) -> list[dict]:
    return recent_activity_groups.build_recent_weekly_target_digest(sources=sources, limit=limit)
