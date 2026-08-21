"""Shared portfolio analysis module coverage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_PORTFOLIO_ANALYSIS_MODULES = [
    ("team_report", "기준 리포트", {"collaborative-team-report", "institutional-stock-breakdown", "dossier-synthesis"}),
    ("trade_setup", "매매 전략", {"smart-trade-setup", "trade-setup", "strategy"}),
    ("earnings_reaction", "실적 분석", {"earnings-reaction", "earnings-release", "earnings", "public-ir-sec"}),
    ("model_update_note", "모델 업데이트 노트", {"earnings-filing-note", "model-update", "dossier-synthesis"}),
    ("checklist", "체크리스트", {"research-checklist", "checklist"}),
    ("recent_capture", "최근 정보 입력", {"research-capture", "public-ir-sec", "dart-filing-watch", "chart-analysis"}),
]

# A saved checklist is evidence that the workflow was started, not evidence that
# the human review is complete. The dashboard already uses 75% as its practical
# readiness boundary, so coverage uses the same gate.
REVIEW_CHECKLIST_COMPLETION_THRESHOLD = 0.75

# A human-review packet is an evidence inventory only.  It must never make a
# position look documented or approved simply because the source links were
# gathered automatically.
HUMAN_REVIEW_PACKET_TYPE = "human-review-packet"


def normalize_portfolio_analysis_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def _as_optional_ratio(value: Any) -> float | None:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return None
    if ratio < 0 or ratio > 1:
        return None
    return ratio


def _as_optional_count(value: Any) -> int | None:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (
        str(entry.get("date") or entry.get("created_at") or entry.get("saved_at") or ""),
        str(entry.get("file_name") or entry.get("storage_path") or ""),
    )


def portfolio_vault_entries(vault_dir: Path, tickers: list[str]) -> list[dict[str, Any]]:
    """Read ticker-folder JSON evidence and mark only path-consistent files as local evidence."""
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ticker_value in tickers:
        ticker = normalize_portfolio_analysis_ticker(ticker_value)
        if not ticker or ticker in {"CASH", "UNKNOWN"}:
            continue
        folder = vault_dir / ticker
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            key = (ticker, path.name)
            if key in seen:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            item = payload if isinstance(payload, dict) else {}
            payload_ticker = normalize_portfolio_analysis_ticker(
                item.get("ticker")
                or (item.get("captured_item") or {}).get("ticker")
                if isinstance(item.get("captured_item"), dict)
                else item.get("ticker")
            )
            if payload_ticker and payload_ticker != ticker:
                continue
            seen.add(key)
            data_quality = item.get("data_quality")
            quality_payload = data_quality if isinstance(data_quality, dict) else {}
            injected_data = item.get("injected_data")
            entries.append(
                {
                    "ticker": ticker,
                    "file_name": path.name,
                    "date": item.get("date") or item.get("created_at") or item.get("saved_at"),
                    "type": item.get("type"),
                    "category": item.get("category"),
                    "analysis_type": item.get("analysis_type"),
                    "document_type": item.get("document_type"),
                    "source_type": item.get("source_type"),
                    "scope": item.get("scope"),
                    "title": item.get("title") or item.get("summary"),
                    "summary": item.get("summary"),
                    "tags": item.get("tags") or [],
                    "completion_rate": item.get("completion_rate"),
                    "completed_count": item.get("completed_count"),
                    "total_count": item.get("total_count"),
                    "readiness_level": item.get("readiness_level"),
                    "data_quality": quality_payload.get("data_quality") or data_quality,
                    "source_confidence": quality_payload.get("source_confidence")
                    or item.get("source_confidence"),
                    "source_count": len(injected_data) if isinstance(injected_data, list) else item.get("source_count"),
                    "current_price": item.get("current_price"),
                    "local_vault_verified": True,
                }
            )
    return entries


def merge_portfolio_analysis_entries(
    manifest: list[dict[str, Any]],
    extra: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in [*manifest, *extra]:
        if not isinstance(entry, dict):
            continue
        ticker = normalize_portfolio_analysis_ticker(entry.get("ticker"))
        file_name = str(entry.get("file_name") or entry.get("storage_path") or entry.get("path") or "")
        key = (ticker, file_name)
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    return merged


def portfolio_analysis_entries_for_ticker(
    entries: list[dict[str, Any]],
    ticker: str,
    *,
    manifest_verifier=None,
) -> list[dict[str, Any]]:
    normalized = normalize_portfolio_analysis_ticker(ticker)
    matches = [
        entry
        for entry in entries
        if normalize_portfolio_analysis_ticker(entry.get("ticker")) == normalized
    ]
    if manifest_verifier is None:
        return matches
    return [
        entry
        for entry in matches
        if entry.get("local_vault_verified") is True or manifest_verifier(entry, normalized)
    ]


def portfolio_analysis_entry_markers(entry: dict[str, Any]) -> set[str]:
    markers: set[str] = set()
    for key in ("type", "category", "analysis_type", "document_type", "source_type", "scope", "file_name", "title"):
        value = str(entry.get(key) or "").strip().lower().replace("_", "-")
        if value:
            markers.add(value)
    for tag in entry.get("tags") or []:
        value = str(tag or "").strip().lower().replace("_", "-")
        if value:
            markers.add(value)
    file_name = str(entry.get("file_name") or "").strip().lower().replace("_", "-")
    if file_name:
        markers.add(file_name)
        if file_name.endswith(".json") or file_name.endswith(".md"):
            markers.add(file_name.rsplit(".", 1)[0])
    return markers


def portfolio_analysis_module_entries(
    entries: list[dict[str, Any]],
    module_key: str,
) -> list[dict[str, Any]]:
    """Return stored entries that satisfy a document-presence module marker."""
    expected_types = next(
        (
            expected
            for key, _label, expected in REQUIRED_PORTFOLIO_ANALYSIS_MODULES
            if key == module_key
        ),
        set(),
    )
    if not expected_types:
        return []
    matched: list[dict[str, Any]] = []
    for entry in entries:
        markers = portfolio_analysis_entry_markers(entry)
        if any(
            expected in marker or marker in expected
            for expected in expected_types
            for marker in markers
        ):
            matched.append(entry)
    return matched


def portfolio_analysis_module_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    """Document-presence state retained for compatibility with existing clients."""
    return {
        key: bool(portfolio_analysis_module_entries(entries, key))
        for key, _label, _expected_types in REQUIRED_PORTFOLIO_ANALYSIS_MODULES
    }


def portfolio_analysis_checklist_status(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe whether a saved checklist actually clears the human-review gate."""
    checklist_entries = portfolio_analysis_module_entries(entries, "checklist")
    if not checklist_entries:
        return {
            "documented": False,
            "review_ready": False,
            "completion_rate": None,
            "completed_count": None,
            "total_count": None,
            "readiness_level": None,
            "required_completion_rate": REVIEW_CHECKLIST_COMPLETION_THRESHOLD,
            "reason": "체크리스트 문서가 없습니다.",
        }

    latest = max(checklist_entries, key=_entry_sort_key)
    completion_rate = _as_optional_ratio(latest.get("completion_rate"))
    completed_count = _as_optional_count(latest.get("completed_count"))
    total_count = _as_optional_count(latest.get("total_count"))
    if completion_rate is None:
        return {
            "documented": True,
            "review_ready": False,
            "completion_rate": None,
            "completed_count": completed_count,
            "total_count": total_count,
            "readiness_level": latest.get("readiness_level"),
            "required_completion_rate": REVIEW_CHECKLIST_COMPLETION_THRESHOLD,
            "reason": "저장된 체크리스트의 완료율을 확인할 수 없습니다.",
        }

    review_ready = completion_rate >= REVIEW_CHECKLIST_COMPLETION_THRESHOLD
    completed_text = (
        f"{completed_count}/{total_count}"
        if completed_count is not None and total_count not in {None, 0}
        else f"{completion_rate:.0%}"
    )
    return {
        "documented": True,
        "review_ready": review_ready,
        "completion_rate": completion_rate,
        "completed_count": completed_count,
        "total_count": total_count,
        "readiness_level": latest.get("readiness_level"),
        "required_completion_rate": REVIEW_CHECKLIST_COMPLETION_THRESHOLD,
        "reason": (
            f"체크리스트 {completed_text}로 검토 게이트를 충족했습니다."
            if review_ready
            else (
                f"체크리스트 {completed_text}; "
                f"검토 게이트 {REVIEW_CHECKLIST_COMPLETION_THRESHOLD:.0%} 미만입니다."
            )
        ),
    }


def portfolio_analysis_review_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    """Review-gate state: documentation plus a sufficiently completed checklist."""
    state = portfolio_analysis_module_state(entries)
    state["checklist"] = portfolio_analysis_checklist_status(entries)["review_ready"]
    return state


def portfolio_human_review_packet(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest non-decision evidence packet without changing module state."""
    packets = [
        entry
        for entry in entries
        if str(entry.get("type") or "").strip().lower() == HUMAN_REVIEW_PACKET_TYPE
    ]
    if not packets:
        return None
    latest = max(packets, key=_entry_sort_key)
    return {
        "date": latest.get("date") or latest.get("created_at") or latest.get("saved_at"),
        "file_name": latest.get("file_name"),
        "summary": latest.get("summary"),
        "data_quality": latest.get("data_quality"),
        "source_count": latest.get("source_count"),
        "review_gate_effect": "none",
    }


def missing_portfolio_analysis_labels(module_state: dict[str, bool]) -> list[str]:
    return [
        label
        for key, label, _expected_types in REQUIRED_PORTFOLIO_ANALYSIS_MODULES
        if not module_state.get(key)
    ]


def portfolio_analysis_next_action(missing_labels: list[str], *, verified: bool = True) -> str:
    if not verified:
        return "공식 티커 인증을 먼저 보강하세요."
    if not missing_labels:
        return "핵심 분석이 모두 연결되어 있습니다. 새 데이터 유입 시 갱신만 하면 됩니다."
    first = missing_labels[0]
    if first == "기준 리포트":
        return "팀 리포트로 기준 투자 논거를 먼저 생성하세요."
    if first == "매매 전략":
        return "매매 전략에서 진입 구간, 손절, 목표가를 설계하세요."
    if first == "실적 분석":
        return "최근 실적 반응을 연결해 다음 실적 전 추적 항목을 정리하세요."
    if first == "모델 업데이트 노트":
        return "보고 자동화에서 어닝 콜/공시 기반 모델 업데이트 노트를 작성하세요."
    if first == "체크리스트":
        return "16개 리서치 체크리스트로 투자 준비도를 수치화하세요."
    return "뉴스/리포트/메모를 정보 입력에 저장해 논거 변화를 추적하세요."
