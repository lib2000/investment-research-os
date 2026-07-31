param(
  [string]$ProjectRoot = "",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [int]$Port = 8001,
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
. $CredentialHelper

function Invoke-ResearchApi {
  param([string]$Method, [string]$Path, [hashtable]$Headers)
  Invoke-RestMethod -Method $Method -Uri "http://127.0.0.1:$Port$Path" -Headers $Headers -TimeoutSec 180
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

  $ranAny = @($operations | Where-Object { $_.action -eq "ran" }).Count -gt 0
  $syncAction = "skipped"
  if ($ranAny -and -not $DryRun) {
    & $Sync | Out-Host
    $syncAction = "ran"
  } elseif ($DryRun -and @($operations | Where-Object { $_.action -eq "would_run" }).Count -gt 0) {
    $syncAction = "would_run"
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
