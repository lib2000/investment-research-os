param(
  [string]$OpenClawWorkspace = "$env:USERPROFILE\.openclaw\workspace",
  [switch]$SkipCopy
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$exportScript = Join-Path $projectRoot "tools\export_openclaw_investment_context.py"
$sourceDir = Join-Path $projectRoot "research_vault\_system\openclaw_integration"
$targetDir = Join-Path $OpenClawWorkspace "data\investment_research"

if (-not (Test-Path -LiteralPath $exportScript)) {
  throw "OpenClaw export script not found: $exportScript"
}

python $exportScript --print-summary | Out-Host

$jsonPath = Join-Path $sourceDir "investment_research_context.json"
$markdownPath = Join-Path $sourceDir "investment_research_context.md"
if (-not (Test-Path -LiteralPath $jsonPath)) {
  throw "Generated JSON context not found: $jsonPath"
}
if (-not (Test-Path -LiteralPath $markdownPath)) {
  throw "Generated Markdown context not found: $markdownPath"
}

if ($SkipCopy) {
  Write-Host "OpenClaw copy skipped. Generated context remains in $sourceDir"
  exit 0
}

if (-not (Test-Path -LiteralPath $OpenClawWorkspace)) {
  throw "OpenClaw workspace not found: $OpenClawWorkspace"
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -Force -LiteralPath $jsonPath -Destination (Join-Path $targetDir "investment_research_context.json")
Copy-Item -Force -LiteralPath $markdownPath -Destination (Join-Path $targetDir "investment_research_context.md")

$context = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$statusPath = Join-Path $targetDir "bridge_status.json"
$status = [ordered]@{
  status = "ok"
  copied_at = (Get-Date).ToString("o")
  source_project = $projectRoot
  source_context_json = $jsonPath
  source_context_markdown = $markdownPath
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
  "- source generator: ``$exportScript``",
  "- ``bridge_status.json``: last copy status and source/target paths",
  "- secrets, broker tokens, raw DB files, and account-auth material are excluded.",
  ""
)
Set-Content -Path $readmePath -Value $readme -Encoding UTF8

Get-ChildItem -LiteralPath $targetDir |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize
