"""Secret-free console status for the 07:00 portfolio report Telegram alert."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ALERT_TASK_NAME = "InvestmentJournalApp OpenClaw Portfolio Report Alert"
POSTRUN_TASK_NAME = "InvestmentJournalApp OpenClaw Portfolio Report Alert Postrun"
NEVER_RUN_PREFIXES = ("1999-11-30", "0001-01-01")


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_scheduled_task(task_name: str, *, project_root: Path) -> dict[str, Any]:
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
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            cwd=project_root,
            env={**os.environ, "PORTFOLIO_REPORT_ALERT_TASK_NAME": task_name},
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return {"found": False, "error": f"scheduled task check unavailable: {exc}"}
    if completed.returncode != 0:
        return {
            "found": False,
            "returncode": completed.returncode,
            "error": _safe_text(completed.stderr or completed.stdout),
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"found": False, "error": f"scheduled task JSON parse failed: {exc.msg}"}
    return {"found": True, **payload}


def _never_run(task: dict[str, Any]) -> bool:
    text = _safe_text(task.get("LastRunTime"))
    return not text or any(text.startswith(prefix) for prefix in NEVER_RUN_PREFIXES)


def _task_status(task: dict[str, Any], *, expected_time: str, required_marker: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []
    arguments = _safe_text(task.get("Arguments"))
    trigger = _safe_text(task.get("Trigger") or task.get("NextRunTime"))
    if not task.get("found"):
        errors.append(_safe_text(task.get("error")) or "scheduled task not found")
    if required_marker and required_marker not in arguments:
        errors.append(f"scheduled task does not call {required_marker}")
    if expected_time and expected_time not in trigger:
        errors.append(f"scheduled task is not configured for {expected_time}")
    missed = int(task.get("NumberOfMissedRuns") or 0)
    if missed:
        errors.append(f"scheduled task missed runs: {missed}")
    never_run = _never_run(task)
    last_result = int(task.get("LastTaskResult") or 0)
    if never_run:
        info.append("scheduled task is registered and waiting for its first run")
    elif last_result not in {0, 267009, 267011}:
        errors.append(f"scheduled task last result is non-success: {last_result}")
    return {
        "status": "error" if errors else "first_run_pending" if never_run else "ok",
        "found": bool(task.get("found")),
        "never_run": never_run,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "task_name": task.get("TaskName"),
        "task_state": task.get("State"),
        "last_run_at": task.get("LastRunTime"),
        "last_result": task.get("LastTaskResult"),
        "next_run_at": task.get("NextRunTime"),
        "trigger": task.get("Trigger"),
    }


def _alert_state_status(state: dict[str, Any], *, state_path: Path) -> dict[str, Any]:
    plan = state.get("last_plan") if isinstance(state.get("last_plan"), dict) else {}
    return {
        "state_file": str(state_path),
        "state_exists": state_path.exists(),
        "updated_at": state.get("updated_at"),
        "target_bot": state.get("target_bot") or "@lib20_bot",
        "send_time": state.get("send_time") or "07:00",
        "candidate_count": plan.get("candidate_count"),
        "message_count": plan.get("message_count"),
        "delivered": plan.get("delivered"),
        "chat_id_configured": plan.get("chat_id_configured"),
        "sent_report_key_count": len(state.get("sent_report_keys") or []),
    }


def _postrun_state_status(state: dict[str, Any], *, state_path: Path) -> dict[str, Any]:
    return {
        "state_file": str(state_path),
        "state_exists": state_path.exists(),
        "updated_at": state.get("updated_at"),
        "last_status": state.get("last_status"),
        "last_should_send": state.get("last_should_send"),
        "last_sent": state.get("last_sent"),
        "sent_fingerprint_count": len(state.get("sent_fingerprints") or []),
    }


def _section_status(task_status: dict[str, Any], state_status: dict[str, Any]) -> str:
    if task_status["status"] == "error":
        return "error"
    if not state_status.get("state_exists"):
        return "first_run_pending" if task_status.get("never_run") else "needs_attention"
    if task_status["status"] == "first_run_pending":
        return "first_run_pending"
    return "ok"


def build_portfolio_report_alert_console_status(
    *,
    project_root: Path,
    alert_state_path: Path,
    postrun_state_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    alert_task = _task_status(
        _read_scheduled_task(ALERT_TASK_NAME, project_root=project_root),
        expected_time="07:00",
        required_marker="run_openclaw_portfolio_report_alert.ps1",
    )
    postrun_task = _task_status(
        _read_scheduled_task(POSTRUN_TASK_NAME, project_root=project_root),
        expected_time="07:10",
        required_marker="run_openclaw_portfolio_report_alert_postrun.ps1",
    )
    alert_state = _alert_state_status(read_json_object(alert_state_path), state_path=alert_state_path)
    postrun_state = _postrun_state_status(read_json_object(postrun_state_path), state_path=postrun_state_path)
    alert_status = _section_status(alert_task, alert_state)
    postrun_status = _section_status(postrun_task, postrun_state)
    statuses = {alert_status, postrun_status}
    if "error" in statuses:
        status = "needs_attention"
        next_action = "예약 작업 오류를 확인하고 07:00 알림/07:10 사후점검 등록 상태를 다시 점검하세요."
    elif "needs_attention" in statuses:
        status = "needs_attention"
        next_action = "최근 실행 상태 파일이 없거나 오래되었습니다. 07:00 본작업과 07:10 사후점검 로그를 확인하세요."
    elif statuses == {"ok"}:
        status = "ok"
        next_action = "최근 보유 종목 리포트 알림과 사후점검이 정상입니다."
    else:
        status = "first_run_pending"
        next_action = "첫 예약 실행 전입니다. 다음 07:00 실행 후 07:10 사후점검 상태가 자동 갱신됩니다."
    return {
        "status": status,
        "module": "portfolio_report_alert_console_status",
        "design": "portfolio_report_alert_console_status_v1",
        "target_bot": "@lib20_bot",
        "alert_time": "07:00",
        "postrun_time": "07:10",
        "checked_at": (now or datetime.now()).isoformat(timespec="seconds"),
        "alert": {"status": alert_status, "task": alert_task, "state": alert_state},
        "postrun": {"status": postrun_status, "task": postrun_task, "state": postrun_state},
        "next_action": next_action,
    }
