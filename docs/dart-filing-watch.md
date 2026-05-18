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
