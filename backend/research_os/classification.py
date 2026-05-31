"""Automatic research classification tag helpers."""

from __future__ import annotations

import re

DEFAULT_SPECIAL_RESEARCH_KEYS = {
    "INBOX",
    "MACRO",
    "SECTOR",
    "MARKET",
    "MARKET-US",
    "MARKET-KR",
    "MARKET-GLOBAL",
    "POLICY",
    "RATES",
    "FLOWS",
    "CUSTOMS",
}


def enum_or_str_value(value: object) -> str:
    return str(getattr(value, "value", value))


def merge_research_tags(*tag_groups: object) -> list[str]:
    tags: list[str] = []
    for group in tag_groups:
        if group is None:
            continue
        if isinstance(group, str):
            candidates = [group]
        elif isinstance(group, list | tuple | set):
            candidates = list(group)
        else:
            candidates = [group]
        for tag in candidates:
            cleaned = str(tag or "").strip()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
    return tags


def normalize_system_tag_value(value: object) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


def classification_system_tags(
    ticker: object,
    source_type: object | None = None,
    scope_reason: object | None = None,
    *,
    special_research_keys: set[str] | None = None,
) -> list[str]:
    tags: list[str] = []
    normalized_ticker = str(ticker or "").strip().upper()
    research_keys = special_research_keys or DEFAULT_SPECIAL_RESEARCH_KEYS
    if normalized_ticker in research_keys:
        tags.append(f"research_scope:{normalized_ticker.lower()}")
        if normalized_ticker.startswith("MARKET-"):
            tags.append("research_scope:market")
    if source_type is not None:
        source_value = normalize_system_tag_value(enum_or_str_value(source_type))
        if source_value:
            tags.append(f"source_type:{source_value}")
    reason_value = normalize_system_tag_value(scope_reason)
    if reason_value:
        tags.append(f"auto_scope:{reason_value}")
    return tags
