"""Versioned Korean domestic-equity session information for research operations.

The module deliberately describes market availability only.  It is not an
order-acceptance gate: individual instruments, broker routing, exchange
eligibility, holidays, and trading halts must still be checked at execution
time by the brokerage integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEDULE_EFFECTIVE_DATE = date(2026, 9, 14)
SCHEDULE_VERSION = "krx-after-market-2026-09-14"


def korea_timezone() -> ZoneInfo:
    """Return the IANA Korea timezone without relying on the host locale."""
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError as exc:  # pragma: no cover - normal Python ships tzdata.
        raise RuntimeError("Asia/Seoul 시간대를 찾을 수 없습니다.") from exc


@dataclass(frozen=True)
class DomesticMarketWindow:
    """One exchange window, including a possible pre-trade order phase."""

    venue: str
    key: str
    label: str
    order_open: time
    close: time
    trading_open: time
    summary: str
    eligibility_note: str

    def as_dict(self) -> dict[str, str]:
        return {
            "venue": self.venue,
            "key": self.key,
            "label": self.label,
            "order_open": self.order_open.isoformat(),
            "trading_open": self.trading_open.isoformat(),
            "close": self.close.isoformat(),
            "summary": self.summary,
            "eligibility_note": self.eligibility_note,
        }


def _time(value: str) -> time:
    return time.fromisoformat(value)


CURRENT_WINDOWS: tuple[DomesticMarketWindow, ...] = (
    DomesticMarketWindow(
        venue="NXT",
        key="pre_market",
        label="NXT 프리마켓",
        order_open=_time("07:59:50"),
        trading_open=_time("08:00:00"),
        close=_time("08:50:00"),
        summary="08:00–08:50",
        eligibility_note="NXT 선정종목만 해당하며 증권사·주문유형별 제한이 적용됩니다.",
    ),
    DomesticMarketWindow(
        venue="KRX",
        key="pre_open_closing_price",
        label="KRX 장개시전 시간외종가",
        order_open=_time("08:30:00"),
        trading_open=_time("08:30:00"),
        close=_time("08:40:00"),
        summary="08:30–08:40",
        eligibility_note="전일 종가 기준의 시간외종가 거래입니다.",
    ),
    DomesticMarketWindow(
        venue="KRX",
        key="regular_market",
        label="KRX 정규장",
        order_open=_time("08:20:00"),
        trading_open=_time("09:00:00"),
        close=_time("15:30:00"),
        summary="09:00–15:30 (호가접수 08:20부터)",
        eligibility_note="개별 종목의 거래정지·관리종목 여부와 주문유형 제한은 별도 확인이 필요합니다.",
    ),
    DomesticMarketWindow(
        venue="NXT",
        key="main_market",
        label="NXT 메인마켓",
        order_open=_time("09:00:30"),
        trading_open=_time("09:00:30"),
        close=_time("15:20:00"),
        summary="09:00:30–15:20",
        eligibility_note="NXT 선정종목만 해당하며 조건부지정가 주문은 제공되지 않습니다.",
    ),
    DomesticMarketWindow(
        venue="KRX",
        key="post_close_closing_price",
        label="KRX 장종료후 시간외종가",
        order_open=_time("15:30:00"),
        trading_open=_time("15:40:00"),
        close=_time("16:00:00"),
        summary="15:40–16:00 (호가접수 15:30부터)",
        eligibility_note="당일 종가 기준의 시간외종가 거래입니다.",
    ),
    DomesticMarketWindow(
        venue="NXT",
        key="after_market",
        label="NXT 애프터마켓",
        order_open=_time("15:30:00"),
        trading_open=_time("15:40:00"),
        close=_time("20:00:00"),
        summary="15:40–20:00 (호가접수 15:30부터)",
        eligibility_note="NXT 선정종목만 해당하며 15:30–15:40에는 지정가 주문만 가능합니다.",
    ),
    DomesticMarketWindow(
        venue="KRX",
        key="after_market",
        label="KRX 애프터마켓",
        order_open=_time("16:00:00"),
        trading_open=_time("16:00:00"),
        close=_time("20:00:00"),
        summary="16:00–20:00",
        eligibility_note="2026-09-14 신설 접속매매입니다. ETF·ETN 등 종목·증권사별 거래 제한을 확인해야 합니다.",
    ),
)


SOURCES: tuple[dict[str, str], ...] = (
    {
        "label": "한국거래소 KRX After-market 안내",
        "url": "https://global.krx.co.kr/contents/GLB/06/0602/0602020203/GLB0602020203T2.jsp",
    },
    {
        "label": "넥스트레이드 시장 운영시간",
        "url": "https://nextrade.co.kr/en/main.do",
    },
    {
        "label": "한국투자증권 2026-09-14 시행 공지",
        "url": "https://securities.koreainvestment.com/main/customer/notice/Notice.jsp?cmd=TF04ga000002&num=47532",
    },
)


def _coerce_korea_datetime(value: datetime | None) -> datetime:
    now = value or datetime.now(korea_timezone())
    if now.tzinfo is None:
        return now.replace(tzinfo=korea_timezone())
    return now.astimezone(korea_timezone())


def _is_between(value: time, start: time, end: time) -> bool:
    return start <= value < end


def _active_windows(now: datetime) -> tuple[list[DomesticMarketWindow], list[DomesticMarketWindow]]:
    """Return current order-acceptance and actual-trading windows."""
    current_time = now.timetz().replace(tzinfo=None)
    accepting = [
        window
        for window in CURRENT_WINDOWS
        if _is_between(current_time, window.order_open, window.close)
    ]
    trading = [
        window
        for window in accepting
        if _is_between(current_time, window.trading_open, window.close)
    ]
    return accepting, trading


def _state_label(state: str) -> str:
    return {
        "open": "거래 진행 중",
        "order_acceptance": "호가 접수 중",
        "closed": "장 종료",
        "non_business_day": "휴장일 가능성",
        "pre_effective": "시행 전 일정",
    }.get(state, "상태 확인 필요")


def _next_transition(now: datetime) -> str | None:
    """Return the next same-day schedule boundary in local ISO form."""
    candidates: list[datetime] = []
    for window in CURRENT_WINDOWS:
        for boundary in (window.order_open, window.trading_open, window.close):
            candidate = now.replace(
                hour=boundary.hour,
                minute=boundary.minute,
                second=boundary.second,
                microsecond=0,
            )
            if candidate > now:
                candidates.append(candidate)
    if not candidates:
        return None
    return min(candidates).isoformat(timespec="seconds")


def build_domestic_market_hours_status(now: datetime | None = None) -> dict[str, Any]:
    """Build a research-safe view of the KRX/NXT post-2026-09-14 schedule.

    This intentionally treats only Saturday and Sunday as known non-business
    days.  Korean exchange holidays and emergency halts require an authoritative
    calendar/feed and are surfaced as an explicit limitation rather than guessed.
    """
    current = _coerce_korea_datetime(now)
    effective = current.date() >= SCHEDULE_EFFECTIVE_DATE
    weekday = current.weekday() < 5
    accepting: list[DomesticMarketWindow] = []
    trading: list[DomesticMarketWindow] = []
    if effective and weekday:
        accepting, trading = _active_windows(current)

    if not effective:
        state = "pre_effective"
    elif not weekday:
        state = "non_business_day"
    elif trading:
        state = "open"
    elif accepting:
        state = "order_acceptance"
    else:
        state = "closed"

    active = trading or accepting
    return {
        "module": "domestic_market_hours",
        "schedule_version": SCHEDULE_VERSION,
        "effective_date": SCHEDULE_EFFECTIVE_DATE.isoformat(),
        "as_of": current.isoformat(timespec="seconds"),
        "timezone": "Asia/Seoul",
        "is_weekday": weekday,
        "calendar_basis": "weekday_only",
        "holiday_status": "not_verified",
        "market_state": state,
        "market_state_label": _state_label(state),
        "current_sessions": [window.as_dict() for window in active],
        "current_trading_sessions": [window.as_dict() for window in trading],
        "next_transition_at": _next_transition(current) if effective and weekday else None,
        "venues": {
            "KRX": [window.as_dict() for window in CURRENT_WINDOWS if window.venue == "KRX"],
            "NXT": [window.as_dict() for window in CURRENT_WINDOWS if window.venue == "NXT"],
        },
        "operational_note": (
            "이 정보는 리서치·자동화 시각 안내용입니다. 실제 주문 가능 여부는 "
            "증권사, 종목, 주문유형, 거래정지, 휴장일 기준으로 다시 확인해야 합니다."
        ),
        "sources": [dict(source) for source in SOURCES],
    }
