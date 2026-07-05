"""Check the Windows scheduled task for the OpenClaw answer capture cycle."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_NAME = "InvestmentJournalApp OpenClaw Answer Capture Cycle"
DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_answer_capture_cycle_state.json"
LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
NEVER_RUN_PREFIXES = ("1999-11-30", "0001-01-01")
SUCCESS_RESULT_CODES = {0, 267009, 267011}
DEFAULT_REQUIRED_ARGS = ("run_openclaw_answer_capture_cycle.ps1", "-WriteState", "-Collect")


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


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


def read_scheduled_task(task_name: str) -> dict[str, Any]:
    ps = r"""
$task = Get-ScheduledTask -TaskName $env:OPENCLAW_ANSWER_CAPTURE_TASK_NAME -ErrorAction Stop
$info = $task | Get-ScheduledTaskInfo
$trigger = $task.Triggers[0]
[pscustomobject]@{
  TaskName = $task.TaskName
  State = "$($task.State)"
  Execute = $task.Actions[0].Execute
  Arguments = $task.Actions[0].Arguments
  LastRunTime = $info.LastRunTime.ToString("o")
  LastTaskResult = $info.LastTaskResult
  NextRunTime = $info.NextRunTime.ToString("o")
  NumberOfMissedRuns = $info.NumberOfMissedRuns
  Trigger = $trigger.StartBoundary
  RepetitionInterval = "$($trigger.Repetition.Interval)"
} | ConvertTo-Json -Depth 4
"""
    env = {**os.environ, "OPENCLAW_ANSWER_CAPTURE_TASK_NAME": task_name}
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
    expected_time: str = "00:05",
    expected_interval: str = "PT15M",
    required_args: tuple[str, ...] = DEFAULT_REQUIRED_ARGS,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(LOCAL_TIMEZONE)
    errors: list[str] = []
    warnings: list[str] = []
    if not task.get("found"):
        errors.append(_safe_text(task.get("error")) or "OpenClaw answer capture scheduled task not found")

    arguments = _safe_text(task.get("Arguments"))
    missing_args = [item for item in required_args if item not in arguments]
    if missing_args:
        errors.append("scheduled task missing answer capture arguments: " + ", ".join(missing_args))

    execute = _safe_text(task.get("Execute")).lower()
    if execute and "powershell" not in execute:
        errors.append(f"scheduled task execute is unexpected: {task.get('Execute')}")

    trigger = _safe_text(task.get("Trigger") or task.get("NextRunTime"))
    if expected_time and expected_time not in trigger:
        errors.append(f"scheduled task is not configured for {expected_time}")

    interval = _safe_text(task.get("RepetitionInterval"))
    if expected_interval and interval and interval != expected_interval:
        errors.append(f"scheduled task interval mismatch: {interval} != {expected_interval}")

    next_run = _parse_datetime(task.get("NextRunTime"))
    if not next_run:
        errors.append("scheduled task next run time is unavailable")
    elif next_run < now:
        warnings.append("scheduled task next run time is in the past")
    elif (next_run - now).total_seconds() > 24 * 3600:
        warnings.append("scheduled task next run time is more than 24 hours away")

    last_run_text = _safe_text(task.get("LastRunTime"))
    never_run = not last_run_text or any(last_run_text.startswith(prefix) for prefix in NEVER_RUN_PREFIXES)
    last_result = int(task.get("LastTaskResult") or 0)
    if never_run:
        warnings.append("scheduled task has not run yet")
    elif last_result not in SUCCESS_RESULT_CODES:
        errors.append(f"scheduled task last result is non-success: {last_result}")

    missed = int(task.get("NumberOfMissedRuns") or 0)
    if missed:
        errors.append(f"scheduled task missed runs: {missed}")

    state_age = _age_hours(state_file, now=now)
    if state_age is None:
        warnings.append("answer capture cycle state file has not been written yet")
        if require_state_fresh:
            errors.append("answer capture cycle state file is missing")
    elif state_age > max_state_age_hours:
        message = f"answer capture cycle state file is stale: {state_age:.1f}h"
        if require_state_fresh:
            errors.append(message)
        else:
            warnings.append(message)

    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "warnings": warnings,
        "task": task,
        "state_file": str(state_file),
        "state_file_exists": state_age is not None,
        "state_file_age_hours": state_age,
        "never_run": never_run,
        "checked_at": now.isoformat(timespec="seconds"),
    }


def render_text(result: dict[str, Any]) -> str:
    task = result.get("task") if isinstance(result.get("task"), dict) else {}
    lines = [
        f"[{result.get('status')}] openclaw_answer_capture_task_status_v1",
        f"- task_name: {task.get('TaskName')}",
        f"- next_run: {task.get('NextRunTime')}",
        f"- last_run: {task.get('LastRunTime')}",
        f"- last_result: {task.get('LastTaskResult')}",
        f"- repetition_interval: {task.get('RepetitionInterval')}",
        f"- state_file_exists: {result.get('state_file_exists')}",
        f"- state_file_age_hours: {result.get('state_file_age_hours')}",
    ]
    for warning in result.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the OpenClaw answer capture scheduled task.")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--max-state-age-hours", type=float, default=24)
    parser.add_argument("--require-state-fresh", action="store_true")
    parser.add_argument("--expected-time", default="00:05")
    parser.add_argument("--expected-interval", default="PT15M")
    parser.add_argument("--required-arg", action="append", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state_file = args.state_file if args.state_file.is_absolute() else PROJECT_ROOT / args.state_file
    result = evaluate_task_status(
        read_scheduled_task(args.task_name),
        state_file=state_file,
        max_state_age_hours=args.max_state_age_hours,
        require_state_fresh=args.require_state_fresh,
        expected_time=args.expected_time,
        expected_interval=args.expected_interval,
        required_args=tuple(args.required_arg) if args.required_arg is not None else DEFAULT_REQUIRED_ARGS,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
