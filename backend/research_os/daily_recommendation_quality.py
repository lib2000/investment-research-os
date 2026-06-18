"""Storage quality scoring helpers for daily recommendations."""

from __future__ import annotations

from typing import Any

from research_os import daily_recommendation_candidates
from research_os import daily_recommendation_evidence
from research_os.storage_quality import (
    is_archived_research_entry,
    storage_quality_entry_is_policy_url_only,
    storage_quality_entry_needs_body,
    storage_quality_entry_needs_ocr,
)


def daily_recommendation_manifest_quality_by_ticker(
    manifest_entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    quality_by_ticker: dict[str, dict[str, Any]] = {}
    for entry in manifest_entries:
        if not isinstance(entry, dict):
            continue
        ticker = daily_recommendation_evidence.normalize_recommendation_ticker(entry.get("ticker"))
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


def apply_daily_recommendation_storage_quality(candidate: dict[str, Any], quality: dict[str, Any] | None) -> None:
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
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 8, "검증 저장자료 품질")
    elif high_quality_count > 0:
        daily_recommendation_candidates.add_daily_recommendation_score(candidate, 3, "검증 저장자료 품질")
    else:
        candidate.setdefault("quality_flags", []).append("검증된 활성 저장자료 부족")
        add_points = 3 if active_count else 5
        daily_recommendation_candidates.add_daily_recommendation_penalty(
            candidate,
            "검증된 활성 저장자료 부족",
            add_points,
        )
    if duplicate_count:
        penalty = min(8, max(2, duplicate_count))
        daily_recommendation_candidates.add_daily_recommendation_penalty(
            candidate,
            "중복 의심 저장자료 대표화 필요",
            penalty,
        )
        candidate.setdefault("quality_flags", []).append("중복 의심 자료는 대표 자료만 근거로 사용")
    if body_missing_count or ocr_needed_count:
        penalty = min(10, (body_missing_count * 3) + (ocr_needed_count * 3))
        daily_recommendation_candidates.add_daily_recommendation_penalty(
            candidate,
            "본문/OCR 보강 필요 자료 존재",
            penalty,
        )
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
