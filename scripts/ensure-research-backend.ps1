param(
  [string]$ProjectRoot = "",
  [int]$Port = 8001,
  [string]$HostName = "127.0.0.1",
  [int]$WaitSeconds = 20,
  [string]$StateFile = "",
  [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$RestartScript = Join-Path $ProjectRootPath "scripts\restart-research-backend.ps1"
if (-not (Test-Path -LiteralPath $RestartScript)) {
  throw "Research backend restart script not found: $RestartScript"
}

if (-not $StateFile) {
  $StateFile = Join-Path $ProjectRootPath "tmp\research_backend_watchdog_state.json"
}
$StateDir = Split-Path -Parent $StateFile
if ($StateDir) {
  New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
}

$BaseUrl = "http://$HostName`:$Port"
$Headers = @{ Authorization = "Bearer dev-local-token" }

function Test-ResearchBackendHealthy {
  param([string]$Url)

  try {
    $health = Invoke-RestMethod -Uri "$Url/api/v1/system/health" -Headers $Headers -TimeoutSec 5
    $console = Invoke-WebRequest -UseBasicParsing -Uri "$Url/console/index.html" -TimeoutSec 5
    return ($health.status -eq "success" -and $console.StatusCode -eq 200)
  } catch {
    return $false
  }
}

function Write-WatchdogState {
  param(
    [string]$Status,
    [string]$Message,
    [bool]$RestartAttempted
  )

  $payload = [ordered]@{
    status = $Status
    message = $Message
    checked_at = (Get-Date).ToString("o")
    base_url = $BaseUrl
    restart_attempted = $RestartAttempted
    state_file = $StateFile
  }
  $payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

if (Test-ResearchBackendHealthy -Url $BaseUrl) {
  Write-WatchdogState -Status "ok" -Message "research backend is already healthy" -RestartAttempted $false
  Write-Host "Research backend healthy: $BaseUrl"
  exit 0
}

if ($NoRestart.IsPresent) {
  Write-WatchdogState -Status "down" -Message "research backend is down and restart is disabled" -RestartAttempted $false
  Write-Warning "Research backend is down: $BaseUrl"
  exit 1
}

Write-Host "Research backend is down. Restarting: $BaseUrl"
& $RestartScript -Port $Port -HostName $HostName -WaitSeconds $WaitSeconds

if (Test-ResearchBackendHealthy -Url $BaseUrl) {
  Write-WatchdogState -Status "restarted" -Message "research backend was restarted and is healthy" -RestartAttempted $true
  Write-Host "Research backend restarted and healthy: $BaseUrl"
  exit 0
}

Write-WatchdogState -Status "failed" -Message "research backend restart completed but health check still failed" -RestartAttempted $true
throw "Research backend restart did not recover health: $BaseUrl"
