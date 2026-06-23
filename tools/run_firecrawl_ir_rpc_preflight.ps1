param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [Parameter(Mandatory = $true)]
  [string]$EnvFile,
  [ValidateSet("Preflight", "Submit")]
  [string]$Mode = "Preflight",
  [string]$OutputJson = "output\firecrawl-ir-rpc-preflight.json",
  [string]$SubmitOutputJson = "output\firecrawl-ir-rpc-submit.json",
  [switch]$EnvOverride
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([System.IO.Path]::IsPathRooted($EnvFile)) {
  $EnvFilePath = (Resolve-Path -LiteralPath $EnvFile).Path
} else {
  $EnvFilePath = (Resolve-Path -LiteralPath (Join-Path $ProjectRootPath $EnvFile)).Path
}

function Invoke-FirecrawlCheck {
  param(
    [string[]]$Arguments,
    [string]$Label
  )

  Write-Host ""
  Write-Host "==> $Label"
  python @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

Push-Location $ProjectRootPath
try {
  $preflightArgs = @(
    "tools\check_firecrawl_ir_collector.py",
    "--env-file",
    $EnvFilePath,
    "--require-env-registry",
    "--require-rpc-ready",
    "--output-json",
    $OutputJson
  )
  if ($EnvOverride) {
    $preflightArgs += "--env-override"
  }

  Invoke-FirecrawlCheck -Label "Firecrawl IR RPC readiness preflight" -Arguments $preflightArgs

  if ($Mode -eq "Submit") {
    $submitArgs = @(
      "tools\check_firecrawl_ir_collector.py",
      "--env-file",
      $EnvFilePath,
      "--require-env-registry",
      "--submit",
      "--output-json",
      $SubmitOutputJson
    )
    if ($EnvOverride) {
      $submitArgs += "--env-override"
    }

    Invoke-FirecrawlCheck -Label "Firecrawl IR RPC submit" -Arguments $submitArgs
  }

  Write-Host ""
  Write-Host "Firecrawl IR RPC pipeline completed: $Mode"
} finally {
  Pop-Location
}
