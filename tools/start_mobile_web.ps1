param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$HostName = "localhost",
  [int]$Port = 8082,
  [string]$ApiBaseUrl = "http://127.0.0.1:8010",
  [switch]$StopExistingPortProcess,
  [switch]$ForceExistingPortProcess,
  [switch]$ClearCache
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

function Get-PortOwningProcessIds {
  param([int]$LocalPort)

  $processIds = @()

  $connections = Get-NetTCPConnection -LocalPort $LocalPort -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -and $_.OwningProcess -gt 0 }
  if ($connections) {
    $processIds += @($connections | Select-Object -ExpandProperty OwningProcess)
  }
  if ($processIds.Count -gt 0) {
    return @($processIds | Sort-Object -Unique)
  }

  # Get-NetTCPConnection can miss some listeners on Windows depending on shell privileges.
  # netstat is slower, but it is a reliable fallback for local dev port cleanup.
  $netstatLines = netstat -ano 2>$null |
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

  return @($processIds | Sort-Object -Unique)
}

function Stop-PortProcess {
  param([int]$LocalPort)

  $processIds = @(Get-PortOwningProcessIds -LocalPort $LocalPort)
  if (-not $processIds -or $processIds.Count -eq 0) {
    Write-Host "포트 $LocalPort 잔류 프로세스 없음"
    return
  }

  foreach ($processId in $processIds) {
    $process = $null
    $processName = "unknown"
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      $processName = $process.ProcessName
    } catch {
      $processName = "unknown"
    }

    if (-not $ForceExistingPortProcess -and $processName -eq "unknown") {
      Write-Warning "포트 $LocalPort 프로세스 종료 건너뜀: PID $processId (unknown). .\tools\show_dev_server_ports.ps1 로 확인한 뒤 관리자 권한 정리 또는 다른 예약 포트를 사용하세요."
      continue
    }

    try {
      Write-Host "포트 $LocalPort 프로세스 종료: PID $processId ($processName)"
      Stop-Process -Id $processId -Force
    } catch {
      Write-Warning "포트 $LocalPort Stop-Process 실패: PID $processId - $($_.Exception.Message)"
      if (-not $ForceExistingPortProcess) {
        Write-Warning "강제 taskkill은 실행하지 않았습니다. 정말 강제 종료하려면 -ForceExistingPortProcess를 함께 사용하세요."
        continue
      }
      taskkill /PID $processId /F 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) {
        Write-Host "포트 $LocalPort 프로세스 taskkill 종료: PID $processId"
      } else {
        Write-Warning "포트 $LocalPort taskkill 실패: PID $processId"
      }
    }
  }
}

if ($StopExistingPortProcess) {
  Stop-PortProcess -LocalPort $Port
}

$existingProcessIds = @(Get-PortOwningProcessIds -LocalPort $Port)
if ($existingProcessIds.Count -gt 0) {
  $processLabels = foreach ($processId in $existingProcessIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      "$processId/$($process.ProcessName)"
    } catch {
      "$processId/unknown"
    }
  }
  throw "포트 $Port 가 이미 사용 중입니다: $($processLabels -join ', '). .\tools\show_dev_server_ports.ps1 로 확인한 뒤 정리하거나 -StopExistingPortProcess를 사용하세요."
}

$mobilePath = Join-Path $ProjectRootPath "apps\mobile"
if (-not (Test-Path -LiteralPath $mobilePath)) {
  throw "모바일 앱 경로를 찾을 수 없습니다: $mobilePath"
}

$env:EXPO_PUBLIC_API_BASE_URL = $ApiBaseUrl

Set-Location -LiteralPath $mobilePath
Write-Host "Expo 모바일 웹 미리보기를 시작합니다."
Write-Host "URL: http://$HostName`:$Port"
Write-Host "API: $ApiBaseUrl"
if ($ClearCache) {
  Write-Host "Metro 캐시를 비우고 시작합니다."
}

$expoArgs = @("expo", "start", "--web", "--host", $HostName, "--port", "$Port")
if ($ClearCache) {
  $expoArgs += "--clear"
}

npx @expoArgs
