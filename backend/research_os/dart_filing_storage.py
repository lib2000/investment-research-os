"""Storage helpers for DART filing watch reports."""

from __future__ import annotations

from datetime import date, datetime


def save_dart_filing_watch_item(runtime, *, ticker: str, filing: dict, settings):
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    importance, action, tags = runtime.dart_filing_importance(str(filing.get("report_name") or ""))
    markdown = runtime.render_dart_filing_markdown(ticker, filing, importance, action)
    receipt_date_text = str(filing.get("receipt_date") or "")
    try:
        report_date = datetime.strptime(receipt_date_text, "%Y%m%d").date()
    except ValueError:
        report_date = date.today()
    payload = {
        "module": "dart_filing_watch",
        "ticker": ticker,
        "filing": filing,
        "importance": importance,
        "action": action,
        "tags": tags,
    }
    summary = f"{filing.get('corp_name') or ticker} DART 신규 공시: {filing.get('report_name') or '공시명 미확인'}"
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="dart-filing-watch",
        markdown=markdown,
        structured_payload=payload,
        manifest_entry=runtime.manifest_with_ticker_verification(
            ticker,
            {
                "module": "dart_filing_watch",
                "summary": summary,
                "source_type": "official_filing",
                "source_url": filing.get("source_url"),
                "confidence": 0.96,
                "importance": importance,
                "tags": tags,
                "rcept_no": filing.get("rcept_no"),
            },
        ),
        report_date=report_date,
        file_suffix=str(filing.get("rcept_no") or ""),
        # A DART receipt number is immutable. Force-refreshing the same filing
        # must update its canonical local record rather than add a sequence copy.
        overwrite_existing=True,
    )
    runtime.upsert_research_memory_document(
        vault_dir=vault_dir,
        entry={
            "ticker": ticker,
            "type": "dart-filing-watch",
            "date": report_date.isoformat(),
            "file_name": storage.file_name,
            "relative_path": storage.relative_path,
            "summary": summary,
            "source_type": "official_filing",
            "tags": tags,
        },
        full_text=markdown,
    )
    return storage
