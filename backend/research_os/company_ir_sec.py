"""SEC company submissions parsing helpers for company IR sources."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Callable


SEC_INTERESTING_FORMS = {"8-K", "10-Q", "10-K", "20-F", "6-K", "SD", "SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A"}


def _clean_sec_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sec_cik_from_submissions_url(url: str) -> str:
    match = re.search(r"CIK0*(\d+)\.json", url or "", re.IGNORECASE)
    return match.group(1) if match else ""


def sec_archive_url(source, accession_number: str, primary_document: str) -> str:
    cik = sec_cik_from_submissions_url(source.source_url)
    accession = re.sub(r"[^0-9]", "", accession_number or "")
    document = _clean_sec_text(primary_document)
    if not cik or not accession or not document:
        return source.source_url
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"


def classify_sec_filing(form: str, description: str = "") -> tuple[str, str]:
    form_key = _clean_sec_text(form).upper()
    description_key = _clean_sec_text(description).lower()
    if form_key in {"10-Q", "10-K", "20-F"}:
        return "SEC 실적 공시", "financial_report"
    if form_key == "8-K" and any(
        keyword in description_key
        for keyword in ["financial result", "earnings", "press release", "exhibit 99.1", "results"]
    ):
        return "SEC 실적/보도자료", "financial_release"
    if form_key in {"SC 13G", "SC 13G/A", "SC 13D", "SC 13D/A"}:
        return "SEC 지분 공시", "ownership_filing"
    if form_key == "6-K":
        return "SEC 해외발행사 공시", "foreign_issuer_filing"
    if form_key == "SD":
        return "SEC 공급망/지속가능 공시", "specialized_disclosure"
    return "SEC 중요 공시", "material_filing"


def parse_sec_company_submissions(
    payload: dict | str,
    *,
    source,
    item_factory: Callable[..., object],
    item_id_factory: Callable[[object, str, str, str], str],
    normalize_date: Callable[[str | None], str],
    limit: int = 30,
) -> list[dict]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict):
        return []
    recent = ((payload.get("filings") or {}).get("recent") or {}) if isinstance(payload.get("filings"), dict) else {}
    forms = list(recent.get("form") or [])
    filing_dates = list(recent.get("filingDate") or [])
    report_dates = list(recent.get("reportDate") or [])
    accessions = list(recent.get("accessionNumber") or [])
    documents = list(recent.get("primaryDocument") or [])
    descriptions = list(recent.get("primaryDocDescription") or [])
    items: list[object] = []
    seen: set[str] = set()
    for index, form_value in enumerate(forms):
        form = _clean_sec_text(form_value).upper()
        if form not in SEC_INTERESTING_FORMS:
            continue
        filing_date = _clean_sec_text(filing_dates[index] if index < len(filing_dates) else "")
        report_date = _clean_sec_text(report_dates[index] if index < len(report_dates) else "")
        accession = _clean_sec_text(accessions[index] if index < len(accessions) else "")
        document = _clean_sec_text(documents[index] if index < len(documents) else "")
        description = _clean_sec_text(descriptions[index] if index < len(descriptions) else "")
        title_detail = description if description and description.upper() != form else "SEC filing"
        title = f"{source.company_name} {form} {title_detail}"
        filing_category, filing_group = classify_sec_filing(form, title_detail)
        detail_url = sec_archive_url(source, accession, document)
        published_at = normalize_date(filing_date) or filing_date or normalize_date(report_date) or report_date
        item_id = item_id_factory(source, title, published_at, detail_url)
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append(
            item_factory(
                item_id=item_id,
                ticker=source.ticker,
                company_name=source.company_name,
                title=title,
                source_provider=source.provider,
                source_scope=source.source_scope,
                published_at=published_at,
                detail_url=detail_url,
                source_url=source.source_url,
                category=filing_category,
                filing_form=form,
                filing_group=filing_group,
            )
        )
        if len(items) >= max(1, limit):
            break
    return [asdict(item) for item in items]
