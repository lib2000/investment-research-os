"""Post-run health check and optional Telegram alert for the 07:00 report alert."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
TOOLS_DIR = PROJECT_ROOT / "tools"
for candidate in (BACKEND_DIR, TOOLS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from check_portfolio_report_alert import (  # noqa: E402
    default_bot_token,
    default_chat_id,
    default_target_bot,
    read_json,
    redacted_for_output,
    write_json,
)
from check_portfolio_report_alert_task_status import (  # noqa: E402
    DEFAULT_STATE_FILE,
    DEFAULT_TASK_NAME,
    evaluate_task_status,
    read_scheduled_task,
)
from research_os.telegram_brief_delivery import execute_telegram_delivery  # noqa: E402


DESIGN_NAME = "portfolio_report_alert_postrun_v1"
DEFAULT_MONITOR_STATE = PROJECT_ROOT / "research_vault" / "_system" / "portfolio_report_alert_postrun_state.json"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def fingerprint(status: dict[str, Any]) -> str:
    task = status.get("task") if isinstance(status.get("task"), dict) else {}
    parts = [
        str(status.get("status")),
        "|".join(str(item) for item in status.get("errors") or []),
        str(task.get("LastRunTime")),
        str(task.get("LastTaskResult")),
        str(status.get("state_file_exists")),
    ]
    return "::".join(parts)


def build_alert_text(status: dict[str, Any]) -> str:
    task = status.get("task") if isinstance(status.get("task"), dict) else {}
    lines = [
        "보유 종목 리포트 알림 사후점검 (Portfolio Report Alert Post-run Check)",
        f"상태: {status.get('status')}",
        f"작업: {task.get('TaskName') or DEFAULT_TASK_NAME}",
        f"마지막 실행: {task.get('LastRunTime')}",
        f"마지막 결과: {task.get('LastTaskResult')}",
        f"다음 실행: {task.get('NextRunTime')}",
        f"상태 파일 존재: {status.get('state_file_exists')}",
        f"상태 파일 경과시간: {status.get('state_file_age_hours')}",
    ]
    errors = [str(item) for item in status.get("errors") or []]
    warnings = [str(item) for item in status.get("warnings") or []]
    if errors:
        lines.append("오류:")
        lines.extend(f"- {item}" for item in errors[:8])
    if warnings:
        lines.append("경고:")
        lines.extend(f"- {item}" for item in warnings[:8])
    return "\n".join(lines)


def build_payload(status: dict[str, Any], *, chat_id: str, target_bot: str, notify_ok: bool) -> dict[str, Any]:
    should_send = status.get("status") != "ok" or notify_ok
    text = build_alert_text(status) if should_send else ""
    messages = []
    if text:
        messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
                "priority": "must_keep",
                "category": "portfolio_report_alert_postrun",
            }
        )
    return {
        "design": DESIGN_NAME,
        "message_type": "portfolio_report_alert_postrun",
        "target_bot": target_bot,
        "should_send": should_send,
        "chat_id_configured": bool(chat_id),
        "message_count": len(messages),
        "messages": messages,
        "text": text,
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    state_file = args.state_file if args.state_file.is_absolute() else PROJECT_ROOT / args.state_file
    monitor_state_file = args.monitor_state_file if args.monitor_state_file.is_absolute() else PROJECT_ROOT / args.monitor_state_file
    status = evaluate_task_status(
        read_scheduled_task(args.task_name),
        state_file=state_file,
        max_state_age_hours=args.max_state_age_hours,
        require_state_fresh=False,
        expected_time="07:00",
    )
    if not status.get("never_run"):
        if not status.get("state_file_exists"):
            status["errors"].append("portfolio report alert state file is missing")
        elif (
            status.get("state_file_age_hours") is not None
            and float(status.get("state_file_age_hours") or 0) > float(args.max_state_age_hours)
        ):
            status["errors"].append(
                f"portfolio report alert state file is stale: {float(status.get('state_file_age_hours') or 0):.1f}h"
            )
        status["status"] = "error" if status.get("errors") else "ok"
    bot_token, bot_token_source = default_bot_token()
    chat_id, chat_id_source = default_chat_id()
    target_bot, target_bot_source = default_target_bot()
    effective_chat_id = args.chat_id if args.chat_id is not None else chat_id
    enabled = bool(args.enabled or env_bool("TELEGRAM_REPORT_ALERT_POSTRUN_ENABLED", False))
    dry_run = True
    if args.submit:
        dry_run = False
    elif not env_bool("TELEGRAM_REPORT_ALERT_POSTRUN_DRY_RUN", True):
        dry_run = False

    monitor_state = read_json(monitor_state_file, {"sent_fingerprints": []})
    if not isinstance(monitor_state, dict):
        raise SystemExit(f"monitor state JSON object expected: {monitor_state_file}")
    current_fingerprint = fingerprint(status)
    already_sent = current_fingerprint in set(str(item) for item in monitor_state.get("sent_fingerprints") or [])
    payload = build_payload(status, chat_id=effective_chat_id, target_bot=target_bot, notify_ok=args.notify_ok)
    if already_sent and not args.repeat:
        payload = {**payload, "should_send": False, "message_count": 0, "messages": [], "text": ""}

    delivery = execute_telegram_delivery(
        payload,
        state={"sent_messages": monitor_state.get("sent_messages") or []},
        enabled=enabled,
        dry_run=dry_run,
        cleanup_enabled=False,
        bot_token=bot_token,
        api_base_url=args.api_base_url,
        timeout_seconds=args.timeout_seconds,
    )
    sent = bool(delivery.get("applied_send_count"))
    sent_fingerprints = list(dict.fromkeys(str(item) for item in monitor_state.get("sent_fingerprints") or [] if item))
    if sent:
        sent_fingerprints.append(current_fingerprint)
    next_state = {
        **monitor_state,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "last_status": status.get("status"),
        "last_fingerprint": current_fingerprint,
        "last_should_send": payload.get("should_send"),
        "last_sent": sent,
        "sent_fingerprints": list(dict.fromkeys(sent_fingerprints))[-50:],
    }
    if delivery.get("updated_state"):
        next_state["sent_messages"] = delivery["updated_state"].get("sent_messages") or []
    result = {
        "design": DESIGN_NAME,
        "status": status.get("status"),
        "errors": status.get("errors") or [],
        "warnings": status.get("warnings") or [],
        "task_status": status,
        "enabled": enabled,
        "dry_run": dry_run,
        "bot_token_configured": bool(bot_token),
        "bot_token_source": bot_token_source if bot_token else "none",
        "chat_id_configured": bool(effective_chat_id),
        "chat_id_source": "cli" if args.chat_id is not None and args.chat_id else chat_id_source,
        "target_bot": target_bot,
        "target_bot_source": target_bot_source,
        "already_sent": already_sent,
        "fingerprint": current_fingerprint,
        "payload": redacted_for_output(payload),
        "delivery": redacted_for_output({key: value for key, value in delivery.items() if key != "updated_state"}),
        "monitor_state_file": str(monitor_state_file),
        "updated_state": redacted_for_output(next_state),
    }
    if args.write_state:
        write_json(monitor_state_file, next_state)
        result["state_written"] = True
    else:
        result["state_written"] = False
    return result


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"[{result.get('status')}] {DESIGN_NAME}",
        f"- enabled: {result.get('enabled')}",
        f"- dry_run: {result.get('dry_run')}",
        f"- should_send: {((result.get('payload') or {}).get('should_send'))}",
        f"- applied_send_count: {((result.get('delivery') or {}).get('applied_send_count'))}",
        f"- state_written: {result.get('state_written')}",
    ]
    for warning in result.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the 07:00 portfolio report alert and notify on failures.")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--monitor-state-file", type=Path, default=DEFAULT_MONITOR_STATE)
    parser.add_argument("--max-state-age-hours", type=float, default=2)
    parser.add_argument("--chat-id", default=None)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--notify-ok", action="store_true")
    parser.add_argument("--repeat", action="store_true")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--api-base-url", default=os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org"))
    parser.add_argument("--timeout-seconds", type=float, default=float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10")))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_result(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
