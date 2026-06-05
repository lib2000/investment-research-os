"""Shared portfolio analysis module coverage helpers."""

from __future__ import annotations

from typing import Any

REQUIRED_PORTFOLIO_ANALYSIS_MODULES = [
    ("team_report", "기준 리포트", {"collaborative-team-report", "institutional-stock-breakdown", "dossier-synthesis"}),
    ("trade_setup", "매매 전략", {"smart-trade-setup", "trade-setup", "strategy"}),
    ("earnings_reaction", "실적 분석", {"earnings-reaction", "earnings-release", "earnings", "public-ir-sec"}),
    ("model_update_note", "모델 업데이트 노트", {"earnings-filing-note", "model-update", "dossier-synthesis"}),
    ("checklist", "체크리스트", {"research-checklist", "checklist"}),
    ("recent_capture", "최근 정보 입력", {"research-capture", "public-ir-sec", "dart-filing-watch", "chart-analysis"}),
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


def portfolio_analysis_module_state(entries: list[dict[str, Any]]) -> dict[str, bool]:
    markers = set().union(*(portfolio_analysis_entry_markers(entry) for entry in entries)) if entries else set()
    return {
        key: any(
            expected in marker or marker in expected
            for expected in expected_types
            for marker in markers
        )
        for key, _label, expected_types in REQUIRED_PORTFOLIO_ANALYSIS_MODULES
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
