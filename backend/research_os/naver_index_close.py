"""Structured Naver Finance KOSPI/KOSDAQ close snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from research_os.settings import Settings


NAVER_KOREA_INDEX_CODES = ("KOSPI", "KOSDAQ")


def _snapshot_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def fetch_naver_korea_index_close_report(settings: Settings) -> dict | None:
    """Return a verified, closed-market snapshot suitable for the KR journal."""
    if not settings.naver_finance_enabled:
        return None
    base_url = settings.naver_finance_base_url.rstrip("/")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
    indices: list[dict] = []
    with httpx.Client(
        timeout=settings.naver_finance_timeout_seconds,
        headers=headers,
        trust_env=False,
    ) as client:
        for code in NAVER_KOREA_INDEX_CODES:
            source_url = f"{base_url}/api/index/{code}/basic"
            response = client.get(source_url)
            response.raise_for_status()
            payload = response.json()
            traded_at = payload.get("localTradedAt")
            traded_date = _snapshot_date(traded_at)
            if str(payload.get("marketStatus") or "").upper() != "CLOSE" or not traded_date:
                return None
            direction = (payload.get("compareToPreviousPrice") or {}).get("text") or "미확인"
            indices.append(
                {
                    "code": code,
                    "name": payload.get("stockName") or code,
                    "close_price": payload.get("closePrice"),
                    "change": payload.get("compareToPreviousClosePrice"),
                    "change_ratio": payload.get("fluctuationsRatio"),
                    "direction": direction,
                    "market_status": "CLOSE",
                    "local_traded_at": traded_at,
                    "traded_date": traded_date,
                    "source_url": source_url,
                }
            )
    if len(indices) != len(NAVER_KOREA_INDEX_CODES):
        return None
    published_at = max(str(item["traded_date"]) for item in indices)
    snippets = [
        (
            f"{item['name']} {item.get('close_price') or '미확인'}p, "
            f"전일 대비 {item.get('change') or '미확인'} "
            f"({item.get('change_ratio') or '미확인'}%), {item['direction']}"
        )
        for item in indices
    ]
    return {
        "item_id": f"naver-index-close-{published_at}",
        "title": "네이버 증권 KOSPI·KOSDAQ 장 마감 스냅샷",
        "broker": "네이버 증권",
        "provider": "Naver Finance",
        "category": "시황정보",
        "published_at": published_at,
        "url": f"{base_url}/domestic/index/KOSPI/total",
        "source_urls": [item["source_url"] for item in indices],
        "source_kind": "official_index_close_snapshot",
        "indices": indices,
        "source_analysis": {
            "status": "verified_close",
            "snippets": snippets,
            "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    }


def render_naver_korea_index_lines(report: dict | None) -> list[str]:
    if not report:
        return []
    return [
        (
            f"{item.get('name') or item.get('code')}: {item.get('close_price') or 'n/a'}p "
            f"({item.get('change') or 'n/a'}, {item.get('change_ratio') or 'n/a'}%, "
            f"{item.get('direction') or 'n/a'}, {item.get('market_status') or 'n/a'}, "
            f"{item.get('local_traded_at') or 'n/a'})"
        )
        for item in report.get("indices") or []
    ]
