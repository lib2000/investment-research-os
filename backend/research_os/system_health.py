from datetime import datetime
import json
import os
import socket
import subprocess
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings, mask_secret


SYSTEM_HEALTH_CHECK_ROUTES = {
    "root": "ok",
    "openapi": "ok",
    "data_providers_status_route": "/api/v1/data-providers/status",
    "ocr_status_route": "/api/v1/ocr/status",
    "storage_quality_route": "/api/v1/storage/quality-dashboard",
}

TRADING_TOOL_SERVICES = (
    ("strategy_api", 8000, "전략 API"),
    ("strategy_builder", 3100, "전략 빌더"),
    ("backtester_api", 8002, "백테스터 API"),
    ("backtester", 3200, "백테스터"),
)


def _probe_local_service(service: tuple[str, int, str]) -> dict:
    service_id, port, label = service
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            ready = True
    except OSError:
        ready = False
    return {
        "id": service_id,
        "label": label,
        "status": "ready" if ready else "needs_attention",
        "port": port,
        "next_action": None if ready else f"{label}를 시작하세요.",
    }


def _docker_status() -> dict:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        ready = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ready = False
    return {
        "id": "docker",
        "label": "Docker",
        "status": "ready" if ready else "needs_attention",
        "next_action": None if ready else "Docker Desktop을 시작하세요.",
    }


def _lean_data_status() -> dict:
    root = Path(os.getenv("LEAN_DATA_ROOT", "D:/workspace/lean-data"))
    ready = root.exists()
    return {
        "id": "lean",
        "label": "Lean 데이터",
        "status": "ready" if ready else "needs_attention",
        "path_configured": bool(str(root)),
        "next_action": None if ready else "Lean 데이터 경로를 확인하세요.",
    }


def _kis_paper_status() -> dict:
    try:
        settings = Settings()
        configured = bool(str(settings.kis_app_key or "").strip() and str(settings.kis_app_secret or "").strip())
    except Exception:
        configured = False
    return {
        "id": "kis",
        "label": "KIS 모의투자",
        "status": "ready" if configured else "needs_auth",
        "next_action": None if configured else "KIS 모의투자 자격 증명을 설정하세요.",
    }


def _wsl_gateway_listener_ready(distro: str) -> bool:
    """Confirm the gateway is bound inside WSL, not just on a Windows port proxy."""
    probe = (
        "import socket; "
        "s=socket.socket(); s.settimeout(0.5); "
        "r=s.connect_ex(('127.0.0.1',18789)); s.close(); "
        "print(1 if r == 0 else 0)"
    )
    try:
        result = subprocess.run(
            ["wsl.exe", "-d", distro, "--user", "root", "--exec", "python3", "-c", probe],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0 and str(result.stdout).strip() == "1"
    except (OSError, subprocess.TimeoutExpired):
        return False


def _openclaw_mobile_status() -> dict:
    gateway_ready = False
    gateway_listener_source = "none"
    distro = os.getenv("OPENCLAW_WSL_DISTRO", "Ubuntu-24.04")
    try:
        with urlopen("http://127.0.0.1:18789/", timeout=1) as response:
            gateway_ready = int(getattr(response, "status", 0)) < 500
            if gateway_ready:
                gateway_listener_source = "http"
    except Exception:
        # The gateway port is a WebSocket endpoint and may close a plain HTTP
        # probe even while it is healthy. A Windows TCP listener alone is not
        # enough because portproxy can remain after the WSL gateway has died.
        try:
            with socket.create_connection(("127.0.0.1", 18789), timeout=0.35):
                gateway_ready = _wsl_gateway_listener_ready(distro)
                if gateway_ready:
                    gateway_listener_source = "wsl"
        except OSError:
            gateway_ready = False
    paired_devices = 0
    try:
        # Avoid `bash -lc` here.  On a cold WSL boot it can wait for the user
        # shell/systemd session and make the whole workbench status endpoint
        # look down.  Direct `wsl --exec` returns the same count quickly.
        wsl_user = os.getenv("OPENCLAW_WSL_USER", "lib2000")
        # The Windows backend can read the WSL UNC mount directly.  This
        # avoids starting a cold WSL VM for every status request (which can
        # take longer than the HTTP health budget) and keeps the check on the
        # OpenClaw user's home rather than the default WSL root account.
        pairing_path = Path(fr"\\wsl$\{distro}\home\{wsl_user}\.openclaw\nodes\paired.json")
        if pairing_path.exists():
            payload = json.loads(pairing_path.read_text(encoding="utf-8"))
            devices = payload.get("devices", payload) if isinstance(payload, dict) else payload
            paired_devices = len(devices) if isinstance(devices, (dict, list)) else 0
        else:
            pairing_probe = (
                "import json; from pathlib import Path; "
                f"p=Path('/home/{wsl_user}/.openclaw/nodes/paired.json'); "
                "d=json.loads(p.read_text()) if p.exists() else {}; "
                "print(len(d) if isinstance(d, dict) else 0)"
            )
            result = subprocess.run(
                ["wsl.exe", "-d", distro, "--user", "root", "--exec", "python3", "-c", pairing_probe],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0:
                try:
                    payload = json.loads(result.stdout or "{}")
                    devices = payload.get("devices", payload) if isinstance(payload, dict) else payload
                    paired_devices = len(devices) if isinstance(devices, (dict, list)) else int(str(result.stdout).strip() or 0)
                except (TypeError, ValueError, json.JSONDecodeError):
                    paired_devices = int(str(result.stdout).strip() or 0)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        paired_devices = 0
    ready = gateway_ready and paired_devices > 0
    return {
        "id": "openclaw_mobile",
        "label": "OpenClaw/iPhone",
        "status": "ready" if ready else "needs_attention",
        "gateway_ready": gateway_ready,
        "gateway_listener_source": gateway_listener_source,
        "paired_devices": paired_devices,
        "next_action": None if ready else "OpenClaw 게이트웨이와 iPhone 페어링을 확인하세요.",
    }


def _windows_autostart_status() -> dict:
    script = Path(__file__).resolve().parents[2] / "tools" / "check_investment_research_autostart.ps1"
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        payload = json.loads(result.stdout or "{}")
        if isinstance(payload, dict) and payload.get("status") in {"ready", "needs_attention"}:
            payload.pop("token", None)
            payload["id"] = "windows_autostart"
            payload["label"] = "Windows 자동 시작"
            payload.setdefault("next_action", None if payload.get("status") == "ready" else "자동 시작 작업을 확인하세요.")
            return payload
    except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError):
        pass
    return {
        "id": "windows_autostart",
        "label": "Windows 자동 시작",
        "status": "needs_attention",
        "next_action": "자동 시작 작업을 확인하세요.",
    }


def build_investment_workbench_status() -> dict:
    checks = [
        *(_probe_local_service(service) for service in TRADING_TOOL_SERVICES),
        _docker_status(),
        _lean_data_status(),
        _kis_paper_status(),
        _openclaw_mobile_status(),
        _windows_autostart_status(),
    ]
    ready_count = sum(item.get("status") == "ready" for item in checks)
    return {
        "status": "ready" if ready_count == len(checks) else "needs_attention",
        "checked_at": system_health_timestamp(),
        "ready_count": ready_count,
        "check_count": len(checks),
        "checks": checks,
        "recovery_command": 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "investment-research-os.ps1" start',
    }


def system_health_timestamp() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).replace(microsecond=0).isoformat()


def build_system_health_payload(settings: Settings, ocr_status: dict) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return {
        "status": "success",
        "module": "system_health",
        "message": "투자 리서치 OS 백엔드가 정상 응답 중입니다.",
        "server_time": system_health_timestamp(),
        "data_provider_mode": settings.data_provider_mode,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "resolved_research_vault_dir": str(vault_dir),
        "onedrive_excluded": "onedrive" not in str(vault_dir).lower(),
        "ocr_status": ocr_status.get("status"),
        "ocr_ready": bool(ocr_status.get("ready")),
        "checks": dict(SYSTEM_HEALTH_CHECK_ROUTES),
    }


def build_data_provider_status_payload(
    settings: Settings,
    ocr_status: dict,
    provider_status: dict,
) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return {
        "status": "success",
        "mode": settings.data_provider_mode,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "live_data_max_age_minutes": settings.live_data_max_age_minutes,
        "earnings_calendar_on_demand_refresh": settings.earnings_calendar_on_demand_refresh,
        "resolved_research_vault_dir": str(vault_dir),
        "onedrive_excluded": "onedrive" not in str(vault_dir).lower(),
        "ocr": ocr_status,
        "providers": provider_status,
    }


def _configured_secret(value: str | None) -> bool:
    normalized = str(value or "").strip()
    return bool(normalized and normalized != "********")


def credential_storage_policy(settings: Settings) -> dict:
    return {
        "runtime_source": "환경변수와 로컬 .env 파일은 python-dotenv로 로드합니다.",
        "local_secret_files": [
            ".env",
            "backend/.env",
            "mobile_app/.env",
            "apps/mobile/.env",
        ],
        "gitignore_required": True,
        "frontend_rule": (
            "EXPO_PUBLIC_* 값은 앱 번들에 노출될 수 있으므로 API Base URL과 개발용 토큰 외의 "
            "증권사/API 키를 넣지 않습니다."
        ),
        "backend_rule": "증권사/API 키, 접근 토큰, SECRET_SALT는 백엔드 환경변수 또는 무시된 로컬 파일에만 둡니다.",
        "token_cache": {
            "kis_allow_token_issue": settings.kis_allow_token_issue,
            "kis_access_token_file_configured": bool(settings.kis_access_token_file.strip()),
            "kis_token_cache_file": settings.kis_token_cache_file,
            "default_location": "../research_vault/_system/kis_access_token.json",
            "gitignored_by_default": True,
            "note": "KIS tokenP 신규 발급은 기본 비활성화이며, 기존 토큰 재사용 또는 무시된 캐시 파일을 우선합니다.",
        },
        "toss_read_only": {
            "enabled": settings.toss_enabled,
            "client_id_configured": _configured_secret(settings.toss_client_id),
            "client_secret_configured": _configured_secret(settings.toss_client_secret),
            "account_seq_configured": bool(settings.toss_account_seq.strip()),
            "token_cache_file": settings.toss_token_cache_file,
            "gitignored_by_default": True,
            "note": "토스증권은 보유자산 조회만 연결하며 주문·조건주문 API는 호출하지 않습니다.",
        },
        "configured_secrets": {
            "kiwoom_api_key": _configured_secret(settings.brokerage_api_key),
            "kiwoom_api_secret": _configured_secret(settings.brokerage_api_secret),
            "secret_salt": _configured_secret(settings.secret_salt),
            "kis_app_key": _configured_secret(settings.kis_app_key),
            "kis_app_secret": _configured_secret(settings.kis_app_secret),
            "kis_access_token": _configured_secret(settings.kis_access_token),
            "toss_client_id": _configured_secret(settings.toss_client_id),
            "toss_client_secret": _configured_secret(settings.toss_client_secret),
            "dart_api_key": _configured_secret(settings.dart_api_key),
            "financial_datasets_api_key": _configured_secret(settings.financial_datasets_api_key),
            "finnhub_api_key": _configured_secret(settings.finnhub_api_key),
            "tiingo_api_key": _configured_secret(settings.tiingo_api_key),
            "alpha_vantage_api_key": _configured_secret(settings.alpha_vantage_api_key),
            "tavily_api_key": _configured_secret(settings.tavily_api_key),
            "brave_api_key": _configured_secret(settings.brave_api_key),
            "nps_odcloud_api_key": _configured_secret(settings.nps_odcloud_api_key),
            "customs_trade_api_key": _configured_secret(settings.customs_trade_api_key),
        },
        "response_rule": "상태/점검 API는 실제 값을 반환하지 않고 마스킹 값 또는 설정 여부만 반환합니다.",
    }


def build_safety_config_payload(settings: Settings) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return {
        "brokerage_api_key": mask_secret(settings.brokerage_api_key),
        "brokerage_api_secret": mask_secret(settings.brokerage_api_secret),
        "kiwoom_base_url": settings.kiwoom_base_url,
        "kiwoom_mock_base_url": settings.kiwoom_mock_base_url,
        "kiwoom_use_mock": settings.kiwoom_use_mock,
        "kiwoom_registered_ip": mask_secret(settings.kiwoom_registered_ip),
        "toss_enabled": settings.toss_enabled,
        "toss_client_id": mask_secret(settings.toss_client_id),
        "toss_client_secret": mask_secret(settings.toss_client_secret),
        "toss_base_url": settings.toss_base_url,
        "toss_account_seq": mask_secret(settings.toss_account_seq),
        "toss_token_cache_file": settings.toss_token_cache_file,
        "toss_read_only": True,
        "secret_salt": mask_secret(settings.secret_salt),
        "research_vault_dir": settings.research_vault_dir,
        "resolved_research_vault_dir": str(vault_dir),
        "block_onedrive_paths": settings.block_onedrive_paths,
        "onedrive_excluded": "onedrive" not in str(vault_dir).lower(),
        "live_data_max_age_minutes": settings.live_data_max_age_minutes,
        "earnings_calendar_on_demand_refresh": settings.earnings_calendar_on_demand_refresh,
        "data_provider_mode": settings.data_provider_mode,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "fmp_api_key": mask_secret(settings.fmp_api_key),
        "fmp_base_url": settings.fmp_base_url,
        "fmp_timeout_seconds": settings.fmp_timeout_seconds,
        "dart_api_key": mask_secret(settings.dart_api_key),
        "dart_base_url": settings.dart_base_url,
        "financial_datasets_api_key": mask_secret(settings.financial_datasets_api_key),
        "finnhub_api_key": mask_secret(settings.finnhub_api_key),
        "tiingo_api_key": mask_secret(settings.tiingo_api_key),
        "alpha_vantage_api_key": mask_secret(settings.alpha_vantage_api_key),
        "tavily_api_key": mask_secret(settings.tavily_api_key),
        "brave_api_key": mask_secret(settings.brave_api_key),
        "naver_finance_enabled": settings.naver_finance_enabled,
        "naver_finance_base_url": settings.naver_finance_base_url,
        "naver_finance_timeout_seconds": settings.naver_finance_timeout_seconds,
        "nps_odcloud_enabled": settings.nps_odcloud_enabled,
        "nps_odcloud_api_key": mask_secret(settings.nps_odcloud_api_key),
        "nps_odcloud_base_url": settings.nps_odcloud_base_url,
        "nps_domestic_stock_docs_url": settings.nps_domestic_stock_docs_url,
        "nps_large_holding_docs_url": settings.nps_large_holding_docs_url,
        "nps_domestic_stock_api_url": settings.nps_domestic_stock_api_url,
        "nps_large_holding_api_url": settings.nps_large_holding_api_url,
        "customs_trade_enabled": settings.customs_trade_enabled,
        "customs_trade_api_key": mask_secret(settings.customs_trade_api_key),
        "customs_trade_api_url": settings.customs_trade_api_url,
        "customs_trade_total_api_url": settings.customs_trade_total_api_url,
        "customs_trade_total_docs_url": settings.customs_trade_total_docs_url,
        "customs_trade_release_days": settings.customs_trade_release_days,
        "credential_policy": credential_storage_policy(settings),
        "secrets_are_masked": True,
    }
