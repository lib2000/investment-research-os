"""Recent weekly activity grouping helpers."""

from __future__ import annotations

from re import fullmatch, sub


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


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