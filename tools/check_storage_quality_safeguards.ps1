param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [int]$MaxBodyMissing = 0,
  [int]$MaxOcrNeeded = 0,
  [int]$BodyMissingItemLimit = 10,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$headers = @{ Authorization = "Bearer $DevUserToken" }
$uri = "$BaseUrl/api/v1/storage/quality-dashboard"

function Get-ValueOrDefault {
  param(
    [object]$Value,
    [object]$DefaultValue
  )
  if ($null -eq $Value) {
    return $DefaultValue
  }
  return $Value
}

try {
  $quality = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -TimeoutSec 20
} catch {
  throw "저장소 품질 대시보드 조회 실패: $($_.Exception.Message)"
}

$bodyMissing = [int](Get-ValueOrDefault $quality.body_missing_count 0)
$ocrNeeded = [int](Get-ValueOrDefault $quality.ocr_needed_count 0)
$archivedCount = [int](Get-ValueOrDefault $quality.archived_count 0)
$legacyOrDuplicate = [int](Get-ValueOrDefault $quality.legacy_or_duplicate_count 0)
$newsQualityIssues = [int](Get-ValueOrDefault $quality.news_quality_issue_count 0)
$policy = $quality.policy
$policyMessage = [string](Get-ValueOrDefault $policy.message "")
$metadataOnlyPolicy = $policyMessage.Contains("원문 본문은 저장하지 않고") -or [string]($policy.news_body_storage) -eq "metadata_only"

$bodyMissingOk = $bodyMissing -le $MaxBodyMissing
$ocrNeededOk = $ocrNeeded -le $MaxOcrNeeded
$softArchiveVisible = $archivedCount -ge 0 -and $legacyOrDuplicate -ge 0
$copyrightPolicyOk = $metadataOnlyPolicy

$bodyMissingItemRows = @(
  foreach ($item in @($quality.body_missing_items)) {
    if ($null -eq $item) {
      continue
    }

    $tags = @($item.tags) | Where-Object { $null -ne $_ -and "$_".Trim() -ne "" }
    [pscustomobject]@{
      Ticker = [string](Get-ValueOrDefault $item.ticker "")
      Date = [string](Get-ValueOrDefault $item.date "")
      FileName = [string](Get-ValueOrDefault $item.file_name "")
      RelativePath = [string](Get-ValueOrDefault $item.relative_path "")
      QualityStatus = [string](Get-ValueOrDefault $item.quality_status "")
      Tags = $tags
      Summary = [string](Get-ValueOrDefault $item.summary "")
    }
  }
)
$bodyMissingItems = @($bodyMissingItemRows | Select-Object -First ([Math]::Max(0, $BodyMissingItemLimit)))

$bodyMissingItemDetailsOk = (
  $bodyMissing -eq 0 -or
  (
    $bodyMissingItems.Count -gt 0 -and
    (
      @($bodyMissingItems | Where-Object {
        [string]::IsNullOrWhiteSpace($_.FileName) -or
        [string]::IsNullOrWhiteSpace($_.RelativePath) -or
        [string]::IsNullOrWhiteSpace($_.QualityStatus)
      }).Count -eq 0
    )
  )
)

$nextActions = @(
  foreach ($action in @($quality.next_actions)) {
    if ($null -ne $action -and "$action".Trim() -ne "") {
      [string]$action
    }
  }
)

$result = [pscustomobject]@{
  Status = if ($bodyMissingOk -and $ocrNeededOk -and $softArchiveVisible -and $copyrightPolicyOk -and $bodyMissingItemDetailsOk) { "success" } else { "warning" }
  Module = $quality.module
  AsOf = $quality.as_of
  ManifestCount = [int](Get-ValueOrDefault $quality.manifest_count 0)
  NormalCount = [int](Get-ValueOrDefault $quality.normal_count 0)
  BodyMissingCount = $bodyMissing
  MaxBodyMissing = $MaxBodyMissing
  BodyMissingOk = $bodyMissingOk
  BodyMissingItemDetailsOk = $bodyMissingItemDetailsOk
  BodyMissingItems = $bodyMissingItems
  OcrNeededCount = $ocrNeeded
  MaxOcrNeeded = $MaxOcrNeeded
  OcrNeededOk = $ocrNeededOk
  ArchivedCount = $archivedCount
  LegacyOrDuplicateCount = $legacyOrDuplicate
  SoftArchiveVisible = $softArchiveVisible
  NewsQualityIssueCount = $newsQualityIssues
  NewsBodyStoragePolicy = $policy.news_body_storage
  CopyrightPolicyOk = $copyrightPolicyOk
  NextActions = $nextActions
  Message = if ($bodyMissingOk -and $ocrNeededOk -and $softArchiveVisible -and $copyrightPolicyOk) {
    if ($bodyMissingItemDetailsOk) {
      "저장소 품질 안전장치 확인 완료"
    } else {
      "저장소 품질 대상 항목 세부정보 확인 필요"
    }
  } else {
    "저장소 품질 안전장치 확인 필요"
  }
}

$json = $result | ConvertTo-Json -Depth 4
Write-Output $json

if ($Strict -and $result.Status -ne "success") {
  throw $result.Message
}
