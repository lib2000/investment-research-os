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

현재 분리된 도메인 모듈은 아래와 같습니다.

| 모듈 | 역할 | 대표 회귀 테스트 |
|---|---|---|
| `backend\research_os\source_url_preview.py` | 웹 본문 미리보기 응답 조립 | `WebCaptureRenderingTests` |
| `backend\research_os\portfolio_import.py` | CSV/JSON/XLSX 포트폴리오 파일 파싱, 국내/해외 통화 추론 | `BackendModuleBoundaryTests`, `PortfolioPerformanceTests` |
| `backend\research_os\portfolio_sync.py` | 키움 국내 잔고 반영, 해외/수동 보유 수량 보호, 동기화 상태 요약 | `BackendModuleBoundaryTests`, `PortfolioPerformanceTests` |
| `backend\research_os\storage_quality.py` | 소프트 보관 정책, 저장 데이터 품질/OCR/본문 보강 판정 | `BackendModuleBoundaryTests`, `ResearchMemoryPolicyTests` |
| `backend\research_os\system_health.py` | 연구 콘솔/데이터 프로바이더 상태 점검 payload 조립, OneDrive/OCR/라우트 안전 확인 | `BackendModuleBoundaryTests` |
| `backend\research_os\customs_trade.py` | 관세청 수출입 빈 응답 비저장 품질 판정 | `CustomsTradeDataQualityTests` |
| `backend\research_os\market_journal.py` | 네이버 마감 시황 시장일지 출처 메타데이터 | `NaverResearchIngestTests` |

## 실행 가드

로컬 실행 전에는 아래 명령을 통과해야 합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

이 스크립트는 OneDrive 경로, 잘못된 프로젝트 루트, 핵심 진입점 누락을 즉시 차단합니다.
