param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TradingApiRoot = "",
  [int]$WaitSeconds = 180
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
. (Join-Path $ProjectRootPath "tools\resolve_investment_workspace.ps1")
$workspacePaths = Get-InvestmentWorkspacePaths -ProjectRoot $ProjectRootPath
if ([string]::IsNullOrWhiteSpace($TradingApiRoot)) {
  $TradingApiRoot = $workspacePaths.TradingApiRoot
}
$TradingApiRoot = (Resolve-Path -LiteralPath $TradingApiRoot).Path

$pythonCommand = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $pythonCommand) {
  throw "python.exe was not found."
}

$RuntimeDir = Join-Path $ProjectRootPath "tmp\investment-analysis-apis"
$StatePath = Join-Path $RuntimeDir "services.json"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$services = @(
  [pscustomobject]@{
    Name = "strategy-backend"
    Port = 8000
    WorkDir = Join-Path $TradingApiRoot "strategy_builder"
    HealthUri = "http://127.0.0.1:8000/api/strategies"
  },
  [pscustomobject]@{
    Name = "backtester-backend"
    Port = 8002
    WorkDir = Join-Path $TradingApiRoot "backtester"
    HealthUri = "http://127.0.0.1:8002/api/strategies"
  }
)

function Test-ServiceHealthy {
  param([string]$Uri)
  try {
    Invoke-RestMethod -Uri $Uri -TimeoutSec 5 | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Get-ListenerProcessId {
  param([int]$Port)
  $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($null -eq $listener) { return $null }
  return [int]$listener.OwningProcess
}

$started = @()
$state = @()
try {
  foreach ($service in $services) {
    if (-not (Test-Path -LiteralPath $service.WorkDir -PathType Container)) {
      throw "Analysis API work directory was not found: $($service.WorkDir)"
    }

    if (Test-ServiceHealthy -Uri $service.HealthUri) {
      $listenerProcessId = Get-ListenerProcessId -Port $service.Port
      $state += [pscustomobject]@{
        name = $service.Name
        port = $service.Port
        pid = $listenerProcessId
        started_by_runner = $false
        health_uri = $service.HealthUri
      }
      Write-Host "$($service.Name) already healthy: $($service.HealthUri)"
      continue
    }

    $listenerProcessId = Get-ListenerProcessId -Port $service.Port
    if ($null -ne $listenerProcessId) {
      throw "Port $($service.Port) is occupied by PID $listenerProcessId, but $($service.Name) is not healthy."
    }

    $stdout = Join-Path $RuntimeDir "$($service.Name).log"
    $stderr = Join-Path $RuntimeDir "$($service.Name).error.log"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue
    $process = Start-Process `
      -FilePath $pythonCommand.Source `
      -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", [string]$service.Port) `
      -WorkingDirectory $service.WorkDir `
      -WindowStyle Hidden `
      -RedirectStandardOutput $stdout `
      -RedirectStandardError $stderr `
      -PassThru
    $started += [pscustomobject]@{ Process = $process; Service = $service }

    $deadline = (Get-Date).AddSeconds([Math]::Max($WaitSeconds, 30))
    $ready = $false
    while ((Get-Date) -lt $deadline) {
      Start-Sleep -Seconds 2
      if (Test-ServiceHealthy -Uri $service.HealthUri) {
        Start-Sleep -Seconds 2
        if (Test-ServiceHealthy -Uri $service.HealthUri) {
          $ready = $true
          break
        }
      }
      if ($process.HasExited) { break }
    }

    if (-not $ready) {
      $errorTail = if (Test-Path -LiteralPath $stderr) {
        (Get-Content -LiteralPath $stderr -Tail 30) -join " | "
      } else {
        "no error log"
      }
      throw "$($service.Name) did not become healthy within $WaitSeconds seconds. $errorTail"
    }

    $listenerProcessId = Get-ListenerProcessId -Port $service.Port
    $state += [pscustomobject]@{
      name = $service.Name
      port = $service.Port
      pid = $listenerProcessId
      started_by_runner = $true
      health_uri = $service.HealthUri
      stdout_log = $stdout
      stderr_log = $stderr
    }
    Write-Host "$($service.Name) ready: $($service.HealthUri)"
  }

  $tempStatePath = "$StatePath.tmp"
  $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $tempStatePath -Encoding UTF8
  Move-Item -LiteralPath $tempStatePath -Destination $StatePath -Force
  Write-Host "Analysis APIs ready. State: $StatePath"
} catch {
  foreach ($entry in $started) {
    if (-not $entry.Process.HasExited) {
      Stop-Process -Id $entry.Process.Id -Force -ErrorAction SilentlyContinue
    }
  }
  throw
}
