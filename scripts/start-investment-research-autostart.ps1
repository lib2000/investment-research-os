param(
  [string]$ProjectRoot = "D:\workspace\InvestmentJournalApp",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [string]$OpenClawWslDistro = "Ubuntu-24.04",
  [string]$StateFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$CredentialHelper = Join-Path $ProjectRootPath "tools\investment_research_credential.ps1"
$Launcher = Join-Path $ProjectRootPath "investment-research-os.ps1"
$StatePath = if ($StateFile) { [IO.Path]::GetFullPath($StateFile) } else { Join-Path $ProjectRootPath "tmp\investment_research_autostart_state.json" }
$LogPath = Join-Path $ProjectRootPath "tmp\investment_research_autostart.log"

. $CredentialHelper
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StatePath) | Out-Null
$startedAt = (Get-Date).ToString("o")
$token = $null
$credentialLoaded = $false
$openClawGatewayReady = $false
$status = "failed"
$exitCode = 1
$message = "자동 시작 실행 전 오류"

try {
  $token = Get-InvestmentResearchCredentialSecret -Target $CredentialTarget
  if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Windows Credential Manager에 자동 시작 자격 증명이 없습니다."
  }
  $credentialLoaded = $true
  $env:DEV_USER_TOKEN = $token
  $userBusReady = $false
  for ($attempt = 1; $attempt -le 8; $attempt++) {
    # Use WSL's direct exec path.  A login shell can wait on a systemd user
    # session during cold boot and make the logon task time out even though
    # the user bus is already usable.
    $userBusState = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user is-active default.target 2>&1
    if ($LASTEXITCODE -eq 0 -and "$userBusState" -match "(?m)^active\s*$") {
      $userBusReady = $true
      break
    }
    Start-Sleep -Seconds 2
  }
  if (-not $userBusReady) {
    throw "WSL systemd 사용자 세션이 준비되지 않았습니다. 로그인 직후 사용자 버스가 늦게 올라왔을 수 있습니다."
  }
  $openClawOutput = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user start openclaw-gateway.service 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "WSL OpenClaw 게이트웨이 사용자 서비스를 시작하지 못했습니다."
  }
  $openClawState = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user is-active openclaw-gateway.service 2>$null
  $openClawGatewayReady = $LASTEXITCODE -eq 0 -and "$openClawState" -match "(?m)^active\s*$"
  if (-not $openClawGatewayReady) {
    throw "WSL OpenClaw 게이트웨이 사용자 서비스가 active 상태가 아닙니다."
  }
  $output = & $Launcher start 2>&1
  $launcherSucceeded = $?
  $exitCode = if ($launcherSucceeded) { 0 } else { 1 }
  $outputText = ($output | Out-String -Width 240).Trim()
  if ($outputText) {
    "[$((Get-Date).ToString('o'))]`n$outputText" | Add-Content -LiteralPath $LogPath -Encoding UTF8
  }
  if ($exitCode -ne 0) {
    throw "통합 실행기가 종료 코드 $exitCode`을 반환했습니다."
  }
  $status = "success"
  $message = "투자 리서치 OS 통합 작업대 자동 시작을 확인했습니다."
} catch {
  $message = $_.Exception.Message
  "[$((Get-Date).ToString('o'))] ERROR $message" | Add-Content -LiteralPath $LogPath -Encoding UTF8
} finally {
  Remove-Item Env:DEV_USER_TOKEN -ErrorAction SilentlyContinue
  $token = $null
  $state = [ordered]@{
    status = $status
    started_at = $startedAt
    completed_at = (Get-Date).ToString("o")
    exit_code = $exitCode
    credential_target = $CredentialTarget
    credential_configured = $credentialLoaded
    openclaw_gateway_ready = $openClawGatewayReady
    message = $message
    project_root = $ProjectRootPath
  }
  $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

if ($status -ne "success") {
  throw $message
}
