param(
  [ValidateSet("start", "status", "stop")]
  [string]$Action = "start",
  [switch]$OpenConsole
)

$ErrorActionPreference = "Stop"
$ResearchRoot = $PSScriptRoot
$TradingRoot = Join-Path (Split-Path -Parent $ResearchRoot) "open-trading-api"
$TradingScript = Join-Path $TradingRoot "investment-web.ps1"
$EnsureBackend = Join-Path $ResearchRoot "scripts\ensure-research-backend.ps1"
$ConsoleUrl = "http://127.0.0.1:8001/console/"
$AccessToken = if ($env:DEV_USER_TOKEN) { $env:DEV_USER_TOKEN.Trim() } else { "dev-local-token" }
$Headers = @{ Authorization = "Bearer $AccessToken" }

if (-not (Test-Path -LiteralPath $TradingScript)) {
  throw "Trading launcher not found: $TradingScript"
}

function Read-WorkbenchStatus {
  try {
    return Invoke-RestMethod `
      -Uri "http://127.0.0.1:8001/api/v1/system/investment-workbench" `
      -Headers $Headers `
      -TimeoutSec 10
  } catch {
    return $null
  }
}

function Test-ResearchBackendReady {
  try {
    Invoke-RestMethod `
      -Uri "http://127.0.0.1:8001/api/v1/system/health" `
      -Headers $Headers `
      -TimeoutSec 10 `
      -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Ensure-KisPaperSession {
  $authUrl = "http://127.0.0.1:8002/api/auth"
  try {
    $current = Invoke-RestMethod -Uri "$authUrl/status" -TimeoutSec 8
    if ($current.authenticated -eq $true -and $current.mode -in @("vps", "paper")) {
      Write-Host "KIS paper session is already authenticated."
      return $true
    }
    if ($current.mode -notin @("vps", "paper")) {
      Write-Warning "KIS is not configured for paper mode. Automatic authentication was skipped."
      return $false
    }
    $payload = @{ mode = "vps" } | ConvertTo-Json
    $login = Invoke-RestMethod `
      -Uri "$authUrl/login" `
      -Method Post `
      -ContentType "application/json" `
      -Body $payload `
      -TimeoutSec 30
    if ($login.authenticated -eq $true -and $login.mode -in @("vps", "paper")) {
      Write-Host "KIS paper session authenticated from existing local configuration."
      return $true
    }
  } catch {
    Write-Warning "KIS paper session recovery failed: $($_.Exception.Message)"
  }
  return $false
}

function Show-WorkbenchStatus {
  $status = Read-WorkbenchStatus
  if (-not $status) {
    Write-Host "Research Console API (8001): STOPPED"
    & $TradingScript status
    return
  }
  $labels = @{
    strategy_api = "Strategy API"
    backtester_api = "Backtester API"
    strategy_builder = "Strategy Builder"
    backtester = "Backtester"
    docker = "Docker/Lean Engine"
    lean_data = "Lean Reference Data"
    kis_paper = "KIS Paper Trading"
    openclaw_mobile = "OpenClaw/iPhone"
    windows_autostart = "Windows Autostart"
  }
  $status.checks | ForEach-Object {
    $nextAction = ""
    if ($_.status -ne "ready") {
      $nextAction = switch ($_.id) {
        "docker" { "Start Docker Desktop Linux engine"; break }
        "lean_data" { "Initialize Lean reference data"; break }
        "kis_paper" { "Authenticate KIS paper mode in Backtester"; break }
        "openclaw_mobile" { "Connect the iPhone app to the OpenClaw gateway"; break }
        "windows_autostart" { "Register the Windows logon autostart task"; break }
        default { "Run the integrated launcher again" }
      }
    }
    [pscustomobject]@{
      Component = $labels[[string]$_.id]
      Status = $_.status
      HTTP = $_.http_status
      LatencyMs = $_.latency_ms
      NextAction = $nextAction
    }
  } | Format-Table -AutoSize
  Write-Host "Ready: $($status.ready_count)/$($status.check_count)"
  Write-Host "Console: $ConsoleUrl"
}

if ($Action -eq "status") {
  Show-WorkbenchStatus
  exit 0
}

if ($Action -eq "stop") {
  & $TradingScript stop
  Write-Host "Research Console backend is intentionally left running for watchdog compatibility."
  Show-WorkbenchStatus
  exit 0
}

& $EnsureBackend
$tradingProcess = Start-Process `
  -FilePath "powershell.exe" `
  -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $TradingScript,
    "start"
  ) `
  -WorkingDirectory $TradingRoot `
  -PassThru `
  -NoNewWindow


Ensure-KisPaperSession | Out-Null

$deadline = (Get-Date).AddSeconds(90)
do {
  Start-Sleep -Seconds 1
  $backendReady = Test-ResearchBackendReady
} until ($backendReady -or (Get-Date) -gt $deadline)

if (-not $backendReady) {
  throw "Research OS health API did not respond after startup."
}

Show-WorkbenchStatus
if ($OpenConsole) {
  Start-Process $ConsoleUrl
}
