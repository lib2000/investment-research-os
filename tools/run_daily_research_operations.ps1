param(
  [string]$ProjectRoot = "",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [string]$LogPath = "",
  [int]$PortfolioRefreshTimeoutSeconds = 120,
  [int]$RecommendationRunTimeoutSeconds = 600,
  [int]$ResearchAutomationTimeoutSeconds = 300,
  [switch]$SkipPortfolioRefresh,
  [switch]$SkipRecommendationRun,
  [switch]$SkipRecommendationPreview,
  [switch]$SkipTelegramBriefDelivery,
  [switch]$SubmitTelegramBriefDelivery,
  [switch]$EnableTelegramBriefCleanup,
  [switch]$SkipPortfolioReportAlert,
  [switch]$SubmitPortfolioReportAlert,
  [switch]$SkipResearchAutomationRefresh,
  [switch]$SkipDartFilingDuplicateCleanup,
  [switch]$SkipResearchSourceStoreCheck,
  [switch]$SkipPortfolioAnalysisCoverage,
  [switch]$SkipOpenClawSync,
  [switch]$RequireCompletionAudit,
  [switch]$SkipVerification
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

if ([string]::IsNullOrWhiteSpace($LogPath)) {
  $LogPath = Join-Path $ProjectRootPath "research_vault\_system\daily_research_operations_task.log"
}
$LogDirectory = Split-Path -Parent $LogPath
if ($LogDirectory) {
  New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
}

$script:DailyResearchOperationsLogPath = $LogPath
$script:DailyResearchOperationsSecret = ""
$script:DailyResearchOperationsCurrentStep = "initialization"

function Write-DailyResearchOperationsLog {
  param(
    [Parameter(Mandatory = $true)][string]$Level,
    [Parameter(Mandatory = $true)][string]$Message
  )

  $safeMessage = $Message
  if (-not [string]::IsNullOrWhiteSpace($script:DailyResearchOperationsSecret)) {
    $safeMessage = $safeMessage.Replace($script:DailyResearchOperationsSecret, "[REDACTED]")
  }
  $safeMessage = $safeMessage -replace "[\r\n]+", " | "
  $line = "[{0}] [{1}] [{2}] {3}" -f (Get-Date).ToString("o"), $Level, $script:DailyResearchOperationsCurrentStep, $safeMessage
  try {
    [System.IO.File]::AppendAllText(
      $script:DailyResearchOperationsLogPath,
      "$line`r`n",
      [System.Text.UTF8Encoding]::new($false)
    )
  } catch {
    # A logging failure must never hide the actual scheduled-task failure.
  }
}

trap {
  Write-DailyResearchOperationsLog -Level "ERROR" -Message $_.Exception.Message
  exit 1
}

. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")

if ([string]::IsNullOrWhiteSpace($DevUserToken)) {
  $DevUserToken = Get-InvestmentResearchCredentialSecret -Target $CredentialTarget
}
if ([string]::IsNullOrWhiteSpace($DevUserToken)) {
  throw "Windows Credential Manager에 투자 리서치 API 토큰이 없습니다: $CredentialTarget"
}
$script:DailyResearchOperationsSecret = $DevUserToken
Write-DailyResearchOperationsLog -Level "START" -Message "daily research operations started"

function Invoke-DailyResearchStep {
  param(
    [string]$Name,
    [scriptblock]$Block
  )

  Write-Host ""
  Write-Host "==> $Name"
  $script:DailyResearchOperationsCurrentStep = $Name
  Write-DailyResearchOperationsLog -Level "START" -Message "$Name started"
  $global:LASTEXITCODE = 0
  $stepOutput = @(& $Block 2>&1)
  $stepExitCode = $LASTEXITCODE
  foreach ($entry in $stepOutput) {
    Write-Output $entry
  }
  if ($stepExitCode -ne 0) {
    $outputTail = @(
      $stepOutput |
        ForEach-Object { ($_ | Out-String -Width 240).TrimEnd() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Last 20
    )
    foreach ($line in $outputTail) {
      Write-DailyResearchOperationsLog -Level "DETAIL" -Message $line
    }
    throw "$Name 실패: 종료 코드 $stepExitCode"
  }
  Write-Host "정상 $Name"
  Write-DailyResearchOperationsLog -Level "OK" -Message "$Name completed"
}

if (-not $SkipPortfolioRefresh.IsPresent) {
  Invoke-DailyResearchStep "포트폴리오 가격 갱신" {
    python tools\refresh_portfolio_prices.py `
      --base-url $BaseUrl `
      --token $DevUserToken `
      --timeout $PortfolioRefreshTimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "포트폴리오 가격 갱신 응답은 실패했지만 저장 상태 검증을 시도합니다."
      python tools\check_portfolio_store.py `
        --portfolio "이형주" `
        --min-holdings 17 `
        --expected-holdings-count 17 `
        --forbid-zero `
        --max-price-age-hours 24 `
        --max-portfolio-age-hours 24
      if ($LASTEXITCODE -ne 0) {
        return
      }
      python tools\check_all_portfolio_store.py `
        --min-holdings 1 `
        --forbid-zero `
        --max-price-age-hours 24 `
        --max-sync-age-hours 168
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "포트폴리오 저장 상태 검증이 통과해 운영 루틴을 계속합니다."
      }
    }
  }
}

if (-not $SkipRecommendationRun.IsPresent) {
  Invoke-DailyResearchStep "오늘 추천 강제 재분석" {
    $headers = @{
      Authorization = "Bearer $DevUserToken"
      "Content-Type" = "application/json"
    }
    $query = "force=true" + [char]38 + "save_result=true"
    $uri = "$($BaseUrl.TrimEnd('/'))/api/v1/daily-recommendations/run?$query"
    try {
      $result = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -TimeoutSec $RecommendationRunTimeoutSeconds
    } catch {
      Write-Warning "오늘 추천 API 응답 실패/타임아웃: $($_.Exception.Message)"
      python tools\check_daily_recommendations_store.py `
        --require-milestones `
        --require-quality `
        --expected-latest-count 6 `
        --max-latest-age-days 0
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "오늘 추천 저장 검증이 통과해 운영 루틴을 계속합니다."
        return
      }
      throw
    }
    Write-Host (
      "상태={0}; 추천일={1}; 최신추천일={2}; 전체기록={3}; 저장={4}" -f
      $result.status,
      $result.recommendation_date,
      $result.latest_recommendation_date,
      $result.record_count,
      $result.storage_path
    )
  }
}

if (-not $SkipRecommendationPreview.IsPresent) {
  Invoke-DailyResearchStep "추천 저장/재계산 프리뷰 저장" {
    python tools\check_daily_recommendation_candidate_policy.py `
      --require-hold-warning `
      --expected-held-ticker 112610 `
      --output-json tmp\daily_recommendation_candidate_policy_preview.json
  }
}

if (-not $SkipTelegramBriefDelivery.IsPresent) {
  Invoke-DailyResearchStep "텔레그램 중요 브리프 delivery ledger 갱신" {
    $telegramDeliveryArgs = @(
      "tools\check_telegram_brief_delivery.py",
      "--write-state"
    )
    if ($SubmitTelegramBriefDelivery.IsPresent) {
      $telegramDeliveryArgs += @("--enabled", "--submit")
    }
    if ($EnableTelegramBriefCleanup.IsPresent) {
      $telegramDeliveryArgs += "--cleanup-enabled"
    }
    python @telegramDeliveryArgs
  }
}

if (-not $SkipPortfolioReportAlert.IsPresent) {
  Invoke-DailyResearchStep "텔레그램 보유 종목 신규 리포트 알림 ledger 갱신" {
    $portfolioReportAlertArgs = @(
      "tools\check_portfolio_report_alert.py",
      "--write-state"
    )
    if ($SubmitPortfolioReportAlert.IsPresent) {
      $portfolioReportAlertArgs += @("--enabled", "--submit")
    }
    python @portfolioReportAlertArgs
  }
}

if (-not $SkipResearchAutomationRefresh.IsPresent) {
  Invoke-DailyResearchStep "실적 일정/DART/IR/중복/Dossier 상태 갱신" {
    $previousPipelineToken = $env:INVESTMENT_RESEARCH_DEV_USER_TOKEN
    try {
      $env:INVESTMENT_RESEARCH_DEV_USER_TOKEN = $DevUserToken
      python tools\check_research_evidence_pipeline.py `
        --base-url $BaseUrl `
        --timeout $ResearchAutomationTimeoutSeconds `
        --refresh `
        --write-state `
        --strict `
        --json
    } finally {
      if ($null -eq $previousPipelineToken) {
        Remove-Item Env:INVESTMENT_RESEARCH_DEV_USER_TOKEN -ErrorAction SilentlyContinue
      } else {
        $env:INVESTMENT_RESEARCH_DEV_USER_TOKEN = $previousPipelineToken
      }
    }
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "실적 일정/DART/IR/중복/Dossier 통합 점검에 실패해 저장 상태 검증을 시도합니다."
      python tools\check_research_source_store.py --strict
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "리서치 소스 저장 상태 검증이 통과해 운영 루틴을 계속합니다."
        return
      }
    }
  }
}

if (-not $SkipDartFilingDuplicateCleanup.IsPresent) {
  Invoke-DailyResearchStep "DART 공시 중복 소프트 보관 정리" {
    # Local-only cleanup: only byte-identical captures with the same DART
    # receipt number are archived. No source file is hard-deleted.
    python tools\cleanup_duplicate_dart_filings.py --apply --write-state --recent-tickers-hours 36 --max-recent-tickers 12
  }
}

if (-not $SkipResearchSourceStoreCheck.IsPresent) {
  Invoke-DailyResearchStep "리서치 상태 저장 무결성 점검" {
    # Local-only integrity check. It catches malformed state JSON before the
    # next source refresh or dashboard read can silently fall back to defaults.
    python tools\check_research_source_store.py --strict
  }
}

if (-not $SkipPortfolioAnalysisCoverage.IsPresent) {
  Invoke-DailyResearchStep "포트폴리오 분석 문서/검토 게이트 backlog 갱신" {
    # This is local-only bookkeeping. It never creates a report, calls an LLM,
    # sends a notification, or submits an order.
    # Keep scheduled-task logs compact; the complete per-holding backlog is
    # persisted locally in research_vault/_system/portfolio_analysis_backlog.json.
    python tools\check_portfolio_analysis_coverage.py `
      --all-portfolios `
      --min-average-completion 0.95 `
      --write-backlog `
      --strict `
      --limit 0
  }
}

if (-not $SkipOpenClawSync.IsPresent) {
  Invoke-DailyResearchStep "OpenClaw 투자리서치 브리지 동기화" {
    # Keep the decision-support bridge fresh even while normal development changes are uncommitted.
    # The bridge itself marks completion audit as deferred in that state.
    if ($RequireCompletionAudit.IsPresent) {
      & (Join-Path $PSScriptRoot "sync_openclaw_investment_context.ps1") -RequireCompletionAudit
    } else {
      & (Join-Path $PSScriptRoot "sync_openclaw_investment_context.ps1")
    }
  }
}

if (-not $SkipVerification.IsPresent) {
  Invoke-DailyResearchStep "운영 검증" {
    & (Join-Path $PSScriptRoot "verify_research_console.ps1") `
      -ProjectRoot $ProjectRootPath `
      -SkipLiveSmoke `
      -SkipWriteSmoke `
      -CheckPortfolioStore `
      -CheckNpsDomesticEquityAllocation `
      -CheckDailyRecommendationStore `
      -CheckInvestmentInsightHub
  }
}

Write-Host ""
Write-Host "일일 리서치 운영 루틴 완료"
$script:DailyResearchOperationsCurrentStep = "complete"
Write-DailyResearchOperationsLog -Level "OK" -Message "daily research operations completed"
