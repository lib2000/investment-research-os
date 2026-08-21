"""Build local-only evidence packets for human portfolio review.

The packet deliberately inventories persisted evidence without creating a team
report, trade setup, checklist answer, recommendation, or order instruction.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from research_os.portfolio_analysis_coverage import (
    HUMAN_REVIEW_PACKET_TYPE,
    normalize_portfolio_analysis_ticker,
)

SEOUL = ZoneInfo("Asia/Seoul")
OFFICIAL_DART_PREFIX = "https://dart.fss.or.kr/"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _number_or_none(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not numeric.is_integer():
        return numeric
    return int(numeric)


def _source_label(raw_source: Any, *, kind: str) -> str:
    source = str(raw_source or "").lower()
    if "koreainvestment.com" in source:
        return "KIS 국내 시세 API"
    if source == "toss_holdings" or "toss" in source:
        return "토스증권 보유자산 동기화"
    if kind == "price":
        return "저장 포트폴리오 가격"
    if kind == "sync":
        return "저장 포트폴리오 동기화"
    return "저장 데이터"


def portfolio_holding_evidence(store: dict[str, Any], ticker: str) -> list[dict[str, Any]]:
    """Extract only review-relevant, non-secret fields for one stored holding."""
    normalized = normalize_portfolio_analysis_ticker(ticker)
    portfolios = store.get("portfolios") if isinstance(store.get("portfolios"), dict) else {}
    rows: list[dict[str, Any]] = []
    for portfolio_key, portfolio in portfolios.items():
        if not isinstance(portfolio, dict):
            continue
        portfolio_name = _clean_text(portfolio.get("portfolio_name")) or _clean_text(portfolio_key) or "포트폴리오"
        holdings = portfolio.get("holdings") if isinstance(portfolio.get("holdings"), list) else []
        for holding in holdings:
            if not isinstance(holding, dict):
                continue
            if normalize_portfolio_analysis_ticker(holding.get("ticker")) != normalized:
                continue
            rows.append(
                {
                    "portfolio_name": portfolio_name,
                    "company_name": _clean_text(holding.get("name")) or normalized,
                    "quantity": _number_or_none(holding.get("quantity")),
                    "current_price": _number_or_none(holding.get("current_price")),
                    "price_source": _source_label(holding.get("price_source"), kind="price"),
                    "price_refresh_status": _clean_text(holding.get("price_refresh_status")),
                    "price_checked_at": _clean_text(holding.get("price_checked_at")),
                    "sync_source": _source_label(holding.get("sync_source"), kind="sync"),
                    "sync_status": _clean_text(holding.get("sync_status")),
                    "sync_checked_at": _clean_text(holding.get("sync_checked_at")),
                }
            )
    return rows


def stored_dart_filings(vault_dir: Path, ticker: str) -> list[dict[str, str]]:
    """Read and deduplicate persisted official DART filing metadata for a ticker."""
    normalized = normalize_portfolio_analysis_ticker(ticker)
    folder = vault_dir / normalized
    if not folder.exists():
        return []
    by_receipt: dict[str, dict[str, str]] = {}
    for path in sorted(folder.glob("*.json")):
        payload = _read_json(path, {})
        if not isinstance(payload, dict):
            continue
        filing = payload.get("filing")
        if not isinstance(filing, dict):
            continue
        filing_ticker = normalize_portfolio_analysis_ticker(filing.get("stock_code"))
        if filing_ticker and filing_ticker != normalized:
            continue
        receipt_number = _clean_text(filing.get("rcept_no"))
        source_url = _clean_text(filing.get("source_url"))
        if not receipt_number or not source_url or not source_url.startswith(OFFICIAL_DART_PREFIX):
            continue
        by_receipt[receipt_number] = {
            "receipt_date": _clean_text(filing.get("receipt_date")) or "확인 필요",
            "rcept_no": receipt_number,
            "report_name": " ".join(str(filing.get("report_name") or "공시명 확인 필요").split()),
            "source_url": source_url,
        }
    return sorted(
        by_receipt.values(),
        key=lambda item: (item["receipt_date"], item["rcept_no"]),
        reverse=True,
    )


def dart_daily_watch_evidence(cache: dict[str, Any], ticker: str) -> dict[str, Any]:
    """Describe whether the persisted daily DART watch actually checked this ticker."""
    normalized = normalize_portfolio_analysis_ticker(ticker)
    daily = cache.get("daily_check") if isinstance(cache.get("daily_check"), dict) else {}
    checked = {
        normalize_portfolio_analysis_ticker(value)
        for value in (daily.get("checked_tickers") or [])
    }
    failures = [
        item
        for item in (daily.get("failed_tickers") or [])
        if isinstance(item, dict)
        and normalize_portfolio_analysis_ticker(item.get("ticker")) == normalized
    ]
    return {
        "last_run": _clean_text(cache.get("last_run")) or _clean_text(cache.get("updated_at")),
        "daily_checked_at": _clean_text(daily.get("checked_at")),
        "checked": normalized in checked,
        "failure_count": len(failures),
        "failures": [
            {"message": _clean_text(item.get("error")) or _clean_text(item.get("message"))}
            for item in failures
        ],
    }


def _format_price(value: int | float | None) -> str:
    if value is None:
        return "가격 확인 필요"
    return f"{value:,.0f}원"


def build_portfolio_human_review_packet(
    *,
    ticker: str,
    portfolio_store: dict[str, Any],
    dart_cache: dict[str, Any],
    vault_dir: Path,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build an evidence inventory; this never changes document or review readiness."""
    normalized = normalize_portfolio_analysis_ticker(ticker)
    if not normalized:
        raise ValueError("티커가 필요합니다.")
    timestamp = generated_at or datetime.now(SEOUL)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=SEOUL)
    timestamp = timestamp.astimezone(SEOUL).replace(microsecond=0)

    holdings = portfolio_holding_evidence(portfolio_store, normalized)
    filings = stored_dart_filings(vault_dir, normalized)
    daily_watch = dart_daily_watch_evidence(dart_cache, normalized)
    company_name = next((item["company_name"] for item in holdings if item.get("company_name")), normalized)
    price_rows = [item for item in holdings if item.get("current_price") is not None]
    latest_price = max(price_rows, key=lambda item: str(item.get("price_checked_at") or ""), default=None)
    quantity_confirmation_required = any(
        str(item.get("sync_status") or "").endswith("_missing")
        for item in holdings
    )
    latest_filing = filings[0] if filings else None

    review_requirements = []
    if quantity_confirmation_required:
        review_requirements.append(
            "토스 동기화에서 미검출된 보유 수량은 자동으로 바꾸지 않았습니다. 실제 계좌의 수량·평단을 사람이 확인하세요."
        )
    elif not holdings:
        review_requirements.append("저장 포트폴리오에서 보유 기록을 찾지 못했습니다. 계좌와 종목 연결을 먼저 확인하세요.")
    if latest_filing:
        review_requirements.append(
            f"DART {latest_filing['report_name']} 원문에서 매출·손익·현금흐름·계약/자금조달 주석이 기존 논거를 바꾸는지 확인하세요."
        )
    else:
        review_requirements.append("저장된 공식 DART 공시를 찾지 못했습니다. 공시 감시 상태와 법인코드 매칭을 확인하세요.")
    review_requirements.append(
        "기준 리포트, 매매 전략, 16개 체크리스트는 사람 검토가 끝난 뒤 별도 작성해야 하며 이 패킷으로 자동 완료하지 않습니다."
    )

    summary_bits = []
    if latest_price:
        summary_bits.append(
            f"저장 가격 {_format_price(latest_price.get('current_price'))} ({latest_price.get('price_checked_at') or '시각 확인 필요'})"
        )
    if latest_filing:
        summary_bits.append(
            f"최신 공식 공시 {latest_filing['report_name']} ({latest_filing['receipt_date']})"
        )
    if quantity_confirmation_required:
        summary_bits.append("토스 잔고 미검출로 수량 확인 필요")
    summary = "; ".join(summary_bits) or "사람 검토를 위한 저장 증빙을 확인하세요."

    return {
        "type": HUMAN_REVIEW_PACKET_TYPE,
        "ticker": normalized,
        "date": timestamp.date().isoformat(),
        "created_at": timestamp.isoformat(),
        "title": f"{company_name} ({normalized}) 사람 검토 준비 패킷",
        "summary": summary,
        "tags": ["human-review", "evidence-inventory", "official-source"],
        "data_quality": "저장된 공식 공시·가격·동기화 메타데이터만 사용",
        "source_count": len(filings) + len(price_rows),
        "review_gate": {
            "affects_document_coverage": False,
            "affects_review_gate": False,
            "reason": "근거 목록은 사람 검토를 돕지만 기준 리포트·매매 전략·체크리스트를 대체하지 않습니다.",
        },
        "holding_snapshot": {
            "holding_count": len(holdings),
            "quantity_confirmation_required": quantity_confirmation_required,
            "items": holdings,
        },
        "price_evidence": latest_price,
        "dart_daily_watch": daily_watch,
        "dart_filings": filings,
        "review_requirements": review_requirements,
    }


def render_portfolio_human_review_packet_markdown(packet: dict[str, Any]) -> str:
    """Render a concise, non-recommendation review packet."""
    holdings = (packet.get("holding_snapshot") or {}).get("items") or []
    price = packet.get("price_evidence") or {}
    daily_watch = packet.get("dart_daily_watch") or {}
    filings = packet.get("dart_filings") or []
    review_gate = packet.get("review_gate") or {}
    lines = [
        f"# {packet.get('title') or packet.get('ticker')}",
        "",
        f"생성 시각: {packet.get('created_at') or '확인 필요'}",
        "",
        "> 이 문서는 사람 검토를 위한 증빙 목록입니다. 투자 판단·매수·매도 지시가 아니며, 분석 문서 커버리지나 검토 게이트를 통과시키지 않습니다.",
        "",
        "## 저장된 가격 근거",
    ]
    if price:
        lines.extend(
            [
                f"- 현재가: {_format_price(price.get('current_price'))}",
                f"- 출처: {price.get('price_source') or '확인 필요'}",
                f"- 확인 시각: {price.get('price_checked_at') or '확인 필요'}",
                f"- 갱신 상태: {price.get('price_refresh_status') or '확인 필요'}",
            ]
        )
    else:
        lines.append("- 저장 가격을 확인할 수 없습니다.")

    lines.extend(["", "## 보유 동기화 상태"])
    if holdings:
        for item in holdings:
            lines.append(
                f"- {item.get('portfolio_name') or '포트폴리오'}: 수량 {item.get('quantity') if item.get('quantity') is not None else '확인 필요'} · "
                f"{item.get('sync_source') or '출처 확인 필요'} · {item.get('sync_status') or '상태 확인 필요'} · "
                f"확인 {item.get('sync_checked_at') or '시각 확인 필요'}"
            )
    else:
        lines.append("- 저장 포트폴리오에서 종목을 찾지 못했습니다.")

    lines.extend(["", "## 공식 DART 공시"])
    if filings:
        for filing in filings:
            lines.append(
                f"- {filing['receipt_date']} · {filing['report_name']} · [원문]({filing['source_url']})"
            )
    else:
        lines.append("- 저장된 공식 DART 공시가 없습니다.")
    lines.extend(
        [
            f"- 일일 감시 확인: {'확인됨' if daily_watch.get('checked') else '확인 필요'} · "
            f"{daily_watch.get('daily_checked_at') or daily_watch.get('last_run') or '시각 확인 필요'} · 실패 {daily_watch.get('failure_count') or 0}건",
            "",
            "## 사람 검토가 필요한 항목",
        ]
    )
    lines.extend(f"- {item}" for item in packet.get("review_requirements") or [])
    lines.extend(
        [
            "",
            "## 검토 게이트",
            f"- 문서 커버리지 반영: {'예' if review_gate.get('affects_document_coverage') else '아니오'}",
            f"- 검토 게이트 반영: {'예' if review_gate.get('affects_review_gate') else '아니오'}",
            f"- 이유: {review_gate.get('reason') or '확인 필요'}",
            "",
        ]
    )
    return "\n".join(lines)


def write_portfolio_human_review_packet(packet: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Write a stable same-day JSON/Markdown pair under the local research vault."""
    ticker = normalize_portfolio_analysis_ticker(packet.get("ticker"))
    packet_date = _clean_text(packet.get("date"))
    if not ticker or not packet_date:
        raise ValueError("패킷의 티커와 날짜가 필요합니다.")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{ticker}-human-review-packet-{packet_date}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_portfolio_human_review_packet_markdown(packet), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
