param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp"
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

$contracts = @(
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
      'Start-Process',
      '-WindowStyle Hidden',
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
      '포트폴리오 저장 파일 오프라인 확인',
      '[switch]$CheckStorageQualitySafeguards',
      '[switch]$CheckSourceAutomationStatus',
      '[switch]$CheckSourceAutomationStore',
      'check_research_source_store.py',
      '리서치 소스 저장 파일 오프라인 확인',
      '[switch]$CheckDailyRecommendations',
      '[switch]$CheckDailyRecommendationStore',
      'check_daily_recommendations_store.py',
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
      'check_portfolio_store.py',
      'check_research_source_store.py',
      'check_backend_module_health.py',
      'check_console_static_contract.py',
      'check_storage_quality_store.py',
      'check_daily_recommendations_store.py',
      '오프라인 운영 점검 통과'
    )
  },



  @{
    Path = "tools\check_console_static_contract.py"
    Snippets = @(
      'REQUIRED_IDS',
      'REQUIRED_TABS',
      'selector_ids',
      '클래식 콘솔 정적 계약 정상'
    )
  },
  @{
    Path = "tools\check_backend_module_health.py"
    Snippets = @(
      'EXPECTED_MODULES',
      'EXPECTED_MAIN_IMPORTS',
      'BANNED_TERMS',
      '백엔드 모듈 상태 정상'
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
      '포트폴리오 저장 수량 상태 정상'
    )
  },
  @{
    Path = "tools\check_research_source_store.py"
    Snippets = @(
      'SYSTEM_DIR',
      'ticker_registry_source_status.json',
      '--strict',
      '리서치 소스 저장 상태 정상'
    )
  },
  @{
    Path = "tools\check_daily_recommendations_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'EXPECTED_MILESTONES',
      '--require-milestones',
      '--require-quality',
      '점수 설명 누락',
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

  $content = Get-Content -LiteralPath $path -Raw
  foreach ($snippet in $contract.Snippets) {
    if (-not $content.Contains($snippet)) {
      $missing += "$($contract.Path): $snippet"
    }
  }

  if ($contract.Path.EndsWith(".ps1")) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
      $path,
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
