"""Shared utility helpers for data provider adapters."""

from __future__ import annotations

from datetime import datetime, timezone
import re


def _is_configured_secret(value: str) -> bool:
    return bool(value and value.strip() and value.strip() != "********")


def _provider_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_value(row: dict, keys: list[str]) -> object | None:
    normalized = {
        str(key).strip().lower().replace(" ", "").replace("_", ""): value
        for key, value in row.items()
    }
    for key in keys:
        wanted = key.strip().lower().replace(" ", "").replace("_", "")
        if wanted in normalized and normalized[wanted] not in (None, ""):
            return normalized[wanted]
    return None


def _parse_float_value(value: object | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "").replace("▲", "").replace("▼", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_korean_stock_code(value: str) -> str:
    text = str(value or "").strip().upper()
    text = text.removesuffix(".KS").removesuffix(".KQ")
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits and len(digits) <= 6 else text


def _compact_company_name(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or "").lower())
    for suffix in ["주식회사", "(주)", "㈜", "보통주", "우선주", "corporation", "corp.", "corp", "inc.", "inc"]:
        text = text.replace(suffix.lower(), "")
    return text


def _format_ratio(numerator: float | int | None, denominator: float | int | None) -> str:
    if not numerator or not denominator:
        return "n/a"
    return f"{(numerator / denominator):.1%}"


def _safe_provider_error(error: Exception) -> str:
    text = str(error)
    if "apikey=" in text:
        text = text.split("apikey=", 1)[0] + "apikey=****"
    if "serviceKey=" in text:
        text = text.split("serviceKey=", 1)[0] + "serviceKey=****"
    if "402" in text or "Payment Required" in text:
        if "financialdatasets" in text.lower():
            return (
                "Financial Datasets API의 현재 플랜/쿼터 제한(402 Payment Required)입니다. "
                "해당 데이터는 합성하지 않고 경고로만 표시합니다."
            )
        return (
            "FMP 무료 플랜 제한(402 Payment Required)입니다. "
            "유료 업그레이드는 사용하지 않고, 가격 데이터는 KIS로 대체하는 구성이 권장됩니다."
        )
    return text
