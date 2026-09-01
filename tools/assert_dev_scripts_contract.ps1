param(
  [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

$contracts = @(
  @{
    Path = "scripts\start-research-backend.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'research_os_main.py',
      'research_os_main:app',
      'Resolve-BackendPython',
      '-PythonExe',
      'Get-Command netstat',
      '-StopExistingPortProcess',
      'Get-CimInstance Win32_Process',
      'Test-ResearchBackendCommandLine',
      'Stop-ResearchBackendProcesses',
      '중복 백엔드 프로세스 정리'
    )
  },
  @{
    Path = "scripts\restart-research-backend.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'start-research-backend.ps1',
      '-StopExistingPortProcess',
      '/api/v1/system/health',
      '/console/index.html',
      'RedirectStandardOutput',
      'RedirectStandardError',
      '재시작 확인 완료',
      'Get-CimInstance Win32_Process',
      'Get-PortOwningProcessIds',
      'Assert-SingleResearchBackendListener',
      '백엔드 포트 단일성 확인 완료',
      '중복 백엔드 프로세스 정리'
    )
  },
  @{
    Path = "scripts\enter-investment-research-os.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '[switch]$RestartBackend',
      '[switch]$OpenConsole',
      'restart-research-backend.ps1 -Port 8001',
      'status_research_console.ps1 -Strict',
      '-RestartBackend -OpenConsole',
      'http://127.0.0.1:8001/console/index.html'
    )
  },
  @{
    Path = "tools\start_backend.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$StopExistingPortProcess',
      '$ForceExistingPortProcess',
      'Assert-PortAvailable',
      'show_dev_server_ports.ps1',
      'fallback 포트를 사용하세요',
      '강제 taskkill은 실행하지 않았습니다'
    )
  },
  @{
    Path = "tools\start_mobile_web.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$StopExistingPortProcess',
      '$ForceExistingPortProcess',
      '$env:EXPO_PUBLIC_API_BASE_URL',
      '$expoHostName',
      'Expo web supports --host values lan, tunnel, or localhost',
      'Unsupported Expo host',
      'show_dev_server_ports.ps1',
      '강제 taskkill은 실행하지 않았습니다',
      'npx @expoArgs'
    )
  },
  @{
    Path = "tools\restart_backend_verified.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'stop_dev_servers.ps1',
      'Invoke-CimMethod',
      'Win32_Process',
      '$FallbackPorts',
      'UsedFallback',
      'ConvertTo-Json',
      '/api/v1/manual-transactions/import.csv/template',
      'manual-transactions-template.csv',
      'CSV 템플릿 API 응답 검증에 실패했습니다.',
      '8001 연구 콘솔은 research_os_main:app 진입점입니다.',
      'restart-research-backend.ps1 -Port 8001',
      'main:app 기반 모바일/API 백엔드 검증용'
    )
  },
  @{
    Path = "tools\status_dev_servers.ps1"
    Snippets = @(
      '[switch]$Strict',
      '[switch]$RequirePortfolio',
      '$FallbackApiPorts',
      'Get-PortOwningProcessIds',
      'API fallback',
      'Invoke-BackendStatusCheck',
      '정상 fallback API 사용',
      '$apiBaseUrlExplicit',
      'manual CSV template',
      '/api/v1/manual-transactions/import.csv/template',
      '선택 건너뜀',
      '상태 점검 실패'
    )
  },
  @{
    Path = "tools\status_research_console.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/system/health',
      '/api/v1/data-providers/status',
      '/api/v1/ocr/status',
      '/api/v1/storage/quality-dashboard',
      '/console/index.html',
      'OneDrive 제외',
      '저장 데이터 본문 누락',
      '연구 콘솔 상태 점검 통과',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\smoke_mobile_web.ps1"
    Snippets = @(
      '$FallbackApiPorts',
      '$RequirePortfolio',
      'Invoke-BackendSmoke',
      'fallback API 확인',
      'OK fallback API smoke',
      'Invoke-RequiredText',
      '/api/v1/manual-transactions/import.csv/template',
      'CSV 템플릿 API만 404라면 오래된 백엔드가 8010 포트를 잡고 있을 수 있습니다.',
      'start_backend.ps1 -StopExistingPortProcess'
    )
  },
  @{
    Path = "tools\smoke_kiwoom_history_live.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$ConfirmLiveApi',
      '$CheckTokenFirst',
      '$NoCancelOnTimeout',
      '$FallbackApiPorts',
      'TradeDate는 YYYY-MM-DD 또는 YYYYMMDD 형식',
      '실행하려면 명시적으로 -ConfirmLiveApi',
      '/api/v1/brokerage/status',
      '/api/v1/brokerage/kiwoom/token-test',
      '/api/v1/sync/kiwoom/history/start',
      '/api/v1/sync/kiwoom/history/jobs/$jobId',
      '/api/v1/sync/kiwoom/history/jobs/$jobId/cancel',
      '/api/v1/journal/drafts?page=1&page_size=1',
      '토큰 원문과 계좌번호',
      'ConvertTo-Json'
    )
  },
  @{
    Path = "tools\smoke_kiwoom_history_range_live.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '$ConfirmLiveApi',
      '$CheckTokenFirst',
      '$NoCancelOnTimeout',
      '$FallbackApiPorts',
      '$MaxRangeDays',
      'StartDate/EndDate는 YYYY-MM-DD 또는 YYYYMMDD 형식',
      '실행하려면 명시적으로 -ConfirmLiveApi',
      '최대 $MaxRangeDays 일',
      '/api/v1/brokerage/status',
      '/api/v1/brokerage/kiwoom/token-test',
      '/api/v1/sync/kiwoom/history/start',
      '/api/v1/sync/kiwoom/history/jobs/$jobId',
      '/api/v1/sync/kiwoom/history/jobs/$jobId/cancel',
      '/api/v1/journal/drafts?page=1&page_size=1',
      '토큰 원문과 계좌번호',
      'ConvertTo-Json'
    )
  },
  @{
    Path = "tools\stop_dev_servers.ps1"
    Snippets = @(
      '[switch]$DryRun',
      '[switch]$ForceAnyProcess',
      '$AllowedProcessNames',
      'Get-Command netstat',
      'Test-CanStopProcess',
      'remainingProcessIds',
      '기본 개발 포트가 아니며 허용된 개발 프로세스가 아닙니다'
    )
  },
  @{
    Path = "tools\check_customs_trade_quality.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/macro/customs-trade/latest',
      '/api/v1/macro/customs-trade/total-trend/status',
      'LatestStorageSkipped',
      'LatestHasValidRows',
      'LatestSavedValidRows',
      'LatestRequiresTotalTrendStatus',
      'LatestHasTotalTrendStatus',
      'CustomsFileCountChangeAllowed',
      'TotalTrendHasStorage',
      '$RequireTotalTrendAuthorized',
      'Get-CustomsVaultFileCount',
      'CustomsDirExistsBefore',
      'CustomsDirExistsAfter',
      'CustomsDirCreatedDuringCheck',
      'CustomsFileCountChanged',
      '점검 중 CUSTOMS 폴더가 새로 생성되었습니다.',
      'next_action',
      'OutputEncoding',
      '관세청 수출입 데이터 품질 점검 실패'
    )
  },
  @{
    Path = "tools\check_portfolio_quantity_protection.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/portfolios/${encodedPortfolioName}?refresh_prices=false&persist_refresh=false',
      '[uri]::EscapeDataString($PortfolioName)',
      'active_portfolio',
      'ExpectedQuantity',
      'ExpectedCurrency',
      'manual_or_overseas_protected',
      'QuantityOk',
      'CurrencyOk',
      'SyncProtected',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\check_storage_quality_safeguards.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      '/api/v1/storage/quality-dashboard',
      'MaxBodyMissing',
      'MaxOcrNeeded',
      'BodyMissingItemLimit',
      'BodyMissingOk',
      'BodyMissingItems',
      'BodyMissingItemDetailsOk',
      'OcrNeededOk',
      'SoftArchiveVisible',
      'CopyrightPolicyOk',
      'NextActions',
      '원문 본문은 저장하지 않고',
      '저장소 품질 안전장치 확인 완료',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\check_core_safeguards.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'check_customs_trade_quality.ps1',
      'check_portfolio_quantity_protection.ps1',
      'check_storage_quality_safeguards.ps1',
      'CustomsStartYymm',
      'PortfolioExpectedQuantity',
      'PortfolioExpectedHoldings',
      'MaxBodyMissing',
      'LatestStorageSkipped',
      'LatestSavedValidRows',
      'CustomsFileCountChangeAllowed',
      'SyncProtected',
      'CheckedCount',
      'FailedCount',
      'Items',
      'BodyMissingItems',
      'NewsBodyStoragePolicy',
      'NextActions',
      '핵심 안전장치 확인 완료',
      '[switch]$Strict'
    )
  },
  @{
    Path = "tools\verify_research_console.ps1"
    Snippets = @(
      '[switch]$CheckCoreSafeguards',
      '[switch]$CheckCustomsTradeQuality',
      '[switch]$CheckPortfolioQuantityProtection',
      '[switch]$CheckPortfolioStore',
      'check_portfolio_store.py',
      'check_all_portfolio_store.py',
      '포트폴리오 저장 파일 오프라인 확인',
      '전체 포트폴리오 저장 구조 확인',
      '[switch]$CheckStorageQualitySafeguards',
      '[switch]$CheckSourceAutomationStatus',
      '[switch]$CheckSourceAutomationStore',
      'check_research_source_store.py',
      '리서치 소스 저장 파일 오프라인 확인',
      '[switch]$CheckDailyRecommendations',
      '[switch]$CheckDailyRecommendationStore',
      '[switch]$CheckInterestSummaryLayout',
      '[switch]$CheckInvestmentInsightHub',
      '[string]$ClickSmokeStopAfter',
      '[switch]$ClickSmokeOnlyPublicIrSec',
      '[switch]$ClickSmokeProgress',
      '$clickSmokeArgs',
      '--stop-after',
      '--only-public-ir-sec',
      'check_daily_recommendations_store.py',
      'check_interest_summary_render_layout.py',
      'check_investment_insight_hub.py',
      'backend\research_os\investment_insight_hub.py',
      'Resolve-VerifyPython',
      'Resolve-LiveSmokePython',
      'pythonLiveSmoke',
      'Resolve-VerifyNode',
      'Convert-ToWslPath',
      'Convert-ToolArgsForWsl',
      '일일 추천 저장 파일 오프라인 확인',
      '관심종목/섹터 이름-only 상세 열림 확인',
      '통합 투자 인사이트 허브 오프라인 확인',
      '$CustomsBaseUrl',
      '$CustomsDevUserToken',
      '$CustomsStartYymm',
      '$CustomsEndYymm',
      '$RequireCustomsTotalTrendAuthorized',
      '$PortfolioQuantityBaseUrl',
      '$PortfolioQuantityName',
      '$PortfolioQuantityTicker',
      '$PortfolioQuantityExpected',
      '$PortfolioQuantityExpectedHoldings',
      '$StorageQualityBaseUrl',
      '$StorageQualityMaxBodyMissing',
      '$StorageQualityMaxOcrNeeded',
      'check_customs_trade_quality.ps1',
      'check_portfolio_quantity_protection.ps1',
      'check_storage_quality_safeguards.ps1',
      'check_core_safeguards.ps1',
      '핵심 안전장치 묶음 확인',
      '-BaseUrl $CustomsBaseUrl',
      '-DevUserToken $CustomsDevUserToken',
      '-RequireTotalTrendAuthorized:$RequireCustomsTotalTrendAuthorized',
      '$LASTEXITCODE',
      'ConvertFrom-Json',
      'CustomsDirExistsBefore',
      'CustomsDirExistsAfter',
      'CustomsDirCreatedDuringCheck',
      'CustomsFileCountChanged',
      'CustomsFileCountChangeAllowed',
      'LatestStorageSkipped',
      'LatestSavedValidRows',
      'TotalTrendHttpStatusCode',
      'TotalTrendHasStorage',
      '포트폴리오 수량 보호 확인',
      'SyncProtected',
      '저장소 품질 안전장치 확인',
      'NewsBodyStoragePolicy',
      '본문 보강 대상='
    )
  },

  @{
    Path = "tools\run_daily_research_operations.ps1"
    Snippets = @(
      'refresh_portfolio_prices.py',
      '$SkipVerification.IsPresent',
      '/api/v1/daily-recommendations/run?',
      '[char]38',
      'save_result=true',
      '[switch]$SkipRecommendationPreview',
      '[switch]$SkipTelegramBriefDelivery',
      '[switch]$SubmitTelegramBriefDelivery',
      '[switch]$EnableTelegramBriefCleanup',
      '[switch]$SkipResearchAutomationRefresh',
      '[switch]$SkipOpenClawSync',
      'check_daily_recommendation_candidate_policy.py',
      'check_telegram_brief_delivery.py',
      '--output-json',
      '--write-state',
      '--cleanup-enabled',
      'tmp\daily_recommendation_candidate_policy_preview.json',
      '추천 저장/재계산 프리뷰 저장',
      '텔레그램 중요 브리프 delivery ledger 갱신',
      '실적 일정/DART/IR/중복/Dossier 상태 갱신',
      'check_research_evidence_pipeline.py',
      'INVESTMENT_RESEARCH_DEV_USER_TOKEN',
      '--refresh',
      '--write-state',
      '--strict',
      'check_research_source_store.py --strict',
      '리서치 소스 저장 상태 검증이 통과해 운영 루틴을 계속합니다.',
      'sync_openclaw_investment_context.ps1',
      'OpenClaw 투자리서치 브리지 동기화',
      '포트폴리오 가격 갱신 응답은 실패했지만 저장 상태 검증을 시도합니다.',
      'check_all_portfolio_store.py',
      '오늘 추천 API 응답 실패/타임아웃',
      '--max-latest-age-days 0',
      '오늘 추천 저장 검증이 통과해 운영 루틴을 계속합니다.',
      'verify_research_console.ps1',
      '-CheckPortfolioStore',
      '-CheckNpsDomesticEquityAllocation',
      '-CheckDailyRecommendationStore',
      '-CheckInvestmentInsightHub',
      '포트폴리오 가격 갱신',
      '오늘 추천 강제 재분석',
      '운영 검증',
      '일일 리서치 운영 루틴 완료'
    )
  },

  @{
    Path = "tools\smoke_research_console_windows.ps1"
    Snippets = @(
      'assert_project_root.ps1',
      'Resolve-WindowsPython',
      'Start-Process',
      'PYTHONIOENCODING',
      'PYTHONUTF8',
      'smoke_research_console_menus.py',
      'smoke_research_console_clicks.py',
      '--only-system-check',
      '[switch]$PublicIrSecClicks',
      '--only-public-ir-sec',
      '실제 브라우저 스모크 검증 완료'
    )
  },

  @{
    Path = "tools\smoke_research_console_clicks.py"
    Snippets = @(
      '--only-system-check',
      '--progress',
      '--progress-heartbeat-seconds',
      '--list-stages',
      '--stop-after',
      '--only-public-ir-sec',
      '[smoke]',
      'system check completion',
      '전체 시스템 점검 완료',
      '네이버 리서치/시장일지 상태',
      'recentWeeklyEvidenceSynthesisButton',
      'recentWeeklyEvidenceButtonVisible'
    )
  },

  @{
    Path = "tools\verify_research_console.ps1"
    Snippets = @(
      'ClickSmokeProgressHeartbeatSeconds',
      '--progress-heartbeat-seconds',
      'ClickSmokeStopAfter',
      'ClickSmokeProgress'
    )
  },




  @{
    Path = "tools\smoke_research_console_menus.py"
    Snippets = @(
      "DEFAULT_URL",
      "include_write_actions",
      "dashboardCommandLayout",
      "clippedDashboardCommands",
      "menuResults",
      "shortcutResults",
      "runtimeErrors",
      "#recentWeeklyEvidenceSynthesisButton",
      "추천 근거 요약"
    )
  },
  @{
    Path = "tools\check_offline_readiness.py"
    Snippets = @(
      'CHECKS',
      'check_git_sync_status.py',
      'check_public_repo_safety.py',
      'check_backend_runtime_env.py',
      '--check-daily-tests',
      'check_portfolio_analysis_coverage.py',
      '--all-portfolios',
      '--min-average-completion',
      '포트폴리오 분석 커버리지',
      'check_portfolio_store.py',
      'check_all_portfolio_store.py',
      '전체 포트폴리오 저장 구조',
      '--max-price-age-hours',
      '--max-sync-age-hours',
      '--min-holdings',
      'check_research_source_store.py',
      'check_public_ir_sec_store.py',
      '공개 IR/SEC 저장 품질',
      'Firecrawl IR registry 샘플 payload',
      'docs/examples/firecrawl_ir_registry.sample.json',
      'check_backend_module_health.py',
      'check_operational_readiness_score.py',
      '운영 완성도 95%',
      'analyze_code_diff_impact.py',
      '변경 영향 분석',
      'check_console_static_contract.py',
      'check_console_asset_and_js.py',
      'check_storage_quality_store.py',
      'check_rag_failure_diagnostics.py',
      'check_llm_bridge_store.py',
      'check_rag_synthesis_store.py',
      'check_openclaw_investment_context.py',
      'check_openclaw_bridge_completion.py',
      'show_openclaw_bridge_status.py',
      'check_openclaw_consumer_smoke.py',
      '--require-report-hashes',
      'check_daily_recommendations_store.py',
      'check_daily_recommendation_citations.py',
      'OpenClaw 투자리서치 브리지',
      'OpenClaw 상태 요약',
      'OpenClaw 소비자 smoke',
      '저장/RAG 실패 진단',
      '매일 추천 RAG 근거 문서',
      'LLM/RAG 저장 상태',
      'RAG 합성 저장 상태',
      '오프라인 운영 점검 통과'
    )
  },
  @{
    Path = "tools\run_firecrawl_ir_rpc_preflight.ps1"
    Snippets = @(
      '[Parameter(Mandatory = $true)]',
      '[ValidateSet("Preflight", "Submit")]',
      '--env-file',
      '--require-env-registry',
      '--require-rpc-ready',
      '--submit',
      'firecrawl-ir-rpc-preflight.json',
      'firecrawl-ir-rpc-submit.json'
    )
  },
  @{
    Path = "tools\analyze_code_diff_impact.py"
    Snippets = @(
      'FLOW_IMPACT_HINTS',
      'fallback_flow_ids',
      'investment_direction',
      '투자 방향 프로필 점수',
      'daily_recommendations',
      '--refresh',
      '--strict',
      '운영 흐름별 재검증 권장'
    )
  },





  @{
    Path = "tools\build_code_knowledge_graph.py"
    Snippets = @(
      "SCAN_GLOBS",
      "backend/research_os/README.md",
      "docs/structure-map.md",
      "FLOW_DEFINITIONS",
      "code_knowledge_graph.json"
    )
  },
  @{
    Path = "tools\check_code_knowledge_graph.py"
    Snippets = @(
      'REQUIRED_FLOW_IDS',
      'REQUIRED_NODE_IDS',
      '--max-graph-age-hours',
      '그래프 생성 시각 오래됨',
      '그래프 node_count 불일치',
      '그래프 edge_count 불일치',
      '그래프 summary.flows_ok 불일치',
      '코드 지식 그래프 상태 정상'
    )
  },






  @{
    Path = "tools\check_investment_calendar_store.py"
    Snippets = @(
      '투자 캘린더 저장 파일',
      'build_investment_calendar_earnings_events',
      'load_latest_calendar_file_payload',
      'merge_investment_calendar_events',
      'earnings_calendar_cache.json',
      'user_portfolios.json',
      'interest_list.json',
      '--min-earnings-events',
      'future_earnings_candidate_count',
      '향후 실적 후보',
      '실적발표 이벤트 제목 표기 누락',
      '투자 캘린더 저장/실적발표 상태 정상'
    )
  },
  @{
    Path = "tools\check_operational_readiness_score.py"
    Snippets = @(
      '운영 완성도 점수',
      '--min-score',
      '--daily-time',
      '07:00',
      'daily_recommendations_state.json',
      'time(hour=7)',
      'code_knowledge_graph.json',
      'user_portfolios.json',
      'research_automation_status.json',
      '투자 캘린더/실적 일정',
      'future_earnings_candidates',
      '향후 실적 후보',
      '추천 근거 문서 연결',
      'recommendation_citations_signal',
      '저장/RAG 실패 진단',
      'rag_diagnostics_signal',
      'openclaw_bridge_signal',
      'openclaw_investment_bridge',
      'openclaw_completion_signal',
      'openclaw_completion_audit',
      'openclaw_status_summary_signal',
      'openclaw_status_summary',
      'check_openclaw_bridge_completion.py',
      'show_openclaw_bridge_status.py',
      '--require-report-hashes',
      'OpenClaw 투자리서치 브리지',
      'OpenClaw 상태 요약',
      'check_openclaw_investment_context.py',
      '운영 완성도 점검 정상'
    )
  },

  @{
    Path = "tools\check_daily_recommendation_render_layout.py"
    Snippets = @(
      '오늘 추천 결과 카드 렌더링 레이아웃',
      'dailyRecommendationCards',
      'marketSectionCount',
      'recommendationCardCount',
      'clippedTextElements',
      'pageHasHorizontalOverflow',
      '--output-screenshot',
      '추천 결과 렌더링 점검 정상'
    )
  },

  @{
    Path = "tools\check_interest_summary_render_layout.py"
    Snippets = @(
      '보유종목과 관심종목/섹터 요약 클릭 상세 열림',
      'holding-card-summary',
      'holdingDetailOpened',
      'overviewChipCount',
      'actionLabels',
      'holdingActionFlows',
      '보유 종목 상세 액션 흐름 실패',
      'interest-ticker-summary-row',
      'interest-sector-summary-row',
      'tickerNameOnlyCount',
      'sectorNameOnlyCount',
      'tickerDetailOpened',
      'sectorDetailOpened',
      '관심 요약 렌더링 점검 정상'
    )
  },

  @{
    Path = "tools\check_news_inbox_priority_queue.py"
    Snippets = @(
      '뉴스 인박스 우선 분류 큐',
      'news_inbox.json',
      'priority_count',
      'policy_priority_count',
      'target_matched_count',
      'priority_reason',
      'strict_errors',
      '뉴스 인박스 우선 분류'
    )
  },

  @{
    Path = "tools\check_storage_duplicate_review.py"
    Snippets = @(
      '저장 자료 중복 리뷰',
      'storage_duplicate_review.json',
      'representative_only',
      'excluded_from_dossier',
      'hard_delete_allowed',
      'duplicate_entry_count',
      'strict_errors',
      'Dossier 사용 정책'
    )
  },

  @{
    Path = "tools\check_macro_source_signal_linkage.py"
    Snippets = @(
      '매크로/지역 소스 연결 신호',
      'kcif_reports_watch.json',
      'regional_business_sources_watch.json',
      'recommended_action',
      'matched_themes',
      'target_matches',
      'KCIF 상세',
      'strict_errors'
    )
  },





  @{
    Path = "tools\check_portfolio_analysis_coverage.py"
    Snippets = @(
      '포트폴리오 분석 모듈 커버리지',
      '--write-backlog',
      '--all-portfolios',
      'unique_holdings_from_portfolios',
      'portfolio_analysis_backlog.json',
      'portfolio_analysis_module_state',
      'portfolio_analysis_review_state',
      '--min-average-review-completion',
      'portfolio_analysis_next_action',
      '포트폴리오 분석 커버리지 점검 정상'
    )
  },


  @{
    Path = "tools\build_portfolio_human_review_packet.py"
    Snippets = @(
      '사람 검토 준비 패킷',
      '--ticker',
      '--write',
      'local_only',
      'build_portfolio_human_review_packet'
    )
  },


  @{
    Path = "backend\research_os\portfolio_analysis_coverage.py"
    Snippets = @(
      'REQUIRED_PORTFOLIO_ANALYSIS_MODULES',
      'team_report',
      'smart-trade-setup',
      'REVIEW_CHECKLIST_COMPLETION_THRESHOLD',
      'HUMAN_REVIEW_PACKET_TYPE',
      'portfolio_analysis_checklist_status',
      'portfolio_human_review_packet',
      'portfolio_human_review_queue',
      'missing_portfolio_analysis_labels',
      'portfolio_analysis_next_action'
    )
  },


  @{
    Path = "backend\research_os\portfolio_review_packet.py"
    Snippets = @(
      'human-review-packet',
      'stored_dart_filings',
      'build_portfolio_human_review_packet',
      'affects_review_gate',
      'write_portfolio_human_review_packet'
    )
  },


  @{
    Path = "backend\research_os\rag_synthesis.py"
    Snippets = @(
      'REPORT_TYPE = "rag-query-synthesis"',
      'build_rag_query_synthesis_payload',
      'render_rag_query_synthesis_markdown',
      'rag_synthesis_storage_key',
      'build_rag_query_synthesis_thesis'
    )
  },


  @{
    Path = "backend\research_os\rag_memory.py"
    Snippets = @(
      'refresh_index: bool = True',
      'if refresh_index:',
      'backfill_research_memory_documents_from_manifest(vault_dir)'
    )
  },


  @{
    Path = "backend\research_os_main.py"
    Snippets = @(
      'request.refresh_dossier'
    )
  },


  @{
    Path = "backend\research_os\analysis_context.py"
    Snippets = @(
      'refresh_index=False',
      'search_research_memory_documents'
    )
  },


  @{
    Path = "backend\research_os\analysis_module_storage.py"
    Snippets = @(
      'dossier_refresh_status',
      'upsert_research_memory_document(vault_dir=vault_dir, entry=saved_entry)'
    )
  },


  @{
    Path = "mobile_app\research_console\api.js"
    Snippets = @(
      'refreshDossier = false',
      'refresh_dossier: refreshDossier'
    )
  },


  @{
    Path = "mobile_app\research_console\console.js"
    Snippets = @(
      'translateDossierRefreshStatus',
      'Dossier 갱신:'
    )
  },






  @{
    Path = "tools\check_public_repo_safety.py"
    Snippets = @(
      'FORBIDDEN_PATH_PATTERNS',
      'ALLOWED_PATHS',
      'SECRET_VALUE_PATTERNS',
      '--exclude-standard',
      '공개 후보 파일',
      '공개 저장소 안전 점검 통과'
    )
  },





  @{
    Path = "tools\check_backend_runtime_env.py"
    Snippets = @(
      'REQUIRED_DISTRIBUTIONS',
      'preferred_python',
      'installed_versions_with_python',
      '.venv',
      'python-dotenv',
      '/api/v1/system/health',
      '--strict',
      '--check-daily-tests',
      'tests.test_daily_recommendations',
      '일일 추천 단위 테스트',
      '백엔드 런타임 준비 상태 확인 완료'
    )
  },
  @{
    Path = "tools\check_git_sync_status.py"
    Snippets = @(
      'origin',
      'rev-list',
      '--strict',
      '작업트리 변경',
      'Git 동기화 엄격 점검 실패',
      '푸시 대기 커밋',
      'Git 동기화 상태 확인 완료'
    )
  },
  @{
    Path = "tools\check_console_asset_and_js.py"
    Snippets = @(
      'update_console_asset_hashes',
      'node',
      '--check',
      '클래식 콘솔 자산/JS 상태 정상'
    )
  },
  @{
    Path = "tools\check_console_static_contract.py"
    Snippets = @(
      'REQUIRED_IDS',
      'REQUIRED_TABS',
      'REQUIRED_FEEDBACK_BUTTON_IDS',
      'REQUIRED_WORKFLOW_ACTIONS',
      'REQUIRED_CSS_SNIPPETS',
      'REQUIRED_LIVE_REGIONS',
      'outputStatus',
      'aria-live',
      '실시간 피드백 aria-live 계약 누락',
      'HTML 버튼 type 속성 누락',
      'HTML 버튼 type 값 확인 필요',
      'JS 템플릿 버튼 type 속성 누락',
      'HTML 버튼 타입:',
      '실시간 피드백 영역',
      'FEEDBACK_TOKENS',
      'button_has_feedback',
      'workflow_actions_in_js_templates',
      'handled_workflow_actions',
      'today-research-update',
      'dashboard-refresh',
      'dailyRecommendationCitationRows',
      'dailyRecommendationMarketGroups',
      'daily-recommendation-citation',
      'daily_recommendation_top_panel_schedule',
      'daily-recommendation-top-panel',
      '근거 문서',
      '워크플로우 핸들러 누락',
      '필수 워크플로우 버튼 누락',
      '메뉴/버튼 레이아웃 CSS 계약 누락',
      '메뉴/버튼 레이아웃 CSS',
      '즉시 피드백/로딩 연결 누락 버튼',
      'selector_ids',
      '클래식 콘솔 정적 계약 정상'
    )
  },
  @{
    Path = "tools\check_backend_module_health.py"
    Snippets = @(
      'EXPECTED_MODULES',
      'EXPECTED_MAIN_IMPORTS',
      'research_os.analysis_data_provider',
      'analysis_data_provider.py',
      'research_os.brokerage',
      'research_os.kis_data_provider',
      'kis_data_provider.py',
      'research_os.data_provider_core',
      'data_provider_core.py',
      'research_os.data_provider_status',
      'research_os.data_provider_status_messages',
      'alpha_vantage_data_provider.py',
      'research_os.alpha_vantage_data_provider',
      'financial_datasets_data_provider.py',
      'research_os.financial_datasets_data_provider',
      'finnhub_data_provider.py',
      'research_os.finnhub_data_provider',
      'fmp_data_provider.py',
      'research_os.fmp_data_provider',
      'research_os.nps_data_provider',
      'research_os.opendart_data_provider',
      'opendart_data_provider.py',
      'nps_data_provider.py',
      'provider_usage.py',
      'research_os.provider_usage',
      'research_os.customs_data_provider',
      'customs_data_provider.py',
      'tiingo_data_provider.py',
      'research_os.tiingo_data_provider',
      'web_search_data_provider.py',
      'research_os.web_search_data_provider',
      'research_os.file_extraction',
      'research_os.market_journal',
      'research_os.portfolio_analysis_coverage',
      'portfolio_analysis_coverage.py',
      'research_os.portfolio_store',
      'portfolio_store.py',
      'research_os.rag_memory',
      'research_os.research_memory',
      'research_os.state_store',
      'state_store.py',
      'BANNED_TERMS',
      'DEFAULT_MAIN_MAX_LINES',
      'DEFAULT_MIN_MODULE_COUNT',
      '--main-max-lines',
      '--min-module-count',
      '큰 도메인 모듈',
      '줄 수 상한 초과',
      '백엔드 모듈 상태 정상'
    )
  },
  @{
    Path = "backend\research_os\README.md"
    Snippets = @(
      "docs/structure-map.md",
      "portfolio_analysis_coverage.py",
      "regional_sources.py",
      "source_url_preview.py",
      "ticker_registry.py",
      "system_health.py",
      "state_store.py",
      "포트폴리오 저장 JSON 읽기"
    )
  },
  @{
    Path = "tools\check_llm_bridge_store.py"
    Snippets = @(
      'DEFAULT_MANIFEST',
      'DEFAULT_RAG_DB',
      'PROMPT_MARKER',
      'RESPONSE_MARKER',
      '--require-active-rag',
      'LLM/RAG 저장 상태 정상',
      'RAG 연결 누락',
      '원 프롬프트 누락',
      'LLM 응답 누락'
    )
  },
  @{
    Path = "tools\check_rag_synthesis_store.py"
    Snippets = @(
      'DEFAULT_MANIFEST',
      'DEFAULT_RAG_DB',
      'REPORT_TYPE',
      '--require-latest-rag',
      'RAG 합성 저장 상태 정상',
      'RAG 연결 누락',
      '다음 액션 누락'
    )
  },
  @{
    Path = "tools\check_rag_failure_diagnostics.py"
    Snippets = @(
      'DEFAULT_MANIFEST',
      'DEFAULT_RAG_DB',
      'MIN_SEARCHABLE_CHARS',
      'missing_rag_document',
      'low_search_text',
      'missing_classification_reason',
      '--max-errors',
      '--strict',
      '저장/RAG 진단 점수',
      '저장/RAG 실패 진단 정상'
    )
  },
  @{
    Path = "backend\research_os\portfolio_performance.py"
    Snippets = @(
      'build_price_refresh_summary',
      'target_price_currency',
      'is_plausible_target_price',
      'is_probable_year_or_metadata_number',
      'target_price_context_source_type',
      'target_price_result',
      'filter_target_price_outliers'
    )
  },
  @{
    Path = "tools\check_public_ir_sec_store.py"
    Snippets = @(
      'is_public_ir_sec',
      'source_url_processing',
      'load_rag_paths',
      'expected_source_type',
      'is_recommendation_usable',
      'source_provider 누락',
      'source_type 분류 확인 필요',
      'RAG 색인 누락',
      '추천 가산 가능',
      '--require-any',
      'URL-only 항목 needs_body_copy 누락',
      '공개 IR/SEC 저장 품질 상태 정상'
    )
  },
  @{
    Path = "tools\check_storage_quality_store.py"
    Snippets = @(
      'BODY_TAGS',
      'OCR_MARKERS',
      '--strict',
      '오프라인 저장 품질 상태 정상'
    )
  },
  @{
    Path = "tools\check_portfolio_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'DEFAULT_EXPECTED',
      '--forbid-zero',
      '--expected-holdings-count',
      '--max-holdings',
      '보유 종목 수 불일치',
      '보유 종목 수 상한 초과',
      '--allow-cash',
      '--max-price-age-hours',
      '--max-portfolio-age-hours',
      '--max-sync-age-hours',
      '--weight-tolerance',
      '--calculation-relative-tolerance',
      '평가금액 계산 불일치',
      '해외 평가/투자금 환율 불일치',
      '수익률 계산 불일치',
      '포트폴리오 updated_at 오래됨/누락',
      '포트폴리오 비중 합계 불일치',
      '수량 동기화 확인 시각 오래됨/누락',
      '예수금/CASH 항목 혼입',
      '해외/수동 수량 보호 상태 누락',
      '포트폴리오 총액 불일치',
      '포트폴리오 저장 수량 상태 정상'
    )
  },
  @{
    Path = "tools\check_all_portfolio_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'CASH_TICKERS',
      '--forbid-zero',
      '--allow-cash',
      '--require-overseas-protection',
      '--max-price-age-hours',
      '--max-sync-age-hours',
      '--max-portfolio-age-hours',
      '--stale-warning-age-hours',
      '가격 확인 시각 오래됨/누락',
      '수량 동기화 확인 시각 오래됨/누락',
      '갱신 권고',
      '해외/수동 수량 보호 상태 누락',
      '해외 보호',
      'holding_count 불일치',
      '중복 보유 종목',
      '수량 0 종목 잔존',
      '예수금/CASH 항목 혼입',
      '포트폴리오 총액 불일치',
      '전체 포트폴리오 저장 구조 상태 정상'
    )
  },
  @{
    Path = "tools\refresh_portfolio_prices.py"
    Snippets = @(
      'reconciled_refresh',
      'parse_timestamp',
      'reconciled_after_error',
      'refresh_warning',
      'updated_at',
      'persist_refresh=true'
    )
  },
  @{
    Path = "tools\refresh_portfolio_prices.ps1"
    Snippets = @(
      'Find-ReconciledRefresh',
      'reconciled_after_error',
      'refresh_warning',
      '[datetimeoffset]::UtcNow',
      'persist_refresh=true'
    )
  },
  @{
    Path = "tools\check_research_source_store.py"
    Snippets = @(
      'SYSTEM_DIR',
      'ticker_registry_source_status.json',
      '--min-kcif-reports',
      '--min-regional-provider-count',
      'metadata_policy_ok',
      'rows_from_mapping_or_list',
      'missing_storage_files',
      'naver_pdf_import_failure_rows',
      '네이버 PDF 추출 런타임 실패 메모 잔존',
      '네이버 리서치 저장 파일 누락',
      '신한 리서치 저장 파일 누락',
      '--min-naver-reports',
      '--min-shinhan-reports',
      '--min-market-journal-entries',
      '--max-naver-missing-storage',
      '--max-market-journal-attempt-age-hours',
      '--max-dossier-queue-age-hours',
      'naver_market_close_journal_state.json',
      'telegram_market_close_journal_state.json',
      'research_automation_status.json',
      '리서치 자동화 상태',
      '리서치 자동화 저장 결과 확인 필요',
      '리서치 자동화 실패 건 존재',
      '리서치 자동화 RAG 연결 결과 부족',
      '리서치 자동화 뉴스 미승격 항목 존재',
      '리서치 자동화 Dossier 갱신',
      '마감 시황 자동 시도',
      '텔레그램 미국 시장일지 자동 시도',
      '자동 마감 시황 시장일지 출처 메타데이터 누락',
      '지역/중국/대외 소스 제공자 누락',
      '네이버 리서치',
      '신한 리서치',
      '마감 시황 시장일지',
      'CSF=',
      '리서치 소스 저장 상태 정상'
    )
  },
  @{
    Path = "backend\research_os\recent_activity.py"
    Snippets = @(
      'compact_recent_dart_entry',
      'dedupe_recent_activity_items',
      'annotate_recent_weekly_navigation_hints',
      'annotate_recent_weekly_recommendation_links',
      'build_recent_weekly_category_groups'
    )
  },
  @{
    Path = "tools\check_recent_weekly_brief.py"
    Snippets = @(
      'DEFAULT_MANIFEST',
      'DEFAULT_PORTFOLIOS',
      'DEFAULT_INTERESTS',
      'DEFAULT_RECOMMENDATIONS',
      'build_target_terms',
      'latest_recommendation_records',
      'recommendation_path_index',
      '--min-linked-recent-items',
      '최근 1주 자료/추천 근거 연결 상태 정상'
    )
  },
  @{
    Path = "tools\check_daily_recommendation_citations.py"
    Snippets = @(
      'DEFAULT_STORE',
      'RAG_REPORT_TYPE_PRIORITY',
      '--write-back',
      '--strict',
      'evidence_documents',
      '매일 추천 RAG 근거 문서 연결 정상'
    )
  },
  @{
    Path = "tools\check_daily_recommendations_store.py"
    Snippets = @(
      'DEFAULT_STORE',
      'DEFAULT_STATE',
      'EXPECTED_MILESTONE_DAYS',
      'EXPECTED_MILESTONES',
      'EXPECTED_STATE_STATUSES',
      'MARKET_ORDER',
      'EXPECTED_MARKET_RANKS',
      'LOCAL_TIMEZONE',
      'Asia/Seoul',
      'local_today',
      '--daily-time',
      '07:00',
      'time(hour=7)',
      '--expected-latest-count',
      '--max-latest-age-days',
      '최신 추천일 오래됨',
      '추천 수 불일치',
      '추천 수 불일치: {latest_by_market',
      'validate_all_date_rank_integrity',
      '--skip-all-date-integrity',
      '추천 순위 불일치',
      '일자별 추천 티커 중복',
      'validate_tracking_milestones',
      'nearest_milestone_label',
      'REQUIRED_EVIDENCE_CATEGORIES',
      'evidence_category_names',
      '근거 분산 부족',
      '목표일 불일치',
      '다음 추적',
      '--state',
      '스케줄 상태',
      '마지막 실행일 불일치',
      '--require-milestones',
      '--require-quality',
      '점수 설명 누락',
      'validate_score_evidence_alignment',
      'validate_investment_direction_profile',
      '투자 방향 프로필 저장 누락',
      '투자 방향 점수와 프로필 테마 불일치',
      '투자 방향 프로필 가산점 불일치',
      'component_points_sum',
      '최근 공시 점수와 근거 문구 불일치',
      '공개 IR/SEC 점수와 근거 문구 불일치',
      '점수 합계 불일치',
      '기준가 조회일 불일치 또는 누락',
      '최신 추천 티커 중복',
      '해외 종목 환율 추적 플래그 누락',
      '매일 추천 저장 상태 정상'
    )
  },
  @{
    Path = "tools\export_openclaw_investment_context.py"
    Snippets = @(
      'openclaw_investment_research_context',
      'raw_tokens_excluded',
      'investment_research_context.json',
      'investment_research_context.md',
      'openclaw_bridge_manifest.json',
      'investment_research_openclaw_bridge_v1',
      'read_order',
      '/api/v1/system/health',
      'build_recommendation_state',
      'build_news_state',
      'build_nps_state',
      'build_firecrawl_state',
      'enabled_default',
      'dry_run_default',
      'strict_refresh_command',
      'completion_audit_command',
      'final_completion_audit_command',
      'status_summary_command',
      'offline_readiness_command',
      'status_file',
      'completion_report',
      'completion_report_sha256',
      'completion_report_file',
      'completion_report_json_file',
      'completion_report_json',
      'show_openclaw_bridge_status.py --json',
      'restricted_actions'
    )
  },
  @{
    Path = "tools\check_openclaw_investment_context.py"
    Snippets = @(
      'DEFAULT_OPENCLAW_DIR',
      'SECRET_PATTERNS',
      'validate_bundle',
      'raw token exclusion flag must be true',
      'KR/US recommendation counts are incomplete',
      'Firecrawl safety defaults must remain enabled=false and dry_run=true',
      'OpenClaw usage must point to bridge_status.json',
      'OpenClaw usage must include final completion hash audit command',
      'OpenClaw usage must include status summary command',
      'OpenClaw usage must include offline readiness command',
      'openclaw_bridge_manifest.json',
      'strict_refresh_command',
      'completion_audit_command',
      'final_completion_audit_command',
      'status_summary_command',
      'completion_report_file',
      'completion_report_json_file',
      'OpenClaw bridge manifest completion_report_json_file mismatch',
      'OpenClaw usage must point to completion report JSON',
      'offline_readiness_command',
      'show_openclaw_bridge_status.py --json',
      'openclaw_bridge_completion_report.json',
      'OpenClaw bridge manifest schema mismatch',
      'OpenClaw bridge manifest read_order mismatch',
      'bridge status read_order mismatch',
      'bridge_status.json',
      'validate_no_secret_like_content(status_path)',
      'source_git_commit',
      'source_git_dirty',
      'startup_notes_updated',
      'completion_report_markdown',
      'operational_commands',
      'file_sha256',
      'bridge status file_sha256 mismatch',
      'bridge status operational command mismatch',
      'OpenClaw completion report hash target missing',
      'OpenClaw bridge README is missing source git',
      'OpenClaw bridge README status summary mismatch',
      'OpenClaw bridge README is missing latest recommendation',
      'OpenClaw bridge README is missing manifest command',
      'secrets_excluded'
    )
  },
  @{
    Path = "tools\check_openclaw_bridge_completion.py"
    Snippets = @(
      'openclaw_bridge_completion',
      'validate_bridge_status',
      'source_git_commit',
      'source_git_dirty',
      'validate_openclaw_workspace',
      'operational_commands',
      'final_completion_audit',
      'Operational Commands',
      'Read Order',
      'Read order:',
      'file_sha256',
      'completion_report_sha256',
      'require_report_hashes',
      '--require-report-hashes',
      'bridge status missing completion_report_sha256',
      'bridge status file_sha256 mismatch',
      'bridge status completion_report_sha256 mismatch',
      'completion report hashes match completion report files',
      'source git must be synced with upstream',
      'openclaw_bridge_completion_report.json',
      'openclaw_bridge_completion_report.md',
      'sync_openclaw_investment_context.ps1 -RequireCompletionAudit',
      'check_openclaw_bridge_completion.py --max-age-hours 24',
      'check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes',
      'show_openclaw_bridge_status.py --json',
      'check_offline_readiness.py --json',
      'OpenClaw startup notes point to bridge files, status summary, final audit command, today answer readiness, answer quality smokes, question read-order smoke, answer sample smoke, actual answer audit, WSL PA answer context, fresh bootstrap check, and current source git'
    )
  },
  @{
    Path = "tools\sync_openclaw_investment_context.ps1"
    Snippets = @(
      'OpenClawWorkspace',
      'MaxAgeHours',
      'SkipValidation',
      'RequireCompletionAudit',
      '[Console]::OutputEncoding',
      'PYTHONIOENCODING = "utf-8"',
      'PYTHONUTF8 = "1"',
      'Set-OpenClawBridgeNoteSection',
      'investment-research-os-bridge:start',
      'export_openclaw_investment_context.py',
      'check_openclaw_investment_context.py',
      'check_openclaw_bridge_completion.py',
      'show_openclaw_bridge_status.py',
      'investment_research_context.json',
      'investment_research_context.md',
      'openclaw_bridge_manifest.json',
      'openclaw_bridge_completion_report.json',
      'openclaw_bridge_completion_report.md',
      'bridge_status.json',
      'read_order',
      'Read order:',
      'context generated at',
      'latest recommendation date',
      'latest market counts',
      'latest_recommendations',
      '$latestRecommendationReadmeLines',
      '- latest recommendations:',
      'telegram favorite saved',
      'core file SHA256 hashes',
      'completion_report_sha256',
      'Completion report hashes',
      'final strict refresh',
      'completion audit',
      'final completion audit',
      'final_completion_audit',
      'status summary',
      'status_summary',
      'offline_readiness',
      'source_git_commit',
      'source_git_dirty',
      'startup_notes_updated',
      'completion_report_markdown',
      'operational_commands',
      'file_sha256',
      'secrets_excluded',
      'Copy-Item -Force',
      '--write-report',
      'OpenClaw completion audit skipped because source git worktree is dirty.',
      'OpenClaw final context validation failed',
      'OpenClaw final completion audit failed',
      'OpenClaw status summary failed',
      'show_openclaw_bridge_status.py --json',
      '--openclaw-dir $targetDir --json',
      '--require-report-hashes',
      '--source-dir $sourceDir --openclaw-dir $targetDir --max-age-hours $MaxAgeHours',
      'account-auth material are excluded'
    )
  },
  @{
    Path = "docs\openclaw-investment-research-bridge.md"
    Snippets = @(
      'openclaw_bridge_manifest.json',
      'bridge_status.json',
      '안전 갱신 명령',
      '최종 엄격 갱신 명령',
      '완료 감사 명령',
      '최종 완료 해시 감사 명령',
      '운영 명령 묶음',
      '첫 읽기 순서',
      'Read order:',
      'data/investment_research/openclaw_bridge_completion_report.json',
      '최신성 기준 시간',
      '핵심 파일 SHA256',
      '완료 리포트 SHA256',
      '완료 리포트 Markdown/JSON 파일명',
      'read_order',
      '컨텍스트 생성 시각',
      '전체 오프라인 준비도 명령',
      '상태 요약 명령',
      'show_openclaw_bridge_status.py --json',
      '시작 노트가 현재 source git 커밋',
      '최종 완료 해시 감사 명령',
      '매니페스트 명령과 일치',
      '민감정보 제외',
      '실거래 주문'
    )
  },
  @{
    Path = "tools\check_openclaw_bridge_completion.py"
    Snippets = @(
      '## Latest Recommendations',
      'latest_recommendations',
      'baseline_price',
      'OpenClaw Investment Research Bridge Completion Report'
    )
  },
  @{
    Path = "tools\show_openclaw_bridge_status.py"
    Snippets = @(
      'show_openclaw_bridge_status',
      'build_status_summary',
      'bridge_status.json',
      'openclaw_bridge_manifest.json',
      'investment_research_context.json',
      'openclaw_bridge_completion_report.json',
      'read_order_files_present',
      'latest_recommendation_date',
      'latest_recommendations',
      'summarize_latest_recommendations',
      'latest_recommendations count mismatch',
      'telegram_saved_count',
      'final_completion_audit',
      '--json'
    )
  },
  @{
    Path = "tools\check_openclaw_consumer_smoke.py"
    Snippets = @(
      'OpenClaw consumer smoke',
      'EXPECTED_READ_ORDER',
      'bridge_status.json',
      'openclaw_bridge_manifest.json',
      'investment_research_context.md',
      'investment_research_context.json',
      'openclaw_bridge_completion_report.md',
      'openclaw_bridge_completion_report.json',
      'completion_report_sha256',
      'latest_recommendation_count',
      'latest_recommendations',
      'sensitive_markers_checked',
      '--expected-latest-count',
      '--json'
    )
  },
  @{
    Path = "tools\show_dev_server_ports.ps1"
    Snippets = @(
      'Get-Command netstat',
      '$netstatCommand',
      '[Console]::OutputEncoding',
      'return @($listeners | Sort-Object Address, Port -Unique)',
      'Port conflicts detected',
      '예약 포트 충돌 없음'
    )
  },
  @{
    Path = "tools\verify_mobile_stack.ps1"
    Snippets = @(
      '$SkipPortRegistryCheck',
      '예약 포트 레지스트리 점검',
      'show_dev_server_ports.ps1',
      '-OnlyConflicts',
      '$LASTEXITCODE',
      'npm run typecheck',
      '$global:LASTEXITCODE = 0',
      'assert_mobile_testids.ps1',
      'assert_dev_scripts_contract.ps1',
      'npx expo export',
      'Remove-SafeDirectory'
    )
  }
)

$missing = @()
foreach ($contract in $contracts) {
  $path = Join-Path $ProjectRootPath $contract.Path
  if (-not (Test-Path -LiteralPath $path)) {
    $missing += "$($contract.Path): 파일 없음"
    continue
  }

  $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
  foreach ($snippet in $contract.Snippets) {
    if (-not $content.Contains($snippet)) {
      $missing += "$($contract.Path): $snippet"
    }
  }

  if ($contract.Path.EndsWith(".ps1")) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseInput(
      $content,
      [ref]$tokens,
      [ref]$parseErrors
    ) | Out-Null
    foreach ($parseError in @($parseErrors)) {
      $missing += "$($contract.Path): PowerShell syntax - $($parseError.Message)"
    }
  }
}

if ($missing.Count -gt 0) {
  $message = "개발 스크립트 계약 검증 실패:`n" + ($missing -join "`n")
  throw $message
}

Write-Host "OK 개발 스크립트 계약 검증 통과"
