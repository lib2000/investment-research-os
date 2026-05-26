param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8010,
  [int[]]$FallbackPorts = @(),
  [string]$DevUserToken = "dev-local-token",
  [int]$TimeoutSeconds = 20,
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$backendPath = Join-Path $ProjectRootPath "backend"
if (-not (Test-Path -LiteralPath $backendPath)) {
  throw "백엔드 경로를 찾을 수 없습니다: $backendPath"
}

$tempDir = Join-Path $ProjectRootPath ".test-tmp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$candidatePorts = @($Port) + @($FallbackPorts) | Select-Object -Unique
$attemptErrors = @()

foreach ($candidatePort in $candidatePorts) {
  Write-Output "기존 백엔드 포트를 정리합니다: $candidatePort"
  try {
    & (Join-Path $PSScriptRoot "stop_dev_servers.ps1") -ProjectRoot $ProjectRootPath -Ports @($candidatePort)
  } catch {
    $attemptErrors += "포트 $candidatePort 정리 실패: $($_.Exception.Message)"
    continue
  }

  $stdoutLog = Join-Path $tempDir "backend-$candidatePort.out.log"
  $stderrLog = Join-Path $tempDir "backend-$candidatePort.err.log"

  $uvicornArgs = @("-m", "uvicorn", "main:app", "--host", $HostName, "--port", "$candidatePort")
  if ($Reload) {
    $uvicornArgs += "--reload"
  }

  Write-Output "백엔드를 백그라운드에서 시작합니다: http://$HostName`:$candidatePort"
  $process = Start-Process `
    -FilePath "python.exe" `
    -ArgumentList $uvicornArgs `
    -WorkingDirectory $backendPath `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

  $baseUrl = "http://$HostName`:$candidatePort"
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $lastError = $null

  try {
    while ((Get-Date) -lt $deadline) {
      if ($process.HasExited) {
        $stderr = if (Test-Path -LiteralPath $stderrLog) { Get-Content -LiteralPath $stderrLog -Raw } else { "" }
        throw "백엔드 프로세스가 시작 직후 종료되었습니다. PID=$($process.Id)`n$stderr"
      }

      try {
        $openapi = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -TimeoutSec 3
        $paths = @($openapi.paths.PSObject.Properties.Name)
        if ($paths -notcontains "/api/v1/manual-transactions/import.csv/template") {
          throw "openapi에 CSV 템플릿 라우트가 없습니다. 오래된 백엔드 코드가 실행 중일 수 있습니다."
        }

        $headers = @{ Authorization = "Bearer $DevUserToken" }
        $template = Invoke-WebRequest -Uri "$baseUrl/api/v1/manual-transactions/import.csv/template" -Headers $headers -UseBasicParsing -TimeoutSec 3
        if ($template.StatusCode -ne 200 -or $template.Headers["Content-Disposition"] -notlike "*manual-transactions-template.csv*") {
          throw "CSV 템플릿 API 응답 검증에 실패했습니다."
        }

        $result = [PSCustomObject]@{
          Status = "success"
          Message = "백엔드 재시작 및 CSV 템플릿 API 검증 완료"
          Pid = $process.Id
          Url = $baseUrl
          Port = $candidatePort
          RequestedPort = $Port
          UsedFallback = ($candidatePort -ne $Port)
          StdoutLog = $stdoutLog
          StderrLog = $stderrLog
        }
        Write-Host ($result | ConvertTo-Json -Depth 4)
        return
      } catch {
        $lastError = $_.Exception.Message
        Start-Sleep -Milliseconds 500
      }
    }

    throw "백엔드 재시작 검증이 제한 시간 내 완료되지 않았습니다. 마지막 오류: $lastError"
  } catch {
    $attemptErrors += "포트 $candidatePort 실패: $($_.Exception.Message)"
    if ($process -and -not $process.HasExited) {
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}

throw "사용 가능한 백엔드 포트를 검증하지 못했습니다.`n$($attemptErrors -join "`n")"
