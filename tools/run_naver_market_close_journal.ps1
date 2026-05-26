param(
  [int]$Port = 8001,
  [string]$HostName = "127.0.0.1",
  [string]$AccessToken = "dev-local-token",
  [switch]$Force,
  [switch]$StartBackendIfNeeded
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$BackendScript = Join-Path $ProjectRootPath "scripts\start-research-backend.ps1"
$ApiBase = "http://$HostName`:$Port"
$SystemDir = Join-Path $ProjectRootPath "research_vault\_system"
$LogPath = Join-Path $SystemDir "naver_market_close_journal_task.log"

New-Item -ItemType Directory -Force -Path $SystemDir | Out-Null

function Write-TaskLog {
  param([string]$Message)
  $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
  Add-Content -Path $LogPath -Value "[$timestamp] $Message" -Encoding UTF8
}

function Test-BackendReady {
  try {
    Invoke-RestMethod -Uri "$ApiBase/" -TimeoutSec 5 | Out-Null
    return $true
  } catch {
    return $false
  }
}

if (-not (Test-BackendReady)) {
  if (-not $StartBackendIfNeeded) {
    Write-TaskLog "backend_unavailable: $ApiBase"
    throw "백엔드가 실행 중이 아닙니다. -StartBackendIfNeeded 옵션을 사용하거나 먼저 백엔드를 시작하세요."
  }
  Write-TaskLog "backend_start_requested: $ApiBase"
  Start-Process -FilePath powershell.exe `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BackendScript, "-Port", $Port `
    -WorkingDirectory $ProjectRootPath `
    -WindowStyle Hidden
  Start-Sleep -Seconds 8
}

if (-not (Test-BackendReady)) {
  Write-TaskLog "backend_start_failed: $ApiBase"
  throw "백엔드를 시작했지만 $ApiBase 응답을 확인하지 못했습니다."
}

$forceText = if ($Force) { "true" } else { "false" }
$uri = "$ApiBase/api/v1/naver-research/market-close-journal/refresh?force=$forceText"
$result = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ Authorization = "Bearer $AccessToken" } -TimeoutSec 120
Write-TaskLog "market_close_journal_refresh: status=$($result.status), entry=$($result.entry.entry_id), title=$($result.source.title)"
$result | ConvertTo-Json -Depth 12
