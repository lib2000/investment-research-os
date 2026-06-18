"""Firecrawl IR collector payload and Market Signal Graph RPC helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

import httpx


DESIGN_NAME = "firecrawl_ir_collector_v1"
SOURCE_PLATFORM = "firecrawl_ir"
SOURCE_KIND = "ir"
CHANNEL = "web"
COLLECTOR = "firecrawl"
TARGET_TYPE = "company_ir"


@dataclass(frozen=True)
class FirecrawlIrInput:
    company: str
    ticker: str
    raw_url: str
    resolved_url: str | None = None
    page_title: str | None = None
    markdown: str | None = None
    text: str | None = None
    author: str | None = None
    language: str = "en"
    published_at: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def normalize_ir_markdown(value: str | None, *, max_chars: int = 1400) -> str:
    compact = " ".join(str(value or "").replace("\r", "\n").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rstrip() + "..."


def _safe_company(value: str, ticker: str) -> str:
    company = " ".join(str(value or "").split())
    return company or str(ticker or "").strip().upper() or "company"


def _safe_ticker(value: str) -> str:
    return str(value or "").strip().upper()


def _safe_url(raw_url: str, resolved_url: str | None = None) -> str:
    candidate = str(resolved_url or raw_url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Firecrawl IR payload requires a public http/https URL.")
    return candidate


def _safe_title(value: str | None, company: str) -> str:
    title = " ".join(str(value or "").split())
    return title[:180] or f"{company} Investor Relations"


def build_firecrawl_ir_signal_payload(item: FirecrawlIrInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, dict):
        item = FirecrawlIrInput(
            company=str(item.get("company") or ""),
            ticker=str(item.get("ticker") or ""),
            raw_url=str(item.get("raw_url") or item.get("url") or ""),
            resolved_url=item.get("resolved_url") or item.get("final_url"),
            page_title=item.get("page_title") or item.get("title"),
            markdown=item.get("markdown"),
            text=item.get("text"),
            author=item.get("author"),
            language=str(item.get("language") or "en"),
            published_at=item.get("published_at"),
        )
    ticker = _safe_ticker(item.ticker)
    company = _safe_company(item.company, ticker)
    raw_url = str(item.raw_url or "").strip()
    resolved_url = _safe_url(raw_url, item.resolved_url)
    title = _safe_title(item.page_title, company)
    summary_source = item.text if item.text is not None else item.markdown
    normalized_text = normalize_ir_markdown(summary_source)
    if not normalized_text:
        normalized_text = f"{company} Investor Relations page captured by Firecrawl."
    external_id = sha256_hex(resolved_url)
    canonical_hash = sha256_hex(f"{SOURCE_PLATFORM}{resolved_url}{title}")
    return {
        "source_name": f"{company}_ir",
        "source_platform": SOURCE_PLATFORM,
        "source_kind": SOURCE_KIND,
        "channel": CHANNEL,
        "external_id": external_id,
        "url": resolved_url,
        "title": title,
        "text": normalized_text,
        "author": item.author or f"{company} Investor Relations",
        "language": item.language or "en",
        "canonical_hash": canonical_hash,
        "metadata": {
            "collector": COLLECTOR,
            "collector_design": DESIGN_NAME,
            "target_type": TARGET_TYPE,
            "company": company,
            "ticker": ticker,
            "page_type": "investor_relations",
            "raw_url": raw_url or resolved_url,
            "resolved_url": resolved_url,
            "content_chars": len(normalized_text),
        },
        "published_at": item.published_at or "",
        "needs_enrichment": True,
        "analysis_status": "pending",
    }


def upsert_external_signal_payload(
    payload: dict[str, Any],
    *,
    rpc_url: str,
    service_role_key: str,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    if not rpc_url:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_rpc_url_missing",
            "design": DESIGN_NAME,
        }
    if not service_role_key:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_service_role_key_missing",
            "design": DESIGN_NAME,
        }
    headers = {
        "apikey": service_role_key,
        "authorization": f"Bearer {service_role_key}",
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(rpc_url, headers=headers, json={"payload": payload})
        if response.status_code in {200, 201, 204}:
            data: Any = None
            if response.content:
                try:
                    data = response.json()
                except ValueError:
                    data = response.text[:500]
            return {
                "status": "success",
                "design": DESIGN_NAME,
                "http_status": response.status_code,
                "result": data,
            }
        lowered = response.text.lower()
        reason = "supabase_project_paused" if "paused" in lowered or "inactive" in lowered else "rpc_error"
        return {
            "status": "skipped" if reason == "supabase_project_paused" else "failed",
            "reason": reason,
            "design": DESIGN_NAME,
            "http_status": response.status_code,
            "message": response.text[:500],
        }
    except httpx.RequestError as exc:
        return {
            "status": "skipped",
            "reason": "market_signal_graph_unreachable",
            "design": DESIGN_NAME,
            "message": str(exc)[:500],
        }


def build_firecrawl_ir_collection_result(
    item: FirecrawlIrInput | dict[str, Any],
    settings: Any,
    *,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    payload = build_firecrawl_ir_signal_payload(item)
    effective_dry_run = settings.firecrawl_ir_dry_run if dry_run is None else dry_run
    result = {
        "status": "dry_run" if effective_dry_run else "ready",
        "design": DESIGN_NAME,
        "source_platform": SOURCE_PLATFORM,
        "payload": payload,
        "rpc": None,
        "collected_at": _utc_now_iso(),
    }
    if effective_dry_run:
        return result
    result["rpc"] = upsert_external_signal_payload(
        payload,
        rpc_url=settings.market_signal_graph_rpc_url,
        service_role_key=settings.market_signal_graph_service_role_key,
        timeout_seconds=settings.market_signal_graph_timeout_seconds,
    )
    rpc_status = (result["rpc"] or {}).get("status")
    result["status"] = "success" if rpc_status == "success" else "skipped"
    return result
