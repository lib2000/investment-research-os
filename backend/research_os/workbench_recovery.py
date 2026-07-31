"""Allowlisted local service recovery jobs for the investment workbench."""

from __future__ import annotations

import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from research_os.state_store import read_json_store, write_json_store


ALLOWED_RECOVERY_ACTIONS = {
    "all": "전체 작업대",
    "trading_tools": "전략·백테스트",
    "kis_paper": "KIS 모의투자",
    "openclaw": "OpenClaw",
}
TERMINAL_STATUSES = {"success", "failed", "rejected", "interrupted"}
_LOCK = threading.RLock()
_ACTIVE_JOB_ID: str | None = None


def _timestamp() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()


def _safe_job(job: dict) -> dict:
    allowed_keys = {
        "job_id",
        "action",
        "label",
        "status",
        "stage",
        "requested_at",
        "started_at",
        "completed_at",
        "duration_ms",
        "exit_code",
        "ready_before",
        "ready_after",
        "check_count",
        "error_code",
        "message",
    }
    return {key: job.get(key) for key in allowed_keys if key in job}


def _read_jobs(history_path: Path) -> list[dict]:
    payload = read_json_store(history_path, {"jobs": []})
    return [item for item in payload.get("jobs", []) if isinstance(item, dict)]


def _persist_job(history_path: Path, job: dict) -> None:
    jobs = [item for item in _read_jobs(history_path) if item.get("job_id") != job.get("job_id")]
    write_json_store(history_path, {"jobs": [_safe_job(job), *jobs][:20]})


def _fixed_command(action: str, project_root: Path) -> tuple[list[str], int]:
    launcher = project_root / "investment-research-os.ps1"
    trading_script = project_root.parent / "open-trading-api" / "investment-web.ps1"
    commands = {
        "all": (["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "start"], 180),
        "trading_tools": (["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(trading_script), "start"], 150),
        "kis_paper": (["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher), "start"], 180),
        "openclaw": (["wsl.exe", "-d", os.getenv("OPENCLAW_WSL_DISTRO", "Ubuntu-24.04"), "--", "systemctl", "--user", "start", "openclaw-gateway.service"], 30),
    }
    return commands[action]


def _target_ready(action: str, status: dict) -> bool:
    checks = {item.get("id"): item.get("status") for item in status.get("checks", []) if isinstance(item, dict)}
    targets = {
        "all": tuple(checks),
        "trading_tools": ("strategy_api", "backtester_api", "strategy_builder", "backtester"),
        "kis_paper": ("kis_paper",),
        "openclaw": ("openclaw_mobile",),
    }[action]
    return bool(targets) and all(checks.get(target) == "ready" for target in targets)


def _run_job(
    job: dict,
    *,
    project_root: Path,
    history_path: Path,
    status_builder: Callable[[], dict],
) -> None:
    global _ACTIVE_JOB_ID
    started = datetime.now(ZoneInfo("Asia/Seoul"))
    try:
        before = status_builder()
        with _LOCK:
            job.update(
                status="running",
                stage="고정 복구 명령 실행",
                started_at=started.replace(microsecond=0).isoformat(),
                ready_before=int(before.get("ready_count") or 0),
                check_count=int(before.get("check_count") or 0),
                message="허용된 로컬 복구 작업을 실행하고 있습니다.",
            )
            _persist_job(history_path, job)

        command, timeout_seconds = _fixed_command(job["action"], project_root)
        completed = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        with _LOCK:
            job["stage"] = "대상 서비스 재점검"
            job["exit_code"] = int(completed.returncode)
            _persist_job(history_path, job)

        after = status_builder()
        target_ready = _target_ready(job["action"], after)
        if completed.returncode != 0:
            job.update(status="failed", error_code="launcher_failed", message="고정 복구 명령이 정상 종료되지 않았습니다.")
        elif not target_ready:
            job.update(status="failed", error_code="target_not_ready", message="복구 명령은 끝났지만 대상 서비스가 아직 정상 상태가 아닙니다.")
        else:
            job.update(status="success", stage="완료", message="대상 서비스 복구와 재점검이 완료되었습니다.")
        job["ready_after"] = int(after.get("ready_count") or 0)
        job["check_count"] = int(after.get("check_count") or job.get("check_count") or 0)
    except subprocess.TimeoutExpired:
        job.update(status="failed", error_code="timeout", message="복구 작업 제한 시간을 초과했습니다.")
    except (FileNotFoundError, OSError):
        job.update(status="failed", error_code="runner_unavailable", message="고정 복구 실행기를 시작하지 못했습니다.")
    except Exception:
        job.update(status="failed", error_code="internal_error", message="복구 작업 내부 오류가 발생했습니다.")
    finally:
        completed_at = datetime.now(ZoneInfo("Asia/Seoul"))
        job["completed_at"] = completed_at.replace(microsecond=0).isoformat()
        job["duration_ms"] = max(0, round((completed_at - started).total_seconds() * 1000))
        if job.get("status") not in TERMINAL_STATUSES:
            job.update(status="failed", error_code="incomplete", message="복구 작업이 완료 상태를 기록하지 못했습니다.")
        with _LOCK:
            _persist_job(history_path, job)
            if _ACTIVE_JOB_ID == job.get("job_id"):
                _ACTIVE_JOB_ID = None


def start_recovery_job(
    action: str,
    *,
    project_root: Path,
    history_path: Path,
    status_builder: Callable[[], dict],
) -> dict:
    global _ACTIVE_JOB_ID
    normalized = str(action or "").strip()
    if normalized not in ALLOWED_RECOVERY_ACTIONS:
        raise ValueError("unsupported_recovery_action")
    with _LOCK:
        if _ACTIVE_JOB_ID:
            raise RuntimeError("recovery_already_running")
        existing = _read_jobs(history_path)
        for item in existing:
            if item.get("status") in {"queued", "running"}:
                item.update(status="interrupted", stage="중단됨", completed_at=_timestamp(), error_code="backend_restarted", message="백엔드 재시작으로 이전 작업 상태가 종료되었습니다.")
                _persist_job(history_path, item)
        job = {
            "job_id": uuid4().hex,
            "action": normalized,
            "label": ALLOWED_RECOVERY_ACTIONS[normalized],
            "status": "queued",
            "stage": "실행 대기",
            "requested_at": _timestamp(),
            "message": "복구 작업을 시작할 준비가 되었습니다.",
        }
        _ACTIVE_JOB_ID = job["job_id"]
        _persist_job(history_path, job)
        thread = threading.Thread(
            target=_run_job,
            kwargs={
                "job": job,
                "project_root": project_root,
                "history_path": history_path,
                "status_builder": status_builder,
            },
            name=f"workbench-recovery-{normalized}",
            daemon=True,
        )
        thread.start()
        return _safe_job(job)


def recovery_status(history_path: Path) -> dict:
    with _LOCK:
        jobs = [_safe_job(item) for item in _read_jobs(history_path)[:20]]
        active = next((item for item in jobs if item.get("job_id") == _ACTIVE_JOB_ID), None)
    return {
        "status": "running" if active else "idle",
        "active_job": active,
        "history": jobs,
        "allowed_actions": [
            {"id": action, "label": label}
            for action, label in ALLOWED_RECOVERY_ACTIONS.items()
        ],
        "history_retention": 20,
        "security": {
            "allowlisted_only": True,
            "accepts_command_text": False,
            "stores_subprocess_output": False,
            "live_trading_allowed": False,
        },
    }
