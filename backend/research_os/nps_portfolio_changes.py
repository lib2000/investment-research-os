"""NPS public-data portfolio change snapshots."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from re import sub
from typing import Any, Iterable

from research_os.models import PortfolioHolding, SavedPortfolio
from research_os.nps_data_provider import NpsOdcloudClient
from research_os.portfolio_store import read_portfolio_store
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings
from research_os.state_store import current_storage_timestamp, read_json_store, user_state_dir, write_json_store


NPS_PORTFOLIO_CHANGE_SNAPSHOT_FILE = "nps_portfolio_change_snapshot.json"
NPS_REBALANCING_ARTICLE_URL = "https://kr.investing.com/news/stock-market-news/article-2000291"


def _public_rebalancing_context(as_of_date: date, *, refresh_attempted: bool) -> dict:
    return {
        "status": "public_sources_only",
        "as_of": as_of_date.isoformat(),
        "primary_article_url": NPS_REBALANCING_ARTICLE_URL,
        "article_observations": [
            {
                "label": "reported_rebalance_restart",
                "value": "2026-07-01 국내주식 리밸런싱 재개 보도",
                "source_url": NPS_REBALANCING_ARTICLE_URL,
            },
            {
                "label": "reported_target_band",
                "value": "기사 기준 2026년 국내주식 목표비중 20.8%, SAA ±6%p, TAA ±2%p로 총 상단 28.8% 언급",
                "source_url": NPS_REBALANCING_ARTICLE_URL,
            },
            {
                "label": "reported_sell_estimate_range",
                "value": "시장 추정 매도 필요 규모는 약 37.3조~74.4조원 범위로 보도되어 단일 확정치로 쓰지 않음",
                "source_url": NPS_REBALANCING_ARTICLE_URL,
            },
            {
                "label": "reported_execution_style",
                "value": "단기 매도 폭탄보다 장기간 분산 매도 및 종목 교체 가능성이 기사에서 제시됨",
                "source_url": NPS_REBALANCING_ARTICLE_URL,
            },
        ],
        "operational_constraints": [
            "국민연금 리밸런싱의 세부 집행 시점, 주문 규모, 종목별 주문은 시장 충격 최소화를 위해 비공개로 취급합니다.",
            "증권사나 트레이딩 시스템 API로 국민연금의 직접 주문 데이터를 조회할 수 없다고 가정합니다.",
            "시스템은 5% 이상 지분율 공시, 공공데이터포털 대량보유/보유자료, 시장 수급/뉴스를 결합해 사후 또는 간접 신호만 산출합니다.",
            "공개자료 기반 추정은 추천 점수의 보조 리스크 신호로만 반영하고 확정 매매 주문으로 해석하지 않습니다.",
        ],
        "data_policy": {
            "order_flow_access": "not_available",
            "broker_api_linkage": "not_supported",
            "realtime_rebalancing_detection": "not_supported",
            "supported_evidence": [
                "public_article",
                "odcloud_nps_large_holding",
                "odcloud_nps_domestic_stock",
                "dart_large_holding_disclosure",
                "market_supply_demand_news",
            ],
            "refresh_attempted": refresh_attempted,
        },
        "decision_rule": (
            "국민연금 관련 신호는 공개자료 기반 압력/위험도 플래그로만 사용하고, "
            "실시간 리밸런싱 주문 탐지나 특정 종목 매도 확정으로 승격하지 않습니다."
        ),
    }


def nps_portfolio_change_snapshot_path(settings: Settings) -> Path:
    return user_state_dir(settings) / NPS_PORTFOLIO_CHANGE_SNAPSHOT_FILE


def read_nps_portfolio_change_snapshot(settings: Settings) -> dict:
    return read_json_store(nps_portfolio_change_snapshot_path(settings), {})


def _cache_file(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "nps_odcloud_rows_cache.json"


def _compact_name(value: str | None) -> str:
    text = sub(r"\([^)]*\)", "", str(value or ""))
    text = sub(r"주식회사|\(주\)|㈜|주\)|\(주|corporation|corp\.?|inc\.?|co\.?|ltd\.?", "", text, flags=2)
    return sub(r"[^0-9a-zA-Z가-힣]+", "", text).casefold()


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _read_cache_records(settings: Settings) -> tuple[list[dict], list[dict], list[str], str | None]:
    path = _cache_file(settings)
    if not path.exists():
        return [], [], [f"국민연금 ODCLOUD 캐시가 없습니다: {path}"], None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [], [f"국민연금 ODCLOUD 캐시 읽기 실패: {exc}"], None
    if not isinstance(payload, dict):
        return [], [], ["국민연금 ODCLOUD 캐시 형식이 dict가 아닙니다."], None
    domestic_rows: list[dict] = []
    large_rows: list[dict] = []
    used_urls: list[str] = []
    newest_ts = None
    for record in payload.values():
        if not isinstance(record, dict):
            continue
        if record.get("used_url"):
            used_urls.append(str(record.get("used_url")))
        if record.get("ts") and (newest_ts is None or float(record.get("ts") or 0) > newest_ts):
            newest_ts = float(record.get("ts") or 0)
        for row in record.get("rows") or []:
            if not isinstance(row, dict):
                continue
            if "보고서 작성기준일" in row or "발행기관명" in row:
                large_rows.append(row)
            elif "연도" in row:
                domestic_rows.append(row)
    cache_updated_at = (
        datetime.fromtimestamp(newest_ts, timezone.utc).isoformat(timespec="seconds") if newest_ts else None
    )
    return domestic_rows, large_rows, sorted(set(used_urls)), cache_updated_at


def _portfolio_holdings(settings: Settings, portfolio_name: str) -> tuple[str, list[PortfolioHolding]]:
    store = read_portfolio_store(settings)
    portfolios = store.get("portfolios", {}) if isinstance(store, dict) else {}
    if portfolio_name != "__all__":
        candidates = [
            payload for key, payload in portfolios.items()
            if key == portfolio_name or str(payload.get("portfolio_name") or "") == portfolio_name
        ]
    else:
        candidates = list(portfolios.values())
    holdings: list[PortfolioHolding] = []
    names = []
    for payload in candidates:
        try:
            portfolio = SavedPortfolio.model_validate(payload)
        except Exception:
            continue
        names.append(portfolio.portfolio_name)
        holdings.extend(portfolio.holdings)
    return ("전체 저장 포트폴리오" if portfolio_name == "__all__" else (names[0] if names else portfolio_name), holdings)


def _event_payload(row: dict) -> dict:
    return {
        "issuer": row.get("발행기관명") or row.get("Issuer"),
        "base_date": row.get("보고서 작성기준일") or row.get("기준일"),
        "holding_ratio": _parse_float(row.get("지분율(퍼센트)") or row.get("지분율")),
        "source_number": row.get("번호"),
        "raw": row,
    }


def _match_holdings(events: Iterable[dict], holdings: Iterable[PortfolioHolding]) -> list[dict]:
    compact_events = [(_compact_name(event.get("issuer")), event) for event in events]
    matches: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for holding in holdings:
        h_name = _compact_name(holding.name or holding.ticker)
        if not h_name:
            continue
        for issuer_key, event in compact_events:
            if not issuer_key:
                continue
            loose_match_allowed = min(len(h_name), len(issuer_key)) >= 4
            if h_name == issuer_key or (loose_match_allowed and (h_name in issuer_key or issuer_key in h_name)):
                key = (str(holding.ticker), str(event.get("issuer")))
                if key in seen:
                    continue
                seen.add(key)
                matches.append(
                    {
                        "ticker": holding.ticker,
                        "holding_name": holding.name,
                        "market_value": holding.market_value,
                        "issuer": event.get("issuer"),
                        "base_date": event.get("base_date"),
                        "holding_ratio": event.get("holding_ratio"),
                        "reason": "저장 포트폴리오 보유명과 국민연금 대량보유 발행기관명이 매칭되었습니다.",
                    }
                )
    return sorted(matches, key=lambda item: (str(item.get("base_date") or ""), float(item.get("market_value") or 0)), reverse=True)


def build_nps_portfolio_change_snapshot(
    settings: Settings,
    *,
    as_of: str | date,
    portfolio_name: str = "__all__",
) -> dict:
    as_of_date = as_of if isinstance(as_of, date) else datetime.strptime(str(as_of), "%Y-%m-%d").date()
    refresh_attempted = False
    refresh_warnings: list[str] = []
    if settings.nps_odcloud_api_key:
        refresh_attempted = True
        try:
            client = NpsOdcloudClient(settings)
            _, domestic_errors, _ = client.fetch_domestic_stock_rows()
            _, large_errors, _ = client.fetch_large_holding_rows()
            refresh_warnings.extend(domestic_errors or [])
            refresh_warnings.extend(large_errors or [])
        except Exception as exc:
            refresh_warnings.append(f"국민연금 ODCLOUD 최신 호출 실패: {exc}")
    domestic_rows, large_rows, source_urls, cache_updated_at = _read_cache_records(settings)
    warnings: list[str] = []
    if not settings.nps_odcloud_api_key:
        warnings.append("NPS_ODCLOUD_API_KEY가 없어 외부 최신 호출 대신 기존 ODCLOUD 캐시를 분석했습니다.")
    warnings.extend(refresh_warnings[:4])
    dated_events = [
        _event_payload(row)
        for row in large_rows
        if _parse_date(row.get("보고서 작성기준일")) and _parse_date(row.get("보고서 작성기준일")) <= as_of_date
    ]
    dated_events.sort(key=lambda item: str(item.get("base_date") or ""), reverse=True)
    latest_event_date = max((str(item.get("base_date") or "") for item in dated_events), default=None)
    latest_events = [item for item in dated_events if item.get("base_date") == latest_event_date] if latest_event_date else []
    portfolio_label, holdings = _portfolio_holdings(settings, portfolio_name)
    matches = _match_holdings(dated_events, holdings)
    stale = bool(latest_event_date and latest_event_date < as_of_date.isoformat())
    if stale:
        warnings.append(f"캐시 내 최신 대량보유 기준일은 {latest_event_date}로 요청 기준일 {as_of_date.isoformat()}보다 오래되었습니다.")
    status = "warning" if warnings else "success"
    if not dated_events:
        status = "needs_data"
        warnings.append("요청 기준일 이하 국민연금 대량보유 이벤트가 캐시에 없습니다.")
    summary = (
        f"{as_of_date.isoformat()} 기준 국민연금 대량보유 캐시 {len(dated_events)}건 분석, "
        f"최신 기준일 {latest_event_date or '없음'}, 포트폴리오 매칭 {len(matches)}건"
    )
    first_next_action = (
        "공공데이터포털 API 호출은 성공했지만 원천 최신 기준일이 오래되었습니다. 국민연금/공시 포털의 최신 대량보유 공개 여부를 별도 확인하세요."
        if refresh_attempted
        else "NPS_ODCLOUD_API_KEY를 설정한 뒤 같은 기준일로 재수집해 캐시 최신성을 확인하세요."
    )
    return {
        "status": status,
        "module": "nps_portfolio_change_snapshot",
        "as_of": as_of_date.isoformat(),
        "generated_at": current_storage_timestamp(),
        "portfolio_name": portfolio_label,
        "refresh_attempted": refresh_attempted,
        "refresh_status": "attempted" if refresh_attempted else "skipped_no_api_key",
        "public_rebalancing_context": _public_rebalancing_context(as_of_date, refresh_attempted=refresh_attempted),
        "cache_updated_at": cache_updated_at,
        "source_urls": source_urls,
        "domestic_stock_row_count": len(domestic_rows),
        "large_holding_row_count": len(large_rows),
        "event_count_as_of": len(dated_events),
        "latest_event_date": latest_event_date,
        "latest_events": latest_events[:20],
        "portfolio_matches": matches[:20],
        "warnings": warnings,
        "next_actions": [
            first_next_action,
            "국민연금 리밸런싱은 주문 시점/규모가 비공개이므로 시스템은 기사·공시·공공데이터 기반 압력 신호만 사용합니다.",
            "포트폴리오 매칭 종목은 추가매수 전 국민연금 지분율 기준일과 최근 DART 대량보유 공시를 함께 확인하세요.",
            "캐시 최신 기준일이 요청 기준일보다 오래되면 투자 판단에는 보수적으로 참고 신호만 반영하세요.",
        ],
        "summary": summary,
    }


def save_nps_portfolio_change_snapshot(snapshot: dict, settings: Settings) -> dict:
    write_json_store(nps_portfolio_change_snapshot_path(settings), snapshot)
    return {"status": "saved", "path": str(nps_portfolio_change_snapshot_path(settings)), "snapshot": snapshot}


def build_nps_rebalancing_pressure_index(snapshot: dict | None) -> dict:
    if not isinstance(snapshot, dict) or not snapshot:
        return {
            "status": "missing",
            "by_ticker": {},
            "global_kr_pressure": None,
            "decision_rule": "국민연금 리밸런싱 스냅샷이 없어 추천/포트폴리오 판단에는 반영하지 않습니다.",
        }
    context = snapshot.get("public_rebalancing_context") if isinstance(snapshot.get("public_rebalancing_context"), dict) else {}
    data_policy = context.get("data_policy") if isinstance(context.get("data_policy"), dict) else {}
    decision_rule = context.get("decision_rule") or (
        "국민연금 관련 신호는 공개자료 기반 압력/위험도 플래그로만 사용합니다."
    )
    global_kr_pressure = {
        "level": "market_watch",
        "penalty_points": 2,
        "reason": "국민연금 국내주식 리밸런싱 재개 보도와 주문 비공개 원칙으로 한국 종목은 수급 변동성 확인이 필요합니다.",
        "order_flow_access": data_policy.get("order_flow_access") or "not_available",
        "realtime_rebalancing_detection": data_policy.get("realtime_rebalancing_detection") or "not_supported",
        "source_url": context.get("primary_article_url") or NPS_REBALANCING_ARTICLE_URL,
    }
    by_ticker: dict[str, dict] = {}
    for match in snapshot.get("portfolio_matches") or []:
        if not isinstance(match, dict):
            continue
        ticker = str(match.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        by_ticker[ticker] = {
            "ticker": ticker,
            "level": "matched_holding_watch",
            "penalty_points": 4,
            "issuer": match.get("issuer"),
            "base_date": match.get("base_date"),
            "holding_ratio": match.get("holding_ratio"),
            "reason": (
                f"{match.get('issuer') or match.get('holding_name') or ticker} 국민연금 대량보유 공개자료가 매칭되어 "
                "추가매수 전 지분율 기준일과 최근 공시 확인이 필요합니다."
            ),
            "data_policy": data_policy,
            "decision_rule": decision_rule,
        }
    return {
        "status": snapshot.get("status") or "unknown",
        "as_of": snapshot.get("as_of"),
        "latest_event_date": snapshot.get("latest_event_date"),
        "summary": snapshot.get("summary"),
        "by_ticker": by_ticker,
        "global_kr_pressure": global_kr_pressure,
        "decision_rule": decision_rule,
    }


def nps_rebalancing_pressure_for_candidate(
    pressure_index: dict | None,
    ticker: str,
    *,
    currency: str | None = None,
) -> dict | None:
    if not isinstance(pressure_index, dict) or pressure_index.get("status") == "missing":
        return None
    normalized = str(ticker or "").strip().upper()
    by_ticker = pressure_index.get("by_ticker") if isinstance(pressure_index.get("by_ticker"), dict) else {}
    if normalized in by_ticker:
        return by_ticker[normalized]
    is_kr_equity_like = normalized.isdigit() and len(normalized) == 6 and str(currency or "KRW").upper() == "KRW"
    global_pressure = pressure_index.get("global_kr_pressure")
    if is_kr_equity_like and isinstance(global_pressure, dict):
        return {
            **global_pressure,
            "ticker": normalized,
            "decision_rule": pressure_index.get("decision_rule"),
        }
    return None


def apply_nps_rebalancing_pressure_to_recommendation(candidate: dict, pressure: dict | None) -> dict:
    if not isinstance(pressure, dict) or not pressure:
        return candidate
    points = max(0, int(pressure.get("penalty_points") or 0))
    label = (
        "국민연금 리밸런싱 매칭 보유 공시"
        if pressure.get("level") == "matched_holding_watch"
        else "국민연금 리밸런싱 시장 압력"
    )
    if points:
        candidate["score"] = int(candidate.get("score") or 0) - points
        candidate.setdefault("score_penalties", []).append(f"{label} (-{points})")
    reason = str(pressure.get("reason") or "").strip()
    if reason:
        candidate.setdefault("risk_notes", []).append(reason)
    candidate.setdefault("evidence_sources", []).append(
        "국민연금 리밸런싱 공개자료 기반 압력 신호"
    )
    candidate["nps_rebalancing_pressure"] = {
        "level": pressure.get("level"),
        "penalty_points": points,
        "reason": reason,
        "base_date": pressure.get("base_date"),
        "holding_ratio": pressure.get("holding_ratio"),
        "decision_rule": pressure.get("decision_rule"),
    }
    return candidate
