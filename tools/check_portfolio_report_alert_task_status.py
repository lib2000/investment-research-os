"""Check the Windows scheduled task for the 07:00 portfolio report Telegram alert."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_NAME = "InvestmentJournalApp OpenClaw Portfolio Report Alert"
DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "portfolio_report_alert_state.json"
LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
NEVER_RUN_PREFIXES = ("1999-11-30", "0001-01-01")
SUCCESS_RESULT_CODES = {0, 267009, 267011}
DEFAULT_REQUIRED_ARGS = ("run_openclaw_portfolio_report_alert.ps1", "-WriteState")
DEFAULT_TARGET_BOT = "@lib20_bot"


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_bot_username(value: Any) -> str:
    text = _safe_text(value) or DEFAULT_TARGET_BOT
    if not text.startswith("@"):
        text = "@" + text
    return text


def _parse_datetime(value: Any) -> datetime | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
    return parsed


def _age_hours(path: Path, *, now: datetime | None = None) -> float | None:
    if not path.exists():
        return None
    now = now or datetime.now(LOCAL_TIMEZONE)
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=LOCAL_TIMEZONE)
    return max(0.0, (now - modified).total_seconds() / 3600)


def _configured_env(name: str) -> dict[str, Any]:
    current = bool(os.getenv(name, "").strip())
    user = ""
    machine = ""
    try:
        user = os.getenv(name, "") or ""
        # Environment.GetEnvironmentVariable is the reliable way to check values
        # persisted for Windows scheduled tasks without printing secret contents.
        command = (
            "[Environment]::GetEnvironmentVariable('{0}', 'User');"
            "[Environment]::GetEnvironmentVariable('{0}', 'Machine')"
        ).format(name)
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        lines = [line.strip() for line in (completed.stdout or "").splitlines()]
        user = lines[0] if len(lines) >= 1 else user
        machine = lines[1] if len(lines) >= 2 else ""
    except OSError:
        pass
    return {
        "name": name,
        "configured": bool(current or user or machine),
        "current_process": current,
        "user": bool(user),
        "machine": bool(machine),
    }


def _read_windows_env_pair(name: str) -> tuple[str, str]:
    current = os.getenv(name, "").strip()
    user = ""
    machine = ""
    try:
        command = (
            "[Environment]::GetEnvironmentVariable('{0}', 'User');"
            "[Environment]::GetEnvironmentVariable('{0}', 'Machine')"
        ).format(name)
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        lines = [line.strip() for line in (completed.stdout or "").splitlines()]
        user = lines[0] if len(lines) >= 1 else ""
        machine = lines[1] if len(lines) >= 2 else ""
    except OSError:
        pass
    value = current or user or machine
    source = "current_process" if current else "user" if user else "machine" if machine else "default"
    return value, source


def telegram_target_bot_status() -> dict[str, Any]:
    variables: list[dict[str, Any]] = []
    selected_value = ""
    selected_source = "default"
    for name in ("TELEGRAM_REPORT_ALERT_TARGET_BOT_USERNAME", "TELEGRAM_BOT_USERNAME"):
        value, scope = _read_windows_env_pair(name)
        variables.append(
            {
                "name": name,
                "configured": bool(value),
                "selected_scope": scope if value else "none",
            }
        )
        if value and not selected_value:
            selected_value = value
            selected_source = name
    return {
        "target_bot": _normalize_bot_username(selected_value),
        "target_bot_source": selected_source,
        "variables": variables,
    }


def _read_state_target_bot(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""
    if not isinstance(data, dict):
        return ""
    return _normalize_bot_username(data.get("target_bot")) if data.get("target_bot") else ""


def telegram_env_status() -> dict[str, Any]:
    token_vars = [
        "TELEGRAM_REPORT_ALERT_BOT_TOKEN",
        "MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
    ]
    chat_vars = [
        "TELEGRAM_REPORT_ALERT_CHAT_ID",
        "MARKET_SIGNAL_GRAPH_TELEGRAM_CHAT_ID",
        "TELEGRAM_CHAT_ID",
    ]
    token = [_configured_env(name) for name in token_vars]
    chat = [_configured_env(name) for name in chat_vars]
    return {
        "token_configured": any(item["configured"] for item in token),
        "chat_id_configured": any(item["configured"] for item in chat),
        "token_variables": token,
        "chat_id_variables": chat,
    }


def read_scheduled_task(task_name: str) -> dict[str, Any]:
    ps = r"""
$task = Get-ScheduledTask -TaskName $env:PORTFOLIO_REPORT_ALERT_TASK_NAME -ErrorAction Stop
$info = $task | Get-ScheduledTaskInfo
[pscustomobject]@{
  TaskName = $task.TaskName
  State = "$($task.State)"
  Execute = $task.Actions[0].Execute
  Arguments = $task.Actions[0].Arguments
  LastRunTime = $info.LastRunTime.ToString("o")
  LastTaskResult = $info.LastTaskResult
  NextRunTime = $info.NextRunTime.ToString("o")
  NumberOfMissedRuns = $info.NumberOfMissedRuns
  Trigger = $task.Triggers[0].StartBoundary
} | ConvertTo-Json -Depth 4
"""
    env = {**os.environ, "PORTFOLIO_REPORT_ALERT_TASK_NAME": task_name}
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        return {
            "found": False,
            "returncode": completed.returncode,
            "error": _safe_text(completed.stderr or completed.stdout),
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"found": False, "returncode": 1, "error": f"scheduled task JSON parse failed: {exc.msg}"}
    return {"found": True, **payload}


def evaluate_task_status(
    task: dict[str, Any],
    *,
    state_file: Path,
    max_state_age_hours: float,
    require_state_fresh: bool,
    expected_time: str = "07:00",
    required_args: tuple[str, ...] = DEFAULT_REQUIRED_ARGS,
    require_telegram_env: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(LOCAL_TIMEZONE)
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []
    if not task.get("found"):
        errors.append(_safe_text(task.get("error")) or "portfolio report alert scheduled task not found")

    arguments = _safe_text(task.get("Arguments"))
    missing_args = [item for item in required_args if item not in arguments]
    if missing_args:
        errors.append("scheduled task missing required arguments: " + ", ".join(missing_args))
    standalone_live_submit = "-Enabled" in arguments and "-Submit" in arguments
    if task.get("found") and not standalone_live_submit:
        info.append("standalone Telegram send is disabled; integrated Investment Priority Brief owns live delivery")

    trigger = _safe_text(task.get("Trigger") or task.get("NextRunTime"))
    if expected_time and expected_time not in trigger:
        errors.append(f"scheduled task is not configured for {expected_time}")

    next_run = _parse_datetime(task.get("NextRunTime"))
    if not next_run:
        errors.append("scheduled task next run time is unavailable")
    elif next_run < now:
        warnings.append("scheduled task next run time is in the past")
    elif (next_run - now).total_seconds() > 48 * 3600:
        warnings.append("scheduled task next run time is more than 48 hours away")

    last_run_text = _safe_text(task.get("LastRunTime"))
    never_run = not last_run_text or any(last_run_text.startswith(prefix) for prefix in NEVER_RUN_PREFIXES)
    last_result = int(task.get("LastTaskResult") or 0)
    if never_run:
        info.append("scheduled task is registered and waiting for its first run")
    elif last_result not in SUCCESS_RESULT_CODES:
        errors.append(f"scheduled task last result is non-success: {last_result}")

    missed = int(task.get("NumberOfMissedRuns") or 0)
    if missed:
        errors.append(f"scheduled task missed runs: {missed}")

    env_status = telegram_env_status()
    target_bot_status = telegram_target_bot_status()
    if require_telegram_env and not env_status["token_configured"]:
        errors.append("Telegram bot token is not configured for scheduled task runtime")
    if require_telegram_env and not env_status["chat_id_configured"]:
        errors.append("Telegram chat id is not configured for scheduled task runtime")

    state_age = _age_hours(state_file, now=now)
    state_target_bot = _read_state_target_bot(state_file)
    configured_target_bot = str(target_bot_status.get("target_bot") or DEFAULT_TARGET_BOT)
    if state_target_bot and state_target_bot != configured_target_bot:
        warnings.append(
            f"portfolio report alert target bot changed: state={state_target_bot}, configured={configured_target_bot}"
        )
    if state_age is None:
        if require_state_fresh:
            errors.append("portfolio report alert state file is missing")
        elif never_run:
            info.append("portfolio report alert state file will be written after the first run")
        else:
            warnings.append("portfolio report alert state file has not been written yet")
    elif state_age > max_state_age_hours:
        message = f"portfolio report alert state file is stale: {state_age:.1f}h"
        if require_state_fresh:
            errors.append(message)
        else:
            warnings.append(message)

    return {
        "status": "error" if errors else "ok",
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "task": task,
        "env": env_status,
        "target_bot": target_bot_status,
        "state_target_bot": state_target_bot,
        "state_file": str(state_file),
        "state_file_exists": state_age is not None,
        "state_file_age_hours": state_age,
        "never_run": never_run,
        "standalone_live_submit_configured": standalone_live_submit,
        "checked_at": now.isoformat(timespec="seconds"),
    }


def render_text(result: dict[str, Any]) -> str:
    task = result.get("task") if isinstance(result.get("task"), dict) else {}
    lines = [
        f"[{result.get('status')}] portfolio_report_alert_task_status_v1",
        f"- task_name: {task.get('TaskName')}",
        f"- next_run: {task.get('NextRunTime')}",
        f"- last_run: {task.get('LastRunTime')}",
        f"- last_result: {task.get('LastTaskResult')}",
        f"- token_configured: {((result.get('env') or {}).get('token_configured'))}",
        f"- chat_id_configured: {((result.get('env') or {}).get('chat_id_configured'))}",
        f"- target_bot: {((result.get('target_bot') or {}).get('target_bot'))}",
        f"- state_target_bot: {result.get('state_target_bot')}",
        f"- state_file_exists: {result.get('state_file_exists')}",
        f"- state_file_age_hours: {result.get('state_file_age_hours')}",
    ]
    for warning in result.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for item in result.get("info") or []:
        lines.append(f"- info: {item}")
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the 07:00 OpenClaw Telegram holding-report scheduled task.")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--max-state-age-hours", type=float, default=36)
    parser.add_argument("--require-state-fresh", action="store_true")
    parser.add_argument("--expected-time", default="07:00")
    parser.add_argument("--required-arg", action="append", default=None)
    parser.add_argument("--skip-telegram-env-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state_file = args.state_file if args.state_file.is_absolute() else PROJECT_ROOT / args.state_file
    result = evaluate_task_status(
        read_scheduled_task(args.task_name),
        state_file=state_file,
        max_state_age_hours=args.max_state_age_hours,
        require_state_fresh=args.require_state_fresh,
        expected_time=args.expected_time,
        required_args=tuple(args.required_arg) if args.required_arg is not None else DEFAULT_REQUIRED_ARGS,
        require_telegram_env=not args.skip_telegram_env_check,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
