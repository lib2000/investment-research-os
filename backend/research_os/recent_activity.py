"""Recent activity compaction helpers for the research OS.

The FastAPI entrypoint still orchestrates the weekly brief, but small source-
specific compaction rules live here so scoring and UI payloads share the same
quality semantics.
"""

from __future__ import annotations

from datetime import date, datetime
from re import fullmatch, sub
from urllib.parse import urlparse


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


def _provider_from_public_ir_url(source_url: object) -> str:
    text = str(source_url or "").strip()
    parsed = urlparse(text)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return "공개 IR/SEC"
    if host.endswith("sec.gov"):
        return "SEC EDGAR"
    return host[4:] if host.startswith("www.") else host


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

def is_public_ir_sec_manifest_entry(entry: dict) -> bool:
    return (
        str(entry.get("scope") or "") == "public_ir_sec"
        or str(entry.get("ticker") or "").upper() == "PUBLIC_IR_SEC"
        or str(entry.get("type") or entry.get("report_type") or "") == "public-ir-sec"
    )


def public_ir_sec_entry_is_usable_for_recommendation(entry: dict) -> bool:
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    status = str(quality.get("status") or entry.get("capture_quality_status") or "")
    if bool(quality.get("body_supplemented")):
        return True
    return not bool(quality.get("needs_body_copy")) and status != "보강 필요"


def compact_recent_public_ir_sec_entry(entry: dict, target_terms: dict) -> dict | None:
    entry_date = str(entry.get("date") or "")[:10]
    if not entry_date:
        return None
    tags = [str(tag) for tag in (entry.get("tags") or []) if isinstance(tag, str)]
    text = " ".join(
        str(entry.get(key) or "")
        for key in [
            "title",
            "summary",
            "source_url",
            "final_url",
            "file_name",
            "relative_path",
            "type",
            "source_type",
            "source_provider",
            "source_category",
            "filing_form",
            "filing_group",
        ]
    )
    text += " " + " ".join(tags)
    related_targets: list[str] = []
    matched_ticker = ""
    ticker_names = target_terms.get("ticker_names") or {}
    entry_ticker = _normalize_ticker(entry.get("ticker"))
    ticker_set = target_terms.get("ticker_set") or set(target_terms.get("tickers") or [])
    if entry_ticker and entry_ticker in ticker_set:
        related_targets.append(ticker_names.get(entry_ticker) or entry_ticker)
        matched_ticker = entry_ticker
    for ticker in target_terms.get("tickers") or []:
        if ticker and ticker in text and (ticker_names.get(ticker) or ticker) not in related_targets:
            related_targets.append(ticker_names.get(ticker) or ticker)
            matched_ticker = matched_ticker or ticker
    name_to_ticker = {str(name): str(ticker) for ticker, name in ticker_names.items() if name}
    for name in target_terms.get("names") or []:
        if name and name in text and name not in related_targets:
            related_targets.append(name)
            matched_ticker = matched_ticker or _normalize_ticker(name_to_ticker.get(name, ""))
    for sector in target_terms.get("sectors") or []:
        if sector and sector in text and sector not in related_targets:
            related_targets.append(sector)
    if not related_targets:
        return None
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    usable = public_ir_sec_entry_is_usable_for_recommendation(entry)
    source_url = str(entry.get("source_url") or entry.get("final_url") or "")
    provider = str(entry.get("source_provider") or _provider_from_public_ir_url(source_url)).strip()
    filing_form = str(entry.get("filing_form") or "").strip()
    source_category = str(entry.get("source_category") or "").strip()
    if "SEC" in provider.upper() and filing_form:
        reliability_label = f"공식 SEC {filing_form}"
    elif source_category:
        reliability_label = source_category
    elif usable:
        reliability_label = "본문 추출 완료"
    else:
        reliability_label = "URL-only 보강 필요"
    return {
        "category": "public_ir_sec",
        "date": entry_date,
        "ticker": matched_ticker,
        "title": entry.get("title") or entry.get("file_name") or "공개 IR/SEC 자료",
        "company": ticker_names.get(matched_ticker) or related_targets[0],
        "company_name": ticker_names.get(matched_ticker) or related_targets[0],
        "report_type": "public-ir-sec",
        "source_type": entry.get("source_type") or "public_ir_sec",
        "source_provider": provider,
        "source_category": source_category,
        "filing_form": filing_form,
        "filing_group": entry.get("filing_group") or "",
        "source_reliability": reliability_label,
        "summary": entry.get("summary") or entry.get("title") or entry.get("file_name") or "공개 IR/SEC 자료",
        "relative_path": entry.get("relative_path"),
        "source_url": source_url,
        "related_targets": related_targets,
        "tags": tags[:12],
        "quality_status": quality.get("status") or entry.get("capture_quality_status") or "품질 미확인",
        "needs_body_copy": bool(quality.get("needs_body_copy")) and not usable,
        "usable_for_recommendation": usable,
        "recommendation_guard": "추천 가산 가능" if usable else "본문 보강 전 추천 점수 가산 제외",
    }


def recent_weekly_source_family(provider: str) -> str:
    original = str(provider or "").strip()
    if not original:
        return "출처 미확인"
    value = sub(r"^https?://", "", original.strip().lower()).split("/")[0].split(":")[0].strip(".")
    if "." not in value:
        return original
    if value.startswith("www."):
        value = value[4:]
    labels = [label for label in value.split(".") if label]
    if len(labels) >= 3 and labels[-1] == "kr" and labels[-2] in {"co", "or", "go", "ac", "ne", "re", "pe"}:
        return ".".join(labels[-3:])
    if len(labels) >= 3 and all(fullmatch(r"[a-z0-9-]+", label) for label in labels):
        return ".".join(labels[-2:])
    return value or original


def recent_weekly_category_group(label: str, key: str, items: list[dict], *, limit: int = 8, note: str = "") -> dict:
    all_items = list(items or [])
    visible_items = all_items[: max(1, limit)]
    target_names: set[str] = set()
    usable_count = 0
    needs_body_count = 0
    recommendation_link_count = 0
    latest_recommendation_link_count = 0
    quality_statuses: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    source_family_counts: dict[str, int] = {}
    filing_form_counts: dict[str, int] = {}
    reliability_counts: dict[str, int] = {}
    tickers: set[str] = set()
    for item in all_items:
        related_targets = item.get("related_targets") if isinstance(item, dict) else []
        if isinstance(related_targets, list):
            for target in related_targets[:3]:
                if target:
                    target_names.add(str(target))
        company_name = item.get("company_name") if isinstance(item, dict) else ""
        if company_name:
            target_names.add(str(company_name))
        ticker = _normalize_ticker(str(item.get("ticker") or "")) if isinstance(item, dict) else ""
        if ticker:
            tickers.add(ticker)
    quality_items = [item for item in all_items if isinstance(item, dict)]
    for item in quality_items:
        if item.get("usable_for_recommendation"):
            usable_count += 1
        if item.get("needs_body_copy"):
            needs_body_count += 1
        if item.get("used_in_recommendation"):
            recommendation_link_count += 1
        if item.get("used_in_latest_recommendation"):
            latest_recommendation_link_count += 1
        quality_status = str(item.get("quality_status") or item.get("recommendation_guard") or "").strip()
        if quality_status:
            quality_statuses[quality_status] = quality_statuses.get(quality_status, 0) + 1
        if key == "public_ir_sec":
            provider = str(item.get("source_provider") or "출처 미확인").strip()
            if provider:
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
                source_family = recent_weekly_source_family(provider)
                source_family_counts[source_family] = source_family_counts.get(source_family, 0) + 1
            filing_form = str(item.get("filing_form") or "").strip()
            if filing_form:
                filing_form_counts[filing_form] = filing_form_counts.get(filing_form, 0) + 1
            reliability = str(item.get("source_reliability") or item.get("source_category") or "").strip()
            if reliability:
                reliability_counts[reliability] = reliability_counts.get(reliability, 0) + 1
    quality_summary = {
        "total_count": len(quality_items),
        "visible_count": len(visible_items),
        "usable_for_recommendation": usable_count,
        "needs_body_copy": needs_body_count,
        "blocked_or_needs_review": max(0, len(quality_items) - usable_count) if key == "public_ir_sec" else 0,
        "recommendation_evidence_linked": recommendation_link_count,
        "latest_recommendation_evidence_linked": latest_recommendation_link_count,
        "statuses": quality_statuses,
        "providers": dict(sorted(provider_counts.items(), key=lambda item: (-item[1], item[0]))[:8]),
        "source_families": dict(sorted(source_family_counts.items(), key=lambda item: (-item[1], item[0]))[:8]),
        "filing_forms": dict(sorted(filing_form_counts.items(), key=lambda item: (-item[1], item[0]))[:8]),
        "reliability_labels": dict(sorted(reliability_counts.items(), key=lambda item: (-item[1], item[0]))[:8]),
    }
    return {
        "key": key,
        "label": label,
        "count": len(all_items),
        "visible_count": len(visible_items),
        "target_count": len(target_names),
        "target_names": sorted(target_names)[:8],
        "ticker_count": len(tickers),
        "tickers": sorted(tickers),
        "quality_summary": quality_summary,
        "note": note,
        "items": visible_items,
    }


def build_recent_weekly_category_groups(
    *,
    ownership_filings: list[dict],
    important_filings: list[dict],
    display_reports: list[dict],
    public_ir_sec_items: list[dict],
    customs_exports: list[dict],
    market_context: list[dict],
) -> list[dict]:
    non_ownership_filings = [
        item for item in important_filings if item not in ownership_filings
    ]
    return [
        recent_weekly_category_group(
            "수급/대량보유",
            "ownership_filings",
            ownership_filings,
            note="국민연금, 주요주주, 대량보유 변동처럼 수급 판단에 직접 쓰는 공시입니다.",
        ),
        recent_weekly_category_group(
            "중요 공시",
            "important_filings",
            non_ownership_filings or important_filings,
            note="실적, 주요 계약, 증자, 경영 변화 등 투자 판단에 영향이 큰 공시입니다.",
        ),
        recent_weekly_category_group(
            "핵심 리포트",
            "display_reports",
            display_reports,
            note="보유/관심 종목과 연결된 증권사 및 기관 리포트입니다.",
        ),
        recent_weekly_category_group(
            "공개 IR/SEC",
            "public_ir_sec",
            public_ir_sec_items,
            note="상장사 IR, SEC, 공개 보도자료 중 최근 1주 추천 근거로 연결 가능한 자료입니다.",
        ),
        recent_weekly_category_group(
            "수출입",
            "customs_exports",
            customs_exports,
            note="관세청 등 실제 수치가 확인된 수출입 자료입니다.",
        ),
        recent_weekly_category_group(
            "시장/매크로",
            "market_context",
            market_context,
            note="시장일지와 추천 판단의 배경으로 쓰는 공통 자료입니다.",
        ),
    ]


def build_recent_weekly_target_digest(*, sources: list[tuple[str, list[dict]]], limit: int = 20) -> list[dict]:
    digest: dict[str, dict] = {}
    for bucket, items in sources:
        for item in items or []:
            if not isinstance(item, dict):
                continue
            raw_targets = item.get("related_targets") if isinstance(item.get("related_targets"), list) else []
            targets = [str(target).strip() for target in raw_targets if str(target or "").strip()]
            company_name = str(item.get("company_name") or "").strip()
            if not targets and company_name:
                targets = [company_name]
            if not targets:
                targets = ["시장/섹터 공통"]
            for target in targets[:3]:
                current = digest.setdefault(
                    target,
                    {
                        "target": target,
                        "filing": 0,
                        "report": 0,
                        "public_ir_sec": 0,
                        "customs": 0,
                        "market": 0,
                        "recommendation_evidence_linked": 0,
                        "latest_recommendation_evidence_linked": 0,
                        "total": 0,
                    },
                )
                if bucket in current:
                    current[bucket] += 1
                if item.get("used_in_recommendation"):
                    current["recommendation_evidence_linked"] += 1
                if item.get("used_in_latest_recommendation"):
                    current["latest_recommendation_evidence_linked"] += 1
                current["total"] += 1
    return sorted(
        digest.values(),
        key=lambda item: (-int(item.get("total") or 0), str(item.get("target") or "")),
    )[: max(1, limit)]
