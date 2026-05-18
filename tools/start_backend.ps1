param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8010,
  [int]$LegacyPort = 8000,
  [switch]$SkipLegacyPortCleanup
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

function Stop-LegacyPortProcess {
  param([int]$LocalPort)

  $connections = Get-NetTCPConnection -LocalPort $LocalPort -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -and $_.OwningProcess -gt 0 }

  $processIds = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
  if (-not $processIds -or $processIds.Count -eq 0) {
    Write-Host "포트 $LocalPort 잔류 프로세스 없음"
    return
  }

  foreach ($processId in $processIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      Write-Host "포트 $LocalPort 프로세스 종료: PID $processId ($($process.ProcessName))"
      Stop-Process -Id $processId -Force
    } catch {
      Write-Warning "포트 $LocalPort 프로세스 종료 실패: PID $processId - $($_.Exception.Message)"
    }
  }
}

if (-not $SkipLegacyPortCleanup) {
  Stop-LegacyPortProcess -LocalPort $LegacyPort
}

$backendPath = Join-Path $ProjectRootPath "backend"
if (-not (Test-Path -LiteralPath $backendPath)) {
  throw "백엔드 경로를 찾을 수 없습니다: $backendPath"
}

Set-Location -LiteralPath $backendPath
python -m uvicorn main:app --reload --host $HostName --port $Port
