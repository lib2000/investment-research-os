# Investment Journal App

개인 투자자를 위한 모바일 주식 매매일지 및 투자 분석 앱 설계 초안입니다.

현재 범위는 모바일 앱과 증권사 OpenAPI를 안전하게 연결하기 위한 초기 서버 아키텍처, API 계약, 보안 원칙, 백엔드/모바일 통신 보일러플레이트입니다.

## 현재 구조

```text
InvestmentJournalApp/
  apps/
    research-console/        # 장기 React 웹 콘솔 이관 대상
    mobile/                  # 장기 Expo 모바일 앱 이관 대상
  backend/
    app/
      brokerage.py
      models.py
      security.py
      settings.py
    research_os/
      data_providers.py
      research_memory.py
      rag_memory.py
    research_os_main.py
    main.py
    requirements.txt
  docs/
    architecture.md
    long-term-architecture.md
    kiwoom-integration.md
  mobile_app/
    research_console/
      index.html
      console.js
      api.js
    api.js
  research_vault/
  scripts/
```

현재 운영 콘솔은 `mobile_app\research_console`입니다. `apps\research-console`은 장기 React 전환 대상이며, 기존 화면을 깨지 않기 위한 이관 공간입니다.

장기 구조와 이관 기준은 [docs/long-term-architecture.md](docs/long-term-architecture.md)를 기준으로 합니다.

폴더 정책은 [docs/folder-policy.md](docs/folder-policy.md)를 기준으로 한다. 활성 프로젝트 루트는 `C:\Users\lib20\InvestmentJournalApp`이며, OneDrive 경로에서는 서버 실행, 코드 수정, 생성 파일 저장을 하지 않는다.

최근 폴더 정리 결과는 [docs/folder_cleanup_2026-05-17.md](docs/folder_cleanup_2026-05-17.md)에 기록했다.

작업 전 루트 확인:

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\assert_project_root.ps1 -PassThru
```

## Research OS 백엔드 실행

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\scripts\start-research-backend.ps1
```

API 문서:

```text
http://127.0.0.1:8001/docs
```

## 리서치 콘솔 실행

백엔드와 별도 터미널에서 실행합니다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\scripts\open-research-console.ps1
```

브라우저:

```text
http://127.0.0.1:5500/index.html
```

## 모바일 앱 실행

Expo/React Native 이관용 모바일 앱은 `apps\mobile`에 있다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp\apps\mobile
Copy-Item .env.example .env
npm install
npm run start
```

실제 휴대폰의 Expo Go에서 테스트할 때는 `apps\mobile\.env`의 `EXPO_PUBLIC_API_BASE_URL`을 `http://<PC의_내부_IP>:8010` 형식으로 바꿔야 합니다. Android 에뮬레이터는 보통 `http://10.0.2.2:8010`을 사용합니다.

기존 정적 웹 미리보기는 `mobile_app\web_preview\index.html`에 유지한다.

## 투자일지 백엔드 실행

최신 투자일지 API 백엔드는 8010 포트를 사용한다. 아래 스크립트는 오래된 8000 포트 잔류 프로세스를 먼저 정리한 뒤 최신 백엔드를 실행한다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\start_backend.ps1
```

잔류 프로세스 정리 없이 실행해야 하는 특수 상황에서는 다음 옵션을 사용한다.

```powershell
.\tools\start_backend.ps1 -SkipLegacyPortCleanup
```

## 현재 결정 사항

- 첫 연동 증권사: 키움증권
- 후속 연동 증권사: 한국투자증권
- 인증 권장안: Supabase Auth 또는 동등한 JWT 기반 인증, 백엔드 검증 필수
- 데이터베이스 권장안: 로컬 개발은 SQLite WAL 모드, 클라우드/운영 배포는 PostgreSQL
- ORB 기본값: 5분 Opening Range, 사용자 설정으로 변경 가능

키움 연동 세부 설계는 [docs/kiwoom-integration.md](docs/kiwoom-integration.md)를 기준으로 진행합니다.

키움 APP KEY 관리 화면에서는 먼저 현재 개발 PC의 공인 IP를 등록해야 합니다. 운영 배포 시에는 로컬 PC IP가 아니라 서버의 고정 outbound IP를 등록해야 합니다.

발급받은 키는 채팅이나 코드에 붙이지 말고 `backend\.env`에만 넣으세요. 토큰 발급 확인은 `/api/v1/brokerage/kiwoom/token-test`에서 마스킹된 응답으로 확인합니다.

계좌번호 조회 확인은 `/api/v1/brokerage/kiwoom/accounts-test`에서 마스킹된 계좌번호로 확인합니다.

계좌번호는 원문을 저장하지 않는다. 표시가 필요한 경우에는 `1234****90` 형식의 마스킹 값만 사용하고, 식별/중복 제거가 필요한 경우에는 `SECRET_SALT` 기반 SHA-256 해시 앞 16자리만 사용한다.

잔고/보유종목 조회 확인은 `/api/v1/brokerage/kiwoom/balance-test`에서 정규화된 `summary`와 `holdings`로 확인합니다.

당일 매매일지 조회 확인은 `/api/v1/brokerage/kiwoom/trade-journal-test`에서 정규화된 `summary`와 `items`로 확인합니다.

주문/체결 상세 조회 확인은 `/api/v1/brokerage/kiwoom/order-executions-test`에서 정규화된 `executions`로 확인합니다.

모바일 앱 화면용 API:

- `GET /api/v1/portfolio`: 현재 포트폴리오 요약과 보유종목
- `GET /api/v1/journal/source-trades`: 매매일지 자동 생성을 위한 당일 매매 요약과 주문/체결 상세
- `POST /api/v1/sync/kiwoom`: 키움 데이터를 조회하고 로컬 DB에 동기화
- `GET /api/v1/sync/latest`: 최근 동기화 상태
- `GET /api/v1/journal/drafts`: 복기가 필요한 매매일지 초안 목록

### API 설계 규칙

정식 분석 API는 `GET /api/v1/journal/analytics`로 고정한다. 예전 경로인 `GET /api/v1/analytics/journal`는 호환을 위해 301 리다이렉트만 제공한다.

분석 API는 선택 기간 필터를 지원한다.

```text
GET /api/v1/journal/analytics?start_date=2026-01-01&end_date=2026-12-31
```

### React Native 이전 준비

모바일 화면은 네트워크 지연, 작은 화면, 백그라운드 전환, 오프라인 상태를 전제로 설계한다.

현재 반영한 모바일 API 계약:

- 목록 API는 `page`, `page_size` 쿼리 파라미터를 받는다.
- 응답에는 기존 배열 필드와 함께 `total`, `page`, `page_size`, `total_pages`, `has_next`, `has_previous`를 포함한다.
- 기존 웹 미리보기 호환을 위해 `drafts`, `entries`, `transactions` 필드는 유지한다.

페이지네이션 적용 API:

- `GET /api/v1/journal/drafts?page=1&page_size=50`
- `GET /api/v1/journal/entries?page=1&page_size=50`
- `GET /api/v1/manual-transactions?page=1&page_size=100`
- `POST /api/v1/manual-transactions/import.csv`

RN 이전 시 추가 구현할 항목:

- 인증: 로컬 개발용 `DEV_USER_TOKEN` 대신 JWT 또는 앱 PIN 기반 잠금 화면을 추가한다.
- 오프라인: 최근 포트폴리오, 일지 초안, 분석 요약은 기기 로컬 캐시에 저장하고, 서버 응답 `updated_at` 기준으로 갱신한다.
- 에러 메시지: 서버 응답은 `success=false`, `error.code`, `error.message` 구조와 한국어 메시지로 통일한다.
- CSV 업로드: 타 증권사 거래내역 가져오기는 `multipart/form-data` 기반 `POST /api/v1/manual-transactions/import.csv`를 사용한다.
- 목록 UX: RN에서는 `has_next=true`일 때 다음 페이지를 요청하는 무한스크롤 또는 더보기 버튼을 사용한다.
- 차트: 분석 화면은 `react-native-gifted-charts`의 `BarChart`, `LineChart`, `PieChart`를 사용한다.
- 분석 기간: RN 분석 화면은 `1개월`, `3개월`, `6개월`, `1년`, `전체` 필터를 제공한다.
- 수익 기준: RN 분석 화면은 `월간`, `분기`, `연간` 수익 막대 차트 전환을 제공한다.
- 비중 기준: RN 분석 화면은 `종목별`, `유형별`, `계좌별` 도넛 차트 전환을 제공한다.
- 비용/부가수익: RN 분석 화면은 배당, 세금, 수수료 막대 차트를 제공한다.

모바일 앱 골격:

- `apps/mobile/App.tsx`: TanStack Query Provider와 앱 셸
- `apps/mobile/src/api/client.ts`: 백엔드 API 클라이언트와 공통 에러 처리
- `apps/mobile/src/hooks/useInvestmentQueries.ts`: 포트폴리오, 일지 초안, 수동입력, 분석 Query 훅
- `apps/mobile/src/hooks/useInvestmentQueries.ts`: 수동 거래 저장/삭제 mutation과 관련 Query 자동 갱신
- `apps/mobile/src/hooks/useInvestmentQueries.ts`: 일지 초안 작성 완료 mutation과 관련 Query 자동 갱신
- `apps/mobile/src/hooks/useInvestmentQueries.ts`: 작성 완료 일지 목록 조회/삭제와 관련 Query 자동 갱신
- `apps/mobile/src/screens/AppShell.tsx`: 모바일 탭형 화면 골격, 일지 작성/수정 폼, 수동입력 폼, 분석 차트

CSV 가져오기 지원 컬럼:

- `거래일`, `증권사`, `계좌`, `유형`, `종목코드`, `종목명`
- `수량`, `가격`, `매수금액`, `매도금액`, `매매손익`
- `배당`, `세금`, `수수료`, `통화`, `환율`
- `분할보정비율`, `보정메모`, `메모`

React Native 일지 초안 화면:

- 초안을 선택하고 전략, 셋업 태그, 진입/청산 근거, 원칙 준수 여부, 복기 메모를 입력한다.
- `일지 작성 완료` 저장 후 `journal-drafts`와 `journal-analytics` Query를 다시 불러온다.
- 저장된 초안은 백엔드에서 `completed` 상태로 전환되고 분석 손익에 반영된다.

React Native 작성 완료 일지 화면:

- 작성 완료 일지 목록을 조회한다.
- 기존 일지를 선택해 전략, 태그, 근거, 원칙 준수 여부, 손익, 메모를 수정한다.
- 일지를 삭제하면 백엔드에서 연결된 초안이 다시 `needs_review` 상태로 돌아간다.
- 수정/삭제 후 `journal-entries`, `journal-drafts`, `journal-analytics` Query를 다시 불러온다.

에러 응답은 다음 형태로 통일한다.

```json
{
  "success": false,
  "error": {
    "code": "HTTP_404",
    "message": "과거 거래 동기화 작업을 찾을 수 없습니다."
  }
}
```

`DELETE /api/v1/sync/kiwoom/history/records`는 즉시 삭제하지 않는다. 먼저 삭제 대상 카운트를 반환하고, `confirm=true`가 붙은 두 번째 요청에서 `deleted_at`을 기록하는 소프트 삭제를 수행한다.

### 데이터 정합성 정책

키움 원천 데이터와 수동 입력이 같은 거래를 가리키면 분석 수치가 중복 계산될 수 있으므로 거래 지문을 저장한다.

거래 지문 기준:

- 거래일
- 종목코드
- 수량
- 가격

키움 동기화 데이터는 `trade_dedup_keys`에 우선 등록된다. 수동 입력 거래가 같은 지문을 가지면 `dedup_status=duplicate_kiwoom`으로 저장하고 분석 합산에서는 제외한다. 과거 거래 재실행은 `journal_drafts`의 `UNIQUE(source_type, source_key)`와 안정적인 source key, dedup key 등록을 통해 기본적으로 upsert 방식으로 동작한다.

### SQLite 동시성 설정

로컬 개발 DB는 SQLite를 사용하며, 과거 거래 대량 동기화 중 분석 화면 조회가 막히지 않도록 WAL(Write-Ahead Logging) 모드를 기본 활성화한다.

관련 환경 변수:

- `SQLITE_ENABLE_WAL=true`
- `SQLITE_BUSY_TIMEOUT_MS=30000`
- `SQLITE_SYNCHRONOUS=NORMAL`
- `SQLITE_RESTRICT_FILE_PERMISSIONS=true`
- `SQLITE_ENCRYPTION_KEY=` optional, SQLCipher 지원 드라이버가 있을 때만 사용

DB 파일은 생성/접속 시 소유자 읽기/쓰기 권한으로 제한한다. Windows에서는 `icacls`를 이용해 현재 사용자 권한 중심으로 ACL을 제한하고, Unix 계열에서는 `0600` 권한을 적용한다.

`SQLITE_ENCRYPTION_KEY`를 설정하면 백엔드는 SQLCipher 지원 여부를 확인한다. 현재 Python 기본 `sqlite3` 드라이버는 SQLCipher를 지원하지 않으므로, 키가 설정됐는데 암호화 드라이버가 아니면 서버 시작을 실패시켜 “암호화된 줄 알고 평문 저장”되는 상태를 막는다.

SQLite는 단일 사용자 로컬 개발에는 충분하지만, 모바일 앱 백엔드를 클라우드로 배포하거나 다중 사용자를 지원할 때는 PostgreSQL과 KMS/Secret Manager 기반 저장소로 이전하는 것을 전제로 한다.

### SQLite 백업 설정

투자 데이터가 단일 SQLite 파일에 집중되므로 백엔드 시작 시 SQLite hot backup을 수행한다. 백업은 DB를 단순 파일 복사하지 않고 `sqlite3.Connection.backup()` API로 생성해 WAL 사용 중에도 안전하게 복제한다.

관련 환경 변수:

- `DB_BACKUP_ON_STARTUP=true`
- `DB_BACKUP_DIR=backups`
- `DB_BACKUP_RETENTION_DAYS=30`
- `DB_BACKUP_INTERVAL_HOURS=168`

동작 방식:

- 서버 시작 시 최근 백업이 없거나 `DB_BACKUP_INTERVAL_HOURS`가 지나면 백업을 생성한다.
- `DB_BACKUP_RETENTION_DAYS`보다 오래된 백업 파일은 자동 삭제한다.
- 백업 파일도 DB 파일과 동일하게 접근 권한 제한을 적용한다.
- 수동 백업은 `POST /api/v1/admin/backups`, 백업 목록 확인은 `GET /api/v1/admin/backups`를 사용한다.

### 백그라운드 작업 안정성

과거 거래 불러오기는 `history_sync_jobs`에 진행 상태를 저장한다.

저장되는 상태:

- `current_date`: 현재 처리 중인 날짜
- `last_success_date`: 마지막 성공 날짜
- `next_date`: 이어받을 날짜
- `last_page_api_id`: 현재 날짜 안에서 마지막으로 처리한 키움 API ID
- `last_page_no`: 현재 날짜 안에서 마지막으로 처리한 페이지 번호
- `last_cursor`: 현재 날짜 안에서 마지막으로 받은 페이지 커서
- `retry_count`: 현재 날짜 재시도 횟수
- `last_backoff_seconds`: 마지막 백오프 대기 시간
- `resume_from_job_id`: 이어받은 원본 작업 ID

서버가 재시작되면 startup 단계에서 `running` 또는 `cancel_requested` 작업을 `paused`로 전환한다. 같은 기간으로 다시 과거 거래 불러오기를 시작하면 `next_date`부터 이어받는다.

키움 API 호출은 보수적으로 제한한다.

- `HISTORY_SYNC_RATE_LIMIT_SECONDS=2.0`: 날짜별 조회 사이 최소 대기
- `HISTORY_SYNC_REQUEST_DELAY_SECONDS=2.0`: 매매 요약 조회와 체결 상세 조회 사이 대기
- `HISTORY_SYNC_BACKOFF_*`: 실패 시 지수 백오프
- `KIWOOM_PAGE_DELAY_SECONDS=0.4`: 페이지네이션이 있는 API의 페이지 간 대기
- 증권사 또는 중간 서버가 `Retry-After` 헤더를 반환하면 지수 백오프보다 긴 값을 우선 적용한다.

현재 재개 단위는 날짜 단위이며, 페이지 체크포인트는 장애 분석과 안전한 재시도 판단을 위해 저장한다. 페이지 단위 재개가 필요한 수준으로 데이터가 커지면 `last_cursor`를 시작 커서로 사용하는 전용 worker로 확장한다.

### 증권사 토큰 자동 갱신

백엔드는 증권사 접근 토큰을 매 요청마다 새로 발급하지 않고 DB에 캐시한다.

기본 동작:

- 토큰이 유효하면 캐시된 access token을 재사용한다.
- 만료 예정 시간이 `TOKEN_EXPIRY_BUFFER_SECONDS` 이내로 들어오면 자동 재발급한다.
- 키움 REST API는 현재 접근토큰 발급 응답에 refresh token을 제공하지 않는 구조이므로 기본값은 `client_credentials` 재발급이다.
- refresh token을 제공하는 증권사나 향후 키움 정책 변경에 대비해 `KIWOOM_ALLOW_REFRESH_TOKEN` 옵션과 저장 컬럼을 준비해 두었다.
- API 응답과 로그에는 토큰 원문을 반환하지 않고 마스킹 값만 사용한다.

관련 환경 변수:

- `TOKEN_EXPIRY_BUFFER_SECONDS=300`
- `KIWOOM_ALLOW_REFRESH_TOKEN=false`

운영 배포 시에는 DB 평문 저장 대신 클라우드 Secret Manager 또는 KMS 기반 암호화 저장소로 이전하는 것이 좋다.

### 금융 도메인 보정

해외 주식과 국내 주식을 함께 분석할 때 원통화 금액을 그대로 합산하면 총손익이 왜곡된다. 수동 입력 거래는 원천 통화 금액을 보존하고, 분석 합산에는 KRW 환산값만 사용한다.

반영된 항목:

- 수동 입력 거래의 `currency`, `fx_rate_krw` 저장
- `fx_rates` 기준정보 테이블과 `POST /api/v1/reference/fx-rates`
- 환율이 없는 외화 거래는 총손익 합산에서 제외하고 분석 화면에 `환율 미적용` 건수로 표시
- 수동 입력 거래의 `commission_amount` 저장 및 순손익 계산 시 차감
- `split_adjustment_ratio`, `adjusted_quantity`, `adjusted_price`, `adjustment_note` 저장
- `corporate_actions` 기준정보 테이블과 `POST /api/v1/reference/corporate-actions`
- 분석 응답의 `currency_breakdown`, `fx_unconverted_count`, `corporate_action_adjusted_count`

순손익 계산은 `매매손익 + 배당 - 세금 - 수수료`를 기본으로 한다. 평가손익은 포트폴리오 화면에서 별도 표시하며, 실현손익 분석에는 확정 거래 손익만 넣는다.

액면분할/주식분할은 보정비율을 입력해 현재 기준 수량과 단가를 함께 남긴다. 예를 들어 5:1 분할이면 `split_adjustment_ratio=5`로 저장하고, 분석 화면에서는 분할 보정 건수와 보정 수량/단가를 확인한다.

### 차트 시각화 유지보수 방침

현재 `mobile_app/web_preview/index.html`의 분석 차트는 외부 의존성 없이 동작하는 미리보기용 SVG 구현이다. 초기 검증에는 가볍지만, 툴팁, 드래그 줌, 모바일 터치 이벤트, 접근성, 애니메이션을 직접 구현하기 시작하면 유지보수 비용이 빠르게 커진다.

현재 SVG에는 원본 거래 row를 직접 넘기지 않는다. 백엔드가 만든 연간/분기/월간/비중/추이 집계 결과만 넘기고, 프론트에서도 `CHART_LIMITS`로 렌더링 점 수를 제한한다.

React Native 화면은 직접 SVG 헬퍼를 확장하지 않고 `react-native-gifted-charts`를 사용한다.

적용 범위:

- `BarChart`: 월간/연간/분기 수익
- `LineChart`: 누적 손익 추이
- `PieChart`: 종목별/유형별/계좌별 비중

Expo 의존성은 `react-native-gifted-charts`, `expo-linear-gradient`, `react-native-svg` 조합으로 관리한다. 향후 모바일 터치 툴팁, 애니메이션, 기간 선택 상호작용은 라이브러리 props 중심으로 확장한다.

실기기 확인 체크포인트:

- Expo Go에서 분석 탭 진입 시 차트가 빈 화면 없이 표시되는지 확인한다.
- `1개월`, `3개월`, `6개월`, `1년`, `전체` 필터를 눌렀을 때 데이터가 다시 불러와지는지 확인한다.
- `월간`, `분기`, `연간` 수익 기준 전환 시 막대 차트 라벨이 잘리지 않는지 확인한다.
- `종목별`, `유형별`, `계좌별` 비중 기준 전환 시 도넛 차트와 범례가 겹치지 않는지 확인한다.
- 배당/세금/수수료 데이터가 없을 때 빈 상태 문구가 자연스럽게 표시되는지 확인한다.

### 프론트 정적 파일 동기화

개발 원본은 `mobile_app/web_preview/index.html` 하나로 본다. `mobile_app/dist/index.html`은 수동 편집하지 않고 스크립트로 동기화한다.

```powershell
.\scripts\sync-web-preview-to-dist.ps1
.\scripts\verify-web-dist-sync.ps1
```

배포 전에는 `verify-web-dist-sync.ps1`로 두 파일의 SHA-256 해시가 같은지 확인한다.
- `POST /api/v1/journal/entries`: 매매일지 작성/수정
- `GET /api/v1/journal/entries`: 작성된 매매일지 목록
- `GET /api/v1/journal/analytics`: 분석 화면 데이터
- `GET /api/v1/analytics/journal`: legacy redirect
