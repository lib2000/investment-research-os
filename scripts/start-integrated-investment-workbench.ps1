param(
  [string]$TradingApiRoot = "",
  [switch]$OpenConsole
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workspaceResolver = Join-Path $ProjectRoot "tools\resolve_investment_workspace.ps1"
. $workspaceResolver
$workspacePaths = Get-InvestmentWorkspacePaths -ProjectRoot $ProjectRoot
if ([string]::IsNullOrWhiteSpace($TradingApiRoot)) {
  $TradingApiRoot = $workspacePaths.TradingApiRoot
}
$TradingLauncher = Join-Path $TradingApiRoot "investment-web.ps1"

if (-not (Test-Path -LiteralPath $TradingLauncher)) {
  throw "전략 빌더/백테스터 실행기를 찾지 못했습니다: $TradingLauncher"
}

Write-Host "Investment Research OS 백엔드를 시작합니다."
& (Join-Path $ProjectRoot "scripts\restart-research-backend.ps1") -Port 8001 -WaitSeconds 30

Write-Host "전략 빌더와 백테스터를 시작합니다."
& $TradingLauncher start

$targets = @(
  @{ Name = "Research OS"; Url = "http://127.0.0.1:8001/console/index.html" },
  @{ Name = "Strategy Builder"; Url = "http://127.0.0.1:3100/builder" },
  @{ Name = "Backtester"; Url = "http://127.0.0.1:3200/backtest" }
)

foreach ($target in $targets) {
  $response = Invoke-WebRequest -UseBasicParsing -Uri $target.Url -TimeoutSec 15
  if ($response.StatusCode -ne 200) {
    throw "$($target.Name) 확인 실패: HTTP $($response.StatusCode)"
  }
  Write-Host "$($target.Name): $($target.Url)"
}

if ($OpenConsole) {
  Start-Process $targets[0].Url
}
