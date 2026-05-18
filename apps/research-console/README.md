# Research Console App

이 폴더는 장기 React/Vite 웹 콘솔 이관 대상입니다.

현재 운영 화면은 아직 `mobile_app/research_console`에 있습니다. 새 화면을 만들 때는 기존 콘솔을 바로 삭제하지 않고, 이 폴더에서 화면 단위로 옮깁니다.

## 이관 원칙

- API 계약은 `backend/research_os_main.py`와 현재 `mobile_app/research_console/api.js`를 기준으로 유지합니다.
- 화면 상태는 React 컴포넌트와 훅으로 분리합니다.
- 저장, 분석, 외부 API 호출은 모두 백엔드 API를 통해 수행합니다.
- `research_vault` 파일을 프론트엔드에서 직접 수정하지 않습니다.

## 우선 이관 화면

1. 포트폴리오
2. 대시보드
3. 정보입력
4. 시장일지
5. 저장 데이터

## 현재 준비된 기반 모듈

- `src/shared/api/client.js`: FastAPI 공통 요청 클라이언트
- `src/shared/api/portfolioApi.js`: 포트폴리오 API 계약 래퍼
- `src/shared/format/money.js`: 원화/달러/숫자 포맷
- `src/shared/format/percent.js`: 수익률 포맷과 부호 판정
- `src/features/portfolio/portfolioModel.js`: 포트폴리오 보유 종목 정규화, 수익/수익률 계산, 정렬, 입력 검증

## 검증

```powershell
cd C:\Users\lib20\InvestmentJournalApp\apps\research-console
npm run check
npm run test:portfolio
npm run test:portfolio-api
npm run verify
```

`test:portfolio-api`는 백엔드 `http://127.0.0.1:8001`이 실행 중일 때 저장된 `가족 합산`, `김효경`, `이지원`, `이형주` 포트폴리오의 서버 총액과 React 계산 총액을 비교합니다.

## 개발 서버

의존성이 설치되어 있으면 아래 명령으로 새 React 콘솔을 확인합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp\apps\research-console
npm run dev
```

브라우저 주소:

```text
http://127.0.0.1:5173
```

기존 운영 콘솔은 계속 `mobile_app/research_console`을 사용합니다.
