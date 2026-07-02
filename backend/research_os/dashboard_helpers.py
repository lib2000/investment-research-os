"""Ticker dashboard display helper functions."""

from __future__ import annotations

from re import search, sub
from types import SimpleNamespace

from .models import DashboardReportSummary, ResearchMemoryFile


def report_file_sequence(file_name: str) -> int:
    match = search(r"\d{4}-\d{2}-\d{2}-(\d+)\.(?:md|json)$", file_name)
    if match:
        return int(match.group(1))
    return 1 if search(r"\d{4}-\d{2}-\d{2}\.(?:md|json)$", file_name) else 0


def latest_manifest_entry(entries: list[dict], *report_types: str) -> dict | None:
    wanted = set(report_types)
    matches = [entry for entry in entries if entry.get("type") in wanted]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda entry: (
            entry.get("date", ""),
            report_file_sequence(entry.get("file_name", "")),
            entry.get("file_name", ""),
        ),
        reverse=True,
    )[0]


def build_latest_dossier_preview(
    runtime: SimpleNamespace,
    ticker: str,
    entries: list[dict],
    vault_dir,
) -> dict:
    dossier_entry = latest_manifest_entry(entries, "dossier-synthesis")
    if not dossier_entry:
        return {}
    payload = runtime.read_manifest_entry_payload(dossier_entry, vault_dir)
    source = payload if payload else dossier_entry
    return {
        "ticker": ticker,
        "company_name": source.get("company_name") or dossier_entry.get("company_name") or runtime.ticker_company_name(ticker),
        "date": source.get("date") or dossier_entry.get("date"),
        "file_name": dossier_entry.get("file_name"),
        "relative_path": dossier_entry.get("relative_path"),
        "summary": source.get("thesis_summary") or source.get("summary") or dossier_entry.get("summary"),
        "confidence": source.get("confidence") or dossier_entry.get("source_confidence"),
        "source_count": source.get("source_count") or dossier_entry.get("source_count") or 0,
        "duplicate_count": source.get("duplicate_count") or dossier_entry.get("duplicate_count") or 0,
        "consensus_facts": (source.get("consensus_facts") or [])[:3],
        "bull_thesis": (source.get("bull_thesis") or [])[:3],
        "bear_thesis": (source.get("bear_thesis") or [])[:3],
        "cruxes": (source.get("cruxes") or [])[:3],
        "observables": (source.get("observables") or [])[:4],
    }


def build_document_quality_digest(
    runtime: SimpleNamespace,
    ticker: str,
    entries: list[dict],
    vault_dir,
) -> dict:
    documents: list[dict] = []
    for entry in entries:
        if entry.get("type") != "research-capture":
            continue
        payload = runtime.read_manifest_entry_payload(entry, vault_dir)
        attachment = entry.get("attachment") or payload.get("attachment") or {}
        url_processing = entry.get("source_url_processing") or payload.get("source_url_processing") or {}
        has_file = bool(attachment)
        has_url = bool(url_processing)
        if not (has_file or has_url):
            continue
        profile = attachment.get("extraction_profile") or {}
        warnings = attachment.get("extraction_warnings") or []
        quality = attachment.get("extraction_quality")
        try:
            quality_value = float(quality)
        except (TypeError, ValueError):
            quality_value = 0.0 if has_file else 0.55
        char_count = int(
            attachment.get("extraction_char_count")
            or profile.get("char_count")
            or len(str(payload.get("document_preview") or ""))
            or 0
        )
        if not quality and char_count:
            quality_value = min(0.95, max(0.45, char_count / 6000))
        documents.append(
            {
                "date": entry.get("date"),
                "file_name": attachment.get("file_name") or entry.get("file_name"),
                "title": entry.get("title") or entry.get("summary") or attachment.get("file_name"),
                "document_type": attachment.get("document_type") or ("웹 문서" if has_url else "파일"),
                "quality": round(quality_value, 2) if quality_value else None,
                "char_count": char_count,
                "analysis_readiness": profile.get("analysis_readiness") or ("웹 본문 추출" if has_url else "확인 필요"),
                "next_action": profile.get("next_action") or ("추출 본문으로 자동 분류·태깅 완료" if char_count else "본문 추출 상태를 확인하세요."),
                "warnings": warnings[:3],
                "source_url": url_processing.get("source_url"),
                "relative_path": entry.get("relative_path"),
            }
        )
    documents = sorted(
        documents,
        key=lambda item: (item.get("date") or "", item.get("file_name") or ""),
        reverse=True,
    )[:5]
    if not documents:
        return {}
    usable = [item for item in documents if (item.get("quality") or 0) >= 0.65 or (item.get("char_count") or 0) >= 1000]
    warning_count = sum(len(item.get("warnings") or []) for item in documents)
    latest = documents[0]
    return {
        "ticker": ticker,
        "document_count": len(documents),
        "usable_count": len(usable),
        "warning_count": warning_count,
        "latest": latest,
        "documents": documents,
        "headline": "추출 품질 양호" if usable else "추출 품질 확인 필요",
    }


def build_latest_market_journal_reference(runtime: SimpleNamespace, settings) -> dict:
    store = runtime.read_market_close_journal(settings)
    entries = [
        item
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    if not entries:
        return {}
    latest = sorted(
        entries,
        key=lambda item: (item.get("session_date") or "", item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )[0]
    return {
        "market": latest.get("market"),
        "session_date": latest.get("session_date"),
        "sentiment": latest.get("sentiment"),
        "risk_level": latest.get("risk_level"),
        "regime": latest.get("regime"),
        "key_drivers": (latest.get("key_drivers") or [])[:4],
        "sector_implications": (latest.get("sector_implications") or [])[:4],
        "auto_utilization_focus": (latest.get("auto_utilization_focus") or [])[:4],
        "portfolio_actions": (latest.get("portfolio_actions") or [])[:3],
        "next_session_watch": (latest.get("next_session_watch") or [])[:4],
        "tags": (latest.get("tags") or [])[:8],
    }


def latest_manifest_thesis_snapshot(ticker: str, entries: list[dict]) -> dict:
    thesis_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("investment_thesis"), dict)
    ]
    if not thesis_entries:
        return {}
    latest_entry = sorted(
        thesis_entries,
        key=lambda entry: (
            entry.get("date", ""),
            report_file_sequence(entry.get("file_name", "")),
            entry.get("file_name", ""),
        ),
        reverse=True,
    )[0]
    thesis = latest_entry.get("investment_thesis") or {}
    watch_items = [
        item for item in latest_entry.get("watch_items", []) if isinstance(item, dict)
    ]
    valuation = thesis.get("valuation_assumptions") if isinstance(thesis, dict) else {}
    if not isinstance(valuation, dict):
        valuation = {}
    return {
        "ticker": thesis.get("ticker") or ticker,
        "company_name": latest_entry.get("company_name"),
        "thesis_summary": thesis.get("thesis") or latest_entry.get("summary"),
        "bull_triggers": thesis.get("bull_triggers") or [],
        "bear_triggers": thesis.get("bear_triggers") or [],
        "invalidation_conditions": thesis.get("invalidation_conditions") or [],
        "watch_kpis": thesis.get("watch_kpis") or [],
        "watch_items": watch_items,
        "source_report_type": latest_entry.get("type"),
        "source_file_name": latest_entry.get("file_name"),
        "source_relative_path": latest_entry.get("relative_path"),
        "source_date": latest_entry.get("date"),
        "confidence": latest_entry.get("source_confidence") or valuation.get("confidence"),
        "updated_at": latest_entry.get("updated_at") or latest_entry.get("date"),
    }

def compact_tooltip_text(value: object, limit: int = 180) -> str:
    if value is None:
        return "근거 요약 없음"
    if isinstance(value, list):
        value = " / ".join(str(item) for item in value[:2])
    elif isinstance(value, dict):
        value = " / ".join(f"{key}: {item}" for key, item in list(value.items())[:3])
    text = sub(r"\s+", " ", str(value)).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text or "근거 요약 없음"


def dashboard_report_impact_reason(entry: dict) -> str | None:
    if entry.get("type") != "thesis-impact-review":
        return None
    reasons: list[str] = []
    impact = entry.get("overall_impact")
    if impact:
        reasons.append(f"판정: {impact}")
    summary = entry.get("summary")
    if summary:
        reasons.append(f"요약: {compact_tooltip_text(summary, 140)}")
    for finding in (entry.get("findings") or [])[:2]:
        if not isinstance(finding, dict):
            continue
        reference = compact_tooltip_text(finding.get("thesis_reference") or "기존 투자 논거", 70)
        evidence = compact_tooltip_text(
            finding.get("rationale") or finding.get("evidence") or finding.get("signal"),
            150,
        )
        reasons.append(f"근거: {reference} → {evidence}")
    next_actions = [compact_tooltip_text(item, 80) for item in (entry.get("next_actions") or [])[:2]]
    if next_actions:
        reasons.append("다음 조치: " + " / ".join(next_actions))
    return "\n".join(reasons) if reasons else None


def dashboard_report_summary(entry: dict) -> DashboardReportSummary:
    impact_reason = dashboard_report_impact_reason(entry)
    impact_label = entry.get("overall_impact") if entry.get("type") == "thesis-impact-review" else None
    return DashboardReportSummary(
        type=entry.get("type", "unknown"),
        file_name=entry.get("file_name", "unknown.md"),
        relative_path=entry.get("relative_path", ""),
        date=entry.get("date", ""),
        summary=entry.get("summary"),
        impact_label=impact_label,
        impact_reason=impact_reason,
        tooltip=impact_reason,
    )


def infer_report_type_from_file(file_name: str) -> str:
    known_types = [
        "collaborative-team-report",
        "institutional-stock-breakdown",
        "smart-trade-setup",
        "earnings-reaction",
        "research-capture",
        "thesis-impact-review",
        "dossier-synthesis",
        "research-checklist",
        "portfolio-risk-scan",
        "reinforcement-portfolio-optimizer",
        "sector-opportunity",
        "long-term-compounder",
    ]
    for report_type in known_types:
        if report_type in file_name:
            return report_type
    return "saved-report"


def infer_report_date_from_file(file_name: str) -> str:
    match = search(r"\d{4}-\d{2}-\d{2}", file_name)
    if match:
        return match.group(0)
    return ""


def build_dashboard_latest_reports(
    entries: list[dict],
    files: list[ResearchMemoryFile],
) -> list[DashboardReportSummary]:
    summaries = [dashboard_report_summary(entry) for entry in entries]
    seen_paths = {
        summary.relative_path
        for summary in summaries
        if summary.relative_path
    }
    for file in files:
        if file.relative_path in seen_paths:
            continue
        summaries.append(
            DashboardReportSummary(
                type=infer_report_type_from_file(file.file_name),
                file_name=file.file_name,
                relative_path=file.relative_path,
                date=infer_report_date_from_file(file.file_name),
                summary=f"저장된 Markdown 리포트: {file.file_name}",
            )
        )

    return summaries[:6]


def render_dashboard_watch_item(item: object) -> str:
    if isinstance(item, dict):
        metric = item.get("metric", "추적 항목")
        condition = item.get("condition", "조건 확인 필요")
        action = item.get("action", "후속 점검")
        priority = item.get("priority", "medium")
        return f"[{_translate_severity_label(priority)}] {metric}: {condition} -> {action}"
    return str(item)


def _translate_severity_label(value: object) -> str:
    labels = {
        "high": "높음",
        "medium": "보통",
        "low": "낮음",
    }
    return labels.get(str(value), str(value))
