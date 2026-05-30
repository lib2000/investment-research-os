# 투자 리서치 OS 운영 점검 노트

최종 갱신: 2026-05-30

## 매일 추천 1~3위

- 확인 위치: 콘솔 대시보드의 `오늘 추천 1~3위`, 또는 저장 데이터 탭의 `오늘 추천 1~3위` / `추천 추적 상태`
- API 확인: `GET /api/v1/daily-recommendations/status`
- 실행 시각: `DAILY_RECOMMENDATIONS_TIME` 기본값 `09:00`
- 저장 위치: `research_vault/_system/daily_recommendations.json`
- 스케줄 상태 위치: `research_vault/_system/daily_recommendations_state.json`
- 저장 항목: 추천일, 순위, 회사명, 기준가, 통화, 점수 구성, 감점/확인 사유, 근거, 포트폴리오 연결, 사후 추적표
- 품질 가드: 활성 저장자료 중 중복 의심, 본문 보강 필요, OCR 필요, URL-only 정책 자료는 추천 근거에서 감점/확인 플래그로 분리하고, 검증된 저장자료가 충분한 후보만 품질 점수를 받는다.
- 추적 주기: 추천 후 1주일, 15일, 1달, 3달, 6달
- 추적 점검: 오프라인 가드는 각 마일스톤의 목표일이 추천일 기준 7/15/30/90/180일 뒤인지, 추적 완료 항목에 가격·확인시각·수익률이 있는지 확인한다.
- 해외 종목: 원통화 기준 수익률을 우선 저장하고, 화면에는 USD/KRW 환율 반영 필요 여부를 함께 표시한다.

2026-05-30 기준 최신 저장 상태는 `records` 배열에 일자별 3개 후보가 쌓이는 구조다. 브라우저 화면에서 한글이 정상인데 터미널 JSON만 깨져 보이면 PowerShell/WSL 출력 인코딩 문제일 수 있으므로, 콘솔 화면이나 Python 직접 파일 읽기로 UTF-8 원본을 확인한다.

## 소스 자동 수집 품질

- DART 공시: 공시번호와 종목 기준으로 중복을 제외하고, 보유/관심 종목 커버리지를 점검한다.
- 네이버 리서치/시장일지: 저작권 안전 정책에 맞춰 요약/메타데이터 중심으로 저장하고, URL·본문 해시·제목 유사도로 중복을 제외한다.
- KIEP/KCIF: 매크로 보고서 제목, 발행일, 링크, 요약 메타데이터를 시장일지와 리스크 메모에 연결한다.
- EMERiCs/CSF: 지역·중국·신흥국 자료를 제목/링크/발행기관/요약 기준으로 활용한다.
- 백엔드가 꺼진 상태에서는 `python tools\check_research_source_store.py --strict`로 KCIF, EMERiCs/CSF/KIEP, 네이버 리서치, 신한 리서치, 마감 시황 시장일지, 티커 레지스트리, 중복 Dossier 큐 캐시 상태를 먼저 확인한다.
- 네이버/신한 리서치 캐시는 제목·발행일·링크·요약·저장 경로가 모두 있어야 정상이며, 네이버 캐시는 `시황정보` 항목이 있어야 시장일지 자동 활용 흐름을 통과한다.

## 포트폴리오 연결

- 추천 후보가 보유 종목이면 포트폴리오 리스크 스캔 우선 확인 대상으로 표시한다.
- 해외주식과 수동 관리 수량은 키움 국내 잔고 동기화가 덮어쓰지 않아야 한다.
- 이형주 포트폴리오의 `PL` 100주 보존은 회귀 검증의 기준 사례다.
- 백엔드가 꺼진 상태에서는 `python tools\check_portfolio_store.py --portfolio 이형주 --min-holdings 17 --forbid-zero`로 저장 원본 수량을 먼저 확인한다.
- 오프라인 포트폴리오 가드는 `updated_at`, 가격 확인 시각, 해외/수동 수량 `sync_checked_at`, 비중 합계, 저장 총액과 종목 평가금액 합계까지 함께 확인한다.

## 검증 명령

백엔드가 꺼져 있거나 Windows 실행 브리지가 불안정하면 먼저 아래 파일 기반 점검으로 핵심 저장 상태를 확인한다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
python tools\check_offline_readiness.py
python tools\check_git_sync_status.py
python tools\check_backend_runtime_env.py
python tools\check_backend_module_health.py --strict
python tools\check_console_static_contract.py --strict
python tools\check_console_asset_and_js.py
python tools\check_storage_quality_store.py --strict
```

백엔드가 실행 중이면 통합 검증을 사용한다.

`check_backend_runtime_env.py`는 현재 Python 의존성과 `8001` health 응답을 함께 보여준다. 백엔드가 꺼져 있거나 WSL에서 Windows 백엔드에 접근하지 못하는 상태는 기본 점검에서는 권고로 표시하고, 운영 배포 직전처럼 반드시 실행 상태를 강제해야 할 때만 `--strict`를 붙인다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckCoreSafeguards -CheckSourceAutomationStatus -CheckSourceAutomationStore -CheckDailyRecommendations -CheckDailyRecommendationStore -CheckStorageQualitySafeguards -CheckPortfolioQuantityProtection -CheckPortfolioStore -StorageQualityMaxBodyMissing 0 -StorageQualityMaxOcrNeeded 0
python tools\smoke_research_console_clicks.py --url http://127.0.0.1:8001/console/index.html?smoke=clicks
python tools\check_daily_recommendations_store.py --require-milestones --require-quality
```

전체 클릭 스모크는 실제 메뉴/버튼/포트폴리오/LLM/RAG/추천 추적까지 확인하므로 수 분이 걸릴 수 있다. 자동화나 터미널 래퍼에서 실행할 때는 외부 명령 제한 시간을 최소 600초 이상으로 둔다.

## 운영 주의

- 자동 추천은 매수 지시가 아니라 보유/관심 데이터 기반 일일 검토 후보이다.
- 저작권 제한 소스는 원문 전문을 저장하지 않고 메타데이터와 요약 중심으로 연결한다.
- 민감정보와 `.env`는 커밋하지 않는다.
- OneDrive는 작업 루트로 사용하지 않는다.
