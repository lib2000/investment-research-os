param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-DailyStrategyValidation-0845",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")

$StatePath = Join-Path $ProjectRootPath "tmp\daily_strategy_validation_state.json"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$taskInfo = if ($task) { $task | Get-ScheduledTaskInfo } else { $null }
$state = if (Test-Path -LiteralPath $StatePath) {
  try { [IO.File]::ReadAllText($StatePath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json } catch { $null }
} else { $null }
$arguments = if ($task) { [string]$task.Actions[0].Arguments } else { "" }
$commandSafe = -not ($arguments -match "DEV_USER_TOKEN\s*=|dev-local-token|Bearer\s+")
$runnerConfigured = $arguments -match "run_daily_strategy_validation\.ps1"
$startWhenAvailable = $null -ne $task -and [bool]$task.Settings.StartWhenAvailable
$credentialConfigured = Test-InvestmentResearchCredential -Target $CredentialTarget
$lastResultReady = $null -eq $taskInfo -or $taskInfo.LastRunTime.Year -lt 2000 -or $taskInfo.LastTaskResult -in @(0, 267009, 267011)
$ready = $null -ne $task -and $runnerConfigured -and $commandSafe -and $startWhenAvailable -and $credentialConfigured -and $lastResultReady

$result = [ordered]@{
  status = if ($ready) { "ready" } else { "needs_attention" }
  task_name = $TaskName
  task_registered = $null -ne $task
  task_state = if ($task) { [string]$task.State } else { "missing" }
  runner_configured = $runnerConfigured
  command_safe = $commandSafe
  start_when_available = $startWhenAvailable
  credential_configured = $credentialConfigured
  last_run_time = if ($taskInfo -and $taskInfo.LastRunTime.Year -ge 2000) { $taskInfo.LastRunTime.ToString("o") } else { $null }
  last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
  next_run_time = if ($taskInfo -and $taskInfo.NextRunTime.Year -ge 2000) { $taskInfo.NextRunTime.ToString("o") } else { $null }
  latest_run_status = if ($state) { [string]$state.status } else { $null }
  latest_run_date = if ($state) { [string]$state.run_date } else { $null }
  latest_run_id = if ($state -and $state.backtest) { [string]$state.backtest.run_id } else { $null }
  live_order_endpoint_called = if ($state -and $state.safety) { [bool]$state.safety.live_order_endpoint_called } else { $null }
}

if ($Json) {
  $result | ConvertTo-Json -Depth 6 -Compress
} else {
  $result | Format-List
}
if (-not $ready) { exit 1 }
