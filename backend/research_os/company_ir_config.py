from __future__ import annotations

import json
import re
from typing import Callable, Iterable


def _clean_ir_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def source_from_mapping(item: dict, index: int, source_factory: Callable[..., object]) -> object | None:
    source_url = _clean_ir_text(item.get("source_url") or item.get("url"))
    ticker = _clean_ir_text(item.get("ticker") or item.get("target_key")).upper()
    company_name = _clean_ir_text(item.get("company_name") or item.get("company") or ticker)
    if not source_url or not ticker or not source_url.startswith(("http://", "https://")):
        return None
    source_key = _clean_ir_text(item.get("source_key") or item.get("key"))
    if not source_key:
        source_key = re.sub(r"[^a-z0-9_]+", "_", f"{ticker.lower()}_ir_{index}").strip("_")
    provider = _clean_ir_text(item.get("provider") or f"{company_name} IR")
    source_scope = _clean_ir_text(item.get("source_scope") or "company_ir_press_releases")
    return source_factory(
        source_key=source_key,
        ticker=ticker,
        company_name=company_name,
        provider=provider,
        source_url=source_url,
        source_scope=source_scope,
    )


def configured_company_ir_sources(
    base_sources: Iterable[object],
    config_json: str | None,
    source_factory: Callable[..., object],
) -> list[object]:
    sources = list(base_sources)
    text = _clean_ir_text(config_json)
    if not text:
        return sources
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return sources
    if isinstance(payload, dict):
        payload = payload.get("sources") or []
    if not isinstance(payload, list):
        return sources
    seen = {(source.ticker, source.source_url) for source in sources}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        source = source_from_mapping(item, index, source_factory)
        if not source or (source.ticker, source.source_url) in seen:
            continue
        seen.add((source.ticker, source.source_url))
        sources.append(source)
    return sources
