param(
  [int]$Port = 8001,
  [string]$HostName = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ProjectRootPath = & (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$BackendRoot = Join-Path $ProjectRootPath "backend"

if (-not (Test-Path (Join-Path $BackendRoot "research_os_main.py"))) {
  throw "Research OS 백엔드 진입점을 찾을 수 없습니다: $BackendRoot"
}

Push-Location $BackendRoot
try {
  python -m uvicorn research_os_main:app --host $HostName --port $Port
} finally {
  Pop-Location
}
