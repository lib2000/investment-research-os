$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$src = Join-Path $repoRoot "mobile_app\web_preview\index.html"
$dst = Join-Path $repoRoot "mobile_app\dist\index.html"

if (!(Test-Path -LiteralPath $src)) {
    throw "Source file not found: $src"
}

if (!(Test-Path -LiteralPath $dst)) {
    throw "Dist file not found: $dst"
}

$srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash
$dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash

if ($srcHash -ne $dstHash) {
    Write-Error "web_preview and dist are out of sync. Run scripts\sync-web-preview-to-dist.ps1"
}

Write-Host "web_preview and dist are in sync."
Write-Host "sha256: $srcHash"
