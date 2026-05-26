from datetime import datetime
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
        "configured_secrets": {
            "kiwoom_api_key": _configured_secret(settings.brokerage_api_key),
            "kiwoom_api_secret": _configured_secret(settings.brokerage_api_secret),
            "secret_salt": _configured_secret(settings.secret_salt),
            "kis_app_key": _configured_secret(settings.kis_app_key),
            "kis_app_secret": _configured_secret(settings.kis_app_secret),
            "kis_access_token": _configured_secret(settings.kis_access_token),
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
