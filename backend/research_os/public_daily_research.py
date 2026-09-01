"""Build a privacy-safe static feed for the public Daily Research homepage.

The internal research system can use family portfolios, watchlists, cached
documents, and ranking data. This module is the explicit boundary between that
private workspace and a public page: it only returns a small, review-oriented
subset that is safe to publish after the normal daily card has been created.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from research_os.daily_family_top_pick import read_daily_family_top_pick_card
from research_os.daily_recommendation_store import read_daily_recommendation_store
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings
from research_os.state_store import current_storage_date, current_storage_timestamp


SCHEMA_VERSION = "1.0"
SITE_NAME = "X10THINK Daily Research"
PUBLICATION_START_DATE = date(2026, 9, 1)
PUBLIC_DISCLAIMER = (
    "공개 정보와 검증된 리서치 근거를 정리한 참고용 기록. "
    "매수·매도 지시 없음. 투자 판단과 손실 책임은 본인에게."
)
PRIVATE_TEXT_MARKERS = (
    "가족",
    "보유 종목",
    "관심 종목",
    "portfolio",
    "holding",
    "watchlist",
    "dossier",
    "팀 리포트",
    "저장 품질",
    "저장된 ",
    "저장자료",
    "저장 데이터",
    "추천 후",
    "내부 메모",
    "참고자료)",
)


def public_daily_research_default_output_path(project_root: Path) -> Path:
    return project_root / "apps" / "daily-research-site" / "data" / "public-daily-research.json"


def _clean_text(value: object, *, limit: int = 180, fallback: str = "") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return fallback
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)].rstrip()}…"


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return int(number)


def _valid_iso_date(value: object) -> str | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _is_public_issue_date(value: str | None) -> bool:
    return bool(value and value >= PUBLICATION_START_DATE.isoformat())


def _public_text(value: object, *, limit: int = 160, fallback: str = "") -> str:
    text = _clean_text(value, limit=limit, fallback="")
    lowered = text.casefold()
    if not text or any(marker.casefold() in lowered for marker in PRIVATE_TEXT_MARKERS):
        return fallback
    text = re.sub(r"https?://\S+", "", text).strip(" -|")
    return _clean_text(text, limit=limit, fallback=fallback)


def _public_list(values: object, *, limit: int, fallback: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values if isinstance(values, list) else []:
        text = _public_text(value, limit=130)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
        if len(result) >= limit:
            break
    for item in fallback:
        if len(result) >= limit:
            break
        text = _clean_text(item, limit=130)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result[:limit]


def _source_type(value: object) -> str:
    text = str(value or "").casefold()
    if any(marker in text for marker in ("sec", "dart", "공시", "filing")):
        return "공시 원문"
    if any(marker in text for marker in ("ir", "investor relations", "기업 자료")):
        return "기업 IR"
    if any(marker in text for marker in ("실적", "earnings", "transcript")):
        return "실적 자료"
    if any(marker in text for marker in ("정책", "산업", "통상", "market")):
        return "산업·정책 자료"
    return "검증된 리서치 근거"


def _source_types(values: object) -> list[str]:
    result: list[str] = []
    for value in values if isinstance(values, list) else []:
        text = _public_text(value, limit=96)
        if not text:
            continue
        label = _source_type(text)
        if label not in result:
            result.append(label)
    return result or ["공시 원문", "기업 IR", "실적 자료"]


def _metric_value(card: dict[str, Any], label: str) -> str | None:
    for metric in card.get("metrics", []) if isinstance(card.get("metrics"), list) else []:
        if not isinstance(metric, dict) or str(metric.get("label") or "").strip() != label:
            continue
        value = _public_text(metric.get("value"), limit=48)
        if value and value != "확인 필요":
            return value
    return None


def _public_latest_card(top_pick: dict[str, Any], *, publication_state: str) -> dict[str, Any] | None:
    card = top_pick.get("card")
    if not isinstance(card, dict) or publication_state not in {"published", "awaiting_daily_refresh"}:
        return None

    evidence_strength = card.get("evidence_strength")
    evidence_strength = evidence_strength if isinstance(evidence_strength, dict) else {}
    grade = str(evidence_strength.get("grade") or "").upper()
    if grade not in {"A", "B", "C"}:
        grade = "검토 필요"
    document_count = max(0, _safe_int(evidence_strength.get("document_count")))
    recent_30d_count = max(0, _safe_int(evidence_strength.get("recent_30d_count")))
    next_review = card.get("next_review")
    next_review = next_review if isinstance(next_review, dict) else {}
    target_date = _valid_iso_date(next_review.get("target_date")) or "추후 공지"
    company_name = _clean_text(card.get("company_name"), limit=64, fallback="종목 정보 준비 중")
    ticker = _clean_text(card.get("ticker"), limit=16, fallback="-").upper()
    market = _clean_text(card.get("market"), limit=16, fallback="시장 확인 중")
    baseline_price = _metric_value(card, "기준 가격")

    metrics = [
        {
            "label": "근거 품질",
            "value": grade,
            "detail": f"최근 30일 기준 문서 {recent_30d_count}건",
        },
        {
            "label": "근거 문서",
            "value": f"{document_count}건",
            "detail": "공시·IR·실적·산업 자료를 대조",
        },
        {
            "label": "다음 확인",
            "value": target_date,
            "detail": _public_text(next_review.get("label"), limit=48, fallback="후속 공개 자료 점검"),
        },
    ]
    if baseline_price:
        metrics.insert(
            2,
            {
                "label": "기준 가격",
                "value": baseline_price,
                "detail": "리서치 생성 당시 기준 · 실시간 시세 아님",
            },
        )

    reasons = _public_list(
        card.get("reasons"),
        limit=3,
        fallback=[
            "공개 원문과 최근 업데이트를 함께 대조.",
            "근거가 약해지면 우선순위 재검토.",
        ],
    )
    risks = _public_list(
        card.get("risks"),
        limit=3,
        fallback=[
            "기준 가격은 실시간 시세가 아님. 변동성이 클 때는 판단 보류.",
            "신규 공시·실적 발표 시 핵심 논거와 리스크 재확인.",
        ],
    )
    source_types = _source_types(card.get("evidence"))
    report_date = _valid_iso_date(top_pick.get("recommendation_date"))

    return {
        "id": f"{report_date or 'undated'}-{ticker.lower()}",
        "edition_label": "오늘의 리서치" if publication_state == "published" else "최근 발행 리서치",
        "report_date": report_date,
        "published_at": _clean_text(top_pick.get("generated_at"), limit=40, fallback=None),
        "company_name": company_name,
        "ticker": ticker,
        "market": market,
        "stance": "근거 우선 검토",
        "headline": _public_text(
            card.get("thesis"),
            limit=150,
            fallback="핵심 원문과 최근 업데이트 중심의 우선 검토 기록.",
        ),
        "metrics": metrics[:4],
        "reasons": reasons,
        "risks": risks,
        "evidence": {
            "grade": grade,
            "document_count": document_count,
            "recent_30d_count": recent_30d_count,
            "source_types": source_types,
            "review_gate": "핵심 원문 재확인 뒤 검토",
        },
        "next_review": {
            "date": target_date,
            "label": _public_text(next_review.get("label"), limit=48, fallback="후속 공개 자료 점검"),
        },
        "disclaimer": PUBLIC_DISCLAIMER,
    }


def _archive_sort_key(record: dict[str, Any]) -> tuple[str, float, float, str]:
    quality = record.get("evidence_quality_summary")
    quality = quality if isinstance(quality, dict) else {}
    score = _safe_int(record.get("score"), default=-1)
    quality_score = _safe_int(quality.get("score"), default=-1)
    return (
        str(record.get("recommendation_date") or ""),
        score,
        quality_score,
        str(record.get("ticker") or "").upper(),
    )


def _public_archive(
    recommendations: dict[str, Any],
    *,
    start_date: str = PUBLICATION_START_DATE.isoformat(),
    limit: int = 12,
) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    records = recommendations.get("records", [])
    for raw in records if isinstance(records, list) else []:
        if not isinstance(raw, dict):
            continue
        report_date = _valid_iso_date(raw.get("recommendation_date"))
        ticker = _clean_text(raw.get("ticker"), limit=16).upper()
        if not report_date or report_date < start_date or not ticker:
            continue
        by_date.setdefault(report_date, []).append(raw)

    archive: list[dict[str, Any]] = []
    for report_date in sorted(by_date, reverse=True):
        records = by_date[report_date]
        eligible = [
            item
            for item in records
            if not bool(
                (item.get("evidence_quality_summary") if isinstance(item.get("evidence_quality_summary"), dict) else {})
                .get("blocks_buy_decision")
            )
        ]
        selected = max(eligible or records, key=_archive_sort_key)
        quality = selected.get("evidence_quality_summary")
        quality = quality if isinstance(quality, dict) else {}
        grade = str(quality.get("grade") or "검토 필요").upper()
        if grade not in {"A", "B", "C"}:
            grade = "검토 필요"
        archive.append(
            {
                "report_date": report_date,
                "company_name": _clean_text(selected.get("company_name") or selected.get("ticker"), limit=64),
                "ticker": _clean_text(selected.get("ticker"), limit=16).upper(),
                "market": _clean_text(
                    selected.get("market_label") or selected.get("market"),
                    limit=16,
                    fallback="시장 확인 중",
                ),
                "evidence_grade": grade,
                "evidence_document_count": max(0, _safe_int(quality.get("document_count"))),
                "label": "발행 기록",
            }
        )
        if len(archive) >= limit:
            break
    return archive


def _public_freshness(evidence_status: dict[str, Any]) -> dict[str, Any]:
    checks = evidence_status.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    successful = sum(
        1
        for value in checks.values()
        if isinstance(value, dict) and str(value.get("status") or "").lower() == "success"
    )
    return {
        "evidence_refreshed_at": _clean_text(evidence_status.get("as_of"), limit=40, fallback=None),
        "source_refresh_status": "점검 완료" if successful else "점검 기록 준비 중",
        "source_categories": ["공시 원문", "기업 IR", "실적 자료", "산업·정책 자료"],
    }


def build_public_daily_research_feed(
    top_pick: dict[str, Any],
    recommendations: dict[str, Any],
    evidence_status: dict[str, Any] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Transform private inputs into a static, privacy-safe public feed."""

    today_value = (today or current_storage_date()).isoformat()
    publication_start_date = PUBLICATION_START_DATE.isoformat()
    card = top_pick.get("card") if isinstance(top_pick.get("card"), dict) else None
    recommendation_date = _valid_iso_date(top_pick.get("recommendation_date"))
    status = str(top_pick.get("status") or "").lower()
    if not card:
        publication_state = "unavailable"
        publication_message = "오늘 발행할 리서치 카드 준비 중."
    elif not _is_public_issue_date(recommendation_date):
        publication_state = "awaiting_first_issue"
        publication_message = f"공개 발행 이력은 {publication_start_date}부터. 첫 리서치 준비 중."
    elif status == "review_hold":
        publication_state = "review_hold"
        publication_message = "오늘 후보는 근거 보강 중. 공개 발행은 보류."
    elif recommendation_date != today_value:
        publication_state = "awaiting_daily_refresh"
        publication_message = "오늘 리서치 준비 중. 아래에는 최근 발행 이력."
    else:
        publication_state = "published"
        publication_message = "오늘 리서치 발행 완료. 핵심 원문과 리스크 확인."

    return {
        "schema_version": SCHEMA_VERSION,
        "site": {
            "name": SITE_NAME,
            "tagline": "하루 한 종목, 근거와 리스크를 한 장에.",
            "description": "공시·IR·실적·산업 자료를 대조한 하루 한 종목 리서치 기록",
        },
        "generated_at": current_storage_timestamp(),
        "publication": {
            "state": publication_state,
            "message": publication_message,
            "report_date": recommendation_date,
            "archive_start_date": publication_start_date,
            "next_scheduled_issue": "매일 08:00 KST 이후",
        },
        "latest": _public_latest_card(top_pick, publication_state=publication_state),
        "archive": _public_archive(recommendations, start_date=publication_start_date),
        "methodology": {
            "summary": "후보 점검, 공개 원문·최신성 대조, 리스크와 다음 확인 일정 기록.",
            "steps": [
                "공시·IR·실적·산업 자료 수집",
                "근거 품질과 최신성 점검",
                "리스크와 다음 확인 일정 기록",
            ],
            "human_review": "자동 주문·매매 실행과 분리된 리서치 기록.",
        },
        "data_freshness": _public_freshness(evidence_status or {}),
        "disclaimer": PUBLIC_DISCLAIMER,
    }


def _evidence_status_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "research_evidence_pipeline_status.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def get_public_daily_research_feed(settings: Settings) -> dict[str, Any]:
    return build_public_daily_research_feed(
        read_daily_family_top_pick_card(settings),
        read_daily_recommendation_store(settings),
        _read_json(_evidence_status_path(settings)),
    )


def write_public_daily_research_feed(settings: Settings, output_path: Path) -> dict[str, Any]:
    """Write the sanitized feed atomically; no private source file is modified."""

    payload = get_public_daily_research_feed(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)
    return payload
