# 자격증명 관리 정책

투자 리서치 OS는 로컬 개발 기준으로 API 키와 접근 토큰을 코드에 저장하지 않습니다. 실제 값은 Git에 올라가지 않는 `.env` 파일이나 무시된 토큰 캐시 파일에만 둡니다.

## 저장 위치

- 백엔드 API 키: `backend\.env`
- 모바일/프론트 개발 설정: `mobile_app\.env`, `apps\mobile\.env`
- KIS 접근 토큰 캐시 기본값: `research_vault\_system\kis_access_token.json`
- 리서치 저장소와 토큰 캐시는 `research_vault\` 아래에 두는 것을 기본으로 합니다.

`.gitignore`는 `.env`, `research_vault\`, 로컬 DB, 키 파일, 토큰 JSON을 제외합니다. 예시 파일인 `.env.example`만 Git에 보관합니다.

## 넣어도 되는 값과 안 되는 값

백엔드 `.env`에만 둬야 하는 값:

- `KIWOOM_API_KEY`, `KIWOOM_API_SECRET`
- `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCESS_TOKEN`, `KIS_ACCESS_TOKEN_FILE`
- `DART_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `ALPHA_VANTAGE_API_KEY`
- `TAVILY_API_KEY`, `BRAVE_API_KEY`, `NPS_ODCLOUD_API_KEY`, `CUSTOMS_TRADE_API_KEY`
- `KCIF_USERNAME`, `KCIF_PASSWORD`
- `SECRET_SALT`

관세청 수출입은 같은 공공데이터 키를 쓰더라도 서비스별 활용 신청/승인이 다를 수 있습니다. `CUSTOMS_TRADE_API_URL`은 품목·국가별 실적용이고, `CUSTOMS_TRADE_TOTAL_API_URL`은 1일·11일·21일 잠정/총괄 수출입동향 확인용입니다. 총괄 API가 403을 반환하면 키 값 문제가 아니라 data.go.kr의 해당 서비스 권한 상태를 먼저 확인합니다.

프론트 `.env`에 넣을 수 있는 값:

- `EXPO_PUBLIC_API_BASE_URL`
- 개발 환경에서만 쓰는 `EXPO_PUBLIC_DEV_USER_TOKEN`

`EXPO_PUBLIC_*` 값은 앱 번들에 포함될 수 있으므로 증권사 키, 외부 데이터 API 키, 계좌 토큰, 개인 식별용 secret을 넣으면 안 됩니다.

## KIS 토큰 원칙

`KIS_ALLOW_TOKEN_ISSUE=false`가 기본값입니다. 자동매매나 다른 시스템과 충돌하지 않도록 tokenP 신규 발급은 기본적으로 막고, 기존 접근 토큰 또는 무시된 토큰 파일을 우선 재사용합니다.

권장 설정:

```dotenv
KIS_ALLOW_TOKEN_ISSUE=false
KIS_ACCESS_TOKEN=
KIS_ACCESS_TOKEN_FILE=
KIS_TOKEN_CACHE_FILE=../research_vault/_system/kis_access_token.json
```

## KCIF 계정 원칙

KCIF ID와 비밀번호는 `backend\.env`에만 둡니다. 채팅, 프론트 `.env`, `.env.example`, 테스트 코드에는 실제 값을 넣지 않습니다.

권장 설정:

```dotenv
KCIF_USE_LOGIN=true
KCIF_USERNAME=
KCIF_PASSWORD=
KCIF_REPORT_LIST_URL=https://www.kcif.or.kr/annual/reportList
KCIF_LOGIN_PROC_URL=https://www.kcif.or.kr/webUser/loginProc
```

KCIF 연동은 로그인 세션으로 볼 수 있는 상세 화면을 활용하되, 보고서 PDF나 전문 원문은 자동 다운로드/저장하지 않습니다. 저장되는 것은 제목, 분류, 날짜, 링크, 파일명, 관련 테마, 수치 신호, 자체 파생 메모입니다.

## 상태 확인

`GET /api/v1/config/safety`는 실제 키 값을 반환하지 않습니다. 응답에는 마스킹된 값, 설정 여부, 그리고 `credential_policy`만 포함됩니다.

확인할 항목:

- `secrets_are_masked: true`
- `credential_policy.gitignore_required: true`
- `credential_policy.configured_secrets`는 true/false만 표시
- `credential_policy.token_cache.kis_allow_token_issue`가 의도한 값인지 확인

## 새 키를 추가할 때 체크리스트

1. `backend\research_os\settings.py`에서 환경변수로만 읽는다.
2. 실제 값은 `.env.example`에 넣지 않고 빈 값 또는 `********`로 둔다.
3. 상태 API에는 `mask_secret()` 또는 true/false 설정 여부만 노출한다.
4. 프론트 코드와 `EXPO_PUBLIC_*`에는 secret을 넣지 않는다.
5. 캐시 파일이 필요하면 `research_vault\_system\`처럼 Git 무시 경로를 사용한다.
6. 테스트에 실제 키를 넣지 않는다.
