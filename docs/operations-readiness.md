# 투자 리서치 OS 운영 점검 노트

최종 갱신: 2026-05-29

## 매일 추천 1~3위

- 확인 위치: 콘솔 대시보드의 `오늘 추천 1~3위`, 또는 저장 데이터 탭의 `오늘 추천 1~3위` / `추천 추적 상태`
- 실행 시각: `DAILY_RECOMMENDATIONS_TIME` 기본값 `09:00`
- 저장 위치: `research_vault/_system/daily_recommendations.json`
- 저장 항목: 추천일, 순위, 회사명, 기준가, 통화, 점수 구성, 감점/확인 사유, 근거, 포트폴리오 연결, 사후 추적표
- 품질 가드: 활성 저장자료 중 중복 의심, 본문 보강 필요, OCR 필요, URL-only 정책 자료는 추천 근거에서 감점/확인 플래그로 분리하고, 검증된 저장자료가 충분한 후보만 품질 점수를 받는다.
- 추적 주기: 추천 후 1주일, 15일, 1달, 3달, 6달
- 해외 종목: 원통화 기준 수익률을 우선 저장하고, 화면에는 USD/KRW 환율 반영 필요 여부를 함께 표시한다.

## 소스 자동 수집 품질

- DART 공시: 공시번호와 종목 기준으로 중복을 제외하고, 보유/관심 종목 커버리지를 점검한다.
- 네이버 리서치/시장일지: 저작권 안전 정책에 맞춰 요약/메타데이터 중심으로 저장하고, URL·본문 해시·제목 유사도로 중복을 제외한다.
- KIEP/KCIF: 매크로 보고서 제목, 발행일, 링크, 요약 메타데이터를 시장일지와 리스크 메모에 연결한다.
- EMERiCs/CSF: 지역·중국·신흥국 자료를 제목/링크/발행기관/요약 기준으로 활용한다.

## 포트폴리오 연결

- 추천 후보가 보유 종목이면 포트폴리오 리스크 스캔 우선 확인 대상으로 표시한다.
- 해외주식과 수동 관리 수량은 키움 국내 잔고 동기화가 덮어쓰지 않아야 한다.
- 이형주 포트폴리오의 `PL` 100주 보존은 회귀 검증의 기준 사례다.

## 검증 명령

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckCoreSafeguards -CheckSourceAutomationStatus -CheckDailyRecommendations -CheckStorageQualitySafeguards -CheckPortfolioQuantityProtection -StorageQualityMaxBodyMissing 0 -StorageQualityMaxOcrNeeded 0
python tools\smoke_research_console_clicks.py --url http://127.0.0.1:8001/console/index.html?smoke=clicks
```

## 운영 주의

- 자동 추천은 매수 지시가 아니라 보유/관심 데이터 기반 일일 검토 후보이다.
- 저작권 제한 소스는 원문 전문을 저장하지 않고 메타데이터와 요약 중심으로 연결한다.
- 민감정보와 `.env`는 커밋하지 않는다.
- OneDrive는 작업 루트로 사용하지 않는다.
