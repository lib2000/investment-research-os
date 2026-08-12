# 토스증권 Open API 읽기 전용 연동

상태: 구현됨 (읽기 전용)

공식 문서: [토스증권 Open API 가이드](https://developers.tossinvest.com/docs)

## 범위

- OAuth 2.0 Client Credentials 토큰 발급
- `GET /api/v1/accounts` 계좌 목록 확인
- `GET /api/v1/holdings` 국내·미국 보유자산 확인
- 포트폴리오 화면에서 미리보기 후 사용자가 적용

주문 생성·정정·취소와 조건주문 API는 호출하지 않는다. 토스 원격 보유자산에만 있는 신규 종목도 자동 추가하지 않고 별도 `untracked_remote` 목록으로 표시한다.

## 설정

실제 값은 `backend/.env`에만 둔다.

```dotenv
TOSS_ENABLED=false
TOSS_CLIENT_ID=
TOSS_CLIENT_SECRET=
TOSS_ACCOUNT_SEQ=
TOSS_TOKEN_CACHE_FILE=../research_vault/_system/toss_access_token.json
```

`TOSS_ACCOUNT_SEQ`가 비어 있으면 계좌 목록에서 첫 `BROKERAGE` 계좌를 선택한다. 토큰 캐시는 `research_vault/_system` 아래에 저장되며 Git에 포함되지 않는다.

## API 경로

- `POST /api/v1/brokerage/toss/token-test`
- `GET /api/v1/brokerage/toss/accounts`
- `GET /api/v1/brokerage/toss/holdings`
- `GET /api/v1/brokerage/toss/orders?query_date=YYYY-MM-DD&status=ALL`
- `POST /api/v1/portfolios/{portfolio_name}/sync/toss/preview`
- `POST /api/v1/portfolios/{portfolio_name}/sync/toss`
- `GET /api/v1/brokerage/toss/workflow/status`
- `POST /api/v1/brokerage/toss/workflow/run`
- `POST /api/v1/brokerage/toss/workflow/paper-simulate?confirm=true`
- `GET /api/v1/brokerage/toss/workflow/paper-evaluation?days=7`

모든 포트폴리오 동기화는 기존 저장 종목과 티커가 일치하는 항목만 갱신한다. 미리보기는 저장하지 않으며, 적용 버튼을 눌렀을 때만 `portfolio_sync_history.jsonl`에 이력을 남긴다.

## 뉴스→조건→거래 기록→복기 워크플로

`TOSS_WORKFLOW_ENABLED=true`이면 매일 설정된 시각(기본 16:10 KST)에 뉴스 인박스와 보유·관심 종목을 대조해 조건 일치 주문안을 만들고, 같은 날짜의 토스 주문 이력을 기록·복기한다. 종목 코드가 뉴스에 없어도 검증된 회사명, 영문 법인명(예: `Planet Labs PBC` → `Planet Labs`)과 저장 별칭을 정규화해 매칭하며, 각 결과에 `matched_entities` 근거를 남긴다. 관심종목의 부정 신호는 보유 수량이 없으므로 매도 주문안으로 만들지 않고 `WATCH`로 남긴다. 주문안에는 수량과 가격을 자동 확정하지 않으며 `manual_review_required`와 `blocked_live_order` 상태로 저장한다.

현재 단계에서는 주문 생성·정정·취소 API를 호출하지 않는다. 자동화가 실행되어도 실계좌에 주문이 제출되지 않으며, 실제 매매를 연결하려면 별도의 위험 한도·승인·모의검증 설계가 선행되어야 한다.

`TOSS_PAPER_TRADING_ENABLED=true`일 때만 콘솔의 `모의체결 기록`이 활성화된다. 명시적 확인 요청 후 기존 주문안에 대해 1주·참고가격 기준의 결정적 모의체결을 저장하며, 토스 API에는 쓰기 요청을 보내지 않는다.

워크플로는 주문안에 포함된 보유·관심 종목에 한해 읽기 전용 시장 데이터 제공자에서 가격 스냅샷을 수집한다. 저장된 현재가가 있으면 이를 우선 사용하고, 없을 때만 KIS 등 읽기 전용 가격 경로를 조회한다. 스냅샷은 워크플로 기준일과 `price_source`를 함께 기록하며, 예약 워크플로는 장 종료 후 실행하는 운영 일정에 맞춰 하루 한 번 저장한다. 실거래 설정과 별개이며 `TOSS_LIVE_TRADING_ENABLED=false` 상태에서는 토스 주문 쓰기 API가 호출되지 않는다.

콘솔의 `7일 모의평가`는 누적된 모의체결을 기준으로 종목별 손익, 수익률, 승률, 최대낙폭, 표본 수와 근거 강도를 계산한다. 관측일 또는 표본이 부족하면 `insufficient_sample`로 표시하며, 결과는 실계좌 성과나 투자 권고로 해석하지 않는다.

## 검증

- 공식 응답 스키마 정규화: `tests/test_toss_invest.py`
- 토큰 캐시·마스킹: `tests/test_toss_invest.py`
- 미매칭 기존 종목 보존·원격 신규 종목 보고: `tests/test_toss_invest.py`
