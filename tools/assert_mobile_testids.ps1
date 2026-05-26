param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp"
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$appShellPath = Join-Path $ProjectRootPath "apps\mobile\src\screens\AppShell.tsx"
$readmePath = Join-Path $ProjectRootPath "apps\mobile\README.md"

if (-not (Test-Path -LiteralPath $appShellPath)) {
  throw "모바일 AppShell 파일을 찾을 수 없습니다: $appShellPath"
}
if (-not (Test-Path -LiteralPath $readmePath)) {
  throw "모바일 README 파일을 찾을 수 없습니다: $readmePath"
}

$appShell = Get-Content -LiteralPath $appShellPath -Raw
$readme = Get-Content -LiteralPath $readmePath -Raw

$requiredAppShellSnippets = @(
  'testID={`tab-${tab.key}`}',
  'testID={`analytics-range-${range.key}`}',
  'testIDPrefix="analytics-profit-basis"',
  'testIDPrefix="analytics-allocation-basis"',
  'testID="manual-csv-input"',
  'testID="manual-csv-template-button"',
  'testID="manual-csv-pick-file-button"',
  'testID="manual-csv-fill-sample-button"',
  'testID="manual-csv-import-button"',
  'testID="analytics-empty-range"',
  'testID="analytics-profit-empty"',
  'testID="analytics-trend-empty"',
  'testID="analytics-allocation-empty"',
  'testID="analytics-dividend-empty"',
  'testID="analytics-cost-empty"',
  'testID="analytics-profit-chart"',
  'testID="analytics-trend-chart"',
  'testID="analytics-allocation-chart"',
  'testID="analytics-dividend-chart"',
  'testID="analytics-cost-chart"'
)

$requiredReadmeTokens = @(
  'tab-portfolio',
  'tab-drafts',
  'tab-entries',
  'tab-manual',
  'tab-analytics',
  'analytics-range-1m',
  'analytics-range-3m',
  'analytics-range-6m',
  'analytics-range-1y',
  'analytics-range-all',
  'analytics-profit-basis-monthly',
  'analytics-profit-basis-quarterly',
  'analytics-profit-basis-annual',
  'analytics-allocation-basis-ticker',
  'analytics-allocation-basis-type',
  'analytics-allocation-basis-account',
  'analytics-empty-range',
  'analytics-profit-empty',
  'analytics-trend-empty',
  'analytics-allocation-empty',
  'analytics-dividend-empty',
  'analytics-cost-empty',
  'manual-csv-input',
  'manual-csv-template-button',
  'manual-csv-pick-file-button',
  'manual-csv-fill-sample-button',
  'manual-csv-import-button',
  'analytics-profit-chart',
  'analytics-trend-chart',
  'analytics-allocation-chart',
  'analytics-dividend-chart',
  'analytics-cost-chart'
)

$missing = @()
foreach ($snippet in $requiredAppShellSnippets) {
  if (-not $appShell.Contains($snippet)) {
    $missing += "AppShell.tsx: $snippet"
  }
}

foreach ($token in $requiredReadmeTokens) {
  if (-not $readme.Contains($token)) {
    $missing += "apps/mobile/README.md: $token"
  }
}

if ($missing.Count -gt 0) {
  $message = "모바일 testID 검증 실패:`n" + ($missing -join "`n")
  throw $message
}

Write-Host "OK 모바일 testID 검증 통과"
