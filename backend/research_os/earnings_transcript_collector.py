"""Earnings transcript payload helpers for Market Signal Graph."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse


DESIGN_NAME = "earnings_transcript_collector_v1"
SOURCE_PLATFORM = "earnings_transcript"
SOURCE_KIND = "earnings_transcript"
CHANNEL = "web"
COLLECTOR = "firecrawl"
TARGET_TYPE = "earnings_call_transcript"


@dataclass(frozen=True)
class EarningsTranscriptInput:
    company: str
    ticker: str
    raw_url: str
    resolved_url: str | None = None
    title: str | None = None
    transcript_text: str | None = None
    fiscal_period: str | None = None
    event_date: str | None = None
    speaker_count: int | None = None
    language: str = "en"
    published_at: str | None = None


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_ticker(value: Any) -> str:
    return _safe_text(value).upper()


def _safe_company(value: Any, ticker: str) -> str:
    return _safe_text(value) or ticker or "company"


def _safe_url(raw_url: str, resolved_url: str | None = None) -> str:
    candidate = str(resolved_url or raw_url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Earnings transcript payload requires a public http/https URL.")
    return candidate


def normalize_transcript_text(value: Any, *, max_chars: int = 2400) -> str:
    compact = " ".join(str(value or "").replace("\r", "\n").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rstrip() + "..."


def _payload_containers(item: dict[str, Any]) -> list[dict[str, Any]]:
    containers = [item]
    for key in ("data", "scrape", "firecrawl", "result", "transcript"):
        nested = _dict_value(item.get(key))
        if nested:
            containers.append(nested)
    return containers


def _metadata(containers: list[dict[str, Any]]) -> dict[str, Any]:
    for container in containers:
        metadata = _dict_value(container.get("metadata"))
        if metadata:
            return metadata
    return {}


def _coerce_transcript_input(item: dict[str, Any]) -> EarningsTranscriptInput:
    containers = _payload_containers(item)
    metadata = _metadata(containers)
    transcript_text = _first_non_empty(
        item.get("transcript_text"),
        item.get("text"),
        item.get("markdown"),
        *(container.get("transcript_text") for container in containers),
        *(container.get("text") for container in containers),
        *(container.get("markdown") for container in containers),
    )
    raw_url = _first_non_empty(
        item.get("raw_url"),
        item.get("source_url"),
        item.get("url"),
        metadata.get("sourceURL"),
        metadata.get("sourceUrl"),
        metadata.get("url"),
    )
    resolved_url = _first_non_empty(
        item.get("resolved_url"),
        item.get("final_url"),
        item.get("resolvedURL"),
        metadata.get("sourceURL"),
        metadata.get("sourceUrl"),
        metadata.get("url"),
    )
    return EarningsTranscriptInput(
        company=str(_first_non_empty(item.get("company"), metadata.get("company")) or ""),
        ticker=str(_first_non_empty(item.get("ticker"), metadata.get("ticker"), metadata.get("symbol")) or ""),
        raw_url=str(raw_url or ""),
        resolved_url=resolved_url,
        title=_first_non_empty(item.get("title"), item.get("page_title"), metadata.get("title")),
        transcript_text=transcript_text,
        fiscal_period=_first_non_empty(item.get("fiscal_period"), item.get("quarter"), metadata.get("fiscalPeriod")),
        event_date=_first_non_empty(item.get("event_date"), item.get("earnings_date"), metadata.get("eventDate")),
        speaker_count=item.get("speaker_count") if item.get("speaker_count") is not None else metadata.get("speakerCount"),
        language=str(_first_non_empty(item.get("language"), metadata.get("language")) or "en"),
        published_at=_first_non_empty(item.get("published_at"), metadata.get("publishedTime")),
    )


def build_earnings_transcript_signal_payload(item: EarningsTranscriptInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, dict):
        item = _coerce_transcript_input(item)
    ticker = _safe_ticker(item.ticker)
    company = _safe_company(item.company, ticker)
    raw_url = str(item.raw_url or "").strip()
    resolved_url = _safe_url(raw_url, item.resolved_url)
    fiscal_period = _safe_text(item.fiscal_period)
    event_date = _safe_text(item.event_date)
    title = _safe_text(item.title) or f"{company} earnings call transcript"
    normalized_text = normalize_transcript_text(item.transcript_text)
    if not normalized_text:
        normalized_text = f"{company} earnings call transcript captured for {fiscal_period or event_date or 'latest period'}."
    external_id = sha256_hex(f"{resolved_url}|{fiscal_period}|{event_date}")
    canonical_hash = sha256_hex(f"{SOURCE_PLATFORM}{resolved_url}{title}{event_date}")
    return {
        "source_name": f"{company}_earnings_transcript",
        "source_platform": SOURCE_PLATFORM,
        "source_kind": SOURCE_KIND,
        "channel": CHANNEL,
        "external_id": external_id,
        "url": resolved_url,
        "title": title,
        "text": normalized_text,
        "author": f"{company} earnings call",
        "language": item.language or "en",
        "canonical_hash": canonical_hash,
        "metadata": {
            "collector": COLLECTOR,
            "collector_design": DESIGN_NAME,
            "target_type": TARGET_TYPE,
            "company": company,
            "ticker": ticker,
            "page_type": "earnings_call_transcript",
            "fiscal_period": fiscal_period,
            "event_date": event_date,
            "speaker_count": item.speaker_count,
            "raw_url": raw_url or resolved_url,
            "resolved_url": resolved_url,
            "content_chars": len(normalized_text),
        },
        "published_at": item.published_at or event_date or "",
        "needs_enrichment": True,
        "analysis_status": "pending",
    }


def normalize_earnings_transcript_inputs(data: Any) -> list[EarningsTranscriptInput | dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "sources", "results", "payloads", "transcripts"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def build_earnings_transcript_batch_result(items: list[EarningsTranscriptInput | dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        try:
            payload = build_earnings_transcript_signal_payload(item)
            errors: list[str] = []
        except Exception as exc:
            payload = None
            errors = [str(exc)]
        results.append({"index": index, "status": "valid" if payload else "failed", "payload": payload, "errors": errors})
    failed_count = sum(1 for item in results if item["status"] == "failed")
    return {
        "status": "failed" if failed_count else "success",
        "design": DESIGN_NAME,
        "source_platform": SOURCE_PLATFORM,
        "item_count": len(items),
        "valid_count": len(items) - failed_count,
        "failed_count": failed_count,
        "results": results,
    }
