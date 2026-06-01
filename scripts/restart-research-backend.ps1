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
