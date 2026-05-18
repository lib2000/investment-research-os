# Investment Journal App 작업 결과 요약

작성일: 2026-05-16
작업 경로: `C:\Users\lib20\InvestmentJournalApp`
주의: 본 문서는 민감정보를 제외하고 작성했다. API 키, 시크릿, 토큰, 계좌번호 원문, 개인 인증값은 포함하지 않는다.

## 1. 프로젝트 방향

개인 투자자가 사용할 투자 관리 앱을 목표로 한다.

핵심 기능은 다음과 같다.

- 키움증권 REST API 기반 포트폴리오/거래 데이터 연동
- 매매일지 초안 생성 및 수동 일지 작성
- 과거 거래 이력 불러오기
- 타 증권사 거래내역 수동 입력
- 수익, 비중, 배당, 세금 중심 분석
- 모바일 앱을 고려한 백엔드 API 게이트웨이 구조

보안상 모바일 앱에서 증권사 API를 직접 호출하지 않고 아래 구조를 사용한다.

```text
모바일/웹 클라이언트
  -> 자체 백엔드 API 게이트웨이
  -> 증권사 API
```

## 2. 기술 구성

백엔드:

- Python
- FastAPI
- Uvicorn
- SQLite 로컬 DB
- 키움증권 REST API 연동 모듈

프론트 미리보기:

- 정적 HTML/CSS/JavaScript
- 파일 위치: `mobile_app\web_preview\index.html`
- 배포용 정적 파일 위치: `mobile_app\dist\index.html`

React Native 모바일 앱:

- Expo SDK 55
- React Native 0.83
- React 19.2
- TypeScript
- TanStack Query 5
- react-native-gifted-charts
- 파일 위치: `apps\mobile`

현재 개발용 포트:

- 백엔드 API: `http://127.0.0.1:8010`
- 프론트 미리보기: `http://127.0.0.1:8082`

참고:

- `8000` 포트에는 오래된 리스너가 남아 있어 현재 앱에서는 사용하지 않는다.
- 프론트의 `API_BASE_URL`은 `http://127.0.0.1:8010`으로 설정되어 있다.

## 3. 보안 및 민감정보 처리

적용한 원칙:

- API 키, 시크릿, 토큰은 코드에 하드코딩하지 않는다.
- `.env` 환경 변수를 통해 민감정보를 읽는다.
- 화면/문서/로그에는 민감정보 원문을 출력하지 않는다.
- 토큰 테스트 결과는 마스킹된 값만 표시한다.
- 계좌번호 등 개인 식별 가능 정보는 원문 저장을 금지하고 해시 + 마스킹으로 통일한다.
- SQLite 파일은 WAL 모드와 접근 권한 제한을 적용한다.
- SQLite 암호화 키가 설정됐는데 SQLCipher 지원 드라이버가 아니면 서버 시작을 실패시킨다.
- SQLite DB는 hot backup 방식으로 주기 백업하고 오래된 백업을 자동 정리한다.

민감정보 예시:

- 키움 App Key
- 키움 App Secret
- 접근 토큰
- 계좌번호 원문
- 개인 인증용 토큰
- SECRET_SALT 값

이 문서에는 위 값들을 포함하지 않았다.

## 4. 키움증권 연동 진행 상태

첫 연동 증권사는 키움증권으로 확정했다.

구현/검증한 영역:

- OAuth 접근 토큰 발급 테스트
- 계좌번호 조회 테스트
- 계좌평가잔고/보유종목 조회 테스트
- 당일매매일지 조회 테스트
- 주문체결내역 상세 조회 테스트
- 포트폴리오 조회 API
- 매매일지 원천 거래 조회 API

토큰 자동 갱신/회전:

- 접근 토큰을 매번 새로 발급하지 않고 `brokerage_tokens` 테이블에 캐시한다.
- 만료 예정 시간이 설정 버퍼 이내로 들어오면 백엔드가 자동으로 새 access token을 발급받아 저장한다.
- 키움 REST API 공식 문서의 현재 접근토큰 발급 응답은 `expires_dt`, `token_type`, `token` 중심이며 refresh token 필드는 없다.
- 따라서 현재 기본 동작은 refresh token 갱신이 아니라 `client_credentials` 기반 access token 재발급이다.
- 향후 refresh token을 제공하는 증권사 또는 키움 정책 변경에 대비해 refresh token 저장 컬럼과 옵션을 준비했다.
- 토큰 테스트 API는 원문 토큰을 반환하지 않고 마스킹 값만 반환한다.

관련 설정:

```env
TOKEN_EXPIRY_BUFFER_SECONDS=300
KIWOOM_ALLOW_REFRESH_TOKEN=false
```

운영 배포 시 토큰 저장소는 SQLite/DB 평문 저장이 아니라 Secret Manager, KMS, Vault 등 안전한 키 저장소로 이전하는 것이 권장된다.

계좌번호 저장 정책:

- 키움 계좌번호 조회 API는 원문 계좌번호를 반환하지 않는다.
- 표시용 값은 앞 4자리와 뒤 2자리만 남긴 마스킹 값으로 반환한다.
- 식별용 값은 `SECRET_SALT`를 사용한 SHA-256 해시 앞 16자리만 사용한다.
- 매매일지 초안 payload 저장 전 계좌번호 필드는 원문 대신 `*_hash`, `*_masked` 필드로 치환한다.
- 수동입력 계좌명에 계좌번호로 보이는 숫자열이 들어오면 DB에는 마스킹 계좌명과 `account_hash`만 저장한다.

키움 API 사용 시 확인한 운영 조건:

- 키움 REST API 사용을 위해 허용 IP 등록이 필요하다.
- 현재 개발 환경에서는 로컬 개발 PC 또는 API 서버가 외부로 나가는 공인 IP를 등록해야 한다.
- 모바일 앱은 키움 API를 직접 호출하지 않고 백엔드 API만 호출한다.

## 5. 백엔드 주요 API

현재 백엔드 주요 API는 다음과 같다.

포트폴리오:

- `GET /api/v1/portfolio`

키움 테스트:

- `POST /api/v1/brokerage/kiwoom/token-test`
- `POST /api/v1/brokerage/kiwoom/accounts-test`
- `POST /api/v1/brokerage/kiwoom/balance-test`
- `POST /api/v1/brokerage/kiwoom/trade-journal-test`
- `POST /api/v1/brokerage/kiwoom/order-executions-test`

동기화:

- `POST /api/v1/sync/kiwoom`
- `GET /api/v1/sync/latest`

과거 거래 불러오기:

- `POST /api/v1/sync/kiwoom/history/start`
- `GET /api/v1/sync/kiwoom/history/latest`
- `GET /api/v1/sync/kiwoom/history/jobs/{job_id}`
- `POST /api/v1/sync/kiwoom/history/jobs/{job_id}/cancel`
- `DELETE /api/v1/sync/kiwoom/history/records`

매매일지:

- `GET /api/v1/journal/source-trades`
- `GET /api/v1/journal/drafts?page=1&page_size=50`
- `POST /api/v1/journal/entries`
- `GET /api/v1/journal/entries?page=1&page_size=50`
- `DELETE /api/v1/journal/entries/{entry_id}`
- `GET /api/v1/journal/entries/export.csv`

타 증권사/수동 거래:

- `GET /api/v1/manual-transactions?page=1&page_size=100`
- `POST /api/v1/manual-transactions`
- `POST /api/v1/manual-transactions/import.csv`
- `DELETE /api/v1/manual-transactions/{transaction_id}`

분석:

- `GET /api/v1/journal/analytics`
- `GET /api/v1/analytics/journal` legacy redirect

관리/백업:

- `GET /api/v1/admin/backups`
- `POST /api/v1/admin/backups`

분석 API 정식 경로는 `GET /api/v1/journal/analytics`로 정리했다.
분석 API는 `start_date`, `end_date` 선택 기간 필터를 지원한다.

React Native 이전 준비:

- `GET /api/v1/journal/drafts`에 `page`, `page_size` 페이지네이션을 추가했다.
- `GET /api/v1/journal/entries`에 `page`, `page_size` 페이지네이션을 추가했다.
- `GET /api/v1/manual-transactions`에 `page`, `page_size` 페이지네이션을 추가했다.
- 각 목록 응답은 `total`, `page`, `page_size`, `total_pages`, `has_next`, `has_previous`를 포함한다.
- 기존 웹 미리보기 호환을 위해 `drafts`, `entries`, `transactions` 배열 필드는 유지한다.
- RN 이전 시 로컬 개발 토큰을 JWT 또는 PIN 인증으로 교체한다.
- RN 이전 시 최근 데이터 오프라인 캐시 전략을 적용한다.
- RN 분석 화면 차트는 `react-native-gifted-charts`를 사용한다.
- RN 분석 화면은 `1개월`, `3개월`, `6개월`, `1년`, `전체` 기간 필터를 제공한다.
- RN 분석 화면은 `월간`, `분기`, `연간` 수익 막대 차트 전환을 제공한다.
- RN 분석 화면은 `종목별`, `유형별`, `계좌별` 비중 도넛 차트 전환을 제공한다.
- RN 분석 화면은 배당, 세금, 수수료 막대 차트를 제공한다.
- RN 작성 완료 일지 화면은 목록 조회, 수정, 삭제를 제공한다.
- 타 증권사 CSV 가져오기는 `multipart/form-data` 기반 `POST /api/v1/manual-transactions/import.csv`로 구현했다.
- CSV 가져오기는 UTF-8, CP949, EUC-KR 인코딩을 지원한다.
- CSV 헤더는 한글과 영문 별칭을 모두 지원한다.
- 행별 검증 실패는 전체 실패가 아니라 실패 행 목록으로 반환한다.

API 경로 정리:

- 정식 분석 API는 `GET /api/v1/journal/analytics`이다.
- 기존 `GET /api/v1/analytics/journal`는 301 리다이렉트로만 유지한다.
- 프론트도 정식 경로를 우선 호출하도록 변경했다.

에러 응답 형식:

```json
{
  "success": false,
  "error": {
    "code": "HTTP_404",
    "message": "과거 거래 동기화 작업을 찾을 수 없습니다."
  }
}
```

- `AppError`, `HTTPException`, 요청 검증 오류, 미처리 서버 오류를 공통 JSON 구조로 반환한다.
- 프론트는 `error.message`를 우선 표시한다.

위험 삭제 API 보완:

- `DELETE /api/v1/sync/kiwoom/history/records`는 첫 요청에서 삭제 대상 카운트를 반환한다.
- `confirm=true`가 있을 때만 실제 삭제 처리를 수행한다.
- 실제 삭제는 물리 삭제가 아니라 `deleted_at`을 기록하는 소프트 삭제다.
- 작성 완료 매매일지는 계속 보존한다.

중복 방지:

- 키움 동기화 데이터와 수동 입력 거래는 거래 지문으로 비교한다.
- 거래 지문 기준은 거래일, 종목코드, 수량, 가격이다.
- 키움 원천 거래 지문은 `trade_dedup_keys`에 우선 등록된다.
- 같은 지문을 가진 수동 거래는 `duplicate_kiwoom` 상태로 저장하고 분석 합산에서 제외한다.
- 과거 거래 재실행은 안정적인 source key와 `UNIQUE(source_type, source_key)` 기반으로 upsert 처리한다.
- 기존처럼 삭제 후 재실행도 가능하지만, 삭제 없이 재실행해도 같은 원천 거래는 덮어쓰는 방향이다.

## 6. 로컬 DB 및 저장 데이터

SQLite 기반 로컬 DB를 사용한다.

동시성 보완:

- SQLite WAL(Write-Ahead Logging) 모드를 기본 활성화한다.
- `busy_timeout`을 설정해 짧은 쓰기 락 때문에 즉시 실패하지 않도록 한다.
- 과거 거래 대량 쓰기 중 분석 화면 조회가 어느 정도 동시에 가능하도록 한다.
- 로컬 개발 단계의 완화책이며, 클라우드/운영 배포 시에는 PostgreSQL 전환을 권장한다.

백업 보완:

- 서버 시작 시 최근 백업이 없거나 백업 주기가 지났으면 SQLite hot backup을 생성한다.
- 단순 파일 복사가 아니라 `sqlite3.Connection.backup()` API를 사용한다.
- 기본 백업 위치는 `backend\backups`이다.
- 기본 보관 기간은 30일이며 오래된 백업은 자동 삭제한다.
- 수동 백업 API와 백업 목록 API를 추가했다.
- 백업 파일에도 접근 권한 제한을 적용한다.

관련 API:

- `GET /api/v1/admin/backups`
- `POST /api/v1/admin/backups`

관련 환경 변수:

```env
DB_BACKUP_ON_STARTUP=true
DB_BACKUP_DIR=backups
DB_BACKUP_RETENTION_DAYS=30
DB_BACKUP_INTERVAL_HOURS=168
```

백그라운드 작업 복구:

- 과거 거래 불러오기 작업은 `history_sync_jobs`에 진행 상태를 저장한다.
- 서버 재시작 시 startup 단계에서 `running`, `cancel_requested` 작업을 `paused`로 전환한다.
- `paused` 작업은 `next_date`를 보존하므로 같은 기간으로 다시 시작하면 이어받을 수 있다.
- 저장되는 재개 정보는 현재 처리일, 마지막 성공일, 다음 재개일, 마지막 API 페이지, 마지막 페이지 커서, 재시도 횟수, 마지막 백오프 대기 시간이다.
- 날짜 내부 페이지 진행상태는 `last_page_api_id`, `last_page_no`, `last_cursor`로 저장한다.
- 페이지 체크포인트는 키움 `ka10170`, `kt00007` 페이지 조회 중 갱신된다.
- 일시정지된 작업은 실제 실행 중인 프로세스가 없으므로 기록 삭제도 가능하다.
- 기록 삭제는 소프트 삭제 방식이며, 삭제된 동기화/초안/작업 이력은 일반 조회에서 제외된다.

관련 설정:

```env
SQLITE_ENABLE_WAL=true
SQLITE_BUSY_TIMEOUT_MS=30000
SQLITE_SYNCHRONOUS=NORMAL
SQLITE_RESTRICT_FILE_PERMISSIONS=true
SQLITE_ENCRYPTION_KEY=
```

파일 보안 보완:

- DB, WAL, SHM 파일 권한을 소유자 중심으로 제한한다.
- Windows에서는 `icacls`로 현재 사용자 권한 중심 ACL을 적용한다.
- Unix 계열에서는 `0600` 권한을 적용한다.
- `SQLITE_ENCRYPTION_KEY`는 SQLCipher 지원 드라이버가 준비된 환경에서만 활성화한다.
- 기본 Python `sqlite3`처럼 암호화를 지원하지 않는 드라이버에서 키가 설정되면 서버 시작을 실패시켜 평문 저장 착각을 막는다.

키움 API Rate Limit 완화:

```env
HISTORY_SYNC_RATE_LIMIT_SECONDS=2.0
HISTORY_SYNC_REQUEST_DELAY_SECONDS=2.0
HISTORY_SYNC_BACKOFF_INITIAL_SECONDS=2.0
HISTORY_SYNC_BACKOFF_MAX_SECONDS=60.0
HISTORY_SYNC_BACKOFF_MULTIPLIER=2.0
KIWOOM_PAGE_DELAY_SECONDS=0.4
```

- 날짜별 과거 조회 사이 최소 2초를 둔다.
- 같은 날짜 안에서도 매매 요약 조회와 체결 상세 조회 사이 2초를 둔다.
- 실패 시 지수 백오프로 재시도한다.
- 증권사 또는 중간 서버가 `Retry-After` 헤더를 주면 지수 백오프보다 긴 값을 우선 적용한다.
- 작업 중 멈춤 요청이 들어오면 대기 중에도 취소 상태를 확인한다.

주요 저장 대상:

- 동기화 실행 이력
- 포트폴리오 스냅샷
- 매매일지 초안
- 작성 완료 매매일지
- 과거 거래 불러오기 작업 상태
- 과거 거래 원천 기록
- 수동 입력 거래내역

수동 입력 거래 테이블에는 다음 항목을 저장할 수 있다.

- 거래일
- 증권사
- 계좌명
- 거래 유형
- 종목코드
- 종목명
- 수량
- 가격
- 매수금액
- 매도금액
- 매매손익
- 배당
- 세금
- 수수료
- 통화
- 환율
- 액면분할/주식분할 보정비율
- 보정 수량
- 보정 단가
- 권리락/분할 메모
- 메모

## 7. 프론트 화면 구성

현재 미리보기 앱은 5개 탭으로 구성되어 있다.

- 포트폴리오
- 동기화
- 일지 초안
- 수동입력
- 분석

### 포트폴리오

보유종목, 평가금액, 손익 등 포트폴리오 정보를 표시한다.

### 동기화

키움 데이터 동기화와 과거 거래 불러오기를 담당한다.

반영된 기능:

- 일반 동기화
- 과거 거래 불러오기
- 연도 단위 기간 선택
- 직접 기간 선택
- 진행 상태 표시
- 불러오기 중단 버튼
- 불러오기 기록 삭제
- 대기 초안 수 동기화

### 일지 초안

자동 생성된 매매일지 초안을 보여준다.

초안 목록 상세 정보는 일관된 형식으로 정리했다.

- 일자
- 원천
- 상태
- 수량
- 가격
- 금액/시간
- 종목정보
- 복기 대기 상태

체크리스트 복기 항목은 사용자 요청에 따라 제거했다.

### 수동입력

타 증권사 거래내역을 직접 입력할 수 있는 화면이다.

입력 가능 항목:

- 거래일
- 증권사
- 계좌
- 유형
- 종목코드
- 종목명
- 수량
- 가격
- 매수금액
- 매도금액
- 매매손익
- 배당
- 세금
- 수수료
- 통화
- 환율
- 분할 보정비율
- 권리락/분할 메모
- 메모

저장된 수동 거래는 분석 데이터에도 포함된다.

### 분석

기존 분석 항목 중 사용성이 낮은 항목은 정리하고, 투자자가 자주 보는 항목 중심으로 재구성했다.

포함된 분석:

- 핵심 성과
- 손익 요약
- 연간 수익
- 분기 수익
- 월간 수익
- 수익 추이
- 종목별 비중
- 유형별 비중
- 계좌별 비중
- 배당
- 세금
- 전략 성과
- 종목별 거래
- 베스트/워스트 거래
- 연속 손익
- 일지 현황

추가된 그래프:

- 연간/분기/월간 수익 막대 그래프
- 누적 손익 라인 그래프
- 종목별/유형별/계좌별 비중 도넛 그래프
- 배당/세금 연도별 막대 그래프

웹 미리보기는 기존 SVG 기반 경량 차트를 유지하고, React Native 모바일 앱은 `react-native-gifted-charts`로 차트 구현을 고정했다.

시각화 유지보수 방침:

- SVG에는 원본 거래 row를 직접 넘기지 않고 백엔드 집계 결과만 넘긴다.
- 웹 미리보기는 `CHART_LIMITS`로 막대 12개, 추이 24점, 도넛 6개 세그먼트로 렌더링 점 수를 제한한다.
- React Native 앱에서는 직접 SVG 헬퍼를 확장하지 않고 `react-native-gifted-charts`를 사용한다.
- RN 분석 화면은 `BarChart`, `LineChart`, `PieChart`를 사용한다.
- 월간 수익은 막대 차트, 누적 손익 추이는 라인 차트, 종목별 비중은 도넛 차트로 표시한다.
- Expo 의존성은 `react-native-gifted-charts`, `expo-linear-gradient`, `react-native-svg` 조합으로 관리한다.
- 향후 툴팁, 터치 상호작용, 애니메이션, 모바일 반응형 처리는 라이브러리 props 중심으로 확장한다.

프론트 파일 동기화:

- 개발 원본은 `mobile_app\web_preview\index.html`이다.
- `mobile_app\dist\index.html`은 직접 편집하지 않고 `scripts\sync-web-preview-to-dist.ps1`로 생성한다.
- 배포 전에는 `scripts\verify-web-dist-sync.ps1`로 두 파일의 SHA-256 해시를 비교한다.

React Native 이전 준비:

- `apps\mobile`에 Expo/React Native 앱 골격을 추가했다.
- `App.tsx`에서 TanStack Query Provider를 구성했다.
- `src\api\client.ts`에서 백엔드 API 기본 URL, 인증 헤더, 공통 에러 처리를 담당한다.
- `src\hooks\useInvestmentQueries.ts`에서 포트폴리오, 일지 초안, 수동 입력, 분석 Query 훅을 제공한다.
- `src\hooks\useInvestmentQueries.ts`에서 수동 거래 저장/삭제 mutation과 관련 Query 자동 갱신을 제공한다.
- `src\hooks\useInvestmentQueries.ts`에서 일지 초안 작성 완료 mutation과 관련 Query 자동 갱신을 제공한다.
- `src\hooks\useInvestmentQueries.ts`에서 작성 완료 일지 목록 조회/삭제와 관련 Query 자동 갱신을 제공한다.
- `src\screens\AppShell.tsx`에서 포트폴리오, 일지 초안, 수동입력, 분석 탭형 화면 골격을 제공한다.
- `src\screens\AppShell.tsx`의 일지 초안 탭에 초안 선택, 복기 입력, 작성 완료 버튼을 추가했다.
- `src\screens\AppShell.tsx`의 작성 완료 일지 탭에 목록, 수정 폼, 삭제 버튼을 추가했다.
- `src\screens\AppShell.tsx`의 수동입력 탭에 거래 저장 폼과 삭제 버튼을 추가했다.
- `src\screens\AppShell.tsx`의 분석 탭에 `react-native-gifted-charts` 기반 막대/라인/도넛 차트를 추가했다.
- 분석 탭의 기간 필터는 선택 기간을 `start_date`, `end_date` 쿼리로 백엔드에 전달한다.
- 분석 탭의 수익 막대 차트는 월간/분기/연간 기준을 전환한다.
- 분석 탭의 비중 도넛 차트는 종목별/유형별/계좌별 기준을 전환한다.
- 분석 탭에는 배당, 세금, 수수료 차트를 추가했다.
- 모바일 앱에는 증권사 API 키나 외부 데이터 API 키를 저장하지 않는다.
- 실제 휴대폰 테스트 시 `EXPO_PUBLIC_API_BASE_URL`은 개발 PC 내부 IP와 8010 포트로 설정한다.

## 8. 과거 거래 불러오기

사용자 요청에 따라 과거 거래 불러오기 UX를 단순화했다.

반영 내용:

- 버튼 문구를 `과거 거래 불러오기`로 단순화
- 연도 단위 빠른 선택 제공
- 직접 기간 선택 제공
- 불러오기 작업을 백그라운드 작업으로 실행
- 진행 상태 조회
- 작업 중단
- 기록 삭제
- 초안 목록 초기화/동기화 관련 문제 수정

주의:

- 증권사 API 정책상 한 번에 조회 가능한 기간에 제한이 있을 수 있다.
- 앱에서는 장기 조회를 연도 단위로 나누어 실행하는 방향으로 구성했다.

## 9. 분석 계산에 포함되는 데이터

분석은 작성 완료 일지와 수동 입력 거래를 함께 사용한다.

수익 계산에 반영되는 항목:

- 매매손익
- 배당
- 세금
- 수동 입력 거래의 손익

수동 입력 거래의 순손익 계산 방식:

```text
원통화 순손익 = 매매손익 + 배당 - 세금 - 수수료
KRW 순손익 = 원통화 순손익 * 적용 환율
```

금융 도메인 예외 처리:

- 원화 거래는 `fx_rate_krw=1`로 처리한다.
- 외화 거래는 입력 환율 또는 기준정보 테이블의 최근 환율을 사용해 KRW로 환산한다.
- 환율이 없는 외화 거래는 총손익 합산에서 제외하고 `환율 미적용` 건수로 표시한다.
- 액면분할/주식분할은 `split_adjustment_ratio`로 수량과 단가를 보정한다.
- 예: 5:1 분할이면 보정수량은 `수량 * 5`, 보정단가는 `가격 / 5`로 저장한다.
- 원천 입력 금액과 보정값을 함께 보존해 나중에 검증할 수 있게 했다.

추가된 기준정보 API:

- `POST /api/v1/reference/fx-rates`: 통화별 환율 저장
- `POST /api/v1/reference/corporate-actions`: 액면분할/주식분할 등 권리정보 저장

비중 분석 기준:

- 종목별
- 거래 유형별
- 계좌별

기간 분석 기준:

- 연간
- 분기
- 월간

## 10. 실행 방법

백엔드 실행:

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\start_backend.ps1
```

이 스크립트는 8000 포트에 남은 오래된 리스너를 먼저 종료한 뒤 8010 포트로 최신 백엔드를 실행한다.

프론트 접속:

```text
http://127.0.0.1:8082
```

브라우저에서 변경사항이 바로 보이지 않으면 `Ctrl + F5`로 강력 새로고침한다.

## 11. 포트 관련 이슈

현재 `8000` 포트에는 오래된 리스너가 남아 있어 사용하지 않는 것이 좋다.

확인된 상태:

- `8000`: 오래된 서버 응답 가능성이 있음
- `8010`: 최신 백엔드용 포트
- `8082`: 프론트 정적 미리보기 포트

`HTTP 404`가 발생했던 원인:

- 프론트는 최신 API를 호출했지만, `8000` 포트의 오래된 백엔드가 응답했다.
- 오래된 백엔드는 `manual-transactions` API를 모르기 때문에 404가 발생했다.

조치:

- 프론트의 API 주소를 `http://127.0.0.1:8010`으로 변경했다.
- 최신 백엔드는 `8010`에서 실행하도록 정리했다.
- `tools\start_backend.ps1`를 추가해 8000 포트 잔류 프로세스를 자동 종료하고 8010 포트로 최신 백엔드를 실행하도록 했다.

## 12. 주요 수정 파일

백엔드:

- `backend\main.py`
- `backend\app\application_models.py`
- `backend\app\backup.py`
- `backend\app\database.py`
- `backend\app\kiwoom_account.py`
- `backend\app\kiwoom_auth.py`
- `backend\app\kiwoom_balance.py`
- `backend\app\kiwoom_trade_journal.py`
- `backend\app\kiwoom_order_execution.py`

프론트:

- `mobile_app\web_preview\index.html`
- `mobile_app\dist\index.html`

모바일 앱:

- `apps\mobile\package.json`
- `apps\mobile\app.json`
- `apps\mobile\tsconfig.json`
- `apps\mobile\App.tsx`
- `apps\mobile\.env.example`
- `apps\mobile\src\api\client.ts`
- `apps\mobile\src\api\types.ts`
- `apps\mobile\src\hooks\useInvestmentQueries.ts`
- `apps\mobile\src\queryClient.ts`
- `apps\mobile\src\screens\AppShell.tsx`

실행 스크립트:

- `tools\start_backend.ps1`

문서:

- `CODEX_WORKING_RULES.md`
- `README.md`
- `docs\investment_journal_work_summary_2026-05-16.md`

## 13. 현재 운영 규칙

사용자 요청에 따라 작업 위치는 다음 경로를 기준으로 한다.

```text
C:\Users\lib20\InvestmentJournalApp
```

원드라이브 경로에서는 작업하지 않는다.

폴더 정책은 `docs\folder-policy.md`를 기준으로 한다.
폴더 정리 결과는 `docs\folder_cleanup_2026-05-17.md`에 기록했다.

작업 전 루트 확인:

```powershell
.\tools\assert_project_root.ps1 -PassThru
```

정리 후보 확인:

```powershell
.\tools\list_cleanup_candidates.ps1
```

임시/백업 폴더 삭제는 후보 확인 후 별도 확인을 거쳐 진행한다.

## 14. 다음 단계 제안

우선순위 높은 다음 작업:

- 실제 수동 입력 데이터를 넣고 분석 그래프 표시 확인
- 키움 과거 거래 불러오기 장기 실행 실데이터 점검
- React Native 모바일 앱에서 작성/삭제/CSV 업로드 mutation 이전
- React Native 분석 화면에서 `react-native-gifted-charts` 차트의 실기기 렌더링 확인
- API 응답/에러 메시지 한글화 정리
- 분석 화면 기간 필터 추가
- 환율 공급처를 확정해 자동 환율 적재 작업 추가
- 액면분할/배당락 기준정보 자동 수집처 확정

## 15. 검증한 내용

확인한 검증 항목:

- 백엔드 Python 컴파일 통과
- FastAPI 주요 라우트 응답 확인
- 분석 API 경로 응답 확인
- 수동 입력 API 응답 확인
- 외화 수동 거래의 KRW 환산 분석 확인
- 환율 없는 외화 거래가 합산에서 제외되고 미적용 건수로 잡히는지 확인
- 분할 보정비율 입력 시 보정 건수와 보정 수량/단가 저장 확인
- 키움 원천 거래와 같은 지문을 가진 수동 거래가 분석에서 중복 제외되는지 확인
- 수수료가 순손익에서 차감되는지 확인
- 서버 재시작 상황을 가정해 running 작업이 paused로 전환되고 next_date가 보존되는지 확인
- paused 작업이 같은 기간 재실행 시 이어받기 후보로 잡히는지 확인
- 페이지 체크포인트가 `last_page_api_id`, `last_page_no`, `last_cursor`에 저장되고 날짜 성공 후 초기화되는지 확인
- `Retry-After` 헤더가 백오프 대기 시간에 반영되는지 확인
- 레거시 분석 API가 301로 정식 분석 API에 리다이렉트되는지 확인
- 에러 응답이 `success=false`, `error.code`, `error.message` 구조로 반환되는지 확인
- 기록 삭제 API가 confirm 전에는 카운트만 반환하고 confirm 후에는 소프트 삭제하는지 확인
- SQLite hot backup 생성 및 오래된 백업 삭제 확인
- 수동 백업 API와 백업 목록 API 응답 확인
- 목록 API 페이지네이션 메타데이터 응답 확인
- `tools\start_backend.ps1` PowerShell 문법 확인
- 수동 입력 CSV multipart 업로드 API 응답 확인
- CSV 가져오기 후 수동 입력 목록 total 증가 확인
- 수동입력 탭 CSV 가져오기 UI 추가 확인
- Expo 모바일 앱 설정 JSON 검증
- Expo 모바일 앱 API 클라이언트와 TanStack Query 훅 파일 추가 확인
- Expo 모바일 앱 의존성 설치 확인
- Expo 모바일 앱 TypeScript 타입체크 통과
- Expo public config에서 SDK 55 설정 확인
- 모바일 앱 운영 의존성 기준 npm audit 취약점 0건 확인
- `react-native-gifted-charts` 설치 및 RN 분석 탭 import/사용 위치 확인
- RN 분석 탭 막대/라인/도넛 차트 타입체크 통과
- RN 분석 탭 수익/비중 기준 전환 타입체크 통과
- RN 분석 탭 배당/세금/수수료 차트 타입체크 통과
- RN 수동입력 저장/삭제 mutation 타입체크 통과
- 수동 입력 `POST /api/v1/manual-transactions`, 목록 조회, `DELETE /api/v1/manual-transactions/{transaction_id}` 라우트 검증
- RN 일지 초안 작성 완료 mutation 타입체크 통과
- 일지 작성 `POST /api/v1/journal/entries` 라우트, 초안 completed 전환, 분석 손익 반영 검증
- RN 작성 완료 일지 목록/수정/삭제 타입체크 통과
- 작성 완료 일지 목록 조회, 수정 upsert, 삭제 후 초안 needs_review 복귀 검증
- 분석 API 선택 기간 필터가 집계 결과를 줄이는지 직접 DB 함수 검증
- 분석 API `start_date`, `end_date` 라우트 응답 및 역전 기간 400 응답 확인
- Expo export는 현재 로컬 환경의 `127.0.0.1:9` 연결 거부로 완료하지 못했다. 앱 코드 타입체크는 통과했으며, 실제 렌더링은 Expo Go 또는 에뮬레이터에서 확인해야 한다.
- `web_preview`와 `dist` 동기화 스크립트 및 해시 검증 스크립트 확인
- SVG 차트가 원본 거래 row가 아니라 집계 결과와 제한된 점 수만 렌더링하는지 확인
- 프론트 스크립트 문법 확인
- 프론트 정적 파일에 최신 코드 반영 확인
- 그래프 렌더링 함수 포함 확인
- 프론트 API 주소가 `8010`으로 설정된 것 확인

민감정보는 검증 출력과 문서에 포함하지 않았다.
