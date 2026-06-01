param(
  [ValidateSet("Both", "Menus", "Clicks")]
  [string]$Mode = "Both",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [switch]$FullClicks,
  [switch]$IncludeWriteActions
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot (Resolve-Path (Join-Path $PSScriptRoot "..")) -PassThru
$LogDir = Join-Path $ProjectRootPath "tmp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Resolve-WindowsPython {
  $candidates = @(
    (Join-Path $ProjectRootPath ".venv-win\Scripts\python.exe"),
    "C:\Users\lib20\AppData\Local\Programs\Python\Python312\python.exe"
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      return (Resolve-Path $candidate).Path
    }
  }

  foreach ($commandName in @("python", "py")) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
  }

  throw "Windows Python 실행 파일을 찾지 못했습니다. .venv-win 또는 Python 3.12 설치 상태를 확인하세요."
}

function Invoke-SmokeScript {
  param(
    [string]$Name,
    [string]$PythonExe,
    [string]$ScriptPath,
    [string[]]$Arguments
  )

  $stdoutPath = Join-Path $LogDir "research-console-$Name.out.json"
  $stderrPath = Join-Path $LogDir "research-console-$Name.err.log"
  Remove-Item -Force $stdoutPath, $stderrPath -ErrorAction SilentlyContinue

  $argumentList = @($ScriptPath) + $Arguments
  Write-Host "실제 브라우저 스모크 실행: $Name"
  $process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $argumentList `
    -WorkingDirectory $ProjectRootPath `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -Wait `
    -PassThru `
    -NoNewWindow

  $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8 } else { "" }
  $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8 } else { "" }
  if ($process.ExitCode -ne 0) {
    throw "$Name 스모크 실패(exit=$($process.ExitCode)). stdout=$stdout stderr=$stderr"
  }

  try {
    $payload = $stdout | ConvertFrom-Json
  } catch {
    throw "$Name 스모크 출력 JSON 파싱 실패: $($_.Exception.Message) | stdout=$stdout"
  }
  if ($payload.status -ne "success") {
    throw "$Name 스모크 상태 실패: $($payload.status) | $stdout"
  }

  Write-Host "정상 $Name 스모크 통과"
  return $payload
}

$pythonExe = Resolve-WindowsPython
Write-Host "Windows Python: $pythonExe"

$results = @{}
if ($Mode -in @("Both", "Menus")) {
  $menuArgs = @("--url", "$BaseUrl/console/index.html?smoke=menus-windows")
  if ($IncludeWriteActions) {
    $menuArgs += "--include-write-actions"
  }
  $results.Menus = Invoke-SmokeScript `
    -Name "menus-windows" `
    -PythonExe $pythonExe `
    -ScriptPath (Join-Path $ProjectRootPath "tools\smoke_research_console_menus.py") `
    -Arguments $menuArgs
}

if ($Mode -in @("Both", "Clicks")) {
  $clickArgs = @("--url", "$BaseUrl/console/index.html?smoke=clicks-windows")
  if (-not $FullClicks) {
    $clickArgs += "--only-system-check"
  }
  $results.Clicks = Invoke-SmokeScript `
    -Name "clicks-windows" `
    -PythonExe $pythonExe `
    -ScriptPath (Join-Path $ProjectRootPath "tools\smoke_research_console_clicks.py") `
    -Arguments $clickArgs
}

Write-Host "실제 브라우저 스모크 검증 완료: $Mode"
