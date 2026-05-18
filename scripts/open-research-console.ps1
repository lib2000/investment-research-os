param(
  [int]$Port = 5500
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$ConsoleRoot = Join-Path $ProjectRootPath "mobile_app\research_console"

if (-not (Test-Path (Join-Path $ConsoleRoot "index.html"))) {
  throw "Classic Research Console index.html을 찾을 수 없습니다: $ConsoleRoot"
}

Push-Location $ConsoleRoot
try {
  python -m http.server $Port --bind 127.0.0.1
} finally {
  Pop-Location
}
