"""Recent activity compaction helpers for the research OS.

The FastAPI entrypoint still orchestrates the weekly brief, but small source-
specific compaction rules live here so scoring and UI payloads share the same
quality semantics.
"""

from __future__ import annotations


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def is_public_ir_sec_manifest_entry(entry: dict) -> bool:
    return (
        str(entry.get("scope") or "") == "public_ir_sec"
        or str(entry.get("ticker") or "").upper() == "PUBLIC_IR_SEC"
        or str(entry.get("type") or entry.get("report_type") or "") == "public-ir-sec"
    )


def public_ir_sec_entry_is_usable_for_recommendation(entry: dict) -> bool:
    quality = entry.get("capture_quality") if isinstance(entry.get("capture_quality"), dict) else {}
    status = str(quality.get("status") or entry.get("capture_quality_status") or "")
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
        ]
    )
    text += " " + " ".join(tags)
    related_targets: list[str] = []
    matched_ticker = ""
    ticker_names = target_terms.get("ticker_names") or {}
    for ticker in target_terms.get("tickers") or []:
        if ticker and ticker in text:
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
    return {
        "category": "public_ir_sec",
        "date": entry_date,
        "ticker": matched_ticker,
        "company_name": ticker_names.get(matched_ticker) or related_targets[0],
        "report_type": "public-ir-sec",
        "source_type": entry.get("source_type") or "public_ir_sec",
        "summary": entry.get("summary") or entry.get("title") or entry.get("file_name") or "공개 IR/SEC 자료",
        "relative_path": entry.get("relative_path"),
        "source_url": entry.get("source_url") or entry.get("final_url"),
        "related_targets": related_targets,
        "tags": tags[:12],
        "quality_status": quality.get("status") or entry.get("capture_quality_status") or "품질 미확인",
        "needs_body_copy": bool(quality.get("needs_body_copy")),
        "usable_for_recommendation": usable,
        "recommendation_guard": "추천 가산 가능" if usable else "본문 보강 전 추천 점수 가산 제외",
    }
