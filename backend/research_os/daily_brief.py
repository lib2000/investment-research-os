"""Daily research brief payload, rendering, and storage workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol


class DailyBriefRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def portfolio_thesis_date_age_days(runtime: DailyBriefRuntime, source_date: object) -> int | None:
    if not source_date:
        return None
    try:
        parsed = date.fromisoformat(str(source_date)[:10])
    except ValueError:
        return None
    return (runtime.current_storage_date() - parsed).days


def build_daily_portfolio_thesis_overview(runtime: DailyBriefRuntime, settings, vault_dir: Path) -> dict:
    response = runtime.portfolio_store_response(settings)
    by_ticker: dict[str, dict] = {}
    for portfolio in response.portfolios:
        for holding in portfolio.holdings:
            ticker = runtime.normalize_ticker(holding.ticker)
            if not ticker or ticker == "UNKNOWN":
                continue
            record = by_ticker.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "company_name": holding.name or ticker,
                    "market_value": 0.0,
                    "portfolios": [],
                },
            )
            if holding.name and record["company_name"] == ticker:
                record["company_name"] = holding.name
            if holding.market_value is not None:
                record["market_value"] += float(holding.market_value)
            if portfolio.portfolio_name not in record["portfolios"]:
                record["portfolios"].append(portfolio.portfolio_name)

    items: list[dict] = []
    for ticker, record in by_ticker.items():
        verification = runtime.verify_ticker_symbol(ticker, settings)
        official_symbol = runtime.normalize_ticker(verification.official_symbol or ticker)
        company_name = verification.company_name or record["company_name"] or official_symbol
        try:
            snapshot = runtime.read_ticker_thesis_snapshot(vault_dir, official_symbol)
        except Exception:
            snapshot = None
        age_days = portfolio_thesis_date_age_days(runtime, (snapshot or {}).get("source_date"))
        confidence = (snapshot or {}).get("confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
        bear_triggers = (snapshot or {}).get("bear_triggers") or []
        status = "정상"
        action = "새 자료가 들어오면 기존 논거와 비교하세요."
        priority_score = 0
        if not verification.verified:
            status = "티커 인증 필요"
            action = "회사명 또는 공식 티커를 확인해 등록하세요."
            priority_score += 70
        elif not snapshot:
            status = "논거 스냅샷 필요"
            action = "Dossier 또는 저장 데이터 검색 합성을 실행하세요."
            priority_score += 60
        else:
            if age_days is not None and age_days > 14:
                status = "논거 갱신 필요"
                action = "최근 시장일지·뉴스·실적 자료를 반영해 합성을 다시 실행하세요."
                priority_score += 35
            if confidence_value is not None and confidence_value < 0.7:
                status = "신뢰도 보강 필요"
                action = "원문 수치와 공시 자료를 보강해 신뢰도를 높이세요."
                priority_score += 25
            if bear_triggers:
                priority_score += min(20, len(bear_triggers) * 5)
        priority_score += min(30, int((record.get("market_value") or 0) / 1_000_000))
        items.append(
            {
                "ticker": official_symbol,
                "company_name": company_name,
                "market_value": record.get("market_value") or 0,
                "portfolios": record["portfolios"],
                "verified": verification.verified,
                "snapshot_connected": bool(snapshot),
                "snapshot_date": (snapshot or {}).get("source_date"),
                "snapshot_age_days": age_days,
                "confidence": confidence_value,
                "summary": (snapshot or {}).get("thesis_summary") or "",
                "bull_triggers": ((snapshot or {}).get("bull_triggers") or [])[:2],
                "bear_triggers": bear_triggers[:2],
                "watch_kpis": ((snapshot or {}).get("watch_kpis") or runtime.ticker_watch_kpis(official_symbol))[:5],
                "status": status,
                "recommended_action": action,
                "priority_score": priority_score,
            }
        )
    items.sort(key=lambda item: (item["priority_score"], item["market_value"]), reverse=True)
    connected_count = sum(1 for item in items if item["snapshot_connected"])
    verified_count = sum(1 for item in items if item["verified"])
    high_priority = [
        item
        for item in items
        if item["status"] != "정상" or item.get("bear_triggers")
    ][:8]
    return {
        "portfolio_count": len(response.portfolios),
        "holding_count": len(items),
        "verified_count": verified_count,
        "snapshot_connected_count": connected_count,
        "coverage_rate": connected_count / len(items) if items else 0.0,
        "items": items[:20],
        "priority_reviews": high_priority,
    }


def build_daily_brief_payload(runtime: DailyBriefRuntime, settings) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = sorted(
        [
            entry
            for entry in runtime.read_manifest(vault_dir)
            if isinstance(entry, dict)
            and entry.get("type") not in {"daily-dossier-brief"}
        ],
        key=runtime.manifest_entry_sort_key,
        reverse=True,
    )
    tickers = runtime.dossier_candidate_tickers(settings, limit=50)
    snapshots: list[dict] = []
    for ticker in tickers:
        try:
            snapshot = runtime.read_ticker_thesis_snapshot(vault_dir, ticker)
            if snapshot:
                snapshots.append(
                    {
                        "ticker": ticker,
                        "company_name": snapshot.get("company_name") or runtime.ticker_company_name(ticker),
                        "summary": snapshot.get("thesis_summary"),
                        "confidence": snapshot.get("confidence"),
                        "updated_at": snapshot.get("updated_at"),
                    }
                )
        except Exception:
            continue
    unique_recent_entries, duplicate_recent_entries = runtime.dedupe_manifest_entries_by_similarity(
        manifest_entries,
        vault_dir,
        limit=15,
    )
    recent_entries = [
        {
            "ticker": entry.get("ticker"),
            "type": entry.get("type"),
            "date": entry.get("date"),
            "summary": entry.get("summary"),
            "confidence": entry.get("confidence") or entry.get("source_confidence"),
        }
        for entry in unique_recent_entries
    ]
    unique_market_entries, duplicate_market_entries = runtime.dedupe_manifest_entries_by_similarity(
        [
            entry
            for entry in manifest_entries
            if entry.get("ticker") in {"MARKET", "MARKET-KR", "MARKET-US", "MARKET-GLOBAL", "MACRO", "CUSTOMS"}
            and entry.get("type") not in {"daily-dossier-brief", "rag-query-synthesis"}
        ],
        vault_dir,
        limit=5,
    )
    market_entries = [
        entry
        for entry in unique_market_entries
    ]
    portfolio_overview = build_daily_portfolio_thesis_overview(runtime, settings, vault_dir)
    interest_automation = runtime.build_interest_automation_board(settings, save_result=False)
    customs_trade_reference = runtime.build_daily_customs_trade_reference(settings)
    return {
        "date": runtime.current_storage_date().isoformat(),
        "generated_at": runtime.current_storage_timestamp(),
        "portfolio_tickers": tickers,
        "snapshot_count": len(snapshots),
        "portfolio_snapshot_count": portfolio_overview["snapshot_connected_count"],
        "portfolio_holding_count": portfolio_overview["holding_count"],
        "recent_entry_count": len(recent_entries),
        "duplicate_recent_entry_count": len(duplicate_recent_entries),
        "duplicate_market_entry_count": len(duplicate_market_entries),
        "market_entries": market_entries,
        "customs_trade_reference": customs_trade_reference,
        "portfolio_overview": portfolio_overview,
        "interest_automation": interest_automation,
        "snapshots": snapshots,
        "recent_entries": recent_entries,
        "next_actions": [
            "우선 점검 종목은 포트폴리오 비중, 논거 공백, 낮은 신뢰도, 약세 논거를 함께 반영해 자동 선별됩니다.",
            "신규 입력 자료가 있는 종목은 Dossier 합성 보고서의 강세/약세 논거 변화를 먼저 확인하세요.",
            "시장일지·거시 자료는 보유 종목의 섹터 노출과 자동 대조해 다음 매매 후보 필터로 사용하세요.",
            "신뢰도 낮은 자료는 투자 결론보다 관찰 항목으로만 반영하고, 원문·공시·수치 확인 후 가중치를 높이세요.",
        ],
    }


def render_daily_brief_markdown(payload: dict) -> str:
    def entry_lines(entries: list[dict], empty: str) -> str:
        if not entries:
            return f"- {empty}"
        lines = []
        for entry in entries:
            label = entry.get("ticker") or entry.get("company_name") or "대상 미확인"
            confidence = entry.get("confidence")
            confidence_text = f" · 신뢰도 {float(confidence):.0%}" if confidence is not None else ""
            lines.append(
                f"- {entry.get('date') or entry.get('updated_at') or '날짜 미확인'} · "
                f"{label} · {entry.get('type') or 'snapshot'}{confidence_text}: "
                f"{entry.get('summary') or '요약 없음'}"
            )
        return "\n".join(lines)

    def portfolio_priority_lines(entries: list[dict]) -> str:
        if not entries:
            return "- 우선 점검 종목이 없습니다."
        lines = []
        for entry in entries:
            confidence = entry.get("confidence")
            confidence_text = f" · 신뢰도 {float(confidence):.0%}" if confidence is not None else ""
            bear_text = (
                f" · 약세: {', '.join(entry.get('bear_triggers') or [])}"
                if entry.get("bear_triggers")
                else ""
            )
            kpi_text = ", ".join(entry.get("watch_kpis") or []) or "KPI 미정"
            lines.append(
                f"- {entry.get('company_name') or entry.get('ticker')}({entry.get('ticker')}) · "
                f"{entry.get('status') or '상태 미확인'}{confidence_text}: "
                f"{entry.get('recommended_action') or '후속 점검'} "
                f"확인 KPI: {kpi_text}{bear_text}"
            )
        return "\n".join(lines)

    def interest_target_lines(payload: dict) -> str:
        targets = (payload.get("ticker_targets") or [])[:8]
        sectors = (payload.get("sector_targets") or [])[:5]
        lines: list[str] = []
        for entry in targets:
            lines.append(
                f"- {entry.get('company_name') or entry.get('ticker')}({entry.get('ticker')}) · "
                f"저장 자료 {entry.get('recent_document_count', 0)}개 · "
                f"RAG {entry.get('rag_document_count', 0)}개 · "
                f"검색 예시: {', '.join((entry.get('rag_query_examples') or [])[:2]) or '없음'}"
            )
        for entry in sectors:
            lines.append(
                f"- {entry.get('name')} · {entry.get('region') or 'GLOBAL'} · "
                f"저장 자료 {entry.get('recent_document_count', 0)}개 · "
                f"검색 예시: {', '.join((entry.get('rag_query_examples') or [])[:2]) or '없음'}"
            )
        return "\n".join(lines) if lines else "- 관심목록 수집 대상이 없습니다."

    portfolio_overview = payload.get("portfolio_overview") or {}
    interest_automation = payload.get("interest_automation") or {}
    customs_reference = payload.get("customs_trade_reference") or {}
    customs_lines = []
    if customs_reference:
        customs_lines.extend(customs_reference.get("key_takeaways") or [])
        customs_lines.extend(customs_reference.get("sector_implications") or [])
        if customs_reference.get("warnings"):
            customs_lines.extend([f"경고: {item}" for item in customs_reference.get("warnings", [])])

    return f"""---
ticker: MARKET
type: daily-dossier-brief
date: {payload["date"]}
module: research_automation_daily_brief
---

# 일일 리서치 브리핑

## 시스템 상태

- 생성 시각: {payload["generated_at"]}
- 연결 종목: {len(payload["portfolio_tickers"])}개
- 최신 Dossier 스냅샷: {payload["snapshot_count"]}개
- 포트폴리오 논거 연결: {portfolio_overview.get("snapshot_connected_count", 0)}/{portfolio_overview.get("holding_count", 0)}개
- 최근 저장 자료 반영: {payload["recent_entry_count"]}개

## 시장/거시 입력

{entry_lines(payload["market_entries"], "최근 시장일지 또는 거시 자료가 없습니다.")}

## 관세청 수출입/재고 참고자료

{chr(10).join(f"- {item}" for item in customs_lines) if customs_lines else "- 오늘은 관세청 1일/11일/21일 자동 점검일이 아니거나 표시할 자료가 없습니다."}

## 종목별 최신 논거

{entry_lines(payload["snapshots"], "아직 Dossier 스냅샷이 없습니다.")}

## 포트폴리오 우선 점검

{portfolio_priority_lines((portfolio_overview.get("priority_reviews") or [])[:8])}

## 관심목록 자동 수집 대상

{interest_target_lines(interest_automation)}

## 최근 저장 자료

{entry_lines(payload["recent_entries"], "최근 저장 자료가 없습니다.")}

## 다음 액션

{chr(10).join(f"- {item}" for item in payload["next_actions"])}
"""


def save_daily_brief(runtime: DailyBriefRuntime, payload: dict, settings) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    markdown = render_daily_brief_markdown(payload)
    storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker="MARKET",
        report_type="daily-dossier-brief",
        markdown=markdown,
        structured_payload=payload,
        manifest_entry=runtime.manifest_with_ticker_verification("MARKET", {
            "summary": f"{payload['date']} 일일 리서치 브리핑: {payload['snapshot_count']}개 Dossier 스냅샷 반영",
            "source_confidence": 0.78,
            "tags": ["daily_brief", "dossier", "automation", "market"],
        }),
        report_date=runtime.current_storage_date(),
    )
    payload["storage"] = storage.model_dump(mode="json")
    runtime.write_json_store(
        runtime.latest_daily_brief_path(settings),
        {
            "updated_at": runtime.current_storage_timestamp(),
            "payload": payload,
            "storage": payload["storage"],
        },
    )
    return payload


def read_latest_daily_brief(runtime: DailyBriefRuntime, settings) -> dict:
    return runtime.read_json_store(runtime.latest_daily_brief_path(settings), {})
