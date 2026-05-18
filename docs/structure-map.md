# Investment Research OS 구조 지도

작성일: 2026-05-18

이 문서는 저장소 내부 경로의 공식 역할을 고정합니다. 기능 이동이나 폴더명 변경 전에는 이 문서를 먼저 갱신합니다.

## 공식 경로

| 공식 명칭 | 경로 | 현재 역할 | 변경 정책 |
|---|---|---|---|
| Research OS Backend | `backend\research_os_main.py` | 현재 FastAPI 앱 진입점 | 즉시 삭제하지 않고 라우터/서비스를 단계적으로 분리 |
| Research OS Domain | `backend\research_os\` | 데이터 프로바이더, RAG, 리서치 메모리, 설정 | 새 백엔드 도메인 로직은 이 하위로 이동 |
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

## 실행 가드

로컬 실행 전에는 아래 명령을 통과해야 합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

이 스크립트는 OneDrive 경로, 잘못된 프로젝트 루트, 핵심 진입점 누락을 즉시 차단합니다.
