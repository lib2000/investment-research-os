"""Daily recommendation milestone tracking helpers."""

from __future__ import annotations

from datetime import date, timedelta


TRACKING_MILESTONES = [
    {"key": "7d", "label": "추천 후 1주일", "days": 7},
    {"key": "15d", "label": "추천 후 15일", "days": 15},
    {"key": "1m", "label": "추천 후 1달", "days": 30},
    {"key": "3m", "label": "추천 후 3달", "days": 90},
    {"key": "6m", "label": "추천 후 6달", "days": 180},
]


def build_tracking_milestones(recommendation_date: date) -> list[dict]:
    return [
        {
            **milestone,
            "target_date": (recommendation_date + timedelta(days=int(milestone["days"]))).isoformat(),
            "status": "pending",
            "price": None,
            "price_checked_at": None,
            "price_change": None,
            "price_change_pct": None,
            "investment_situation": "아직 추적 예정일 전입니다.",
        }
        for milestone in TRACKING_MILESTONES
    ]


def summarize_tracking_performance(records: list[dict]) -> dict:
    summary = {
        "total_milestones": 0,
        "complete_count": 0,
        "pending_count": 0,
        "price_unavailable_count": 0,
        "positive_count": 0,
        "negative_count": 0,
        "flat_count": 0,
        "best": None,
        "worst": None,
    }
    completed_rows: list[dict] = []
    for record in records:
        for milestone in record.get("tracking_milestones", []):
            if not isinstance(milestone, dict):
                continue
            summary["total_milestones"] += 1
            status = milestone.get("status") or "pending"
            if status == "complete":
                summary["complete_count"] += 1
                try:
                    change_pct = float(milestone.get("price_change_pct") or 0)
                except (TypeError, ValueError):
                    change_pct = 0.0
                if change_pct > 0:
                    summary["positive_count"] += 1
                elif change_pct < 0:
                    summary["negative_count"] += 1
                else:
                    summary["flat_count"] += 1
                completed_rows.append(
                    {
                        "record_id": record.get("record_id"),
                        "company_name": record.get("company_name"),
                        "ticker": record.get("ticker"),
                        "rank": record.get("rank"),
                        "recommendation_date": record.get("recommendation_date"),
                        "milestone": milestone.get("label") or milestone.get("key"),
                        "target_date": milestone.get("target_date"),
                        "baseline_price": record.get("baseline_price"),
                        "price": milestone.get("price"),
                        "price_change": milestone.get("price_change"),
                        "price_change_pct": change_pct,
                        "investment_situation": milestone.get("investment_situation"),
                    }
                )
            elif status == "price_unavailable":
                summary["price_unavailable_count"] += 1
            else:
                summary["pending_count"] += 1
    completed_rows.sort(key=lambda item: item.get("price_change_pct") or 0, reverse=True)
    if completed_rows:
        summary["best"] = completed_rows[0]
        summary["worst"] = completed_rows[-1]
    return summary


def investment_situation(change_pct: float | None) -> str:
    if change_pct is None:
        return "현재가를 확인하지 못해 추적 보류 상태입니다."
    pct = change_pct * 100
    if pct >= 15:
        return "추천 후 강한 상승 구간입니다. 차익 실현/비중 유지 근거를 함께 점검하세요."
    if pct >= 5:
        return "추천 후 양호한 상승 구간입니다. 초기 근거가 유지되는지 확인하세요."
    if pct >= -5:
        return "추천 후 큰 변동 없이 관찰 구간입니다. 추가 근거를 더 확인하세요."
    if pct >= -15:
        return "추천 후 약세 구간입니다. 손실 원인과 투자 논거 훼손 여부를 점검하세요."
    return "추천 후 큰 폭의 약세입니다. 리스크 경고로 분류하고 재검토가 필요합니다."