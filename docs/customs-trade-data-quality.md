# 관세청 수출입 데이터 품질 운영 노트

관세청 수출입 연동은 투자 신호로 쓰기 전에 데이터 품질을 먼저 확인합니다. 빈 응답이나 서비스 상태 메시지는 정상 수출입 데이터로 저장하지 않습니다.

## API 구분

| 용도 | 설정 | 기본 URL | 저장 여부 |
|---|---|---|---|
| 품목·국가별 수출입 실적 | `CUSTOMS_TRADE_API_URL` | `https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList` | 실제 수치 행이 있을 때만 `research_vault\CUSTOMS` 저장 |
| 수출입총괄/잠정 동향 진단 | `CUSTOMS_TRADE_TOTAL_API_URL` | `https://apis.data.go.kr/1220000/Newtrade/getNewtradeList` | 진단 전용. 저장하지 않음 |

총괄 API 문서 설정은 `CUSTOMS_TRADE_TOTAL_DOCS_URL`이며 기본값은 `https://www.data.go.kr/data/15102108/openapi.do`입니다.

## 저장 차단 기준

품목별 API가 HTTP 200 또는 정상서비스 메시지를 반환해도, 아래 값이 없는 행은 투자 데이터로 보지 않습니다.

- 기간, HS 코드, 품목명, 국가코드, 국가명 같은 식별자
- 수출액, 수입액, 무역수지, 수출중량, 수입중량 같은 수치

유효 행이 0개이면 응답은 `warning`, `data_quality: no_valid_trade_rows`, `storage_skipped: true`가 됩니다. 이 경우 `research_vault\CUSTOMS`와 RAG에는 새 문서를 만들지 않습니다.

## 403 처리

`CUSTOMS_TRADE_TOTAL_API_URL` 호출이 403을 반환하면 키 값이 비어 있다는 뜻이 아니라, data.go.kr의 해당 서비스 활용 신청/승인 또는 키 권한이 맞지 않을 가능성이 큽니다.

확인 순서:

1. data.go.kr에서 `관세청_수출입총괄(GW)` 활용 신청 상태 확인
2. 승인된 인증키가 `CUSTOMS_TRADE_API_KEY`와 같은 키인지 확인
3. 백엔드 재시작 후 `/api/v1/macro/customs-trade/total-trend/status` 호출

진단 API는 저장하지 않는 라우트입니다. 응답에 `storage_policy`가 포함되고 `storage` 필드는 없어야 합니다.

## 운영 확인 명령

```powershell
cd C:\Users\lib20\InvestmentJournalApp
$headers = @{ Authorization = 'Bearer dev-local-token' }
Invoke-RestMethod -Headers $headers -Uri 'http://127.0.0.1:8001/api/v1/macro/customs-trade/latest?start_yymm=202605&end_yymm=202605&save_result=true'
Invoke-RestMethod -Headers $headers -Uri 'http://127.0.0.1:8001/api/v1/macro/customs-trade/total-trend/status?start_yymm=202605&end_yymm=202605'
```

`latest` 호출에서 빈 응답이면 `storage_skipped: true`가 보여야 하고, `total-trend/status`는 권한/HTTP 상태를 보여주되 파일을 만들면 안 됩니다.

같은 확인을 한 번에 실행하려면 아래 스크립트를 사용합니다.

```powershell
.\tools\check_customs_trade_quality.ps1 -StartYymm 202605 -EndYymm 202605
```

이 스크립트는 `CUSTOMS` 파일 수 불변, 빈 응답 저장 차단, 총괄 진단의 비저장 계약, `next_action` 표시 여부를 함께 확인합니다. 점검 전후 `CUSTOMS` 폴더 존재 여부도 `CustomsDirExistsBefore`, `CustomsDirExistsAfter`로 출력하며, `CustomsDirCreatedDuringCheck`, `CustomsFileCountChanged`가 모두 `false`여야 점검 중 저장소가 오염되지 않은 상태입니다. 폴더가 없던 환경에서 점검 중 새 폴더가 생기면 실패합니다.

총괄 API가 실제 승인 완료 상태인지까지 운영 게이트로 걸고 싶으면 `-RequireTotalTrendAuthorized`를 붙입니다. 현재 총괄 API가 403이면 이 명령은 의도적으로 실패합니다.

```powershell
.\tools\check_customs_trade_quality.ps1 -StartYymm 202605 -EndYymm 202605 -RequireTotalTrendAuthorized
```

통합 검증에 포함하려면 아래처럼 백엔드 주소와 기간을 함께 지정할 수 있습니다.

```powershell
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -CustomsBaseUrl http://127.0.0.1:8001 -CustomsStartYymm 202605 -CustomsEndYymm 202605
```

개발 토큰을 바꾼 환경에서는 `-CustomsDevUserToken`을 함께 지정합니다.

```powershell
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -CustomsBaseUrl http://127.0.0.1:8001 -CustomsDevUserToken dev-local-token -CustomsStartYymm 202605 -CustomsEndYymm 202605
```

총괄 API 승인 완료까지 통합 검증 조건에 포함하려면 아래 스위치를 추가합니다. data.go.kr 승인 전에는 403 상태를 숨기지 않고 실패로 표시합니다.

```powershell
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -RequireCustomsTotalTrendAuthorized -CustomsBaseUrl http://127.0.0.1:8001 -CustomsDevUserToken dev-local-token -CustomsStartYymm 202605 -CustomsEndYymm 202605
```

## 회귀 테스트

```powershell
python -m unittest tests.test_backend_regressions.CustomsTradeDataQualityTests
python -m unittest tests.test_backend_regressions
```

관세청 전용 테스트는 서비스 상태 메시지 필터링, 빈 데이터 저장 차단, 총괄 API 403 진단, 일일 참고자료 경고 전파, 진단 라우트의 비저장 계약을 확인합니다.
