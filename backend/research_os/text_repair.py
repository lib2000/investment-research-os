"""Text repair helpers for cached logs and payloads."""

from __future__ import annotations


def repair_mojibake_log_line(value: str) -> str:
    text = str(value or "")
    if not text or not any(marker in text for marker in ("Ã", "Â", "ì", "ê", "ë", "í", "\x80", "\x81")):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except Exception:
        return text
    hangul_count = sum(1 for char in repaired if "\uac00" <= char <= "\ud7a3")
    original_hangul_count = sum(1 for char in text if "\uac00" <= char <= "\ud7a3")
    return repaired if hangul_count > original_hangul_count else text


def repair_mojibake_payload(value):
    if isinstance(value, str):
        return repair_mojibake_log_line(value)
    if isinstance(value, list):
        return [repair_mojibake_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_mojibake_payload(item) for key, item in value.items()}
    return value
