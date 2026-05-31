# 투자 리서치 OS 운영 점검 노트

최종 갱신: 2026-05-31

## 매일 추천 1~3위

- 확인 위치: 콘솔 대시보드의 `오늘 추천 1~3위`, 또는 저장 데이터 탭의 `오늘 추천 1~3위` / `추천 추적 상태`
- API 확인: `GET /api/v1/daily-recommendations/status`
- 실행 시각: `DAILY_RECOMMENDATIONS_TIME` 기본값 `09:00`
- 저장 위치: `research_vault/_system/daily_recommendations.json`
- 스케줄 상태 위치: `research_vault/_system/daily_recommendations_state.json`
- 저장 항목: 추천일, 순위, 회사명, 기준가, 통화, 점수 구성, 감점/확인 사유, 근거, 포트폴리오 연결, 사후 추적표
- 화면 표시: 콘솔은 `오늘의 추천 결과`를 제목으로 보여주고, 추천 기록은 일자별 1~3위 목록으로 묶는다. 1주/15일/1달/3달/6달 경과는 요약 막대 그래프와 종목별 타임라인으로 같이 표시한다.
- 품질 가드: 활성 저장자료 중 중복 의심, 본문 보강 필요, OCR 필요, URL-only 정책 자료는 추천 근거에서 감점/확인 플래그로 분리하고, 검증된 저장자료가 충분한 후보만 품질 점수를 받는다.
- 최신성 가드: 추천 저장 점검은 `Asia/Seoul` 날짜 기준으로 최신 추천일이 허용 범위 안에 있고, 해당 일자 추천이 정확히 3개인지 확인한다. 또한 각 후보의 기준가 조회 시각이 24시간을 넘으면 추천 품질 점검에서 실패한다.
- 근거 분산 가드: 추천 후보별 근거가 `저장 품질`, `목표가/리포트`, `최근 저장/RAG`, `보유/관심 범위` 범주를 모두 포함하는지 오프라인 점검에서 확인한다. 저장 품질 대시보드 연결이 없는 후보도 `저장 품질:` 근거와 확인 플래그를 남겨 품질 공백을 숨기지 않는다. 한 범주에만 기대는 추천은 실패로 처리한다.
- 추적 주기: 추천 후 1주일, 15일, 1달, 3달, 6달
- 추적 점검: 오프라인 가드는 각 마일스톤의 목표일이 추천일 기준 7/15/30/90/180일 뒤인지, 추적 완료 항목에 가격·확인시각·수익률이 있는지 확인한다.
- 해외 종목: 원통화 기준 수익률을 우선 저장하고, 화면에는 USD/KRW 환율 반영 필요 여부를 함께 표시한다.

- LLM/RAG 저장 상태: `python tools\check_llm_bridge_store.py --require-active-rag`로 LLM 연동 응답의 원 프롬프트, 응답 본문, Markdown/JSON 저장 파일, RAG 색인 연결을 백엔드 없이 확인한다.

- UI 회귀 가드: `python tools\check_console_static_contract.py --strict`는 추천 결과 화면의 `오늘의 추천 결과`, `일자별 추천 목록`, `경과 그래프` 렌더링 계약과 관련 CSS 클래스를 확인한다.

2026-05-30 기준 최신 저장 상태는 `records` 배열에 일자별 3개 후보가 쌓이는 구조다. 브라우저 화면에서 한글이 정상인데 터미널 JSON만 깨져 보이면 PowerShell/WSL 출력 인코딩 문제일 수 있으므로, 콘솔 화면이나 Python 직접 파일 읽기로 UTF-8 원본을 확인한다.

## 소스 자동 수집 품질

- DART 공시: 공시번호와 종목 기준으로 중복을 제외하고, 보유/관심 종목 커버리지를 점검한다.
- 네이버 리서치/시장일지: 저작권 안전 정책에 맞춰 요약/메타데이터 중심으로 저장하고, URL·본문 해시·제목 유사도로 중복을 제외한다.
- KIEP/KCIF: 매크로 보고서 제목, 발행일, 링크, 요약 메타데이터를 시장일지와 리스크 메모에 연결한다.
- EMERiCs/CSF: 지역·중국·신흥국 자료를 제목/링크/발행기관/요약 기준으로 활용한다.
- 백엔드가 꺼진 상태에서는 `python tools\check_research_source_store.py --strict`로 KCIF, EMERiCs/CSF/KIEP, 네이버 리서치, 신한 리서치, 마감 시황 시장일지, 티커 레지스트리, 중복 Dossier 큐 캐시 상태를 먼저 확인한다. 이 점검은 마감 시황 자동 수집 시도 상태와 리서치 자동화 Dossier 갱신 상태도 함께 확인하며, 네이버 리서치 저장경로 누락은 기본 허용 0건으로 본다.
- 네이버 리서치 캐시에 메타데이터와 PDF 링크는 있으나 저장경로만 비어 있으면 삭제하지 않고 `repair_naver_research_cache(..., save_result=True)` 경로로 Markdown/JSON 저장을 보강한다. 복구 후 `python tools\check_research_source_store.py --strict`에서 `저장경로 누락 0개`, `파일 누락 0개`가 나와야 한다.
- 중복 Dossier 큐 갱신은 `dossier_refresh_queue_status.json`뿐 아니라 `research_automation_status.json`의 상위 `updated_at`과 `last_deduped_dossier_refresh.updated_at`도 함께 갱신해야 한다.
- 네이버/신한 리서치 캐시는 제목·발행일·링크·요약·저장 경로가 모두 있어야 정상이며, 저장 경로의 Markdown/JSON 파일이 실제로 존재해야 한다. 네이버 캐시는 `시황정보` 항목이 있어야 시장일지 자동 활용 흐름을 통과한다.

## 포트폴리오 연결

- 추천 후보가 보유 종목이면 포트폴리오 리스크 스캔 우선 확인 대상으로 표시한다.
- 해외주식과 수동 관리 수량은 키움 국내 잔고 동기화가 덮어쓰지 않아야 한다.
- 이형주 포트폴리오의 `PL` 100주 보존은 회귀 검증의 기준 사례다.
- 백엔드가 꺼진 상태에서는 `python tools\check_portfolio_store.py --portfolio 이형주 --min-holdings 17 --expected-holdings-count 17 --forbid-zero`로 저장 원본 수량을 먼저 확인한다.
- 오프라인 포트폴리오 가드는 `updated_at`, 가격 확인 시각, 해외/수동 수량 `sync_checked_at`, 비중 합계, 저장 총액과 종목 평가금액 합계까지 함께 확인한다. 묶음 점검은 가격 확인과 포트폴리오 갱신 시각이 24시간을 넘으면 실패시켜 실시간 연동 지연을 조기에 잡는다. 종목별로 평가금액, 투자금, 수익, 수익률 계산도 재검산하며 해외 종목은 평가/투자금에 적용된 환율이 서로 크게 어긋나지 않는지 확인한다.
- 보유 종목 수 가드: 이형주 포트폴리오는 정상 기준 17개를 정확히 확인해 다른 포트폴리오 종목이 섞여 화면이 넘치는 회귀를 잡는다.

## 검증 명령

백엔드가 꺼져 있거나 Windows 실행 브리지가 불안정하면 먼저 아래 파일 기반 점검으로 핵심 저장 상태를 확인한다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
python tools\check_offline_readiness.py
python tools\check_git_sync_status.py
python tools\check_git_sync_status.py --strict
python tools\check_backend_runtime_env.py
python tools\check_backend_module_health.py --strict
python tools\check_console_static_contract.py --strict
python tools\check_console_asset_and_js.py
python tools\check_storage_quality_store.py --strict
python tools\check_llm_bridge_store.py --require-active-rag
python tools\build_code_knowledge_graph.py --print-summary
python tools\check_code_knowledge_graph.py --strict
python tools\check_operational_readiness_score.py --strict --min-score 95
python tools\check_portfolio_analysis_coverage.py --all-portfolios --min-average-completion 0.95 --write-backlog --strict
python tools\analyze_code_diff_impact.py --refresh --strict
```

백엔드가 실행 중이면 통합 검증을 사용한다.

`check_backend_runtime_env.py`는 현재 Python 의존성과 `8001` health 응답을 함께 보여준다. 백엔드가 꺼져 있거나 WSL에서 Windows 백엔드에 접근하지 못하는 상태는 기본 점검에서는 권고로 표시하고, 운영 배포 직전처럼 반드시 실행 상태를 강제해야 할 때만 `--strict`를 붙인다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckCoreSafeguards -CheckSourceAutomationStatus -CheckSourceAutomationStore -CheckDailyRecommendations -CheckDailyRecommendationStore -CheckStorageQualitySafeguards -CheckPortfolioQuantityProtection -CheckPortfolioStore -StorageQualityMaxBodyMissing 0 -StorageQualityMaxOcrNeeded 0
python tools\smoke_research_console_clicks.py --url http://127.0.0.1:8001/console/index.html?smoke=clicks
python tools\smoke_research_console_menus.py
python tools\smoke_research_console_external_sources.py
python tools\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 3 --max-latest-age-days 1
```

전체 클릭 스모크는 실제 메뉴/버튼/포트폴리오/LLM/RAG/추천 추적까지 확인하므로 수 분이 걸릴 수 있다. 자동화나 터미널 래퍼에서 실행할 때는 외부 명령 제한 시간을 최소 600초 이상으로 둔다.
정적 콘솔 계약은 상단 액션 피드백과 추천 카드의 `aria-live` 영역도 확인해, 버튼 클릭 후 메시지가 보이지 않는 회귀를 백엔드 없이 잡는다.
메뉴 스모크는 17개 상단 메뉴가 모두 열리는지, 대시보드 주요 버튼에 즉시 피드백이 뜨는지, 버튼 텍스트가 잘리지 않는지 확인한다.
외부 소스 스모크는 KCIF, EMERiCs/CSF/KIEP, 자동화 상태 버튼이 화면에서 실제 결과를 반환하는지 확인한다.


## 코드 정리와 운영 안정화

- 코드 지식 그래프는 백엔드 없이 `research_vault\_system\code_knowledge_graph.json`에 생성되며, 소스코드 원문을 외부로 전송하지 않는다.
- `시스템 구조 맵` 버튼은 운영 콘솔에서 코드/운영 흐름 연결 상태를 보여주는 확인 전용 액션이다.
- 변경 전후에는 `python tools\analyze_code_diff_impact.py --refresh`로 매일 추천, RAG, 포트폴리오, 소스 자동화, 자동 분류, 콘솔 클릭 회귀, 백엔드 모듈 헬스 중 어느 검증을 다시 돌려야 하는지 확인한다.
- 오프라인 준비 점검에는 코드 지식 그래프 엄격 검증, 운영 완성도 95% 점검, 전체 포트폴리오 분석 커버리지 95% 이상 점검, 변경 영향 분석이 포함되어, 필수 흐름이나 핵심 모듈이 빠지거나 새 코드 파일이 그래프에 매핑되지 않으면 운영 전 점검에서 실패한다.

## 빠른 복구/확인 위치

- `현재 작업 디렉토리가 없습니다` 또는 OneDrive 경로가 보이면 PowerShell에서 `. C:\Users\lib20\InvestmentJournalApp\scripts\enter-investment-research-os.ps1`를 실행해 현재 창의 작업 루트를 바로잡는다.
- 콘솔 주소는 `http://127.0.0.1:8001/console/index.html`이고, 백엔드는 `C:\Users\lib20\InvestmentJournalApp`에서 `.\scripts\start-research-backend.ps1 -Port 8001`로 실행한다.
- 매일 추천은 첫 화면의 `오늘 추천 1~3위`, 저장 데이터 탭의 `오늘 추천 1~3위`, `추천 추적 상태`에서 본다. 백엔드가 꺼져 있으면 `python tools\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 3 --max-latest-age-days 1`로 저장 원본을 확인한다.
- 푸시 대기 커밋이 있으면 Windows Git 인증이 가능한 터미널에서 `git push origin main`을 실행한다. OneDrive 경로에서는 푸시 전 검증이나 서버 실행을 하지 않는다.

## 운영 주의

- 자동 추천은 매수 지시가 아니라 보유/관심 데이터 기반 일일 검토 후보이다.
- 저작권 제한 소스는 원문 전문을 저장하지 않고 메타데이터와 요약 중심으로 연결한다.
- 민감정보와 `.env`는 커밋하지 않는다.
- OneDrive는 작업 루트로 사용하지 않는다.
- `python tools\check_git_sync_status.py --strict`는 작업트리 변경이나 원격 ahead가 있을 때 운영 전 점검 실패로 처리한다. 로컬 ahead 커밋은 Windows Git 인증 가능한 터미널에서 `git push origin main`으로 올린다.
