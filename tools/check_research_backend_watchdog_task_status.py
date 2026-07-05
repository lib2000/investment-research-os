"""Check the Windows scheduled task that keeps the Research OS backend alive."""

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
DEFAULT_TASK_NAME = "InvestmentJournalApp Research Backend Watchdog"
DEFAULT_STATE_FILE = PROJECT_ROOT / "tmp" / "research_backend_watchdog_state.json"
DEFAULT_REQUIRED_ARGS = ("ensure-research-backend.ps1", "-Port", "8001")
LOCAL_TIMEZONE = ZoneInfo("Asia/Seoul")
NEVER_RUN_PREFIXES = ("1999-11-30", "0001-01-01")
SUCCESS_RESULT_CODES = {0, 267009, 267011}


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
$task = Get-ScheduledTask -TaskName $env:RESEARCH_BACKEND_WATCHDOG_TASK_NAME -ErrorAction Stop
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
  RepetitionInterval = "$($task.Triggers[0].Repetition.Interval)"
} | ConvertTo-Json -Depth 4
"""
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        cwd=PROJECT_ROOT,
        env={**os.environ, "RESEARCH_BACKEND_WATCHDOG_TASK_NAME": task_name},
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
    required_args: tuple[str, ...] = DEFAULT_REQUIRED_ARGS,
    expected_interval: str = "PT10M",
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(LOCAL_TIMEZONE)
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []
    if not task.get("found"):
        errors.append(_safe_text(task.get("error")) or "research backend watchdog scheduled task not found")

    arguments = _safe_text(task.get("Arguments"))
    missing_args = [item for item in required_args if item not in arguments]
    if missing_args:
        errors.append("watchdog scheduled task missing arguments: " + ", ".join(missing_args))

    interval = _safe_text(task.get("RepetitionInterval"))
    if expected_interval and interval != expected_interval:
        errors.append(f"watchdog repetition interval is not {expected_interval}: {interval or 'missing'}")

    next_run = _parse_datetime(task.get("NextRunTime"))
    if not next_run:
        errors.append("watchdog next run time is unavailable")
    elif next_run < now:
        warnings.append("watchdog next run time is in the past")
    elif (next_run - now).total_seconds() > 24 * 3600:
        warnings.append("watchdog next run time is more than 24 hours away")

    last_run_text = _safe_text(task.get("LastRunTime"))
    never_run = not last_run_text or any(last_run_text.startswith(prefix) for prefix in NEVER_RUN_PREFIXES)
    last_result = int(task.get("LastTaskResult") or 0)
    if never_run:
        info.append("watchdog task is registered and waiting for its first run")
    elif last_result not in SUCCESS_RESULT_CODES:
        errors.append(f"watchdog last result is non-success: {last_result}")

    missed = int(task.get("NumberOfMissedRuns") or 0)
    if missed:
        errors.append(f"watchdog missed runs: {missed}")

    state_age = _age_hours(state_file, now=now)
    if state_age is None:
        warnings.append("watchdog state file has not been written yet")
    elif state_age > max_state_age_hours:
        warnings.append(f"watchdog state file is stale: {state_age:.1f}h")

    return {
        "status": "error" if errors else "ok",
        "errors": errors,
        "warnings": warnings,
        "info": info,
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
        f"[{result.get('status')}] research_backend_watchdog_task_status_v1",
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
    for item in result.get("info") or []:
        lines.append(f"- info: {item}")
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Research OS backend watchdog scheduled task.")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--max-state-age-hours", type=float, default=2)
    parser.add_argument("--expected-interval", default="PT10M")
    parser.add_argument("--required-arg", action="append", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state_file = args.state_file if args.state_file.is_absolute() else PROJECT_ROOT / args.state_file
    result = evaluate_task_status(
        read_scheduled_task(args.task_name),
        state_file=state_file,
        max_state_age_hours=args.max_state_age_hours,
        required_args=tuple(args.required_arg) if args.required_arg is not None else DEFAULT_REQUIRED_ARGS,
        expected_interval=args.expected_interval,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
