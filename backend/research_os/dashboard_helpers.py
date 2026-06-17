"""Ticker dashboard display helper functions."""

from __future__ import annotations

from re import search, sub

from .models import DashboardReportSummary, ResearchMemoryFile


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
