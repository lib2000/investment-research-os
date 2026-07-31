param(
  [string]$ProjectRoot = "",
  [int]$TempRetentionDays = 14,
  [int]$LogRetentionDays = 30,
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$now = Get-Date
$tempCutoff = $now.AddDays(-[Math]::Max($TempRetentionDays, 1))
$logCutoff = $now.AddDays(-[Math]::Max($LogRetentionDays, 1))
$statePath = Join-Path $ProjectRootPath "tmp\local_cleanup_state.json"

function Get-SafeChildren {
  param([string]$Path, [datetime]$OlderThan)
  if (-not (Test-Path -LiteralPath $Path)) { return @() }
  @(Get-ChildItem -LiteralPath $Path -Force -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.LastWriteTime -lt $OlderThan -and
      $_.Name -notlike "*.env" -and
      $_.Name -notlike "*.key" -and
      $_.Name -notlike "*.pem" -and
      $_.Name -notlike "*.pfx" -and
      $_.Name -notlike "*.p12"
    })
}

$cacheNames = @("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache")
$cacheSearchRoots = @(
  (Join-Path $ProjectRootPath "backend"),
  (Join-Path $ProjectRootPath "tools"),
  (Join-Path $ProjectRootPath "scripts"),
  (Join-Path $ProjectRootPath "tests")
) | Where-Object { Test-Path -LiteralPath $_ }
$cacheDirectories = @(
  foreach ($searchRoot in $cacheSearchRoots) {
    Get-ChildItem -LiteralPath $searchRoot -Force -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -in $cacheNames -and
      $_.FullName -notlike "*\research_vault\*"
    }
  }
)
$agedTempFiles = @(
  Get-SafeChildren -Path (Join-Path $ProjectRootPath "tmp") -OlderThan $tempCutoff
  Get-SafeChildren -Path (Join-Path $ProjectRootPath ".test-tmp") -OlderThan $tempCutoff
)
$agedLogs = @(
  @((Join-Path $ProjectRootPath "logs"), (Join-Path $ProjectRootPath "tmp")) |
    Where-Object { Test-Path -LiteralPath $_ } |
    ForEach-Object { Get-ChildItem -LiteralPath $_ -Force -Recurse -File -ErrorAction SilentlyContinue } |
    Where-Object {
      $_.LastWriteTime -lt $logCutoff -and
      ($_.Name -like "*.log" -or $_.Name -like "*.out.log" -or $_.Name -like "*.err.log") -and
      $_.FullName -notlike "*\backups\*"
    }
)
$agedMigrationDirs = @(
  Get-ChildItem -LiteralPath $ProjectRootPath -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object {
      ($_.Name -like ".codex_migration_backup_*" -or $_.Name -like "research_vault_*_tmp") -and
      $_.LastWriteTime -lt $logCutoff
    }
)

$targets = @(
  foreach ($directory in $cacheDirectories) { [pscustomobject]@{ kind="cache_directory"; path=$directory.FullName; bytes=0 } }
  foreach ($file in $agedTempFiles) { [pscustomobject]@{ kind="aged_temp_file"; path=$file.FullName; bytes=$file.Length } }
  foreach ($file in $agedLogs) { [pscustomobject]@{ kind="aged_log_file"; path=$file.FullName; bytes=$file.Length } }
  foreach ($directory in $agedMigrationDirs) { [pscustomobject]@{ kind="aged_migration_directory"; path=$directory.FullName; bytes=0 } }
) | Group-Object path | ForEach-Object { $_.Group | Select-Object -First 1 }

$deleted = @()
$failures = @()
if ($Apply) {
  foreach ($target in $targets) {
    if ($target.path -notlike "$ProjectRootPath\*") { throw "Unsafe cleanup target: $($target.path)" }
    try {
      Remove-Item -LiteralPath $target.path -Recurse -Force -ErrorAction Stop
      $deleted += $target
    } catch {
      $failures += [pscustomobject]@{ kind=$target.kind; path=$target.path; error=$_.Exception.Message }
    }
  }
}

$result = [ordered]@{
  status = if ($failures.Count -eq 0) { "success" } else { "partial_success" }
  applied = [bool]$Apply
  generated_at = $now.ToString("o")
  retention_days = @{ temp=$TempRetentionDays; logs=$LogRetentionDays }
  candidate_count = $targets.Count
  deleted_count = $deleted.Count
  failed_count = $failures.Count
  candidate_bytes = [long](($targets | Measure-Object -Property bytes -Sum).Sum)
  targets = if ($Apply) { @() } else { $targets }
  failures = $failures
  protected_paths = @("research_vault", "backups", "*.sqlite*", ".env*", "credentials", "secrets")
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $statePath) | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8
$result | ConvertTo-Json -Depth 6
