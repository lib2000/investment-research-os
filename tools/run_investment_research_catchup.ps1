param(
  [string]$ProjectRoot = "",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [int]$Port = 8001,
  [string]$StrategyValidationTime = "08:45",
  [string]$ResearchOperationsTime = "18:30",
  [int]$DockerStartupTimeoutSeconds = 180,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$CredentialHelper = Join-Path $ProjectRootPath "tools\investment_research_credential.ps1"
$Watchdog = Join-Path $ProjectRootPath "scripts\ensure-research-backend.ps1"
$Sync = Join-Path $ProjectRootPath "tools\sync_openclaw_investment_context.ps1"
$StatePath = Join-Path $ProjectRootPath "tmp\investment_research_catchup_state.json"
$DailyOperationsRunner = Join-Path $ProjectRootPath "tools\run_daily_research_operations.ps1"
$StrategyValidationRunner = Join-Path $ProjectRootPath "tools\run_daily_strategy_validation.ps1"
$StrategyValidationStatePath = Join-Path $ProjectRootPath "tmp\daily_strategy_validation_state.json"
$ResearchAutomationStatusPath = Join-Path $ProjectRootPath "research_vault\_system\research_automation_status.json"
. $CredentialHelper

function Invoke-ResearchApi {
  param([string]$Method, [string]$Path, [hashtable]$Headers)
  Invoke-RestMethod -Method $Method -Uri "http://127.0.0.1:$Port$Path" -Headers $Headers -TimeoutSec 180
}

function Get-LatestPortfolioCloseCutoff {
  param([datetimeoffset]$Now = [datetimeoffset]::Now)
  $candidate = [datetimeoffset]::new($Now.Year, $Now.Month, $Now.Day, 18, 30, 0, $Now.Offset)
  if ($Now -lt $candidate) { $candidate = $candidate.AddDays(-1) }
  while ($candidate.DayOfWeek -in @([DayOfWeek]::Saturday, [DayOfWeek]::Sunday)) {
    $candidate = $candidate.AddDays(-1)
  }
  return $candidate
}

function Test-PortfolioRefreshDue {
  param([string]$StorePath)
  if (-not (Test-Path -LiteralPath $StorePath)) { return $true }
  try {
    $store = [IO.File]::ReadAllText($StorePath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    $portfolios = @($store.portfolios.PSObject.Properties | ForEach-Object { $_.Value })
    if ($portfolios.Count -eq 0) { return $true }
    $cutoff = Get-LatestPortfolioCloseCutoff
    foreach ($portfolio in $portfolios) {
      if (-not $portfolio.updated_at) { return $true }
      if ([datetimeoffset]::Parse([string]$portfolio.updated_at) -lt $cutoff) { return $true }
    }
    return $false
  } catch {
    return $true
  }
}

function Get-LatestScheduledCutoff {
  param(
    [string]$At,
    [datetimeoffset]$Now = [datetimeoffset]::Now
  )

  if ($At -notmatch "^(?<hour>\d{1,2}):(?<minute>\d{2})$") {
    throw "Scheduled time must use HH:mm format: $At"
  }
  $hour = [int]$matches.hour
  $minute = [int]$matches.minute
  if ($hour -gt 23 -or $minute -gt 59) {
    throw "Scheduled time is outside the local day: $At"
  }
  $cutoff = [datetimeoffset]::new($Now.Year, $Now.Month, $Now.Day, $hour, $minute, 0, $Now.Offset)
  if ($Now -lt $cutoff) {
    $cutoff = $cutoff.AddDays(-1)
  }
  return $cutoff
}

function Test-StrategyValidationDue {
  param(
    [string]$StateFile,
    [string]$TargetRunDate
  )

  if (-not (Test-Path -LiteralPath $StateFile)) { return $true }
  try {
    $state = [IO.File]::ReadAllText($StateFile, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    return -not ($state.status -eq "success" -and [string]$state.run_date -eq $TargetRunDate)
  } catch {
    return $true
  }
}

function Test-ResearchAutomationDue {
  param(
    [string]$StatusFile,
    [datetimeoffset]$Cutoff
  )

  if (-not (Test-Path -LiteralPath $StatusFile)) { return $true }
  try {
    $status = [IO.File]::ReadAllText($StatusFile, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$status.updated_at)) { return $true }
    return [datetimeoffset]::Parse([string]$status.updated_at) -lt $Cutoff
  } catch {
    return $true
  }
}

function Get-SafeCatchupError {
  param([object]$ErrorRecord, [string]$Secret)
  $message = [string]$ErrorRecord
  if (-not [string]::IsNullOrWhiteSpace($Secret)) {
    $message = $message.Replace($Secret, "[REDACTED]")
  }
  $message = $message -replace "[\r\n]+", " | "
  if ($message.Length -gt 500) { return $message.Substring(0, 500) }
  return $message
}

$startedAt = (Get-Date).ToString("o")
$operations = @()
$token = $null
try {
  if (-not $DryRun) {
    & $Watchdog -ProjectRoot $ProjectRootPath -Port $Port | Out-Host
  }

  $token = Get-InvestmentResearchCredentialSecret -Target $CredentialTarget
  if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Windows Credential Manager에 투자 리서치 API 토큰이 없습니다."
  }
  $headers = @{ Authorization = "Bearer $token" }
  $catchupFailures = @()
  $portfolioStorePath = Join-Path $ProjectRootPath "research_vault\_system\user_portfolios.json"
  $portfolioDue = Test-PortfolioRefreshDue -StorePath $portfolioStorePath
  $portfolioOperation = [ordered]@{
    id = "portfolio_close_prices"
    enabled = $true
    due_before = $portfolioDue
    action = "skipped"
    result_status = if ($portfolioDue) { "stale" } else { "fresh" }
  }
  if ($portfolioDue) {
    if ($DryRun) {
      $portfolioOperation.action = "would_run"
    } else {
      & (Join-Path $ProjectRootPath "tools\refresh_portfolio_prices.ps1") `
        -ProjectRoot $ProjectRootPath `
        -BaseUrl "http://127.0.0.1:$Port" `
        -DevUserToken $token `
        -SkipCheck | Out-Host
      if (-not $?) { throw "포트폴리오 장 종료 가격 catch-up에 실패했습니다." }
      $portfolioOperation.action = "ran"
      $portfolioOperation.result_status = "success"
    }
  }
  $operations += [pscustomobject]$portfolioOperation
  $plans = @(
    @{ id="daily_recommendations"; status="/api/v1/daily-recommendations/status"; run="/api/v1/daily-recommendations/run?force=false&save_result=true" },
    @{ id="naver_market_close_journal"; status="/api/v1/naver-research/market-close-journal/task-status"; run="/api/v1/naver-research/market-close-journal/refresh?force=false" },
    @{ id="telegram_us_market_close_journal"; status="/api/v1/telegram-market-close-journal/task-status"; run="/api/v1/telegram-market-close-journal/refresh?force=false" },
    @{ id="telegram_favorite_posts"; status="/api/v1/telegram/favorite-posts/task-status"; run="/api/v1/telegram/favorite-posts/run?force=false" }
  )

  foreach ($plan in $plans) {
    $status = Invoke-ResearchApi -Method "GET" -Path $plan.status -Headers $headers
    $due = [bool]$status.due_now
    $enabled = if ($null -eq $status.enabled) { $true } else { [bool]$status.enabled }
    $operation = [ordered]@{ id=$plan.id; enabled=$enabled; due_before=$due; action="skipped"; result_status=$status.status }
    if ($enabled -and $due) {
      if ($DryRun) {
        $operation.action = "would_run"
      } else {
        $result = Invoke-ResearchApi -Method "POST" -Path $plan.run -Headers $headers
        $operation.action = "ran"
        $operation.result_status = $result.status
      }
    }
    $operations += [pscustomobject]$operation
  }

  $researchCutoff = Get-LatestScheduledCutoff -At $ResearchOperationsTime
  $researchAutomationDue = Test-ResearchAutomationDue -StatusFile $ResearchAutomationStatusPath -Cutoff $researchCutoff
  $researchOperation = [ordered]@{
    id = "research_evidence_and_quality"
    enabled = $true
    due_before = $researchAutomationDue
    action = "skipped"
    result_status = if ($researchAutomationDue) { "stale" } else { "fresh" }
  }
  if ($researchAutomationDue) {
    if ($DryRun) {
      $researchOperation.action = "would_run"
    } else {
      try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DailyOperationsRunner `
          -ProjectRoot $ProjectRootPath `
          -CredentialTarget $CredentialTarget `
          -BaseUrl "http://127.0.0.1:$Port" `
          -SkipPortfolioRefresh `
          -SkipRecommendationRun `
          -SkipRecommendationPreview `
          -SkipTelegramBriefDelivery `
          -SkipPortfolioReportAlert `
          -SkipOpenClawSync `
          -SkipVerification
        if ($LASTEXITCODE -ne 0) {
          throw "research evidence and local quality runner exited with code $LASTEXITCODE"
        }
        $researchOperation.action = "ran"
        $researchOperation.result_status = "success"
      } catch {
        $researchOperation.action = "failed"
        $researchOperation.result_status = "failed"
        $researchOperation.error = Get-SafeCatchupError -ErrorRecord $_ -Secret $token
        $catchupFailures += "research_evidence_and_quality"
      }
    }
  }
  $operations += [pscustomobject]$researchOperation

  $strategyCutoff = Get-LatestScheduledCutoff -At $StrategyValidationTime
  $strategyRunDate = $strategyCutoff.ToString("yyyy-MM-dd")
  $strategyDue = Test-StrategyValidationDue -StateFile $StrategyValidationStatePath -TargetRunDate $strategyRunDate
  $strategyOperation = [ordered]@{
    id = "daily_strategy_validation"
    enabled = $true
    target_run_date = $strategyRunDate
    due_before = $strategyDue
    action = "skipped"
    result_status = if ($strategyDue) { "stale" } else { "fresh" }
    live_order_endpoint_called = $false
  }
  if ($strategyDue) {
    if ($DryRun) {
      $strategyOperation.action = "would_run"
    } else {
      try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StrategyValidationRunner `
          -ProjectRoot $ProjectRootPath `
          -CredentialTarget $CredentialTarget `
          -RunDate $strategyRunDate `
          -StartServicesIfNeeded `
          -StartDockerIfNeeded `
          -DockerStartupTimeoutSeconds $DockerStartupTimeoutSeconds
        if ($LASTEXITCODE -ne 0) {
          throw "daily strategy validation runner exited with code $LASTEXITCODE"
        }
        $strategyOperation.action = "ran"
        $strategyOperation.result_status = "success"
      } catch {
        $strategyOperation.action = "failed"
        $strategyOperation.result_status = "failed"
        $strategyOperation.error = Get-SafeCatchupError -ErrorRecord $_ -Secret $token
        $catchupFailures += "daily_strategy_validation"
      }
    }
  }
  $operations += [pscustomobject]$strategyOperation

  $ranAny = @($operations | Where-Object { $_.action -eq "ran" }).Count -gt 0
  $syncAction = "skipped"
  if ($ranAny -and -not $DryRun) {
    & $Sync | Out-Host
    $syncAction = "ran"
  } elseif ($DryRun -and @($operations | Where-Object { $_.action -eq "would_run" }).Count -gt 0) {
    $syncAction = "would_run"
  }

  if ($catchupFailures.Count -gt 0) {
    throw ("Catch-up steps need attention: " + ($catchupFailures -join ", "))
  }

  $payload = [ordered]@{
    status = "success"
    started_at = $startedAt
    completed_at = (Get-Date).ToString("o")
    dry_run = [bool]$DryRun
    operations = $operations
    openclaw_sync = $syncAction
    project_root = $ProjectRootPath
  }
  $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding UTF8
  $payload | ConvertTo-Json -Depth 8
} catch {
  $payload = [ordered]@{
    status = "failed"
    started_at = $startedAt
    completed_at = (Get-Date).ToString("o")
    dry_run = [bool]$DryRun
    operations = $operations
    error = $_.Exception.Message
    project_root = $ProjectRootPath
  }
  $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding UTF8
  throw
} finally {
  $token = $null
}
