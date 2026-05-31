param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp"
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

$contracts = @(
  @{
    Path = "scripts\start-research-backend.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'research_os_main.py',
      'research_os_main:app',
      'Resolve-BackendPython',
      '-PythonExe',
      'Get-Command netstat',
      '-StopExistingPortProcess'
    )
  },
  @{
    Path = "tools\start_backend.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$StopExistingPortProcess',
      '$ForceExistingPortProcess',
      'Assert-PortAvailable',
      'show_dev_server_ports.ps1',
      'fallback 포트를 사용하세요',
      '강제 taskkill은 실행하지 않았습니다'
    )
  },
  @{
    Path = "tools\start_mobile_web.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$StopExistingPortProcess',
      '$ForceExistingPortProcess',
      '$env:EXPO_PUBLIC_API_BASE_URL',
      'show_dev_server_ports.ps1',
      '강제 taskkill은 실행하지 않았습니다',
      'npx @expoArgs'
    )
  },
  @{
    Path = "tools\restart_backend_verified.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'stop_dev_servers.ps1',
      'Invoke-CimMethod',
      'Win32_Process',
      '$FallbackPorts',
      'UsedFallback',
      'ConvertTo-Json',
      '/api/v1/manual-transactions/import.csv/template',
      'manual-transactions-template.csv',
      'CSV 템플릿 API 응답 검증에 실패했습니다.'
    )
  },
  @{
    Path = "tools\status_dev_servers.ps1"
    Snippets = @(
      '[switch]$Strict',
      '[switch]$RequirePortfolio',
      '$FallbackApiPorts',
      'Get-PortOwningProcessIds',
      'API fallback',
      'Invoke-BackendStatusCheck',
      '정상 fallback API 사용',
      '$apiBaseUrlExplicit',
      'manual CSV template',
      '/api/v1/manual-transactions/import.csv/template',
      '선택 건너뜀',
      '상태 점검 실패'
    )
  },
  @{
    Path = "tools\status_research_console.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/system/health',
      '/api/v1/data-providers/status',
      '/api/v1/ocr/status',
      '/api/v1/storage/quality-dashboard',
      '/console/index.html',
      'OneDrive 제외',
      '저장 데이터 본문 누락',
      '연구 콘솔 상태 점검 통과',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\smoke_mobile_web.ps1"
    Snippets = @(
      '$FallbackApiPorts',
      '$RequirePortfolio',
      'Invoke-BackendSmoke',
      'fallback API 확인',
      'OK fallback API smoke',
      'Invoke-RequiredText',
      '/api/v1/manual-transactions/import.csv/template',
      'CSV 템플릿 API만 404라면 오래된 백엔드가 8010 포트를 잡고 있을 수 있습니다.',
      'start_backend.ps1 -StopExistingPortProcess'
    )
  },
  @{
    Path = "tools\smoke_kiwoom_history_live.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$ConfirmLiveApi',
      '$CheckTokenFirst',
      '$NoCancelOnTimeout',
      '$FallbackApiPorts',
      'TradeDate는 YYYY-MM-DD 또는 YYYYMMDD 형식',
      '실행하려면 명시적으로 -ConfirmLiveApi',
      '/api/v1/brokerage/status',
      '/api/v1/brokerage/kiwoom/token-test',
      '/api/v1/sync/kiwoom/history/start',
      '/api/v1/sync/kiwoom/history/jobs/$jobId',
      '/api/v1/sync/kiwoom/history/jobs/$jobId/cancel',
      '/api/v1/journal/drafts?page=1&page_size=1',
      '토큰 원문과 계좌번호',
      'ConvertTo-Json'
    )
  },
  @{
    Path = "tools\smoke_kiwoom_history_range_live.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$ConfirmLiveApi',
      '$CheckTokenFirst',
      '$NoCancelOnTimeout',
      '$FallbackApiPorts',
      '$MaxRangeDays',
      'StartDate/EndDate는 YYYY-MM-DD 또는 YYYYMMDD 형식',
      '실행하려면 명시적으로 -ConfirmLiveApi',
      '최대 $MaxRangeDays 일',
      '/api/v1/brokerage/status',
      '/api/v1/brokerage/kiwoom/token-test',
      '/api/v1/sync/kiwoom/history/start',
      '/api/v1/sync/kiwoom/history/jobs/$jobId',
      '/api/v1/sync/kiwoom/history/jobs/$jobId/cancel',
      '/api/v1/journal/drafts?page=1&page_size=1',
      '토큰 원문과 계좌번호',
      'ConvertTo-Json'
    )
  },
  @{
    Path = "tools\stop_dev_servers.ps1"
    Snippets = @(
      '[switch]$DryRun',
      '[switch]$ForceAnyProcess',
      '$AllowedProcessNames',
      'Get-Command netstat',
      'Test-CanStopProcess',
      'remainingProcessIds',
      '기본 개발 포트가 아니며 허용된 개발 프로세스가 아닙니다'
    )
  },
  @{
    Path = "tools\check_customs_trade_quality.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/macro/customs-trade/latest',
      '/api/v1/macro/customs-trade/total-trend/status',
      'LatestStorageSkipped',
      'LatestHasTotalTrendStatus',
      'TotalTrendHasStorage',
      '$RequireTotalTrendAuthorized',
      'Get-CustomsVaultFileCount',
      'CustomsDirExistsBefore',
      'CustomsDirExistsAfter',
      'CustomsDirCreatedDuringCheck',
      'CustomsFileCountChanged',
      '점검 중 CUSTOMS 폴더가 새로 생성되었습니다.',
      'next_action',
      'OutputEncoding',
      '관세청 수출입 데이터 품질 점검 실패'
    )
  },
  @{
    Path = "tools\check_portfolio_quantity_protection.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/portfolios/${encodedPortfolioName}?refresh_prices=false&persist_refresh=false',
      '[uri]::EscapeDataString($PortfolioName)',
      'active_portfolio',
      'ExpectedQuantity',
      'ExpectedCurrency',
      'manual_or_overseas_protected',
      'QuantityOk',
      'CurrencyOk',
      'SyncProtected',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\check_storage_quality_safeguards.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/storage/quality-dashboard',
      'MaxBodyMissing',
      'MaxOcrNeeded',
      'BodyMissingItemLimit',
      'BodyMissingOk',
      'BodyMissingItems',
      'BodyMissingItemDetailsOk',
      'OcrNeededOk',
      'SoftArchiveVisible',
      'CopyrightPolicyOk',
      'NextActions',
      '원문 본문은 저장하지 않고',
      '저장소 품질 안전장치 확인 완료',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\check_core_safeguards.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'check_customs_trade_quality.ps1',
      'check_portfolio_quantity_protection.ps1',
      'check_storage_quality_safeguards.ps1',
      'CustomsStartYymm',
      'PortfolioExpectedQuantity',
      'PortfolioExpectedHoldings',
      'MaxBodyMissing',
      'LatestStorageSkipped',
      'SyncProtected',
      'CheckedCount',
      'FailedCount',
      'Items',
      'BodyMissingItems',
      'NewsBodyStoragePolicy',
      'NextActions',
      '핵심 안전장치 확인 완료',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\verify_research_console.ps1"
    Snippets = @(
      '[switch]$CheckCoreSafeguards',
      '[switch]$CheckCustomsTradeQuality',
      '[switch]$CheckPortfolioQuantityProtection',
      '[switch]$CheckPortfolioStore',
      'check_portfolio_store.py',
      'check_all_portfolio_store.py',
      '포트폴리오 저장 파일 오프라인 확인',
      '전체 포트폴리오 저장 구조 확인',
      '[switch]$CheckStorageQualitySafeguards',
      '[switch]$CheckSourceAutomationStatus',
      '[switch]$CheckSourceAutomationStore',
      'check_research_source_store.py',
      '리서치 소스 저장 파일 오프라인 확인',
      '[switch]$CheckDailyRecommendations',
      '[switch]$CheckDailyRecommendationStore',
      'check_daily_recommendations_store.py',
      'Resolve-VerifyPython',
      'Resolve-VerifyNode',
      'Convert-ToWslPath',
      'Convert-ToolArgsForWsl',
      '일일 추천 저장 파일 오프라인 확인',
      '$CustomsBaseUrl',
      '$CustomsDevUserToken',
      '$CustomsStartYymm',
      '$CustomsEndYymm',
      '$RequireCustomsTotalTrendAuthorized',
      '$PortfolioQuantityBaseUrl',
      '$PortfolioQuantityName',
      '$PortfolioQuantityTicker',
      '$PortfolioQuantityExpected',
      '$PortfolioQuantityExpectedHoldings',
      '$StorageQualityBaseUrl',
      '$StorageQualityMaxBodyMissing',
      '$StorageQualityMaxOcrNeeded',
      'check_customs_trade_quality.ps1',
      'check_portfolio_quantity_protection.ps1',
      'check_storage_quality_safeguards.ps1',
      'check_core_safeguards.ps1',
      '핵심 안전장치 묶음 확인',
      '-BaseUrl $CustomsBaseUrl',
      '-DevUserToken $CustomsDevUserToken',
      '-RequireTotalTrendAuthorized:$RequireCustomsTotalTrendAuthorized',
      '$LASTEXITCODE',
      'ConvertFrom-Json',
      'CustomsDirExistsBefore',
      'CustomsDirExistsAfter',
      'CustomsDirCreatedDuringCheck',
      'CustomsFileCountChanged',
      'LatestStorageSkipped',
      'TotalTrendHttpStatusCode',
      'TotalTrendHasStorage',
      '포트폴리오 수량 보호 확인',
      'SyncProtected',
      '저장소 품질 안전장치 확인',
      'NewsBodyStoragePolicy',
      '본문 보강 대상='
    )
  },
  @{
    Path = "tools\smoke_research_console_clicks.py"
    Snippets = @(
      '--only-system-check',
      'system check completion',
      '전체 시스템 점검 완료',
      '네이버 리서치/시장일지 상태'
    )
  },




  @{
    Path = "tools\check_offline_readiness.py"
    Snippets = @(
      'CHECKS',
      'check_git_sync_status.py',
      'check_public_repo_safety.py',
      'check_backend_runtime_env.py',
      'check_portfolio_analysis_coverage.py',
      '--all-portfolios',
      '--min-average-completion',
      '포트폴리오 분석 커버리지',
      'check_portfolio_store.py',
      'check_all_portfolio_store.py',
      '전체 포트폴리오 저장 구조',
      '--expected-holdings-count',
      'check_research_source_store.py',
      'check_backend_module_health.py',
      'check_operational_readiness_score.py',
      '운영 완성도 95%',
      'check_console_static_contract.py',
      'check_console_asset_and_js.py',
      'check_storage_quality_store.py',
      'check_llm_bridge_store.py',
      'check_daily_recommendations_store.py',
      'LLM/RAG 저장 상태',
      '오프라인 운영 점검 통과'
    )
  },





  @{
    Path = "tools\check_operational_readiness_score.py"
    Snippets = @(
      '운영 완성도 점수',
      '--min-score',
      'daily_recommendations_state.json',
      'code_knowledge_graph.json',
      'user_portfolios.json',
      'research_automation_status.json',
      '운영 완성도 점검 정상'
    )
  },





  @{
    Path = "tools\check_portfolio_analysis_coverage.py"
    Snippets = @(
      '포트폴리오 분석 모듈 커버리지',
      '--write-backlog',
      '--all-portfolios',
      'unique_holdings_from_portfolios',
      'portfolio_analysis_backlog.json',
      'portfolio_analysis_module_state',
      'portfolio_analysis_next_action',
      '포트폴리오 분석 커버리지 점검 정상'
    )
  },


  @{
    Path = "backend\research_os\portfolio_analysis_coverage.py"
    Snippets = @(
      'REQUIRED_PORTFOLIO_ANALYSIS_MODULES',
      'team_report',
      'smart-trade-setup',
      'missing_portfolio_analysis_labels',
      'portfolio_analysis_next_action'
    )
  },


  @{
    Path = "backend\research_os\rag_memory.py"
    Snippets = @(
      'refresh_index: bool = True',
      'if refresh_index:',
      'backfill_research_memory_documents_from_manifest(vault_dir)'
    )
  },


  @{
    Path = "backend\research_os_main.py"
    Snippets = @(
      'refresh_index=False',
      'request.refresh_dossier',
      'dossier_refresh_status',
      'upsert_research_memory_document(vault_dir=vault_dir, entry=saved_entry)'
    )
  },


  @{
    Path = "mobile_app\research_console\api.js"
    Snippets = @(
      'refreshDossier = false',
      'refresh_dossier: refreshDossier'
    )
  },


  @{
    Path = "mobile_app\research_console\console.js"
    Snippets = @(
      'translateDossierRefreshStatus',
      'Dossier 갱신:'
    )
  },






  @{
    Path = "tools\check_public_repo_safety.py"
    Snippets = @(
      'FORBIDDEN_PATH_PATTERNS',
      'ALLOWED_PATHS',
      'SECRET_VALUE_PATTERNS',
      '--exclude-standard',
      '공개 후보 파일',
      '공개 저장소 안전 점검 통과'
    )
  },





  @{
    Path = "tools\check_backend_runtime_env.py"
    Snippets = @(
      'REQUIRED_DISTRIBUTIONS',
      'preferred_python',
      'installed_versions_with_python',
      '.venv',
      'python-dotenv',
      '/api/v1/system/health',
      '--strict',
      '백엔드 런타임 준비 상태 확인 완료'
    )
  },
  @{
    Path = "tools\check_git_sync_status.py"
    Snippets = @(
      'origin',
      'rev-list',
      '--strict',
      '작업트리 변경',
      'Git 동기화 엄격 점검 실패',
      '푸시 대기 커밋',
      'Git 동기화 상태 확인 완료'
    )
  },
  @{
    Path = "tools\check_console_asset_and_js.py"
    Snippets = @(
      'update_console_asset_hashes',
      'node',
      '--check',
      '클래식 콘솔 자산/JS 상태 정상'
    )
  },
  @{
    Path = "tools\check_console_static_contract.py"
    Snippets = @(
      'REQUIRED_IDS',
      'REQUIRED_TABS',
      'REQUIRED_FEEDBACK_BUTTON_IDS',
      'REQUIRED_WORKFLOW_ACTIONS',
      'REQUIRED_CSS_SNIPPETS',
      'REQUIRED_LIVE_REGIONS',
      'outputStatus',
      'aria-live',
      '실시간 피드백 aria-live 계약 누락',
      '실시간 피드백 영역',
      'FEEDBACK_TOKENS',
      'button_has_feedback',
      'workflow_actions_in_js_templates',
      'handled_workflow_actions',
      'today-research-update',
      'dashboard-refresh',
      '워크플로우 핸들러 누락',
      '필수 워크플로우 버튼 누락',
      '메뉴/버튼 레이아웃 CSS 계약 누락',
      '메뉴/버튼 레이아웃 CSS',
      '즉시 피드백/로딩 연결 누락 버튼',
      'selector_ids',
      '클래식 콘솔 정적 계약 정상'
    )
  },
  @{
    Path = "tools\check_backend_module_health.py"
    Snippets = @(
      'EXPECTED_MODULES',
      'EXPECTED_MAIN_IMPORTS',
      'research_os.brokerage',
      'research_os.data_providers',
      'research_os.file_extraction',
      'research_os.market_journal',
      'research_os.rag_memory',
      'research_os.research_memory',
      'BANNED_TERMS',
      'DEFAULT_MAIN_MAX_LINES',
      'DEFAULT_MIN_MODULE_COUNT',
      '--main-max-lines',
      '--min-module-count',
      '큰 도메인 모듈',
      '줄 수 상한 초과',
      '백엔드 모듈 상태 정상'
    )
  },
  @{
    Path = "tools\check_llm_bridge_store.py"
    Snippets = @(
      'DEFAULT_MANIFEST',
      'DEFAULT_RAG_DB',
      'PROMPT_MARKER',
      'RESPONSE_MARKER',
      '--require-active-rag',
      'LLM/RAG 저장 상태 정상',
      'RAG 연결 누락',
      '원 프롬프트 누락',
      'LLM 응답 누락'
    )
  },
  @{
    Path = "tools\check_storage_quality_store.py"
    Snippets = @(
      'BODY_TAGS',
      'OCR_MARKERS',
      '--strict',
      '오프라인 저장 품질 상태 정상'
    )
  },
  @{
    Path = "tools\check_portfolio_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'DEFAULT_EXPECTED',
      '--forbid-zero',
      '--expected-holdings-count',
      '--max-holdings',
      '보유 종목 수 불일치',
      '보유 종목 수 상한 초과',
      '--allow-cash',
      '--max-price-age-hours',
      '--max-portfolio-age-hours',
      '--max-sync-age-hours',
      '--weight-tolerance',
      '--calculation-relative-tolerance',
      '평가금액 계산 불일치',
      '해외 평가/투자금 환율 불일치',
      '수익률 계산 불일치',
      '포트폴리오 updated_at 오래됨/누락',
      '포트폴리오 비중 합계 불일치',
      '수량 동기화 확인 시각 오래됨/누락',
      '예수금/CASH 항목 혼입',
      '해외/수동 수량 보호 상태 누락',
      '포트폴리오 총액 불일치',
      '포트폴리오 저장 수량 상태 정상'
    )
  },
  @{
    Path = "tools\check_all_portfolio_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'CASH_TICKERS',
      '--forbid-zero',
      '--allow-cash',
      '--max-portfolio-age-hours',
      'holding_count 불일치',
      '중복 보유 종목',
      '수량 0 종목 잔존',
      '예수금/CASH 항목 혼입',
      '포트폴리오 총액 불일치',
      '전체 포트폴리오 저장 구조 상태 정상'
    )
  },
  @{
    Path = "tools\check_research_source_store.py"
    Snippets = @(
      'SYSTEM_DIR',
      'ticker_registry_source_status.json',
      '--min-kcif-reports',
      '--min-regional-provider-count',
      'metadata_policy_ok',
      'rows_from_mapping_or_list',
      'missing_storage_files',
      '네이버 리서치 저장 파일 누락',
      '신한 리서치 저장 파일 누락',
      '--min-naver-reports',
      '--min-shinhan-reports',
      '--min-market-journal-entries',
      '--max-naver-missing-storage',
      '--max-market-journal-attempt-age-hours',
      '--max-dossier-queue-age-hours',
      'naver_market_close_journal_state.json',
      'research_automation_status.json',
      '리서치 자동화 Dossier 갱신',
      '마감 시황 자동 시도',
      '자동 마감 시황 시장일지 출처 메타데이터 누락',
      '지역/중국/대외 소스 제공자 누락',
      '네이버 리서치',
      '신한 리서치',
      '마감 시황 시장일지',
      'CSF=',
      '리서치 소스 저장 상태 정상'
    )
  },
  @{
    Path = "tools\check_daily_recommendations_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'DEFAULT_STATE',
      'EXPECTED_MILESTONE_DAYS',
      'EXPECTED_MILESTONES',
      'EXPECTED_STATE_STATUSES',
      'LOCAL_TIMEZONE',
      'Asia/Seoul',
      'local_today',
      '--expected-latest-count',
      '--max-latest-age-days',
      '최신 추천일 오래됨',
      '추천 수 불일치',
      'validate_tracking_milestones',
      'nearest_milestone_label',
      'REQUIRED_EVIDENCE_CATEGORIES',
      'evidence_category_names',
      '근거 분산 부족',
      '목표일 불일치',
      '다음 추적',
      '--state',
      '스케줄 상태',
      '마지막 실행일 불일치',
      '--require-milestones',
      '--require-quality',
      '점수 설명 누락',
      '기준가 조회일 불일치 또는 누락',
      '최신 추천 티커 중복',
      '해외 종목 환율 추적 플래그 누락',
      '매일 추천 저장 상태 정상'
    )
  },
  @{
    Path = "tools\verify_mobile_stack.ps1"
    Snippets = @(
      '$SkipPortRegistryCheck',
      '예약 포트 레지스트리 점검',
      'show_dev_server_ports.ps1',
      '-OnlyConflicts',
      '$LASTEXITCODE',
      'npm run typecheck',
      '$global:LASTEXITCODE = 0',
      'assert_mobile_testids.ps1',
      'assert_dev_scripts_contract.ps1',
      'npx expo export',
      'Remove-SafeDirectory'
    )
  }
)

$missing = @()
foreach ($contract in $contracts) {
  $path = Join-Path $ProjectRootPath $contract.Path
  if (-not (Test-Path -LiteralPath $path)) {
    $missing += "$($contract.Path): 파일 없음"
    continue
  }

  $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
  foreach ($snippet in $contract.Snippets) {
    if (-not $content.Contains($snippet)) {
      $missing += "$($contract.Path): $snippet"
    }
  }

  if ($contract.Path.EndsWith(".ps1")) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseInput(
      $content,
      [ref]$tokens,
      [ref]$parseErrors
    ) | Out-Null
    foreach ($parseError in @($parseErrors)) {
      $missing += "$($contract.Path): PowerShell syntax - $($parseError.Message)"
    }
  }
}

if ($missing.Count -gt 0) {
  $message = "개발 스크립트 계약 검증 실패:`n" + ($missing -join "`n")
  throw $message
}

Write-Host "OK 개발 스크립트 계약 검증 통과"
