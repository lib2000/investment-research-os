param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [double]$StaleGraceFactor = 2.0,
  [double]$StaleGraceHours = 1.0,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$headers = @{ Authorization = "Bearer $DevUserToken" }

function Invoke-JsonGet {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [hashtable]$Headers = @{},
    [int]$TimeoutSec = 20
  )
  try {
    if ($Headers.Count -gt 0) {
      return Invoke-RestMethod -Uri $Uri -Method Get -Headers $Headers -TimeoutSec $TimeoutSec
    }
    return Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec $TimeoutSec
  } catch {
    throw "API request failed: $Uri - $($_.Exception.Message)"
  }
}

function Convert-SourceDate {
  param([object]$Value)
  if (-not $Value) {
    return $null
  }
  try {
    return [datetimeoffset]::Parse([string]$Value)
  } catch {
    return $null
  }
}

$health = Invoke-JsonGet -Uri "$BaseUrl/api/v1/system/health"
$status = Invoke-JsonGet -Uri "$BaseUrl/api/v1/research-automation/status" -Headers $headers -TimeoutSec 30

$requiredSources = @(
  [pscustomobject]@{ Key = "kcif_reports_watch"; Label = "KCIF macro reports"; RequireRelated = $true },
  [pscustomobject]@{ Key = "regional_business_sources_watch"; Label = "EMERiCs/CSF/KIEP regional macro sources"; RequireRelated = $true },
  [pscustomobject]@{ Key = "naver_research"; Label = "Naver finance research"; RequireRelated = $true },
  [pscustomobject]@{ Key = "shinhan_research"; Label = "Shinhan research"; RequireRelated = $true },
  [pscustomobject]@{ Key = "dart_filing_watch"; Label = "DART holdings and interest filings"; RequireRelated = $false }
)

$now = if ($status.as_of) { Convert-SourceDate $status.as_of } else { [datetimeoffset]::Now }
if (-not $now) {
  $now = [datetimeoffset]::Now
}

$schedule = @($status.source_schedule)
$checks = foreach ($source in $requiredSources) {
  $item = @($schedule | Where-Object { $_.key -eq $source.Key } | Select-Object -First 1)
  if (-not $item) {
    [pscustomobject]@{
      Key = $source.Key
      Label = $source.Label
      Status = "warning"
      Message = "$($source.Label) is missing from source_schedule."
      Enabled = $false
      AutoRefresh = $false
      Due = $null
      RelatedCount = $null
      LastCheckedAt = $null
      AgeHours = $null
      MaxAgeHours = $null
      Policy = $null
    }
    continue
  }

  $lastChecked = Convert-SourceDate $item.last_checked_at
  $refreshHours = if ($item.refresh_hours) { [double]$item.refresh_hours } else { 24.0 }
  $maxAgeHours = ($refreshHours * $StaleGraceFactor) + $StaleGraceHours
  $ageHours = if ($lastChecked) { ($now - $lastChecked).TotalHours } else { $null }
  $relatedCount = if ($null -ne $item.related_count) { [int]$item.related_count } else { 0 }

  $issues = @()
  if (-not [bool]$item.enabled) {
    $issues += "disabled"
  }
  if (-not [bool]$item.auto_refresh) {
    $issues += "auto refresh off"
  }
  if ([string]::IsNullOrWhiteSpace([string]$item.policy)) {
    $issues += "missing policy"
  }
  if (-not $lastChecked) {
    $issues += "missing last_checked_at"
  } elseif ($ageHours -gt $maxAgeHours) {
    $issues += "stale last_checked_at"
  }
  if ($source.RequireRelated -and $relatedCount -le 0) {
    $issues += "no related items"
  }
  $displayLabel = $source.Label

  [pscustomobject]@{
    Key = $source.Key
    Label = $displayLabel
    Status = if ($issues.Count -eq 0) { "success" } else { "warning" }
    Message = if ($issues.Count -eq 0) { "$($source.Label) automation OK" } else { "$($source.Label): $($issues -join ', ')" }
    Enabled = [bool]$item.enabled
    AutoRefresh = [bool]$item.auto_refresh
    Due = [bool]$item.due
    RelatedCount = $relatedCount
    LastCheckedAt = $item.last_checked_at
    AgeHours = if ($null -ne $ageHours) { [math]::Round($ageHours, 2) } else { $null }
    MaxAgeHours = [math]::Round($maxAgeHours, 2)
    Policy = $item.policy
  }
}

$dartDaily = $status.dart_daily_check
if (-not $dartDaily -and $status.last_run) {
  $dartDaily = $status.last_run.dart_daily_check
}
if (-not $dartDaily -and $status.dashboard_digest) {
  $dartDaily = $status.dashboard_digest.dart_daily_check
}
$dartIssues = @()
if ($dartDaily) {
  if ($dartDaily.failure_count -gt 0) {
    $dartIssues += "DART failures: $($dartDaily.failure_count)"
  }
  if ($null -ne $dartDaily.coverage_rate -and [double]$dartDaily.coverage_rate -lt 0.9) {
    $dartIssues += "DART coverage below 90%"
  }
  if ($dartDaily.due -eq $true -and $dartDaily.status -ne "complete") {
    $dartIssues += "DART daily check due but incomplete"
  }
} else {
  $dartIssues += "missing DART daily check"
}

$allOk = (
  $health.status -eq "success" -and
  $health.onedrive_excluded -eq $true -and
  @($checks | Where-Object { $_.Status -ne "success" }).Count -eq 0 -and
  $dartIssues.Count -eq 0
)

$result = [pscustomobject]@{
  Status = if ($allOk) { "success" } else { "warning" }
  BaseUrl = $BaseUrl
  BackendStatus = $health.status
  OneDriveExcluded = [bool]$health.onedrive_excluded
  AsOf = $status.as_of
  SourceScheduleDueCount = if ($null -ne $status.source_schedule_due_count) {
    [int]$status.source_schedule_due_count
  } elseif ($status.last_run -and $null -ne $status.last_run.source_schedule_due_count) {
    [int]$status.last_run.source_schedule_due_count
  } elseif ($status.dashboard_digest -and $null -ne $status.dashboard_digest.source_schedule_due_count) {
    [int]$status.dashboard_digest.source_schedule_due_count
  } else {
    @($checks | Where-Object { $_.Due }).Count
  }
  CheckedSourceCount = @($checks).Count
  FailedSourceCount = @($checks | Where-Object { $_.Status -ne "success" }).Count
  Sources = @($checks)
  DartDailyCheck = [pscustomobject]@{
    Status = $dartDaily.status
    Due = $dartDaily.due
    CoverageRate = $dartDaily.coverage_rate
    CheckedCount = $dartDaily.checked_count
    CurrentTargetCount = $dartDaily.current_target_count
    FailureCount = $dartDaily.failure_count
    ReliabilityStatus = $dartDaily.reliability_status
    ReliabilityMessage = $dartDaily.reliability_message
    Issues = @($dartIssues)
  }
  NextActions = if ($status.next_actions) {
    @($status.next_actions)
  } elseif ($status.dashboard_digest) {
    @($status.dashboard_digest.next_actions)
  } elseif ($status.last_run) {
    @($status.last_run.next_actions)
  } else {
    @()
  }
  Message = if ($allOk) {
    "Research source automation OK"
  } else {
    "Research source automation needs attention"
  }
}

$json = $result | ConvertTo-Json -Depth 8
Write-Output $json

if ($Strict -and -not $allOk) {
  throw $result.Message
}
