"""Duplicate-review and Dossier refresh queue workflows."""

from __future__ import annotations

from pathlib import Path
from re import fullmatch, search
from typing import Protocol

from research_os import dossier_synthesis
from research_os.dossier_text import (
    DOSSIER_ALLOWED_REPORT_TYPES,
    compact_representative_sentence,
    content_fingerprint,
    is_allowed_dossier_source_entry,
    is_dossier_noise_line,
    manifest_entry_sort_key,
    manifest_similarity_text,
    plain_research_lines,
    read_manifest_entry_text,
    similarity_tokens,
    token_jaccard_similarity,
)
from research_os.models import InvestmentThesis, WatchItem
from research_os.settings import Settings


class DossierQueueRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def compact_manifest_review_entry(runtime: DossierQueueRuntime, entry: dict) -> dict:
    return {
        "ticker": entry.get("ticker"),
        "company_name": entry.get("company_name"),
        "type": entry.get("type"),
        "date": entry.get("date"),
        "title": entry.get("title") or entry.get("file_name") or "제목 없음",
        "summary": compact_representative_sentence(entry.get("summary") or "", 180),
        "file_name": entry.get("file_name"),
        "relative_path": entry.get("relative_path"),
        "source_url": entry.get("source_url"),
    }


def build_storage_duplicate_review(
    runtime: DossierQueueRuntime,
    settings,
    *,
    limit: int = 80,
    save_result: bool = True,
) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = [
        entry
        for entry in runtime.read_manifest(vault_dir)
        if isinstance(entry, dict)
        and str(entry.get("type") or "").strip().lower() in DOSSIER_ALLOWED_REPORT_TYPES
    ]
    archived_input_count = sum(1 for entry in manifest_entries if runtime.is_archived_research_entry(entry))
    manifest_entries = [entry for entry in manifest_entries if not runtime.is_archived_research_entry(entry)]
    manifest_entries.sort(key=manifest_entry_sort_key, reverse=True)

    representatives: list[dict] = []
    groups: list[dict] = []
    exact_keys: dict[str, int] = {}
    token_sets: list[set[str]] = []
    checked_count = 0

    for entry in manifest_entries[: max(limit * 10, 200)]:
        text = read_manifest_entry_text(vault_dir, entry)
        if not plain_research_lines(text, limit=3) and is_dossier_noise_line(entry.get("summary")):
            continue
        checked_count += 1
        exact_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(manifest_similarity_text(entry, text))
        )
        tokens = similarity_tokens(manifest_similarity_text(entry, text))
        match_index: int | None = None
        reason = "no_match"
        similarity = 0.0

        if exact_key and exact_key in exact_keys:
            match_index = exact_keys[exact_key]
            reason = "exact_match"
            similarity = 1.0
        else:
            best: tuple[float, int] | None = None
            for index, previous_tokens in enumerate(token_sets):
                current_ticker = str(entry.get("ticker") or "").upper()
                previous_ticker = str((representatives[index] if index < len(representatives) else {}).get("ticker") or "").upper()
                same_scope = current_ticker == previous_ticker or (
                    current_ticker in runtime.special_research_keys and previous_ticker in runtime.special_research_keys
                )
                if not same_scope:
                    continue
                if len(tokens) < 8 or len(previous_tokens) < 8:
                    continue
                score = token_jaccard_similarity(tokens, previous_tokens)
                if score >= 0.84 and (best is None or score > best[0]):
                    best = (score, index)
            if best is not None:
                similarity, match_index = best
                reason = "title_body_similarity"

        if match_index is None:
            exact_keys[exact_key] = len(representatives)
            token_sets.append(tokens if tokens else set())
            representatives.append(entry)
            continue

        while len(groups) <= match_index:
            representative = representatives[len(groups)] if len(groups) < len(representatives) else {}
            groups.append(
                {
                    "group_id": content_fingerprint(
                        f"{representative.get('ticker')} {representative.get('file_name')} {representative.get('source_url')}"
                    )[:16],
                    "ticker": representative.get("ticker"),
                    "company_name": representative.get("company_name"),
                    "representative": compact_manifest_review_entry(runtime, representative),
                    "duplicates": [],
                    "duplicate_count": 0,
                    "excluded_duplicate_count": 0,
                    "dossier_usage": "representative_only",
                    "duplicate_usage": "excluded_from_dossier",
                    "reasons": {},
                    "recommended_action": "대표 자료 1개만 Dossier 합성에 사용하고, 중복 자료는 복기용 원문으로만 유지합니다.",
                }
            )

        group = groups[match_index]
        group["duplicates"].append(
            {
                **compact_manifest_review_entry(runtime, entry),
                "duplicate_reason": reason,
                "similarity": round(similarity, 4),
            }
        )
        group["duplicate_count"] = len(group["duplicates"])
        group["excluded_duplicate_count"] = group["duplicate_count"]
        reasons = group.setdefault("reasons", {})
        reasons[reason] = int(reasons.get(reason) or 0) + 1

    groups = [group for group in groups if group.get("duplicate_count")]
    groups.sort(key=lambda item: int(item.get("duplicate_count") or 0), reverse=True)
    groups = groups[: max(limit, 1)]
    duplicate_entry_count = sum(int(group.get("duplicate_count") or 0) for group in groups)

    ticker_breakdown: dict[str, dict] = {}
    for group in groups:
        key = str(group.get("ticker") or "UNKNOWN")
        item = ticker_breakdown.setdefault(
            key,
            {
                "ticker": key,
                "company_name": group.get("company_name"),
                "duplicate_group_count": 0,
                "duplicate_entry_count": 0,
            },
        )
        item["duplicate_group_count"] += 1
        item["duplicate_entry_count"] += int(group.get("duplicate_count") or 0)

    payload = {
        "status": "success",
        "module": "storage_duplicate_review",
        "as_of": runtime.current_storage_timestamp(),
        "checked_count": checked_count,
        "skipped_archived_count": archived_input_count,
        "unique_representative_count": len(representatives),
        "duplicate_group_count": len(groups),
        "duplicate_entry_count": duplicate_entry_count,
        "representative_policy": {
            "dossier_usage": "representative_only",
            "duplicate_usage": "excluded_from_dossier",
            "archive_policy": "soft_archive_only",
            "hard_delete_allowed": False,
            "message": "Dossier 합성과 추천 근거에는 대표 자료만 사용하고 중복 의심 자료는 복기/원문 추적용으로 유지합니다.",
        },
        "dossier_usage_summary": {
            "representative_count": len(representatives),
            "duplicate_excluded_count": duplicate_entry_count,
            "archived_excluded_count": archived_input_count,
            "needs_dossier_refresh_count": len(ticker_breakdown),
        },
        "groups": groups,
        "ticker_breakdown": sorted(
            ticker_breakdown.values(),
            key=lambda item: (int(item.get("duplicate_entry_count") or 0), int(item.get("duplicate_group_count") or 0)),
            reverse=True,
        )[:20],
        "next_actions": [
            "Dossier 합성/추천 근거에는 representative_only 정책을 적용해 중복 의심 자료를 제외했습니다.",
            "중복 의심이 많은 종목부터 Dossier 재합성을 실행해 최신 투자 논거를 다시 고정하세요.",
            "source_url/content_hash 일치 자료는 사실상 같은 자료로 보고 대표 자료만 의사결정에 반영하세요.",
            "제목·본문 유사 자료는 원문이 다른 업데이트일 수 있으므로 요약 차이가 있는지 우선 확인하세요.",
        ],
    }
    if save_result:
        runtime.write_json_store(runtime.storage_duplicate_review_path(settings), payload)
        payload["storage"] = {
            "relative_path": str(runtime.storage_duplicate_review_path(settings).relative_to(vault_dir.parent)).replace("\\", "/")
        }
    return payload


def build_dossier_payload(runtime: DossierQueueRuntime, ticker: str, vault_dir: Path) -> dict:
    return dossier_synthesis.build_dossier_payload(runtime, ticker, vault_dir)


def render_dossier_markdown(payload: dict) -> str:
    return dossier_synthesis.render_dossier_markdown(payload)


def synthesize_and_save_dossier(
    runtime: DossierQueueRuntime,
    ticker: str,
    settings: Settings,
    *,
    save_result: bool = True,
) -> dict:
    normalized_ticker = runtime.ensure_verified_ticker(ticker, settings)
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    payload = build_dossier_payload(runtime, normalized_ticker, vault_dir)
    if int(payload.get("source_count") or 0) <= 0:
        # Do not turn fallback wording into a persisted investment thesis.
        # The preview endpoint intentionally returns this structured state too,
        # so every client sees the same evidence gate before an action is saved.
        return dossier_synthesis.build_insufficient_evidence_result(payload)
    storage = None
    if save_result:
        markdown = render_dossier_markdown(payload)
        storage = runtime.save_research_markdown(
            vault_dir=vault_dir,
            ticker=normalized_ticker,
            report_type="dossier-synthesis",
            markdown=markdown,
            structured_payload=payload,
            manifest_entry=runtime.manifest_with_ticker_verification(normalized_ticker, {
                "summary": payload["thesis_summary"],
                "company_name": payload["company_name"],
                "source_count": payload["source_count"],
                "duplicate_count": payload["duplicate_count"],
                "source_confidence": payload["confidence"],
                "tags": payload["tags"],
                "investment_thesis": {
                    "ticker": normalized_ticker,
                    "thesis": payload["thesis_summary"],
                    "time_horizon": "상시 업데이트",
                    "bull_triggers": payload["bull_thesis"],
                    "bear_triggers": payload["bear_thesis"],
                    "invalidation_conditions": payload["invalidation_conditions"],
                    "watch_kpis": runtime.ticker_watch_kpis(normalized_ticker),
                    "valuation_assumptions": {
                        "method": "저장 자료 기반 Dossier 합성",
                        "confidence": payload["confidence"],
                    },
                    "last_updated": payload["date"],
                },
                "watch_items": [
                    {
                        "ticker": normalized_ticker,
                        "metric": item.split(":")[0],
                        "condition": item,
                        "action": "다음 정보 입력/시장일지/실적 분석에서 자동 대조",
                        "priority": "medium",
                    }
                    for item in payload["observables"][:5]
                ],
            }),
            report_date=runtime.current_storage_date(),
        )
        payload["storage"] = storage.model_dump(mode="json")
        thesis = InvestmentThesis(
            ticker=normalized_ticker,
            thesis=payload["thesis_summary"],
            time_horizon="상시 업데이트",
            bull_triggers=payload["bull_thesis"],
            bear_triggers=payload["bear_thesis"],
            invalidation_conditions=payload["invalidation_conditions"],
            watch_kpis=runtime.ticker_watch_kpis(normalized_ticker),
            valuation_assumptions={
                "method": "저장 자료 기반 Dossier 합성",
                "confidence": payload["confidence"],
            },
            last_updated=payload["date"],
        )
        watch_items = [
            WatchItem(
                ticker=normalized_ticker,
                metric=item.split(":")[0],
                condition=item,
                action="다음 정보 입력/시장일지/실적 분석에서 자동 대조",
                priority="medium",
            )
            for item in payload["observables"][:5]
        ]
        runtime.upsert_ticker_thesis_snapshot(
            vault_dir=vault_dir,
            ticker=normalized_ticker,
            company_name=payload["company_name"],
            investment_thesis=thesis,
            watch_items=watch_items,
            source_entry={
                "type": "dossier-synthesis",
                "date": payload["date"],
                "file_name": storage.file_name if storage else None,
                "relative_path": storage.relative_path if storage else None,
            },
            confidence=payload["confidence"],
        )
    return {"status": "success", "module": "dossier_synthesis", **payload}


def dossier_candidate_tickers(runtime: DossierQueueRuntime, settings: Settings, limit: int = 30) -> list[str]:
    tickers: set[str] = set()
    for ticker in runtime.portfolio_calendar_tickers(settings):
        normalized = runtime.normalize_ticker(ticker)
        if is_dossier_refresh_ticker_key(runtime, normalized):
            tickers.add(normalized)
    try:
        interest_payload = runtime.read_interest_list(settings)
        for item in interest_payload.get("tickers", []):
            if isinstance(item, dict) and item.get("ticker"):
                tickers.add(runtime.ensure_verified_ticker(str(item["ticker"]), settings))
    except Exception:
        pass
    try:
        vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
        for entry in runtime.read_manifest(vault_dir):
            ticker = runtime.normalize_ticker(str(entry.get("ticker") or ""))
            if is_dossier_refresh_ticker_key(runtime, ticker):
                tickers.add(ticker)
    except Exception:
        pass
    return sorted(tickers)[: max(1, min(limit, 100))]

def is_dossier_refresh_ticker_key(runtime: DossierQueueRuntime, ticker: str) -> bool:
    normalized = runtime.normalize_ticker(ticker)
    if (
        not normalized
        or normalized in runtime.special_research_keys
        or normalized in {"UNKNOWN", "CASH"}
        or normalized.startswith("COMPOUNDER-")
        or "-" in normalized
    ):
        return False
    if fullmatch(r"\d{6}", normalized):
        return True
    if fullmatch(r"[A-Z]{1,5}", normalized):
        return True
    if fullmatch(r"[A-Z0-9]{6}", normalized) and search(r"[A-Z]", normalized):
        return True
    return False


def has_verified_dossier_source(runtime: DossierQueueRuntime, settings, ticker: str) -> bool:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    normalized = runtime.normalize_ticker(ticker)
    for entry in runtime.read_manifest(vault_dir):
        if not isinstance(entry, dict):
            continue
        if runtime.normalize_ticker(str(entry.get("ticker") or "")) != normalized:
            continue
        if not is_allowed_dossier_source_entry(entry):
            continue
        if runtime.is_verified_manifest_entry(entry, normalized):
            return True
    return False


def dossier_refresh_candidates_from_duplicate_review(runtime: DossierQueueRuntime, settings, limit: int = 8) -> list[dict]:
    review = runtime.read_json_store(runtime.storage_duplicate_review_path(settings), {})
    if not review:
        review = runtime.build_storage_duplicate_review(settings, limit=max(limit * 3, 20), save_result=False)
    candidates: list[dict] = []
    seen: set[str] = set()
    for item in review.get("ticker_breakdown") or []:
        ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
        if not is_dossier_refresh_ticker_key(runtime, ticker) or ticker in seen:
            continue
        if not has_verified_dossier_source(runtime, settings, ticker):
            continue
        seen.add(ticker)
        candidates.append(
            {
                "ticker": ticker,
                "company_name": item.get("company_name") or runtime.ticker_company_name(ticker),
                "duplicate_group_count": int(item.get("duplicate_group_count") or 0),
                "duplicate_entry_count": int(item.get("duplicate_entry_count") or 0),
                "reason": "중복 리뷰에서 대표 자료 재합성이 필요한 종목으로 선별됨",
            }
        )
        if len(candidates) >= max(limit, 1):
            break
    return candidates


def run_deduped_dossier_refresh_queue(
    runtime: DossierQueueRuntime,
    settings,
    *,
    limit: int = 8,
    save_result: bool = True,
) -> dict:
    candidates = runtime.dossier_refresh_candidates_from_duplicate_review(settings, limit=limit)
    refreshed: list[dict] = []
    failed: list[dict] = []
    skipped: list[dict] = []

    for candidate in candidates:
        ticker = candidate["ticker"]
        try:
            preview = runtime.synthesize_and_save_dossier(ticker, settings, save_result=False)
            if int(preview.get("source_count") or 0) <= 0:
                skipped.append({**candidate, "reason": "Dossier에 사용할 검증된 고유 자료가 없어 저장을 건너뜀"})
                continue
            result = runtime.synthesize_and_save_dossier(ticker, settings, save_result=save_result)
            refreshed.append(
                {
                    "ticker": ticker,
                    "company_name": result.get("company_name") or candidate.get("company_name"),
                    "source_count": result.get("source_count"),
                    "duplicate_count": result.get("duplicate_count"),
                    "confidence": result.get("confidence"),
                    "storage": result.get("storage"),
                    "reason": candidate.get("reason"),
                }
            )
        except Exception as exc:
            message = runtime.provider_error_message(exc, settings)
            if "공식 티커" in message or "확인되지 않았습니다" in message:
                skipped.append({**candidate, "reason": message})
            else:
                failed.append({**candidate, "error": message})

    payload = {
        "status": "success" if not failed else "partial",
        "module": "deduped_dossier_refresh_queue",
        "as_of": runtime.current_storage_timestamp(),
        "candidate_count": len(candidates),
        "refreshed_count": len(refreshed),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "candidates": candidates,
        "refreshed": refreshed,
        "failed": failed,
        "skipped": skipped,
        "next_actions": [
            "갱신된 Dossier의 강세/약세 논거가 대시보드 최신 투자 논거에 반영됐는지 확인하세요.",
            "실패 또는 스킵 종목은 티커 인증 상태와 원천 저장 자료 품질을 먼저 점검하세요.",
            "중복 리뷰가 새로 생성되면 이 큐를 다시 실행해 대표 자료 기준을 갱신하세요.",
        ],
    }
    if save_result:
        runtime.write_json_store(runtime.dossier_refresh_queue_status_path(settings), payload)
        status = runtime.read_json_store(runtime.research_automation_status_path(settings), {})
        if isinstance(status, dict):
            duplicate_review = runtime.read_json_store(runtime.storage_duplicate_review_path(settings), {})
            if isinstance(duplicate_review, dict):
                status["duplicate_suspected_count"] = int(duplicate_review.get("duplicate_entry_count") or 0)
                status["duplicate_group_count"] = int(duplicate_review.get("duplicate_group_count") or 0)
            status["updated_at"] = payload["as_of"]
            status["last_deduped_dossier_refresh"] = {
                "updated_at": payload["as_of"],
                "candidate_count": payload["candidate_count"],
                "refreshed_count": payload["refreshed_count"],
                "failed_count": payload["failed_count"],
                "skipped_count": payload["skipped_count"],
            }
            runtime.write_json_store(runtime.research_automation_status_path(settings), status)
    return payload
