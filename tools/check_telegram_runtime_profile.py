"""Summarize Telegram runtime settings without exposing secrets."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_portfolio_report_alert_task_status import (  # noqa: E402
    DEFAULT_TASK_NAME,
    telegram_env_status,
    telegram_target_bot_status,
    read_scheduled_task,
)
from research_os.settings import Settings  # noqa: E402
from research_os.telegram_authenticated_collector import masked_collection_status, sample_limited_channel_status  # noqa: E402


LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
POSTRUN_TASK_NAME = "InvestmentJournalApp OpenClaw Portfolio Report Alert Postrun"
DEFAULT_SYSTEM_DIR = PROJECT_ROOT / "research_vault" / "_system"
DEFAULT_ALERT_STATE = DEFAULT_SYSTEM_DIR / "portfolio_report_alert_state.json"
DEFAULT_POSTRUN_STATE = DEFAULT_SYSTEM_DIR / "portfolio_report_alert_postrun_state.json"
DEFAULT_BRIEF_STATE = DEFAULT_SYSTEM_DIR / "telegram_brief_delivery_state.json"


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def safe_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def iso_age_hours(value: Any, *, now: datetime) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
    return max(0.0, (now.astimezone(parsed.tzinfo) - parsed).total_seconds() / 3600)


def task_summary(task: dict[str, Any], *, expected_time: str, required_marker: str) -> dict[str, Any]:
    arguments = " ".join(str(task.get("Arguments") or "").split())
    trigger = str(task.get("Trigger") or task.get("NextRunTime") or "")
    errors: list[str] = []
    warnings: list[str] = []
    if not task.get("found"):
        errors.append(str(task.get("error") or "scheduled task not found"))
    if required_marker and required_marker not in arguments:
        errors.append(f"missing runner marker: {required_marker}")
    if expected_time and expected_time not in trigger:
        errors.append(f"expected time {expected_time} not found in trigger")
    if int(task.get("NumberOfMissedRuns") or 0):
        errors.append(f"missed runs: {task.get('NumberOfMissedRuns')}")
    last_result = int(task.get("LastTaskResult") or 0)
    if task.get("found") and last_result not in {0, 267009, 267011}:
        errors.append(f"last task result: {last_result}")
    enabled_live = "-Enabled" in arguments and "-Submit" in arguments
    if task.get("found") and not enabled_live:
        warnings.append("scheduled task is not configured for live submit")
    return {
        "status": "error" if errors else "ok",
        "found": bool(task.get("found")),
        "task_name": task.get("TaskName"),
        "expected_time": expected_time,
        "live_submit_configured": enabled_live,
        "last_run_at": task.get("LastRunTime"),
        "next_run_at": task.get("NextRunTime"),
        "last_result": task.get("LastTaskResult"),
        "errors": errors,
        "warnings": warnings,
    }


def brief_delivery_summary(state: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    plan = state.get("last_delivery_plan") if isinstance(state.get("last_delivery_plan"), dict) else {}
    return {
        "status": "ok" if plan else "ledger_missing",
        "state_updated_at": state.get("updated_at"),
        "state_age_hours": iso_age_hours(state.get("updated_at"), now=now),
        "last_enabled": plan.get("enabled"),
        "last_dry_run": plan.get("dry_run"),
        "last_live_ready": plan.get("live_ready"),
        "last_planned_send_count": plan.get("planned_send_count"),
        "last_applied_send_count": plan.get("applied_send_count"),
        "sent_message_count": safe_count(state.get("sent_messages")),
    }


def alert_state_summary(state: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    plan = state.get("last_plan") if isinstance(state.get("last_plan"), dict) else {}
    sent_messages = state.get("sent_messages") if isinstance(state.get("sent_messages"), list) else []
    latest = sent_messages[-1] if sent_messages and isinstance(sent_messages[-1], dict) else {}
    return {
        "status": "ok" if state else "state_missing",
        "state_updated_at": state.get("updated_at"),
        "state_age_hours": iso_age_hours(state.get("updated_at"), now=now),
        "target_bot": state.get("target_bot"),
        "candidate_count": plan.get("candidate_count"),
        "message_count": plan.get("message_count"),
        "delivered": plan.get("delivered"),
        "sent_report_key_count": safe_count(state.get("sent_report_keys")),
        "sent_message_count": len(sent_messages),
        "latest_message_id": latest.get("message_id"),
        "latest_sent_at": latest.get("sent_at"),
    }


def postrun_state_summary(state: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    receipt = state.get("last_receipt") if isinstance(state.get("last_receipt"), dict) else {}
    return {
        "status": "ok" if state else "state_missing",
        "state_updated_at": state.get("updated_at"),
        "state_age_hours": iso_age_hours(state.get("updated_at"), now=now),
        "last_status": state.get("last_status"),
        "last_sent": state.get("last_sent"),
        "receipt_status": receipt.get("status"),
        "receipt_delivered": receipt.get("delivered"),
        "receipt_latest_message_id": receipt.get("latest_message_id"),
        "receipt_latest_sent_at": receipt.get("latest_sent_at"),
    }


def authenticated_collector_summary(settings: Settings) -> dict[str, Any]:
    collector = masked_collection_status(settings)
    limited = sample_limited_channel_status(settings)
    return {
        "status": "ready" if collector.get("ready") else "not_ready",
        "ready": collector.get("ready"),
        "enabled": collector.get("enabled"),
        "dry_run": collector.get("dry_run"),
        "telethon_installed": (collector.get("dependency") or {}).get("telethon_installed"),
        "api_id_configured": (collector.get("secrets") or {}).get("api_id_configured"),
        "api_hash_configured": (collector.get("secrets") or {}).get("api_hash_configured"),
        "session_file_exists": (collector.get("secrets") or {}).get("session_file_exists"),
        "session_file_name": (collector.get("secrets") or {}).get("session_file_name"),
        "channel_count": collector.get("channel_count"),
        "limited_channel_count": limited.get("limited_channel_count"),
        "blockers": list((collector.get("blockers") or [])[:8]),
    }


def build_runtime_profile(
    *,
    now: datetime | None = None,
    project_root: Path = PROJECT_ROOT,
    env_status: dict[str, Any] | None = None,
    target_bot: dict[str, Any] | None = None,
    alert_task: dict[str, Any] | None = None,
    postrun_task: dict[str, Any] | None = None,
    brief_state: dict[str, Any] | None = None,
    alert_state: dict[str, Any] | None = None,
    postrun_state: dict[str, Any] | None = None,
    auth_collector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(LOCAL_TIMEZONE)
    system_dir = project_root / "research_vault" / "_system"
    env = env_status if env_status is not None else telegram_env_status()
    target = target_bot if target_bot is not None else telegram_target_bot_status()
    alert_task_payload = alert_task if alert_task is not None else read_scheduled_task(DEFAULT_TASK_NAME)
    postrun_task_payload = postrun_task if postrun_task is not None else read_scheduled_task(POSTRUN_TASK_NAME)
    brief_state_payload = brief_state if brief_state is not None else read_json_object(system_dir / "telegram_brief_delivery_state.json")
    alert_state_payload = alert_state if alert_state is not None else read_json_object(system_dir / "portfolio_report_alert_state.json")
    postrun_state_payload = postrun_state if postrun_state is not None else read_json_object(system_dir / "portfolio_report_alert_postrun_state.json")
    auth = auth_collector if auth_collector is not None else authenticated_collector_summary(
        Settings(research_vault_dir=str(project_root / "research_vault"))
    )

    errors: list[str] = []
    warnings: list[str] = []
    if not env.get("token_configured"):
        errors.append("Telegram bot token is not configured")
    if not env.get("chat_id_configured"):
        errors.append("Telegram chat id is not configured")

    alert_task_summary = task_summary(
        alert_task_payload,
        expected_time="07:00",
        required_marker="run_openclaw_portfolio_report_alert.ps1",
    )
    postrun_task_summary = task_summary(
        postrun_task_payload,
        expected_time="07:10",
        required_marker="run_openclaw_portfolio_report_alert_postrun.ps1",
    )
    errors.extend(f"portfolio_alert_task: {item}" for item in alert_task_summary["errors"])
    errors.extend(f"portfolio_postrun_task: {item}" for item in postrun_task_summary["errors"])
    warnings.extend(f"portfolio_alert_task: {item}" for item in alert_task_summary["warnings"])
    warnings.extend(f"portfolio_postrun_task: {item}" for item in postrun_task_summary["warnings"])
    if not auth.get("ready"):
        warnings.append("authenticated collector is optional and not ready")

    profile = {
        "design": "telegram_runtime_profile_v1",
        "status": "error" if errors else "ok",
        "generated_at": now.isoformat(timespec="seconds"),
        "secret_policy": "Bot tokens, chat IDs, API hashes, and Telegram session contents are never printed.",
        "environment": {
            "token_configured": env.get("token_configured"),
            "chat_id_configured": env.get("chat_id_configured"),
            "token_sources": [
                item.get("name")
                for item in env.get("token_variables", [])
                if isinstance(item, dict) and item.get("configured")
            ],
            "chat_id_sources": [
                item.get("name")
                for item in env.get("chat_id_variables", [])
                if isinstance(item, dict) and item.get("configured")
            ],
            "target_bot": target.get("target_bot"),
            "target_bot_source": target.get("target_bot_source"),
        },
        "channels": {
            "priority_brief": brief_delivery_summary(brief_state_payload, now=now),
            "portfolio_report_alert": {
                "task": alert_task_summary,
                "state": alert_state_summary(alert_state_payload, now=now),
            },
            "portfolio_report_postrun": {
                "task": postrun_task_summary,
                "state": postrun_state_summary(postrun_state_payload, now=now),
            },
            "authenticated_collector": auth,
        },
        "errors": errors,
        "warnings": warnings,
    }
    return profile


def render_text(profile: dict[str, Any]) -> str:
    env = profile.get("environment") if isinstance(profile.get("environment"), dict) else {}
    channels = profile.get("channels") if isinstance(profile.get("channels"), dict) else {}
    alert = channels.get("portfolio_report_alert") if isinstance(channels.get("portfolio_report_alert"), dict) else {}
    postrun = channels.get("portfolio_report_postrun") if isinstance(channels.get("portfolio_report_postrun"), dict) else {}
    auth = channels.get("authenticated_collector") if isinstance(channels.get("authenticated_collector"), dict) else {}
    lines = [
        f"[{profile.get('status')}] telegram_runtime_profile_v1",
        f"- target_bot: {env.get('target_bot')} ({env.get('target_bot_source')})",
        f"- token_configured: {env.get('token_configured')}",
        f"- chat_id_configured: {env.get('chat_id_configured')}",
        f"- portfolio_alert_task: {((alert.get('task') or {}).get('status'))}",
        f"- portfolio_postrun_task: {((postrun.get('task') or {}).get('status'))}",
        f"- authenticated_collector: {auth.get('status')}",
    ]
    for warning in profile.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for error in profile.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram runtime profile을 secret 없이 한 번에 점검합니다.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    profile = build_runtime_profile()
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(render_text(profile))
    return 0 if profile.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
