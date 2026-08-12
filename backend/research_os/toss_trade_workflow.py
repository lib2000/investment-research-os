"""Staged Toss research-to-trade workflow.

The workflow automates evidence collection and review artifacts only.  It
creates no live order and deliberately leaves quantity/order approval to a
human-controlled step.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
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


def _text(item: dict[str, Any]) -> str:
    values = [item.get(key) for key in ("title", "summary", "raw_content", "scope_reason", "tags")]
    return " ".join(str(value or "") for value in values).lower()


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
    analyzed: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for item in news_items[:100]:
        if not isinstance(item, dict):
            continue
        text = _text(item)
        signal, positive_hits, negative_hits = _signal(text)
        tickers = sorted(_ticker_candidates(item))
        matched = sorted(set(tickers) & holding_tickers)
        confidence = float(item.get("confidence") or 0)
        quality = str(item.get("quality_status") or item.get("review_status") or "unknown")
        evidence_strength = "strong" if item.get("source_url") and confidence >= 0.7 else "medium" if item.get("source_url") or confidence >= 0.55 else "low"
        action = "WATCH"
        if matched and signal == "positive":
            action = "BUY_REVIEW"
        elif matched and signal == "negative":
            action = "SELL_REVIEW"
        analyzed_item = {
            "id": item.get("id"),
            "title": str(item.get("title") or "뉴스 항목")[:140],
            "source_url": item.get("source_url"),
            "tickers": tickers,
            "matched_holdings": matched,
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
                    "source_news_id": item.get("id"),
                    "reason": "뉴스 신호와 기존 보유종목이 조건에 맞았습니다.",
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
) -> dict[str, Any]:
    review = build_trade_review(orders)
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
            "record": {"status": "completed", "order_count": len(orders)},
            "review": review,
        },
        "news_analysis": news_result,
        "orders": orders,
        "review": review,
        "human_gate": {
            "required": True,
            "reason": "생성된 신호는 검증되지 않은 투자 판단이며 실계좌 주문으로 직접 연결하지 않습니다.",
        },
    }


def append_workflow_history(settings: Settings, result: dict[str, Any]) -> None:
    record = {
        "run_at": result.get("run_at"),
        "status": result.get("status"),
        "workflow": result.get("workflow"),
        "stage_status": {key: value.get("status") for key, value in (result.get("stages") or {}).items() if isinstance(value, dict)},
        "proposal_count": len((result.get("news_analysis") or {}).get("proposals") or []),
        "order_count": len(result.get("orders") or []),
        "review": result.get("review") or {},
    }
    with workflow_history_path(settings).open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False))
        file.write("\n")
