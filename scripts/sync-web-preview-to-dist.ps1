$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repoRoot "mobile_app\web_preview\index.html"
$dstDir = Join-Path $repoRoot "mobile_app\dist"
$dst = Join-Path $dstDir "index.html"

if (!(Test-Path -LiteralPath $src)) {
    throw "Source file not found: $src"
}

if (!(Test-Path -LiteralPath $dstDir)) {
    New-Item -ItemType Directory -Path $dstDir | Out-Null
}

Copy-Item -LiteralPath $src -Destination $dst -Force
Write-Host "dist sync complete: $dst"
Write-Host "synced_at: $(Get-Date -Format o)"
