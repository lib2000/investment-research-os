"""Provider usage quota helpers for external data APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading


_PROVIDER_USAGE_LOCK = threading.Lock()


def resolve_backend_relative_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[1] / path).resolve()


def consume_external_provider_quota(
    *,
    provider_name: str,
    usage_file: str,
    daily_limit: int,
    monthly_limit: int,
    units: int = 1,
    unit_label: str = "requests",
) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    today_key = now.date().isoformat()
    month_key = f"{now.year:04d}-{now.month:02d}"
    path = resolve_backend_relative_path(usage_file)
    with _PROVIDER_USAGE_LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        usage = payload.get(provider_name)
        if not isinstance(usage, dict):
            usage = {}
        if usage.get("day") != today_key:
            usage["day"] = today_key
            usage["day_count"] = 0
        if usage.get("month") != month_key:
            usage["month"] = month_key
            usage["month_count"] = 0
        day_count = int(usage.get("day_count") or 0)
        month_count = int(usage.get("month_count") or 0)
        if daily_limit >= 0 and day_count + units > daily_limit:
            return (
                False,
                f"{provider_name} 무료 한도 보호: 오늘 {day_count}/{daily_limit} {unit_label}를 이미 사용해 추가 호출을 건너뜁니다.",
            )
        if monthly_limit >= 0 and month_count + units > monthly_limit:
            return (
                False,
                f"{provider_name} 무료 한도 보호: 이번 달 {month_count}/{monthly_limit} {unit_label}를 이미 사용해 추가 호출을 건너뜁니다.",
            )
        usage["day_count"] = day_count + units
        usage["month_count"] = month_count + units
        usage["last_used_at"] = now.isoformat()
        payload[provider_name] = usage
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return (
        True,
        f"{provider_name} 사용량 기록: 오늘 {day_count + units}/{daily_limit}, 이번 달 {month_count + units}/{monthly_limit} {unit_label}.",
    )
