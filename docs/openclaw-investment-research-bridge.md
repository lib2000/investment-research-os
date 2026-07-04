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
- `research_vault/_system/openclaw_integration/openclaw_bridge_manifest.json`

OpenClaw 워크스페이스 동기화 위치:

- `%USERPROFILE%/.openclaw/workspace/data/investment_research/investment_research_context.json`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/investment_research_context.md`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/openclaw_bridge_manifest.json`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/bridge_status.json`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/openclaw_bridge_completion_report.json`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/openclaw_bridge_completion_report.md`
- `%USERPROFILE%/.openclaw/workspace/data/investment_research/README.md`

`openclaw_bridge_manifest.json`은 OpenClaw 자동화가 읽을 수 있는 파일 지도다. 컨텍스트 파일명, Markdown 파일명, 상태 파일명, 첫 읽기 순서(`read_order`), 완료 리포트 Markdown/JSON 파일명, 안전 갱신 명령, 최종 엄격 갱신 명령, 검증 명령, 완료 감사 명령, 최종 완료 해시 감사 명령, 전체 오프라인 준비도 명령, 민감정보 제외 범위를 포함한다.

`bridge_status.json`은 OpenClaw가 가장 먼저 읽는 런타임 상태 파일이다. 첫 읽기 순서, 원본 커밋/브랜치/dirty 상태, 컨텍스트 생성 시각, 최신성 기준 시간, 최신 추천일, 한국/미국 추천 수, 텔레그램 반영 수, 민감정보 제외 확인, 완료 리포트 경로, 시작 안내 갱신 여부, 운영 명령 묶음, 핵심 파일 SHA256, 완료 리포트 SHA256을 포함한다. `README.md`에도 컨텍스트 생성 시각, 최신 추천일, 시장별 추천 수, 텔레그램 반영 수를 요약해 둔다.

OpenClaw 시작 노트(`MEMORY.md`, `HEARTBEAT.md`)에는 최신 source git 브랜치/커밋과 최종 완료 해시 감사 명령이 함께 기록된다. 완료 감사는 이 시작 노트가 현재 `bridge_status.json`의 source git과 같은 커밋을 가리키는지도 확인한다.

## 갱신

OpenClaw까지 동기화:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1
```

최종 완료용 엄격 동기화:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit
```

Investment Research OS 내부 번들만 생성:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -SkipCopy
```

## 검증

```powershell
python tools\check_openclaw_investment_context.py --max-age-hours 1
```

최종 완료 감사:

```powershell
python tools\check_openclaw_bridge_completion.py --max-age-hours 1 --write-report
```

완료 리포트 해시까지 필수로 확인하는 최종 감사:

```powershell
python tools\check_openclaw_bridge_completion.py --max-age-hours 1 --require-report-hashes
```

검증 항목:

- JSON/Markdown 번들 존재 여부
- OpenClaw 브리지 매니페스트 존재 여부와 스키마/파일 지도 일치 여부
- OpenClaw 브리지 매니페스트와 `bridge_status.json`의 `read_order` 일치 여부
- `bridge_status.json`의 복사 상태, 생성 시각, 민감정보 제외 확인 여부
- `bridge_status.json`의 최신성 기준 시간과 완료 감사의 `--max-age-hours` 기준 일치 여부
- `bridge_status.json`의 완료 리포트 경로, 시작 안내 갱신 여부, 운영 명령이 매니페스트 명령과 일치하는지 여부
- `bridge_status.json`의 운영 명령에 전체 오프라인 준비도 명령이 포함되는지 여부
- `bridge_status.json`의 핵심 파일 SHA256이 실제 JSON/Markdown/manifest 파일과 일치하는지 여부
- `bridge_status.json`의 완료 리포트 SHA256이 실제 완료 리포트 파일과 일치하는지 여부
- 원본 Git 브랜치가 `main`이고 upstream과 동기화되어 있으며 작업트리가 clean인지 여부
- `bridge_status.json`의 원본 커밋/브랜치/dirty 상태가 현재 Git 상태와 일치하는지 여부
- OpenClaw 시작 노트가 현재 source git 커밋과 최종 완료 해시 감사 명령을 포함하는지 여부
- `openclaw_bridge_completion_report.md/json`에 최종 감사 결과가 저장되고 매니페스트가 두 파일명을 모두 노출하는지 여부
- 최신 추천 한국 3개, 미국 3개 포함 여부
- 텔레그램 인기글 반영 여부
- 국민연금 컨텍스트가 공개자료 기반으로 표시되는지 여부
- Firecrawl 안전 기본값 `enabled=false`, `dry_run=true` 유지 여부
- 토큰/시크릿 형태의 민감정보가 포함되지 않았는지 여부

## OpenClaw 사용 규칙

- OpenClaw는 먼저 `data/investment_research/bridge_status.json`과 `data/investment_research/openclaw_bridge_manifest.json`을 읽어 최신성, 파일명, 갱신 명령, 완료 리포트 Markdown/JSON 위치를 확인한다.
- 사람이 읽을 요약은 `data/investment_research/investment_research_context.md`를 사용한다.
- 더 구조적인 처리가 필요하면 `data/investment_research/investment_research_context.json`을 읽는다.
- 전체 운영 준비도는 원본 프로젝트에서 `python tools\check_offline_readiness.py --json`을 실행해 확인한다.
- 원본 상세 판단은 Investment Research OS 콘솔에서 확인한다.
- 실거래 주문, 계좌 인증, API 키 요청에는 이 번들을 사용하지 않는다.
