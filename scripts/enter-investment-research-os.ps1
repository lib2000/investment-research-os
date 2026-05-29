param(
  [switch]$OpenConsole
)

$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp"
if (-not (Test-Path -LiteralPath $ProjectRoot)) {
  throw "Investment Research OS 작업 루트를 찾을 수 없습니다: $ProjectRoot"
}

Set-Location -LiteralPath $ProjectRoot
& (Join-Path $ProjectRoot "tools\assert_project_root.ps1") -ProjectRoot $ProjectRoot | Out-Null

Write-Host "작업 디렉토리를 Investment Research OS 루트로 맞췄습니다."
Write-Host "현재 위치: $ProjectRoot"
Write-Host "백엔드 실행: .\scripts\start-research-backend.ps1 -Port 8001"
Write-Host "콘솔 주소:  http://127.0.0.1:8001/console/index.html"
Write-Host "매일 추천: 콘솔 대시보드의 '오늘 추천 1~3위' 또는 저장 데이터 탭에서 확인"

if ($OpenConsole) {
  Start-Process "http://127.0.0.1:8001/console/index.html"
}
