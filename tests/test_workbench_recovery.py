import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os import workbench_recovery


def _ready_status():
    ids = (
        "strategy_api",
        "backtester_api",
        "strategy_builder",
        "backtester",
        "docker",
        "lean_data",
        "kis_paper",
        "openclaw_mobile",
        "windows_autostart",
    )
    return {
        "ready_count": len(ids),
        "check_count": len(ids),
        "checks": [{"id": item, "status": "ready"} for item in ids],
    }


def test_recovery_rejects_non_allowlisted_action(tmp_path):
    with pytest.raises(ValueError, match="unsupported_recovery_action"):
        workbench_recovery.start_recovery_job(
            "powershell -Command whoami",
            project_root=tmp_path,
            history_path=tmp_path / "history.json",
            status_builder=_ready_status,
        )


def test_recovery_runs_fixed_command_and_stores_safe_metadata(monkeypatch, tmp_path):
    calls = []

    class ImmediateThread:
        def __init__(self, *, target, kwargs, **_ignored):
            self.target = target
            self.kwargs = kwargs

        def start(self):
            self.target(**self.kwargs)

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="secret output", stderr="secret error")

    monkeypatch.setattr(workbench_recovery.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(workbench_recovery.subprocess, "run", fake_run)
    monkeypatch.setattr(workbench_recovery, "_ACTIVE_JOB_ID", None)

    job = workbench_recovery.start_recovery_job(
        "all",
        project_root=tmp_path,
        history_path=tmp_path / "history.json",
        status_builder=_ready_status,
    )
    payload = workbench_recovery.recovery_status(tmp_path / "history.json")

    assert job["action"] == "all"
    assert calls[0][0][-1] == "start"
    assert calls[0][0][-2].endswith("investment-research-os.ps1")
    assert calls[0][1]["capture_output"] is True
    assert payload["status"] == "idle"
    assert payload["history"][0]["status"] == "success"
    assert payload["history"][0]["ready_after"] == 9
    assert "stdout" not in payload["history"][0]
    assert "stderr" not in payload["history"][0]
    assert payload["security"] == {
        "allowlisted_only": True,
        "accepts_command_text": False,
        "stores_subprocess_output": False,
        "live_trading_allowed": False,
    }


def test_recovery_blocks_duplicate_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(workbench_recovery, "_ACTIVE_JOB_ID", "already-running")
    with pytest.raises(RuntimeError, match="recovery_already_running"):
        workbench_recovery.start_recovery_job(
            "openclaw",
            project_root=tmp_path,
            history_path=tmp_path / "history.json",
            status_builder=_ready_status,
        )
