# OpenClaw Investment Research Bridge

Investment Research OS 상태를 OpenClaw가 읽을 수 있도록 민감정보를 제외한 요약 번들로 내보낸다.

## 목적

- OpenClaw가 최신 한국/미국 추천 1~3위, 관심종목, 포트폴리오, 텔레그램 인기글, 국민연금 공개자료 모니터, Firecrawl 상태를 읽을 수 있게 한다.
- 브로커 인증 정보, API 키, 토큰, 원문 DB, 계좌 원문 데이터는 넘기지 않는다.
- 실거래 판단이나 주문 실행이 아니라 투자 판단 보조 컨텍스트로만 사용한다.

## 생성 파일

Investment Research OS 내부 생성 위치:

- `research_vault/_system/openclaw_integration/investment_research_context.json`
- `research_vault/_system/openclaw_integration/investment_research_context.md`

OpenClaw 워크스페이스 동기화 위치:

- `%USERPROFILE%/.openclaw/workspace/data/investment_research/investment_research_context.json`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/investment_research_context.md`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/README.md`

## 갱신

OpenClaw까지 동기화:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1
```

Investment Research OS 내부 번들만 생성:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -SkipCopy
```

## 검증

```powershell
python tools\check_openclaw_investment_context.py --max-age-hours 1
```

검증 항목:

- JSON/Markdown 번들 존재 여부
- 최신 추천 한국 3개, 미국 3개 포함 여부
- 텔레그램 인기글 반영 여부
- 국민연금 컨텍스트가 공개자료 기반으로 표시되는지 여부
- Firecrawl 안전 기본값 `enabled=false`, `dry_run=true` 유지 여부
- 토큰/시크릿 형태의 민감정보가 포함되지 않았는지 여부

## OpenClaw 사용 규칙

- OpenClaw는 먼저 `data/investment_research/investment_research_context.md`를 읽는다.
- 더 구조적인 처리가 필요하면 `data/investment_research/investment_research_context.json`을 읽는다.
- 원본 상세 판단은 Investment Research OS 콘솔에서 확인한다.
- 실거래 주문, 계좌 인증, API 키 요청에는 이 번들을 사용하지 않는다.
