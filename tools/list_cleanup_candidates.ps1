param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp"
)

$ErrorActionPreference = "Stop"

$Root = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

$topLevelPatterns = @(".codex_migration_backup_*", "research_vault_*_tmp")
foreach ($pattern in $topLevelPatterns) {
  Get-ChildItem -LiteralPath $Root -Force -Directory -Filter $pattern -ErrorAction SilentlyContinue |
    Select-Object FullName, LastWriteTime
}

$searchRoots = @(
  (Join-Path $Root "backend"),
  (Join-Path $Root "apps"),
  (Join-Path $Root "mobile_app"),
  (Join-Path $Root "scripts"),
  (Join-Path $Root "tools")
) | Where-Object { Test-Path -LiteralPath $_ }

foreach ($searchRoot in $searchRoots) {
  Get-ChildItem -LiteralPath $searchRoot -Force -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -in @("__pycache__", ".expo-export-check") -and
      $_.FullName -notlike "*\node_modules\*"
    } |
    Select-Object FullName, LastWriteTime
}
