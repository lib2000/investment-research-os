param(
  [string]$ProjectRoot = "",
  [switch]$DueOnly,
  [switch]$Force,
  [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$projectPythonDirectory = Join-Path $ProjectRootPath ".venv-win\Scripts"
$projectPython = Join-Path $projectPythonDirectory "python.exe"
if (Test-Path -LiteralPath $projectPython) {
  $env:PATH = "$projectPythonDirectory;$env:PATH"
}

if ([string]::IsNullOrWhiteSpace($LogPath)) {
  $LogPath = Join-Path $ProjectRootPath "research_vault\_system\pension_rebalancing_task.log"
}
$logDirectory = Split-Path -Parent $LogPath
if ($logDirectory) {
  New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
}

function Write-PensionRebalancingLog {
  param([string]$Level, [string]$Message)
  $line = "[{0}] [{1}] {2}" -f (Get-Date).ToString("o"), $Level, ($Message -replace "[\r\n]+", " | ")
  [System.IO.File]::AppendAllText($LogPath, "$line`r`n", [System.Text.UTF8Encoding]::new($false))
}

try {
  $arguments = @("tools\run_pension_rebalancing.py", "--json")
  if ($DueOnly.IsPresent) { $arguments += "--due-only" }
  if ($Force.IsPresent) { $arguments += "--force" }
  Write-PensionRebalancingLog -Level "START" -Message "pension rebalancing review started"
  $result = & python @arguments 2>&1
  $exitCode = $LASTEXITCODE
  foreach ($line in $result) { Write-Output $line }
  if ($exitCode -ne 0) {
    throw "연금 리밸런싱 Python 러너 실패: 종료 코드 $exitCode"
  }
  Write-PensionRebalancingLog -Level "OK" -Message "pension rebalancing review finished"
  exit 0
} catch {
  Write-PensionRebalancingLog -Level "ERROR" -Message $_.Exception.Message
  throw
}
