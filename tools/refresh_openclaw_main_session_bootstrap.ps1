param(
  [string]$SessionsPath = "$env:USERPROFILE\.openclaw\agents\main\sessions\sessions.json",
  [string]$SessionKey = "agent:main:main"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

if (-not (Test-Path -LiteralPath $SessionsPath)) {
  throw "OpenClaw sessions file not found: $SessionsPath"
}

$raw = Get-Content -LiteralPath $SessionsPath -Raw -Encoding UTF8
$sessions = $raw | ConvertFrom-Json
$entryProperty = $sessions.PSObject.Properties[$SessionKey]
if ($null -eq $entryProperty) {
  $known = ($sessions.PSObject.Properties.Name -join ", ")
  throw "OpenClaw session key not found: $SessionKey. Known keys: $known"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = "$SessionsPath.bak.$timestamp"
Copy-Item -LiteralPath $SessionsPath -Destination $backupPath -Force

$entry = $entryProperty.Value
$entry.systemSent = $false
$entry.PSObject.Properties.Remove("systemPromptReport")
$entry.PSObject.Properties.Remove("workspaceBootstrapReport")
$entry.PSObject.Properties.Remove("bootstrapReport")
if ($entry.PSObject.Properties["updatedAt"]) {
  $entry.updatedAt = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
}

$sessions | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $SessionsPath -Encoding UTF8

$updated = (Get-Content -LiteralPath $SessionsPath -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties[$SessionKey].Value
$result = [ordered]@{
  status = "ok"
  sessions_path = $SessionsPath
  backup_path = $backupPath
  session_key = $SessionKey
  session_id = $updated.sessionId
  system_sent = $updated.systemSent
  has_system_prompt_report = ($null -ne $updated.PSObject.Properties["systemPromptReport"])
  has_workspace_bootstrap_report = ($null -ne $updated.PSObject.Properties["workspaceBootstrapReport"])
}
$result | ConvertTo-Json -Depth 4
