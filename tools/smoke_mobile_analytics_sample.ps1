param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$ApiBaseUrl = "http://127.0.0.1:8010",
  [string]$DevUserToken = "dev-local-token",
  [switch]$KeepSampleData
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

function Assert-Condition {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

$headers = @{
  Authorization = "Bearer $DevUserToken"
  "Content-Type" = "text/csv; charset=utf-8"
}
$authHeaders = @{ Authorization = "Bearer $DevUserToken" }

function Remove-SmokeAnalyticsTransactions {
  $list = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/api/v1/manual-transactions?page=1&page_size=100" `
    -Method Get `
    -Headers $authHeaders

  $targets = @($list.transactions | Where-Object {
      $_.broker -eq "SMOKE_ANALYTICS" -or $_.memo -eq "analytics smoke"
    })

  foreach ($transaction in $targets) {
    if ($transaction.id) {
      Invoke-RestMethod `
        -Uri "$ApiBaseUrl/api/v1/manual-transactions/$($transaction.id)" `
        -Method Delete `
        -Headers $authHeaders | Out-Null
      Write-Host "deleted existing sample transaction $($transaction.id)"
    }
  }
}

$csv = @"
거래일,증권사,계좌,유형,종목코드,종목명,수량,가격,매매손익,배당,세금,수수료,통화,메모
2026-01-15,SMOKE_ANALYTICS,성장계좌,trade,SMK001,샘플성장,1,1000,120,0,5,2,KRW,analytics smoke
2026-02-18,SMOKE_ANALYTICS,성장계좌,trade,SMK002,샘플방어,2,1500,-40,0,3,2,KRW,analytics smoke
2026-03-20,SMOKE_ANALYTICS,배당계좌,dividend,SMK001,샘플성장,0,0,0,35,4,1,KRW,analytics smoke
"@

Write-Host "분석 샘플 데이터 스모크 테스트를 시작합니다."
Remove-SmokeAnalyticsTransactions

$importResult = Invoke-RestMethod `
  -Uri "$ApiBaseUrl/api/v1/manual-transactions/import.csv" `
  -Method Post `
  -Headers $headers `
  -Body $csv

Assert-Condition ($importResult.status -eq "success") "CSV 가져오기 응답 상태가 success가 아닙니다."
Assert-Condition ($importResult.imported_count -eq 3) "CSV 샘플 3건을 가져오지 못했습니다."
Write-Host "OK sample CSV import"

try {
  $analytics = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/api/v1/journal/analytics?start_date=2026-01-01&end_date=2026-12-31" `
    -Method Get `
    -Headers $authHeaders

  Assert-Condition ($analytics.status -eq "success") "분석 API 응답 상태가 success가 아닙니다."
  Assert-Condition ($analytics.manual_transactions_count -ge 3) "분석 API에 수동 거래가 반영되지 않았습니다."
  Assert-Condition ($analytics.monthly_profit.Count -gt 0) "월간 수익 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.quarterly_profit.Count -gt 0) "분기 수익 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.annual_profit.Count -gt 0) "연간 수익 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.profit_trend.Count -gt 0) "수익 추이 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.ticker_allocation.Count -gt 0) "종목별 비중 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.type_allocation.Count -gt 0) "유형별 비중 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.account_allocation.Count -gt 0) "계좌별 비중 데이터가 생성되지 않았습니다."
  Assert-Condition ($analytics.dividend_total -ge 35) "배당 데이터가 반영되지 않았습니다."
  Assert-Condition ($analytics.tax_total -ge 12) "세금 데이터가 반영되지 않았습니다."
  Assert-Condition ($analytics.commission_total -ge 5) "수수료 데이터가 반영되지 않았습니다."

  Write-Host "OK analytics with sample data"
  Write-Host ("총손익: {0}, 배당: {1}, 세금: {2}, 수수료: {3}" -f `
    $analytics.realized_profit_loss_total,
    $analytics.dividend_total,
    $analytics.tax_total,
    $analytics.commission_total)
} finally {
  if (-not $KeepSampleData) {
    foreach ($transaction in $importResult.transactions) {
      if ($transaction.id) {
        Invoke-RestMethod `
          -Uri "$ApiBaseUrl/api/v1/manual-transactions/$($transaction.id)" `
          -Method Delete `
          -Headers $authHeaders | Out-Null
        Write-Host "deleted sample transaction $($transaction.id)"
      }
    }
  } else {
    Write-Host "샘플 데이터를 유지했습니다. 삭제하려면 수동입력 목록에서 SMOKE_ANALYTICS 항목을 삭제하세요."
  }
}

Write-Host "분석 샘플 데이터 스모크 테스트 통과"
