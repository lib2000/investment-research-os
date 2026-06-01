param(
  [int]$Port = 8001,
  [string]$HostName = "127.0.0.1",
  [int]$WaitSeconds = 20,
  [switch]$OpenConsole
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRootPath = & (Join-Path $ProjectRoot "tools/assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$StartScript = Join-Path $ProjectRootPath "scripts\start-research-backend.ps1"
$LogDir = Join-Path $ProjectRootPath "tmp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$StdoutLog = Join-Path $LogDir "research-backend-$Port.out.log"
$StderrLog = Join-Path $LogDir "research-backend-$Port.err.log"
$BaseUrl = "http://$HostName`:$Port"

if (-not (Test-Path -LiteralPath $StartScript)) {
  throw "백엔드 시작 스크립트를 찾지 못했습니다: $StartScript"
}

function Get-PortOwningProcessIds {
  param([int]$LocalPort)

  $processIds = @()
  $connections = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -and $_.OwningProcess -gt 0 }
  if ($connections) {
    $processIds += @($connections | Select-Object -ExpandProperty OwningProcess)
  }

  $netstatCommand = Get-Command netstat -ErrorAction SilentlyContinue
  if ($netstatCommand) {
    $netstatLines = & $netstatCommand.Source -ano 2>$null |
      Select-String -Pattern "[:.]$LocalPort\s" |
      Select-String -Pattern "LISTENING"
    foreach ($line in $netstatLines) {
      $parts = ($line.Line.Trim() -split "\s+") | Where-Object { $_ }
      if ($parts.Count -lt 4) {
        continue
      }
      $localAddress = $parts[1]
      $ownerText = $parts[-1]
      if ($localAddress -notmatch "[:.]$LocalPort$") {
        continue
      }
      $ownerProcessId = 0
      if ([int]::TryParse($ownerText, [ref]$ownerProcessId) -and $ownerProcessId -gt 0) {
        $processIds += $ownerProcessId
      }
    }
  }

  return @($processIds | Sort-Object -Unique)
}

function Test-ResearchBackendCommandLine {
  param(
    [string]$CommandLine,
    [int]$LocalPort
  )

  if ([string]::IsNullOrWhiteSpace($CommandLine)) {
    return $false
  }

  $portPattern = "(^|\s)--port\s+$LocalPort(\s|$)"
  return ($CommandLine -like "*uvicorn*" -and
    $CommandLine -like "*research_os_main:app*" -and
    $CommandLine -match $portPattern)
}

function Get-ResearchBackendProcessInfo {
  param([int]$LocalPort)

  return @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { Test-ResearchBackendCommandLine -CommandLine ([string]$_.CommandLine) -LocalPort $LocalPort })
}

function Stop-ResearchBackendProcesses {
  param([int]$LocalPort)

  $processes = @(Get-ResearchBackendProcessInfo -LocalPort $LocalPort)
  foreach ($process in $processes) {
    try {
      Write-Host "중복 백엔드 프로세스 정리: PID $($process.ProcessId)"
      Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
    } catch {
      Write-Warning "중복 백엔드 프로세스 정리 실패: PID $($process.ProcessId) - $($_.Exception.Message)"
    }
  }

  if ($processes.Count -gt 0) {
    Start-Sleep -Seconds 1
  }
}

function Assert-SingleResearchBackendListener {
  param([int]$LocalPort)

  $listenerProcessIds = @(Get-PortOwningProcessIds -LocalPort $LocalPort)
  if ($listenerProcessIds.Count -ne 1) {
    throw "백엔드 포트 단일성 확인 실패: $LocalPort 리스너 $($listenerProcessIds.Count)개 발견. PIDs=$($listenerProcessIds -join ', ')"
  }

  $processes = @(Get-ResearchBackendProcessInfo -LocalPort $LocalPort)
  $backendProcessIds = @($processes | Select-Object -ExpandProperty ProcessId)
  if ($backendProcessIds.Count -eq 0 -or $backendProcessIds -notcontains $listenerProcessIds[0]) {
    $labels = foreach ($process in $processes) {
      "PID $($process.ProcessId): $($process.CommandLine)"
    }
    throw "백엔드 포트 소유자가 research_os_main:app 프로세스로 확인되지 않았습니다. listener=$($listenerProcessIds[0]), backend=$($labels -join ' | ')"
  }

  Write-Host "백엔드 포트 단일성 확인 완료: listener PID $($listenerProcessIds[0]), 관련 프로세스 $($processes.Count)개"
}

$arguments = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $StartScript,
  "-Port", "$Port",
  "-HostName", $HostName,
  "-StopExistingPortProcess"
)

Write-Host "Research OS 백엔드를 재시작합니다: $BaseUrl"
Write-Host "표준 출력 로그: $StdoutLog"
Write-Host "오류 로그: $StderrLog"
Stop-ResearchBackendProcesses -LocalPort $Port

Start-Process `
  -FilePath "powershell.exe" `
  -ArgumentList $arguments `
  -WorkingDirectory $ProjectRootPath `
  -RedirectStandardOutput $StdoutLog `
  -RedirectStandardError $StderrLog `
  -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$lastError = $null
$headers = @{ Authorization = "Bearer dev-local-token" }
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 1
  try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/api/v1/system/health" -Headers $headers -TimeoutSec 3
    $console = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/console/index.html" -TimeoutSec 3
    if ($health.status -eq "success" -and $console.StatusCode -eq 200) {
      Write-Host "재시작 확인 완료: health=$($health.status), console=$($console.StatusCode)"
      Assert-SingleResearchBackendListener -LocalPort $Port
      Write-Host "콘솔 주소: $BaseUrl/console/index.html"
      if ($OpenConsole) {
        Start-Process "$BaseUrl/console/index.html"
      }
      return
    }
  } catch {
    $lastError = $_.Exception.Message
  }
}

Write-Host "백엔드 재시작 확인 실패. 마지막 오류: $lastError"
Write-Host "표준 출력 로그 확인: $StdoutLog"
Write-Host "오류 로그 확인: $StderrLog"
throw "Research OS 백엔드가 $WaitSeconds 초 안에 정상 응답하지 않았습니다."
