param(
  [string]$OpenClawWorkspace = "$env:USERPROFILE\.openclaw\workspace",
  [double]$MaxAgeHours = 24,
  [switch]$SkipCopy,
  [switch]$SkipValidation,
  [switch]$SkipWslSync,
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
$knowledgeGraphCheckScript = Join-Path $projectRoot "tools\check_openclaw_knowledge_graph.py"
$completionScript = Join-Path $projectRoot "tools\check_openclaw_bridge_completion.py"
$statusSummaryScript = Join-Path $projectRoot "tools\show_openclaw_bridge_status.py"
$quickHealthScript = Join-Path $projectRoot "tools\check_openclaw_quick_health.py"
$todayAnswerQualityScript = Join-Path $projectRoot "tools\check_openclaw_today_answer_quality.py"
$priorityAnswerQualityScript = Join-Path $projectRoot "tools\check_openclaw_priority_answer_quality.py"
$questionReadOrderScript = Join-Path $projectRoot "tools\check_openclaw_question_read_order.py"
$answerSamplesScript = Join-Path $projectRoot "tools\check_openclaw_answer_samples.py"
$actualAnswerAuditScript = Join-Path $projectRoot "tools\check_openclaw_actual_answer_audit.py"
$answerCaptureCycleScript = Join-Path $projectRoot "tools\check_openclaw_answer_capture_cycle.py"
$answerCaptureCycleRunner = Join-Path $projectRoot "tools\run_openclaw_answer_capture_cycle.ps1"
$answerCaptureCycleRegisterScript = Join-Path $projectRoot "tools\register_openclaw_answer_capture_cycle_task.ps1"
$answerCaptureTaskStatusScript = Join-Path $projectRoot "tools\check_openclaw_answer_capture_task_status.py"
$actualAnswerCaptureScript = Join-Path $projectRoot "tools\capture_openclaw_actual_answer.py"
$pendingAnswerCollectScript = Join-Path $projectRoot "tools\collect_openclaw_pending_answers.py"
$wslSyncScript = Join-Path $projectRoot "tools\sync_openclaw_wsl_investment_context.ps1"
$wslAnswerContextScript = Join-Path $projectRoot "tools\check_openclaw_wsl_answer_context.py"
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
    $content = [regex]::Replace($content, $pattern, "")
  }
  if ([string]::IsNullOrWhiteSpace($content)) {
    $content = $sectionText + [Environment]::NewLine
  } else {
    $content = $sectionText + ([Environment]::NewLine * 2) + $content.Trim()
  }
  Set-Content -Path $Path -Value ($content.TrimEnd() + [Environment]::NewLine) -Encoding UTF8
}

function Set-OpenClawDailyInvestmentMemory {
  param(
    [string]$Workspace,
    [string]$DateText,
    [string]$GitBranch,
    [string]$GitCommit
  )
  $memoryDir = Join-Path $Workspace "memory"
  New-Item -ItemType Directory -Force -Path $memoryDir | Out-Null
  $path = Join-Path $memoryDir "$DateText.md"
  $lines = @(
    "# $DateText Investment Research OS Daily Context",
    "",
    "## Critical Answer Rule",
    "- 사용자가 '오늘 시스템에서 구현한 작업 보고하고 다음 스케줄을 말해줘'라고 물으면 MEMORY.md만 보고 답하지 않는다.",
    "- 반드시 먼저 data/investment_research/bridge_status.json을 확인하고, data/investment_research/openclaw_first_read.json의 today_work_report, answer_correction, next_schedule을 기준으로 답한다.",
    "- openclaw_first_read.json today_work_report.has_implementation_today=true이면 '오늘 구현 작업 없음' 또는 '특별히 새로 구현된 작업 기록 없음'이라고 답하면 안 된다.",
    "- 현재 source git: $GitBranch $GitCommit.",
    "- 검증 명령: python tools\check_openclaw_today_answer_readiness.py --json",
    "- 질문별 read-order 검증: python tools\check_openclaw_question_read_order.py --json",
    "- 질문별 답변 샘플 검증: python tools\check_openclaw_answer_samples.py --json",
    "- 답변 캡처 cycle: python tools\check_openclaw_answer_capture_cycle.py --json",
    "- 답변 캡처 cycle 실행: powershell.exe -ExecutionPolicy Bypass -File .\tools\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState",
    "- 답변 캡처 작업 상태: python tools\check_openclaw_answer_capture_task_status.py --json",
    "- 실제 답변 캡처: python tools\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json",
    "- pending 답변 수집: python tools\collect_openclaw_pending_answers.py --json",
    "- 실제 답변 캡처 상태: python tools\check_openclaw_actual_answer_capture_status.py --json",
    "- 실제 답변 사후감사: python tools\check_openclaw_actual_answer_audit.py --json",
    "- 답변 직전 fresh bootstrap 검증: python tools\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json",
    "",
    "## Required Read Order",
    "1. data/investment_research/bridge_status.json",
    "2. data/investment_research/openclaw_first_read.json",
    "3. data/investment_research/openclaw_first_read.md",
    "4. data/investment_research/openclaw_bridge_manifest.json"
  )
  Set-Content -Path $path -Value (($lines -join [Environment]::NewLine) + [Environment]::NewLine) -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $exportScript)) {
  throw "OpenClaw export script not found: $exportScript"
}
if (-not (Test-Path -LiteralPath $checkScript)) {
  throw "OpenClaw check script not found: $checkScript"
}
if (-not (Test-Path -LiteralPath $knowledgeGraphCheckScript)) {
  throw "OpenClaw knowledge graph check script not found: $knowledgeGraphCheckScript"
}
if (-not (Test-Path -LiteralPath $completionScript)) {
  throw "OpenClaw completion check script not found: $completionScript"
}
if (-not (Test-Path -LiteralPath $statusSummaryScript)) {
  throw "OpenClaw status summary script not found: $statusSummaryScript"
}
if (-not (Test-Path -LiteralPath $quickHealthScript)) {
  throw "OpenClaw quick health script not found: $quickHealthScript"
}
if (-not (Test-Path -LiteralPath $todayAnswerQualityScript)) {
  throw "OpenClaw today answer quality script not found: $todayAnswerQualityScript"
}
if (-not (Test-Path -LiteralPath $priorityAnswerQualityScript)) {
  throw "OpenClaw priority answer quality script not found: $priorityAnswerQualityScript"
}
if (-not (Test-Path -LiteralPath $questionReadOrderScript)) {
  throw "OpenClaw question read-order script not found: $questionReadOrderScript"
}
if (-not (Test-Path -LiteralPath $answerSamplesScript)) {
  throw "OpenClaw answer samples script not found: $answerSamplesScript"
}
if (-not (Test-Path -LiteralPath $answerCaptureCycleScript)) {
  throw "OpenClaw answer capture cycle script not found: $answerCaptureCycleScript"
}
if (-not (Test-Path -LiteralPath $answerCaptureCycleRunner)) {
  throw "OpenClaw answer capture cycle runner not found: $answerCaptureCycleRunner"
}
if (-not (Test-Path -LiteralPath $answerCaptureCycleRegisterScript)) {
  throw "OpenClaw answer capture cycle task register script not found: $answerCaptureCycleRegisterScript"
}
if (-not (Test-Path -LiteralPath $answerCaptureTaskStatusScript)) {
  throw "OpenClaw answer capture task status script not found: $answerCaptureTaskStatusScript"
}
if (-not (Test-Path -LiteralPath $pendingAnswerCollectScript)) {
  throw "OpenClaw pending answer collector script not found: $pendingAnswerCollectScript"
}
if (-not (Test-Path -LiteralPath $wslSyncScript)) {
  throw "OpenClaw WSL sync script not found: $wslSyncScript"
}
if (-not (Test-Path -LiteralPath $wslAnswerContextScript)) {
  throw "OpenClaw WSL answer context check script not found: $wslAnswerContextScript"
}

python $exportScript --print-summary | Out-Host

$jsonPath = Join-Path $sourceDir "investment_research_context.json"
$markdownPath = Join-Path $sourceDir "investment_research_context.md"
$knowledgeGraphJsonPath = Join-Path $sourceDir "openclaw_knowledge_graph_blueprint.json"
$knowledgeGraphMarkdownPath = Join-Path $sourceDir "openclaw_knowledge_graph_blueprint.md"
$knowledgeGraphNodesPath = Join-Path $sourceDir "openclaw_knowledge_graph_nodes.json"
$knowledgeGraphEdgesPath = Join-Path $sourceDir "openclaw_knowledge_graph_edges.json"
$knowledgeGraphMasterIndexPath = Join-Path $sourceDir "openclaw_knowledge_graph_master_index.md"
$knowledgeGraphGlossaryPath = Join-Path $sourceDir "openclaw_knowledge_graph_glossary.md"
$knowledgeGraphMarginaliaPath = Join-Path $sourceDir "openclaw_knowledge_graph_marginalia_queue.md"
$firstReadJsonPath = Join-Path $sourceDir "openclaw_first_read.json"
$firstReadMarkdownPath = Join-Path $sourceDir "openclaw_first_read.md"
$manifestPath = Join-Path $sourceDir "openclaw_bridge_manifest.json"
if (-not (Test-Path -LiteralPath $jsonPath)) {
  throw "Generated JSON context not found: $jsonPath"
}
if (-not (Test-Path -LiteralPath $markdownPath)) {
  throw "Generated Markdown context not found: $markdownPath"
}
if (-not (Test-Path -LiteralPath $knowledgeGraphJsonPath)) {
  throw "Generated OpenClaw knowledge graph blueprint JSON not found: $knowledgeGraphJsonPath"
}
if (-not (Test-Path -LiteralPath $knowledgeGraphMarkdownPath)) {
  throw "Generated OpenClaw knowledge graph blueprint Markdown not found: $knowledgeGraphMarkdownPath"
}
foreach ($graphPath in @($knowledgeGraphNodesPath, $knowledgeGraphEdgesPath, $knowledgeGraphMasterIndexPath, $knowledgeGraphGlossaryPath, $knowledgeGraphMarginaliaPath)) {
  if (-not (Test-Path -LiteralPath $graphPath)) {
    throw "Generated OpenClaw knowledge graph artifact not found: $graphPath"
  }
}
if (-not (Test-Path -LiteralPath $firstReadJsonPath)) {
  throw "Generated OpenClaw first-read JSON not found: $firstReadJsonPath"
}
if (-not (Test-Path -LiteralPath $firstReadMarkdownPath)) {
  throw "Generated OpenClaw first-read Markdown not found: $firstReadMarkdownPath"
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
    python $knowledgeGraphCheckScript --source-dir $sourceDir --skip-openclaw --max-age-hours $MaxAgeHours
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw source knowledge graph validation failed: $LASTEXITCODE"
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
Copy-Item -Force -LiteralPath $knowledgeGraphJsonPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_blueprint.json")
Copy-Item -Force -LiteralPath $knowledgeGraphMarkdownPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_blueprint.md")
Copy-Item -Force -LiteralPath $knowledgeGraphNodesPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_nodes.json")
Copy-Item -Force -LiteralPath $knowledgeGraphEdgesPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_edges.json")
Copy-Item -Force -LiteralPath $knowledgeGraphMasterIndexPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_master_index.md")
Copy-Item -Force -LiteralPath $knowledgeGraphGlossaryPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_glossary.md")
Copy-Item -Force -LiteralPath $knowledgeGraphMarginaliaPath -Destination (Join-Path $targetDir "openclaw_knowledge_graph_marginalia_queue.md")
Copy-Item -Force -LiteralPath $firstReadJsonPath -Destination (Join-Path $targetDir "openclaw_first_read.json")
Copy-Item -Force -LiteralPath $firstReadMarkdownPath -Destination (Join-Path $targetDir "openclaw_first_read.md")
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
  knowledge_graph_validation = "python tools\check_openclaw_knowledge_graph.py --max-age-hours 24"
  final_completion_audit = "python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes"
  status_summary = "python tools\show_openclaw_bridge_status.py --json"
  quick_health = "python tools\check_openclaw_quick_health.py --json"
  today_answer_readiness = "python tools\check_openclaw_today_answer_readiness.py --json"
  today_answer_quality = "python tools\check_openclaw_today_answer_quality.py --json"
  priority_answer_quality = "python tools\check_openclaw_priority_answer_quality.py --json"
  question_read_order = "python tools\check_openclaw_question_read_order.py --json"
  answer_samples = "python tools\check_openclaw_answer_samples.py --json"
  actual_answer_audit = "python tools\check_openclaw_actual_answer_audit.py --json"
  answer_capture_cycle = "python tools\check_openclaw_answer_capture_cycle.py --json"
  answer_capture_cycle_run = "powershell.exe -ExecutionPolicy Bypass -File .\tools\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState"
  answer_capture_cycle_register = "powershell.exe -ExecutionPolicy Bypass -File .\tools\register_openclaw_answer_capture_cycle_task.ps1 -Collect"
  answer_capture_task_status = "python tools\check_openclaw_answer_capture_task_status.py --json"
  actual_answer_capture = "python tools\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json"
  pending_answer_collect = "python tools\collect_openclaw_pending_answers.py --json"
  actual_answer_capture_status = "python tools\check_openclaw_actual_answer_capture_status.py --json"
  wsl_refresh = "powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_wsl_investment_context.ps1"
  wsl_answer_context = "python tools\check_openclaw_wsl_answer_context.py --json"
  wsl_fresh_bootstrap = "python tools\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json"
  offline_readiness = "python tools\check_offline_readiness.py --json"
}
$fileSha256 = [ordered]@{
  first_read_json = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_first_read.json")).Hash.ToLowerInvariant()
  first_read_markdown = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_first_read.md")).Hash.ToLowerInvariant()
  context_json = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "investment_research_context.json")).Hash.ToLowerInvariant()
  context_markdown = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "investment_research_context.md")).Hash.ToLowerInvariant()
  knowledge_graph_blueprint_json = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_blueprint.json")).Hash.ToLowerInvariant()
  knowledge_graph_blueprint_markdown = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_blueprint.md")).Hash.ToLowerInvariant()
  knowledge_graph_nodes = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_nodes.json")).Hash.ToLowerInvariant()
  knowledge_graph_edges = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_edges.json")).Hash.ToLowerInvariant()
  knowledge_graph_master_index = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_master_index.md")).Hash.ToLowerInvariant()
  knowledge_graph_glossary = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_glossary.md")).Hash.ToLowerInvariant()
  knowledge_graph_marginalia = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_knowledge_graph_marginalia_queue.md")).Hash.ToLowerInvariant()
  bridge_manifest = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $targetDir "openclaw_bridge_manifest.json")).Hash.ToLowerInvariant()
}
$latestRecommendations = @()
foreach ($row in @($context.current_state.daily_recommendations.latest_rows)) {
  if ($null -eq $row) {
    continue
  }
  $latestRecommendations += [ordered]@{
    market = $row.market
    rank = $row.rank
    ticker = $row.ticker
    company_name = $row.company_name
    score = $row.score
    baseline_price = $row.baseline_price
    currency = $row.currency
  }
}
$latestRecommendationReadmeLines = @("- latest recommendations:")
foreach ($item in @($latestRecommendations)) {
  $latestRecommendationReadmeLines += "  - $($item.market)#$($item.rank) ``$($item.ticker)`` $($item.company_name) | score $($item.score) | baseline $($item.baseline_price) $($item.currency)"
}
$status = [ordered]@{
  status = "ok"
  copied_at = (Get-Date).ToString("o")
  read_order = @(
    "bridge_status.json",
    "openclaw_first_read.md",
    "openclaw_first_read.json",
    "openclaw_bridge_manifest.json",
    "investment_research_context.md",
    "investment_research_context.json",
    "openclaw_knowledge_graph_blueprint.md",
    "openclaw_knowledge_graph_blueprint.json",
    "openclaw_knowledge_graph_nodes.json",
    "openclaw_knowledge_graph_edges.json",
    "openclaw_knowledge_graph_master_index.md",
    "openclaw_knowledge_graph_glossary.md",
    "openclaw_knowledge_graph_marginalia_queue.md",
    "openclaw_bridge_completion_report.md",
    "openclaw_bridge_completion_report.json"
  )
  source_project = $projectRoot
  source_git_commit = $gitCommit
  source_git_branch = $gitBranch
  source_git_dirty = $gitDirty
  source_context_json = $jsonPath
  source_context_markdown = $markdownPath
  source_knowledge_graph_blueprint_json = $knowledgeGraphJsonPath
  source_knowledge_graph_blueprint_markdown = $knowledgeGraphMarkdownPath
  source_knowledge_graph_nodes = $knowledgeGraphNodesPath
  source_knowledge_graph_edges = $knowledgeGraphEdgesPath
  source_knowledge_graph_master_index = $knowledgeGraphMasterIndexPath
  source_knowledge_graph_glossary = $knowledgeGraphGlossaryPath
  source_knowledge_graph_marginalia = $knowledgeGraphMarginaliaPath
  source_first_read_json = $firstReadJsonPath
  source_first_read_markdown = $firstReadMarkdownPath
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
  latest_recommendations = $latestRecommendations
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
  "- ``openclaw_first_read.md``: compact first-read status, recommendations, safety, and command packet",
  "- ``openclaw_first_read.json``: machine-readable first-read packet",
  "- ``openclaw_knowledge_graph_blueprint.md``: human-readable personal knowledge graph blueprint from sanitized investment thesis notes",
  "- ``openclaw_knowledge_graph_blueprint.json``: machine-readable personal knowledge graph blueprint",
  "- ``openclaw_knowledge_graph_nodes.json`` and ``openclaw_knowledge_graph_edges.json``: consumable graph layer",
  "- ``openclaw_knowledge_graph_master_index.md`` / ``openclaw_knowledge_graph_glossary.md`` / ``openclaw_knowledge_graph_marginalia_queue.md``: human-readable graph views",
  "- ``openclaw_bridge_manifest.json``: machine-readable file map and refresh/check commands",
  "- ``openclaw_bridge_completion_report.json``: machine-readable completion audit report",
  "- ``openclaw_bridge_completion_report.md``: latest completion audit report",
  "- source generator: ``$exportScript``",
  "- ``bridge_status.json``: first-read runtime status, read_order, source git state, completion report paths, operational commands, core file SHA256 hashes, and ``completion_report_sha256``",
  "- source git: ``$gitBranch $gitCommit``",
  "- context generated at: ``$($context.generated_at)``",
  "- latest recommendation date: ``$($context.current_state.daily_recommendations.latest_recommendation_date)``",
  "- latest market counts: ``$($context.current_state.daily_recommendations.latest_market_counts | ConvertTo-Json -Compress)``",
  ""
) + $latestRecommendationReadmeLines + @(
  "",
  "- telegram favorite saved: ``$($context.current_state.news_and_telegram.telegram_favorite_posts.saved_count)``",
  "- safe refresh: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1``",
  "- final strict refresh: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit``",
  "- validation: ``python tools\check_openclaw_investment_context.py --max-age-hours 24``",
  "- completion audit: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24``",
  "- knowledge graph validation: ``python tools\check_openclaw_knowledge_graph.py --max-age-hours 24``",
  "- final completion audit: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes``",
  "- status summary: ``python tools\show_openclaw_bridge_status.py --json``",
  "- quick health: ``python tools\check_openclaw_quick_health.py --json``",
  "- today answer readiness: ``python tools\check_openclaw_today_answer_readiness.py --json``",
  "- today answer quality smoke: ``python tools\check_openclaw_today_answer_quality.py --json``",
  "- priority answer quality smoke: ``python tools\check_openclaw_priority_answer_quality.py --json``",
  "- question read-order smoke: ``python tools\check_openclaw_question_read_order.py --json``",
  "- answer samples smoke: ``python tools\check_openclaw_answer_samples.py --json``",
  "- answer capture cycle: ``python tools\check_openclaw_answer_capture_cycle.py --json``",
  "- answer capture cycle runner: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState``",
  "- answer capture cycle task register: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\register_openclaw_answer_capture_cycle_task.ps1 -Collect``",
  "- answer capture task status: ``python tools\check_openclaw_answer_capture_task_status.py --json``",
  "- actual answer capture: ``python tools\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json``",
  "- pending answer collect: ``python tools\collect_openclaw_pending_answers.py --json``",
  "- actual answer capture status: ``python tools\check_openclaw_actual_answer_capture_status.py --json``",
  "- actual answer audit: ``python tools\check_openclaw_actual_answer_audit.py --json``",
  "- WSL sync: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_wsl_investment_context.ps1``",
  "- WSL PA answer context: ``python tools\check_openclaw_wsl_answer_context.py --json``",
  "- WSL PA fresh bootstrap: ``python tools\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json``",
  "- expected status summary hashes: ``hash_status=ok``, ``hash_checked_count=14``, ``hash_mismatches=[]``",
  "- offline readiness: ``python tools\check_offline_readiness.py --json``",
  "- secrets, broker tokens, raw DB files, and account-auth material are excluded.",
  ""
)
Set-Content -Path $readmePath -Value $readme -Encoding UTF8

$todayText = (Get-Date).ToString("yyyy-MM-dd")
$startupLines = @(
  "## Investment Research OS Bridge - Critical Answer Override",
  "",
  "- 질문이 '오늘 시스템에서 구현한 작업 보고하고 다음 스케줄을 말해줘'이면 MEMORY.md만 보고 답하지 않는다.",
  "- 먼저 ``data/investment_research/bridge_status.json``을 확인하고 ``data/investment_research/openclaw_first_read.json``의 ``today_work_report``, ``answer_correction``, ``next_schedule``을 기준으로 답한다.",
  "- ``today_work_report.has_implementation_today=true``이면 '오늘 구현 작업 없음' 또는 '특별히 새로 구현된 작업 기록 없음'이라고 답하면 안 된다.",
  "- 이 규칙의 준비 상태는 ``python tools\check_openclaw_today_answer_readiness.py --json``으로 확인한다.",
  "- Read ``data/investment_research/bridge_status.json`` first.",
  "- Read order: ``bridge_status.json`` -> ``openclaw_first_read.md`` -> ``openclaw_first_read.json`` -> ``openclaw_bridge_manifest.json`` -> ``investment_research_context.md`` -> ``investment_research_context.json`` -> ``openclaw_knowledge_graph_blueprint.md`` -> ``openclaw_knowledge_graph_blueprint.json`` -> ``openclaw_knowledge_graph_nodes.json`` -> ``openclaw_knowledge_graph_edges.json`` -> ``openclaw_knowledge_graph_master_index.md`` -> ``openclaw_knowledge_graph_glossary.md`` -> ``openclaw_knowledge_graph_marginalia_queue.md`` -> ``openclaw_bridge_completion_report.md`` -> ``openclaw_bridge_completion_report.json``.",
  "- First-read packet: ``data/investment_research/openclaw_first_read.md`` and ``data/investment_research/openclaw_first_read.json``.",
  "- Human summary: ``data/investment_research/investment_research_context.md``.",
  "- Machine state: ``data/investment_research/investment_research_context.json``.",
  "- Knowledge graph blueprint: ``data/investment_research/openclaw_knowledge_graph_blueprint.md`` and ``data/investment_research/openclaw_knowledge_graph_blueprint.json``.",
  "- Knowledge graph layer: ``data/investment_research/openclaw_knowledge_graph_nodes.json``, ``openclaw_knowledge_graph_edges.json``, ``openclaw_knowledge_graph_master_index.md``, ``openclaw_knowledge_graph_glossary.md``, ``openclaw_knowledge_graph_marginalia_queue.md``.",
  "- Manifest and commands: ``data/investment_research/openclaw_bridge_manifest.json``.",
  "- Machine completion report: ``data/investment_research/openclaw_bridge_completion_report.json``.",
  "- Human completion report: ``data/investment_research/openclaw_bridge_completion_report.md``.",
  "- Completion report hashes: ``data/investment_research/bridge_status.json`` key ``completion_report_sha256``.",
  "- Source git: ``$gitBranch $gitCommit``.",
  "- Safe refresh from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1``.",
  "- Final strict refresh from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit``.",
  "- Completion audit from ``$projectRoot``: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24``.",
  "- Knowledge graph validation from ``$projectRoot``: ``python tools\check_openclaw_knowledge_graph.py --max-age-hours 24``.",
  "- Final completion audit from ``$projectRoot``: ``python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes``.",
  "- Status summary from ``$projectRoot``: ``python tools\show_openclaw_bridge_status.py --json``.",
  "- Quick health from ``$projectRoot``: ``python tools\check_openclaw_quick_health.py --json``.",
  "- Today answer readiness from ``$projectRoot``: ``python tools\check_openclaw_today_answer_readiness.py --json``.",
  "- Today answer quality smoke from ``$projectRoot``: ``python tools\check_openclaw_today_answer_quality.py --json``.",
  "- Priority answer quality smoke from ``$projectRoot``: ``python tools\check_openclaw_priority_answer_quality.py --json``.",
  "- Question read-order smoke from ``$projectRoot``: ``python tools\check_openclaw_question_read_order.py --json``.",
  "- Answer samples smoke from ``$projectRoot``: ``python tools\check_openclaw_answer_samples.py --json``.",
  "- Answer capture cycle from ``$projectRoot``: ``python tools\check_openclaw_answer_capture_cycle.py --json``.",
  "- Answer capture cycle runner from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState``.",
  "- Answer capture cycle task register from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\register_openclaw_answer_capture_cycle_task.ps1 -Collect``.",
  "- Answer capture task status from ``$projectRoot``: ``python tools\check_openclaw_answer_capture_task_status.py --json``.",
  "- Actual answer capture from ``$projectRoot``: ``python tools\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json``.",
  "- Pending answer collect from ``$projectRoot``: ``python tools\collect_openclaw_pending_answers.py --json``.",
  "- Actual answer capture status from ``$projectRoot``: ``python tools\check_openclaw_actual_answer_capture_status.py --json``.",
  "- Actual answer audit from ``$projectRoot``: ``python tools\check_openclaw_actual_answer_audit.py --json``.",
  "- WSL sync from ``$projectRoot``: ``powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_wsl_investment_context.ps1``.",
  "- WSL PA answer context from ``$projectRoot``: ``python tools\check_openclaw_wsl_answer_context.py --json``.",
  "- WSL PA fresh bootstrap from ``$projectRoot``: ``python tools\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json``.",
  "- Expected status summary hashes: ``hash_status=ok``, ``hash_checked_count=14``, ``hash_mismatches=[]``.",
  "- Offline readiness from ``$projectRoot``: ``python tools\check_offline_readiness.py --json``.",
  "- Never request, expose, or transmit broker tokens, API keys, raw DB files, or account-auth material.",
  "- Treat the bridge as decision-support context only; do not place trades from it."
)
Set-OpenClawDailyInvestmentMemory -Workspace $OpenClawWorkspace -DateText $todayText -GitBranch $gitBranch -GitCommit $gitCommit
Set-OpenClawBridgeNoteSection -Path (Join-Path $OpenClawWorkspace "AGENTS.md") -Lines $startupLines
Set-OpenClawBridgeNoteSection -Path (Join-Path $OpenClawWorkspace "MEMORY.md") -Lines $startupLines
Set-OpenClawBridgeNoteSection -Path (Join-Path $OpenClawWorkspace "HEARTBEAT.md") -Lines $startupLines

if (-not $SkipValidation.IsPresent) {
  python $checkScript --source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours
  if ($LASTEXITCODE -ne 0) {
    throw "OpenClaw context validation failed: $LASTEXITCODE"
  }
  python $knowledgeGraphCheckScript --source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours
  if ($LASTEXITCODE -ne 0) {
    throw "OpenClaw knowledge graph validation failed: $LASTEXITCODE"
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
    python $todayAnswerQualityScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw today answer quality smoke failed: $LASTEXITCODE"
    }
    python $priorityAnswerQualityScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw priority answer quality smoke failed: $LASTEXITCODE"
    }
    python $questionReadOrderScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw question read-order smoke failed: $LASTEXITCODE"
    }
    python $answerSamplesScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw answer samples smoke failed: $LASTEXITCODE"
    }
    python $actualAnswerAuditScript --openclaw-dir $targetDir --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw actual answer audit failed: $LASTEXITCODE"
    }
  }
}

if (-not $SkipWslSync.IsPresent) {
  $wslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
  if ($null -eq $wslCommand) {
    Write-Warning "OpenClaw WSL sync skipped because wsl.exe is not available."
  } else {
    & powershell.exe -ExecutionPolicy Bypass -File $wslSyncScript
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw WSL sync failed: $LASTEXITCODE"
    }
    python $wslAnswerContextScript --json
    if ($LASTEXITCODE -ne 0) {
      throw "OpenClaw WSL answer context check failed: $LASTEXITCODE"
    }
  }
}

Get-ChildItem -LiteralPath $targetDir |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize
