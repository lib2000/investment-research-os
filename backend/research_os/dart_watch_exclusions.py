from __future__ import annotations


def dart_watch_exclusion_reason(item: dict | None) -> str | None:
    if not isinstance(item, dict):
        return None
    verification = item.get("verification")
    tags = item.get("tags") or []
    if (
        isinstance(verification, dict)
        and not verification.get("verified")
        and (
            "verification_pending" in tags
            or verification.get("verification_source") == "save_first_pending_verification"
        )
    ):
        return "verification_pending"
    text_parts = [
        item.get("name"),
        item.get("company_name"),
        item.get("display_name"),
        item.get("sector"),
        " ".join(str(tag) for tag in (item.get("theme_tags") or [])),
    ]
    text = " ".join(str(part or "") for part in text_parts).upper()
    if "ETF" in text or "ETN" in text or "상장지수" in text:
        return "etf_not_dart_corp"
    return None


def dart_excluded_ticker_entry(ticker: str, source: str, reason: str, item: dict | None = None) -> dict:
    name = ""
    if isinstance(item, dict):
        name = str(item.get("name") or item.get("company_name") or item.get("display_name") or "").strip()
    messages = {
        "non_kr_ticker": "국내 6자리 종목코드가 아니어서 DART 법인 공시 감시에서 제외했습니다.",
        "etf_not_dart_corp": "ETF/ETN/펀드는 OpenDART 법인 corp_code 대상이 아니어서 감시에서 제외했습니다.",
        "verification_pending": "공식 티커 인증이 끝나지 않아 DART 법인 공시 감시에서 제외했습니다.",
    }
    return {
        "ticker": ticker,
        "name": name or None,
        "source": source,
        "reason": reason,
        "message": messages.get(reason, "DART 법인 공시 감시 대상이 아니어서 제외했습니다."),
    }


def append_unique_dart_exclusion(runtime, excluded_tickers: list[dict], entry: dict) -> None:
    key = (
        runtime.normalize_ticker(str(entry.get("ticker") or "")),
        str(entry.get("source") or ""),
        str(entry.get("reason") or ""),
    )
    for existing in excluded_tickers:
        existing_key = (
            runtime.normalize_ticker(str(existing.get("ticker") or "")),
            str(existing.get("source") or ""),
            str(existing.get("reason") or ""),
        )
        if existing_key == key:
            if not existing.get("name") and entry.get("name"):
                existing["name"] = entry.get("name")
            return
    excluded_tickers.append(entry)
