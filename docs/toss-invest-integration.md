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
- `POST /api/v1/portfolios/{portfolio_name}/sync/toss/preview`
- `POST /api/v1/portfolios/{portfolio_name}/sync/toss`

모든 포트폴리오 동기화는 기존 저장 종목과 티커가 일치하는 항목만 갱신한다. 미리보기는 저장하지 않으며, 적용 버튼을 눌렀을 때만 `portfolio_sync_history.jsonl`에 이력을 남긴다.

## 검증

- 공식 응답 스키마 정규화: `tests/test_toss_invest.py`
- 토큰 캐시·마스킹: `tests/test_toss_invest.py`
- 미매칭 기존 종목 보존·원격 신규 종목 보고: `tests/test_toss_invest.py`
