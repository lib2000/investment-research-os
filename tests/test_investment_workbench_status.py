import sys
from pathlib import Path
from types import SimpleNamespace


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


def test_trading_tool_probe_rejects_hung_listener(monkeypatch):
    monkeypatch.setattr(system_health, "_local_port_is_listening", lambda _port: True)
    monkeypatch.setattr(system_health, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError()))

    status = system_health.probe_trading_tool_service(("backtester", 3200, "백테스터", "/backtest"))

    assert status["status"] == "needs_attention"
    assert status["readiness"] == "unresponsive"
    assert status["port_open"] is True
    assert status["http_ready"] is False
    assert status["http_status"] is None


def test_trading_tool_probe_requires_successful_http_response(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(system_health, "_local_port_is_listening", lambda _port: True)
    monkeypatch.setattr(system_health, "urlopen", lambda *_args, **_kwargs: Response())

    status = system_health.probe_trading_tool_service(("strategy_builder", 3100, "전략 빌더", "/builder"))

    assert status["status"] == "ready"
    assert status["readiness"] == "ready"
    assert status["port_open"] is True
    assert status["http_ready"] is True
    assert status["http_status"] == 200


def test_console_trading_status_does_not_treat_open_port_as_running(monkeypatch):
    service_rows = [
        {
            "id": service_id,
            "label": label,
            "port": port,
            "probe_path": path,
            "port_open": True,
            "http_ready": service_id != "backtester",
            "http_status": 200 if service_id != "backtester" else None,
            "response_ms": 12,
            "status": "ready" if service_id != "backtester" else "needs_attention",
            "readiness": "ready" if service_id != "backtester" else "unresponsive",
            "next_action": None,
        }
        for service_id, port, label, path in main.TRADING_TOOL_SERVICES
    ]

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    monkeypatch.setattr(main, "probe_trading_tool_services", lambda _services: service_rows)
    monkeypatch.setattr(main.httpx, "get", lambda *_args, **_kwargs: Response())

    payload = main._trading_tool_status_payload()
    backtester = next(item for item in payload["services"] if item["id"] == "backtester")

    assert payload["all_running"] is False
    assert backtester["port_open"] is True
    assert backtester["running"] is False
    assert backtester["readiness"] == "unresponsive"


def test_console_trading_start_recovers_managed_unresponsive_service(monkeypatch, tmp_path):
    launcher = tmp_path / "investment-web.ps1"
    launcher.write_text("# fixed launcher", encoding="utf-8")
    before = {
        "all_running": False,
        "services": [{"id": "backtester", "port_open": True, "running": False}],
    }
    after = {"all_running": True, "services": [{"id": "backtester", "port_open": True, "running": True}]}
    statuses = iter((before, after))
    actions = []

    monkeypatch.setattr(main, "trading_api_root", lambda: tmp_path)
    monkeypatch.setattr(main, "_trading_tool_status_payload", lambda: next(statuses))
    monkeypatch.setattr(
        main,
        "_run_trading_tool_launcher",
        lambda _root, action, *, timeout: actions.append((action, timeout)) or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = main.start_trading_tools()

    assert payload["all_running"] is True
    assert actions == [("stop", 30), ("start", 90)]


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
        stdout = '{"mobile_count":2,"total_count":5,"store":"state_sqlite"}\n'

    monkeypatch.setattr(system_health, "urlopen", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(system_health.subprocess, "run", lambda *_args, **_kwargs: Result())

    status = system_health._openclaw_mobile_status()

    assert status["status"] == "ready"
    assert status["paired_devices"] == 2
    assert status["paired_devices_total"] == 5
    assert status["pairing_store"] == "state_sqlite"
    assert status["next_action"] is None


def test_wsl_gateway_listener_rejects_stale_windows_portproxy(monkeypatch):
    class Result:
        returncode = 0
        stdout = "0\n"

    monkeypatch.setattr(system_health.subprocess, "run", lambda *_args, **_kwargs: Result())

    assert system_health._wsl_gateway_listener_ready("Ubuntu-24.04") is False


def test_wsl_gateway_listener_accepts_real_wsl_socket(monkeypatch):
    class Result:
        returncode = 0
        stdout = "1\n"

    monkeypatch.setattr(system_health.subprocess, "run", lambda *_args, **_kwargs: Result())

    assert system_health._wsl_gateway_listener_ready("Ubuntu-24.04") is True


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


def test_windows_autostart_status_decodes_utf8_json(monkeypatch):
    observed = {}

    def fake_run(*_args, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            returncode=1,
            stdout='{"status":"needs_attention","next_action":"자동 시작 작업을 확인하세요."}\n',
            stderr="",
        )

    monkeypatch.setattr(system_health.subprocess, "run", fake_run)

    status = system_health._windows_autostart_status()

    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "replace"
    assert status["next_action"] == "자동 시작 작업을 확인하세요."


def test_windows_autostart_status_rejects_empty_json(monkeypatch):
    monkeypatch.setattr(
        system_health.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )

    status = system_health._windows_autostart_status()

    assert status["status"] == "needs_attention"
    assert status["next_action"]


def test_windows_autostart_runner_keeps_wsl_alive():
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "start-investment-research-autostart.ps1"
    ).read_text(encoding="utf-8-sig")

    assert "investment-research-wsl-keepalive" in source
    assert '$keepaliveSeconds = "2147483647"' in source
    assert '"/usr/bin/sleep $keepaliveSeconds"' in source
    assert "/usr/bin/sleep infinity" in source
    assert "--user root --exec /usr/bin/sleep" in source
    assert "--user root --exec systemctl --user --machine=$userMachine" in source
    assert 'openclaw_service_probe_mode = "root_machine_user_bus"' in source
    assert "wsl_keepalive_ready" in source
