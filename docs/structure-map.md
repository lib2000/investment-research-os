# Investment Research OS 구조 지도

작성일: 2026-05-18

이 문서는 저장소 내부 경로의 공식 역할을 고정합니다. 기능 이동이나 폴더명 변경 전에는 이 문서를 먼저 갱신합니다.

## 공식 경로

| 공식 명칭 | 경로 | 현재 역할 | 변경 정책 |
|---|---|---|---|
| Research OS Backend | `backend\research_os_main.py` | 현재 FastAPI 앱 진입점 | 즉시 삭제하지 않고 라우터/서비스를 단계적으로 분리 |
| Research OS Domain | `backend\research_os\` | 데이터 프로바이더, RAG, 리서치 메모리, 웹 캡처 유틸, 파일 추출 유틸, 포트폴리오 import/sync, 저장 품질, 엑셀 내보내기 유틸, 설정 | 새 백엔드 도메인 로직은 이 하위로 이동 |
| Journal/Brokerage Domain | `backend\app\` | 기존 매매일지, 증권사 연동 도메인 | Research OS와 섞지 않고 유지 |
| Classic Research Console | `mobile_app\research_console\` | 현재 운영 정적 웹 콘솔 | 기능 안정성 우선. 이동은 별도 단계에서만 수행 |
| React Research Console | `apps\research-console\` | 장기 React/Vite 이관 대상 | 새 화면/리팩터링의 목표 위치 |
| Expo Mobile App | `apps\mobile\` | 장기 모바일 앱 대상 | 모바일 전용 화면과 API 훅 위치 |
| Research Vault | `research_vault\` | 로컬 저장 데이터 | Git 제외. 백엔드 API를 통해서만 읽기/쓰기 |

## 명칭 원칙

- `mobile_app\research_console`은 이름과 달리 현재 모바일 앱이 아니라 Classic Research Console입니다.
- `apps\research-console`은 현재 운영 콘솔을 대체하기 위한 React Research Console입니다.
- 문서, 커밋 메시지, 이슈에서는 가능한 한 `Classic Research Console` 또는 `React Research Console` 명칭을 함께 적습니다.
- 새 기능을 추가할 때는 “현재 운영 콘솔에 즉시 필요한 기능인지”, “React 이관 대상 기능인지”를 먼저 구분합니다.

## 백엔드 분리 가드

`backend\research_os_main.py`는 아직 운영 진입점입니다. 대규모 이동 대신 아래 순서로 쪼갭니다.

1. Pydantic 모델과 순수 유틸리티를 `backend\research_os\models.py` 등 기존 모듈로 이동합니다.
2. `research-memory`, `portfolio`, `market-close`, `capture/file`처럼 도메인별 라우터를 분리합니다.
3. 외부 API 호출과 파일 저장은 서비스 함수로 분리하고, 라우터는 요청/응답 조립만 담당하게 합니다.
4. 각 분리 단계마다 기존 Classic Research Console의 API 호출이 깨지지 않는지 확인합니다.

운영 가드는 `python tools\check_backend_module_health.py --strict`입니다. 2026-06-01 기준 `research_os_main.py`는 23,896줄이고, 스크립트는 도메인 모듈 최소 24개, 메인 파일 26,000줄 상한, 핵심 분리 모듈의 파일 존재와 `research_os_main.py` import 연결을 확인합니다. 큰 기능을 추가할 때 main 파일이 상한에 가까워지면 먼저 서비스 함수 또는 라우터 경계로 분리합니다.

현재 분리된 도메인 모듈은 아래와 같습니다.

| 모듈 | 역할 | 대표 회귀 테스트 |
|---|---|---|
| `backend\research_os\classification.py` | 자동 분류 시스템 태그, 출처 유형 태그, 범위/근거 태그 표준화 | `check_classification_quality.py` |
| `backend\research_os\brokerage.py` | 증권사 연동 공통 클라이언트/상태 추상화 | `BackendModuleBoundaryTests` |
| `backend\research_os\customs_trade.py` | 관세청 수출입 빈 응답 비저장 품질 판정 | `CustomsTradeDataQualityTests` |
| `backend\research_os\daily_recommendations.py` | 매일 추천 1~3위 저장, 스케줄 상태, 사후 추적표, 추천 후보 저장 품질 점수 보정 | `check_daily_recommendations_store.py` |
| `backend\research_os\data_providers.py` | KIS/OpenDART/가격/외부 데이터 프로바이더 호출 | `check_backend_runtime_env.py` |
| `backend\research_os\export_utils.py` | 결과 엑셀 다운로드용 시트/워크북 생성 | `BackendModuleBoundaryTests` |
| `backend\research_os\file_extraction.py` | PDF/이미지/문서 텍스트 추출과 OCR 품질 메타데이터 | `check_storage_quality_store.py` |
| `backend\research_os\kcif_reports.py` | KCIF 보고서 메타데이터 수집/시장일지 연결 | `check_research_source_store.py` |
| `backend\research_os\kiwoom_auth.py` | 키움 인증/토큰 상태 확인 | `smoke_kiwoom_history_live.ps1` |
| `backend\research_os\llm_bridge_status.py` | LLM 응답 저장/RAG 연결 상태 요약 | `smoke_research_console_clicks.py` |
| `backend\research_os\market_journal.py` | 네이버 마감 시황 시장일지 출처 메타데이터 | `NaverResearchIngestTests` |
| `backend\research_os\models.py` | FastAPI 요청/응답 모델 | `python -m py_compile backend\research_os_main.py` |
| `backend\research_os\portfolio_analysis_coverage.py` | 포트폴리오별 보유 종목 분석 커버리지와 보강 큐 생성 | `check_portfolio_analysis_coverage.py` |
| `backend\research_os\portfolio_import.py` | CSV/JSON/XLSX 포트폴리오 파일 파싱, 국내/해외 통화 추론 | `check_portfolio_store.py`, `check_all_portfolio_store.py` |
| `backend\research_os\portfolio_performance.py` | 기간 수익 비교와 가격 갱신 요약 | `check_portfolio_store.py`, `check_all_portfolio_store.py` |
| `backend\research_os\portfolio_store.py` | 포트폴리오 저장 키/정렬 정책 | `check_portfolio_store.py`, `check_all_portfolio_store.py` |
| `backend\research_os\portfolio_sync.py` | 키움 국내 잔고 반영, 해외/수동 보유 수량 보호, 동기화 이력 JSONL 저장/조회, 동기화 상태 요약 | `check_portfolio_store.py`, `check_all_portfolio_store.py` |
| `backend\research_os\rag_memory.py` | RAG 문서 색인/검색/백필 | `smoke_research_console_clicks.py` |
| `backend\research_os\regional_sources.py` | EMERiCs/CSF/KIEP 지역·중국·대외 자료 수집 | `check_research_source_store.py` |
| `backend\research_os\research_memory.py` | 저장 데이터 마크다운/JSON 기록과 manifest 관리 | `check_storage_quality_store.py` |
| `backend\research_os\security.py` | 개발 토큰/사용자 토큰 검증 | `status_research_console.ps1` |
| `backend\research_os\settings.py` | 환경변수 기반 운영 설정 | `check_backend_runtime_env.py` |
| `backend\research_os\source_url_preview.py` | 웹 본문 미리보기 응답 조립 | `WebCaptureRenderingTests` |
| `backend\research_os\storage_quality.py` | 소프트 보관 정책, 저장 데이터 품질/OCR/본문 보강 판정 | `check_storage_quality_store.py` |
| `backend\research_os\system_health.py` | 연구 콘솔/데이터 프로바이더 상태 점검 payload 조립, OneDrive/OCR/라우트 안전 확인 | `status_research_console.ps1` |
| `backend\research_os\ticker_registry.py` | 한국/미국 티커 레지스트리 캐시와 회사명 매칭 | `check_research_source_store.py` |
| `backend\research_os\web_capture.py` | 웹 본문 추출, URL-only 예외 처리, 표시용 컨텍스트 | `WebCaptureRenderingTests` |

## 코드 지식 그래프

Understand-Anything류의 코드 이해 방식을 로컬 운영에 맞춰 가볍게 접목했습니다. 외부 서비스로 코드를 보내지 않고, 저장소 내부의 백엔드/콘솔/도구/운영 문서를 스캔해 `research_vault\_system\code_knowledge_graph.json`에 구조 그래프를 생성합니다.

```powershell
python tools\build_code_knowledge_graph.py --print-summary
python tools\check_code_knowledge_graph.py --strict
python tools\analyze_code_diff_impact.py --refresh --strict
```

그래프는 아래 운영 흐름을 코드 파일, API route, 콘솔 API 호출, DOM 버튼과 연결합니다.

| 흐름 | 확인 목적 |
|---|---|
| 매일 추천 1~3위 | 추천 생성, 저장, 추적표 회귀 범위 확인 |
| 저장 데이터/RAG | LLM 저장, RAG 색인, 저장/RAG 상태 연결 확인 |
| 포트폴리오 실시간/수량 보호 | 수량 덮어쓰기, 가격 갱신, 수익률 계산 영향 확인 |
| 외부 리포트/소스 자동화 | KCIF/KIEP/네이버/신한/지역 소스 수집 영향 확인 |
| 자동 분류 태그/RAG 품질 | 범위/출처/시스템 태그 근거와 품질 점검 연결 확인 |
| 콘솔 클릭/쓰기 회귀 | 버튼 피드백, 쓰기 액션, 메뉴 스모크 영향 확인 |
| 백엔드 모듈 헬스/구조 안정화 | main 파일 비대화, 모듈 경계, 운영 가드 영향 확인 |

Classic Research Console의 저장 데이터 탭에는 `시스템 구조 맵` 버튼이 있으며, 생성된 그래프의 노드/엣지 수, 운영 흐름 연결 상태, 추천/저장품질/소스/포트폴리오 운영 주의 신호를 한국어로 보여줍니다. `python tools\check_code_knowledge_graph.py --strict`는 그래프 생성 시각, node/edge 집계, summary 흐름 집계도 함께 검증합니다. 구조 변경 전에는 `python tools\analyze_code_diff_impact.py --refresh`로 어떤 운영 흐름을 다시 검증해야 하는지 먼저 확인합니다.

## 실행 가드

로컬 실행 전에는 아래 명령을 통과해야 합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

이 스크립트는 OneDrive 경로, 잘못된 프로젝트 루트, 핵심 진입점 누락을 즉시 차단합니다.
