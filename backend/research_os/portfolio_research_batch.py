"""Evidence-only dual-track research batches for saved portfolio holdings.

This module does not fetch sources, call an LLM, create trading instructions, or
change portfolio-analysis completion gates.  It only reorganizes already saved
and verified research evidence into a portfolio-level review document.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


DESIGN_NAME = "portfolio_dual_track_research_v1"
REPORT_DIRECTORY_NAME = "portfolio_research_batches"
HUMAN_REVIEW_PACKET_TYPE = "human-review-packet"

BUSINESS_MARKERS = {
    "dossier-synthesis",
    "collaborative-team-report",
    "institutional-stock-breakdown",
    "research-capture",
    "dart-filing-watch",
    "public-ir-sec",
    "company-ir",
    "industry",
    "sector",
    "business",
}
FINANCIAL_MARKERS = {
    "dossier-synthesis",
    "earnings-reaction",
    "earnings-release",
    "earnings",
    "public-ir-sec",
    "earnings-filing-note",
    "model-update",
    "valuation",
    "target-price",
    "thesis-impact-review",
    "financial",
}
FUND_KEYWORDS = ("ETF", "ETN", "펀드", "FUND", "REIT", "리츠")
# Korean exchange-traded products sometimes omit the literal "ETF" suffix in
# saved portfolio names.  These brand prefixes are product families, not
# operating-company names, so they safely route the review to fund-specific
# questions without relying on an external lookup at batch runtime.
KOREAN_FUND_BRAND_PREFIXES = (
    "TIGER ",
    "KODEX ",
    "ACE ",
    "ARIRANG ",
    "HANARO ",
    "KBSTAR ",
    "KOSEF ",
    "KIWOOM ",
    "SOL ",
    "TIMEFOLIO ",
    "RISE ",
    "PLUS ",
)


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _entry_date(value: Any) -> date | None:
    raw = _safe_text(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _entry_markers(entry: dict[str, Any]) -> set[str]:
    markers: set[str] = set()
    for key in (
        "type",
        "category",
        "analysis_type",
        "document_type",
        "source_type",
        "scope",
        "file_name",
        "title",
    ):
        value = _safe_text(entry.get(key)).lower().replace("_", "-")
        if value:
            markers.add(value)
    for tag in _as_list(entry.get("tags")):
        value = _safe_text(tag).lower().replace("_", "-")
        if value:
            markers.add(value)
    return markers


def _matches_track(entry: dict[str, Any], expected_markers: set[str]) -> bool:
    markers = _entry_markers(entry)
    return any(
        expected in marker or marker in expected
        for expected in expected_markers
        for marker in markers
    )


def _source_row(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": _safe_text(entry.get("date") or entry.get("created_at") or entry.get("saved_at")) or None,
        "type": _safe_text(entry.get("type") or entry.get("analysis_type") or entry.get("document_type")) or "저장 자료",
        "file_name": _safe_text(entry.get("file_name") or entry.get("storage_path")) or None,
        "summary": _safe_text(entry.get("summary") or entry.get("title")) or None,
        "source_count": entry.get("source_count"),
    }


def _latest_date(entries: list[dict[str, Any]]) -> date | None:
    return max((_entry_date(item.get("date")) for item in entries if _entry_date(item.get("date"))), default=None)


def _source_rows(entries: list[dict[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    sorted_entries = sorted(
        entries,
        key=lambda entry: (_safe_text(entry.get("date") or entry.get("created_at") or entry.get("saved_at")), _safe_text(entry.get("file_name"))),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None]] = set()
    for entry in sorted_entries:
        row = _source_row(entry)
        key = (row["date"], row["file_name"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def is_fund_like_holding(company_name: Any) -> bool:
    normalized = _safe_text(company_name).upper()
    return any(keyword in normalized for keyword in FUND_KEYWORDS) or any(
        normalized.startswith(prefix) for prefix in KOREAN_FUND_BRAND_PREFIXES
    )


def _track_spec(*, fund_like: bool) -> dict[str, dict[str, str]]:
    if fund_like:
        return {
            "business": {
                "name": "기초지수·편입·산업 노출",
                "question": "기초지수, 편입 구조와 산업 노출이 기존 보유 목적과 계속 맞는지 확인",
                "missing": "기초지수·편입·산업 노출을 뒷받침할 저장 자료가 부족합니다.",
            },
            "financial": {
                "name": "추적 구조·보수·유동성",
                "question": "추적 구조, 보수, 유동성 및 기초지수/수급 근거를 확인",
                "missing": "추적 구조·보수·유동성 또는 기초지수 자료가 부족합니다.",
            },
        }
    return {
        "business": {
            "name": "사업·산업",
            "question": "핵심 사업, 산업 변화, 경쟁 구도와 관찰 KPI를 원문으로 확인",
            "missing": "사업·산업 변화와 핵심 KPI를 뒷받침할 저장 자료가 부족합니다.",
        },
        "financial": {
            "name": "실적·밸류에이션",
            "question": "매출·마진·현금흐름·실적 반응과 가치평가 가정을 원문으로 확인",
            "missing": "실적·밸류에이션 변화 또는 모델 가정을 뒷받침할 저장 자료가 부족합니다.",
        },
    }


def _research_status(business_entries: list[dict[str, Any]], financial_entries: list[dict[str, Any]]) -> tuple[str, str]:
    if business_entries and financial_entries:
        return "two_track_ready", "두 리서치 트랙의 저장 근거를 함께 검토할 수 있습니다."
    if not business_entries and not financial_entries:
        return "evidence_gap", "두 트랙 모두 저장 근거가 부족합니다. 공식 원문 또는 기존 리서치 저장부터 필요합니다."
    if not business_entries:
        return "business_track_gap", "사업·산업 트랙의 저장 근거를 먼저 보강하세요."
    return "financial_track_gap", "실적·밸류에이션 트랙의 저장 근거를 먼저 보강하세요."


def _evidence_strength(
    business_entries: list[dict[str, Any]],
    financial_entries: list[dict[str, Any]],
    *,
    as_of: date,
) -> tuple[int, int | None]:
    """Return a mechanical evidence score, not a return/confidence forecast."""
    latest = _latest_date([*business_entries, *financial_entries])
    days_since_latest = (as_of - latest).days if latest else None
    score = 0
    if business_entries:
        score += 35
    if financial_entries:
        score += 35
    if latest and days_since_latest <= 30:
        score += 20
    elif latest and days_since_latest <= 90:
        score += 10
    source_count = len({(_safe_text(entry.get("file_name")), _safe_text(entry.get("date"))) for entry in [*business_entries, *financial_entries]})
    if source_count >= 4:
        score += 10
    elif source_count >= 2:
        score += 5
    return score, days_since_latest


def _review_priority(
    status: str,
    days_since_latest: int | None,
    *,
    missing_modules: list[Any],
) -> tuple[str, int, str]:
    if status == "evidence_gap":
        return "high", 0, "두 리서치 트랙의 저장 근거가 모두 부족합니다."
    if status.endswith("_gap"):
        return "high", 0, "두 리서치 트랙 중 하나의 저장 근거가 부족합니다."
    missing = {_safe_text(value) for value in missing_modules}
    core_document_gaps = {"기준 리포트", "매매 전략", "실적 분석", "모델 업데이트 노트"}
    if missing & core_document_gaps:
        labels = ", ".join(sorted(missing & core_document_gaps))
        return "high", 0, f"표준 리서치 문서 공백: {labels}"
    if days_since_latest is None or days_since_latest > 90:
        return "medium", 1, "최근 저장 근거가 90일을 넘었거나 날짜를 확인할 수 없습니다."
    if days_since_latest > 60:
        return "medium", 1, "최근 저장 근거가 60일을 넘어 신선도 점검이 필요합니다."
    return "routine", 2, "두 트랙 근거가 있고 핵심 문서 공백·신선도 경보가 없습니다."


def build_portfolio_research_item(
    record: dict[str, Any],
    entries: list[dict[str, Any]],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Build one source-indexed research item without inferring missing facts."""
    company_name = _safe_text(record.get("company_name")) or _safe_text(record.get("ticker"))
    fund_like = is_fund_like_holding(company_name)
    report_entries = [
        entry
        for entry in entries
        if _safe_text(entry.get("type")).lower() != HUMAN_REVIEW_PACKET_TYPE
    ]
    business_entries = [entry for entry in report_entries if _matches_track(entry, BUSINESS_MARKERS)]
    financial_entries = [entry for entry in report_entries if _matches_track(entry, FINANCIAL_MARKERS)]
    status, status_message = _research_status(business_entries, financial_entries)
    evidence_strength, days_since_latest = _evidence_strength(
        business_entries,
        financial_entries,
        as_of=as_of,
    )
    missing_modules = _as_list(record.get("missing_modules"))
    priority, priority_rank, priority_reason = _review_priority(
        status,
        days_since_latest,
        missing_modules=missing_modules,
    )
    track_spec = _track_spec(fund_like=fund_like)
    checklist_status = _as_mapping(record.get("checklist_status"))
    latest_date = _latest_date(report_entries)

    return {
        "ticker": _safe_text(record.get("ticker")).upper(),
        "official_symbol": _safe_text(record.get("official_symbol")).upper() or None,
        "company_name": company_name,
        "instrument_kind": "fund_like" if fund_like else "company",
        "portfolios": [str(value) for value in _as_list(record.get("portfolios")) if _safe_text(value)],
        "market_value_reference": round(_safe_float(record.get("market_value")), 2),
        "research_status": status,
        "research_status_message": status_message,
        "review_priority": priority,
        "review_priority_reason": priority_reason,
        "evidence_strength": evidence_strength,
        "evidence_strength_definition": "저장 근거의 트랙 충족·최근성·다양성에 대한 기계적 점수이며 투자 성과 예측이 아닙니다.",
        "latest_evidence_date": latest_date.isoformat() if latest_date else None,
        "days_since_latest_evidence": days_since_latest,
        "tracks": {
            "business_industry": {
                "label": track_spec["business"]["name"],
                "question": track_spec["business"]["question"],
                "source_count": len(business_entries),
                "status": "ready" if business_entries else "evidence_gap",
                "missing_reason": None if business_entries else track_spec["business"]["missing"],
                "sources": _source_rows(business_entries),
            },
            "financial_valuation": {
                "label": track_spec["financial"]["name"],
                "question": track_spec["financial"]["question"],
                "source_count": len(financial_entries),
                "status": "ready" if financial_entries else "evidence_gap",
                "missing_reason": None if financial_entries else track_spec["financial"]["missing"],
                "sources": _source_rows(financial_entries),
            },
        },
        "coverage": {
            "documented_completion_rate": record.get("completion_rate"),
            "review_completion_rate": record.get("review_completion_rate"),
            "missing_modules": missing_modules,
            "review_missing_modules": _as_list(record.get("review_missing_modules")),
            "checklist_completion_rate": checklist_status.get("completion_rate"),
            "checklist_review_ready": bool(checklist_status.get("review_ready")),
        },
        "next_human_action": (
            "기준 리포트와 매매 전략의 원문 근거를 먼저 보강하세요. 이 배치는 해당 문서를 자동으로 완료하지 않습니다."
            if {"기준 리포트", "매매 전략"} & {_safe_text(value) for value in missing_modules}
            else (
                "저장된 원문을 확인한 뒤 새 근거를 정보 입력에 저장하고, 기존 논거의 강화·약화·혼합·중립만 별도로 판단하세요."
                if status == "two_track_ready"
                else "공식 공시·IR·실적자료 또는 검증된 리서치를 저장한 뒤 다시 배치를 생성하세요."
            )
        ),
        "safety": {
            "automated_order": False,
            "broker_order_endpoint_called": False,
            "changes_analysis_coverage": False,
            "changes_review_gate": False,
        },
        "_priority_rank": priority_rank,
    }


def build_portfolio_research_batch(
    records: list[dict[str, Any]],
    entries_by_ticker: dict[str, list[dict[str, Any]]],
    *,
    as_of: date,
    portfolio_name: str | None = None,
) -> dict[str, Any]:
    """Assemble all stored-holding research into one review-only batch."""
    items = [
        build_portfolio_research_item(
            record,
            entries_by_ticker.get(_safe_text(record.get("official_symbol") or record.get("ticker")).upper(), []),
            as_of=as_of,
        )
        for record in records
        if _safe_text(record.get("ticker"))
    ]
    items.sort(
        key=lambda item: (
            item["_priority_rank"],
            -_safe_float(item.get("market_value_reference")),
            str(item.get("ticker") or ""),
        )
    )
    for item in items:
        item.pop("_priority_rank", None)
    status_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("research_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    ready_count = status_counts.get("two_track_ready", 0)
    gap_count = len(items) - ready_count
    return {
        "status": "success",
        "module": "portfolio_research_batch",
        "design": DESIGN_NAME,
        "as_of": as_of.isoformat(),
        "portfolio_name": _safe_text(portfolio_name) or "전체 포트폴리오",
        "holding_count": len(items),
        "two_track_ready_count": ready_count,
        "evidence_gap_count": gap_count,
        "status_counts": status_counts,
        "summary": (
            f"저장 보유 종목 {len(items)}개 중 두 트랙 근거 준비 {ready_count}개, "
            f"근거 보강 필요 {gap_count}개입니다. 이 배치는 저장 자료의 검토 순서를 정리할 뿐 매수·매도 판단이나 주문을 생성하지 않습니다."
        ),
        "items": items,
        "safety": {
            "external_source_fetch_called": False,
            "llm_called": False,
            "telegram_sent": False,
            "automated_order": False,
            "broker_order_endpoint_called": False,
            "changes_analysis_coverage": False,
            "changes_review_gate": False,
        },
    }


def render_portfolio_research_batch_markdown(batch: dict[str, Any]) -> str:
    """Render the evidence batch as a research memo, never a trade instruction."""
    lines = [
        "# 보유 종목 이중 트랙 리서치 배치",
        "",
        f"- 기준일: {batch.get('as_of') or '확인 필요'}",
        f"- 범위: {batch.get('portfolio_name') or '전체 포트폴리오'}",
        f"- 보유 종목: {batch.get('holding_count') or 0}개",
        f"- 두 트랙 근거 준비: {batch.get('two_track_ready_count') or 0}개",
        f"- 근거 보강 필요: {batch.get('evidence_gap_count') or 0}개",
        "- 실행 원칙: 저장된 근거만 사용 · 자동 주문 없음 · 사람 검토 전용",
        "",
        "> 이 문서는 투자 판단과 매수·매도 지시가 아닙니다. 증거 강도는 저장 자료의 구성 점수일 뿐 기대수익이나 모델 신뢰도가 아닙니다.",
        "",
        "## 리서치 우선순위",
        "",
        "| 종목 | 구분 | 상태 | 우선순위 | 증거 강도 | 최근 근거 | 다음 검토 |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for item in _as_list(batch.get("items")):
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {company} ({ticker}) | {kind} | {status} | {priority} | {strength} | {latest} | {action} |".format(
                company=_safe_text(item.get("company_name")) or "확인 필요",
                ticker=_safe_text(item.get("ticker")) or "확인 필요",
                kind="ETF/펀드형" if item.get("instrument_kind") == "fund_like" else "개별 종목형",
                status=_safe_text(item.get("research_status")) or "확인 필요",
                priority=_safe_text(item.get("review_priority")) or "확인 필요",
                strength=item.get("evidence_strength") if item.get("evidence_strength") is not None else "확인 필요",
                latest=_safe_text(item.get("latest_evidence_date")) or "확인 필요",
                action=_safe_text(item.get("next_human_action")) or "확인 필요",
            )
        )
    lines.extend(["", "## 종목별 근거", ""])
    for item in _as_list(batch.get("items")):
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                f"### {_safe_text(item.get('company_name')) or item.get('ticker')} ({item.get('ticker')})",
                "",
                f"- 상태: {item.get('research_status') or '확인 필요'} · 증거 강도: {item.get('evidence_strength') if item.get('evidence_strength') is not None else '확인 필요'}/100",
                f"- 최근 근거: {item.get('latest_evidence_date') or '확인 필요'}",
                "",
            ]
        )
        tracks = _as_mapping(item.get("tracks"))
        for key in ("business_industry", "financial_valuation"):
            track = _as_mapping(tracks.get(key))
            lines.append(f"#### {track.get('label') or key}")
            lines.append("")
            lines.append(f"- 검토 질문: {track.get('question') or '확인 필요'}")
            if track.get("sources"):
                for source in _as_list(track.get("sources")):
                    if isinstance(source, dict):
                        lines.append(
                            f"- {source.get('date') or '날짜 확인 필요'} · {source.get('type') or '저장 자료'} · {source.get('summary') or source.get('file_name') or '요약 확인 필요'}"
                        )
            else:
                lines.append(f"- 근거 공백: {track.get('missing_reason') or '확인 필요'}")
            lines.append("")
        lines.append(f"- 사람 검토 다음 단계: {item.get('next_human_action') or '확인 필요'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_portfolio_research_batch(batch: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Save a same-day local evidence memo; the caller owns state-store privacy."""
    output_dir.mkdir(parents=True, exist_ok=True)
    as_of = _safe_text(batch.get("as_of")) or datetime.now().date().isoformat()
    stem = f"{as_of}-portfolio-research-batch"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_portfolio_research_batch_markdown(batch), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
