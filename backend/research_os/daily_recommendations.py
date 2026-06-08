"""Daily recommendation tracker for the research OS.

The module stays deliberately data-source agnostic. The FastAPI layer supplies
ranked candidates and price lookups, while this module owns stable storage,
record de-duplication, milestone tracking, and Korean-facing status text.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from re import search
from re import fullmatch
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings
from research_os.storage_quality import (
    is_archived_research_entry,
    storage_quality_entry_is_policy_url_only,
    storage_quality_entry_needs_body,
    storage_quality_entry_needs_ocr,
)


TRACKING_MILESTONES = [
    {"key": "7d", "label": "추천 후 1주일", "days": 7},
    {"key": "15d", "label": "추천 후 15일", "days": 15},
    {"key": "1m", "label": "추천 후 1달", "days": 30},
    {"key": "3m", "label": "추천 후 3달", "days": 90},
    {"key": "6m", "label": "추천 후 6달", "days": 180},
]


def daily_recommendation_store_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations.json"


def daily_recommendation_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations_state.json"


def current_recommendation_datetime() -> datetime:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return datetime.now().replace(microsecond=0)
    return datetime.now(korea_timezone).replace(microsecond=0)


def parse_daily_recommendations_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.daily_recommendations_time or "09:00").strip())
    if not match:
        return 9, 0
    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return hour, minute


def should_run_daily_recommendations(settings: Settings, now: datetime | None = None) -> bool:
    if not settings.daily_recommendations_enabled:
        return False
    now = now or current_recommendation_datetime()
    hour, minute = parse_daily_recommendations_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = read_json_payload(daily_recommendation_state_path(settings), {})
    return state.get("last_run_date") != now.date().isoformat()


def read_json_payload(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_daily_recommendation_store(settings: Settings) -> dict:
    return read_json_payload(
        daily_recommendation_store_path(settings),
        {
            "module": "daily_stock_recommendations",
            "records": [],
        },
    )


def write_daily_recommendation_store(settings: Settings, payload: dict) -> None:
    payload["module"] = "daily_stock_recommendations"
    write_json_payload(daily_recommendation_store_path(settings), payload)


def parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def recommendation_record_id(recommendation_date: date, rank: int, ticker: str) -> str:
    return f"{recommendation_date.isoformat()}-{rank:02d}-{str(ticker or '').upper()}"




def _normalize_evidence_relative_path(value: object) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("./").lower()


def daily_recommendation_evidence_link_index(settings: Settings, *, limit: int = 120) -> dict[str, Any]:
    """Index recommendation records by RAG evidence document path."""
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = str(store.get("latest_recommendation_date") or "")
    index: dict[str, list[dict[str, Any]]] = {}
    linked_record_ids: set[str] = set()
    linked_latest_record_ids: set[str] = set()
    for record in records[: max(1, limit)]:
        record_id = str(record.get("record_id") or "").strip()
        link = {
            "record_id": record_id,
            "recommendation_date": str(record.get("recommendation_date") or ""),
            "rank": record.get("rank"),
            "ticker": str(record.get("ticker") or "").strip(),
            "company_name": str(record.get("company_name") or "").strip(),
            "is_latest": bool(latest_date and record.get("recommendation_date") == latest_date),
        }
        for document in record.get("evidence_documents") or []:
            if not isinstance(document, dict):
                continue
            for field in ("source_relative_path", "json_relative_path"):
                key = _normalize_evidence_relative_path(document.get(field))
                if not key:
                    continue
                bucket = index.setdefault(key, [])
                if not any(existing.get("record_id") == record_id for existing in bucket):
                    bucket.append(link)
                if record_id:
                    linked_record_ids.add(record_id)
                    if link["is_latest"]:
                        linked_latest_record_ids.add(record_id)
    return {
        "latest_recommendation_date": latest_date,
        "by_relative_path": index,
        "linked_record_count": len(linked_record_ids),
        "latest_linked_record_count": len(linked_latest_record_ids),
    }

def normalize_evidence_documents(value: object, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        relative_path = str(item.get("source_relative_path") or item.get("relative_path") or "").strip()
        title = str(item.get("title") or item.get("source_file_name") or relative_path or "").strip()
        if not relative_path and not title:
            continue
        key = relative_path or title
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": title,
                "source_relative_path": relative_path,
                "source_date": str(item.get("source_date") or item.get("date") or "").strip(),
                "report_type": str(item.get("report_type") or "").strip(),
                "source_type": str(item.get("source_type") or "").strip(),
                "confidence": item.get("confidence"),
                "citation_label": str(item.get("citation_label") or "근거 문서").strip(),
                "matched_claims": [
                    str(claim).strip()
                    for claim in item.get("matched_claims", [])
                    if str(claim or "").strip()
                ][:3],
            }
        )
    return rows[: max(1, min(limit, 10))]


def normalize_candidate(candidate: dict) -> dict:
    ticker = str(candidate.get("ticker") or "").strip().upper()
    company_name = str(candidate.get("company_name") or candidate.get("name") or ticker).strip()
    reasons = [str(item).strip() for item in candidate.get("reasons", []) if str(item or "").strip()]
    evidence = [str(item).strip() for item in candidate.get("evidence_sources", []) if str(item or "").strip()]
    score_components = [
        item
        for item in candidate.get("score_components", [])
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    return {
        **candidate,
        "ticker": ticker,
        "company_name": company_name,
        "score": int(candidate.get("score") or 0),
        "score_components": score_components,
        "reasons": reasons[:6],
        "evidence_sources": evidence[:8],
        "evidence_documents": normalize_evidence_documents(candidate.get("evidence_documents")),
        "score_explanation": candidate.get("score_explanation") or {},
        "score_penalties": [
            str(item).strip()
            for item in candidate.get("score_penalties", [])
            if str(item or "").strip()
        ][:6],
        "quality_flags": [
            str(item).strip()
            for item in candidate.get("quality_flags", [])
            if str(item or "").strip()
        ][:6],
        "overseas_tracking": candidate.get("overseas_tracking") or {},
        "portfolio_risk_connection": candidate.get("portfolio_risk_connection") or {},
    }


def normalize_recommendation_ticker(value: object) -> str:
    text = str(value or "").strip().upper()
    return "".join(char for char in text if char.isalnum() or char in {".", "-", "_"})


def daily_recommendation_target_key(item: dict) -> str:
    return normalize_recommendation_ticker(item.get("ticker") or item.get("key"))


def daily_recommendation_candidate_is_valid(ticker: str, company_name: str) -> bool:
    if not ticker or ticker in {"CASH", "UNKNOWN"}:
        return False
    if fullmatch(r"\d+", ticker) and not fullmatch(r"\d{6}", ticker):
        return False
    if not company_name or company_name.upper().startswith("UNKNOWN"):
        return False
    return True


def ensure_daily_recommendation_candidate(
    candidates_by_ticker: dict[str, dict],
    ticker: str,
    company_name: str,
) -> dict:
    key = normalize_recommendation_ticker(ticker)
    row = candidates_by_ticker.setdefault(
        key,
        {
            "ticker": key,
            "company_name": company_name,
            "score": 0,
            "reasons": [],
            "evidence_sources": [],
            "risk_notes": [],
            "portfolio_context": [],
            "score_penalties": [],
            "quality_flags": [],
            "portfolio_risk_connection": {},
            "overseas_tracking": {},
            "currency": "KRW" if fullmatch(r"\d{6}", key) else "USD",
            "baseline_price": None,
            "baseline_price_source": None,
            "baseline_price_checked_at": None,
        },
    )
    if company_name and (row.get("company_name") == key or not row.get("company_name")):
        row["company_name"] = company_name
    return row


def daily_recommendation_manifest_quality_by_ticker(manifest_entries: list[dict]) -> dict[str, dict]:
    quality_by_ticker: dict[str, dict] = {}
    for entry in manifest_entries:
        if not isinstance(entry, dict):
            continue
        ticker = normalize_recommendation_ticker(entry.get("ticker"))
        if not ticker:
            continue
        quality = quality_by_ticker.setdefault(
            ticker,
            {
                "active_count": 0,
                "archived_count": 0,
                "high_quality_count": 0,
                "duplicate_suspected_count": 0,
                "body_missing_count": 0,
                "ocr_needed_count": 0,
                "policy_url_only_count": 0,
                "latest_quality_date": None,
            },
        )
        if is_archived_research_entry(entry):
            quality["archived_count"] += 1
            continue
        quality["active_count"] += 1
        date_text = str(entry.get("date") or "")[:10]
        if date_text and (not quality["latest_quality_date"] or date_text > quality["latest_quality_date"]):
            quality["latest_quality_date"] = date_text
        duplicate_check = entry.get("duplicate_check") if isinstance(entry.get("duplicate_check"), dict) else {}
        duplicate_suspected = bool(
            duplicate_check.get("is_duplicate_suspected")
            or entry.get("duplicate_reason")
            or int(entry.get("duplicate_count") or 0) > 0
        )
        needs_body = storage_quality_entry_needs_body(entry)
        needs_ocr = storage_quality_entry_needs_ocr(entry)
        policy_url_only = storage_quality_entry_is_policy_url_only(entry)
        if duplicate_suspected:
            quality["duplicate_suspected_count"] += 1
        if needs_body:
            quality["body_missing_count"] += 1
        if needs_ocr:
            quality["ocr_needed_count"] += 1
        if policy_url_only:
            quality["policy_url_only_count"] += 1
        if not duplicate_suspected and not needs_body and not needs_ocr and not policy_url_only:
            quality["high_quality_count"] += 1
    return quality_by_ticker


def add_daily_recommendation_score(candidate: dict, points: int | float, label: str) -> None:
    try:
        numeric_points = int(points)
    except (TypeError, ValueError):
        numeric_points = 0
    if numeric_points <= 0:
        return
    candidate["score"] = int(candidate.get("score") or 0) + numeric_points
    candidate.setdefault("score_components", []).append(
        {"label": str(label or "").strip() or "점수", "points": numeric_points}
    )


def add_daily_recommendation_penalty(candidate: dict, label: str, points: int | float = 0) -> None:
    try:
        numeric_points = abs(int(points))
    except (TypeError, ValueError):
        numeric_points = 0
    text = str(label or "").strip()
    if not text:
        return
    if numeric_points:
        candidate["score"] = int(candidate.get("score") or 0) - numeric_points
        text = f"{text} (-{numeric_points})"
    candidate.setdefault("score_penalties", []).append(text)


def apply_daily_recommendation_storage_quality(candidate: dict, quality: dict | None) -> None:
    if not quality:
        candidate.setdefault("quality_flags", []).append("저장 품질 대시보드 연결 없음")
        quality = {}
    high_quality_count = int(quality.get("high_quality_count") or 0)
    duplicate_count = int(quality.get("duplicate_suspected_count") or 0)
    body_missing_count = int(quality.get("body_missing_count") or 0)
    ocr_needed_count = int(quality.get("ocr_needed_count") or 0)
    archived_count = int(quality.get("archived_count") or 0)
    active_count = int(quality.get("active_count") or 0)
    if high_quality_count >= 3:
        add_daily_recommendation_score(candidate, 8, "검증 저장자료 품질")
    elif high_quality_count > 0:
        add_daily_recommendation_score(candidate, 3, "검증 저장자료 품질")
    else:
        candidate.setdefault("quality_flags", []).append("검증된 활성 저장자료 부족")
        add_points = 3 if active_count else 5
        add_daily_recommendation_penalty(candidate, "검증된 활성 저장자료 부족", add_points)
    if duplicate_count:
        penalty = min(8, max(2, duplicate_count))
        add_daily_recommendation_penalty(candidate, "중복 의심 저장자료 대표화 필요", penalty)
        candidate.setdefault("quality_flags", []).append("중복 의심 자료는 대표 자료만 근거로 사용")
    if body_missing_count or ocr_needed_count:
        penalty = min(10, (body_missing_count * 3) + (ocr_needed_count * 3))
        add_daily_recommendation_penalty(candidate, "본문/OCR 보강 필요 자료 존재", penalty)
        candidate.setdefault("quality_flags", []).append("본문/OCR 보강 전 투자 근거 가중치 제한")
    if archived_count and not active_count:
        candidate.setdefault("quality_flags", []).append("활성 근거 없이 보관 자료만 존재")
    quality_evidence = (
        "저장 품질: "
        f"활용 가능 {high_quality_count}건 · "
        f"중복 제외 {duplicate_count}건 · "
        f"보강 필요 {body_missing_count + ocr_needed_count}건"
    )
    evidence_sources = candidate.setdefault("evidence_sources", [])
    if quality_evidence not in evidence_sources:
        evidence_sources.insert(0, quality_evidence)


def compact_recommendation_text(value: object, max_length: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 1)].rstrip() + "…"


def daily_recommendation_recent_weekly_index(recent_weekly: dict) -> dict[str, dict[str, list[dict]]]:
    """Index recent weekly items and groups by ticker for daily recommendation scoring."""
    items_by_ticker: dict[str, list[dict]] = {}
    for item in [
        *(recent_weekly.get("important_filings") or []),
        *(recent_weekly.get("display_reports") or []),
        *(recent_weekly.get("public_ir_sec_items") or []),
        *(recent_weekly.get("customs_exports") or []),
    ]:
        if not isinstance(item, dict):
            continue
        key = normalize_recommendation_ticker(item.get("ticker"))
        if key:
            items_by_ticker.setdefault(key, []).append(item)

    groups_by_ticker: dict[str, list[dict]] = {}
    for group in recent_weekly.get("category_groups") or []:
        if not isinstance(group, dict):
            continue
        group_key = str(group.get("key") or "").strip()
        group_label = str(group.get("label") or group_key or "최근 자료").strip()
        visible_items = [item for item in group.get("items") or [] if isinstance(item, dict)]
        linked_tickers = {
            ticker
            for ticker in (normalize_recommendation_ticker(ticker) for ticker in group.get("tickers") or [])
            if ticker
        }
        for item in visible_items:
            key = normalize_recommendation_ticker(item.get("ticker"))
            if key:
                linked_tickers.add(key)
        first_visible_item = visible_items[0] if visible_items else {}
        group_summary = compact_recommendation_text(
            first_visible_item.get("summary")
            or first_visible_item.get("title")
            or group.get("note")
            or group_label,
            90,
        )
        for ticker in sorted(linked_tickers):
            groups_by_ticker.setdefault(ticker, []).append(
                {
                    "key": group_key,
                    "label": group_label,
                    "count": int(group.get("count") or 0),
                    "visible_count": int(group.get("visible_count") or 0),
                    "ticker_count": int(group.get("ticker_count") or 0),
                    "quality_summary": group.get("quality_summary") if isinstance(group.get("quality_summary"), dict) else {},
                    "summary": group_summary,
                }
            )
    return {"items_by_ticker": items_by_ticker, "groups_by_ticker": groups_by_ticker}


def daily_recommendation_weekly_group_evidence_text(group: dict) -> str:
    label = str(group.get("label") or group.get("key") or "자료").strip()
    if not label:
        return ""
    total_count = int(group.get("count") or 0)
    visible_count = int(group.get("visible_count") or 0)
    ticker_count = int(group.get("ticker_count") or 0)
    text = f"{label} {total_count}건"
    details = []
    if visible_count and total_count > visible_count:
        details.append(f"표시 {visible_count}/{total_count}건")
    if ticker_count:
        details.append(f"종목 {ticker_count}개")
    if details:
        text += f"({'/'.join(details)})"
    if str(group.get("key") or "") == "public_ir_sec":
        quality = group.get("quality_summary") if isinstance(group.get("quality_summary"), dict) else {}
        usable = int(quality.get("usable_for_recommendation") or 0)
        blocked = int(quality.get("needs_body_copy") or quality.get("blocked_or_needs_review") or 0)
        provider_counts = (
            quality.get("source_families")
            if isinstance(quality.get("source_families"), dict)
            else quality.get("providers")
            if isinstance(quality.get("providers"), dict)
            else {}
        )
        provider_text = "/".join(
            f"{provider} {count}건"
            for provider, count in list(provider_counts.items())[:2]
            if provider
        )
        reliability_counts = quality.get("reliability_labels") if isinstance(quality.get("reliability_labels"), dict) else {}
        reliability_text = "/".join(
            f"{label} {count}건"
            for label, count in list(reliability_counts.items())[:2]
            if label
        )
        text += f"(추천 가능 {usable}건/본문 보강 {blocked}건"
        if provider_text:
            text += f"/출처 {provider_text}"
        if reliability_text:
            text += f"/품질 {reliability_text}"
        text += ")"
    return text


RAG_REPORT_TYPE_PRIORITY = {
    "public-ir-sec": 95,
    "earnings-filing-note": 92,
    "dart-filing-watch": 90,
    "official_filing": 88,
    "thesis-impact-review": 82,
    "collaborative-team-report": 78,
    "dossier-synthesis": 76,
    "research-capture": 72,
    "earnings-reaction": 70,
    "research-checklist": 65,
    "smart-trade-setup": 62,
}


def _safe_float(value: object, default: float = 0.7) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _evidence_document_claims(document: dict[str, Any], claims: list[str]) -> list[str]:
    report_type = str(document.get("report_type") or "").lower()
    source_type = str(document.get("source_type") or "").lower()
    haystack = " ".join(
        str(document.get(key) or "")
        for key in ("title", "summary", "content_excerpt", "source_file_name", "source_relative_path")
    ).lower()
    matched: list[str] = []
    for claim in claims:
        claim_text = str(claim or "").strip()
        if not claim_text:
            continue
        claim_lower = claim_text.lower()
        if "공개 ir/sec" in claim_lower and ("public-ir-sec" in report_type or "sec" in source_type):
            matched.append(claim_text)
        elif "공시" in claim_lower and ("filing" in source_type or "dart" in report_type):
            matched.append(claim_text)
        elif "목표가" in claim_lower or "리포트" in claim_lower:
            if report_type in {"thesis-impact-review", "collaborative-team-report", "dossier-synthesis", "research-capture"}:
                matched.append(claim_text)
        elif "최근 근거 파일" in claim_lower and str(document.get("source_relative_path") or "").split("/")[-1].lower() in claim_lower:
            matched.append(claim_text)
        elif "rag 연결" in claim_lower:
            matched.append(claim_text)
        else:
            tokens = [token for token in claim_lower.replace("/", " ").replace(":", " ").split() if len(token) >= 4]
            if tokens and any(token in haystack for token in tokens[:8]):
                matched.append(claim_text)
    return list(dict.fromkeys(matched))[:3]


def build_daily_recommendation_evidence_documents(
    vault_dir: Path,
    ticker: str,
    evidence_sources: list[str] | tuple[str, ...] | None,
    reasons: list[str] | tuple[str, ...] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return representative RAG documents that support a recommendation record."""
    normalized_ticker = normalize_recommendation_ticker(ticker)
    if not normalized_ticker:
        return []
    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT ticker, report_type, title, summary, content_excerpt, source_type,
                       source_file_name, source_relative_path, json_relative_path,
                       source_date, confidence, tags_json, updated_at
                FROM research_memory_documents
                WHERE upper(ticker) = ?
                ORDER BY source_date DESC, updated_at DESC
                LIMIT 80
                """,
                (normalized_ticker,),
            ).fetchall()
    except sqlite3.Error:
        return []

    claims = [str(item).strip() for item in [*(evidence_sources or []), *(reasons or [])] if str(item or "").strip()]
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        payload = dict(row)
        tags = [str(tag) for tag in _json_list(payload.get("tags_json"))]
        if "archived" in {tag.lower() for tag in tags}:
            continue
        report_type = str(payload.get("report_type") or "")
        source_type = str(payload.get("source_type") or "")
        matched_claims = _evidence_document_claims(payload, claims)
        priority = RAG_REPORT_TYPE_PRIORITY.get(report_type, RAG_REPORT_TYPE_PRIORITY.get(source_type, 55))
        confidence = _safe_float(payload.get("confidence"), 0.7)
        claim_bonus = len(matched_claims) * 12
        text_length_bonus = min(len(str(payload.get("content_excerpt") or "")) / 400, 6)
        score = priority + (confidence * 10) + claim_bonus + text_length_bonus
        scored.append(
            (
                score,
                {
                    "title": str(payload.get("title") or payload.get("source_file_name") or "").strip(),
                    "source_relative_path": str(payload.get("source_relative_path") or "").strip(),
                    "json_relative_path": str(payload.get("json_relative_path") or "").strip(),
                    "source_date": str(payload.get("source_date") or "").strip(),
                    "report_type": report_type,
                    "source_type": source_type,
                    "confidence": confidence,
                    "citation_label": "RAG 근거 문서",
                    "matched_claims": matched_claims,
                },
            )
        )
    scored.sort(key=lambda item: (item[0], item[1].get("source_date") or ""), reverse=True)
    return normalize_evidence_documents([item for _, item in scored], limit=limit)


def unique_text_items(values: list | tuple | None, limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for value in values or []:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text, None)
    return list(seen.keys())[:limit]


def finalize_daily_recommendation_candidate(candidate: dict) -> dict:
    """Normalize recommendation reasons, evidence, risks, and score explanation."""
    if not candidate.get("reasons"):
        candidate.setdefault("reasons", []).append("보유/관심목록과 저장 리서치에 포함된 일일 점검 후보입니다.")
    candidate["reasons"] = unique_text_items(candidate.get("reasons"), 6)
    candidate["evidence_sources"] = unique_text_items(candidate.get("evidence_sources"), 8)
    candidate["evidence_documents"] = normalize_evidence_documents(candidate.get("evidence_documents"))
    candidate["risk_notes"] = unique_text_items(candidate.get("risk_notes"), 5)
    candidate["score_penalties"] = unique_text_items(candidate.get("score_penalties"), 6)
    candidate["quality_flags"] = unique_text_items(candidate.get("quality_flags"), 6)
    score_components = [
        component
        for component in candidate.get("score_components", [])
        if isinstance(component, dict) and str(component.get("label") or "").strip()
    ]
    candidate["score_components"] = score_components
    positive_points = sum(int(component.get("points") or 0) for component in score_components)
    penalty_points = sum(
        int(match.group(1))
        for item in candidate.get("score_penalties", [])
        for match in [search(r"\(-(\d+)\)", str(item))]
        if match
    )
    if positive_points:
        candidate["score_explanation"] = {
            "positive_points": positive_points,
            "penalty_points": penalty_points,
            "final_score": int(candidate.get("score") or 0),
            "top_component": max(
                score_components,
                key=lambda component: int(component.get("points") or 0),
            ),
            "component_weights": [
                {
                    "label": component.get("label"),
                    "points": int(component.get("points") or 0),
                    "weight_pct": round(int(component.get("points") or 0) / positive_points * 100, 1),
                }
                for component in score_components[:8]
            ],
        }
    return candidate


def build_tracking_milestones(recommendation_date: date) -> list[dict]:
    return [
        {
            **milestone,
            "target_date": (recommendation_date + timedelta(days=int(milestone["days"]))).isoformat(),
            "status": "pending",
            "price": None,
            "price_checked_at": None,
            "price_change": None,
            "price_change_pct": None,
            "investment_situation": "아직 추적 예정일 전입니다.",
        }
        for milestone in TRACKING_MILESTONES
    ]


def build_recommendation_record(
    candidate: dict,
    *,
    rank: int,
    recommendation_date: date,
    generated_at: str,
) -> dict:
    normalized = normalize_candidate(candidate)
    baseline_price = normalized.get("baseline_price")
    record = {
        "record_id": recommendation_record_id(recommendation_date, rank, normalized["ticker"]),
        "recommendation_date": recommendation_date.isoformat(),
        "generated_at": generated_at,
        "rank": rank,
        "ticker": normalized["ticker"],
        "company_name": normalized["company_name"],
        "score": normalized["score"],
        "score_components": normalized.get("score_components") or [],
        "score_explanation": normalized.get("score_explanation") or {},
        "score_penalties": normalized.get("score_penalties") or [],
        "quality_flags": normalized.get("quality_flags") or [],
        "recommendation_type": "daily_review_candidate",
        "action_label": "오늘의 검토 후보",
        "baseline_price": baseline_price,
        "baseline_price_source": normalized.get("baseline_price_source"),
        "baseline_price_checked_at": normalized.get("baseline_price_checked_at"),
        "currency": normalized.get("currency") or "KRW",
        "reasons": normalized["reasons"],
        "evidence_sources": normalized["evidence_sources"],
        "evidence_documents": normalized.get("evidence_documents") or [],
        "risk_notes": [
            str(item).strip()
            for item in normalized.get("risk_notes", [])
            if str(item or "").strip()
        ][:5],
        "portfolio_context": normalized.get("portfolio_context") or [],
        "portfolio_risk_connection": normalized.get("portfolio_risk_connection") or {},
        "overseas_tracking": normalized.get("overseas_tracking") or {},
        "tracking_milestones": build_tracking_milestones(recommendation_date),
    }
    return record


def summarize_tracking_performance(records: list[dict]) -> dict:
    summary = {
        "total_milestones": 0,
        "complete_count": 0,
        "pending_count": 0,
        "price_unavailable_count": 0,
        "positive_count": 0,
        "negative_count": 0,
        "flat_count": 0,
        "best": None,
        "worst": None,
    }
    completed_rows: list[dict] = []
    for record in records:
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            summary["total_milestones"] += 1
            status = milestone.get("status") or "pending"
            if status == "complete":
                summary["complete_count"] += 1
                try:
                    change_pct = float(milestone.get("price_change_pct") or 0)
                except (TypeError, ValueError):
                    change_pct = 0.0
                if change_pct > 0:
                    summary["positive_count"] += 1
                elif change_pct < 0:
                    summary["negative_count"] += 1
                else:
                    summary["flat_count"] += 1
                completed_rows.append(
                    {
                        "record_id": record.get("record_id"),
                        "company_name": record.get("company_name"),
                        "ticker": record.get("ticker"),
                        "rank": record.get("rank"),
                        "recommendation_date": record.get("recommendation_date"),
                        "milestone": milestone.get("label") or milestone.get("key"),
                        "target_date": milestone.get("target_date"),
                        "baseline_price": record.get("baseline_price"),
                        "price": milestone.get("price"),
                        "price_change": milestone.get("price_change"),
                        "price_change_pct": change_pct,
                        "investment_situation": milestone.get("investment_situation"),
                    }
                )
            elif status == "price_unavailable":
                summary["price_unavailable_count"] += 1
            else:
                summary["pending_count"] += 1
    completed_rows.sort(key=lambda item: item.get("price_change_pct") or 0, reverse=True)
    if completed_rows:
        summary["best"] = completed_rows[0]
        summary["worst"] = completed_rows[-1]
    return summary


def upsert_daily_recommendations(
    settings: Settings,
    *,
    candidates: list[dict],
    recommendation_date: date,
    generated_at: str,
    force: bool = False,
) -> dict:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    existing_today = [
        item
        for item in records
        if item.get("recommendation_date") == recommendation_date.isoformat()
    ]
    if existing_today and not force:
        return {
            "status": "skipped_existing",
            "module": "daily_stock_recommendations",
            "message": "오늘 추천 후보는 이미 저장되어 있어 중복 저장하지 않았습니다.",
            "recommendation_date": recommendation_date.isoformat(),
            "records": sorted(existing_today, key=lambda item: int(item.get("rank") or 999))[:3],
            "storage_path": str(daily_recommendation_store_path(settings)),
        }

    if force and existing_today:
        today_ids = {item.get("record_id") for item in existing_today}
        records = [item for item in records if item.get("record_id") not in today_ids]

    new_records = [
        build_recommendation_record(
            candidate,
            rank=index + 1,
            recommendation_date=recommendation_date,
            generated_at=generated_at,
        )
        for index, candidate in enumerate(candidates[:3])
    ]
    records.extend(new_records)
    records.sort(
        key=lambda item: (
            str(item.get("recommendation_date") or ""),
            -int(item.get("rank") or 999),
        ),
        reverse=True,
    )
    store.update(
        {
            "updated_at": generated_at,
            "latest_recommendation_date": recommendation_date.isoformat(),
            "records": records,
        }
    )
    write_daily_recommendation_store(settings, store)
    return {
        "status": "success",
        "module": "daily_stock_recommendations",
        "recommendation_date": recommendation_date.isoformat(),
        "saved_count": len(new_records),
        "records": new_records,
        "storage_path": str(daily_recommendation_store_path(settings)),
    }


def investment_situation(change_pct: float | None) -> str:
    if change_pct is None:
        return "현재가를 확인하지 못해 추적 보류 상태입니다."
    pct = change_pct * 100
    if pct >= 15:
        return "추천 후 강한 상승 구간입니다. 차익 실현/비중 유지 근거를 함께 점검하세요."
    if pct >= 5:
        return "추천 후 양호한 상승 구간입니다. 초기 근거가 유지되는지 확인하세요."
    if pct >= -5:
        return "추천 후 큰 변동 없이 관찰 구간입니다. 추가 근거를 더 확인하세요."
    if pct >= -15:
        return "추천 후 약세 구간입니다. 손실 원인과 투자 논거 훼손 여부를 점검하세요."
    return "추천 후 큰 폭의 약세입니다. 리스크 경고로 분류하고 재검토가 필요합니다."


PriceLookup = Callable[[str], tuple[float | None, str | None]]


def update_recommendation_tracking(
    settings: Settings,
    *,
    as_of: date,
    checked_at: str,
    price_lookup: PriceLookup,
) -> dict:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    updated: list[dict] = []
    due_count = 0
    pending_count = 0
    unavailable_count = 0
    for record in records:
        baseline_price = record.get("baseline_price")
        try:
            baseline = float(baseline_price) if baseline_price is not None else None
        except (TypeError, ValueError):
            baseline = None
        milestones = []
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            target_date = parse_date(milestone.get("target_date"))
            if not target_date or target_date > as_of:
                pending_count += 1
                milestones.append(milestone)
                continue
            if milestone.get("status") == "complete" and milestone.get("price") is not None:
                milestones.append(milestone)
                continue
            due_count += 1
            price, source = price_lookup(str(record.get("ticker") or ""))
            if price is None or baseline is None or baseline <= 0:
                unavailable_count += 1
                milestones.append(
                    {
                        **milestone,
                        "status": "price_unavailable",
                        "price_checked_at": checked_at,
                        "price_source": source,
                        "investment_situation": "추적일이 도래했지만 현재가 또는 기준가를 확인하지 못했습니다.",
                    }
                )
                continue
            change = price - baseline
            change_pct = change / baseline
            milestones.append(
                {
                    **milestone,
                    "status": "complete",
                    "price": round(price, 4),
                    "price_checked_at": checked_at,
                    "price_source": source,
                    "price_change": round(change, 4),
                    "price_change_pct": round(change_pct, 4),
                    "investment_situation": investment_situation(change_pct),
                }
            )
        record["tracking_milestones"] = milestones
        updated.append(record)

    store["records"] = updated
    store["tracking_updated_at"] = checked_at
    write_daily_recommendation_store(settings, store)
    return {
        "status": "success",
        "module": "daily_recommendation_tracking",
        "as_of": as_of.isoformat(),
        "checked_at": checked_at,
        "record_count": len(updated),
        "due_count": due_count,
        "pending_count": pending_count,
        "price_unavailable_count": unavailable_count,
        "storage_path": str(daily_recommendation_store_path(settings)),
    }


def summarize_daily_recommendation_store(settings: Settings, *, limit: int = 30) -> dict:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = store.get("latest_recommendation_date")
    latest_records = [
        item for item in records if item.get("recommendation_date") == latest_date
    ] if latest_date else []
    recommendation_dates = sorted(
        {
            str(item.get("recommendation_date"))
            for item in records
            if item.get("recommendation_date")
        },
        reverse=True,
    )
    due_milestones = []
    for record in records:
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            if milestone.get("status") in {"price_unavailable", "complete"}:
                continue
            due_milestones.append(
                {
                    "record_id": record.get("record_id"),
                    "company_name": record.get("company_name"),
                    "ticker": record.get("ticker"),
                    "rank": record.get("rank"),
                    "recommendation_date": record.get("recommendation_date"),
                    "milestone": milestone.get("label"),
                    "target_date": milestone.get("target_date"),
                    "status": milestone.get("status"),
                }
            )
    return {
        "status": "success",
        "module": "daily_stock_recommendations",
        "updated_at": store.get("updated_at"),
        "tracking_updated_at": store.get("tracking_updated_at"),
        "latest_recommendation_date": latest_date,
        "record_count": len(records),
        "recommendation_dates": recommendation_dates[:30],
        "latest_records": sorted(latest_records, key=lambda item: int(item.get("rank") or 999))[:3],
        "records": records[: max(1, min(limit, 200))],
        "due_or_pending_milestones": due_milestones[:30],
        "performance_summary": summarize_tracking_performance(records),
        "storage_path": str(daily_recommendation_store_path(settings)),
    }
