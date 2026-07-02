# 테스트 가이드

이 프로젝트는 문법 검사만으로 회귀를 막기 어렵기 때문에, 빠르게 돌릴 수 있는 표준 검증 명령을 분리해 둡니다.

## 백엔드 회귀 테스트

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

현재 백엔드 테스트는 외부 API나 실제 개인 데이터에 의존하지 않고 다음 경계를 확인합니다.

- 웹 본문 추출 표시 헬퍼가 URL, 언어, 번역 상태, 본문 보강 안내를 보존하는지
- Tesseract 미설치 상태의 이미지 업로드가 중단되지 않고 명확한 OCR 경고와 메타데이터를 남기는지
- 레거시 리서치 자료 정책이 하드 삭제가 아닌 소프트 보관을 기본으로 하는지
- 포트폴리오 기간 수익 비교가 재계산/캐시 정책과 해외 가격 히스토리 한계를 결과에 표시하는지
- 설정/상태 API가 실제 secret 대신 마스킹 값과 설정 여부만 노출하는지
- DART 공시 일일 감시 대상이 보유종목과 관심종목에서 함께 산출되는지
- 관세청 수출입 빈 응답이 저장/RAG에 들어가지 않고, 수출입총괄 403 진단이 비저장 경고로 표시되는지
- 분리된 백엔드 도메인 모듈(`source_url_preview`, `portfolio_import`, `portfolio_sync`, `storage_quality`, `system_health`, `portfolio_performance`, `kcif_reports` 등)이 웹 미리보기, 포트폴리오 수량 보호, 소프트 보관, OCR 품질 판정, 연구 콘솔/데이터 프로바이더 상태 점검, 리포트/성능 계산 경계를 유지하는지

백엔드 모듈 분리 경계만 빠르게 확인하려면 아래 전용 테스트를 사용합니다.

```powershell
python -m unittest tests.test_backend_regressions.BackendModuleBoundaryTests
```

## 백엔드 문법/모듈 경계 검사

```powershell
python tools\check_backend_module_health.py --strict
python -m py_compile backend\research_os_main.py backend\research_os\*.py
```

`check_backend_module_health.py --strict`는 `research_os_main.py`와 분리된 `backend\research_os` 모듈 전체의 Python 파싱, 메인 파일 줄 수 상한, 핵심 분리 모듈 파일 존재, `research_os_main.py` import 연결을 함께 확인합니다. 모듈이 늘어날 때는 긴 `py_compile` 파일 목록을 손으로 갱신하기보다 이 가드의 `EXPECTED_MODULES`와 `EXPECTED_MAIN_IMPORTS`를 먼저 갱신합니다.

관세청 수출입 데이터 품질만 빠르게 확인하려면 아래 전용 테스트를 사용합니다.

```powershell
python -m unittest tests.test_backend_regressions.CustomsTradeDataQualityTests
```

실행 중인 연구 OS 백엔드에서 저장 오염 여부까지 확인하려면 아래 라이브 점검을 사용합니다.

```powershell
.\tools\check_customs_trade_quality.ps1 -StartYymm 202605 -EndYymm 202605
```

빈 관세청 응답 점검 결과는 `CustomsDirCreatedDuringCheck=false`, `CustomsFileCountChanged=false`, `LatestStorageSkipped=true`, `TotalTrendHasStorage=false`를 보여야 합니다. 즉, 빈 관세청 응답은 저장/RAG에 들어가지 않고, 총괄 진단 라우트도 파일을 만들지 않아야 합니다. 실제 수출입 행이 있는 운영 점검에서는 `LatestSavedValidRows=true`이고 저장 파일이 늘어날 수 있으며, 이때는 `CustomsFileCountChangeAllowed=true`가 함께 표시되어야 정상입니다.

data.go.kr의 `관세청_수출입총괄(GW)` 활용 승인이 끝난 뒤에는 아래처럼 승인 상태까지 강제 검증합니다. 승인 전 403 상태에서는 실패하는 것이 정상입니다.

```powershell
.\tools\check_customs_trade_quality.ps1 -StartYymm 202605 -EndYymm 202605 -RequireTotalTrendAuthorized
```

## 기존 콘솔 검증

```powershell
python tools\update_console_asset_hashes.py --check
node --check mobile_app\research_console\console.js
```

실제 버튼 클릭까지 포함해 운영 중인 Classic Research Console을 확인하려면 백엔드 `8001`을 먼저 실행한 뒤 아래 통합 검증을 사용합니다.

```powershell
.\tools\status_research_console.ps1 -Strict
.\tools\check_core_safeguards.ps1 -Strict
.\tools\check_portfolio_quantity_protection.ps1 -Strict
.\tools\check_storage_quality_safeguards.ps1 -Strict
.\tools\run_daily_research_operations.ps1
.\tools\verify_research_console.ps1
.\tools\verify_research_console.ps1 -SkipLiveSmoke
.\tools\verify_research_console.ps1 -SkipWriteSmoke
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckFeedbackSmoke
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCoreSafeguards
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckPortfolioQuantityProtection
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckPortfolioStore
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckNpsDomesticEquityAllocation
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckStorageQualitySafeguards
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckSourceAutomationStore
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckDailyRecommendationStore
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -CustomsStartYymm 202605 -CustomsEndYymm 202605
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -CustomsBaseUrl http://127.0.0.1:8001 -CustomsStartYymm 202605 -CustomsEndYymm 202605
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -CustomsBaseUrl http://127.0.0.1:8001 -CustomsDevUserToken dev-local-token -CustomsStartYymm 202605 -CustomsEndYymm 202605
.\tools\verify_research_console.ps1 -SkipLiveSmoke -CheckCustomsTradeQuality -RequireCustomsTotalTrendAuthorized -CustomsBaseUrl http://127.0.0.1:8001 -CustomsDevUserToken dev-local-token -CustomsStartYymm 202605 -CustomsEndYymm 202605
```

통합 검증의 관세청 요약은 `DirCreated`, `FilesChanged`, `FileChangeAllowed`, `LatestStorageSkipped`, `LatestSavedValidRows`, `TotalTrendHasStorage`를 한 줄로 보여줍니다. 빈 응답 방어에서는 파일 변경이 없어야 하고, 실제 수출입 행 저장에서는 파일 변경이 `FileChangeAllowed=True`로 설명되어야 합니다.

라이브 스모크는 메뉴 17개, 대시보드 바로가기, 매크로/복리성장주, 포트폴리오 기간수익/PL 수량 보존, 네이버 리서치 상태, 저장/삭제 액션, `오늘 한국/미국 추천 1~3위`, `추천 추적 상태`, LLM/RAG 저장 상태를 확인합니다. `-CheckFeedbackSmoke`는 빠른 검증에서도 메뉴/대시보드 클릭 후 `요청 접수`, `처리 중`, `완료` 같은 사용자 피드백이 실제로 표시되는지 확인합니다. 정적 계약은 메뉴/대시보드 버튼이 긴 한국어 문구에서 잘리지 않도록 CSS 줄바꿈·최소폭 규칙을 확인하고, HTML과 JS 템플릿에 있는 `data-workflow-action` 버튼이 실제 워크플로우 핸들러와 연결되어 있는지도 함께 확인합니다. 또한 상단 액션 피드백과 추천 카드의 `aria-live` 영역, HTML/JS 템플릿 버튼의 명시적 `type` 계약을 강제해, 클릭 후 메시지가 보이지 않거나 폼 submit으로 흐르는 회귀를 백엔드 없이 잡습니다. 저장 액션 검증은 `QA-TEST-*` 데이터만 만들고 종료 시 정리합니다.

전체 클릭 스모크는 실제 브라우저 DevTools 명령을 오래 유지하므로 300초 이상 걸릴 수 있습니다. 수동 실행은 아래처럼 하고, 외부 실행 래퍼나 CI 타임아웃은 600초 이상으로 둡니다.

```powershell
python tools\smoke_research_console_clicks.py --url http://127.0.0.1:8001/console/index.html?smoke=clicks --progress --progress-heartbeat-seconds 30
python tools\smoke_research_console_clicks.py --list-stages
python tools\smoke_research_console_clicks.py --only-public-ir-sec --progress --progress-heartbeat-seconds 20
```

부분 실행은 `--list-stages`로 가능한 체크포인트를 확인한 뒤 `--stop-after <stage>`를 붙여 사용합니다. Firecrawl IR Hosted Dry-run 버튼과 공개 IR/SEC 입력 피드백만 빠르게 확인할 때는 `--only-public-ir-sec`를 사용합니다. 장시간 full smoke는 `--progress-heartbeat-seconds`로 브라우저 응답 대기 heartbeat 간격을 조절할 수 있습니다.

`verify_research_console.ps1`에서 라이브 클릭 스모크를 같이 돌릴 때도 같은 부분 실행 옵션을 전달할 수 있습니다.

```powershell
.\tools\verify_research_console.ps1 -ClickSmokeProgress -ClickSmokeStopAfter portfolio
.\tools\verify_research_console.ps1 -SkipWriteSmoke -ClickSmokeOnlyPublicIrSec -ClickSmokeProgress -ClickSmokeProgressHeartbeatSeconds 20
```


Windows PowerShell에서 실제 Chrome을 이용해 메뉴/클릭 스모크를 함께 돌릴 때는 아래 래퍼를 사용합니다. WSL/Codex 격리에서 DevTools localhost 접근이 막혀도 Windows `Start-Process -Wait` 경로로 검증합니다.

```powershell
.\tools\smoke_research_console_windows.ps1 -Mode Both
```

전체 클릭 검증까지 확장하려면 `-FullClicks`를 추가합니다.

```powershell
.\tools\smoke_research_console_windows.ps1 -Mode Clicks -FullClicks
```

백엔드가 꺼져 있어도 포트폴리오 수량, 소스 캐시, 매일 추천 저장 원본은 파일 기반 점검으로 확인할 수 있습니다. 묶음 점검은 아래 명령을 사용합니다.

```powershell
python tools\check_offline_readiness.py
python tools\check_operational_readiness_score.py --strict --min-score 95
python tools\check_portfolio_analysis_coverage.py --all-portfolios --min-average-completion 0.95 --write-backlog --strict
python tools\check_git_sync_status.py
python tools\check_public_repo_safety.py
python tools\check_backend_runtime_env.py --check-daily-tests
python tools\check_backend_module_health.py --strict
python tools\check_console_static_contract.py --strict
python tools\check_console_asset_and_js.py
```

이 묶음 점검에는 `docs\examples\firecrawl_ir_registry.sample.json` 기반 Firecrawl IR registry 샘플 payload 검증도 포함되어, AAPL/JOBY 같은 공개 IR URL 샘플이 Market Signal Graph 입력 payload로 계속 정규화되는지 백엔드 없이 확인합니다.
Firecrawl Monitor 변화 감지는 `python tools\check_firecrawl_monitor_collector.py --input-json docs\examples\firecrawl_monitor_registry.sample.json`로 페이지/검색 target, schedule, goal, changeTracking payload를 먼저 확인합니다. 실제 `/v2/monitor` 생성 전에는 ignored secret env 파일을 만든 뒤 `--require-env-registry --require-create-ready`를 통과시켜야 합니다. 이벤트 수신 모델은 `CompanyIrSourcesWatchTests`의 Firecrawl Monitor 이벤트 정규화/저장/엔드포인트 테스트로 `monitor.page`, `monitor.check.completed`, 중복 upsert, 공개 IR/SEC 상태 연결을 확인합니다.
실전 RPC 전환 전에는 ignored secret env 파일을 만든 뒤 `.\tools\run_firecrawl_ir_rpc_preflight.ps1 -EnvFile path\to\firecrawl-rpc.env`로 `--require-rpc-ready`를 먼저 통과시키고, 실제 적재가 필요한 경우에만 `-Mode Submit`을 추가합니다.

개별 점검은 아래 명령을 사용합니다.

```powershell
python tools\check_portfolio_store.py --portfolio 이형주 --min-holdings 17 --expected-holdings-count 17 --forbid-zero
python tools\check_all_portfolio_store.py --min-holdings 1 --forbid-zero
python tools\check_storage_quality_store.py --strict
python tools\check_rag_failure_diagnostics.py --strict
python tools\check_llm_bridge_store.py --require-active-rag
```

`python tools\check_backend_runtime_env.py --check-daily-tests`는 백엔드 의존성/health 상태와 함께 일일 추천 단위 테스트를 실행합니다. `--strict`는 백엔드 의존성 버전과 `http://127.0.0.1:8001/api/v1/system/health` 응답을 강제 검증합니다. 일반 오프라인 묶음에서는 백엔드 미가동을 권고로만 보여 주고, 실제 운영 전에는 `--strict`로 확인합니다.

WSL/Codex 격리 환경에서는 8001 백엔드가 실행 중이어도 localhost 접근이 `Operation not permitted`로 보일 수 있습니다. 실제 운영 확인은 Windows PowerShell에서 `python tools\check_backend_runtime_env.py --strict`로 재확인합니다.
Windows PATH에 `python`이 없으면 `tools\verify_research_console.ps1`가 프로젝트 WSL `.venv`를 자동으로 사용합니다. 클릭 스모크가 Chrome DevTools 제한으로 막힐 때는 먼저 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckPortfolioStore`로 저장/검증 경로를 확인합니다.

```powershell
python tools\check_research_source_store.py --strict
```

`check_research_source_store.py --strict`는 네이버/신한 리서치 캐시의 저장 경로뿐 아니라 실제 Markdown/JSON 파일 존재도 확인합니다. 시장일지는 기본으로 `KR`, `US` 각각의 저장 항목과 자동 출처 항목이 있는지도 확인하며, 출력에 시장별 건수/자동 건수/최신 세션일과 경과일을 표시합니다. 특정 시장의 최신 세션일이 기본 7일을 넘기면 전체 `updated_at`이 최근이어도 실패합니다.

`check_rag_failure_diagnostics.py --strict`는 활성 리서치 문서가 저장 파일, RAG 색인, 검색 가능한 본문 길이, 자동 분류 근거까지 추천 근거로 쓰기 좋은 상태인지 백엔드 없이 확인합니다.

`check_backend_module_health.py --strict`는 모듈 분리 상태와 Python 문법뿐 아니라 `research_os_main.py`의 `SimpleNamespace` 런타임 주입값이 실제로 정의/import되어 있는지도 확인합니다. 얇은 wrapper를 제거할 때 남은 의존성 주입 참조를 이 단계에서 잡습니다.

`check_llm_bridge_store.py --require-active-rag`는 LLM 연동으로 저장한 원 프롬프트와 응답이 Markdown/JSON 원본 및 RAG 색인에 모두 연결되어 있는지 백엔드 없이 확인합니다.

`check_daily_recommendations_store.py`의 최신성 판정은 실행 서버 로컬 시간이 아니라 `Asia/Seoul` 기준 날짜를 사용합니다. 기본 실행은 저장된 전체 추천 이력도 날짜별 1·2·3위 누락, 순위 중복, 회사명/티커 중복까지 확인합니다. 최신 저장 추천이 현재 추적 피드백의 보류 정책과 충돌하면 `최신 추천 정책 이탈`로 표시합니다.

매일 추천 저장 원본과 사후 추적표만 확인하려면 아래 점검을 사용합니다.

```powershell
python tools\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 6 --max-latest-age-days 1
python tools\check_daily_recommendation_citations.py --strict
python tools\check_daily_recommendation_policy_signals.py --strict
python tools\check_daily_recommendation_candidate_policy.py --require-hold-warning --expected-held-ticker 112610
```

`check_daily_recommendation_candidate_policy.py`는 추천을 새로 저장하지 않고 현재 후보 생성 정책만 dry-run으로 평가합니다. 반복 부진 후보가 충분한 대체 후보가 있는데도 top 3에 다시 들어오면 실패합니다. 보류 전 단계지만 추적 성과가 약한 후보는 `추적 성과 약세 top3 대체` 경고로 top 3 밖 대체 여부를 표시하며, top 후보에 추적 성과 피드백이 있으면 hit rate와 감점도 함께 출력합니다.

시스템 점검 완료 여부만 빠르게 확인하려면 아래 집중 스모크를 사용합니다.

```powershell
python tools\smoke_research_console_clicks.py --only-system-check --progress --progress-heartbeat-seconds 30
```

브라우저 스모크도 WSL/Codex 격리 환경에서는 Chrome DevTools 포트 접근이 차단될 수 있으므로, 실제 화면 검증은 Windows PowerShell에서 실행합니다. Firecrawl IR Hosted Dry-run과 공개 IR/SEC 입력 피드백만 확인할 때는 Windows 래퍼에서도 클릭 스모크를 좁혀 실행할 수 있습니다.

```powershell
.\tools\smoke_research_console_windows.ps1 -Mode Clicks -PublicIrSecClicks
```

## React 콘솔 검증

```powershell
cd apps\research-console
npm run check
npm run test:portfolio
npm run test:portfolio-api
```

`npm run verify`는 위 검증과 빌드를 함께 실행합니다.
