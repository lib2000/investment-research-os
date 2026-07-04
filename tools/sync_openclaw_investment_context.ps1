param(
  [string]$OpenClawWorkspace = "$env:USERPROFILE\.openclaw\workspace",
  [double]$MaxAgeHours = 24,
  [switch]$SkipCopy,
  [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$exportScript = Join-Path $projectRoot "tools\export_openclaw_investment_context.py"
$checkScript = Join-Path $projectRoot "tools\check_openclaw_investment_context.py"
$sourceDir = Join-Path $projectRoot "research_vault\_system\openclaw_integration"
$targetDir = Join-Path $OpenClawWorkspace "data\investment_research"

if (-not (Test-Path -LiteralPath $exportScript)) {
  throw "OpenClaw export script not found: $exportScript"
}
if (-not (Test-Path -LiteralPath $checkScript)) {
  throw "OpenClaw check script not found: $checkScript"
}

python $exportScript --print-summary | Out-Host

$jsonPath = Join-Path $sourceDir "investment_research_context.json"
$markdownPath = Join-Path $sourceDir "investment_research_context.md"
$manifestPath = Join-Path $sourceDir "openclaw_bridge_manifest.json"
if (-not (Test-Path -LiteralPath $jsonPath)) {
  throw "Generated JSON context not found: $jsonPath"
}
if (-not (Test-Path -LiteralPath $markdownPath)) {
  throw "Generated Markdown context not found: $markdownPath"
}
if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "Generated bridge manifest not found: $manifestPath"
}

if ($SkipCopy) {
  if (-not $SkipValidation.IsPresent) {
    python $checkScript --source-dir $sourceDir --skip-openclaw --max-age-hours $MaxAgeHours
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw source context validation failed: $LASTEXITCODE"
    }
  }
  Write-Host "OpenClaw copy skipped. Generated context remains in $sourceDir"
  exit 0
}

if (-not (Test-Path -LiteralPath $OpenClawWorkspace)) {
  throw "OpenClaw workspace not found: $OpenClawWorkspace"
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -Force -LiteralPath $jsonPath -Destination (Join-Path $targetDir "investment_research_context.json")
Copy-Item -Force -LiteralPath $markdownPath -Destination (Join-Path $targetDir "investment_research_context.md")
Copy-Item -Force -LiteralPath $manifestPath -Destination (Join-Path $targetDir "openclaw_bridge_manifest.json")

$context = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$gitCommit = $null
$gitBranch = $null
$gitDirty = $null
try {
  $gitCommit = (git -C $projectRoot rev-parse --short HEAD 2>$null)
  $gitBranch = (git -C $projectRoot rev-parse --abbrev-ref HEAD 2>$null)
  $gitDirty = -not [string]::IsNullOrWhiteSpace((git -C $projectRoot status --short 2>$null))
} catch {
  $gitCommit = $null
  $gitBranch = $null
  $gitDirty = $null
}
$statusPath = Join-Path $targetDir "bridge_status.json"
$status = [ordered]@{
  status = "ok"
  copied_at = (Get-Date).ToString("o")
  source_project = $projectRoot
  source_git_commit = $gitCommit
  source_git_branch = $gitBranch
  source_git_dirty = $gitDirty
  source_context_json = $jsonPath
  source_context_markdown = $markdownPath
  source_bridge_manifest = $manifestPath
  openclaw_workspace = $OpenClawWorkspace
  target_dir = $targetDir
  context_generated_at = $context.generated_at
  latest_recommendation_date = $context.current_state.daily_recommendations.latest_recommendation_date
  latest_market_counts = $context.current_state.daily_recommendations.latest_market_counts
  telegram_saved_count = $context.current_state.news_and_telegram.telegram_favorite_posts.saved_count
  secrets_excluded = $true
}
$status | ConvertTo-Json -Depth 6 | Set-Content -Path $statusPath -Encoding UTF8

$readmePath = Join-Path $targetDir "README.md"
$readme = @(
  "# Investment Research OS Bridge",
  "",
  "- ``investment_research_context.md``: human-readable sanitized summary",
  "- ``investment_research_context.json``: machine-readable sanitized summary",
  "- ``openclaw_bridge_manifest.json``: machine-readable file map and refresh/check commands",
  "- source generator: ``$exportScript``",
  "- ``bridge_status.json``: last copy status and source/target paths",
  "- secrets, broker tokens, raw DB files, and account-auth material are excluded.",
  ""
)
Set-Content -Path $readmePath -Value $readme -Encoding UTF8

Get-ChildItem -LiteralPath $targetDir |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize

if (-not $SkipValidation.IsPresent) {
  python $checkScript --source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours
  if ($LASTEXITCODE -ne 0) {
    throw "OpenClaw context validation failed: $LASTEXITCODE"
  }
}
