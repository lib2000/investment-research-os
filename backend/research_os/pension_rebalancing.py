"""Safe, local-first pension account rebalancing review workflow.

This module intentionally stops at allocation analysis, recurring-review
planning, and human-review packets.  It never calls a broker or order API.
Personal targets and account values live in the ignored ``research_vault``
state store, not in Git.
"""

from __future__ import annotations

import calendar
import math
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from research_os.portfolio_store import portfolio_store_key, read_portfolio_store
from research_os.settings import Settings
from research_os.state_store import (
    current_storage_datetime,
    current_storage_timestamp,
    read_json_store,
    user_state_dir,
    write_json_store,
)


PENSION_REBALANCING_SCHEMA_VERSION = 1
PENSION_REBALANCING_CONFIG_FILE = "pension_rebalancing_config.json"
PENSION_REBALANCING_STATE_FILE = "pension_rebalancing_state.json"
PENSION_REBALANCING_REPORT_DIRECTORY = "pension_rebalancing"
DEFAULT_REBALANCE_THRESHOLD_PCT_POINTS = 5.0
SEOUL_TIMEZONE = "Asia/Seoul"

ASSET_CLASS_LABELS = {
    "domestic_equity": "국내 주식",
    "global_equity": "해외 주식",
    "equity": "주식",
    "bond": "채권",
    "cash": "현금·예수금",
    "cash_equivalent": "현금성 자산",
    "alternative": "대체자산",
    "unclassified": "분류 확인 필요",
}


def default_pension_rebalancing_config() -> dict[str, Any]:
    """Return a deliberately inactive configuration with no financial target."""
    return {
        "schema_version": PENSION_REBALANCING_SCHEMA_VERSION,
        "status": "draft_needs_confirmation",
        "portfolio_name": "",
        "base_currency": "KRW",
        "target_allocation": {},
        "asset_class_by_ticker": {},
        "rebalance_threshold_pct_points": DEFAULT_REBALANCE_THRESHOLD_PCT_POINTS,
        "execution_mode": "manual_review_only",
        "monthly_schedule": {
            "enabled": True,
            "day": 1,
            "time": "19:00",
        },
        "quarterly_schedule": {
            "enabled": True,
            "months": [1, 4, 7, 10],
            "day": 1,
            "time": "19:00",
        },
        "google_calendar": {
            "enabled": False,
            "calendar_id": "primary",
            "reminder_minutes": [1440, 60],
        },
        "google_drive": {
            "enabled": False,
            "folder_id": "",
            "folder_url": "",
            "sync_directory": "",
        },
    }


def pension_rebalancing_config_path(settings: Settings) -> Path:
    return user_state_dir(settings) / PENSION_REBALANCING_CONFIG_FILE


def pension_rebalancing_state_path(settings: Settings) -> Path:
    return user_state_dir(settings) / PENSION_REBALANCING_STATE_FILE


def pension_rebalancing_report_dir(settings: Settings) -> Path:
    return user_state_dir(settings) / PENSION_REBALANCING_REPORT_DIRECTORY


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalized_asset_class(value: Any) -> str:
    raw = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "주식": "equity",
        "국내주식": "domestic_equity",
        "국내_주식": "domestic_equity",
        "해외주식": "global_equity",
        "해외_주식": "global_equity",
        "채권": "bond",
        "현금": "cash",
        "예수금": "cash",
        "현금성": "cash_equivalent",
        "현금성자산": "cash_equivalent",
        "대체자산": "alternative",
    }
    return aliases.get(raw, raw or "unclassified")


def _merge_config(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = default_pension_rebalancing_config()
    merged = {**defaults, **_as_mapping(payload)}
    for key in ("monthly_schedule", "quarterly_schedule", "google_calendar", "google_drive"):
        merged[key] = {**_as_mapping(defaults[key]), **_as_mapping(payload.get(key))}
    merged["target_allocation"] = _as_mapping(payload.get("target_allocation"))
    merged["asset_class_by_ticker"] = _as_mapping(payload.get("asset_class_by_ticker"))
    # A config file must never enable unattended execution, even if edited by
    # hand.  Live broker routing has a separate explicit-approval boundary.
    merged["execution_mode"] = "manual_review_only"
    return merged


def load_pension_rebalancing_config(settings: Settings) -> dict[str, Any]:
    payload = read_json_store(pension_rebalancing_config_path(settings), {})
    return _merge_config(payload)


def initialize_pension_rebalancing_config(settings: Settings) -> dict[str, Any]:
    """Create the local draft config once, without inventing a target mix."""
    path = pension_rebalancing_config_path(settings)
    if path.exists():
        return load_pension_rebalancing_config(settings)
    payload = default_pension_rebalancing_config()
    write_json_store(path, payload)
    return payload


def validate_pension_rebalancing_config(config: dict[str, Any]) -> dict[str, Any]:
    target = _as_mapping(config.get("target_allocation"))
    normalized_target: dict[str, float] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for raw_asset_class, raw_weight in target.items():
        asset_class = _normalized_asset_class(raw_asset_class)
        weight = _finite_number(raw_weight)
        if weight is None or weight < 0 or weight > 1:
            errors.append(f"목표 비중 '{raw_asset_class}'은 0~1 사이 숫자로 입력하세요.")
            continue
        if asset_class in normalized_target:
            errors.append(f"목표 자산군 '{asset_class}'이 중복되었습니다.")
            continue
        normalized_target[asset_class] = weight

    if not normalized_target:
        errors.append("목표 자산배분이 비어 있습니다. 초안 예시를 검토해 직접 확정하세요.")

    total_target_weight = sum(normalized_target.values())
    if normalized_target and not math.isclose(total_target_weight, 1.0, abs_tol=0.001):
        errors.append(f"목표 비중 합계는 100%여야 합니다. 현재 {total_target_weight * 100:.2f}%입니다.")

    threshold = _finite_number(config.get("rebalance_threshold_pct_points"))
    if threshold is None or threshold <= 0 or threshold > 100:
        errors.append("리밸런싱 허용 괴리 기준은 0 초과 100 이하의 %p 값이어야 합니다.")
        threshold = DEFAULT_REBALANCE_THRESHOLD_PCT_POINTS

    portfolio_name = str(config.get("portfolio_name") or "").strip()
    if not portfolio_name:
        warnings.append("연결할 저장 포트폴리오 이름이 없습니다. 보유자산을 먼저 저장하거나 config에 연결하세요.")

    status = str(config.get("status") or "draft_needs_confirmation").strip()
    if status not in {"draft_needs_confirmation", "active"}:
        warnings.append("알 수 없는 설정 상태는 검토 필요 초안으로 처리합니다.")
        status = "draft_needs_confirmation"

    if status != "active":
        warnings.append("목표 배분은 아직 검토 필요 초안입니다. 자동 매수·매도는 항상 차단됩니다.")

    if str(config.get("execution_mode") or "") != "manual_review_only":
        warnings.append("실행 모드는 수동 검토 전용으로 강제되었습니다.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "target_allocation": normalized_target,
        "target_weight_total": total_target_weight,
        "portfolio_name": portfolio_name,
        "status": status,
        "rebalance_threshold_pct_points": threshold,
        "execution_mode": "manual_review_only",
    }


def prepare_pension_rebalancing_config(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize a user-entered config and retain only safe execution mode."""
    config = _merge_config(payload)
    config["schema_version"] = PENSION_REBALANCING_SCHEMA_VERSION
    config["portfolio_name"] = str(config.get("portfolio_name") or "").strip()
    config["base_currency"] = str(config.get("base_currency") or "KRW").strip().upper() or "KRW"
    config["status"] = str(config.get("status") or "draft_needs_confirmation").strip()
    config["target_allocation"] = {
        _normalized_asset_class(asset_class): weight
        for asset_class, weight in _as_mapping(config.get("target_allocation")).items()
    }
    config["asset_class_by_ticker"] = {
        str(ticker).strip().upper(): _normalized_asset_class(asset_class)
        for ticker, asset_class in _as_mapping(config.get("asset_class_by_ticker")).items()
        if str(ticker).strip()
    }
    config["execution_mode"] = "manual_review_only"
    validation = validate_pension_rebalancing_config(config)
    config["status"] = validation["status"]
    return config, validation


def save_pension_rebalancing_config(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    config, validation = prepare_pension_rebalancing_config(payload)
    write_json_store(pension_rebalancing_config_path(settings), config)
    return {
        "status": "saved" if validation["valid"] else "saved_needs_configuration",
        "config": config,
        "validation": validation,
        "storage_path": str(pension_rebalancing_config_path(settings)),
        "execution_mode": "manual_review_only",
        "broker_order_endpoint_called": False,
    }


def _holding_value(holding: dict[str, Any]) -> float | None:
    value = _finite_number(holding.get("market_value"))
    if value is not None and value >= 0:
        return value
    quantity = _finite_number(holding.get("quantity"))
    price = _finite_number(holding.get("current_price"))
    if quantity is not None and price is not None and quantity >= 0 and price >= 0:
        return quantity * price
    return None


def _holding_asset_class(holding: dict[str, Any], config: dict[str, Any]) -> str:
    ticker = str(holding.get("ticker") or "").strip().upper()
    mapping = _as_mapping(config.get("asset_class_by_ticker"))
    if ticker and ticker in mapping:
        return _normalized_asset_class(mapping[ticker])
    name = str(holding.get("name") or "").strip().lower()
    if ticker in {"CASH", "KRW", "USD"} or any(term in name for term in ("현금", "예수금", "cash")):
        return "cash"
    return "unclassified"


def _portfolio_payload_for_config(settings: Settings, config: dict[str, Any]) -> dict[str, Any] | None:
    portfolio_name = str(config.get("portfolio_name") or "").strip()
    if not portfolio_name:
        return None
    store = read_portfolio_store(settings)
    portfolios = _as_mapping(store.get("portfolios"))
    payload = portfolios.get(portfolio_store_key(portfolio_name))
    if isinstance(payload, dict):
        return payload
    folded = portfolio_name.casefold()
    for candidate in portfolios.values():
        if isinstance(candidate, dict) and str(candidate.get("portfolio_name") or "").casefold() == folded:
            return candidate
    return None


def _review_status(deviation_pct_points: float, threshold_pct_points: float) -> tuple[str, str]:
    if deviation_pct_points >= threshold_pct_points:
        return "reduction_review", "현재 비중이 목표보다 높아 축소 여부를 수동 검토"
    if deviation_pct_points <= -threshold_pct_points:
        return "increase_review", "현재 비중이 목표보다 낮아 추가 편입 여부를 수동 검토"
    return "within_band", "허용 괴리 범위 안"


def build_pension_rebalancing_snapshot(
    config: dict[str, Any],
    *,
    portfolio: dict[str, Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Calculate current allocation gaps without producing executable orders."""
    validation = validate_pension_rebalancing_config(config)
    checked_at = checked_at or current_storage_timestamp()
    portfolio = portfolio or {}
    holdings = [item for item in _as_list(portfolio.get("holdings")) if isinstance(item, dict)]
    portfolio_name = str(portfolio.get("portfolio_name") or validation["portfolio_name"] or "연금 계좌").strip()
    warnings = list(validation["warnings"])

    if validation["portfolio_name"] and not portfolio:
        warnings.append(f"저장 포트폴리오 '{validation['portfolio_name']}'을 찾지 못했습니다.")

    classified: dict[str, float] = {}
    skipped_holdings: list[dict[str, str]] = []
    for holding in holdings:
        value = _holding_value(holding)
        ticker = str(holding.get("ticker") or "").strip().upper()
        name = str(holding.get("name") or ticker or "이름 미확인")
        if value is None:
            skipped_holdings.append({"ticker": ticker, "name": name, "reason": "평가금액 또는 수량·현재가가 없습니다."})
            continue
        asset_class = _holding_asset_class(holding, config)
        classified[asset_class] = classified.get(asset_class, 0.0) + value

    reported_value = _finite_number(portfolio.get("portfolio_value"))
    holdings_value = sum(classified.values())
    total_value = reported_value if reported_value is not None and reported_value > 0 else holdings_value
    if reported_value is not None and reported_value > holdings_value + 1 and holdings_value >= 0:
        difference = reported_value - holdings_value
        classified["unclassified"] = classified.get("unclassified", 0.0) + difference
        warnings.append("저장 총액과 보유 평가금액 합계의 차이는 '분류 확인 필요'로 표시했습니다.")

    if skipped_holdings:
        warnings.append(f"평가금액을 계산할 수 없는 보유 항목 {len(skipped_holdings)}개는 비중 계산에서 제외했습니다.")

    allocation_rows: list[dict[str, Any]] = []
    target = validation["target_allocation"]
    relevant_asset_classes = list(target)
    for asset_class in sorted(classified):
        if asset_class not in relevant_asset_classes:
            relevant_asset_classes.append(asset_class)

    if total_value > 0 and validation["valid"]:
        for asset_class in relevant_asset_classes:
            current_value = classified.get(asset_class, 0.0)
            target_weight = target.get(asset_class, 0.0)
            current_weight = current_value / total_value
            deviation_pct_points = (current_weight - target_weight) * 100
            target_value = total_value * target_weight
            status, review_message = _review_status(
                deviation_pct_points,
                validation["rebalance_threshold_pct_points"],
            )
            allocation_rows.append(
                {
                    "asset_class": asset_class,
                    "asset_class_label": ASSET_CLASS_LABELS.get(asset_class, asset_class),
                    "current_value": round(current_value, 2),
                    "current_weight": round(current_weight, 8),
                    "target_value": round(target_value, 2),
                    "target_weight": round(target_weight, 8),
                    "deviation_pct_points": round(deviation_pct_points, 4),
                    "difference_to_target_value": round(target_value - current_value, 2),
                    "review_status": status,
                    "review_message": review_message,
                }
            )
    elif total_value <= 0:
        warnings.append("유효한 총 평가금액이 없어 현재 비중을 계산하지 못했습니다.")

    allocation_rows.sort(key=lambda item: abs(float(item["deviation_pct_points"])), reverse=True)
    review_rows = [row for row in allocation_rows if row["review_status"] != "within_band"]

    if not validation["valid"]:
        status = "needs_configuration"
    elif not portfolio:
        status = "needs_portfolio_import"
    elif total_value <= 0:
        status = "needs_holdings_value"
    elif validation["status"] != "active":
        status = "draft_needs_confirmation"
    elif review_rows:
        status = "review_required"
    else:
        status = "within_rebalance_band"

    manual_review_packet = {
        "mode": "manual_review_only",
        "broker_order_endpoint_called": False,
        "automatic_order_submission": False,
        "candidate_asset_class_adjustments": [
            {
                "asset_class": row["asset_class"],
                "asset_class_label": row["asset_class_label"],
                "difference_to_target_value": row["difference_to_target_value"],
                "review_status": row["review_status"],
            }
            for row in review_rows
        ],
        "required_human_checks": [
            "목표 자산배분이 연금계좌의 위험등급·대출/담보 조건과 일치하는지 확인",
            "펀드·ETF의 매수 가능 여부, 환매/매도 수수료와 거래 가능일 확인",
            "현금 입금·결제 대기 금액과 세금·연금계좌 제약을 반영했는지 확인",
            "검토 결과를 앱 또는 증권사 화면에서 수동 실행하고 체결 내역만 다시 반영",
        ],
    }

    return {
        "status": status,
        "module": "pension_rebalancing",
        "checked_at": checked_at,
        "portfolio_name": portfolio_name,
        "base_currency": str(config.get("base_currency") or "KRW").upper(),
        "portfolio_value": round(total_value, 2),
        "holdings_value": round(holdings_value, 2),
        "holding_count": len(holdings),
        "classified_holding_count": len(holdings) - len(skipped_holdings),
        "skipped_holdings": skipped_holdings,
        "rebalance_threshold_pct_points": validation["rebalance_threshold_pct_points"],
        "target_status": validation["status"],
        "target_weight_total": round(validation["target_weight_total"], 8),
        "allocation_rows": allocation_rows,
        "review_required_count": len(review_rows),
        "validation": validation,
        "warnings": warnings,
        "manual_review_packet": manual_review_packet,
    }


def _schedule_time(value: Any) -> tuple[int, int]:
    raw = str(value or "19:00").strip()
    try:
        hours, minutes = raw.split(":", 1)
        hour = int(hours)
        minute = int(minutes)
    except (TypeError, ValueError):
        return 19, 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour, minute
    return 19, 0


def _valid_day(value: Any) -> int:
    try:
        day = int(value)
    except (TypeError, ValueError):
        return 1
    return min(max(day, 1), 28)


def _iter_months(start: date, months_ahead: int) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    for offset in range(max(1, months_ahead)):
        index = (start.year * 12 + (start.month - 1)) + offset
        months.append((index // 12, index % 12 + 1))
    return months


def build_pension_rebalancing_calendar_plan(
    config: dict[str, Any],
    *,
    start_date: date | None = None,
    months_ahead: int = 15,
) -> dict[str, Any]:
    """Create idempotent monthly/quarterly Calendar event plans and ICS data."""
    start_date = start_date or current_storage_datetime().date()
    events: list[dict[str, Any]] = []
    for kind, schedule, title in (
        ("monthly", _as_mapping(config.get("monthly_schedule")), "월간"),
        ("quarterly", _as_mapping(config.get("quarterly_schedule")), "분기"),
    ):
        if not bool(schedule.get("enabled", True)):
            continue
        hour, minute = _schedule_time(schedule.get("time"))
        day = _valid_day(schedule.get("day"))
        quarterly_months = {
            int(item)
            for item in _as_list(schedule.get("months"))
            if str(item).strip().isdigit() and 1 <= int(item) <= 12
        }
        for year, month in _iter_months(start_date.replace(day=1), months_ahead):
            if kind == "quarterly" and month not in quarterly_months:
                continue
            event_day = min(day, calendar.monthrange(year, month)[1])
            event_date = date(year, month, event_day)
            if event_date < start_date:
                continue
            start_datetime = datetime(year, month, event_day, hour, minute)
            end_datetime = start_datetime + timedelta(minutes=30)
            event_id = f"pension-rebalancing-{kind}-{event_date.isoformat()}"
            events.append(
                {
                    "sync_key": event_id,
                    "event_type": kind,
                    "summary": f"연금 리밸런싱 체크 · {title}",
                    "description": (
                        "목표 자산배분과 현재 비중의 괴리를 확인합니다. "
                        "이 일정은 자동 주문을 실행하지 않으며, 결과는 수동 검토용입니다."
                    ),
                    "start": start_datetime.isoformat(timespec="seconds"),
                    "end": end_datetime.isoformat(timespec="seconds"),
                    "time_zone": SEOUL_TIMEZONE,
                    "reminder_minutes": [
                        int(value)
                        for value in _as_list(_as_mapping(config.get("google_calendar")).get("reminder_minutes"))
                        if _finite_number(value) is not None and int(float(value)) >= 0
                    ]
                    or [1440, 60],
                }
            )
    events.sort(key=lambda item: (item["start"], item["event_type"]))
    calendar_config = _as_mapping(config.get("google_calendar"))
    if calendar_config.get("enabled"):
        sync_status = "pending_calendar_authorization"
        sync_message = "Google Calendar 권한이 확인되면 sync_key 기준으로 생성/갱신할 수 있습니다."
    else:
        sync_status = "calendar_sync_not_enabled"
        sync_message = "Google Calendar 동기화는 config에서 명시적으로 활성화한 뒤 권한을 확인해야 합니다."
    return {
        "status": "ready",
        "calendar_id": str(calendar_config.get("calendar_id") or "primary"),
        "time_zone": SEOUL_TIMEZONE,
        "events": events,
        "sync_status": sync_status,
        "sync_message": sync_message,
    }


def _ics_escape(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def render_pension_rebalancing_ics(calendar_plan: dict[str, Any]) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Investment Research OS//Pension Rebalancing//KO"]
    for event in _as_list(calendar_plan.get("events")):
        start = str(event.get("start") or "").replace("-", "").replace(":", "")
        end = str(event.get("end") or "").replace("-", "").replace(":", "")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_ics_escape(event.get('sync_key'))}@investment-research-os.local",
                f"DTSTAMP:{now_utc}",
                f"DTSTART;TZID={SEOUL_TIMEZONE}:{start}",
                f"DTEND;TZID={SEOUL_TIMEZONE}:{end}",
                f"SUMMARY:{_ics_escape(event.get('summary'))}",
                f"DESCRIPTION:{_ics_escape(event.get('description'))}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _markdown_money(value: Any, currency: str) -> str:
    amount = _finite_number(value)
    if amount is None:
        return "확인 필요"
    return f"{amount:,.0f} {currency}"


def render_pension_rebalancing_markdown(snapshot: dict[str, Any], calendar_plan: dict[str, Any]) -> str:
    currency = str(snapshot.get("base_currency") or "KRW")
    lines = [
        "# 연금계좌 정기 리밸런싱 검토",
        "",
        f"- 점검 시각: {snapshot.get('checked_at') or '확인 필요'}",
        f"- 연결 포트폴리오: {snapshot.get('portfolio_name') or '확인 필요'}",
        f"- 상태: {snapshot.get('status') or '확인 필요'}",
        "- 실행 원칙: 자동 주문 없음 · 앱/증권사 화면에서 수동 검토 후 실행",
        "",
        "## 자산배분 괴리",
        "",
        "| 자산군 | 현재 비중 | 목표 비중 | 괴리(%p) | 목표 대비 금액 | 검토 상태 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    rows = _as_list(snapshot.get("allocation_rows"))
    if rows:
        for row in rows:
            lines.append(
                "| {label} | {current:.2%} | {target:.2%} | {gap:+.2f} | {difference} | {status} |".format(
                    label=str(row.get("asset_class_label") or row.get("asset_class") or "확인 필요"),
                    current=float(row.get("current_weight") or 0),
                    target=float(row.get("target_weight") or 0),
                    gap=float(row.get("deviation_pct_points") or 0),
                    difference=_markdown_money(row.get("difference_to_target_value"), currency),
                    status=str(row.get("review_status") or "확인 필요"),
                )
            )
    else:
        lines.append("| 확인 필요 | - | - | - | - | 목표배분 또는 보유자산 설정 필요 |");

    lines.extend(["", "## 수동 검토 게이트", ""])
    for item in _as_list(_as_mapping(snapshot.get("manual_review_packet")).get("required_human_checks")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Google Calendar/Drive 연동 상태",
            "",
            f"- Calendar: {calendar_plan.get('sync_status') or '확인 필요'}",
            f"- 예정 이벤트: {len(_as_list(calendar_plan.get('events')))}개",
            "- Drive: 로컬 Google Drive 동기화 폴더를 config에 지정한 경우에만 자동 복사합니다.",
            "",
            "## 경고 및 확인 필요",
            "",
        ]
    )
    warnings = _as_list(snapshot.get("warnings")) + _as_list(_as_mapping(snapshot.get("validation")).get("errors"))
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- 추가 경고 없음")
    return "\n".join(lines) + "\n"


def _drive_sync_status(config: dict[str, Any], report_paths: list[Path]) -> dict[str, Any]:
    drive_config = _as_mapping(config.get("google_drive"))
    sync_directory = str(drive_config.get("sync_directory") or "").strip()
    folder_id = str(drive_config.get("folder_id") or "").strip()
    if not sync_directory:
        return {
            "status": "sync_directory_not_configured",
            "folder_id": folder_id or None,
            "copied_files": [],
            "message": "Google Drive Desktop 동기화 폴더 경로를 설정하면 보고서를 자동 복사합니다.",
        }
    destination = Path(sync_directory).expanduser()
    if "onedrive" in str(destination).casefold():
        return {
            "status": "blocked_onedrive_path",
            "folder_id": folder_id or None,
            "copied_files": [],
            "message": "OneDrive 경로는 개인 리서치 리포트 자동 복사 대상으로 사용하지 않습니다.",
        }
    if not destination.exists() or not destination.is_dir():
        return {
            "status": "sync_directory_missing",
            "folder_id": folder_id or None,
            "copied_files": [],
            "message": "설정한 Google Drive 동기화 폴더를 찾지 못했습니다.",
        }
    copied: list[str] = []
    for report_path in report_paths:
        target = destination / report_path.name
        shutil.copy2(report_path, target)
        copied.append(str(target))
    return {
        "status": "copied_to_google_drive_sync_directory",
        "folder_id": folder_id or None,
        "copied_files": copied,
        "message": "Google Drive Desktop 동기화 폴더에 보고서를 복사했습니다.",
    }


def read_pension_rebalancing_state(settings: Settings) -> dict[str, Any]:
    return read_json_store(
        pension_rebalancing_state_path(settings),
        {"last_completed_periods": {}, "last_run_at": None},
    )


def due_pension_rebalancing_periods(
    config: dict[str, Any],
    state: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    """Return missed/current monthly and quarterly periods for a daily task."""
    now = now or current_storage_datetime()
    completed = _as_mapping(state.get("last_completed_periods"))
    due: list[dict[str, str]] = []
    monthly = _as_mapping(config.get("monthly_schedule"))
    monthly_key = f"{now.year:04d}-{now.month:02d}"
    if bool(monthly.get("enabled", True)) and now.day >= _valid_day(monthly.get("day")):
        if completed.get("monthly") != monthly_key:
            due.append({"event_type": "monthly", "period": monthly_key})

    quarterly = _as_mapping(config.get("quarterly_schedule"))
    months = {
        int(item)
        for item in _as_list(quarterly.get("months"))
        if str(item).strip().isdigit() and 1 <= int(item) <= 12
    }
    quarter = ((now.month - 1) // 3) + 1
    quarterly_key = f"{now.year:04d}-Q{quarter}"
    if (
        bool(quarterly.get("enabled", True))
        and now.month in months
        and now.day >= _valid_day(quarterly.get("day"))
        and completed.get("quarterly") != quarterly_key
    ):
        due.append({"event_type": "quarterly", "period": quarterly_key})
    return due


def write_pension_rebalancing_run(
    settings: Settings,
    *,
    due_periods: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    config = load_pension_rebalancing_config(settings)
    portfolio = _portfolio_payload_for_config(settings, config)
    snapshot = build_pension_rebalancing_snapshot(config, portfolio=portfolio)
    calendar_plan = build_pension_rebalancing_calendar_plan(config)
    report_directory = pension_rebalancing_report_dir(settings)
    report_directory.mkdir(parents=True, exist_ok=True)
    stamp = current_storage_datetime().strftime("%Y-%m-%d")
    json_path = report_directory / f"{stamp}-rebalancing-review.json"
    markdown_path = report_directory / f"{stamp}-rebalancing-review.md"
    ics_path = report_directory / "pension-rebalancing-calendar.ics"
    payload = {
        "snapshot": snapshot,
        "calendar_plan": calendar_plan,
        "due_periods": due_periods or [],
        "generated_at": current_storage_timestamp(),
        "execution_mode": "manual_review_only",
        "broker_order_endpoint_called": False,
    }
    write_json_store(json_path, payload)
    markdown_path.write_text(render_pension_rebalancing_markdown(snapshot, calendar_plan), encoding="utf-8")
    ics_path.write_text(render_pension_rebalancing_ics(calendar_plan), encoding="utf-8", newline="\r\n")
    drive_status = _drive_sync_status(config, [json_path, markdown_path, ics_path])

    state = read_pension_rebalancing_state(settings)
    completed = _as_mapping(state.get("last_completed_periods"))
    if snapshot["status"] in {"review_required", "within_rebalance_band"}:
        for due in due_periods or []:
            event_type = str(due.get("event_type") or "")
            period = str(due.get("period") or "")
            if event_type and period:
                completed[event_type] = period
    state.update(
        {
            "last_run_at": current_storage_timestamp(),
            "last_status": snapshot["status"],
            "last_completed_periods": completed,
            "last_report_paths": [str(json_path), str(markdown_path), str(ics_path)],
            "last_drive_status": drive_status,
        }
    )
    write_json_store(pension_rebalancing_state_path(settings), state)
    return {
        **payload,
        "drive_delivery": drive_status,
        "state_path": str(pension_rebalancing_state_path(settings)),
        "report_paths": [str(json_path), str(markdown_path), str(ics_path)],
    }


def build_pension_rebalancing_status(settings: Settings, *, months_ahead: int = 15) -> dict[str, Any]:
    config = load_pension_rebalancing_config(settings)
    portfolio = _portfolio_payload_for_config(settings, config)
    snapshot = build_pension_rebalancing_snapshot(config, portfolio=portfolio)
    calendar_plan = build_pension_rebalancing_calendar_plan(config, months_ahead=months_ahead)
    state = read_pension_rebalancing_state(settings)
    return {
        **snapshot,
        "config_path": str(pension_rebalancing_config_path(settings)),
        "calendar_plan": calendar_plan,
        "state": state,
        "execution_mode": "manual_review_only",
        "broker_order_endpoint_called": False,
    }
