param(
  [string]$ProjectRoot = "",
  [string]$ChannelChatId = "",
  [ValidateSet("lib20", "my_claw")]
  [string]$Bot = "lib20"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$envPath = Join-Path $ProjectRootPath "backend\.env"
if (-not (Test-Path -LiteralPath $envPath)) { throw "env file not found: $envPath" }

function Read-PlainTextSecret {
  param([string]$Prompt)
  $secure = Read-Host -Prompt $Prompt -AsSecureString
  $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  }
}

function Set-EnvValue {
  param(
    [string]$Content,
    [string]$Name,
    [string]$Value
  )
  if ($Value -match "[\r\n]") { throw "$Name cannot contain a newline" }
  $line = "$Name=$Value"
  $pattern = "(?m)^" + [regex]::Escape($Name) + "=.*$"
  if ($Content -match $pattern) {
    return [regex]::Replace($Content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line })
  }
  return $Content.TrimEnd() + [Environment]::NewLine + $line + [Environment]::NewLine
}

if ([string]::IsNullOrWhiteSpace($ChannelChatId)) {
  $ChannelChatId = Read-Host "Target channel (@public_channel or -1001234567890)"
}
$ChannelChatId = $ChannelChatId.Trim()
if ($ChannelChatId -notmatch "^@[A-Za-z0-9_]{5,}$" -and $ChannelChatId -notmatch "^-100\d{6,}$") {
  throw "Enter a public channel username (@channel_name) or private numeric channel ID (-100...)."
}

$botLabel = if ($Bot -eq "lib20") { "@lib20_bot" } else { "@my_claw_lib2000_bot" }
$token = Read-PlainTextSecret "Paste the $botLabel token (input is hidden)"
if ($token -notmatch "^\d+:[A-Za-z0-9_-]{20,}$") {
  throw "The token format is invalid. Copy the full API token from BotFather and try again."
}

$content = [IO.File]::ReadAllText($envPath, [Text.UTF8Encoding]::new($false))
$content = Set-EnvValue $content "TELEGRAM_DEEP_ANALYSIS_ENABLED" "true"
$content = Set-EnvValue $content "TELEGRAM_DEEP_ANALYSIS_TIME" "07:00"
$content = Set-EnvValue $content "TELEGRAM_DEEP_ANALYSIS_CHAT_ID" $ChannelChatId
$content = Set-EnvValue $content "TELEGRAM_BRIEF_DELIVERY_ENABLED" "true"
$content = Set-EnvValue $content "TELEGRAM_BRIEF_DELIVERY_DRY_RUN" "false"
$content = Set-EnvValue $content "TELEGRAM_BOT_TOKEN" $token
[IO.File]::WriteAllText($envPath, $content, [Text.UTF8Encoding]::new($false))

$token = $null
Write-Host "Saved Telegram deep-analysis delivery settings."
Write-Host "- bot: $botLabel"
Write-Host "- target: configured"
Write-Host "- schedule: daily 07:00"
Write-Host "Next: verify with a dry-run first. Live delivery and scheduled-task enablement require separate explicit approval."
