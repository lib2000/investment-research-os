from datetime import datetime
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.domestic_market_hours import build_domestic_market_hours_status


def kst(value: str) -> datetime:
    return datetime.fromisoformat(f"{value}+09:00")


def session_keys(payload):
    return {(item["venue"], item["key"]) for item in payload["current_sessions"]}


def trading_keys(payload):
    return {(item["venue"], item["key"]) for item in payload["current_trading_sessions"]}


def test_effective_schedule_exposes_krx_and_nxt_after_markets():
    payload = build_domestic_market_hours_status(kst("2026-09-14T16:00:00"))

    assert payload["schedule_version"] == "krx-after-market-2026-09-14"
    assert payload["effective_date"] == "2026-09-14"
    assert payload["market_state"] == "open"
    assert ("KRX", "after_market") in trading_keys(payload)
    assert ("NXT", "after_market") in trading_keys(payload)
    assert payload["holiday_status"] == "not_verified"


def test_boundary_transitions_keep_order_acceptance_separate_from_trading():
    before_nxt_pre = build_domestic_market_hours_status(kst("2026-09-14T07:59:49"))
    nxt_pre = build_domestic_market_hours_status(kst("2026-09-14T08:00:00"))
    krx_order_only = build_domestic_market_hours_status(kst("2026-09-14T08:50:00"))
    krx_regular = build_domestic_market_hours_status(kst("2026-09-14T09:00:00"))
    both_main = build_domestic_market_hours_status(kst("2026-09-14T09:00:30"))
    post_close_order = build_domestic_market_hours_status(kst("2026-09-14T15:30:00"))
    after_close = build_domestic_market_hours_status(kst("2026-09-14T20:00:00"))

    assert before_nxt_pre["market_state"] == "closed"
    assert ("NXT", "pre_market") in trading_keys(nxt_pre)
    assert krx_order_only["market_state"] == "order_acceptance"
    assert ("KRX", "regular_market") in session_keys(krx_order_only)
    assert trading_keys(krx_order_only) == set()
    assert trading_keys(krx_regular) == {("KRX", "regular_market")}
    assert ("NXT", "main_market") in trading_keys(both_main)
    assert post_close_order["market_state"] == "order_acceptance"
    assert ("KRX", "post_close_closing_price") in session_keys(post_close_order)
    assert ("NXT", "after_market") in session_keys(post_close_order)
    assert after_close["market_state"] == "closed"


def test_weekend_and_pre_effective_dates_do_not_claim_live_session_status():
    weekend = build_domestic_market_hours_status(kst("2026-09-19T10:00:00"))
    pre_effective = build_domestic_market_hours_status(kst("2026-09-11T16:30:00"))

    assert weekend["market_state"] == "non_business_day"
    assert weekend["current_sessions"] == []
    assert pre_effective["market_state"] == "pre_effective"
    assert pre_effective["current_sessions"] == []
