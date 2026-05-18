param(
  [int]$Port = 8001
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"

if ($ProjectRoot -match "\\OneDrive(\\|$)") {
  throw "OneDrive 경로에서는 Research OS를 실행하지 않습니다. C:\Users\lib20\InvestmentJournalApp 에서 실행하세요."
}

if (-not (Test-Path $BackendDir)) {
  throw "backend 폴더를 찾지 못했습니다: $BackendDir"
}

$serverPids = netstat -ano |
  Select-String "LISTENING" |
  Select-String ":$Port\s" |
  ForEach-Object { ($_ -split "\s+")[-1] } |
  Where-Object { $_ -match "^\d+$" -and $_ -ne "0" } |
  Select-Object -Unique

foreach ($serverPid in $serverPids) {
  Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

$env:BLOCK_ONEDRIVE_PATHS = "true"
$env:RESEARCH_VAULT_DIR = "../research_vault"

Start-Process `
  -FilePath python `
  -ArgumentList @("-m", "uvicorn", "research_os_main:app", "--host", "127.0.0.1", "--port", "$Port") `
  -WorkingDirectory $BackendDir `
  -WindowStyle Hidden

Start-Sleep -Seconds 4

$status = Invoke-RestMethod "http://127.0.0.1:$Port/api/v1/data-providers/status"
$page = Invoke-WebRequest "http://127.0.0.1:$Port/console/index.html" -UseBasicParsing

[pscustomobject]@{
  backend = $status.status
  data_mode = $status.mode
  page_status = $page.StatusCode
  console_url = "http://127.0.0.1:$Port/console/index.html"
} | Format-List
