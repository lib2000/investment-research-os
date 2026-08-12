"""Staged Toss research-to-trade workflow.

The workflow automates evidence collection and review artifacts only.  It
creates no live order and deliberately leaves quantity/order approval to a
human-controlled step.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


POSITIVE_WORDS = {
    "상향", "호실적", "성장", "개선", "흑자", "수주", "계약", "증가", "호재", "긍정",
    "beat", "upgrade", "growth", "profit", "contract", "surge", "positive",
}
NEGATIVE_WORDS = {
    "하향", "부진", "적자", "감소", "리콜", "소송", "규제", "악재", "우려", "부정",
    "miss", "downgrade", "loss", "decline", "lawsuit", "risk", "negative",
}


def _now_kst() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul"))


def workflow_state_path(settings: Settings) -> Path:
    path = resolve_vault_dir(settings.research_vault_dir) / "_system" / "toss_trade_workflow.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def workflow_history_path(settings: Settings) -> Path:
    path = resolve_vault_dir(settings.research_vault_dir) / "_system" / "toss_trade_workflow_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def paper_evaluation_path(settings: Settings) -> Path:
    path = resolve_vault_dir(settings.research_vault_dir) / "_system" / "toss_paper_evaluation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_workflow_state(settings: Settings) -> dict[str, Any]:
    path = workflow_state_path(settings)
    if not path.exists():
        return {"status": "not_run", "runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "corrupt", "runs": []}
    return payload if isinstance(payload, dict) else {"status": "invalid", "runs": []}


def write_workflow_state(settings: Settings, payload: dict[str, Any]) -> None:
    workflow_state_path(settings).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_workflow_history(settings: Settings, *, limit: int = 200) -> list[dict[str, Any]]:
    path = workflow_history_path(settings)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines[-max(1, min(limit, 1000)):]):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def _text(item: dict[str, Any]) -> str:
    values = [
        item.get(key)
        for key in (
            "title",
            "summary",
            "raw_content",
            "scope_reason",
            "tags",
            "company_name",
            "issuer",
            "organization",
            "entities",
            "related_companies",
        )
    ]
    return " ".join(str(value or "") for value in values).lower()


_LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "company", "co", "ltd", "limited",
    "holdings", "holding", "group", "plc", "pbc", "common", "stock", "class", "ordinary",
}
_IGNORED_ALIASES = {
    "etf", "market", "sector", "macro", "policy", "news", "common", "stock", "company",
    "tiger", "kodex", "kiwoom", "sol", "kindex", "arirang", "ace", "plus", "hanaro",
}


def _normalize_entity_text(value: Any) -> str:
    """Normalize Korean/English company text for deterministic substring matching."""
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").lower())


def _entity_aliases(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    aliases: list[str] = []

    def add(candidate: str) -> None:
        normalized = _normalize_entity_text(candidate)
        if not normalized or normalized in _IGNORED_ALIASES:
            return
        # Two Korean characters are useful, but short English/common tokens are too noisy.
        has_korean = bool(re.search(r"[가-힣]", normalized))
        if len(normalized) < (2 if has_korean else 4):
            return
        if normalized not in aliases:
            aliases.append(normalized)

    add(raw)
    words = re.findall(r"[A-Za-z0-9가-힣]+", raw)
    if words and any(re.search(r"[A-Za-z]", word) for word in words):
        trimmed = [word for word in words if word.lower() not in _LEGAL_SUFFIXES]
        add(" ".join(trimmed))
    return aliases


def _holding_entity_aliases(holding: dict[str, Any]) -> list[dict[str, str]]:
    """Return aliases with their origin so matching evidence is explainable."""
    values: list[tuple[Any, str]] = []
    for key in ("name", "company_name", "display_name", "issuer"):
        if holding.get(key):
            values.append((holding.get(key), "company_name"))
    verification = holding.get("verification")
    if isinstance(verification, dict) and verification.get("company_name"):
        values.append((verification.get("company_name"), "verified_company_name"))
    for key in ("alias", "aliases"):
        raw = holding.get(key)
        if isinstance(raw, (list, tuple, set)):
            values.extend((item, "alias") for item in raw)
        elif raw:
            values.append((raw, "alias"))
    aliases: list[dict[str, str]] = []
    seen: set[str] = set()
    for value, matched_by in values:
        for alias in _entity_aliases(value):
            if alias in seen:
                continue
            seen.add(alias)
            aliases.append({"alias": alias, "matched_by": matched_by, "display": str(value).strip()})
    return aliases


def _ticker_candidates(item: dict[str, Any]) -> set[str]:
    candidates: set[str] = set()
    for key in ("ticker", "scope", "symbol"):
        value = str(item.get(key) or "").strip().upper()
        if re.fullmatch(r"[A-Z0-9.\-]{1,20}", value) and value not in {"NEWS", "MARKET", "SECTOR", "MACRO", "INBOX"}:
            candidates.add(value)
    for value in item.get("related_tickers") or []:
        text = str(value or "").strip().upper()
        if re.fullmatch(r"[A-Z0-9.\-]{1,20}", text):
            candidates.add(text)
    return candidates


def _signal(text: str) -> tuple[str, int, int]:
    positive = sum(1 for word in POSITIVE_WORDS if word in text)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text)
    if positive >= negative + 1 and positive > 0:
        return "positive", positive, negative
    if negative >= positive + 1 and negative > 0:
        return "negative", positive, negative
    return "neutral", positive, negative


def analyze_news_items(news_items: list[dict[str, Any]], holdings: list[dict[str, Any]]) -> dict[str, Any]:
    holding_tickers = {
        str(item.get("ticker") or "").strip().upper()
        for item in holdings
        if isinstance(item, dict) and item.get("ticker")
    }
    alias_index: dict[str, list[dict[str, str]]] = {}
    for holding in holdings:
        if not isinstance(holding, dict):
            continue
        ticker = str(holding.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        for alias in _holding_entity_aliases(holding):
            alias_index.setdefault(alias["alias"], []).append(
                {
                    "ticker": ticker,
                    "matched_by": alias["matched_by"],
                    "display": alias["display"],
                }
            )
    analyzed: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for item in news_items[:100]:
        if not isinstance(item, dict):
            continue
        text = _text(item)
        normalized_text = _normalize_entity_text(text)
        signal, positive_hits, negative_hits = _signal(text)
        tickers = sorted(_ticker_candidates(item))
        matched_by_ticker: dict[str, list[dict[str, str]]] = {}
        for ticker in sorted(set(tickers) & holding_tickers):
            matched_by_ticker[ticker] = [{"matched_by": "explicit_ticker", "display": ticker}]
        for alias, alias_matches in alias_index.items():
            if alias not in normalized_text:
                continue
            for alias_match in alias_matches:
                matched_by_ticker.setdefault(alias_match["ticker"], []).append(
                    {"matched_by": alias_match["matched_by"], "display": alias_match["display"]}
                )
        matched = sorted(matched_by_ticker)
        matched_context = [
            {
                "ticker": str(holding.get("ticker") or "").strip().upper(),
                "name": holding.get("name"),
                "quantity": holding.get("quantity"),
                "current_price": holding.get("current_price"),
                "source": holding.get("source", "holding"),
                "source_types": holding.get("source_types") or [holding.get("source", "holding")],
            }
            for holding in holdings
            if isinstance(holding, dict)
            and str(holding.get("ticker") or "").strip().upper() in matched
        ]
        match_evidence = [
            {
                "ticker": ticker,
                "matches": sorted(
                    {
                        (entry.get("matched_by"), entry.get("display"))
                        for entry in entries
                    }
                ),
            }
            for ticker, entries in sorted(matched_by_ticker.items())
        ]
        held_tickers = {
            str(context.get("ticker") or "").strip().upper()
            for context in matched_context
            if "holding" in (context.get("source_types") or [context.get("source", "holding")])
            and (context.get("quantity") is not None or context.get("source") == "holding")
        }
        confidence = float(item.get("confidence") or 0)
        quality = str(item.get("quality_status") or item.get("review_status") or "unknown")
        evidence_strength = "strong" if item.get("source_url") and confidence >= 0.7 else "medium" if item.get("source_url") or confidence >= 0.55 else "low"
        action = "WATCH"
        if matched and signal == "positive":
            action = "BUY_REVIEW"
        elif matched and signal == "negative" and held_tickers:
            action = "SELL_REVIEW"
        analyzed_item = {
            "id": item.get("id"),
            "title": str(item.get("title") or "뉴스 항목")[:140],
            "source_url": item.get("source_url"),
            "tickers": tickers,
            "matched_holdings": matched,
            "matched_entities": match_evidence,
            "matched_context": matched_context,
            "signal": signal,
            "positive_hits": positive_hits,
            "negative_hits": negative_hits,
            "confidence": confidence,
            "evidence_strength": evidence_strength,
            "quality_status": quality,
            "action": action,
        }
        analyzed.append(analyzed_item)
        if action in {"BUY_REVIEW", "SELL_REVIEW"}:
            proposal_id = hashlib.sha256(
                f"{item.get('id')}|{action}|{','.join(matched)}".encode("utf-8")
            ).hexdigest()[:16]
            proposals.append(
                {
                    "proposal_id": proposal_id,
                    "action": action,
                    "symbols": matched,
                    "reference_prices": {
                        str(item.get("ticker")): item.get("current_price")
                        for item in matched_context
                        if item.get("current_price") is not None
                    },
                    "evidence_strength": evidence_strength,
                    "confidence": confidence,
                    "source_news_id": item.get("id"),
                    "match_evidence": match_evidence,
                    "reason": "뉴스 신호와 종목명·티커 매칭 근거가 조건에 맞았습니다.",
                    "quantity": None,
                    "price": None,
                    "order_type": None,
                    "status": "manual_review_required",
                    "execution": "blocked_live_order",
                    "risk_note": "수량·가격·손절 기준을 사람이 검토하고 별도로 승인해야 합니다.",
                }
            )
    return {
        "news_count": len(analyzed),
        "matched_news_count": sum(1 for item in analyzed if item.get("matched_holdings")),
        "analyzed": analyzed,
        "proposals": proposals,
        "message": "뉴스 분석과 조건 검색을 완료했습니다. 주문은 생성하지 않았습니다.",
    }


def build_trade_review(orders: list[dict[str, Any]]) -> dict[str, Any]:
    filled_quantity = 0.0
    filled_amount = 0.0
    buy_count = sell_count = canceled_count = partial_count = 0
    for order in orders:
        if not isinstance(order, dict):
            continue
        side = str(order.get("side") or "").upper()
        status = str(order.get("status") or "").upper()
        execution = order.get("execution") if isinstance(order.get("execution"), dict) else {}
        filled_quantity += float(execution.get("filled_quantity") or 0)
        filled_amount += float(execution.get("filled_amount") or 0)
        buy_count += side == "BUY"
        sell_count += side == "SELL"
        canceled_count += status == "CANCELED"
        partial_count += status == "PARTIAL_FILLED" or (
            float(execution.get("filled_quantity") or 0) > 0
            and float(execution.get("filled_quantity") or 0) < float(order.get("quantity") or 0)
        )
    return {
        "order_count": len(orders),
        "buy_order_count": buy_count,
        "sell_order_count": sell_count,
        "canceled_count": canceled_count,
        "partial_fill_count": partial_count,
        "filled_quantity": round(filled_quantity, 8),
        "filled_amount": round(filled_amount, 2),
        "review_status": "needs_human_review" if orders else "no_orders_today",
        "message": "체결·취소·부분체결을 분리해 기록했습니다." if orders else "오늘 주문 이력이 없습니다.",
    }


def build_workflow_result(
    *,
    run_at: str,
    news_result: dict[str, Any],
    orders: list[dict[str, Any]],
    paper_fills: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    review = build_trade_review(orders)
    simulated_fills = [item for item in (paper_fills or []) if isinstance(item, dict)]
    return {
        "status": "success",
        "workflow": "news_analysis_condition_search_trade_record_review",
        "run_at": run_at,
        "stages": {
            "news_analysis": {"status": "completed", "count": news_result.get("news_count", 0)},
            "condition_search": {"status": "completed", "proposal_count": len(news_result.get("proposals", []))},
            "trade": {
                "status": "blocked_live_order",
                "mode": "manual_approval_required",
                "created_order_count": 0,
                "message": "자동 매매는 안전상 비활성화되어 주문 API를 호출하지 않았습니다.",
            },
            "paper_simulation": {
                "status": "completed" if simulated_fills else "awaiting_user_confirmation",
                "fill_count": len(simulated_fills),
                "message": "모의체결만 기록했으며 토스 주문 API는 호출하지 않았습니다."
                if simulated_fills
                else "사용자 확인 후 모의체결을 생성합니다.",
            },
            "record": {"status": "completed", "order_count": len(orders)},
            "review": review,
        },
        "news_analysis": news_result,
        "orders": orders,
        "paper_fills": simulated_fills,
        "review": review,
        "human_gate": {
            "required": True,
            "reason": "생성된 신호는 검증되지 않은 투자 판단이며 실계좌 주문으로 직접 연결하지 않습니다.",
        },
    }


def simulate_paper_fills(news_result: dict[str, Any], *, run_at: str) -> list[dict[str, Any]]:
    """Create deterministic one-share paper fills for review-only proposals."""
    fills: list[dict[str, Any]] = []
    for proposal in news_result.get("proposals") or []:
        if not isinstance(proposal, dict):
            continue
        action = str(proposal.get("action") or "").upper()
        side = "BUY" if action == "BUY_REVIEW" else "SELL" if action == "SELL_REVIEW" else ""
        if not side:
            continue
        prices = proposal.get("reference_prices") if isinstance(proposal.get("reference_prices"), dict) else {}
        for symbol in proposal.get("symbols") or []:
            ticker = str(symbol or "").strip().upper()
            try:
                reference_price = float(prices.get(ticker) or 0)
            except (TypeError, ValueError):
                reference_price = 0.0
            paper_id = hashlib.sha256(f"paper|{proposal.get('proposal_id')}|{ticker}".encode("utf-8")).hexdigest()[:16]
            fills.append({
                "paper_order_id": paper_id,
                "proposal_id": proposal.get("proposal_id"),
                "symbol": ticker,
                "side": side,
                "status": "simulated_filled" if reference_price > 0 else "awaiting_price",
                "quantity": 1 if reference_price > 0 else 0,
                "reference_price": round(reference_price, 4) if reference_price > 0 else None,
                "amount": round(reference_price, 2) if reference_price > 0 else 0,
                "simulated_at": run_at,
                "execution": "paper_only",
                "evidence_strength": proposal.get("evidence_strength", "low"),
                "confidence": proposal.get("confidence", 0),
            })
    return fills


def append_workflow_history(settings: Settings, result: dict[str, Any]) -> None:
    record = {
        "run_at": result.get("run_at"),
        "status": result.get("status"),
        "workflow": result.get("workflow"),
        "stage_status": {key: value.get("status") for key, value in (result.get("stages") or {}).items() if isinstance(value, dict)},
        "proposal_count": len((result.get("news_analysis") or {}).get("proposals") or []),
        "order_count": len(result.get("orders") or []),
        "paper_fills": [item for item in result.get("paper_fills") or [] if isinstance(item, dict)],
        "review": result.get("review") or {},
    }
    with workflow_history_path(settings).open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False))
        file.write("\n")


def build_paper_evaluation(
    records: list[dict[str, Any]],
    *,
    window_days: int = 7,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Evaluate marked paper fills without treating them as live performance."""
    days = max(1, min(int(window_days or 7), 30))
    try:
        as_of = date.fromisoformat(str(as_of_date)) if as_of_date else _now_kst().date()
    except ValueError:
        as_of = _now_kst().date()
    window_start = as_of - timedelta(days=days - 1)
    fills: list[dict[str, Any]] = []
    observed_dates: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        run_date = str(record.get("run_at") or "")[:10]
        try:
            record_date = date.fromisoformat(run_date)
        except ValueError:
            continue
        if record_date < window_start or record_date > as_of:
            continue
        paper_fills = record.get("paper_fills") if isinstance(record.get("paper_fills"), list) else []
        for fill in paper_fills:
            if not isinstance(fill, dict):
                continue
            observed_dates.add(run_date)
            fills.append({**fill, "run_date": run_date})
    marked = []
    unmarked_count = 0
    for fill in fills:
        if str(fill.get("status") or "") != "simulated_filled":
            unmarked_count += 1
            continue
        try:
            quantity = float(fill.get("quantity") or 0)
            entry = float(fill.get("reference_price") or 0)
            mark = float(fill.get("mark_price") or 0)
        except (TypeError, ValueError):
            quantity = entry = mark = 0.0
        if quantity <= 0 or entry <= 0 or mark <= 0:
            unmarked_count += 1
            continue
        side = str(fill.get("side") or "BUY").upper()
        pnl = (mark - entry) * quantity if side == "BUY" else (entry - mark) * quantity
        marked.append({**fill, "entry_amount": round(entry * quantity, 2), "mark_amount": round(mark * quantity, 2), "pnl": round(pnl, 2)})
    pnl = round(sum(float(item["pnl"]) for item in marked), 2)
    invested = round(sum(float(item["entry_amount"]) for item in marked), 2)
    wins = sum(1 for item in marked if item["pnl"] > 0)
    losses = sum(1 for item in marked if item["pnl"] < 0)
    curve = []
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for item in sorted(marked, key=lambda value: (value.get("simulated_at") or "", value.get("paper_order_id") or "")):
        cumulative += float(item["pnl"])
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
        curve.append(round(cumulative, 2))
    by_symbol: dict[str, dict[str, Any]] = {}
    for item in marked:
        symbol = str(item.get("symbol") or "UNKNOWN")
        bucket = by_symbol.setdefault(symbol, {"symbol": symbol, "fill_count": 0, "pnl": 0.0, "wins": 0, "losses": 0})
        bucket["fill_count"] += 1
        bucket["pnl"] = round(bucket["pnl"] + float(item["pnl"]), 2)
        bucket["wins"] += int(item["pnl"] > 0)
        bucket["losses"] += int(item["pnl"] < 0)
    sample_size = len(marked)
    return {
        "status": "completed" if len(observed_dates) >= days and sample_size else "insufficient_sample",
        "window_days": days,
        "window_start": window_start.isoformat(),
        "as_of_date": as_of.isoformat(),
        "observed_dates": sorted(observed_dates),
        "days_observed": len(observed_dates),
        "sample_size": sample_size,
        "unmarked_count": unmarked_count,
        "filled_count": len(fills),
        "invested_amount": invested,
        "pnl": pnl,
        "return_rate": round((pnl / invested) if invested else 0.0, 6),
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / sample_size) if sample_size else 0.0, 6),
        "max_drawdown": round(max_drawdown, 2),
        "evidence_strength": "low" if sample_size < 10 or unmarked_count else "medium",
        "by_symbol": sorted(by_symbol.values(), key=lambda item: (-abs(item["pnl"]), item["symbol"])),
        "equity_curve": curve,
        "message": "모의체결 평가이며 실계좌 수익률이나 투자 권고가 아닙니다.",
    }
