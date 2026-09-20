# DART 공시 일일 감시

보유종목과 관심종목에 포함된 한국 6자리 종목코드는 DART 신규 공시 감시 대상입니다. 백엔드가 실행 중이고 `DART_API_KEY`가 설정되어 있으면 스케줄러가 주기적으로 OpenDART `list.json`을 조회하고 신규 공시를 저장 데이터/RAG에 보관합니다.

## 기본 동작

- 대상: 저장 포트폴리오 보유종목 + 관심종목 중 한국 6자리 코드
- 제외: 해외 티커, ETF/비한국 코드, 현금
- 기본 주기: `DART_FILING_REFRESH_HOURS=6`
- 기본 조회 범위: `DART_FILING_LOOKBACK_DAYS=45`
- 저장 유형: `dart-filing-watch`
- 중요 공시: `사업보고서`, `반기보고서`, `분기보고서`, `주요사항보고서`, 지분/임원/최대주주, 증권신고서/유상증자/전환사채

45일 조회 범위는 로컬 서버가 며칠 꺼져 있었거나 휴일/공휴일 뒤에 켜진 경우에도 최근 분기보고서와 실적 관련 공시를 다시 잡기 위한 안전장치입니다.

## 상태 확인

```text
GET /api/v1/dart/filings/status
```

확인할 항목:

- `enabled`: DART 자동 감시가 켜져 있고 API 키가 있는지
- `target_universe.portfolio_tickers`: 보유종목 중 감시 대상
- `target_universe.interest_tickers`: 관심종목 중 감시 대상
- `daily_check.due`: 오늘 전체 대상 점검이 아직 필요한지
- `daily_check.missing_tickers`: 오늘 점검 기록에 빠진 대상
- `recent_entries`: 최근 저장된 신규 공시
- `last_failures`: 종목별 조회 실패

## 수동 갱신

```text
POST /api/v1/dart/filings/refresh
```

요청 예:

```json
{
  "force": false,
  "save_result": true
}
```

특정 종목만 강제 확인하려면:

```json
{
  "tickers": ["003230", "071050"],
  "force": true,
  "save_result": true
}
```

## 운영 주의

- `DART_API_KEY`가 비어 있으면 감시는 `skipped`로 표시되고 저장되지 않습니다.
- `daily_check.due=true`가 계속 유지되면 백엔드가 꺼져 있거나 DART 키/네트워크 문제가 있을 가능성이 큽니다.
- 신규 공시는 중복 접수번호(`rcept_no`) 기준으로 중복 저장을 막습니다.

## 사업보고서 분석 랩

리서치 콘솔의 `사업보고서 랩`은 기존 공시 감시를 대체하지 않고, 최종 사업보고서(A001)만 별도 관측하는 운영 화면입니다.

```text
GET  /api/v1/dart/annual-report-lab/status
POST /api/v1/dart/annual-report-lab/refresh
POST /api/v1/dart/annual-report-lab/governance/refresh
```

- OpenDART `list.json`에 `pblntf_detail_ty=A001`, `last_reprt_at=Y`를 적용합니다.
- 가족 보유·관심 한국 종목을 커서 방식으로 하루 12개씩 순환 확인합니다.
- 공식 안내 기준 20,000건의 75%인 15,000건에서 로컬 수집을 선제 중단합니다. 환경값이 더 높아도 실행 시 75%로 강제 제한됩니다.
- HTTP 상태와 DART 본문 `status`를 따로 기록하므로 HTTP 200 응답의 DART 오류도 실패로 보입니다.
- 요청 URL, 요청 파라미터, 인증키는 관측 원장에 저장하지 않습니다. SQLite 본체와 WAL/SHM도 정책 검사 대상입니다.
- 최근 30일 동안 실행 기록이 없는 날은 `NO RUN`으로 명시합니다.
- 백엔드 재기동 시 같은 날 완료된 전체 DART 점검과 스케줄 주기 안의 실적 일정 캐시는 다시 조회하지 않습니다.
- 전체 `corpCode.xml`은 24시간 캐시하며, 캐시에 없는 ETF·비상장 코드도 같은 기간 음성 캐시로 처리해 화면 조회마다 전체 목록을 다시 받지 않습니다.
- 지배구조·주주·보수는 최신 사업연도 사업보고서(`11011`)를 기준으로 최대 2개 종목씩 순환합니다. 최대주주/변동, 임원, 직원, 주식총수, 배당, 이사·감사 보수 API를 확인하고 원문 응답 대신 정규화된 공개 사실·content hash만 보관합니다.
- 사업의 내용 원문 diff와 불리언 스크리닝은 후속 마일스톤이며 현재 화면은 이를 활성 기능으로 오인시키지 않습니다.

일일 운영에서는 `tools/run_daily_research_operations.ps1`의 기존 단일 작업 안에서 A001 색인 뒤 지배구조 스냅샷을 실행합니다. 별도 스케줄을 추가하지 않아 중복 호출과 쿼터 낭비를 막습니다.
