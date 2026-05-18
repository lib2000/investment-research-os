param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [switch]$PassThru
)

$ErrorActionPreference = "Stop"

$ExpectedRoot = "C:\Users\lib20\InvestmentJournalApp"
$resolved = Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop
$rootPath = $resolved.Path.TrimEnd("\")

if ($rootPath -like "*\OneDrive\*") {
  throw "OneDrive 경로에서는 InvestmentJournalApp 작업을 실행하지 않습니다: $rootPath"
}

if ($rootPath -ne $ExpectedRoot) {
  throw "활성 프로젝트 루트가 아닙니다. 현재: $rootPath / 기준: $ExpectedRoot"
}

if (-not (Test-Path -LiteralPath (Join-Path $rootPath "backend\main.py"))) {
  throw "투자일지 백엔드 진입점을 찾을 수 없습니다: $rootPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $rootPath "apps\mobile\package.json"))) {
  throw "Expo 모바일 앱 경로를 찾을 수 없습니다: $rootPath"
}

if ($PassThru) {
  Write-Output $rootPath
}
