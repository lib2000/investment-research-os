import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os import system_health
import research_os_main as main


def test_workbench_status_aggregates_ready_and_attention(monkeypatch):
    monkeypatch.setattr(
        system_health,
        "_probe_local_service",
        lambda service: {"id": service[0], "label": service[1], "status": "ready"},
    )
    monkeypatch.setattr(
        system_health,
        "_docker_status",
        lambda: {"id": "docker", "label": "Docker", "status": "ready"},
    )
    monkeypatch.setattr(
        system_health,
        "_lean_data_status",
        lambda: {"id": "lean", "label": "Lean", "status": "ready"},
    )
    monkeypatch.setattr(
        system_health,
        "_kis_paper_status",
        lambda: {"id": "kis", "label": "KIS", "status": "needs_auth"},
    )
    monkeypatch.setattr(
        system_health,
        "_openclaw_mobile_status",
        lambda: {
            "id": "openclaw_mobile",
            "label": "OpenClaw/iPhone",
            "status": "ready",
            "paired_devices": 1,
        },
    )
    monkeypatch.setattr(
        system_health,
        "_windows_autostart_status",
        lambda: {
            "id": "windows_autostart",
            "label": "Windows 자동 시작",
            "status": "ready",
            "task_registered": True,
        },
    )

    payload = system_health.build_investment_workbench_status()

    assert payload["status"] == "needs_attention"
    assert payload["ready_count"] == payload["check_count"] - 1
    assert payload["checks"][-3]["status"] == "needs_auth"
    assert payload["checks"][-2]["paired_devices"] == 1
    assert payload["checks"][-1]["task_registered"] is True
    assert "investment-research-os.ps1" in payload["recovery_command"]
    assert payload["recovery_command"].endswith('" start')


def test_workbench_history_stores_only_status_metadata(monkeypatch):
    writes = []
    monkeypatch.setattr(
        main,
        "build_investment_workbench_status",
        lambda: {
            "status": "needs_attention",
            "checked_at": "2026-07-13T20:00:00+09:00",
            "ready_count": 6,
            "check_count": 7,
            "checks": [
                {"id": "docker", "label": "Docker", "status": "ready"},
                {"id": "kis_paper", "label": "KIS", "status": "needs_auth", "next_action": "secret-free"},
            ],
        },
    )
    monkeypatch.setattr(main, "workbench_health_history_path", lambda settings: Path("unused"))
    monkeypatch.setattr(main, "read_json_store", lambda path, default: {"events": []})
    monkeypatch.setattr(main, "write_json_store", lambda path, payload: writes.append(payload))

    response = main.read_investment_workbench_status(settings=object())

    assert response["history"][0]["failures"] == [{"id": "kis_paper", "status": "needs_auth"}]
    assert "next_action" not in writes[0]["events"][0]["failures"][0]
    assert "label" not in writes[0]["events"][0]["failures"][0]


def test_openclaw_mobile_status_reports_paired_iphone(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Result:
        returncode = 0
        stdout = "1\n"

    monkeypatch.setattr(system_health, "urlopen", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(system_health.subprocess, "run", lambda *_args, **_kwargs: Result())

    status = system_health._openclaw_mobile_status()

    assert status["status"] == "ready"
    assert status["paired_devices"] == 1
    assert status["next_action"] is None


def test_windows_autostart_status_reports_only_safe_metadata(monkeypatch):
    class Result:
        returncode = 0
        stdout = '{"status":"ready","task_registered":true,"credential_configured":true,"last_startup_status":"success","last_startup_at":"2026-07-14T06:24:11+09:00"}\n'

    monkeypatch.setattr(system_health.subprocess, "run", lambda *_args, **_kwargs: Result())

    status = system_health._windows_autostart_status()

    assert status["status"] == "ready"
    assert status["credential_configured"] is True
    assert status["last_startup_status"] == "success"
    assert "token" not in status
    assert status["next_action"] is None
