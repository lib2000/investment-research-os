"""Persist and render the daily family portfolio top-pick research card.

The card is intentionally a *research review* artifact.  It reuses the
persisted daily-candidate ranking instead of making another market-data call,
filters candidates against the current family holdings and watchlist, and
never emits an order or a delivery request.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
from datetime import date, datetime
from pathlib import Path
from re import search, sub
from typing import Any
from uuid import uuid4

from research_os.daily_recommendation_store import read_daily_recommendation_store
from research_os.portfolio_store import family_member_portfolios, read_portfolio_store
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings
from research_os.state_store import (
    current_storage_date,
    current_storage_timestamp,
    interest_list_path,
    read_json_store,
    write_json_store,
)


MODULE = "daily_family_top_pick_card"
CARD_WIDTH = 1080
CARD_HEIGHT = 1350
DISCLAIMER = "투자 리서치용 검토 후보입니다. 매수·매도 지시나 자동 주문이 아닙니다."


def daily_top_pick_card_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_top_pick_card.json"


def daily_top_pick_card_scheduler_state_path(settings: Settings) -> Path:
    return (
        resolve_vault_dir(settings.research_vault_dir)
        / "_system"
        / "daily_top_pick_card_scheduler_state.json"
    )


def daily_top_pick_card_asset_dir(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_top_pick_cards"


def daily_top_pick_card_svg_path(settings: Settings, recommendation_date: str) -> Path:
    safe_date = str(recommendation_date or "").strip()
    try:
        safe_date = date.fromisoformat(safe_date).isoformat()
    except ValueError:
        safe_date = "undated"
    return daily_top_pick_card_asset_dir(settings) / f"family-top-pick-{safe_date}.svg"


def _clean_text(value: object, *, limit: int = 180, fallback: str = "확인 필요") -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return fallback
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)].rstrip()}…"


def _safe_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_daily_family_top_pick_time(settings: Settings) -> tuple[int, int]:
    """Return the local card-generation time with a safe 07:10 fallback."""
    configured = getattr(settings, "daily_family_top_pick_time", "07:10")
    match = search(r"^(\d{1,2}):(\d{2})$", str(configured or "07:10").strip())
    if not match:
        return 7, 10
    return (
        min(max(int(match.group(1)), 0), 23),
        min(max(int(match.group(2)), 0), 59),
    )


def should_run_daily_family_top_pick_card(
    settings: Settings,
    now: datetime,
) -> bool:
    """Gate the scheduled card to one local execution per calendar day."""
    if not settings.daily_recommendations_enabled:
        return False
    hour, minute = parse_daily_family_top_pick_time(settings)
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < scheduled:
        return False
    state = read_json_store(daily_top_pick_card_scheduler_state_path(settings), {})
    return state.get("last_run_date") != now.date().isoformat()


def record_daily_family_top_pick_schedule_run(
    settings: Settings,
    result: dict[str, Any],
    *,
    run_at: datetime,
) -> dict[str, Any]:
    """Record a scheduler attempt without storing holdings, orders, or secrets."""
    payload = {
        "module": MODULE,
        "last_run_date": run_at.date().isoformat(),
        "last_run_at": run_at.isoformat(timespec="seconds"),
        "last_status": str(result.get("status") or "unknown"),
        "last_generation_status": str(result.get("generation_status") or "unknown"),
        "recommendation_date": str(result.get("recommendation_date") or ""),
        "message": _clean_text(result.get("message"), limit=220),
    }
    write_json_store(daily_top_pick_card_scheduler_state_path(settings), payload)
    return payload


def _attach_schedule(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    """Expose schedule metadata while keeping portfolio membership private."""
    scheduler_state = read_json_store(daily_top_pick_card_scheduler_state_path(settings), {})
    return {
        **payload,
        "schedule": {
            "daily_recommendations_time": settings.daily_recommendations_time,
            "daily_top_pick_time": getattr(settings, "daily_family_top_pick_time", "07:10"),
            "last_scheduled_run_at": scheduler_state.get("last_run_at"),
            "last_scheduled_run_date": scheduler_state.get("last_run_date"),
            "last_scheduled_status": scheduler_state.get("last_status"),
        },
    }


def _normalized_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def _unique_text(values: object, *, limit: int, item_limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values if isinstance(values, list) else []:
        text = _clean_text(value, limit=item_limit, fallback="")
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _scope_fingerprint(holding_tickers: set[str], interest_tickers: set[str]) -> str:
    payload = "|".join(
        ["H", *sorted(holding_tickers), "I", *sorted(interest_tickers)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_family_candidate_scope(settings: Settings) -> dict[str, Any]:
    """Describe the current family-wide holdings/watchlist universe without values."""
    store = read_portfolio_store(settings)
    members = family_member_portfolios(store)
    holding_tickers: set[str] = set()
    holding_count = 0
    for portfolio in members:
        for holding in portfolio.holdings:
            ticker = _normalized_ticker(holding.ticker)
            if not ticker or ticker == "CASH":
                continue
            holding_count += 1
            holding_tickers.add(ticker)

    interest_payload = read_json_store(interest_list_path(settings), {"tickers": []})
    interest_tickers = {
        _normalized_ticker(item.get("ticker"))
        for item in interest_payload.get("tickers", [])
        if isinstance(item, dict) and _normalized_ticker(item.get("ticker"))
    }
    candidate_tickers = holding_tickers | interest_tickers
    return {
        "label": "가족 전체 보유 종목 + 관심 종목",
        "member_portfolio_count": len(members),
        "holding_count": holding_count,
        "unique_holding_count": len(holding_tickers),
        "interest_count": len(interest_tickers),
        "candidate_scope_count": len(candidate_tickers),
        "holding_tickers": sorted(holding_tickers),
        "interest_tickers": sorted(interest_tickers),
        "scope_fingerprint": _scope_fingerprint(holding_tickers, interest_tickers),
    }


def _public_scope(scope: dict[str, Any]) -> dict[str, Any]:
    """Return card metadata without exposing the full family ticker lists."""
    return {
        key: scope.get(key)
        for key in (
            "label",
            "member_portfolio_count",
            "holding_count",
            "unique_holding_count",
            "interest_count",
            "candidate_scope_count",
            "scope_fingerprint",
        )
    }


def _record_quality(record: dict[str, Any]) -> dict[str, Any]:
    quality = record.get("evidence_quality_summary")
    return quality if isinstance(quality, dict) else {}


def _record_sort_key(record: dict[str, Any]) -> tuple[float, float, int, str]:
    quality = _record_quality(record)
    return (
        -(_safe_number(record.get("score")) or 0.0),
        -(_safe_number(quality.get("score")) or 0.0),
        -len(record.get("evidence_documents") or []),
        _normalized_ticker(record.get("ticker")),
    )


def _latest_recommendation_records(settings: Settings) -> tuple[str | None, list[dict[str, Any]], dict[str, Any]]:
    store = read_daily_recommendation_store(settings)
    records = [item for item in store.get("records", []) if isinstance(item, dict)]
    latest_date = str(store.get("latest_recommendation_date") or "").strip()
    if not latest_date and records:
        latest_date = max(str(item.get("recommendation_date") or "") for item in records)
    if not latest_date:
        return None, [], store
    latest_records = [
        item for item in records if str(item.get("recommendation_date") or "") == latest_date
    ]
    return latest_date, latest_records, store


def _source_fingerprint(records: list[dict[str, Any]], recommendation_date: str | None) -> str:
    rows = [
        {
            "ticker": _normalized_ticker(item.get("ticker")),
            "score": item.get("score"),
            "quality": _record_quality(item).get("score"),
            "generated_at": item.get("generated_at"),
            "rank": item.get("rank"),
        }
        for item in sorted(records, key=_record_sort_key)
    ]
    source = json.dumps(
        {"recommendation_date": recommendation_date, "records": rows},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _status_label(record: dict[str, Any], scope: dict[str, Any]) -> str:
    ticker = _normalized_ticker(record.get("ticker"))
    held = ticker in set(scope.get("holding_tickers") or [])
    interested = ticker in set(scope.get("interest_tickers") or [])
    if held and interested:
        return "가족 보유 · 관심 종목"
    if held:
        return "가족 보유 종목"
    if interested:
        return "관심 종목"
    return "범위 재확인 필요"


def _next_review(record: dict[str, Any]) -> dict[str, str]:
    milestones = [item for item in record.get("tracking_milestones", []) if isinstance(item, dict)]
    pending = [
        item
        for item in milestones
        if str(item.get("status") or "").lower() not in {"complete", "success", "skipped_existing"}
    ]
    selected = pending[0] if pending else (milestones[0] if milestones else {})
    target_date = _clean_text(selected.get("target_date"), limit=24, fallback="확인 필요")
    label = _clean_text(selected.get("label") or selected.get("key"), limit=32, fallback="후속 추적 일정")
    return {
        "label": label,
        "target_date": target_date,
        "summary": f"{label} · {target_date}",
    }


def _format_price(value: object, currency: object) -> str:
    number = _safe_number(value)
    if number is None or number <= 0:
        return "확인 필요"
    code = str(currency or "").strip().upper()
    if code == "KRW":
        return f"{round(number):,}원"
    if code == "USD":
        return f"${number:,.2f}"
    return f"{number:,.2f} {code}".strip()


def _confidence_label(quality: dict[str, Any]) -> str:
    grade = str(quality.get("grade") or "").upper()
    if grade == "A":
        return "높음"
    if grade == "B":
        return "보통"
    if grade == "C":
        return "낮음"
    return "확인 필요"


def _build_selected_card(record: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    quality = _record_quality(record)
    score = _safe_number(record.get("score"))
    quality_score = _safe_number(quality.get("score"))
    reasons = _unique_text(record.get("reasons"), limit=3, item_limit=122)
    risks = _unique_text(record.get("risk_notes"), limit=2, item_limit=122)
    evidence = _unique_text(record.get("evidence_sources"), limit=3, item_limit=92)
    if not reasons:
        reasons = ["저장된 일일 후보의 투자 논거를 추가 확인하세요."]
    if not risks:
        risks = ["핵심 원문과 최신 가격 조건을 사람이 최종 확인하세요."]
    next_review = _next_review(record)
    currency = str(record.get("currency") or "").upper() or "통화 확인 필요"
    return {
        "title": "오늘의 우선 리서치 후보",
        "company_name": _clean_text(record.get("company_name") or record.get("ticker"), limit=64),
        "ticker": _normalized_ticker(record.get("ticker")),
        "market": _clean_text(record.get("market_label") or record.get("market"), limit=12),
        "scope_status": _status_label(record, scope),
        "research_stance": "근거 기반 우선 검토",
        "selection_note": "당일 저장된 가족 보유·관심 후보 중 매수 판단 보류가 아닌 후보를 점수와 근거 품질 순으로 정렬했습니다.",
        "metrics": [
            {
                "label": "후보 점수",
                "value": f"{int(score) if score is not None else '확인 필요'}점" if score is not None else "확인 필요",
                "detail": "기존 일일 추천 점수",
            },
            {
                "label": "근거 품질",
                "value": f"{str(quality.get('grade') or '확인 필요').upper()} · {int(quality_score) if quality_score is not None else '확인 필요'}점",
                "detail": _clean_text(quality.get("label"), limit=40),
            },
            {
                "label": "기준 가격",
                "value": _format_price(record.get("baseline_price"), currency),
                "detail": _clean_text(record.get("baseline_price_checked_at"), limit=34),
            },
            {
                "label": "다음 추적",
                "value": next_review["target_date"],
                "detail": next_review["label"],
            },
        ],
        "thesis": reasons[0],
        "reasons": reasons,
        "risks": risks,
        "evidence": evidence,
        "evidence_summary": _clean_text(quality.get("summary"), limit=100),
        "guardrail": _clean_text(quality.get("guardrail_label"), limit=64),
        "guardrail_action": _clean_text(quality.get("guardrail_action"), limit=120),
        "confidence": _confidence_label(quality),
        "evidence_strength": {
            "grade": str(quality.get("grade") or "확인 필요").upper(),
            "score": int(quality_score) if quality_score is not None else None,
            "document_count": int(_safe_number(quality.get("document_count")) or 0),
            "recent_30d_count": int(_safe_number(quality.get("recent_30d_count")) or 0),
        },
        "next_review": next_review,
        "disclaimer": DISCLAIMER,
    }


def _missing_payload(scope: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "status": "not_found",
        "module": MODULE,
        "generated_at": current_storage_timestamp(),
        "recommendation_date": None,
        "is_current": False,
        "scope": _public_scope(scope),
        "selection": {
            "method": "persisted_daily_candidate_score_then_evidence_quality",
            "in_scope_record_count": 0,
            "eligible_count": 0,
            "excluded_review_hold_count": 0,
            "excluded_out_of_scope_count": 0,
            "selected_ticker": None,
            "status": "not_found",
        },
        "card": None,
        "message": message,
        "disclaimer": DISCLAIMER,
    }


def build_daily_family_top_pick_card(settings: Settings) -> dict[str, Any]:
    """Build a single evidence-first candidate from the persisted daily ranking."""
    scope = build_family_candidate_scope(settings)
    recommendation_date, records, _store = _latest_recommendation_records(settings)
    if not recommendation_date:
        return _missing_payload(scope, "최근 일일 추천 후보가 아직 저장되지 않아 오늘의 한 종목 카드를 만들 수 없습니다.")

    scope_tickers = set(scope.get("holding_tickers") or []) | set(scope.get("interest_tickers") or [])
    in_scope = [
        item
        for item in records
        if _normalized_ticker(item.get("ticker")) in scope_tickers
    ]
    if not in_scope:
        return _missing_payload(scope, "최신 일일 추천에 현재 가족 보유·관심 범위와 일치하는 종목이 없습니다.")

    unique_records: dict[str, dict[str, Any]] = {}
    for record in sorted(in_scope, key=_record_sort_key):
        unique_records.setdefault(_normalized_ticker(record.get("ticker")), record)
    scoped_records = list(unique_records.values())
    eligible = [record for record in scoped_records if not bool(_record_quality(record).get("blocks_buy_decision"))]
    selected_pool = eligible or scoped_records
    selected = sorted(selected_pool, key=_record_sort_key)[0]
    selection_status = "ready" if eligible else "review_hold"
    card = _build_selected_card(selected, scope)
    if selection_status == "review_hold":
        card["research_stance"] = "근거 보강 전 검토 보류"
        card["selection_note"] = "현재 범위의 모든 최신 후보가 근거 보강 또는 매수 판단 보류 상태여서, 가장 높은 점수 후보를 보류 카드로만 표시합니다."

    source_fingerprint = _source_fingerprint(scoped_records, recommendation_date)
    current_date = current_storage_date().isoformat()
    return {
        "status": selection_status,
        "module": MODULE,
        "generated_at": current_storage_timestamp(),
        "recommendation_date": recommendation_date,
        "is_current": recommendation_date == current_date,
        "scope": _public_scope(scope),
        "selection": {
            "method": "persisted_daily_candidate_score_then_evidence_quality",
            "source_fingerprint": source_fingerprint,
            "in_scope_record_count": len(scoped_records),
            "eligible_count": len(eligible),
            "excluded_review_hold_count": len(scoped_records) - len(eligible),
            "excluded_out_of_scope_count": max(0, len(records) - len(in_scope)),
            "selected_ticker": card["ticker"],
            "selected_score": selected.get("score"),
            "selected_evidence_grade": card["evidence_strength"]["grade"],
            "status": selection_status,
        },
        "card": card,
        "message": (
            "가족 전체 보유·관심 범위에서 오늘의 우선 리서치 후보를 저장했습니다."
            if selection_status == "ready"
            else "가족 전체 후보는 있으나 근거 보강 전 우선 검토로 승격하지 않았습니다."
        ),
        "disclaimer": DISCLAIMER,
    }


def _svg_lines(value: object, *, limit: int, line_width: int, line_limit: int) -> list[str]:
    text = _clean_text(value, limit=limit, fallback="확인 필요")
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        proposal = f"{current} {word}".strip()
        if current and len(proposal) > line_width:
            lines.append(current)
            current = word
        else:
            current = proposal
    if current:
        lines.append(current)
    final_lines: list[str] = []
    for line in lines:
        if len(line) <= line_width:
            final_lines.append(line)
            continue
        final_lines.extend(line[index : index + line_width] for index in range(0, len(line), line_width))
    return final_lines[:line_limit] or ["확인 필요"]


def _svg_text_lines(
    value: object,
    *,
    x: int,
    y: int,
    size: int,
    fill: str,
    line_height: int,
    line_width: int,
    line_limit: int = 2,
    weight: int = 700,
    limit: int = 180,
) -> str:
    lines = _svg_lines(value, limit=limit, line_width=line_width, line_limit=line_limit)
    return "".join(
        f'<text x="{x}" y="{y + index * line_height}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def render_daily_family_top_pick_svg(payload: dict[str, Any]) -> str:
    """Render a self-contained 1080×1350 dark research snapshot SVG."""
    card = payload.get("card") if isinstance(payload.get("card"), dict) else None
    recommendation_date = _clean_text(payload.get("recommendation_date"), limit=24)
    if not card:
        message = _clean_text(payload.get("message"), limit=220)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-label="오늘의 리서치 후보 생성 대기">
  <rect width="100%" height="100%" fill="#071423"/>
  <rect x="54" y="54" width="972" height="1242" rx="30" fill="#0b1d31" stroke="#2bd5cf" stroke-width="2"/>
  <text x="92" y="136" fill="#62e8e1" font-size="30" font-weight="800" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">FAMILY RESEARCH OS</text>
  <text x="92" y="224" fill="#ffffff" font-size="54" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">오늘의 후보 생성 대기</text>
  {_svg_text_lines(message, x=92, y=312, size=30, fill="#cbd5e1", line_height=46, line_width=40, line_limit=5, weight=650, limit=220)}
  <text x="92" y="1198" fill="#94a3b8" font-size="24" font-weight="700" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(DISCLAIMER)}</text>
</svg>'''

    metrics = card.get("metrics") if isinstance(card.get("metrics"), list) else []
    metric_rects: list[str] = []
    metric_texts: list[str] = []
    for index, metric in enumerate(metrics[:4]):
        col = index % 2
        row = index // 2
        x = 74 + col * 474
        y = 328 + row * 174
        metric_rects.append(
            f'<rect x="{x}" y="{y}" width="448" height="150" rx="18" fill="#102940" stroke="#2d6a85" stroke-width="2"/>'
        )
        metric_texts.append(
            f'<text x="{x + 24}" y="{y + 40}" fill="#78ded8" font-size="24" font-weight="800" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(metric.get("label"), limit=22))}</text>'
        )
        metric_texts.append(
            f'<text x="{x + 24}" y="{y + 88}" fill="#ffffff" font-size="34" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(metric.get("value"), limit=30))}</text>'
        )
        metric_texts.append(
            f'<text x="{x + 24}" y="{y + 122}" fill="#a9bbcb" font-size="19" font-weight="700" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(metric.get("detail"), limit=40))}</text>'
        )

    reason_rows = []
    for index, reason in enumerate(card.get("reasons") or []):
        y = 790 + index * 42
        reason_rows.append(f'<circle cx="102" cy="{y - 7}" r="6" fill="#55d9d0"/>')
        reason_rows.append(_svg_text_lines(reason, x=122, y=y, size=23, fill="#dbeafe", line_height=32, line_width=58, line_limit=1, weight=650, limit=128))

    risk_rows = []
    for index, risk in enumerate(card.get("risks") or []):
        y = 1035 + index * 42
        risk_rows.append(f'<circle cx="102" cy="{y - 7}" r="6" fill="#f6b26b"/>')
        risk_rows.append(_svg_text_lines(risk, x=122, y=y, size=22, fill="#fef3c7", line_height=31, line_width=58, line_limit=1, weight=650, limit=128))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-label="{html.escape(_clean_text(card.get("company_name"), limit=64))} 오늘의 리서치 후보">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#06101f"/><stop offset="55%" stop-color="#0b263e"/><stop offset="100%" stop-color="#071423"/></linearGradient>
    <radialGradient id="orb" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#49e0dc" stop-opacity="0.64"/><stop offset="100%" stop-color="#08355a" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <circle cx="934" cy="156" r="180" fill="url(#orb)"/>
  <circle cx="900" cy="130" r="62" fill="none" stroke="#3fd6cf" stroke-opacity="0.5" stroke-width="2"/>
  <circle cx="900" cy="130" r="38" fill="none" stroke="#3fd6cf" stroke-opacity="0.42" stroke-width="2"/>
  <path d="M70 82 H575" stroke="#44ddd5" stroke-width="3"/>
  <text x="74" y="130" fill="#72e6df" font-size="27" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">FAMILY RESEARCH OS · DAILY TOP PICK</text>
  <text x="74" y="208" fill="#ffffff" font-size="58" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(card.get("company_name"), limit=42))}</text>
  <rect x="74" y="232" width="{min(330, 82 + len(_clean_text(card.get("ticker"), limit=18)) * 22)}" height="48" rx="20" fill="#0f3e57" stroke="#40d9d1" stroke-width="2"/>
  <text x="98" y="264" fill="#7be9e2" font-size="25" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(card.get("ticker"), limit=18))} · {html.escape(_clean_text(card.get("market"), limit=12))}</text>
  <text x="74" y="308" fill="#b9cfde" font-size="25" font-weight="800" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(_clean_text(card.get("scope_status"), limit=42))} · 기준일 {html.escape(recommendation_date)}</text>
  {''.join(metric_rects)}
  {''.join(metric_texts)}
  <rect x="74" y="696" width="932" height="242" rx="20" fill="#0d253b" stroke="#2d6a85" stroke-width="2"/>
  <text x="102" y="744" fill="#6ee7e0" font-size="27" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">핵심 논거</text>
  {_svg_text_lines(card.get("thesis"), x=102, y=786, size=28, fill="#ffffff", line_height=39, line_width=52, line_limit=2, weight=800, limit=150)}
  {''.join(reason_rows)}
  <rect x="74" y="962" width="932" height="226" rx="20" fill="#14283d" stroke="#765a4b" stroke-width="2"/>
  <text x="102" y="1012" fill="#f5c071" font-size="27" font-weight="900" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">리스크 · 다음 확인</text>
  {''.join(risk_rows)}
  <text x="102" y="1136" fill="#fef3c7" font-size="22" font-weight="750" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">검토 기준: {html.escape(_clean_text(card.get("guardrail"), limit=58))}</text>
  <text x="102" y="1172" fill="#a9bbcb" font-size="19" font-weight="650" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">근거: {html.escape(_clean_text(card.get("evidence_summary"), limit=95))}</text>
  <path d="M74 1224 H1006" stroke="#2d6a85" stroke-width="2"/>
  <text x="74" y="1264" fill="#9cb0c0" font-size="19" font-weight="700" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">{html.escape(DISCLAIMER)}</text>
  <text x="74" y="1304" fill="#6ee7e0" font-size="18" font-weight="800" font-family="Malgun Gothic, Noto Sans KR, Arial, sans-serif">근거 강도 {html.escape(_clean_text(card.get("confidence"), limit=16))} · 사람 검토 필수</text>
</svg>'''


def _write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def read_daily_family_top_pick_card(settings: Settings) -> dict[str, Any]:
    stored = read_json_store(daily_top_pick_card_state_path(settings), {})
    if not stored:
        return _attach_schedule(
            settings,
            _missing_payload(build_family_candidate_scope(settings), "오늘의 한 종목 카드가 아직 생성되지 않았습니다."),
        )
    payload = {**stored}
    recommendation_date = str(payload.get("recommendation_date") or "")
    payload["is_current"] = recommendation_date == current_storage_date().isoformat()
    payload.setdefault("module", MODULE)
    payload.setdefault("disclaimer", DISCLAIMER)
    return _attach_schedule(settings, payload)


def run_daily_family_top_pick_card(
    settings: Settings,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Persist the latest card and its SVG asset using local research state only."""
    payload = build_daily_family_top_pick_card(settings)
    existing = read_json_store(daily_top_pick_card_state_path(settings), {})
    same_source = (
        existing.get("recommendation_date") == payload.get("recommendation_date")
        and (existing.get("selection") or {}).get("source_fingerprint")
        == (payload.get("selection") or {}).get("source_fingerprint")
        and (existing.get("scope") or {}).get("scope_fingerprint")
        == (payload.get("scope") or {}).get("scope_fingerprint")
        and existing.get("status") == payload.get("status")
    )
    if same_source and not force:
        return _attach_schedule(
            settings,
            {
                **existing,
                "generation_status": "skipped_existing",
                "message": "동일한 후보 범위와 당일 추천 데이터로 만든 카드가 이미 저장되어 있습니다.",
            },
        )

    recommendation_date = str(payload.get("recommendation_date") or "")
    if recommendation_date:
        svg_path = daily_top_pick_card_svg_path(settings, recommendation_date)
        _write_svg(svg_path, render_daily_family_top_pick_svg(payload))
        payload["asset"] = {
            "format": "svg",
            "file_name": svg_path.name,
            "image_api_path": "/api/v1/daily-top-pick/card.svg",
        }
    payload["generation_status"] = "generated"
    write_json_store(daily_top_pick_card_state_path(settings), payload)
    return _attach_schedule(settings, payload)


def read_daily_family_top_pick_svg(settings: Settings) -> tuple[str | None, str | None]:
    payload = read_daily_family_top_pick_card(settings)
    recommendation_date = str(payload.get("recommendation_date") or "")
    if not recommendation_date:
        return None, None
    path = daily_top_pick_card_svg_path(settings, recommendation_date)
    if not path.exists():
        return None, path.name
    try:
        return path.read_text(encoding="utf-8"), path.name
    except OSError:
        return None, path.name
