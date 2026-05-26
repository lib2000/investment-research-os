# 장기 운영 아키텍처

작성일: 2026-05-10

## 목표

현재 시스템은 이미 프론트엔드와 백엔드를 분리한 풀스택 구조입니다. 장기 운영에서는 기능이 계속 늘어날수록 화면 상태, 외부 데이터 연동, 저장 데이터, 분석 로직이 섞이지 않도록 경계를 고정해야 합니다.

이 문서는 기존 앱을 깨지 않고 React 기반 프론트엔드로 점진 이관할 수 있는 기준 구조를 정의합니다.

## 기준 구조

```text
InvestmentJournalApp/
  apps/
    research-console/          # 장기 React/Vite 웹 콘솔 대상
    mobile/                    # Expo/React Native 모바일 앱 대상
  backend/
    research_os_main.py        # 현재 Research OS FastAPI 진입점
    main.py                    # 기존 매매일지 API 진입점
    research_os/               # 투자 리서치 도메인
    app/                       # 증권사/매매일지 도메인
    requirements.txt
  mobile_app/
    research_console/          # 현재 운영 중인 웹 콘솔
    App.js                     # 현재 Expo 앱
  research_vault/              # 분석 결과, 메모, 포트폴리오, RAG 저장소
  docs/
  scripts/
```

## 운영 원칙

- 활성 프로젝트 루트는 `C:\Users\lib20\InvestmentJournalApp`입니다.
- OneDrive 경로에서는 서버 실행, 파일 저장, 코드 수정을 하지 않습니다.
- 프론트엔드는 화면 상태와 사용자 입력만 담당합니다.
- 백엔드는 데이터 검증, 외부 API 호출, 계산, 파일 저장, 분석 실행을 담당합니다.
- `research_vault`는 사용자가 축적한 투자 지식 저장소입니다. 화면 코드는 이 폴더에 직접 쓰지 않고 백엔드 API를 통해서만 저장합니다.
- 증권사/API 키는 `backend\.env`에만 둡니다. 프론트엔드에는 키를 넣지 않습니다.

## 현재 구조와 장기 구조의 연결

현재 운영 화면은 `mobile_app/research_console`입니다. 이 폴더의 공식 명칭은 **Classic Research Console**입니다. 폴더명에 `mobile_app`이 들어 있지만, 현재 역할은 데스크톱/브라우저 웹 콘솔입니다.

장기 React 전환은 `apps/research-console`에서 시작합니다. 이 폴더의 공식 명칭은 **React Research Console**입니다. 새 화면을 만들 때는 기존 API 계약을 바꾸지 않고, `mobile_app/research_console/api.js`의 호출 흐름을 새 API 클라이언트로 옮깁니다.

경로별 공식 명칭과 변경 정책은 [structure-map.md](structure-map.md)를 기준으로 합니다.

## 프론트엔드 이관 순서

1. 공통 API 클라이언트 분리
2. 탭 상태와 결과 출력 상태 분리
3. 대시보드/포트폴리오처럼 상태가 복잡한 화면부터 React 컴포넌트화
4. 정보입력/시장일지/저장 데이터처럼 공통 저장 흐름을 훅으로 통합
5. 기존 `mobile_app/research_console`을 읽기 전용 레거시 콘솔로 전환

## 백엔드 정리 순서

1. `research_os_main.py`의 Pydantic 모델과 순수 유틸리티를 기존 `backend/research_os/` 모듈로 이동
2. `research-memory`, `portfolio`, `market-close`, `capture/file` 라우터를 도메인별 파일로 분리
3. 데이터 프로바이더를 `providers/` 계층으로 분리
4. 포트폴리오, 시장일지, RAG, 파일 처리 로직을 서비스 계층으로 정리
5. SQLite 로컬 저장은 유지하되 운영 전환 시 PostgreSQL 어댑터를 추가
6. 스케줄러는 별도 모듈에서 관리하고 실행 여부를 설정으로 통제

`research_os_main.py`는 현재 운영 진입점이므로 한 번에 대체하지 않습니다. 각 분리 단계는 Classic Research Console의 기존 API 호출을 통과시킨 뒤 다음 단계로 넘어갑니다.

현재까지 1단계 일부가 진행되어, 웹 URL 미리보기, 포트폴리오 파일 import, 포트폴리오 수량 동기화/보호, 저장 데이터 품질 판정, 연구 콘솔 상태 점검 payload, 관세청 수출입 품질 판정이 `backend/research_os/` 하위 순수 모듈로 분리되었습니다. 다음 분리 대상은 라우터 자체가 아니라, 테스트 가능한 서비스 함수부터 작게 떼어내는 방식으로 진행합니다.

## API 경계

프론트엔드는 다음 영역의 API만 호출합니다.

- `/api/v1/data-providers/*`: 데이터 프로바이더 상태와 스냅샷
- `/api/v1/analysis/modules/*`: 분석 모듈 실행
- `/api/v1/research-memory/*`: 정보 입력, 저장 데이터, RAG 메모리
- `/api/v1/portfolio/*`: 포트폴리오 저장/편집/리스크
- `/api/v1/market-close/*`: 시장일지 저장/조회
- `/api/v1/brokerage/*`: 증권사 연동 상태/조회

프론트엔드는 `research_vault` 파일을 직접 읽거나 쓰지 않습니다.

## 비용 통제

- FMP 무료 한도 초과 시 합성 숫자를 만들지 않고 경고만 표시합니다.
- Tavily/Brave는 일간/월간 사용량 가드를 둡니다.
- Financial Datasets는 비활성화 상태를 기본으로 유지합니다.
- LLM은 자동 웹 조작 없이 수동 프롬프트/응답 저장 방식으로 운영합니다.

## 완료 기준

장기 구조 정리 완료는 다음 상태를 의미합니다.

- 실행 명령이 `scripts/`에서 표준화됨
- README가 현재 운영 주소와 장기 구조를 모두 설명함
- 새 기능은 프론트엔드 화면, 백엔드 API, 저장소 역할을 분리해서 추가됨
- 기존 콘솔을 유지하면서 React 이관이 가능함
