param(
  [string]$OpenClawWorkspace = "$env:USERPROFILE\.openclaw\workspace",
  [double]$MaxAgeHours = 24,
  [switch]$SkipCopy,
  [switch]$SkipValidation,
  [switch]$RequireCompletionAudit
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$exportScript = Join-Path $projectRoot "tools\export_openclaw_investment_context.py"
$checkScript = Join-Path $projectRoot "tools\check_openclaw_investment_context.py"
$completionScript = Join-Path $projectRoot "tools\check_openclaw_bridge_completion.py"
$statusSummaryScript = Join-Path $projectRoot "tools\show_openclaw_bridge_status.py"
$sourceDir = Join-Path $projectRoot "research_vault\_system\openclaw_integration"
$targetDir = Join-Path $OpenClawWorkspace "data\investment_research"

function Set-OpenClawBridgeNoteSection {
  param(
    [string]$Path,
    [string[]]$Lines
  )
  $startMarker = "<!-- investment-research-os-bridge:start -->"
  $endMarker = "<!-- investment-research-os-bridge:end -->"
  $section = @($startMarker) + $Lines + @($endMarker)
  $sectionText = ($section -join [Environment]::NewLine)
  $content = ""
  if (Test-Path -LiteralPath $Path) {
    $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  }
  $pattern = "(?s)" + [regex]::Escape($startMarker) + ".*?" + [regex]::Escape($endMarker)
  if ($content -match $pattern) {
    $content = [regex]::Replace($content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $sectionText })
  } elseif ([string]::IsNullOrWhiteSpace($content)) {
    $content = $sectionText + [Environment]::NewLine
  } else {
    $content = $content.TrimEnd() + ([Environment]::NewLine * 2) + $sectionText + [Environment]::NewLine
  }
  Set-Content -Path $Path -Value $content -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $exportScript)) {
  throw "OpenClaw export script not found: $exportScript"
}
if (-not (Test-Path -LiteralPath $checkScript)) {
  throw "OpenClaw check script not found: $checkScript"
}
if (-not (Test-Path -LiteralPath $completionScript)) {
  throw "OpenClaw completion check script not found: $completionScript"
}
if (-not (Test-Path -LiteralPath $statusSummaryScript)) {
  throw "OpenClaw status summary script not found: $statusSummaryScript"
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
$operationalCommands = [ordered]@{
  safe_refresh = "powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1"
  strict_refresh = "powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit"
  validation = "python tools\check_openclaw_investment_context.py --max-age-hours 24"
  completion_audit = "python tools\check_openclaw_bridge_completion.py --max-age-hours 24"
  final_completion_audit = "python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes"
  status_summary = "python tools\show_openclaw_bridge_status.py --json"
  offline_readiness = "python tools\check_offline_readiness.py --json"
}
$fileSha256 = [ordered]@{
  context_json = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "investment_research_context.json")).Hash.ToLowerInvariant()
  context_markdown = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "investment_research_context.md")).Hash.ToLowerInvariant()
  bridge_manifest = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_bridge_manifest.json")).Hash.ToLowerInvariant()
}
$status = [ordered]@{
  status = "ok"
  copied_at = (Get-Date).ToString("o")
  read_order = @(
    "bridge_status.json",
    "openclaw_bridge_manifest.json",
    "investment_research_context.md",
    "investment_research_context.json",
    "openclaw_bridge_completion_report.md",
    "openclaw_bridge_completion_report.json"
  )
  source_project = $projectRoot
  source_git_commit = $gitCommit
  source_git_branch = $gitBranch
  source_git_dirty = $gitDirty
  source_context_json = $jsonPath
  source_context_markdown = $markdownPath
  source_bridge_manifest = $manifestPath
  openclaw_workspace = $OpenClawWorkspace
  target_dir = $targetDir
  max_age_hours = $MaxAgeHours
  completion_report_json = (Join-Path $targetDir "openclaw_bridge_completion_report.json")
  completion_report_markdown = (Join-Path $targetDir "openclaw_bridge_completion_report.md")
  startup_notes_updated = $true
  operational_commands = $operationalCommands
  file_sha256 = $fileSha256
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
  "- ``openclaw_bridge_completion_report.json``: machine-readable completion audit report",
  "- ``openclaw_bridge_completion_report.md``: latest completion audit report",
  "- source generator: ``$exportScript``",
  "- ``bridge_status.json``: first-read runtime status, read_order, source git state, completion report paths, operational commands, core file SHA256 hashes, and ``completion_report_sha256``",
  "- source git: ``$gitBranch $gitCommit``",
  "- context generated at: ``$($context.generated_at)``",
  "- latest recommendation date: ``$($context.current_state.daily_recommendations.latest_recommendation_date)``",
  "- latest market counts: ``$($context.current_state.daily_recommendations.latest_market_counts | ConvertTo-Json -Compress)``",
  "- telegram favorite saved: ``$($context.current_state.news_and_telegram.telegram_favorite_posts.saved_count)``",
  "- safe refresh: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1``",
  "- final strict refresh: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit``",
  "- validation: ``python tools\check_openclaw_investment_context.py --max-age-hours 24``",
  "- completion audit: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24``",
  "- final completion audit: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes``",
  "- status summary: ``python tools\show_openclaw_bridge_status.py --json``",
  "- offline readiness: ``python tools\check_offline_readiness.py --json``",
  "- secrets, broker tokens, raw DB files, and account-auth material are excluded.",
  ""
)
Set-Content -Path $readmePath -Value $readme -Encoding UTF8

$startupLines = @(
  "## Investment Research OS Bridge",
  "",
  "- Read ``data/investment_research/bridge_status.json`` first.",
  "- Read order: ``bridge_status.json`` -> ``openclaw_bridge_manifest.json`` -> ``investment_research_context.md`` -> ``investment_research_context.json`` -> ``openclaw_bridge_completion_report.md`` -> ``openclaw_bridge_completion_report.json``.",
  "- Human summary: ``data/investment_research/investment_research_context.md``.",
  "- Machine state: ``data/investment_research/investment_research_context.json``.",
  "- Manifest and commands: ``data/investment_research/openclaw_bridge_manifest.json``.",
  "- Machine completion report: ``data/investment_research/openclaw_bridge_completion_report.json``.",
  "- Human completion report: ``data/investment_research/openclaw_bridge_completion_report.md``.",
  "- Completion report hashes: ``data/investment_research/bridge_status.json`` key ``completion_report_sha256``.",
  "- Source git: ``$gitBranch $gitCommit``.",
  "- Safe refresh from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1``.",
  "- Final strict refresh from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit``.",
  "- Completion audit from ``$projectRoot``: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24``.",
  "- Final completion audit from ``$projectRoot``: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes``.",
  "- Status summary from ``$projectRoot``: ``python tools\show_openclaw_bridge_status.py --json``.",
  "- Offline readiness from ``$projectRoot``: ``python tools\check_offline_readiness.py --json``.",
  "- Never request, expose, or transmit broker tokens, API keys, raw DB files, or account-auth material.",
  "- Treat the bridge as decision-support context only; do not place trades from it."
)
Set-OpenClawBridgeNoteSection -Path (Join-Path $OpenClawWorkspace "MEMORY.md") -Lines $startupLines
Set-OpenClawBridgeNoteSection -Path (Join-Path $OpenClawWorkspace "HEARTBEAT.md") -Lines $startupLines

if (-not $SkipValidation.IsPresent) {
  python $checkScript --source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours
  if ($LASTEXITCODE -ne 0) {
    throw "OpenClaw context validation failed: $LASTEXITCODE"
  }
  if ($gitDirty -eq $true) {
    $message = "OpenClaw completion audit skipped because source git worktree is dirty."
    if ($RequireCompletionAudit.IsPresent) {
      throw $message
    }
    Write-Warning $message
  } else {
    python $completionScript --source-dir $sourceDir --openclaw-dir $targetDir --openclaw-workspace $OpenClawWorkspace --max-age-hours $MaxAgeHours --write-report
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw completion audit failed: $LASTEXITCODE"
    }
    python $checkScript --source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw final context validation failed: $LASTEXITCODE"
    }
    python $completionScript --source-dir $sourceDir --openclaw-dir $targetDir --openclaw-workspace $OpenClawWorkspace --max-age-hours $MaxAgeHours --require-report-hashes
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw final completion audit failed: $LASTEXITCODE"
    }
    python $statusSummaryScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw status summary failed: $LASTEXITCODE"
    }
  }
}

Get-ChildItem -LiteralPath $targetDir |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize
