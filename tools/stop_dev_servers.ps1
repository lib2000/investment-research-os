param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [int[]]$Ports = @(8010, 8085),
  [switch]$DryRun,
  [int[]]$DefaultDevPorts = @(8010, 8085),
  [string[]]$AllowedProcessNames = @("python", "pythonw", "node", "pwsh", "powershell"),
  [switch]$ForceAnyProcess
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

function Get-PortOwningProcessIds {
  param([int]$Port)

  $processIds = @()

  $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -and $_.OwningProcess -gt 0 }
  if ($connections) {
    $processIds += @($connections | Select-Object -ExpandProperty OwningProcess)
  }
  if ($processIds.Count -gt 0) {
    return @($processIds | Sort-Object -Unique)
  }

  $netstatCommand = Get-Command netstat -ErrorAction SilentlyContinue
  if ($netstatCommand) {
    $netstatLines = & $netstatCommand.Source -ano 2>$null | Select-String -Pattern "[:.]$Port\s"
    foreach ($line in $netstatLines) {
      $parts = ($line.Line.Trim() -split "\s+") | Where-Object { $_ }
      if ($parts.Count -lt 4) {
        continue
      }

      $localAddress = $parts[1]
      $ownerText = $parts[-1]
      if ($localAddress -notmatch "[:.]$Port$") {
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

function Test-CanStopProcess {
  param(
    [int]$Port,
    [string]$ProcessName
  )

  if ($ForceAnyProcess) {
    return $true
  }

  if ($DefaultDevPorts -contains $Port) {
    return $true
  }

  if (-not $ProcessName -or $ProcessName -eq "이름 확인 불가") {
    return $false
  }

  return ($AllowedProcessNames -contains $ProcessName)
}

foreach ($port in $Ports) {
  $processIds = @(Get-PortOwningProcessIds -Port $port)

  if (-not $processIds -or $processIds.Count -eq 0) {
    Write-Host "포트 $port 실행 프로세스 없음"
    continue
  }

  foreach ($processId in $processIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
      $processName = if ($process) { $process.ProcessName } else { "이름 확인 불가" }
      if (-not (Test-CanStopProcess -Port $port -ProcessName $processName)) {
        Write-Warning "포트 $port 프로세스 종료 건너뜀: PID $processId ($processName). 기본 개발 포트가 아니며 허용된 개발 프로세스가 아닙니다. 강제 종료가 필요하면 -ForceAnyProcess를 사용하세요."
        continue
      }
      if ($DryRun) {
        Write-Host "포트 $port 프로세스 종료 예정: PID $processId ($processName)"
        continue
      }
      Write-Host "포트 $port 프로세스 종료: PID $processId ($processName)"
      Stop-Process -Id $processId -Force
    } catch {
      if (-not (Test-CanStopProcess -Port $port -ProcessName "이름 확인 불가")) {
        Write-Warning "포트 $port 프로세스 종료 건너뜀: PID $processId (이름 확인 불가). 기본 개발 포트가 아니므로 강제 종료가 필요하면 -ForceAnyProcess를 사용하세요."
        continue
      }
      if ($DryRun) {
        Write-Host "포트 $port 프로세스 종료 예정: PID $processId (이름 확인 불가)"
        continue
      }
      Write-Warning "포트 $port Stop-Process 실패: PID $processId - $($_.Exception.Message)"
      taskkill /PID $processId /F 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) {
        Write-Host "포트 $port 프로세스 taskkill 종료: PID $processId"
      } else {
        Write-Warning "포트 $port taskkill 실패: PID $processId"
      }
    }
  }

  if (-not $DryRun) {
    Start-Sleep -Milliseconds 500
    $remainingProcessIds = @(Get-PortOwningProcessIds -Port $port)
    if ($remainingProcessIds.Count -gt 0) {
      throw "포트 $port 리스너가 아직 남아 있습니다: PID $($remainingProcessIds -join ', '). 관리자 권한이 필요하거나 OS가 아직 포트를 해제하지 않았을 수 있습니다."
    }
  }
}
