# 투자 리서치 OS 운영 점검 노트

최종 갱신: 2026-07-07

## 매일 한국/미국 추천 1~3위

- 확인 위치: 콘솔 대시보드의 `오늘 한국/미국 추천 1~3위`, 또는 저장 데이터 탭의 `오늘 한국/미국 추천 1~3위` / `추천 추적 상태`
- API 확인: `GET /api/v1/daily-recommendations/status`
- 실행 시각: `DAILY_RECOMMENDATIONS_TIME` 기본값 `08:00`
- 저장 위치: `research_vault/_system/daily_recommendations.json`
- 스케줄 상태 위치: `research_vault/_system/daily_recommendations_state.json`
- 저장 항목: 추천일, 순위, 회사명, 기준가, 통화, 점수 구성, 감점/확인 사유, 근거, 포트폴리오 연결, 사후 추적표
- 투자 방향 프로필: 사용자 첨부 투자 방향 테마는 오늘 추천 후보 점수, 리스크 메모, 모니터링 트리거에 반영되며 `투자 방향:` / `투자 방향 반영:` 라벨로 화면과 텍스트 출력에 표시된다.
- 화면 표시: 콘솔은 `오늘의 추천 결과`를 제목으로 보여주고, 추천 기록은 한국 1~3위와 미국 1~3위 시장별 목록으로 묶는다. 1주/15일/1달/3달/6달 경과는 요약 막대 그래프와 종목별 타임라인으로 같이 표시한다.
- 품질 가드: 활성 저장자료 중 중복 의심, 본문 보강 필요, OCR 필요, URL-only 정책 자료는 추천 근거에서 감점/확인 플래그로 분리하고, 검증된 저장자료가 충분한 후보만 품질 점수를 받는다.
- 최신성/이력 가드: 추천 저장 점검은 `Asia/Seoul` 날짜 기준으로 최신 추천일이 허용 범위 안에 있고, 해당 일자 추천이 정확히 3개인지 확인한다. 또한 저장된 전체 추천 이력도 날짜별 1·2·3위가 빠짐없이 있고 같은 날짜 안에 회사명/티커/순위가 중복되지 않는지 확인한다. 각 후보의 기준가 조회 시각이 24시간을 넘으면 추천 품질 점검에서 실패한다.
- 근거 분산 가드: 추천 후보별 근거가 `저장 품질`, `목표가/리포트`, `최근 저장/RAG`, `보유/관심 범위` 범주를 모두 포함하는지 오프라인 점검에서 확인한다. 저장 품질 대시보드 연결이 없는 후보도 `저장 품질:` 근거와 확인 플래그를 남겨 품질 공백을 숨기지 않는다. 한 범주에만 기대는 추천은 실패로 처리한다.
- 근거 문서 가드: 추천 기록은 `evidence_sources` 텍스트뿐 아니라 실제 RAG 저장 문서 경로를 담은 `evidence_documents`를 함께 보관한다. `python tools\check_daily_recommendation_citations.py --strict`로 모든 추천 기록의 대표 근거 문서가 실제 파일로 열리는지 확인한다.
- 추적 주기: 추천 후 1주일, 15일, 1달, 3달, 6달
- 추적 점검: 오프라인 가드는 각 마일스톤의 목표일이 추천일 기준 7/15/30/90/180일 뒤인지, 추적 완료 항목에 가격·확인시각·수익률이 있는지 확인한다.
- 해외 종목: 원통화 기준 수익률을 우선 저장하고, 화면에는 USD/KRW 환율 반영 필요 여부를 함께 표시한다.

- LLM/RAG 저장 상태: `python tools\check_llm_bridge_store.py --require-active-rag`로 LLM 연동 응답의 원 프롬프트, 응답 본문, Markdown/JSON 저장 파일, RAG 색인 연결을 백엔드 없이 확인한다.
- 로컬 AI 생존 모드: 고급 외부 AI 모델 접근이 리테일 레벨에서 제한되는 상황을 대비해 `python tools\check_local_ai_survival.py --json --strict`로 포트폴리오 저장소, 리서치 manifest, RAG 색인, 오늘 추천 저장/추적, 규칙 기반 분석 엔진, 수동/로컬 LLM 브리지, OpenClaw 로컬 컨텍스트 번들을 secret-free로 점검한다. OpenAI/DeepSeek 등 외부 모델은 필수 의존성이 아니라 보강 계층이며, 로컬 모델 endpoint가 없어도 규칙/RAG 기반 핵심 운영은 계속되어야 한다.
- 에이전트 운영 기반: 완성도 높은 에이전트 운영은 모델 성능만이 아니라 목표/맥락 패킷, 장기 기억/RAG, 도구 JSON 계약, 안전 기본값, 평가/회귀 게이트, 관측 가능성, 자동화 주기, 로컬 AI 생존성의 8개 축이 동시에 준비되어야 한다. `python tools\check_agent_operating_foundation.py --json --strict`는 이 기반을 secret-free로 점검하고, 콘솔 `에이전트 운영 기반` 버튼과 전체 시스템 점검에서도 같은 payload를 보여준다.
- 저장/RAG 실패 진단: `python tools\check_rag_failure_diagnostics.py --strict`로 활성 리서치 문서의 저장 파일, RAG 색인, 검색 가능 본문 길이, 자동 분류 근거를 한 번에 확인한다.
- 국민연금 국내주식 14%: 기본 운영 점검과 전체 오프라인 readiness는 현재 비중과 리밸런싱 후보를 출력한다. 초과/미달을 운영 게이트 실패로 막아야 할 때는 `python tools\check_operational_readiness_score.py --strict --min-score 95 --enforce-nps-allocation` 또는 `python tools\check_nps_domestic_equity_allocation.py --fail-on-breach`를 사용한다.
- 통합 투자 인사이트 허브: `python tools\check_investment_insight_hub.py --strict`는 저장된 포트폴리오, 시장일지/투자심리, DART 공시, 뉴스 인박스, 정책·법령·규제 자료를 합성해 투자 판단용 인사이트가 실제로 생성되는지 확인한다. 운영 완성도 점수와 전체 오프라인 readiness에 포함되어, 어느 한 소스 패밀리가 비면 실패로 처리한다.
- OpenClaw 브리지: `.\tools\run_daily_research_operations.ps1`의 기본 흐름은 리서치 중복/Dossier 상태를 갱신한 뒤 `.\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit`까지 실행한다. 이 단계는 `bridge_status.json`, `openclaw_first_read.md/json`, `openclaw_bridge_manifest.json`, `investment_research_context.md/json`, 지식 그래프 파일, `openclaw_bridge_completion_report.md/json`을 `%USERPROFILE%\.openclaw\workspace\data\investment_research`에 동기화한다. OpenClaw는 `bridge_status.json`으로 source git/해시/최신성을 확인하고, `openclaw_first_read.md/json`으로 오늘 추천 6개와 KR/US 3개씩의 compact 상태를 먼저 읽은 뒤 큰 컨텍스트로 넘어간다. 완료 감사는 source git이 `main`에서 원격과 동기화되어 있으며 작업트리가 clean인지, first-read packet이 컨텍스트와 일치하는지, 완료 리포트 SHA256이 실제 파일과 맞는지 확인한다. 빠른 상태 요약은 `python tools\show_openclaw_bridge_status.py --json`의 `hash_status=ok`, `hash_checked_count=14`, `hash_mismatches=[]`를 기준으로 보고, OpenClaw 전용 빠른 통합 점검은 `python tools\check_openclaw_quick_health.py --json`으로 `status_summary`, `context_bundle`, `completion_audit`, `consumer_smoke`를 한 번에 확인한다.

- UI 회귀 가드: `python tools\check_console_static_contract.py --strict`는 추천 결과 화면의 `오늘의 추천 결과`, `일자별 추천 목록`, `경과 그래프` 렌더링 계약과 관련 CSS 클래스를 확인한다.

2026-05-30 기준 최신 저장 상태는 `records` 배열에 일자별 3개 후보가 쌓이는 구조다. 브라우저 화면에서 한글이 정상인데 터미널 JSON만 깨져 보이면 PowerShell/WSL 출력 인코딩 문제일 수 있으므로, 콘솔 화면이나 Python 직접 파일 읽기로 UTF-8 원본을 확인한다.

## 소스 자동 수집 품질

- DART 공시: 공시번호와 종목 기준으로 중복을 제외하고, 보유/관심 종목 커버리지를 점검한다.
- 네이버 리서치/시장일지: 저작권 안전 정책에 맞춰 요약/메타데이터 중심으로 저장하고, URL·본문 해시·제목 유사도로 중복을 제외한다.
- KIEP/KCIF: 매크로 보고서 제목, 발행일, 링크, 요약 메타데이터를 시장일지와 리스크 메모에 연결한다.
- EMERiCs/CSF: 지역·중국·신흥국 자료를 제목/링크/발행기관/요약 기준으로 활용한다.
- 공개 IR/SEC: 공개 URL만 수집하고 로그인/전송/우회는 하지 않는다. 본문 추출이 가능한 SEC/IR 페이지, 표 형태 공시 목록, IR 실적발표 목록은 RAG와 최근 1주 자료에 연결한다. 본문 보강이 완료된 항목은 stale `needs_body_copy` 태그를 추천 품질 결함으로 보지 않고, 403/404 중복 범용 항목은 삭제하지 않고 소프트 보관한다. 오늘 추천 점수에는 본문 추출이 정상인 항목만 반영하고, 보강 필요 자료는 경고/다음 액션으로만 노출한다.
- Firecrawl IR Collector v1: Firecrawl MCP 또는 외부 수집 결과는 `firecrawl_ir_collector_v1` payload builder를 거쳐 `source_platform=firecrawl_ir`, URL SHA256 `external_id`, `canonical_hash`, `needs_enrichment=true`, `analysis_status=pending` 형식으로 Market Signal Graph `upsert_external_signal(payload jsonb)`에 전달한다. registry 필드뿐 아니라 Firecrawl scrape 응답의 `data.markdown`/`firecrawl.markdown`, `metadata.title`, `metadata.sourceURL` 같은 중첩 필드도 정규화한다. Hosted API 파일럿은 공식 v2 scrape 계약인 `POST https://api.firecrawl.dev/v2/scrape`, `Authorization: Bearer <token>`, `formats=["markdown"]`을 사용하며 `FIRECRAWL_API_KEY`, `FIRECRAWL_BASE_URL`, `FIRECRAWL_TIMEOUT_SECONDS`를 backend secret env에서만 읽는다. `--hosted-scrape-dry-run`은 첫 번째 IR URL 1건만 호출하고 RPC 저장 없이 정규화 payload를 검증하며 API key 원문은 출력하지 않는다. 로컬 preflight는 `source_platform/external_id` 중복을 우선 차단하고 `source_platform/canonical_hash` 중복을 fallback으로 차단한다. 기본 설정은 비활성/dry-run이며 `FIRECRAWL_IR_SOURCES_JSON`, `FIRECRAWL_IR_ENABLED=true`, `FIRECRAWL_IR_DRY_RUN=false`, `FIRECRAWL_IR_MCP_VERSION=3.17.0`, `MARKET_SIGNAL_GRAPH_ENABLED=true`, `MARKET_SIGNAL_GRAPH_RPC_URL` 또는 `MARKET_SIGNAL_GRAPH_SUPABASE_URL`/`SUPABASE_URL`, service role key가 모두 준비된 경우에만 RPC를 호출한다. `check_firecrawl_ir_collector.py`는 비밀값 없이 `rpc_submit_ready`, `rpc_readiness_errors`, MCP 고정 버전을 출력해 운영 전환 준비 상태를 보여주며 `FIRECRAWL_IR_MCP_VERSION`이 `3.17.0`이 아니면 실패한다. `docs\examples\firecrawl_ir_registry.sample.json` registry 샘플 검증은 full offline readiness에도 포함되어 운영 전 점검에서 샘플 입력 정규화 drift를 함께 잡는다. `--submit`은 실제 RPC/batch 상태를 최상위 `status`와 exit code에 반영해 `success`만 exit 0으로 끝나며, `skipped`/`failed`는 exit 1로 끝난다. batch 로그는 `batch_counts: success=N failed=N skipped=N dry_run=N` 형식으로 기록해 전부 생략된 적재를 성공으로 오인하지 않게 한다.
- Firecrawl Monitor v1: Firecrawl `/v2/monitor`는 페이지(`scrape`), 웹사이트(`crawl`), 웹 전체 검색(`search`) 대상에 스케줄, goal judge, changeTracking, webhook/email 알림을 붙이는 변화 감지 레이어다. Investment Research OS에서는 실전 생성 전에 `firecrawl_monitor_collector_v1`이 registry를 정규화하고 `FIRECRAWL_MONITOR_ENABLED=false`, `FIRECRAWL_MONITOR_DRY_RUN=true` 기본값으로 payload hash, target type, schedule, webhook 설정 여부만 노출한다. `scrape`/`crawl` target은 기본적으로 `formats=["markdown", {"type":"changeTracking","modes":["git-diff"]}]`, `onlyMainContent=true`, `removeBase64Images=true`, `blockAds=true`를 사용하고, structured field 감시는 registry에서 JSON mode schema/prompt를 추가한다. 실제 monitor 생성은 `FIRECRAWL_MONITOR_ENABLED=true`, `FIRECRAWL_MONITOR_DRY_RUN=false`, non-placeholder `FIRECRAWL_API_KEY`가 secret env에 있을 때만 허용하며, webhook 수신 운영 전에는 `tools\check_firecrawl_monitor_collector.py`와 콘솔 `Firecrawl Monitor Dry-run`으로 create readiness를 먼저 검토한다.
- Firecrawl Monitor 이벤트 저장: webhook 또는 수동 ingest 결과는 `firecrawl_monitor_events_v1`에서 `monitor.page`, `monitor.check.completed` 형태로 정규화한 뒤 `research_vault/_system/firecrawl_monitor_events.json`에 저장한다. 저장값은 긴 원문 복사가 아니라 URL, 상태, 짧은 diff 요약, goal judgment, route hint(`policy_news_inbox_candidate`, `public_ir_sec_candidate`, `market_journal_candidate`) 중심이며 공개 IR/SEC 상태 화면에서 최근 이벤트와 라우팅 후보 수를 함께 확인한다.
- Firecrawl Monitor webhook: 외부 수신 endpoint는 `POST /api/v1/public-ir-sec/firecrawl-monitor/webhook`이며 일반 사용자 토큰 대신 `FIRECRAWL_MONITOR_WEBHOOK_SECRET`과 `X-Firecrawl-Webhook-Secret`, `X-Webhook-Secret`, 또는 `Authorization: Bearer ...` 값을 상수 시간 비교한다. secret 미설정 또는 불일치 payload는 이벤트 저장소에 넣지 않고 `firecrawl_monitor_webhook_status.json`에 상태, 사유, 짧은 payload hash만 남긴다.
- Firecrawl Monitor 운영 preflight: 실전 전환 전에는 `python tools\check_firecrawl_monitor_operational_preflight.py --env-file path\to\firecrawl-monitor.env --env-override --require-env-registry --require-webhook-secret`를 먼저 실행한다. 이 검사는 secret과 registry를 확인하고, 임시 vault에서 webhook 불일치 401 및 정상 수신 200/저장 1건 흐름을 검증한다. 단, webhook secret 준비와 registry 안의 monitor webhook target 설정은 별개이므로 status/리포트의 `monitor_webhook_configured`와 `monitor_webhook_count`도 확인한다. 실제 monitor 생성 직전에는 추가로 `--require-create-ready`를 붙인다.
- Firecrawl Monitor 생성 readiness 리포트: `--readiness-report output\firecrawl_monitor_create_readiness_report.json`을 붙이면 실제 `/v2/monitor` 생성 없이 조건, 차단 사유, monitor별 target 수/type/schedule/webhook 여부/payload hash prefix, monitor webhook count만 저장한다. placeholder API key나 placeholder webhook secret은 configured로 보지 않는다.
- Firecrawl Monitor env/runbook: `python tools\create_firecrawl_monitor_env_template.py --output tmp\firecrawl-monitor.local.env`는 기존 파일을 덮어쓰지 않고 `enabled=false`, `dry_run=true`, placeholder secret/API key로 시작하는 로컬 env 템플릿만 만든다. 실전 전환 순서는 `docs\firecrawl-monitor-runbook.md`를 따른다.
- Firecrawl Earnings Collector v1: `firecrawl_earnings_collector_v1`은 earnings release, shareholder letter, earnings event page를 `source_platform=firecrawl_earnings`, `source_kind=earnings`, `target_type=company_earnings` payload로 정규화한다. call 전문은 `earnings_transcript_collector_v1`의 `source_platform=earnings_transcript`로 분리한다.
- DeepSeek IR Analysis contract: `deepseek_ir_analysis_contract_v1`은 수집된 IR signal과 LLM 분석 결과를 `source_platform=deepseek_ir_analysis`, `analysis_type=firecrawl_ir_signal_analysis_v2`의 `signal_analyses` payload로 정규화한다. offline check는 실제 DeepSeek API를 호출하지 않고 분석 ID, 원천 signal 연결, stance/score/confidence, key points/risks/catalysts shape만 검증한다.
- Portfolio Brief contract: `portfolio_brief_contract_v1`은 `signal_analyses`와 통합 점수 결과를 `brief_type=portfolio_ir`, `brief_type=portfolio_health`, `channel=portfolio`의 `public.briefs` payload로 정규화한다.
- OpenClaw Market Signal Graph 운영 라인: `/home/lib2000/market_signal_graph`의 `run_portfolio_ir_pipeline.sh`는 Firecrawl IR 수집, Firecrawl Earnings 수집, pending signal 조회, DeepSeek 분석, `signal_analyses` 저장, `portfolio_ir` brief, `portfolio_health` score brief까지 9단계로 실행된다. user systemd timer `portfolio-ir-pipeline.timer`는 매일 08:00 KST에 `run_portfolio_ir_pipeline_cron.sh`를 실행하며, secret은 `/home/lib2000/.openclaw/secrets/firecrawl.env`와 `/home/lib2000/.openclaw/secrets/deepseek.env`에서만 읽는다. Investment Research OS 쪽에서는 이 라인을 직접 복제하지 않고 `public.signals`, `public.signal_analyses`, `public.briefs`의 계약을 소비/검증 대상으로 본다.
- OpenClaw 수집/분석 계약: IR 입력은 `source_platform=firecrawl_ir`, earnings 입력은 `source_platform=firecrawl_earnings`, DeepSeek 분석은 `analysis_type=firecrawl_ir_signal_analysis_v2` 및 `source_platform=deepseek_ir_analysis`로 구분한다. 포트폴리오 brief 저장은 `brief_type=portfolio_ir`, health score 저장은 `brief_type=portfolio_health`, `channel=portfolio`를 사용한다. 현재 운영 기준 health score는 약 6.7이고 강화 종목은 `PL`, `JOBY`, `VRT`, `CHPT`, `ABSI`, 중립 종목은 `OPEN`, `OPTT`, `ADTN`, `RXRX`, `INTC`로 기록되어 있다.
- OpenClaw 다음 우선순위: `portfolio_change_detection_v1`은 전일 대비 stance/confidence/health score 변화를 추적하고, `telegram_brief_sender_v1`은 08:00 실행 후 `Investment Priority Brief` 1건만 텔레그램으로 보낸다. 메시지는 오늘 한국/미국 추천 1~3위, Portfolio Health, Top Movers, Watch Items만 포함하고 routine OK, dry-run 세부값, 해시/저장 경로, 빈 참고 섹션은 `priority_filter.mode=important_only`로 억제한다. `check_telegram_brief_sender.py`는 실제 전송 없이 `daily_recommendations.json` 최신 추천과 `--chat-id`, `MARKET_SIGNAL_GRAPH_TELEGRAM_CHAT_ID`, `TELEGRAM_CHAT_ID` 순의 chat id 설정 여부를 확인한다. 실제 Bot API 전달/정리는 `telegram_brief_delivery_v1`이 담당하며 기본값은 `TELEGRAM_BRIEF_DELIVERY_ENABLED=false`, `TELEGRAM_BRIEF_DELIVERY_DRY_RUN=true`, `TELEGRAM_BRIEF_CLEANUP_ENABLED=false`다. `check_telegram_brief_delivery.py --sample-state`는 중요 브리프 보호와 저우선순위 삭제 후보를 dry-run으로 검증하고, 실제 전송은 `--enabled --submit`, 실제 삭제는 거기에 `--cleanup-enabled`를 추가한 경우에만 허용한다. 이후 `earnings_transcript_collector_v1`, SEC/DART 통합 점수화를 붙여 IR+Earnings+SEC+DART 통합 Portfolio Score로 확장한다.
- OpenClaw 보유 종목 신규 리포트 알림: `portfolio_report_alert_v1`은 현재 포트폴리오 보유 티커만 대상으로 `research_vault\manifest.json`과 `research_vault\_system\company_ir_sources_watch.json`의 신규 report/filing/IR/earnings 항목을 선별해 매일 07:00 텔레그램 발송 payload를 만든다. 표시 대상은 `TELEGRAM_REPORT_ALERT_TARGET_BOT_USERNAME`으로 맞추며 기본값은 `@lib20_bot`이다. 공용 `TELEGRAM_BOT_TOKEN`이 다른 봇(예: `@my_claw_lib2000_bot`)을 가리키면 표시명도 함께 맞춰야 상태/콘솔 혼선을 피할 수 있다. 기본값은 `TELEGRAM_REPORT_ALERT_ENABLED=false`, `TELEGRAM_REPORT_ALERT_DRY_RUN=true`이며, 실제 전송은 `TELEGRAM_REPORT_ALERT_BOT_TOKEN` 또는 기존 `MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN`/`TELEGRAM_BOT_TOKEN`, 그리고 `TELEGRAM_REPORT_ALERT_CHAT_ID` 또는 기존 chat id가 준비된 상태에서 `--enabled --submit`을 붙였을 때만 허용한다. 발송 이력은 `research_vault\_system\portfolio_report_alert_state.json`에 report key로 남겨 같은 리포트 반복 발송을 막고, 텔레그램 cleanup 로직은 `Portfolio Report Alert` 메시지를 반드시 보호한다. Windows 예약 작업 등록은 `.\tools\register_openclaw_portfolio_report_alert_task.ps1`를 사용하며, live 전환 전에는 `python tools\check_portfolio_report_alert.py --json`으로 dry-run 결과를 먼저 확인한다. 등록 후에는 `python tools\check_portfolio_report_alert_task_status.py --json`으로 07:00 트리거, `-Enabled -Submit -WriteState` 인자, token/chat id 설정 여부, 대상 봇 표시명, 이전 state target bot과 현재 설정의 불일치 경고, 다음 실행 시각과 state 파일 freshness를 확인한다. 첫 실행 전에는 state 파일 미생성과 `LastRunTime=1999-11-30`이 경고로만 표시된다. 07:10 사후 모니터는 `.\tools\register_openclaw_portfolio_report_alert_postrun_task.ps1 -Enabled -Submit`으로 등록하며, `check_portfolio_report_alert_postrun.py`가 07:00 작업 결과와 state 파일 2시간 freshness를 확인한다. 이 사후점검은 `receipt`에 delivered 여부, target bot, message_id, state 갱신 시각을 secret-free로 남긴다. 정상일 때는 텔레그램을 보내지 않고, 실패하거나 state 갱신이 없을 때만 `Portfolio Report Alert Post-run Check` 운영 경고를 보낸다. 콘솔에서는 `GET /api/v1/telegram/portfolio-report-alert/status`와 `보유 리포트 알림 상태` 버튼으로 07:00/07:10 예약, 최신 후보/메시지 수, 사후점검 결과를 secret-free payload로 확인한다.
- Market Signal Graph pipeline contract: `market_signal_graph_pipeline_contract_v1`은 Firecrawl IR payload, Firecrawl earnings payload, earnings transcript payload, DeepSeek IR analysis payload, portfolio brief payload, IR/Earnings/SEC/DART 통합 점수, portfolio health 변화 감지, Telegram brief dry-run을 하나의 offline contract로 묶는다. 외부 RPC, Firecrawl, DeepSeek, Telegram 전송은 호출하지 않고 shape/count/status drift만 검증한다. source payload 중복은 `(source_platform, external_id)`를 우선 보고, fallback으로 `(source_platform, canonical_hash)`를 검사한다.
- 텔레그램 즐겨찾기 인기글 수집 v1은 기본값 `TELEGRAM_FAVORITE_POSTS_ENABLED=false`, 실행 시각 `TELEGRAM_FAVORITE_POSTS_TIME=22:00`이다. `TELEGRAM_FAVORITE_CHANNELS_JSON`에 공개 채널 목록을 명시하면 t.me/s 공개 preview의 제목, 링크, 조회수, 짧은 자체 메모만 뉴스 인박스에 `telegram_favorite` 태그로 반영한다.
- 텔레그램 인증 수집기 v1은 공개 preview가 `View in Telegram` 안내만 반환하거나 파일형/제한 채널이 누락될 때 쓰는 선택 fallback이다. 기본값은 `TELEGRAM_AUTHENTICATED_COLLECTION_ENABLED=false`, `TELEGRAM_AUTHENTICATED_COLLECTION_DRY_RUN=true`이며, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION_FILE`, `TELEGRAM_AUTHENTICATED_CHANNELS_JSON`이 모두 준비되고 선택 의존성 `telethon`이 설치된 경우에만 live 수집 준비 상태가 된다. API hash와 session 파일은 commit 금지이며, readiness/status 출력은 설정 여부와 파일명만 보여주고 원문 secret은 출력하지 않는다. 실제 계정 세션 수집은 `python tools\check_telegram_authenticated_collector.py --env-file path\to\telegram-auth.env --enabled --no-dry-run --collect --allow-live --json`처럼 명시적 live 허용 플래그를 함께 줘야 한다.
- 텔레그램 런타임 프로파일: `python tools\check_telegram_runtime_profile.py --json`은 중요 브리프, 보유 종목 리포트 07:00 알림, 07:10 사후점검, 인증 수집기 readiness를 secret-free로 한 번에 보여준다. Bot token/chat id/API hash/session 원문은 출력하지 않고, 설정 여부, 선택된 env source, 대상 봇, 예약작업 live submit 여부, 최신 message id/receipt만 보여준다. 일반 즐겨찾기/중요 브리프/보유 리포트 알림은 운영 채널이고, 인증 수집기는 optional fallback이므로 `not_ready`여도 전체 readiness를 막지 않지만 warnings에 남긴다.
- 백엔드가 꺼진 상태에서는 `python tools\check_research_source_store.py --strict`로 KCIF, EMERiCs/CSF/KIEP, 네이버 리서치, 신한 리서치, 마감 시황 시장일지, 티커 레지스트리, 중복 Dossier 큐 캐시 상태를 먼저 확인한다. 이 점검은 마감 시황 자동 수집 시도 상태, 리서치 자동화 Dossier 갱신 상태, 시장일지 `KR`/`US` 각각의 저장 항목·자동 출처 항목·최신 세션일 경과도 함께 확인하며, 네이버 리서치 저장경로 누락은 기본 허용 0건으로 본다.
- KCIF와 EMERiCs/CSF/KIEP 자료의 투자 연결 신호는 `python tools\check_macro_source_signal_linkage.py --strict`로 확인한다. 이 점검은 `matched_themes`, `target_matches`, `recommended_action`, KCIF 상세 신호 분석의 저작권 안전 플래그가 채워져 있는지 확인해, 시장일지/보유종목 리스크 메모에 연결 가능한 상태인지 본다.
- 뉴스 인박스 우선 분류는 `python tools\check_news_inbox_priority_queue.py --strict`로 확인한다. 이 점검은 `research_vault\_system\news_inbox.json`에서 미승격 우선 뉴스, 정책·법령·규제 우선 뉴스, 타깃 매칭 뉴스, 품질 확인 건수를 출력하고, 상위 우선 뉴스의 제목·URL·scope가 운영 화면에 표시 가능한 상태인지 확인한다. 같은 보도자료가 날짜/페이지 조회 파라미터만 달리 들어온 경우 `우선 중복 후보`로 묶어 보여준다. 우선 뉴스가 남아 있다는 이유만으로 실패하지 않고, 운영자가 바로 확인할 수 없는 깨진 항목만 실패로 처리한다.
- 저장 자료 중복 리뷰는 `python tools\check_storage_duplicate_review.py --strict`로 확인한다. 이 점검은 `storage_duplicate_review.json`의 대표 자료 수, 중복 그룹/항목 수, `representative_only` / `excluded_from_dossier` / hard delete 금지 정책, 대표·중복 파일 경로 존재 여부를 확인한다. 중복 의심 자료가 남아 있다는 이유만으로 실패하지 않고, Dossier 합성에서 대표 자료만 쓰는 안전 정책이 깨졌을 때 실패한다.
- 네이버 리서치 캐시에 메타데이터와 PDF 링크는 있으나 저장경로만 비어 있으면 삭제하지 않고 `repair_naver_research_cache(..., save_result=True)` 경로로 Markdown/JSON 저장을 보강한다. 복구 후 `python tools\check_research_source_store.py --strict`에서 `저장경로 누락 0개`, `파일 누락 0개`가 나와야 한다.
- 중복 Dossier 큐 갱신은 `dossier_refresh_queue_status.json`뿐 아니라 `research_automation_status.json`의 상위 `updated_at`과 `last_deduped_dossier_refresh.updated_at`도 함께 갱신해야 한다. 소스 자동화 점검은 저장 성공, 실패 0건, RAG 연결, 뉴스 미승격 0건까지 같이 확인한다.
- 네이버/신한 리서치 캐시는 제목·발행일·링크·요약·저장 경로가 모두 있어야 정상이며, 저장 경로의 Markdown/JSON 파일이 실제로 존재해야 한다. 네이버 캐시는 `시황정보` 항목이 있어야 시장일지 자동 활용 흐름을 통과한다.

## 포트폴리오 연결

- 추천 후보가 보유 종목이면 포트폴리오 리스크 스캔 우선 확인 대상으로 표시한다.
- 해외주식과 수동 관리 수량은 키움 국내 잔고 동기화가 덮어쓰지 않아야 한다.
- 이형주 포트폴리오의 `PL` 100주 보존은 회귀 검증의 기준 사례다.
- 백엔드가 꺼진 상태에서는 `python tools\check_portfolio_store.py --portfolio 이형주 --min-holdings 17 --expected-holdings-count 17 --forbid-zero`로 저장 원본 수량을 먼저 확인한다.
- 전체 포트폴리오 공통 구조는 `python tools\check_all_portfolio_store.py --min-holdings 1 --forbid-zero`로 함께 확인한다. 이 점검은 모든 저장 포트폴리오에서 수량 0 종목, 예수금 혼입, 중복 티커, 보유 종목 수 불일치, 총액 불일치, 해외 통화 보유 종목의 `manual_or_overseas_protected` 수량 보호 누락을 잡고, 24시간을 넘긴 포트폴리오는 갱신 권고로 표시한다.
- 오프라인 포트폴리오 가드는 `updated_at`, 가격 확인 시각, 해외/수동 수량 `sync_checked_at`, 비중 합계, 저장 총액과 종목 평가금액 합계까지 함께 확인한다. 묶음 점검은 가격 확인과 포트폴리오 갱신 시각이 24시간을 넘으면 실패시켜 실시간 연동 지연을 조기에 잡는다. 종목별로 평가금액, 투자금, 수익, 수익률 계산도 재검산하며 해외 종목은 평가/투자금에 적용된 환율이 서로 크게 어긋나지 않는지 확인한다.
- 보유 종목 수 가드: 이형주 포트폴리오는 정상 기준 17개를 정확히 확인해 다른 포트폴리오 종목이 섞여 화면이 넘치는 회귀를 잡는다.

## 검증 명령

백엔드가 꺼져 있거나 Windows 실행 브리지가 불안정하면 먼저 아래 파일 기반 점검으로 핵심 저장 상태를 확인한다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
python tools\check_offline_readiness.py
python tools\check_offline_readiness.py --output-json tmp\offline_readiness_latest.json --tail-lines 3
python tools\check_git_sync_status.py
python tools\check_git_sync_status.py --strict
python tools\check_backend_runtime_env.py --check-daily-tests
python tools\check_backend_module_health.py --strict
python tools\check_console_static_contract.py --strict
python tools\check_console_asset_and_js.py
python tools\check_storage_quality_store.py --strict
python tools\check_public_ir_sec_store.py --require-any
python tools\check_firecrawl_ir_collector.py
python tools\check_firecrawl_ir_collector.py --input-json docs\examples\firecrawl_ir_registry.sample.json
python tools\check_firecrawl_ir_collector.py --input-json docs\examples\firecrawl_ir_registry.sample.json --output-json output\firecrawl-ir-payloads.json
python tools\check_firecrawl_ir_collector.py --use-env-registry
python tools\check_firecrawl_ir_collector.py --env-file docs\examples\firecrawl_ir_pilot.env.example --use-env-registry
python tools\check_firecrawl_ir_collector.py --env-file path\to\firecrawl.env --use-env-registry --hosted-scrape-dry-run --output-json output\firecrawl-ir-hosted-dry-run.json
python tools\check_firecrawl_ir_collector.py --require-env-registry --require-rpc-ready
python tools\check_firecrawl_ir_collector.py --env-file path\to\firecrawl.env --require-env-registry --require-rpc-ready
.\tools\run_firecrawl_ir_rpc_preflight.ps1 -EnvFile path\to\firecrawl-rpc.env
.\tools\run_firecrawl_ir_rpc_preflight.ps1 -EnvFile path\to\firecrawl-rpc.env -Mode Submit
python tools\check_firecrawl_monitor_collector.py
python tools\check_firecrawl_monitor_collector.py --input-json docs\examples\firecrawl_monitor_registry.sample.json
python tools\check_firecrawl_monitor_collector.py --env-file docs\examples\firecrawl_monitor.env.example --use-env-registry
python tools\check_firecrawl_monitor_collector.py --env-file path\to\firecrawl-monitor.env --require-env-registry --require-create-ready
python tools\check_firecrawl_earnings_collector.py
python tools\check_deepseek_ir_analysis.py
python tools\check_portfolio_change_detection.py
python tools\check_telegram_brief_sender.py
python tools\check_telegram_runtime_profile.py --json
python tools\check_portfolio_report_alert.py --json
python tools\check_portfolio_report_alert_task_status.py --json
python tools\check_portfolio_report_alert_task_status.py --task-name "InvestmentJournalApp OpenClaw Portfolio Report Alert Postrun" --expected-time 07:10 --required-arg run_openclaw_portfolio_report_alert_postrun.ps1 --required-arg=-WriteState --required-arg=-Enabled --required-arg=-Submit --json
python tools\check_telegram_favorite_posts.py --sample --enabled
python tools\check_telegram_favorite_posts.py --write-env-template tmp\telegram-favorite-posts.local.env
python tools\check_telegram_favorite_posts.py --env-file tmp\telegram-favorite-posts.local.env --live-fetch
python tools\check_telegram_favorite_posts.py --channels-json-file docs\examples\telegram_favorite_channels.from_screenshot.json --live-fetch
python tools\check_telegram_favorite_posts.py --enabled --channels-json '[{"username":"example_channel","label":"Example","max_posts":30}]' --live-fetch
python tools\check_telegram_authenticated_collector.py --json
python tools\check_telegram_authenticated_collector.py --write-env-template tmp\telegram-authenticated-collector.local.env
python tools\check_telegram_authenticated_collector.py --env-file tmp\telegram-authenticated-collector.local.env --enabled --json
python tools\check_earnings_transcript_collector.py
python tools\check_portfolio_signal_score.py
python tools\check_portfolio_brief_contract.py
python tools\check_market_signal_graph_pipeline_contract.py
python tools\check_agent_operating_foundation.py --json --strict
python tools\check_local_ai_survival.py --json --strict
python tools\check_rag_failure_diagnostics.py --strict
python tools\check_llm_bridge_store.py --require-active-rag
python tools\check_investment_insight_hub.py --strict
python tools\check_macro_source_signal_linkage.py --strict
python tools\check_storage_duplicate_review.py --strict
python tools\check_news_inbox_priority_queue.py --strict
python tools\build_code_knowledge_graph.py --print-summary
python tools\check_code_knowledge_graph.py --strict
python tools\check_operational_readiness_score.py --strict --min-score 95
python tools\show_openclaw_bridge_status.py --json
python tools\check_openclaw_quick_health.py --json
python tools\check_openclaw_investment_context.py --max-age-hours 24
python tools\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes
powershell.exe -ExecutionPolicy Bypass -File .\tools\sync_openclaw_investment_context.ps1 -RequireCompletionAudit
python tools\check_portfolio_analysis_coverage.py --all-portfolios --min-average-completion 0.95 --write-backlog --strict
python tools\analyze_code_diff_impact.py --refresh --strict
```

백엔드가 실행 중이면 통합 검증을 사용한다.

`check_backend_runtime_env.py --check-daily-tests`는 현재 Python 의존성, `8001` health 응답, 일일 추천 단위 테스트 결과를 함께 보여준다. 백엔드가 꺼져 있거나 WSL에서 Windows 백엔드에 접근하지 못하는 상태는 기본 점검에서는 권고로 표시하고, 운영 배포 직전처럼 반드시 실행 상태를 강제해야 할 때만 `--strict`를 붙인다.

```powershell
cd C:\Users\lib20\InvestmentJournalApp
.\tools\run_daily_research_operations.ps1
.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckCoreSafeguards -CheckSourceAutomationStatus -CheckSourceAutomationStore -CheckDailyRecommendations -CheckDailyRecommendationStore -CheckStorageQualitySafeguards -CheckPortfolioQuantityProtection -CheckPortfolioStore -StorageQualityMaxBodyMissing 0 -StorageQualityMaxOcrNeeded 0
.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckNpsDomesticEquityAllocation
python tools\smoke_research_console_clicks.py --url http://127.0.0.1:8001/console/index.html?smoke=clicks --progress --progress-heartbeat-seconds 30
python tools\smoke_research_console_clicks.py --list-stages
python tools\smoke_research_console_clicks.py --only-public-ir-sec --progress --progress-heartbeat-seconds 20
python tools\smoke_research_console_menus.py
python tools\smoke_research_console_external_sources.py
python tools\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 6 --max-latest-age-days 1
python tools\check_daily_recommendation_citations.py --strict
python tools\check_daily_recommendation_policy_signals.py --strict
python tools\check_daily_recommendation_render_layout.py --strict --output-screenshot output\daily-recommendation-layout.png
python tools\check_nps_domestic_equity_allocation.py --rebalance-plan
```

`run_daily_research_operations.ps1`는 포트폴리오 가격을 갱신하고, 오늘 추천을 `force=true`로 재분석하고, 텔레그램 중요 브리프 delivery ledger를 `check_telegram_brief_delivery.py --write-state`로 갱신한 뒤, 보유 종목 신규 리포트 알림 ledger를 `check_portfolio_report_alert.py --write-state`로 갱신한다. 이후 리서치 중복/Dossier 상태와 OpenClaw 투자리서치 브리지를 `-RequireCompletionAudit`로 엄격 동기화한다. 텔레그램 단계는 기본 dry-run이며 중요 브리프는 `-SubmitTelegramBriefDelivery`, 보유 종목 리포트 알림은 `-SubmitPortfolioReportAlert`를 붙였을 때만 실제 발송을 시도하고, `-EnableTelegramBriefCleanup`까지 붙여야 저우선순위 메시지 삭제가 허용된다. 마지막으로 포트폴리오 저장/NPS 14%/일일 추천 저장/통합 투자 인사이트 허브/오프라인 readiness 검증을 이어서 실행한다. 백엔드가 이미 `127.0.0.1:8001`에서 실행 중일 때 쓰는 일일 운영 래퍼이며, 필요하면 `-SkipPortfolioRefresh`, `-SkipRecommendationRun`, `-SkipRecommendationPreview`, `-SkipTelegramBriefDelivery`, `-SkipPortfolioReportAlert`, `-SkipResearchAutomationRefresh`, `-SkipOpenClawSync`, `-SkipVerification`로 일부 단계를 건너뛴다. 포트폴리오 갱신이나 추천 API가 시간 초과되더라도 저장 원본 검증이 통과하면 운영 흐름은 복구 경로로 계속 진행한다.

Firecrawl IR RPC 실전 전환은 `docs\examples\firecrawl_ir_rpc.env.example`을 ignored secret env 파일로 복사해 값을 채운 뒤 `.\tools\run_firecrawl_ir_rpc_preflight.ps1 -EnvFile path\to\firecrawl-rpc.env`로 먼저 `--require-env-registry --require-rpc-ready`를 통과해야 한다. 이 단계는 secret 원문을 출력하지 않고 output JSON에는 configured 여부와 readiness error만 남긴다. 실제 적재는 같은 파일로 `-Mode Submit`을 붙였을 때만 실행하며, 전부 `skipped`/`failed`인 batch는 성공으로 보지 않는다.

전체 클릭 스모크는 실제 메뉴/버튼/포트폴리오/LLM/RAG/추천 추적까지 확인하므로 수 분이 걸릴 수 있다. 자동화나 터미널 래퍼에서 실행할 때는 외부 명령 제한 시간을 최소 600초 이상으로 두고, `--progress --progress-heartbeat-seconds 30`으로 주요 진행 구간과 장시간 브라우저 대기 heartbeat를 출력한다. 부분 확인은 `--list-stages`로 가능한 체크포인트를 본 뒤 `--stop-after <stage>`를 붙여 실행한다. Firecrawl IR Hosted Dry-run 버튼과 공개 IR/SEC 입력 피드백만 확인할 때는 `--only-public-ir-sec`를 사용한다. 묶음 검증 래퍼에서는 `.\tools\verify_research_console.ps1 -ClickSmokeProgress -ClickSmokeProgressHeartbeatSeconds 30 -ClickSmokeStopAfter portfolio` 또는 `.\tools\verify_research_console.ps1 -SkipWriteSmoke -ClickSmokeOnlyPublicIrSec -ClickSmokeProgress -ClickSmokeProgressHeartbeatSeconds 20`처럼 같은 옵션을 전달한다. 실제 Windows 브라우저 래퍼에서는 `.\tools\smoke_research_console_windows.ps1 -Mode Clicks -PublicIrSecClicks`로 같은 범위만 실행한다.
정적 콘솔 계약은 상단 액션 피드백과 추천 카드의 `aria-live` 영역도 확인해, 버튼 클릭 후 메시지가 보이지 않는 회귀를 백엔드 없이 잡는다.
메뉴 스모크는 17개 상단 메뉴가 모두 열리는지, 대시보드 주요 버튼에 즉시 피드백이 뜨는지, 버튼 텍스트가 잘리지 않는지 확인한다.
외부 소스 스모크는 KCIF, EMERiCs/CSF/KIEP, 자동화 상태 버튼이 화면에서 실제 결과를 반환하는지 확인한다.


## 코드 정리와 운영 안정화

- 코드 지식 그래프는 백엔드 없이 `research_vault\_system\code_knowledge_graph.json`에 생성되며, 소스코드 원문을 외부로 전송하지 않는다.
- `시스템 구조 맵` 버튼은 운영 콘솔에서 코드/운영 흐름 연결 상태를 보여주는 확인 전용 액션이다.
- 변경 전후에는 `python tools\analyze_code_diff_impact.py --refresh`로 매일 추천, RAG, 포트폴리오, 소스 자동화, 자동 분류, 콘솔 클릭 회귀, 백엔드 모듈 헬스 중 어느 검증을 다시 돌려야 하는지 확인한다.
- 오프라인 준비 점검에는 코드 지식 그래프 엄격 검증, 운영 완성도 95% 점검, 전체 포트폴리오 분석 커버리지 95% 이상 점검, 변경 영향 분석이 포함되어, 필수 흐름이나 핵심 모듈이 빠지거나 새 코드 파일이 그래프에 매핑되지 않으면 운영 전 점검에서 실패한다.

## 빠른 복구/확인 위치

- `현재 작업 디렉토리가 없습니다` 또는 OneDrive 경로가 보이면 PowerShell에서 `. C:\Users\lib20\InvestmentJournalApp\scripts\enter-investment-research-os.ps1`를 실행해 현재 창의 작업 루트를 바로잡는다.
- 콘솔 주소는 `http://127.0.0.1:8001/console/index.html`이고, 백엔드는 `C:\Users\lib20\InvestmentJournalApp`에서 `.\scripts\start-research-backend.ps1 -Port 8001`로 실행한다.
- 매일 추천은 첫 화면의 `오늘 한국/미국 추천 1~3위`, 저장 데이터 탭의 `오늘 한국/미국 추천 1~3위`, `추천 추적 상태`에서 본다. 백엔드가 꺼져 있으면 `python tools\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 6 --max-latest-age-days 1`로 저장 원본을 확인한다.
- 푸시 대기 커밋이 있으면 Windows Git 인증이 가능한 터미널에서 `git push origin main`을 실행한다. OneDrive 경로에서는 푸시 전 검증이나 서버 실행을 하지 않는다.

## 운영 주의

- 자동 추천은 매수 지시가 아니라 보유/관심 데이터 기반 일일 검토 후보이다.
- 저작권 제한 소스는 원문 전문을 저장하지 않고 메타데이터와 요약 중심으로 연결한다.
- 민감정보와 `.env`는 커밋하지 않는다.
- OneDrive는 작업 루트로 사용하지 않는다.
- `python tools\check_git_sync_status.py --strict`는 작업트리 변경이나 원격 ahead가 있을 때 운영 전 점검 실패로 처리한다. 로컬 ahead 커밋은 Windows Git 인증 가능한 터미널에서 `git push origin main`으로 올린다.
