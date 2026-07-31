param(
  [string]$ProjectRoot = "C:\Users\lib20\projects\InvestmentJournalApp",
  [string]$TaskName = "InvestmentResearchOS-Autostart",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")
$StatePath = Join-Path $ProjectRootPath "tmp\investment_research_autostart_state.json"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$credentialConfigured = Test-InvestmentResearchCredential -Target $CredentialTarget
$state = if (Test-Path -LiteralPath $StatePath) { Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json } else { $null }
$taskInfo = if ($task) { $task | Get-ScheduledTaskInfo } else { $null }
$arguments = if ($task) { [string]$task.Actions[0].Arguments } else { "" }
$commandSafe = -not ($arguments -match "DEV_USER_TOKEN\s*=|dev-local-token|Bearer\s+")
$runnerConfigured = $arguments -match "start-investment-research-autostart\.ps1"
$lastResultReady = $null -eq $taskInfo -or $taskInfo.LastRunTime.Year -lt 2000 -or $taskInfo.LastTaskResult -in @(0, 267009, 267011)
$ready = $null -ne $task -and $credentialConfigured -and $commandSafe -and $runnerConfigured -and $lastResultReady
$result = [ordered]@{
  status = if ($ready) { "ready" } else { "needs_attention" }
  task_name = $TaskName
  task_registered = $null -ne $task
  task_state = if ($task) { [string]$task.State } else { "missing" }
  credential_configured = $credentialConfigured
  command_safe = $commandSafe
  runner_configured = $runnerConfigured
  last_run_time = if ($taskInfo) { $taskInfo.LastRunTime.ToString("o") } else { $null }
  last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
  state_file_exists = $null -ne $state
  last_startup_status = if ($state) { $state.status } else { $null }
  last_startup_at = if ($state) { $state.completed_at } else { $null }
  next_action = if ($ready) { $null } elseif (-not $credentialConfigured) { "Windows Credential Manager 자격 증명을 등록하세요." } elseif (-not $task) { "로그인 자동 시작 작업을 등록하세요." } elseif (-not $commandSafe) { "작업 명령줄에서 평문 자격 증명을 제거하세요." } else { "자동 시작 작업의 최근 실행 결과를 확인하세요." }
}

if ($Json) {
  $result | ConvertTo-Json -Depth 4 -Compress
} else {
  $result | Format-List
}

if (-not $ready) { exit 1 }
