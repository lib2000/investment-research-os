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
$wslKeepaliveReady = $false
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
  # In this Windows/WSL setup the distro is stopped after the final wsl.exe
  # client exits, even with an enabled user service. Keep one hidden client
  # attached so OpenClaw remains reachable after this scheduled task ends.
  #
  # Do not use `bash -lc` here. Start-Process flattens argument arrays and can
  # split the shell command after `-c`, which made the old keepalive exit
  # immediately at logon. A direct sleep exec has no shell quoting boundary.
  $keepaliveName = "investment-research-wsl-keepalive"
  $keepaliveSeconds = "2147483647"
  $escapedDistro = [regex]::Escape($OpenClawWslDistro)
  $directKeepalivePattern = [regex]::Escape("/usr/bin/sleep $keepaliveSeconds")
  # Keep existing long-lived clients from earlier registrations compatible.
  # They still keep this distro alive until the next clean boot creates the
  # direct, identifiable form above.
  $legacyKeepalivePattern = [regex]::Escape("/usr/bin/sleep infinity")
  $existingKeepalive = @(
    Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" -ErrorAction SilentlyContinue |
      Where-Object {
        $commandLine = [string]$_.CommandLine
        $commandLine -match $escapedDistro -and (
          $commandLine -match [regex]::Escape($keepaliveName) -or
          $commandLine -match $directKeepalivePattern -or
          $commandLine -match $legacyKeepalivePattern
        )
      }
  )
  if ($existingKeepalive.Count -eq 0) {
    $keepaliveArguments = "-d $OpenClawWslDistro --user root --exec /usr/bin/sleep $keepaliveSeconds"
    $keepaliveProcess = Start-Process -FilePath "wsl.exe" -ArgumentList $keepaliveArguments -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    $wslKeepaliveReady = -not $keepaliveProcess.HasExited
  } else {
    $wslKeepaliveReady = $true
  }
  if (-not $wslKeepaliveReady) {
    throw "WSL keepalive 프로세스를 시작하지 못했습니다."
  }
  $userBusReady = $false
  for ($attempt = 1; $attempt -le 8; $attempt++) {
    # Use WSL's direct exec path.  A login shell can wait on a systemd user
    # session during cold boot and make the logon task time out even though
    # the user bus is already usable.
    # WSL can emit a transient systemd-session warning on stderr even when the
    # command succeeds. Do not let Windows PowerShell turn that warning into a
    # terminating NativeCommandError; the exit code and stdout are authoritative.
    $userBusState = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user is-active default.target 2>$null
    if ($LASTEXITCODE -eq 0 -and "$userBusState" -match "(?m)^active\s*$") {
      $userBusReady = $true
      break
    }
    Start-Sleep -Seconds 2
  }
  if (-not $userBusReady) {
    throw "WSL systemd 사용자 세션이 준비되지 않았습니다. 로그인 직후 사용자 버스가 늦게 올라왔을 수 있습니다."
  }
  $openClawOutput = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user start openclaw-gateway.service 2>$null
  if ($LASTEXITCODE -ne 0) {
    throw "WSL OpenClaw 게이트웨이 사용자 서비스를 시작하지 못했습니다."
  }
  $listenerProbe = "import socket; s=socket.socket(); s.settimeout(0.5); r=s.connect_ex(('127.0.0.1',18789)); s.close(); print(1 if r == 0 else 0)"
  for ($attempt = 1; $attempt -le 18; $attempt++) {
    $openClawState = & wsl.exe -d $OpenClawWslDistro --user lib2000 --exec systemctl --user is-active openclaw-gateway.service 2>$null
    $serviceActive = $LASTEXITCODE -eq 0 -and "$openClawState" -match "(?m)^active\s*$"
    $listenerState = & wsl.exe -d $OpenClawWslDistro --user root --exec python3 -c $listenerProbe 2>$null
    $listenerReady = $LASTEXITCODE -eq 0 -and "$listenerState" -match "(?m)^1\s*$"
    if ($serviceActive -and $listenerReady) {
      $openClawGatewayReady = $true
      break
    }
    Start-Sleep -Seconds 5
  }
  if (-not $openClawGatewayReady) {
    throw "WSL OpenClaw 게이트웨이가 90초 안에 실제 18789 리스너를 열지 못했습니다."
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
    wsl_keepalive_ready = $wslKeepaliveReady
    wsl_keepalive_mode = if ($existingKeepalive.Count -gt 0) { "existing" } else { "direct_root_sleep" }
    openclaw_gateway_ready = $openClawGatewayReady
    message = $message
    project_root = $ProjectRootPath
  }
  $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

if ($status -ne "success") {
  throw $message
}
