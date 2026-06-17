"""Human-readable data provider status messages."""

from __future__ import annotations


def provider_status_message(mode: str, configured: bool) -> str:
    if mode == "fmp" and configured:
        return "FMP 무료 API 프로바이더가 설정되었습니다. 무료 플랜에서 막히는 가격/재무 엔드포인트는 합성 숫자 없이 경고만 표시하고, 가능하면 KIS 현재가를 보조로 사용합니다."
    if mode == "fmp":
        return "FMP 모드가 선택되었지만 FMP_API_KEY가 없어 실제 데이터 자동 주입을 중단합니다."
    if mode == "kis" and configured:
        return "KIS 해외주식 현재가 프로바이더가 활성화되었습니다. FMP 유료 엔드포인트는 호출하지 않습니다."
    if mode == "kis":
        return "KIS 모드가 선택되었지만 KIS_APP_KEY/KIS_APP_SECRET 또는 접근 토큰이 없어 현재가 자동 주입을 중단합니다."
    return "Mock 데이터 프로바이더가 활성화되어 있습니다."


def external_provider_status_message(label: str, configured: bool) -> str:
    if configured:
        return f"{label} 프로바이더가 설정되었습니다."
    return f"{label} API 키가 없어 해당 보강 데이터를 건너뜁니다."


def kis_status_message(client: object) -> str:
    app_key = getattr(client, "app_key", None)
    app_secret = getattr(client, "app_secret", None)
    if getattr(client, "uses_external_token", False):
        return "KIS 해외주식 현재가 프로바이더가 기존 접근 토큰 재사용 모드로 설정되었습니다. tokenP 신규 발급을 호출하지 않습니다."
    if getattr(client, "can_issue_token", False):
        return "KIS 해외주식 현재가 프로바이더가 tokenP 발급 허용 모드로 설정되었습니다."
    if app_key and app_key != "********" and app_secret and app_secret != "********":
        return "KIS 키는 있으나 tokenP 신규 발급이 비활성화되어 있습니다. 자동매매 보호를 위해 KIS_ACCESS_TOKEN 또는 KIS_ACCESS_TOKEN_FILE을 설정하세요."
    return "KIS_APP_KEY/KIS_APP_SECRET 또는 기존 접근 토큰이 없어 KIS 해외주식 현재가 대체 조회를 건너뜁니다."