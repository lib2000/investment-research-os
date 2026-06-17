"""Recent weekly public IR/SEC compaction helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def provider_from_public_ir_url(source_url: object) -> str:
    text = str(source_url or "").strip()
    parsed = urlparse(text)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return "공개 IR/SEC"
    if host.endswith("sec.gov"):
        return "SEC EDGAR"
    return host[4:] if host.startswith("www.") else host

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
    entry_ticker = normalize_ticker(entry.get("ticker"))
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
            matched_ticker = matched_ticker or normalize_ticker(name_to_ticker.get(name, ""))
    for sector in target_terms.get("sectors") or []:
        if sector and sector in text and sector not in related_targets:
            related_targets.append(sector)
    if not related_targets:
        return None
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    usable = public_ir_sec_entry_is_usable_for_recommendation(entry)
    source_url = str(entry.get("source_url") or entry.get("final_url") or "")
    provider = str(entry.get("source_provider") or provider_from_public_ir_url(source_url)).strip()
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
