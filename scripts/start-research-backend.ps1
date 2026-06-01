param(
  [int]$Port = 8001,
  [string]$HostName = "127.0.0.1",
  [string]$PythonExe = "",
  [switch]$StopExistingPortProcess
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$BackendRoot = Join-Path $ProjectRootPath "backend"

if (-not (Test-Path (Join-Path $BackendRoot "research_os_main.py"))) {
  throw "Research OS 백엔드 진입점을 찾을 수 없습니다: $BackendRoot"
}

function Resolve-BackendPython {
  param([string]$RequestedPython)

  if ($RequestedPython) {
    if (Test-Path $RequestedPython) {
      return (Resolve-Path $RequestedPython).Path
    }
    $requestedCommand = Get-Command $RequestedPython -ErrorAction SilentlyContinue
    if ($requestedCommand) {
      return $requestedCommand.Source
    }
    throw "지정한 Python 실행 파일을 찾지 못했습니다: $RequestedPython"
  }

  $localCandidates = @(
    (Join-Path $ProjectRootPath ".venv-win\Scripts\python.exe"),
    (Join-Path $ProjectRootPath ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRootPath "venv\Scripts\python.exe")
  )
  foreach ($candidate in $localCandidates) {
    if (Test-Path $candidate) {
      return (Resolve-Path $candidate).Path
    }
  }

  foreach ($commandName in @("python", "py")) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
  }

  throw "Python 실행 파일을 찾지 못했습니다. Windows PowerShell에서 pip install -r backend\requirements.txt 실행 전 Python을 PATH에 추가하거나, .\scripts\start-research-backend.ps1 -PythonExe C:\Path\To\python.exe 처럼 직접 지정하세요."
}

$ResolvedPython = Resolve-BackendPython -RequestedPython $PythonExe
Write-Host "Python 실행 파일: $ResolvedPython"

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

function Stop-PortProcess {
  param([int]$LocalPort)

  foreach ($processId in @(Get-PortOwningProcessIds -LocalPort $LocalPort)) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      Write-Host "포트 $LocalPort 프로세스 종료: PID $processId ($($process.ProcessName))"
      Stop-Process -Id $processId -Force
    } catch {
      Write-Warning "포트 $LocalPort 프로세스 종료 실패: PID $processId - $($_.Exception.Message)"
    }
  }
}

function Assert-PortAvailable {
  param([int]$LocalPort)

  $processIds = @(Get-PortOwningProcessIds -LocalPort $LocalPort)
  if ($processIds.Count -eq 0) {
    return
  }
  $labels = foreach ($processId in $processIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      "$processId/$($process.ProcessName)"
    } catch {
      "$processId/unknown"
    }
  }
  throw "포트 $LocalPort 가 이미 사용 중입니다: $($labels -join ', '). .\tools\show_dev_server_ports.ps1 로 확인한 뒤 정리하거나 -StopExistingPortProcess를 사용하세요."
}

if ($StopExistingPortProcess) {
  Stop-PortProcess -LocalPort $Port
}

Assert-PortAvailable -LocalPort $Port

Push-Location $BackendRoot
try {
  & $ResolvedPython -m uvicorn research_os_main:app --host $HostName --port $Port
} finally {
  Pop-Location
}
