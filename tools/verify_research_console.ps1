param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$ConsoleUrl = "http://127.0.0.1:8001/console/index.html?smoke=clicks",
  [switch]$SkipLiveSmoke,
  [switch]$SkipWriteSmoke,
  [switch]$CheckFeedbackSmoke,
  [switch]$CheckCoreSafeguards,
  [switch]$CheckCustomsTradeQuality,
  [switch]$CheckPortfolioQuantityProtection,
  [switch]$CheckStorageQualitySafeguards,
  [string]$CustomsBaseUrl = "http://127.0.0.1:8001",
  [string]$CustomsDevUserToken = "dev-local-token",
  [string]$CustomsStartYymm = "202605",
  [string]$CustomsEndYymm = "202605",
  [switch]$RequireCustomsTotalTrendAuthorized,
  [string]$PortfolioQuantityBaseUrl = "http://127.0.0.1:8001",
  [string]$PortfolioQuantityDevUserToken = "dev-local-token",
  [string]$PortfolioQuantityName = "이형주",
  [string]$PortfolioQuantityTicker = "PL",
  [double]$PortfolioQuantityExpected = 100,
  [string]$PortfolioQuantityCurrency = "USD",
  [string]$StorageQualityBaseUrl = "http://127.0.0.1:8001",
  [string]$StorageQualityDevUserToken = "dev-local-token",
  [int]$StorageQualityMaxBodyMissing = 0,
  [int]$StorageQualityMaxOcrNeeded = 0
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

function Invoke-VerifyStep {
  param(
    [string]$Name,
    [scriptblock]$Block
  )

  Write-Host ""
  Write-Host "==> $Name"
  $global:LASTEXITCODE = 0
  & $Block
  if ($LASTEXITCODE -ne 0) {
    throw "$Name 실패: 종료 코드 $LASTEXITCODE"
  }
  Write-Host "정상 $Name"
}

Set-Location -LiteralPath $ProjectRootPath

Invoke-VerifyStep "클래식 콘솔 자산 해시 확인" {
  python tools\update_console_asset_hashes.py --check | Out-Null
}

Invoke-VerifyStep "클래식 콘솔 JavaScript 문법 확인" {
  node --check mobile_app\research_console\console.js
}

Invoke-VerifyStep "리서치 OS Python 문법 확인" {
  python -m py_compile `
    backend\research_os_main.py `
    backend\research_os\customs_trade.py `
    backend\research_os\kcif_reports.py `
    backend\research_os\market_journal.py `
    backend\research_os\portfolio_import.py `
    backend\research_os\portfolio_performance.py `
    backend\research_os\portfolio_store.py `
    backend\research_os\portfolio_sync.py `
    backend\research_os\source_url_preview.py `
    backend\research_os\storage_quality.py `
    backend\research_os\system_health.py `
    tools\smoke_research_console_clicks.py `
    tools\smoke_research_console_menus.py `
    tools\smoke_research_console_write_actions.py
}

Invoke-VerifyStep "백엔드 회귀 테스트" {
  python -m unittest tests.test_backend_regressions
}

Invoke-VerifyStep "QA 쓰기 액션 정리" {
  python tools\smoke_research_console_write_actions.py --cleanup-only
}

if ($CheckCoreSafeguards) {
  Invoke-VerifyStep "핵심 안전장치 묶음 확인" {
    $coreSafeguardsJson = & (Join-Path $PSScriptRoot "check_core_safeguards.ps1") `
      -BaseUrl $CustomsBaseUrl `
      -DevUserToken $CustomsDevUserToken `
      -CustomsStartYymm $CustomsStartYymm `
      -CustomsEndYymm $CustomsEndYymm `
      -RequireCustomsTotalTrendAuthorized:$RequireCustomsTotalTrendAuthorized `
      -PortfolioName $PortfolioQuantityName `
      -PortfolioTicker $PortfolioQuantityTicker `
      -PortfolioExpectedQuantity $PortfolioQuantityExpected `
      -PortfolioExpectedCurrency $PortfolioQuantityCurrency `
      -MaxBodyMissing $StorageQualityMaxBodyMissing `
      -MaxOcrNeeded $StorageQualityMaxOcrNeeded `
      -Strict
    $coreSafeguards = $coreSafeguardsJson | ConvertFrom-Json
    Write-Host (
      "상태={0}; 관세청저장건너뜀={1}; 포트폴리오={2} {3}주; 저장본문누락={4}; 저장OCR필요={5}" -f
      $coreSafeguards.Status,
      $coreSafeguards.Customs.LatestStorageSkipped,
      $coreSafeguards.PortfolioQuantity.PortfolioName,
      $coreSafeguards.PortfolioQuantity.Quantity,
      $coreSafeguards.StorageQuality.BodyMissingCount,
      $coreSafeguards.StorageQuality.OcrNeededCount
    )
  }
}

if ($CheckCustomsTradeQuality) {
  Invoke-VerifyStep "관세청 수출입 데이터 품질 확인" {
    $customsQualityJson = & (Join-Path $PSScriptRoot "check_customs_trade_quality.ps1") `
      -BaseUrl $CustomsBaseUrl `
      -DevUserToken $CustomsDevUserToken `
      -StartYymm $CustomsStartYymm `
      -EndYymm $CustomsEndYymm `
      -RequireTotalTrendAuthorized:$RequireCustomsTotalTrendAuthorized
    $customsQuality = $customsQualityJson | ConvertFrom-Json
    Write-Host (
      "Status={0}; Period={1}; Dir={2}->{3}; DirCreated={4}; Files={5}->{6}; FilesChanged={7}; LatestStorageSkipped={8}; TotalTrendHttp={9}; TotalTrendHasStorage={10}" -f
      $customsQuality.Status,
      $customsQuality.Period,
      $customsQuality.CustomsDirExistsBefore,
      $customsQuality.CustomsDirExistsAfter,
      $customsQuality.CustomsDirCreatedDuringCheck,
      $customsQuality.CustomsFilesBefore,
      $customsQuality.CustomsFilesAfter,
      $customsQuality.CustomsFileCountChanged,
      $customsQuality.LatestStorageSkipped,
      $customsQuality.TotalTrendHttpStatusCode,
      $customsQuality.TotalTrendHasStorage
    )
  }
}

if ($CheckPortfolioQuantityProtection) {
  Invoke-VerifyStep "포트폴리오 수량 보호 확인" {
    $portfolioQuantityJson = & (Join-Path $PSScriptRoot "check_portfolio_quantity_protection.ps1") `
      -BaseUrl $PortfolioQuantityBaseUrl `
      -DevUserToken $PortfolioQuantityDevUserToken `
      -PortfolioName $PortfolioQuantityName `
      -Ticker $PortfolioQuantityTicker `
      -ExpectedQuantity $PortfolioQuantityExpected `
      -ExpectedCurrency $PortfolioQuantityCurrency `
      -Strict
    $portfolioQuantity = $portfolioQuantityJson | ConvertFrom-Json
    Write-Host (
      "상태={0}; 포트폴리오={1}; 종목={2}; 수량={3}; 기대수량={4}; 통화={5}; 수량보호={6}; 갱신시각={7}" -f
      $portfolioQuantity.Status,
      $portfolioQuantity.PortfolioName,
      $portfolioQuantity.Ticker,
      $portfolioQuantity.Quantity,
      $portfolioQuantity.ExpectedQuantity,
      $portfolioQuantity.Currency,
      $portfolioQuantity.SyncProtected,
      $portfolioQuantity.UpdatedAt
    )
  }
}

if ($CheckStorageQualitySafeguards) {
  Invoke-VerifyStep "저장소 품질 안전장치 확인" {
    $storageQualityJson = & (Join-Path $PSScriptRoot "check_storage_quality_safeguards.ps1") `
      -BaseUrl $StorageQualityBaseUrl `
      -DevUserToken $StorageQualityDevUserToken `
      -MaxBodyMissing $StorageQualityMaxBodyMissing `
      -MaxOcrNeeded $StorageQualityMaxOcrNeeded `
      -Strict
    $storageQuality = $storageQualityJson | ConvertFrom-Json
    Write-Host (
      "상태={0}; 본문누락={1}/{2}; OCR필요={3}/{4}; 보관={5}; 레거시/중복={6}; 뉴스저장정책={7}" -f
      $storageQuality.Status,
      $storageQuality.BodyMissingCount,
      $storageQuality.MaxBodyMissing,
      $storageQuality.OcrNeededCount,
      $storageQuality.MaxOcrNeeded,
      $storageQuality.ArchivedCount,
      $storageQuality.LegacyOrDuplicateCount,
      $storageQuality.NewsBodyStoragePolicy
    )
  }
}

if ($CheckFeedbackSmoke) {
  Invoke-VerifyStep "클래식 콘솔 피드백 스모크" {
    python tools\smoke_research_console_menus.py --url $ConsoleUrl
  }
}

if (-not $SkipLiveSmoke) {
  Invoke-VerifyStep "클래식 콘솔 메뉴 스모크" {
    python tools\smoke_research_console_menus.py --url $ConsoleUrl
  }

  Invoke-VerifyStep "클래식 콘솔 클릭 회귀 스모크" {
    python tools\smoke_research_console_clicks.py --url $ConsoleUrl
  }

  if (-not $SkipWriteSmoke) {
    Invoke-VerifyStep "클래식 콘솔 쓰기 액션 스모크" {
      python tools\smoke_research_console_write_actions.py --url $ConsoleUrl
    }
  }

  Invoke-VerifyStep "라이브 스모크 후 QA 쓰기 액션 정리" {
    python tools\smoke_research_console_write_actions.py --cleanup-only
  }
}

Write-Host ""
Write-Host "클래식 리서치 콘솔 검증 통과"
