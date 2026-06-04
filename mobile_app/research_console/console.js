import {
  setApiBaseUrl,
  fetchDataProviderStatus,
  fetchCodeKnowledgeGraph,
  fetchOcrStatus,
  fetchDartFilingWatchStatus,
  refreshDartFilingWatch,
  reportBackendHealthAlert,
  fetchTickerDashboard,
  fetchResearchManifest,
  fetchResearchMemoryFile,
  fetchResearchMemoryFiles,
  archiveResearchMemoryFile,
  archiveLegacyResearchMemoryFiles,
  supplementResearchMemoryFile,
  backfillRagMemoryDocuments,
  reprocessResearchMemoryOcr,
  synthesizeDossier,
  runResearchAutomation,
  fetchResearchAutomationStatus,
  runStorageDuplicateReview,
  runDedupedDossierRefresh,
  fetchDailyBriefing,
  searchAllRagMemoryDocuments,
  searchRagMemoryDocuments,
  synthesizeRagSearchResults,
  fetchTickerProfile,
  fetchTickerDiagnostics,
  fetchTickerRegistryCache,
  fetchLlmBridgeStorageStatus,
  fetchLatestDataSnapshot,
  verifyTickerSymbol,
  deleteTickerRegistryCacheEntry,
  runCollaborativeTeamReport,
  runSmartTradeSetup,
  runNaverChartAnalysis,
  runEarningsReactionAnalyzer,
  runSectorOpportunityFinder,
  runEarningsFilingNoteWorkflow,
  runGpLpStagingWorkflow,
  runLongTermCompounderFinder,
  autoCaptureResearchItem,
  previewSourceUrl,
  fetchNewsInbox,
  fetchStorageQualityDashboard,
  fetchKcifReportsWatch,
  refreshKcifReportsWatch,
  fetchRegionalBusinessSourcesWatch,
  refreshRegionalBusinessSourcesWatch,
  ingestNewsInbox,
  fetchDailyRecommendationsStatus,
  fetchRecentWeeklyResearchBrief,
  fetchPublicIrSecStatus,
  collectPublicIrSec,
  fetchInvestmentCalendar,
  runDailyRecommendations,
  trackDailyRecommendations,
  promoteNewsInboxItem,
  updateNewsInboxItem,
  runPortfolioRiskScan,
  runReinforcementPortfolioOptimizer,
  fetchPortfolios,
  fetchPortfolio,
  fetchPortfolioIntelligentTable,
  fetchPortfolioPerformance,
  fetchTargetConsensusScan,
  fetchPortfolioNpsFlow,
  fetchTickerNpsFlow,
  fetchPortfolioConnectivity,
  fetchPortfolioAnalysisStatus,
  fetchPortfolioTeamReportQueue,
  importPortfolioFile,
  savePortfolio,
  syncKiwoomDomesticPortfolio,
  previewKiwoomDomesticPortfolioSync,
  fetchPortfolioSyncHistory,
  deletePortfolio,
  fetchInterests,
  saveInterests,
  addInterestTicker,
  addInterestSector,
  fetchInterestAutomationBoard,
  fetchMarketCloseJournal,
  fetchNaverResearchStatus,
  repairNaverResearchCache,
  refreshNaverMarketCloseJournal,
  fetchNaverMarketCloseTaskStatus,
  fetchCustomsTradeSnapshot,
  saveMarketCloseReview,
  assessResearchChecklist,
  exportResultXlsx,
} from "./api.js?v=cdb888f10fb1";

const elements = {
  apiBaseUrl: document.querySelector("#apiBaseUrl"),
  accessToken: document.querySelector("#accessToken"),
  backendStatus: document.querySelector("#backendStatus"),
  providerStatus: document.querySelector("#providerStatus"),
  manifestStatus: document.querySelector("#manifestStatus"),
  output: document.querySelector("#output"),
  outputPanel: document.querySelector(".output-panel"),
  outputStatus: document.querySelector("#outputStatus"),
  actionFeedback: document.querySelector("#actionFeedback"),
  statusButton: document.querySelector("#statusButton"),
  clearOutput: document.querySelector("#clearOutput"),
  exportResultExcel: document.querySelector("#exportResultExcel"),
  dashboardForm: document.querySelector("#dashboardForm"),
  dashboardCards: document.querySelector("#dashboardCards"),
  teamForm: document.querySelector("#teamForm"),
  tradeForm: document.querySelector("#tradeForm"),
  chartForm: document.querySelector("#chartForm"),
  chartVisualization: document.querySelector("#chartVisualization"),
  tradePortfolioSelect: document.querySelector("#tradePortfolioSelect"),
  earningsForm: document.querySelector("#earningsForm"),
  macroForm: document.querySelector("#macroForm"),
  kcifReportsWatchButton: document.querySelector("#kcifReportsWatchButton"),
  kcifReportsRefreshButton: document.querySelector("#kcifReportsRefreshButton"),
  regionalBusinessSourcesWatchButton: document.querySelector("#regionalBusinessSourcesWatchButton"),
  regionalBusinessSourcesRefreshButton: document.querySelector("#regionalBusinessSourcesRefreshButton"),
  sectorForm: document.querySelector("#sectorForm"),
  compounderForm: document.querySelector("#compounderForm"),
  captureForm: document.querySelector("#captureForm"),
  captureUrlPreviewButton: document.querySelector("#captureUrlPreviewButton"),
  captureFileStatus: document.querySelector("#captureFileStatus"),
  newsForm: document.querySelector("#newsForm"),
  newsUrlPreviewButton: document.querySelector("#newsUrlPreviewButton"),
  newsInboxButton: document.querySelector("#newsInboxButton"),
  newsPromoteLatestButton: document.querySelector("#newsPromoteLatestButton"),
  newsInboxFilter: document.querySelector("#newsInboxFilter"),
  newsInboxList: document.querySelector("#newsInboxList"),
  llmPromptForm: document.querySelector("#llmPromptForm"),
  llmPromptOutput: document.querySelector("#llmPromptOutput"),
  copyLlmPromptButton: document.querySelector("#copyLlmPromptButton"),
  llmResultForm: document.querySelector("#llmResultForm"),
  llmStorageStatusButton: document.querySelector("#llmStorageStatusButton"),
  earningsFilingNoteForm: document.querySelector("#earningsFilingNoteForm"),
  gpLpStagingForm: document.querySelector("#gpLpStagingForm"),
  marketCloseForm: document.querySelector("#marketCloseForm"),
  marketCloseUrlPreviewButton: document.querySelector("#marketCloseUrlPreviewButton"),
  marketCloseHistoryButton: document.querySelector("#marketCloseHistoryButton"),
  customsTradeSnapshotButton: document.querySelector("#customsTradeSnapshotButton"),
  portfolioForm: document.querySelector("#portfolioForm"),
  portfolioSelect: document.querySelector("#portfolioSelect"),
  portfolioLoadButton: document.querySelector("#portfolioLoadButton"),
  portfolioKiwoomSyncButton: document.querySelector("#portfolioKiwoomSyncButton"),
  portfolioKiwoomApplyButton: document.querySelector("#portfolioKiwoomApplyButton"),
  portfolioKiwoomCancelButton: document.querySelector("#portfolioKiwoomCancelButton"),
  portfolioSyncHistoryButton: document.querySelector("#portfolioSyncHistoryButton"),
  portfolioConnectivityButton: document.querySelector("#portfolioConnectivityButton"),
  portfolioNpsFlowButton: document.querySelector("#portfolioNpsFlowButton"),
  portfolioAnalysisStatusButton: document.querySelector("#portfolioAnalysisStatusButton"),
  portfolioTeamQueueButton: document.querySelector("#portfolioTeamQueueButton"),
  portfolioRunTopTeamButton: document.querySelector("#portfolioRunTopTeamButton"),
  portfolioPerformanceButton: document.querySelector("#portfolioPerformanceButton"),
  portfolioQuickRiskButton: document.querySelector("#portfolioQuickRiskButton"),
  portfolioSaveButton: document.querySelector("#portfolioSaveButton"),
  portfolioDeleteButton: document.querySelector("#portfolioDeleteButton"),
  portfolioOptimizeButton: document.querySelector("#portfolioOptimizeButton"),
  policyObjective: document.querySelector("#policyObjective"),
  policyRiskProfile: document.querySelector("#policyRiskProfile"),
  policyLearningHorizonDays: document.querySelector("#policyLearningHorizonDays"),
  policyMarketState: document.querySelector("#policyMarketState"),
  policySaveResult: document.querySelector("#policySaveResult"),
  portfolioImportFile: document.querySelector("#portfolioImportFile"),
  portfolioImportPickButton: document.querySelector("#portfolioImportPickButton"),
  portfolioImportButton: document.querySelector("#portfolioImportButton"),
  portfolioImportStatus: document.querySelector("#portfolioImportStatus"),
  portfolioExecutionText: document.querySelector("#portfolioExecutionText"),
  portfolioApplyExecutionButton: document.querySelector("#portfolioApplyExecutionButton"),
  portfolioFilter: document.querySelector("#portfolioFilter"),
  portfolioSort: document.querySelector("#portfolioSort"),
  holdingsEditor: document.querySelector("#holdingsEditor"),
  portfolioLoadedAt: document.querySelector("#portfolioLoadedAt"),
  portfolioSyncOverview: document.querySelector("#portfolioSyncOverview"),
  portfolioSmartRefreshButton: document.querySelector("#portfolioSmartRefreshButton"),
  portfolioConsensusScanButton: document.querySelector("#portfolioConsensusScanButton"),
  portfolioSmartChart: document.querySelector("#portfolioSmartChart"),
  portfolioSmartTable: document.querySelector("#portfolioSmartTable"),
  portfolioConsensusTable: document.querySelector("#portfolioConsensusTable"),
  addHoldingButton: document.querySelector("#addHoldingButton"),
  addCashButton: document.querySelector("#addCashButton"),
  recalculatePortfolioButton: document.querySelector("#recalculatePortfolioButton"),
  portfolioSummary: document.querySelector("#portfolioSummary"),
  portfolioAnalysisOverview: document.querySelector("#portfolioAnalysisOverview"),
  portfolioPerformanceOverview: document.querySelector("#portfolioPerformanceOverview"),
  interestsForm: document.querySelector("#interestsForm"),
  interestsSummary: document.querySelector("#interestsSummary"),
  interestsLoadButton: document.querySelector("#interestsLoadButton"),
  interestAutomationButton: document.querySelector("#interestAutomationButton"),
  interestTickerDraft: document.querySelector("#interestTickerDraft"),
  interestTickerEditor: document.querySelector("#interestTickerEditor"),
  addInterestTickerButton: document.querySelector("#addInterestTickerButton"),
  interestSectorDraft: document.querySelector("#interestSectorDraft"),
  interestSectorEditor: document.querySelector("#interestSectorEditor"),
  addInterestSectorButton: document.querySelector("#addInterestSectorButton"),
  checklistForm: document.querySelector("#checklistForm"),
  checklistProgressText: document.querySelector("#checklistProgressText"),
  checklistProgressPercent: document.querySelector("#checklistProgressPercent"),
  checklistProgressBar: document.querySelector("#checklistProgressBar"),
  memoryForm: document.querySelector("#memoryForm"),
  memoryList: document.querySelector("#memoryList"),
  memoryPreview: document.querySelector("#memoryPreview"),
  memoryPreviewMeta: document.querySelector("#memoryPreviewMeta"),
  memoryPreviewTitle: document.querySelector("#memoryPreviewTitle"),
  memoryPreviewContent: document.querySelector("#memoryPreviewContent"),
  memorySupplementForm: document.querySelector("#memorySupplementForm"),
  memorySupplementHelp: document.querySelector("#memorySupplementHelp"),
  memorySupplementBody: document.querySelector("#memorySupplementBody"),
  memorySupplementNote: document.querySelector("#memorySupplementNote"),
  manifestButton: document.querySelector("#manifestButton"),
  ragSearchButton: document.querySelector("#ragSearchButton"),
  ragNaturalSearchButton: document.querySelector("#ragNaturalSearchButton"),
  ragSynthesisButton: document.querySelector("#ragSynthesisButton"),
  dossierButton: document.querySelector("#dossierButton"),
  dailyBriefButton: document.querySelector("#dailyBriefButton"),
  researchAutomationButton: document.querySelector("#researchAutomationButton"),
  todayResearchUpdateButton: document.querySelector("#todayResearchUpdateButton"),
  naverResearchStatusButton: document.querySelector("#naverResearchStatusButton"),
  naverResearchRepairButton: document.querySelector("#naverResearchRepairButton"),
  naverMarketJournalButton: document.querySelector("#naverMarketJournalButton"),
  dailyRecommendationsButton: document.querySelector("#dailyRecommendationsButton"),
  dailyRecommendationsQuickButton: document.querySelector("#dailyRecommendationsQuickButton"),
  recentWeeklyBriefButton: document.querySelector("#recentWeeklyBriefButton"),
  dailyRecommendationsStatusButton: document.querySelector("#dailyRecommendationsStatusButton"),
  dailyRecommendationsStatusQuickButton: document.querySelector("#dailyRecommendationsStatusQuickButton"),
  dailyRecommendationCards: document.querySelector("#dailyRecommendationCards"),
  investmentCalendarTitle: document.querySelector("#investmentCalendarTitle"),
  investmentCalendarMeta: document.querySelector("#investmentCalendarMeta"),
  investmentCalendarMonthly: document.querySelector("#investmentCalendarMonthly"),
  investmentCalendarWeekly: document.querySelector("#investmentCalendarWeekly"),
  investmentCalendarRefreshButton: document.querySelector("#investmentCalendarRefreshButton"),
  researchAutomationStatusButton: document.querySelector("#researchAutomationStatusButton"),
  codeKnowledgeGraphButton: document.querySelector("#codeKnowledgeGraphButton"),
  ragBackfillButton: document.querySelector("#ragBackfillButton"),
  ocrReprocessButton: document.querySelector("#ocrReprocessButton"),
  storageCleanupButton: document.querySelector("#storageCleanupButton"),
  dedupedDossierRefreshButton: document.querySelector("#dedupedDossierRefreshButton"),
  tickerCacheButton: document.querySelector("#tickerCacheButton"),
  publicIrSecUrl: document.querySelector('[name="publicIrSecUrl"]'),
  publicIrSecCollectButton: document.querySelector("#publicIrSecCollectButton"),
  publicIrSecStatusButton: document.querySelector("#publicIrSecStatusButton"),
  tickerCacheList: document.querySelector("#tickerCacheList"),
  dashboardTickerSelect: document.querySelector("#dashboardTickerSelect"),
  dashboardTickerOptions: document.querySelector("#dashboardTickerOptions"),
  dashboardTickerQuickList: document.querySelector("#dashboardTickerQuickList"),
};

const CHECKLIST_TOTAL = 16;
const DEFAULT_TICKER = "";
const DEFAULT_TICKER_DISPLAY = "";
const DASHBOARD_RECENT_TICKERS_STORAGE_KEY = "research_os_recent_dashboard_tickers";
const KOREAN_TICKER_DISPLAY_NAMES = {
  "003230": "삼양식품",
  "018260": "삼성에스디에스",
  "071050": "한국금융지주",
  "189330": "씨이랩",
  "327260": "RF머트리얼즈",
  "043260": "성호전자",
  "0117V0": "TIGER 코리아AI전력기기TOP3플러스 ETF",
  "035510": "신세계I&C",
  "036890": "진성티이씨",
  "089030": "테크윙",
  "112610": "씨에스윈드",
  "377300": "카카오페이",
  "415640": "KB발해인프라",
  "253450": "스튜디오드래곤",
  "360750": "TIGER 미국S&P500 ETF",
  "395160": "KODEX AI반도체 ETF",
  "404650": "SOL KRX기후변화솔루션 ETF",
  "414780": "TIGER 차이나과창판STAR50(합성) ETF",
  "453810": "KIWOOM 인도Nifty50(합성) ETF",
  "361610": "SK아이이테크놀로지",
};
let activeTicker = DEFAULT_TICKER;
let lastDashboard = null;
let lastConfirmedTicker = DEFAULT_TICKER;
let lastTickerVerification = null;
let lastTickerProfile = null;
let savedPortfolios = [];
let activePortfolioSnapshot = null;
let pendingKiwoomDomesticSync = null;
let portfolioSmartRows = [];
let portfolioSmartSort = { key: "market_value", direction: "desc" };
let consensusScanRows = [];
let consensusScanSort = { key: "target_upside", direction: "desc" };
let lastPortfolioAnalysisStatus = null;
let lastPortfolioTeamReportQueue = null;
let lastInterestList = null;
let lastInterestAutomationBoard = null;
let lastTodayResearchUpdate = null;
let activeMemoryPreviewFile = null;
let dashboardTickerGroupsExpanded = false;
let dashboardSyncTimer = null;
let dashboardRequestSeq = 0;
let outputLoadingTimer = null;
let outputStatusTimer = null;
let actionFeedbackTimer = null;
let actionFeedbackLastKey = "";
let actionFeedbackLastAt = 0;
const actionButtonDebounceUntil = new WeakMap();
let outputLoadingStartedAt = 0;
let outputLoadingFrame = 0;
let lastOutputRaw = "대기 중입니다.";
let lastRagSearchResult = null;
let ragTypeFilter = "all";
let ragTickerFilter = "all";
let ragQualityFilter = "all";
let ragSortMode = "relevance_desc";

let lastBackendHealthState = "unknown";
let lastBackendAlertAt = 0;

const BACKEND_ALERT_COOLDOWN_MS = 5 * 60 * 1000;
const TODAY_RESEARCH_UPDATE_STORAGE_KEY = "research_os_today_research_update";
const OUTPUT_HIGHLIGHT_RULES = [
  {
    className: "output-highlight-success",
    pattern: /(공식 인증|인증 완료|정상|성공|완료|강화|우수|긍정)/g,
  },
  {
    className: "output-highlight-warning",
    pattern: /(주의|확인 필요|경고|보류|혼합|중립|데이터 부족|부분 보강 필요|미등록|미입력|대기)/g,
  },
  {
    className: "output-highlight-danger",
    pattern: /(오류|실패|위험|손절|약화|미인증|불가|중단|연결 끊김)/g,
  },
  {
    className: "output-highlight-info",
    pattern: /(저장 데이터|저장 위치|저장 파일|RAG|Pulls|De-dupes|Embeds|Tags|Syntheses|Delivers|Dossier|공시|실적 발표일|다음 예정일|시장일지|티커|포트폴리오)/g,
  },
];
function token() {
  return elements.accessToken.value.trim();
}

function syncApiBaseUrl() {
  elements.apiBaseUrl.value = elements.apiBaseUrl.value.trim();
  setApiBaseUrl(elements.apiBaseUrl.value);
}

function renderPlainOutput(text) {
  elements.output.classList.add("plain-mode");
  elements.output.textContent = String(text ?? "");
}

function renderMarkdownOutput(markdown) {
  elements.output.classList.remove("plain-mode");
  elements.output.innerHTML = markdownToHtml(markdown);
}

function shouldShowCompletionBanner(value, options = {}) {
  if (options.skipCompletion || options.skipCompletionBanner) {
    return false;
  }
  if (options.completionMessage) {
    return true;
  }
  if (value && typeof value === "object") {
    return value.status !== "error";
  }
  const text = String(value ?? "").trim();
  if (!text || /중입니다|처리 중|대기 중|필요|오류/.test(text)) {
    return false;
  }
  return /(완료|저장|조회|생성|불러왔|계산|복사|삭제|추가|갱신|실행|적용|전환|반영)/.test(text);
}

function completionBannerText(value, options = {}) {
  if (options.completionMessage) {
    return options.completionMessage;
  }
  if (value && typeof value === "object") {
    const moduleLabel = completionModuleLabel(value.module || value.payload?.module || "");
    return moduleLabel ? `${moduleLabel} 실행이 완료되었습니다.` : "작업이 완료되었습니다.";
  }
  return "작업이 완료되었습니다.";
}

function completionModuleLabel(moduleName) {
  const labels = {
    research_quick_capture: "정보 입력 저장",
    research_memory_body_supplement: "본문 보강 저장",
    research_memory_archive: "저장 데이터 보관",
    market_close_review: "시장일지 저장",
    market_close_history: "시장일지 조회",
    portfolio_store: "포트폴리오 저장",
    portfolio_risk_scan: "포트폴리오 리스크 스캔",
    interest_list: "관심종목/섹터 저장",
    investor_research_checklist: "체크리스트 분석",
    collaborative_research_team: "팀 리포트",
    smart_trade_setup: "매매 전략",
    earnings_reaction: "실적 분석",
    sector_opportunity: "섹터/산업 리포트",
    long_term_compounder: "복리 성장주 발굴",
    naver_chart_analysis: "차트 분석",
    data_provider_snapshot: "최신 데이터 조회",
    ticker_dashboard: "대시보드 조회",
    dossier_synthesis: "Dossier 합성",
    rag_memory_search: "RAG 검색",
    rag_memory_global_search: "전체 저장 데이터 검색",
    rag_query_synthesis: "검색 결과 합성",
    daily_research_briefing: "일일 브리핑",
    news_inbox: "뉴스 인박스",
    news_inbox_list: "뉴스 인박스 조회",
    news_promotion: "뉴스 승격",
    research_automation_pipeline: "전체 자동화",
    today_research_update: "오늘 리서치 업데이트",
    korea_customs_trade_snapshot: "관세청 수출입 동향",
    korea_customs_trade_total_trend_status: "관세청 수출입총괄 진단",
    kcif_reports_watch: "KCIF 보고서 Watch",
    regional_business_sources_watch: "EMERiCs/CSF/KIEP 자료 Watch",
    earnings_filing_note: "모델 업데이트 노트",
    gp_lp_staging: "LP 보고 스테이징",
    source_url_preview: "웹 본문 미리보기",
    research_memory_ocr_reprocess: "OCR 재처리",
  };
  return labels[moduleName] || "";
}

function setOutput(value, options = {}) {
  lastOutputRaw = value;
  stopOutputLoading();
  const body = formatKoreanResult(value);
  const showCompletion = shouldShowCompletionBanner(value, options);
  if (showCompletion) {
    showOutputStatus("완료", "complete");
  }
  if (showCompletion) {
    renderMarkdownOutput(`**${completionBannerText(value, options)}**\n\n${body}`);
    return;
  }
  renderMarkdownOutput(body);
}

function setError(error) {
  lastOutputRaw = {
    status: "error",
    message: error?.message || String(error),
    generated_at: new Date().toISOString(),
  };
  stopOutputLoading();
  showOutputStatus("오류", "error", 5200);
  renderMarkdownOutput(
    [
      "**오류가 발생했습니다.**",
      "",
      `**원인:** ${error?.message || String(error)}`,
      "",
      "**확인할 것:**",
      "1. API Base가 `http://127.0.0.1:8001`인지 확인",
      "2. 백엔드 서버가 실행 중인지 확인",
      "3. Token이 `dev-local-token`인지 확인",
    ].join("\n")
  );
}

function highlightOutputKeywords(html) {
  return String(html)
    .split(/(<[^>]+>)/g)
    .map((part) => {
      if (!part || part.startsWith("<")) {
        return part;
      }
      return OUTPUT_HIGHLIGHT_RULES.reduce(
        (text, rule) =>
          text.replace(
            rule.pattern,
            (match) => `<span class="${rule.className}">${match}</span>`
          ),
        part
      );
    })
    .join("");
}

function renderInlineMarkdown(text) {
  const html = escapeHtml(text)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
  return highlightOutputKeywords(html);
}

async function notifyBackendHealthWarning(error, context = {}) {
  const now = Date.now();
  if (now - lastBackendAlertAt < BACKEND_ALERT_COOLDOWN_MS) {
    return;
  }
  lastBackendAlertAt = now;

  const apiBase = elements.apiBaseUrl.value.trim();
  const message = `리서치 OS 백엔드 연결 상태를 확인해야 합니다. ${
    error?.message || String(error) || "상태 확인 실패"
  }`;

  if (typeof window !== "undefined" && "Notification" in window) {
    try {
      if (Notification.permission === "default") {
        await Notification.requestPermission();
      }
      if (Notification.permission === "granted") {
        new Notification("리서치 OS 연결 경고", {
          body: message,
          tag: "research-os-backend-health",
        });
      }
    } catch (notificationError) {
      console.warn("브라우저 알림 처리 중 오류:", notificationError);
    }
  }

  await reportBackendHealthAlert(token(), {
    alert_type: "backend_status_warning",
    severity: "warning",
    source: context.source || "research_console_status_check",
    message,
    api_base: apiBase,
    client_timestamp: new Date().toISOString(),
  });
}

function markBackendHealthy() {
  lastBackendHealthState = "healthy";
}
function markdownToHtml(markdown) {
  const lines = String(markdown ?? "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let inCodeBlock = false;
  let codeLines = [];
  let listType = null;

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  const openList = (type) => {
    if (listType !== type) {
      closeList();
      html.push(`<${type}>`);
      listType = type;
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
        inCodeBlock = false;
      } else {
        closeList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (!trimmed) {
      closeList();
      html.push('<div class="markdown-gap"></div>');
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = Math.min(heading[1].length + 2, 5);
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const unordered = trimmed.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      openList("ul");
      html.push(`<li>${renderInlineMarkdown(unordered[1])}</li>`);
      continue;
    }

    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      openList("ol");
      html.push(`<li>${renderInlineMarkdown(ordered[1])}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }

  closeList();
  if (inCodeBlock) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  return html.join("");
}

function renderOutputLoadingFrame(title, steps) {
  const spinnerFrames = ["|", "/", "-", "\\"];
  const elapsedSeconds = Math.max(
    0,
    Math.floor((Date.now() - outputLoadingStartedAt) / 1000)
  );
  const stepIndex = Math.min(
    steps.length - 1,
    Math.floor(outputLoadingFrame / 3)
  );
  const currentStep = steps[stepIndex] || title;
  const completedSteps = steps.slice(0, stepIndex).map((step) => `완료: ${step}`);
  const waitingSteps = steps.slice(stepIndex + 1).map((step) => `대기: ${step}`);
  const spinner = spinnerFrames[outputLoadingFrame % spinnerFrames.length];
  renderPlainOutput([
    `${spinner} ${title}`,
    ``,
    `진행 중: ${currentStep}`,
    `경과 시간: ${elapsedSeconds}초`,
    ``,
    ...completedSteps,
    `진행: ${currentStep} ...`,
    ...waitingSteps,
    ``,
    `분석이 끝나면 이 창에 결과가 자동으로 표시됩니다.`,
  ].join("\n"));
  outputLoadingFrame += 1;
}

function startOutputLoading(title, steps = []) {
  stopOutputLoading();
  if (outputStatusTimer) {
    window.clearTimeout(outputStatusTimer);
    outputStatusTimer = null;
  }
  outputLoadingStartedAt = Date.now();
  outputLoadingFrame = 0;
  elements.outputPanel.classList.add("loading");
  elements.outputStatus.classList.remove("complete", "error", "pending");
  elements.outputStatus.hidden = false;
  elements.outputStatus.style.display = "inline-flex";
  elements.outputStatus.textContent = "처리 중";
  const normalizedSteps = steps.length ? steps : [title];
  renderOutputLoadingFrame(title, normalizedSteps);
  outputLoadingTimer = window.setInterval(() => {
    renderOutputLoadingFrame(title, normalizedSteps);
  }, 650);
}

function stopOutputLoading() {
  if (outputLoadingTimer) {
    window.clearInterval(outputLoadingTimer);
    outputLoadingTimer = null;
  }
  elements.outputPanel.classList.remove("loading");
  elements.outputStatus.hidden = true;
  elements.outputStatus.style.display = "none";
  elements.outputStatus.classList.remove("complete", "error", "pending");
}

function showOutputStatus(message, state = "complete", durationMs = 2600) {
  if (!elements.outputStatus) {
    return;
  }
  if (outputStatusTimer) {
    window.clearTimeout(outputStatusTimer);
    outputStatusTimer = null;
  }
  elements.outputPanel.classList.remove("loading");
  elements.outputStatus.classList.remove("complete", "error", "pending");
  elements.outputStatus.classList.add(state);
  elements.outputStatus.hidden = false;
  elements.outputStatus.style.display = "inline-flex";
  elements.outputStatus.textContent = message;
  outputStatusTimer = window.setTimeout(() => {
    elements.outputStatus.hidden = true;
    elements.outputStatus.style.display = "none";
    elements.outputStatus.classList.remove("complete", "error", "pending");
    outputStatusTimer = null;
  }, durationMs);
}

function actionLabelFromButton(button) {
  return String(button?.textContent || "작업").replace(/\s+/g, " ").trim() || "작업";
}

function showActionFeedback(message, durationMs = 5200) {
  if (!elements.actionFeedback) {
    return;
  }
  if (actionFeedbackTimer) {
    window.clearTimeout(actionFeedbackTimer);
    actionFeedbackTimer = null;
  }
  actionFeedbackLastKey = String(message || "");
  actionFeedbackLastAt = Date.now();
  elements.actionFeedback.hidden = false;
  elements.actionFeedback.textContent = `요청 접수: ${message}`;
  elements.actionFeedback.classList.remove("is-refreshing");
  void elements.actionFeedback.offsetWidth;
  elements.actionFeedback.classList.add("is-refreshing");
  actionFeedbackTimer = window.setTimeout(() => {
    elements.actionFeedback.hidden = true;
    elements.actionFeedback.textContent = "";
    elements.actionFeedback.classList.remove("is-refreshing");
    actionFeedbackTimer = null;
  }, durationMs);
}

function showActionAccepted(message) {
  showActionFeedback(message);
  showOutputStatus("요청 접수", "pending", 2400);
  renderPlainOutput(
    [
      `요청 접수: ${message}`,
      "",
      "작업이 시작됐습니다. 처리 상태와 결과가 이 창에 표시됩니다.",
    ].join("\n")
  );
}

function isDuplicateActionClick(button, message, debounceMs = 900) {
  const now = Date.now();
  const debounceUntil = actionButtonDebounceUntil.get(button) || 0;
  const feedbackKey = String(message || actionLabelFromButton(button));
  return (
    debounceUntil > now ||
    (feedbackKey === actionFeedbackLastKey && now - actionFeedbackLastAt < debounceMs)
  );
}

function blockDuplicateActionClick(event, button, message) {
  event?.preventDefault?.();
  event?.stopImmediatePropagation?.();
  event?.stopPropagation?.();
  showActionFeedback(`${actionLabelFromButton(button)} 요청이 이미 접수되어 처리 중입니다.`, 1800);
  brieflyMarkActionButton(button, 900, { force: true });
}

function registerActionClick(button, message, event = null, debounceMs = 900) {
  if (!button || button.disabled) {
    return false;
  }
  if (isDuplicateActionClick(button, message, debounceMs)) {
    blockDuplicateActionClick(event, button, message);
    return false;
  }
  showActionAccepted(message);
  brieflyMarkActionButton(button, debounceMs);
  return true;
}

function brieflyMarkActionButton(button, durationMs = 1200, options = {}) {
  if (!button || button.disabled) {
    return;
  }
  if (!options.force && button.classList.contains("is-busy")) {
    return;
  }
  button.classList.add("is-busy");
  button.setAttribute("aria-busy", "true");
  actionButtonDebounceUntil.set(button, Date.now() + durationMs);
  window.setTimeout(() => {
    button.classList.remove("is-busy");
    button.removeAttribute("aria-busy");
    actionButtonDebounceUntil.delete(button);
  }, durationMs);
}

function attachButtonActionFeedback(root, messages = {}) {
  if (!root) {
    return;
  }
  root.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest("button");
      if (!button || button.disabled || !root.contains(button)) {
        return;
      }
      const key = button.id || button.dataset.workflowAction || button.type || "";
      const message = messages[key] || `${actionLabelFromButton(button)} 작업을 시작했습니다.`;
      registerActionClick(button, message, event);
    },
    { capture: true }
  );
}

async function setTickerAwareError(error, ticker) {
  const normalizedTicker = normalizeTickerDraft(ticker);
  const message = error?.message || String(error);
  if (normalizedTicker && /티커|인증|422|공식/.test(message)) {
    try {
      const diagnostics = await fetchTickerDiagnostics(token(), normalizedTicker);
      if (diagnostics?.module === "ticker_diagnostics") {
        setOutput(diagnostics);
        return;
      }
    } catch (diagnosticError) {
      console.warn("티커 진단 조회 실패:", diagnosticError);
    }
  }
  setError(error);
}

async function runSecondaryRefresh(description, callback) {
  try {
    await callback();
  } catch (error) {
    console.warn(`${description} 실패:`, error);
    elements.backendStatus.textContent = "새로고침 확인 필요";
  }
}

function setTickerVerificationStatus(verification) {
  lastTickerVerification = verification;
  if (!verification) {
    elements.backendStatus.textContent = "티커 인증 실패";
    return;
  }
  if (verification.verified) {
    elements.backendStatus.textContent = `정상 · ${verification.official_symbol}`;
    return;
  }
  elements.backendStatus.textContent = "티커 미인증";
}

function setDashboardCards(html) {
  elements.dashboardCards.innerHTML = html;
}

function renderDashboardEmptyState() {
  setDashboardCards(`
    <div class="dashboard-actions">
      <button data-workflow-action="portfolio" type="button">포트폴리오</button>
      <button data-workflow-action="capture" type="button">정보 입력</button>
      <button data-workflow-action="chart" class="secondary" type="button">차트 분석</button>
      <button data-workflow-action="memory" class="secondary" type="button">저장 데이터</button>
    </div>
  `);
}

function activePanelId() {
  return document.querySelector(".panel.active")?.id || "";
}

function renderDashboardTickerPending(ticker) {
  const safeTicker = escapeHtml(ticker || "새 티커");
  setDashboardCards(`
    <div class="dashboard-empty-note">
      <strong>${safeTicker}</strong>
      <p>대시보드 조회, 최신 데이터 조회, 리포트 실행 중 필요한 작업을 선택하세요.</p>
    </div>
    <div class="dashboard-actions">
      <button data-workflow-action="dashboard-refresh" type="button">대시보드 새로고침</button>
      <button data-workflow-action="team" type="button">팀 리포트</button>
      <button data-workflow-action="chart" class="secondary" type="button">차트 분석</button>
      <button data-workflow-action="capture" type="button">정보 입력</button>
    </div>
  `);
}

function invalidateTickerDashboard(previousTicker, nextTicker) {
  if (previousTicker === nextTicker) {
    return;
  }
  if (!nextTicker) {
    lastDashboard = null;
    lastTickerVerification = null;
    lastTickerProfile = null;
    renderDashboardTickerPending("입력 대기");
    return;
  }
  if (lastDashboard?.ticker !== nextTicker) {
    lastDashboard = null;
    lastTickerVerification = null;
    lastTickerProfile = null;
    renderDashboardTickerPending(nextTicker);
  }
}

function scheduleDashboardSync(ticker) {
  window.clearTimeout(dashboardSyncTimer);
  const requestedTicker = normalizeTickerDraft(ticker);
  if (!requestedTicker || activePanelId() !== "dashboard") {
    return;
  }
  dashboardSyncTimer = window.setTimeout(async () => {
    const requestId = ++dashboardRequestSeq;
    try {
      await loadTickerDashboard(requestedTicker, { quiet: true, requestId });
    } catch (error) {
      if (requestId === dashboardRequestSeq) {
        await setTickerAwareError(error, requestedTicker);
      }
    }
  }, 700);
}

function formDataObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function isClickSmokeMode() {
  const smokeMode = new URLSearchParams(window.location.search).get("smoke") || "";
  return smokeMode === "clicks" || smokeMode.startsWith("clicks-");
}

function buildManualLlmPrompt(data) {
  const target = String(data.target || "").trim() || "티커 없는 시장/섹터/거시 자료";
  const provider = String(data.provider || "LLM").trim();
  const taskType = String(data.taskType || "종합 투자 분석").trim();
  const outputStyle = String(data.outputStyle || "요약+근거+다음 액션").trim();
  const sourceContext = String(data.sourceContext || "").trim();
  return [
    "당신은 기관급 투자 리서치 협업 분석가입니다.",
    "아래 입력 자료를 바탕으로 한국어로 분석해 주세요.",
    "",
    "중요 규칙:",
    "- 확인되지 않은 수치나 날짜는 추정하지 말고 `확인 필요`로 표시하세요.",
    "- 사실, 해석, 투자 논거 영향을 구분하세요.",
    "- 매수/매도 지시가 아니라 투자 리서치용 판단 근거로 작성하세요.",
    "- 기존 투자 논거를 강화/약화/혼합/중립 중 하나로 분류하고 이유를 짧게 설명하세요.",
    "- 티커가 명확하지 않으면 종목 자료로 단정하지 말고 시장/섹터/거시/정책/금리/수급/미분류 중 가장 적절히 분류하세요.",
    "",
    `대상: ${target}`,
    `사용 LLM: ${provider}`,
    `작업 유형: ${taskType}`,
    `희망 응답 형식: ${outputStyle}`,
    "",
    "응답 형식:",
    "1. 핵심 요약",
    "2. 자료 분류와 신뢰도",
    "3. 투자 논거 영향: 강화/약화/혼합/중립",
    "4. Bull/Base/Bear 시나리오",
    "5. 주요 리스크와 확인 필요 데이터",
    "6. 다음 액션",
    "7. 저장용 태그",
    "",
    "입력 자료:",
    sourceContext || "(여기에 사용자가 붙여넣은 자료가 없습니다. 대상과 작업 유형만 기준으로 확인 필요 항목을 정리하세요.)",
  ].join("\n");
}

function ensureLlmPromptPreview() {
  if (!elements.llmPromptForm || !elements.llmPromptOutput) {
    return "";
  }
  const prompt = buildManualLlmPrompt(formDataObject(elements.llmPromptForm));
  elements.llmPromptOutput.value = prompt;
  return prompt;
}

async function copyTextToClipboard(text) {
  if (!text) {
    throw new Error("복사할 프롬프트가 없습니다.");
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  elements.llmPromptOutput?.focus();
  elements.llmPromptOutput?.select();
  const copied = document.execCommand?.("copy");
  if (!copied) {
    throw new Error("브라우저 클립보드 복사 권한이 없어 직접 선택해 복사해야 합니다.");
  }
}

function parseJsonField(value, label) {
  try {
    const parsed = JSON.parse(value || "[]");
    if (!Array.isArray(parsed)) {
      throw new Error(`${label}은 배열 JSON이어야 합니다.`);
    }
    return parsed;
  } catch (error) {
    throw new Error(`${label} JSON 파싱 실패: ${error.message}`);
  }
}

function parseJsonValue(value, fallback = null) {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    console.warn("JSON 값을 읽지 못했습니다:", error);
    return fallback;
  }
}

function splitTags(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinTags(value) {
  return splitTags(value).join(", ");
}

function inferCurrencyFromTicker(ticker) {
  const normalized = normalizeTickerDraft(ticker);
  if (!normalized || normalized === "CASH") {
    return "KRW";
  }
  if (/^\d{6}$/.test(normalized) || /^[0-9A-Z]{6}$/.test(normalized) && /\d/.test(normalized)) {
    return "KRW";
  }
  return "USD";
}

function normalizeCurrency(value, fallbackTicker = "") {
  const normalized = String(value || "").trim().toUpperCase();
  if (normalized === "KRW" || normalized === "USD") {
    return normalized;
  }
  return inferCurrencyFromTicker(fallbackTicker);
}

function createInput({
  name,
  label,
  value = "",
  type = "text",
  placeholder = "",
  step = "",
  readOnly = false,
  className = "",
  inputMode = null,
}) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  if (className) {
    wrapper.classList.add(...className.split(/\s+/).filter(Boolean));
  }
  const input = document.createElement("input");
  input.name = name;
  input.type = type;
  input.lang = "ko";
  input.autocapitalize = "off";
  input.autocomplete = "off";
  input.spellcheck = false;
  input.value = value ?? "";
  input.placeholder = placeholder;
  input.readOnly = readOnly;
  if (inputMode) {
    input.inputMode = inputMode;
  }
  if (step) {
    input.step = step;
  }
  wrapper.append(input);
  return wrapper;
}

function createHiddenInput(name, value = "") {
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = name;
  input.value = value ?? "";
  return input;
}

function createSelect({ name, label, value = "medium", options = [] }) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  const select = document.createElement("select");
  select.name = name;
  select.lang = "ko";
  options.forEach(([optionValue, optionLabel]) => {
    select.append(new Option(optionLabel, optionValue));
  });
  select.value = value || options[0]?.[0] || "";
  wrapper.append(select);
  return wrapper;
}

function createTextArea({ name, label, value = "", placeholder = "" }) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  wrapper.classList.add("editor-wide");
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.lang = "ko";
  textarea.autocapitalize = "off";
  textarea.autocomplete = "off";
  textarea.spellcheck = false;
  textarea.value = value ?? "";
  textarea.placeholder = placeholder;
  wrapper.append(textarea);
  return wrapper;
}

function createCompactTextArea({
  name,
  label,
  value = "",
  placeholder = "",
  className = "",
  rows = 2,
}) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  if (className) {
    wrapper.classList.add(...className.split(/\s+/).filter(Boolean));
  }
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.lang = "ko";
  textarea.autocapitalize = "off";
  textarea.autocomplete = "off";
  textarea.spellcheck = false;
  textarea.value = value ?? "";
  textarea.placeholder = placeholder;
  textarea.rows = rows;
  wrapper.append(textarea);
  return wrapper;
}

function createRemoveButton(label) {
  const button = document.createElement("button");
  button.className = "secondary editor-remove";
  button.type = "button";
  button.dataset.editorRemove = "true";
  button.textContent = label;
  return button;
}

function applyKoreanInputDefaults(root = document) {
  root.querySelectorAll("input:not([type='hidden']), textarea, select").forEach((element) => {
    element.lang = "ko";
    if (element.tagName !== "SELECT") {
      element.autocapitalize = "off";
      element.autocomplete = element.id === "apiBaseUrl" ? "url" : "off";
      element.spellcheck = false;
    }
  });
}

function koreanObjectParticle(value) {
  const text = String(value ?? "").trim();
  const lastChar = [...text].pop();
  if (!lastChar) {
    return "를";
  }
  const code = lastChar.charCodeAt(0);
  if (code < 0xac00 || code > 0xd7a3) {
    return "를";
  }
  return (code - 0xac00) % 28 === 0 ? "를" : "을";
}

function resetFileInput(input) {
  if (input) {
    input.value = "";
  }
}

function resetFormSafely(form) {
  if (form && typeof form.reset === "function") {
    form.reset();
  }
}

function resetNewsInputScreen() {
  if (!elements.newsForm) {
    return;
  }
  const rawContent = elements.newsForm.elements.rawContent;
  const sourceUrl = elements.newsForm.elements.sourceUrl;
  if (rawContent) {
    rawContent.value = "";
  }
  if (sourceUrl) {
    sourceUrl.value = "";
  }
}

function resetCaptureInputScreen() {
  if (!elements.captureForm) {
    return;
  }
  const rawContent = elements.captureForm.elements.rawContent;
  const sourceUrl = elements.captureForm.elements.sourceUrl;
  const destination = elements.captureForm.elements.destination;
  if (rawContent) {
    rawContent.value = "";
  }
  if (sourceUrl) {
    sourceUrl.value = "";
  }
  if (destination) {
    destination.value = "auto";
  }
  resetFileInput(elements.captureForm.querySelector('input[name="researchFile"]'));
  if (elements.captureForm.elements.runThesisImpact) {
    elements.captureForm.elements.runThesisImpact.checked = true;
  }
  updateCaptureFileStatus(null);
}

function resetMarketCloseInputScreen() {
  if (!elements.marketCloseForm) {
    return;
  }
  const rawSummary = elements.marketCloseForm.elements.rawSummary;
  const sourceUrl = elements.marketCloseForm.elements.sourceUrl;
  const market = elements.marketCloseForm.elements.market;
  if (rawSummary) {
    rawSummary.value = "";
  }
  if (sourceUrl) {
    sourceUrl.value = "";
  }
  if (market) {
    market.value = "US";
  }
  if (elements.marketCloseForm.elements.sessionDate) {
    elements.marketCloseForm.elements.sessionDate.value = "";
  }
  resetFileInput(elements.marketCloseForm.querySelector('input[name="marketCloseFile"]'));
}

function resetLlmResultInputScreen() {
  if (!elements.llmResultForm) {
    return;
  }
  const llmResult = elements.llmResultForm.elements.llmResult;
  if (llmResult) {
    llmResult.value = "";
  }
  if (elements.llmResultForm.elements.runThesisImpact) {
    elements.llmResultForm.elements.runThesisImpact.checked = true;
  }
}

function resetLlmBridgeInputScreen() {
  if (elements.llmPromptForm) {
    const target = elements.llmPromptForm.elements.target;
    const sourceContext = elements.llmPromptForm.elements.sourceContext;
    if (target) {
      target.value = "";
    }
    if (sourceContext) {
      sourceContext.value = "";
    }
  }
  if (elements.llmPromptOutput) {
    elements.llmPromptOutput.value = "";
  }
  resetLlmResultInputScreen();
}

function resetWorkflowDraftForm(form, fileInputName = "") {
  if (!form) {
    return;
  }
  form.querySelectorAll("textarea").forEach((textarea) => {
    textarea.value = "";
  });
  if (fileInputName) {
    resetFileInput(form.querySelector(`input[name="${fileInputName}"]`));
  }
  form.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    checkbox.checked = checkbox.defaultChecked;
  });
}

function createHoldingActionGroup() {
  const group = document.createElement("div");
  group.className = "holding-actions";
  const saveButton = document.createElement("button");
  saveButton.className = "secondary holding-action";
  saveButton.type = "button";
  saveButton.dataset.holdingAction = "save";
  saveButton.textContent = "저장";
  saveButton.title = "수량, 평단, 현재가 등 현재 화면의 포트폴리오 입력값을 저장합니다.";
  const dashboardButton = document.createElement("button");
  dashboardButton.className = "secondary holding-action";
  dashboardButton.type = "button";
  dashboardButton.dataset.holdingAction = "dashboard";
  dashboardButton.textContent = "분석";
  dashboardButton.title = "이 보유 종목을 대시보드와 전체 분석 모듈에 연결합니다.";
  group.append(saveButton, dashboardButton, createRemoveButton("삭제"));
  return group;
}

function portfolioRefreshStatusMeta(status) {
  const normalized = String(status || "unknown").trim().toLowerCase();
  const map = {
    updated: ["갱신됨", "success"],
    confirmed: ["동일 확인", "info"],
    unavailable: ["미확인", "warning"],
    skipped: ["조회 제외", "muted"],
    unknown: ["상태 없음", "muted"],
  };
  const [label, tone] = map[normalized] || map.unknown;
  return { label, tone, normalized };
}

function portfolioRefreshStatusText(row = {}) {
  const meta = portfolioRefreshStatusMeta(row.price_refresh_status);
  const checkedAt = row.price_checked_at ? ` · ${formatDateTime(row.price_checked_at)}` : "";
  return `${meta.label}${checkedAt}`;
}

function createPortfolioRefreshBadge(holding = {}) {
  const badge = document.createElement("div");
  const meta = portfolioRefreshStatusMeta(holding.price_refresh_status);
  badge.className = `portfolio-refresh-badge ${meta.tone}`;
  badge.title = [
    `가격 상태: ${meta.label}`,
    holding.price_checked_at ? `확인 시각: ${formatDateTime(holding.price_checked_at)}` : "",
    holding.price_source ? `출처: ${holding.price_source}` : "",
  ].filter(Boolean).join(" · ");
  const label = document.createElement("span");
  label.textContent = "가격 확인";
  const strong = document.createElement("strong");
  strong.textContent = meta.label;
  badge.append(label, strong);
  return badge;
}

function portfolioSyncStatusMeta(status) {
  const normalized = String(status || "").trim().toLowerCase();
  const map = {
    account_synced: ["키움 동기화", "success"],
    kiwoom_domestic_missing: ["키움 미확인", "warning"],
    manual_or_overseas_protected: ["수동 보호", "info"],
    kiwoom_not_configured: ["설정 필요", "warning"],
    kiwoom_unavailable: ["연결 실패", "warning"],
  };
  const [label, tone] = map[normalized] || ["수동/미확인", "muted"];
  return { label, tone, normalized };
}

function createPortfolioSyncBadge(holding = {}) {
  const badge = document.createElement("div");
  const meta = portfolioSyncStatusMeta(holding.sync_status);
  badge.className = `portfolio-sync-badge ${meta.tone}`;
  badge.title = [
    `계좌 동기화: ${meta.label}`,
    holding.sync_checked_at ? `확인 시각: ${formatDateTime(holding.sync_checked_at)}` : "",
    holding.sync_message || "",
  ].filter(Boolean).join(" · ");
  const label = document.createElement("span");
  label.textContent = "수량 동기화";
  const strong = document.createElement("strong");
  strong.textContent = meta.label;
  badge.append(label, strong);
  return badge;
}

function portfolioRefreshStatusBadgeHtml(row = {}) {
  const meta = portfolioRefreshStatusMeta(row.price_refresh_status);
  return `<span class="smart-status-badge ${escapeHtml(meta.tone)}" title="${escapeHtml(portfolioRefreshStatusText(row))}">${escapeHtml(meta.label)}</span>`;
}

function freshnessStatusBadgeHtml(row = {}) {
  const toneMap = {
    ok: "success",
    warning: "warning",
    needs_action: "danger",
    needsAction: "danger",
  };
  const tone = toneMap[row.freshness_tone] || "muted";
  const label = row.freshness_status || "미확인";
  const title = [
    row.freshness_summary,
    row.latest_research_date ? `최신 저장일 ${row.latest_research_date}` : "",
    row.latest_dart_date ? `최신 공시 ${row.latest_dart_date}` : "",
    row.latest_dart_report || "",
  ].filter(Boolean).join(" · ");
  return `<span class="smart-status-badge ${escapeHtml(tone)}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

function syncCompanyNameAlignment(row) {
  const field = row?.querySelector('[name="name"]');
  if (!field) {
    return;
  }
  const text = field.value.trim();
  const visualLength = Array.from(text).reduce(
    (sum, char) => sum + (/^[\x00-\x7F]$/.test(char) ? 0.55 : 1),
    0
  );
  const manualLines = text.split("\n").length;
  const estimatedLines = Math.max(manualLines, Math.ceil(visualLength / 19));
  const lineClass = Math.min(Math.max(estimatedLines, 1), 3);
  field.classList.remove(
    "company-name-lines-1",
    "company-name-lines-2",
    "company-name-lines-3"
  );
  field.classList.add(`company-name-lines-${lineClass}`);
}

function makePortfolioHoldingRow(holding = {}) {
  const row = document.createElement("div");
  row.className = "editor-row holding-row";
  const currency = normalizeCurrency(holding.currency, holding.ticker);
  const fxRate = inferHoldingFxRateFromValues(holding, currency);
  row.append(
    createInput({
      name: "name",
      label: "회사명",
      value: holding.name || "",
      className: "company-name-field",
    }),
    createInput({
      name: "ticker",
      label: "티커",
      value: holding.ticker || "",
      placeholder: "예: PL",
      className: "ticker-field",
    }),
    createInput({
      name: "market_value",
      label: "평가금액",
      value: formatMoney(holding.market_value, "KRW"),
      inputMode: "decimal",
      className: "money-field market-value-field",
    }),
    createInput({
      name: "current_price",
      label: "현재가",
      value: formatMoney(holding.current_price, currency),
      inputMode: "decimal",
      className: "money-field current-price-field",
    }),
    createPortfolioRefreshBadge(holding),
    createPortfolioSyncBadge(holding),
    createInput({
      name: "average_cost",
      label: "매입가\n(평단)",
      value: formatMoney(holding.average_cost, currency),
      inputMode: "decimal",
      className: "money-field average-cost-field",
    }),
    createInput({
      name: "quantity",
      label: "수량",
      type: "number",
      value: holding.quantity ?? "",
      step: "0.0001",
      className: "quantity-field",
    }),
    createInput({
      name: "unrealized_gain",
      label: "수익",
      value: formatMoney(holding.unrealized_gain, "KRW"),
      inputMode: "decimal",
      className: "money-field gain-field",
      readOnly: true,
    }),
    createInput({
      name: "unrealized_return",
      label: "수익률",
      value:
        holding.unrealized_return === undefined || holding.unrealized_return === null
          ? ""
          : toPercent(holding.unrealized_return),
      className: "return-field",
      readOnly: true,
    }),
    createHiddenInput("currency", currency),
    createHiddenInput("weight", holding.weight ?? ""),
    createHiddenInput("sector", holding.sector || ""),
    createHiddenInput("cost_basis", formatMoney(holding.cost_basis, "KRW")),
    createHiddenInput("fx_rate", fxRate ? String(fxRate) : ""),
    createHiddenInput("theme_tags", joinTags(holding.theme_tags)),
    createHiddenInput("sync_status", holding.sync_status || ""),
    createHiddenInput("sync_source", holding.sync_source || ""),
    createHiddenInput("sync_checked_at", holding.sync_checked_at || ""),
    createHiddenInput("sync_message", holding.sync_message || ""),
    createHoldingActionGroup()
  );
  syncCompanyNameAlignment(row);
  syncPortfolioRowColors(row);
  return row;
}

function makeInterestTickerRow(item = {}) {
  const row = document.createElement("div");
  row.className = "editor-row interest-ticker-row interest-draft-row compact-interest-draft";
  row.append(
    createInput({
      name: "ticker",
      label: "관심종목",
      value: item.ticker || "",
      placeholder: "회사명 또는 티커 입력",
    }),
    createSelect({
      name: "priority",
      label: "우선순위",
      value: item.priority || "medium",
      options: [
        ["high", "높음"],
        ["medium", "보통"],
        ["low", "낮음"],
      ],
    }),
    createTextArea({
      name: "thesis",
      label: "메모",
      value: item.thesis || "",
      placeholder: "추적 이유, 가격 조건, 확인할 논거",
    }),
    createHiddenInput("tags", joinTags(item.tags))
  );
  return row;
}

function makeInterestTickerSummaryRow(item = {}) {
  const row = document.createElement("div");
  row.className =
    "interest-summary-row interest-ticker-summary-row interest-ticker-row interest-compact-card-row";
  const companyName = item.companyName || item.company_name || item.verification?.company_name || item.ticker || "";
  const tickerCode = String(item.ticker || "").trim();
  const identityLabel = companyName || (tickerCode ? "회사명 확인 필요" : "");
  const priorityLabel = { high: "높음", medium: "보통", low: "낮음" }[item.priority || "medium"] || "보통";
  const tags = joinTags(item.tags);
  const verified = Boolean(item.verification?.verified || item.verification?.status === "success");
  const notePreview = compactOutputText(item.thesis || item.notes || "추적 메모 없음", 72);
  const tickerHint = "";
  const detail = document.createElement("details");
  detail.className = "interest-card-details";
  const summary = document.createElement("summary");
  summary.className = "interest-card-summary";
  summary.title = identityLabel;
  summary.innerHTML = `
    <span class="interest-summary-main">
      <strong title="${escapeHtml(identityLabel)}">${escapeHtml(companyName)}</strong>
      ${tickerHint ? `<small class="interest-code-hint">${escapeHtml(tickerHint)}</small>` : ""}
      <span class="interest-summary-note">${escapeHtml(notePreview)}</span>
    </span>
    <span class="interest-summary-meta">
      <b class="priority">${escapeHtml(priorityLabel)}</b>
      <b class="${verified ? "verified" : "pending"}">${verified ? "인증" : "보류"}</b>
      <b class="interest-detail-cue">상세</b>
    </span>
  `;
  const quickActions = document.createElement("div");
  quickActions.className = "interest-card-actions";
  quickActions.innerHTML = `
    <button data-interest-action="dashboard" data-interest-ticker="${escapeHtml(tickerCode)}" type="button" title="${escapeHtml(identityLabel)} 대시보드 보기">보기</button>
    <button data-interest-action="rag-search" data-interest-ticker="${escapeHtml(tickerCode)}" type="button" title="${escapeHtml(identityLabel)} 저장 자료 검색">자료</button>
  `;
  const detailBody = document.createElement("div");
  detailBody.className = "interest-detail-grid";
  detailBody.append(
    createHiddenInput("ticker", tickerCode),
    createHiddenInput("companyName", companyName),
    createSelect({
      name: "priority",
      label: "우선순위",
      value: item.priority || "medium",
      options: [
        ["high", "높음"],
        ["medium", "보통"],
        ["low", "낮음"],
      ],
    }),
    createInput({
      name: "thesis",
      label: "메모",
      value: item.thesis || "",
      placeholder: "추적 이유",
    }),
    createHiddenInput("tags", tags),
    createHiddenInput("notes", item.notes || ""),
    createHiddenInput("verification", JSON.stringify(item.verification || {})),
    quickActions,
    createRemoveButton("삭제")
  );
  detail.append(summary, detailBody);
  row.append(detail);
  return row;
}

function makeInterestSectorRow(item = {}) {
  const row = document.createElement("div");
  row.className = "editor-row interest-sector-row interest-draft-row compact-interest-draft";
  row.append(
    createInput({
      name: "name",
      label: "관심섹터",
      value: item.name || "",
      placeholder: "예: AI 인프라, 전력기기",
    }),
    createInput({
      name: "region",
      label: "지역",
      value: item.region || "KR",
      placeholder: "KR, US, GLOBAL",
    }),
    createSelect({
      name: "priority",
      label: "우선순위",
      value: item.priority || "medium",
      options: [
        ["high", "높음"],
        ["medium", "보통"],
        ["low", "낮음"],
      ],
    }),
    createTextArea({
      name: "thesis",
      label: "메모",
      value: item.thesis || "",
      placeholder: "섹터를 보는 이유와 핵심 체크포인트",
    }),
    createHiddenInput("tags", joinTags(item.tags))
  );
  return row;
}

function makeInterestSectorSummaryRow(item = {}) {
  const row = document.createElement("div");
  row.className =
    "interest-summary-row interest-sector-summary-row interest-sector-row interest-compact-card-row";
  const priorityLabel = { high: "높음", medium: "보통", low: "낮음" }[item.priority || "medium"] || "보통";
  const tags = joinTags(item.tags);
  const notePreview = compactOutputText(item.thesis || item.notes || "확인 포인트 없음", 72);
  const detail = document.createElement("details");
  detail.className = "interest-card-details";
  const summary = document.createElement("summary");
  summary.className = "interest-card-summary";
  summary.innerHTML = `
    <span class="interest-summary-main">
      <strong>${escapeHtml(item.name || "관심섹터")}</strong>
      <span>${escapeHtml(item.region || "KR")}</span>
      <span class="interest-summary-note">${escapeHtml(notePreview)}</span>
    </span>
    <span class="interest-summary-meta">
      <b class="priority">${escapeHtml(priorityLabel)}</b>
      <b class="verified">섹터</b>
      <b class="interest-detail-cue">상세</b>
    </span>
  `;
  const quickActions = document.createElement("div");
  quickActions.className = "interest-card-actions";
  quickActions.innerHTML = `
    <button data-interest-action="sector-rag-search" data-interest-sector="${escapeHtml(item.name || "")}" type="button">자료</button>
  `;
  const detailBody = document.createElement("div");
  detailBody.className = "interest-detail-grid";
  detailBody.append(
    createHiddenInput("name", item.name || ""),
    createInput({
      name: "region",
      label: "지역",
      value: item.region || "KR",
      placeholder: "KR, US, GLOBAL",
    }),
    createSelect({
      name: "priority",
      label: "우선순위",
      value: item.priority || "medium",
      options: [
        ["high", "높음"],
        ["medium", "보통"],
        ["low", "낮음"],
      ],
    }),
    createInput({
      name: "thesis",
      label: "메모",
      value: item.thesis || "",
      placeholder: "확인할 포인트",
    }),
    createHiddenInput("tags", tags),
    createHiddenInput("notes", item.notes || ""),
    quickActions,
    createRemoveButton("삭제")
  );
  detail.append(summary, detailBody);
  row.append(detail);
  return row;
}

function renderEditorRows(container, rows, rowFactory, emptyFactory) {
  container.replaceChildren();
  const items = rows?.length ? rows : [emptyFactory ? emptyFactory() : {}];
  items.forEach((item) => container.append(rowFactory(item)));
}

function renderEditorRowsExact(container, rows, rowFactory, emptyMessage = "아직 추가된 항목이 없습니다.") {
  container.replaceChildren();
  if (!rows?.length) {
    const empty = document.createElement("div");
    empty.className = "editor-empty-state";
    empty.textContent = emptyMessage;
    container.append(empty);
    return;
  }
  rows.forEach((item) => container.append(rowFactory(item)));
}

function addEditorRow(container, rowFactory, rowData = {}) {
  const row = rowFactory(rowData);
  container.append(row);
  return row;
}

function firstEmptyEditorInput(container, rowSelector, inputName) {
  return [...container.querySelectorAll(rowSelector)]
    .map((row) => row.querySelector(`[name="${inputName}"]`))
    .find((input) => input && !input.value.trim());
}

function blockAddWhenRequiredInputIsEmpty(container, rowSelector, inputName, label) {
  const emptyInput = firstEmptyEditorInput(container, rowSelector, inputName);
  if (!emptyInput) {
    return false;
  }
  emptyInput.closest(".editor-row")?.classList.add("row-needs-input");
  emptyInput.focus();
  setOutput(`**입력 필요**\n\n${label} 입력칸이 비어 있습니다. 먼저 값을 입력한 뒤 새 항목을 추가하세요.`);
  return true;
}

function clearEditorInputWarning(event) {
  const row = event.target.closest(".editor-row");
  if (!row) {
    return;
  }
  row.classList.remove("row-needs-input");
}

function rowValue(row, name) {
  return row.querySelector(`[name="${name}"]`)?.value?.trim() || "";
}

function rowNumber(row, name) {
  return numberOrNull(rowValue(row, name));
}

function numericInputValue(row, name) {
  const value = rowNumber(row, name);
  return Number.isFinite(value) ? value : null;
}

function setRowValue(row, name, value) {
  const input = row.querySelector(`[name="${name}"]`);
  if (input) {
    input.value = value ?? "";
  }
}

function setRowMoneyValue(row, name, value, currency = "KRW") {
  const input = row.querySelector(`[name="${name}"]`);
  if (input) {
    input.value = formatMoney(value, currency);
  }
}

function signedPortfolioClass(value) {
  if (value === undefined || value === null || value === "") {
    return "portfolio-neutral";
  }
  const numeric = Number.isFinite(Number(value)) ? Number(value) : numberOrNull(value);
  if (numeric > 0) {
    return "portfolio-positive";
  }
  if (numeric < 0) {
    return "portfolio-negative";
  }
  return "portfolio-neutral";
}

function syncSignedPortfolioField(row, name, value = null) {
  const input = row?.querySelector(`[name="${name}"]`);
  if (!input) {
    return;
  }
  input.classList.remove("portfolio-positive", "portfolio-negative", "portfolio-neutral");
  input.classList.add(signedPortfolioClass(value === null ? rowValue(row, name) : value));
}

function syncPortfolioRowColors(row) {
  syncSignedPortfolioField(row, "unrealized_gain");
  syncSignedPortfolioField(row, "unrealized_return");
}

function markHoldingRowUnsaved(row) {
  if (!row) {
    return;
  }
  row.classList.add("row-unsaved");
  row.querySelector('[data-holding-action="save"]')?.classList.add("needs-save");
}

function clearHoldingRowsUnsaved() {
  elements.holdingsEditor
    ?.querySelectorAll(".holding-row.row-unsaved")
    .forEach((row) => {
      row.classList.remove("row-unsaved");
      row.querySelector('[data-holding-action="save"]')?.classList.remove("needs-save");
    });
}

function sortHoldingsByMarketValue(holdings = []) {
  return [...holdings].sort(
    (a, b) => Number(b.market_value || 0) - Number(a.market_value || 0)
  );
}

function parseRowPercentValue(row, name) {
  const raw = rowValue(row, name);
  const parsed = numberOrNull(raw);
  if (parsed === null) {
    return null;
  }
  return raw.includes("%") ? parsed / 100 : parsed;
}

function rowSearchText(row) {
  return [
    rowValue(row, "ticker"),
    rowValue(row, "name"),
    rowValue(row, "sector"),
    rowValue(row, "theme_tags"),
  ]
    .join(" ")
    .toLowerCase();
}

function applyPortfolioFilter() {
  if (!elements.portfolioFilter) {
    return;
  }
  const query = elements.portfolioFilter.value.trim().toLowerCase();
  holdingRows().forEach((row) => {
    row.hidden = Boolean(query) && !rowSearchText(row).includes(query);
  });
}

function applyPortfolioSort() {
  if (!elements.portfolioSort || !elements.holdingsEditor) {
    return;
  }
  const sortMode = elements.portfolioSort.value || "market_value_desc";
  const rows = holdingRows();
  const stringValue = (row, name) => rowValue(row, name).localeCompare("", "ko-KR") === 0
    ? ""
    : rowValue(row, name);
  const numericValue = (row, name) => rowNumber(row, name) ?? 0;
  const comparators = {
    market_value_desc: (a, b) => numericValue(b, "market_value") - numericValue(a, "market_value"),
    market_value_asc: (a, b) => numericValue(a, "market_value") - numericValue(b, "market_value"),
    gain_desc: (a, b) => numericValue(b, "unrealized_gain") - numericValue(a, "unrealized_gain"),
    return_desc: (a, b) => numericValue(b, "unrealized_return") - numericValue(a, "unrealized_return"),
    ticker_asc: (a, b) => stringValue(a, "ticker").localeCompare(stringValue(b, "ticker"), "ko-KR"),
    sector_asc: (a, b) => stringValue(a, "sector").localeCompare(stringValue(b, "sector"), "ko-KR"),
  };
  rows.sort(comparators[sortMode] || comparators.market_value_desc);
  rows.forEach((row) => elements.holdingsEditor.append(row));
}

function applyPortfolioViewState({ sort = false } = {}) {
  if (sort) {
    applyPortfolioSort();
  }
  applyPortfolioFilter();
}

function rowCurrency(row) {
  return normalizeCurrency(rowValue(row, "currency"), rowValue(row, "ticker"));
}

function inferHoldingFxRateFromValues(holding = {}, currency = "") {
  const normalizedCurrency = normalizeCurrency(currency || holding.currency, holding.ticker);
  if (normalizedCurrency !== "USD") {
    return 1;
  }
  const quantity = Number(holding.quantity);
  const averageCost = Number(holding.average_cost);
  const currentPrice = Number(holding.current_price);
  const costBasis = Number(holding.cost_basis);
  const marketValue = Number(holding.market_value);
  if (quantity > 0 && averageCost > 0 && costBasis > 0) {
    return costBasis / (quantity * averageCost);
  }
  if (quantity > 0 && currentPrice > 0 && marketValue > 0) {
    return marketValue / (quantity * currentPrice);
  }
  return 1;
}

function rowFxRate(row) {
  const currency = rowCurrency(row);
  if (currency !== "USD") {
    return 1;
  }
  const stored = numericInputValue(row, "fx_rate");
  if (stored !== null && stored > 0) {
    return stored;
  }
  const inferred = inferHoldingFxRateFromValues(
    {
      ticker: rowValue(row, "ticker"),
      currency,
      quantity: numericInputValue(row, "quantity"),
      average_cost: numericInputValue(row, "average_cost"),
      current_price: numericInputValue(row, "current_price"),
      cost_basis: numericInputValue(row, "cost_basis"),
      market_value: numericInputValue(row, "market_value"),
    },
    currency
  );
  if (inferred > 0) {
    setRowValue(row, "fx_rate", inferred.toFixed(6));
    return inferred;
  }
  return 1;
}

function holdingRows() {
  return [...elements.holdingsEditor.querySelectorAll(".holding-row")];
}

function isCashTicker(value) {
  return normalizeTickerDraft(value) === "CASH";
}

function normalizeHoldingCashFields(row) {
  const ticker = rowValue(row, "ticker");
  const currencyInput = row.querySelector('[name="currency"]');
  if (currencyInput && !currencyInput.value) {
    currencyInput.value = normalizeCurrency("", ticker);
  }
  if (!isCashTicker(ticker)) {
    return;
  }
  if (currencyInput) {
    currencyInput.value = "KRW";
  }
  if (!rowValue(row, "name")) {
    setRowValue(row, "name", "현금");
  }
  if (!rowValue(row, "sector")) {
    setRowValue(row, "sector", "Cash");
  }
  if (!rowValue(row, "theme_tags")) {
    setRowValue(row, "theme_tags", "Cash");
  }
}

function inferHoldingMarketValue(row, force = false) {
  normalizeHoldingCashFields(row);
  const marketValue = numericInputValue(row, "market_value");
  const quantity = numericInputValue(row, "quantity");
  const currentPrice = numericInputValue(row, "current_price");
  const averageCost = numericInputValue(row, "average_cost");
  const currency = rowCurrency(row);
  if (quantity !== null && averageCost !== null) {
    if (currentPrice !== null) {
      const unrealizedReturn = averageCost > 0 ? (currentPrice - averageCost) / averageCost : null;
      setRowValue(
        row,
        "unrealized_return",
        unrealizedReturn === null ? "" : toPercent(unrealizedReturn)
      );
      const fxRate = rowFxRate(row);
      const costBasis = quantity * averageCost * fxRate;
      const unrealizedGain = quantity * (currentPrice - averageCost) * fxRate;
      setRowMoneyValue(row, "cost_basis", costBasis, "KRW");
      setRowMoneyValue(row, "unrealized_gain", unrealizedGain, "KRW");
      syncPortfolioRowColors(row);
    }
  }
  if ((force || marketValue === null) && quantity !== null && currentPrice !== null) {
    const calculated = quantity * currentPrice * rowFxRate(row);
    setRowMoneyValue(row, "market_value", calculated, "KRW");
    return calculated;
  }
  return marketValue || 0;
}

function calculateRowGainValue(row, marketValue = null) {
  if (isCashTicker(rowValue(row, "ticker"))) {
    return 0;
  }
  const normalizedMarketValue =
    marketValue !== null && Number.isFinite(Number(marketValue))
      ? Number(marketValue)
      : numericInputValue(row, "market_value");
  const costBasis = numericInputValue(row, "cost_basis");
  if (
    normalizedMarketValue !== null &&
    Number.isFinite(normalizedMarketValue) &&
    costBasis !== null &&
    Number.isFinite(costBasis)
  ) {
    return normalizedMarketValue - costBasis;
  }
  const explicitGain = numericInputValue(row, "unrealized_gain");
  if (explicitGain !== null && Number.isFinite(explicitGain)) {
    return explicitGain;
  }
  const rowReturn = parseRowPercentValue(row, "unrealized_return");
  if (
    normalizedMarketValue !== null &&
    Number.isFinite(normalizedMarketValue) &&
    rowReturn !== null &&
    Number.isFinite(rowReturn) &&
    rowReturn > -0.999
  ) {
    const investedValue = normalizedMarketValue / (1 + rowReturn);
    return normalizedMarketValue - investedValue;
  }
  return 0;
}

function syncHoldingGainDisplay(row, marketValue = null) {
  const gainValue = calculateRowGainValue(row, marketValue);
  setRowMoneyValue(row, "unrealized_gain", gainValue, "KRW");
  syncPortfolioRowColors(row);
  return gainValue;
}

function portfolioModuleMissingCounts(status) {
  const items = status?.items || [];
  return items.reduce(
    (counts, item) => {
      const state = item.module_state || {};
      if (!state.team_report) counts.team += 1;
      if (!state.trade_setup) counts.trade += 1;
      if (!state.earnings_reaction) counts.earnings += 1;
      if (!state.model_update_note) counts.model += 1;
      if (!state.checklist) counts.checklist += 1;
      if (!state.recent_capture) counts.capture += 1;
      return counts;
    },
    { team: 0, trade: 0, earnings: 0, model: 0, checklist: 0, capture: 0 }
  );
}

function renderPortfolioAnalysisOverview(status = lastPortfolioAnalysisStatus) {
  if (!elements.portfolioAnalysisOverview) {
    return;
  }
  if (!status) {
    elements.portfolioAnalysisOverview.innerHTML = `
      <div class="warning">
        <span>전체 연결 상태</span>
        <strong>확인 전</strong>
        <p>저장된 포트폴리오를 불러오면 자동으로 점검합니다.</p>
      </div>
    `;
    return;
  }
  const items = status.items || [];
  const holdingCount = status.holding_count || items.length || 0;
  const readyCount = status.ready_count || 0;
  const completion = Number(status.average_completion);
  const completionText = Number.isFinite(completion) ? toPercent(completion) : "n/a";
  const missingCounts = portfolioModuleMissingCounts(status);
  const totalMissing = Object.values(missingCounts).reduce((sum, value) => sum + value, 0);
  const latestDate = items
    .map((item) => item.latest_report_date)
    .filter(Boolean)
    .sort()
    .at(-1) || "미확인";
  const staleItems = items
    .filter((item) => item.missing_modules?.length)
    .slice(0, 3)
    .map((item) => item.official_symbol || item.ticker)
    .filter(Boolean);
  const statusClass = readyCount === holdingCount && holdingCount > 0
    ? "ok"
    : completion >= 0.8
      ? "warning"
      : "needs_action";
  const missingText = totalMissing === 0
    ? "누락 없음"
    : `팀 ${missingCounts.team} · 매매 ${missingCounts.trade} · 실적 ${missingCounts.earnings} · 모델 ${missingCounts.model} · 체크 ${missingCounts.checklist} · 정보 ${missingCounts.capture}`;
  elements.portfolioAnalysisOverview.innerHTML = [
    `<div class="${statusClass}"><span>전체 연결 상태</span><strong>${readyCount}/${holdingCount}</strong><p>${readyCount === holdingCount && holdingCount > 0 ? "모든 보유 종목이 연결됐습니다." : "추가 연결이 필요한 종목이 있습니다."}</p></div>`,
    `<div><span>평균 완성도</span><strong>${escapeHtml(completionText)}</strong><p>6개 모듈 기준 자동 계산</p></div>`,
    `<div class="${totalMissing === 0 ? "ok" : "warning"}"><span>누락 모듈</span><strong>${totalMissing}개</strong><p>${escapeHtml(missingText)}</p></div>`,
    `<div><span>최근 업데이트</span><strong>${escapeHtml(latestDate)}</strong><p>저장 리포트 기준</p></div>`,
    `<div class="${staleItems.length ? "warning" : "ok"}"><span>다음 액션</span><strong>${staleItems.length ? "점검" : "유지"}</strong><p>${escapeHtml(staleItems.length ? `${staleItems.join(", ")} 먼저 보강` : "새 자료 입력 시 자동 비교")}</p></div>`,
  ].join("");
}

function performanceTone(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "neutral";
  }
  if (numeric > 0) {
    return "positive";
  }
  if (numeric < 0) {
    return "negative";
  }
  return "neutral";
}

function performanceQualityTone(label) {
  if (label === "높음") {
    return "positive";
  }
  if (label === "보통" || label === "확인 필요") {
    return "neutral";
  }
  return "negative";
}

function renderPortfolioPerformanceOverview(result) {
  if (!elements.portfolioPerformanceOverview) {
    return;
  }
  if (!result || !Array.isArray(result.periods) || !result.periods.length) {
    elements.portfolioPerformanceOverview.innerHTML =
      '<p class="empty-state">기간 수익 비교를 실행하면 최근 1주일, 1개월, 6개월, 1년 기준 순수익과 수익률이 표시됩니다.</p>';
    return;
  }
  const periodCards = result.periods
    .map((period) => {
      const tone = performanceTone(period.net_profit);
      const coverage = period.coverage_rate === null || period.coverage_rate === undefined
        ? "커버리지 n/a"
        : `커버리지 ${toPercent(period.coverage_rate)}`;
      return `
        <article class="portfolio-performance-card ${tone}">
          <span>${escapeHtml(period.label)}</span>
          <strong>${escapeHtml(formatMoney(period.net_profit, "KRW", "n/a"))}</strong>
          <p>${escapeHtml(period.return_rate === null || period.return_rate === undefined ? "수익률 n/a" : `수익률 ${toPercent(period.return_rate)}`)}</p>
          <small>${escapeHtml(coverage)} · 가격 ${escapeHtml(period.price_as_of || result.price_data_as_of || "미확인")} · 비교 ${escapeHtml(period.target_date || "미확인")} · 포함 ${escapeHtml(formatNumber(period.included_count || 0))}개</small>
        </article>
      `;
    })
    .join("");
  const bestPeriod = [...result.periods]
    .filter((period) => Number.isFinite(Number(period.net_profit)))
    .sort((a, b) => Number(b.net_profit) - Number(a.net_profit))[0];
  const skipped = result.skipped_holdings || [];
  const unsupportedCount = Number(result.unsupported_history_count || 0);
  const unsupportedMarketValue = Number(result.unsupported_history_market_value || 0);
  const priceCache = result.price_history_cache || {};
  const resultCache = result.result_cache || {};
  const refresh = result.current_price_refresh || {};
  const quality = result.performance_quality || {};
  const priceComparison = result.current_price_comparison || {};
  const refreshStatusCounts = refresh.status_counts || {};
  const refreshLatest = refresh.latest_checked_at ? formatDateTime(refresh.latest_checked_at) : "확인 전";
  const refreshText = refresh.enabled
    ? `현재가 강제 갱신 · 갱신 ${formatNumber(refresh.updated || refreshStatusCounts.updated || 0)}개 · 확인 ${formatNumber(refresh.confirmed || refreshStatusCounts.confirmed || 0)}개 · 미확인 ${formatNumber(refresh.unavailable || refreshStatusCounts.unavailable || 0)}개 · 최근 ${refreshLatest}`
    : `저장 현재가 사용 · 가격 히스토리 최신 종가 기준 · ${refresh.description || "빠른 응답을 위해 제공자 강제 갱신은 생략했습니다."}`;
  const calculationText = result.calculation_mode === "recomputed_on_request"
    ? "요청 시 재계산"
    : result.calculation_mode || "계산 방식 미확인";
  const cacheText = resultCache.enabled
    ? "결과 캐시 사용"
    : `결과 캐시 없음 · 가격 히스토리 ${priceCache.enabled ? "메모리 캐시" : "캐시 없음"}${
        priceCache.enabled
          ? ` (hit ${formatNumber(priceCache.hit_count || 0)} / miss ${formatNumber(priceCache.miss_count || 0)})`
          : ""
      }`;
  const skippedText = skipped.length
    ? `기간 수익 제외 ${skipped.length}개: ${skipped.slice(0, 4).map((item) => item.name || "종목 미확인").join(", ")}${skipped.length > 4 ? " 외" : ""}`
    : "제외 종목 없음";
  const skippedDetails = skipped.length
    ? `<details class="portfolio-performance-skip">
        <summary>${escapeHtml(skippedText)}</summary>
        <ul>
          ${skipped
            .slice(0, 12)
            .map(
              (item) => {
                const manualReturn = item.manual_unrealized_return === null || item.manual_unrealized_return === undefined
                  ? ""
                  : ` · 수동 수익률 ${toPercent(item.manual_unrealized_return)}`;
                const manualGain = item.manual_unrealized_gain === null || item.manual_unrealized_gain === undefined
                  ? ""
                  : ` · 수동 손익 ${formatMoney(item.manual_unrealized_gain, "KRW", "n/a")}`;
                const categoryLabel = item.category === "overseas_or_unsupported_history"
                  ? "해외/미지원 히스토리"
                  : item.category === "price_history_live_lookup_deferred" ? "실시간 히스토리 보류" : "히스토리 제한";
                const note = item.manual_result_note ? ` · ${item.manual_result_note}` : " · 저장 손익은 별도 유지합니다.";
                return `<li>${escapeHtml(item.name || "종목 미확인")} · 기간 수익 제외 · ${escapeHtml(categoryLabel)} · ${escapeHtml(item.reason || "가격 히스토리 없음")} · ${escapeHtml(item.impact || "기간 비교에서 제외")}${escapeHtml(manualGain)}${escapeHtml(manualReturn)}${escapeHtml(note)}</li>`;
              }
            )
            .join("")}
        </ul>
      </details>`
    : `<p class="portfolio-performance-note">제외 종목 없이 계산했습니다.</p>`;
  const comparisonItems = Array.isArray(priceComparison.items) ? priceComparison.items : [];
  const comparisonDetails = comparisonItems.length
    ? `<details class="portfolio-performance-skip">
        <summary>저장 현재가와 국내 최신 종가 차이 ${formatNumber(priceComparison.difference_count || comparisonItems.length)}개</summary>
        <ul>
          ${comparisonItems
            .slice(0, 12)
            .map(
              (item) =>
                `<li>${escapeHtml(item.name || "종목 미확인")} · 저장 ${escapeHtml(formatSmartPrice(item.stored_current_price, "KRW", "n/a"))} · 최신 종가 ${escapeHtml(formatSmartPrice(item.history_latest_close, "KRW", "n/a"))} · 차이 ${escapeHtml(toPercent(item.difference_rate))} · ${escapeHtml(item.history_latest_date || "일자 미확인")}</li>`
            )
            .join("")}
        </ul>
      </details>`
    : `<p class="portfolio-performance-note">저장 현재가와 국내 최신 종가 차이가 큰 종목은 없습니다.</p>`;
  const qualityTone = performanceQualityTone(quality.confidence_label);
  const latestStoredPrice = result.latest_stored_price_checked_at || quality.latest_stored_price_checked_at;
  const qualityCards = `
    <div class="portfolio-performance-quality">
      <article class="${qualityTone}">
        <span>정확도</span>
        <strong>${escapeHtml(quality.confidence_label || "확인 전")}</strong>
        <p>최소 커버리지 ${escapeHtml(quality.min_coverage_rate === null || quality.min_coverage_rate === undefined ? "n/a" : toPercent(quality.min_coverage_rate))}</p>
      </article>
      <article>
        <span>가격 기준</span>
        <strong>${escapeHtml(result.price_basis || "저장 현재가")}</strong>
        <p>${escapeHtml(latestStoredPrice ? `저장 현재가 확인 ${formatDateTime(latestStoredPrice)}` : "저장 현재가 확인 시각 없음")}</p>
      </article>
      <article class="${Number(priceComparison.difference_count || 0) ? "neutral" : "positive"}">
        <span>가격 차이</span>
        <strong>${formatNumber(priceComparison.difference_count || 0)}개</strong>
        <p>저장 현재가와 국내 최신 종가 0.5% 이상 차이</p>
      </article>
      <article class="${unsupportedCount ? "neutral" : "positive"}">
        <span>해외/수동</span>
        <strong>${formatNumber(unsupportedCount)}개</strong>
        <p>기간 비교 제외, 저장 손익은 별도 표시</p>
      </article>
    </div>
  `;
  elements.portfolioPerformanceOverview.innerHTML = `
    <div class="portfolio-performance-header">
      <div>
        <span>기간 수익 비교</span>
        <strong>${escapeHtml(result.portfolio_name || "포트폴리오")}</strong>
        <p>가격 기준일 ${escapeHtml(result.price_data_as_of || "미확인")} · 보유 수량은 현재 저장 포트폴리오 기준입니다.</p>
        <div class="portfolio-performance-metrics">
          <span><b>현재 미실현 손익</b>${escapeHtml(formatMoney(result.current_unrealized_gain, "KRW", "n/a"))}</span>
          <span><b>현재 미실현 수익률</b>${escapeHtml(toPercent(result.current_unrealized_return))}</span>
          <span><b>비교 상태</b>${escapeHtml(skippedText)}</span>
          <span><b>현재가 갱신</b>${escapeHtml(refreshText)}</span>
          <span><b>계산/캐시</b>${escapeHtml(calculationText)} · ${escapeHtml(cacheText)}</span>
          <span><b>해외/미지원 제외</b>${escapeHtml(formatNumber(unsupportedCount))}개 · ${escapeHtml(formatMoney(unsupportedMarketValue, "KRW", "0원"))}</span>
        </div>
      </div>
      <b>${escapeHtml(bestPeriod ? `최고 구간 ${bestPeriod.label}` : "구간 비교 대기")}</b>
    </div>
    ${qualityCards}
    <div class="portfolio-performance-grid">${periodCards}</div>
    <p class="portfolio-performance-note">${escapeHtml(result.price_refresh_guidance || "")}</p>
    <p class="portfolio-performance-note">${escapeHtml(result.coverage_note || "")}</p>
    <p class="portfolio-performance-note">${escapeHtml(result.data_limitations?.join(" ") || "기간 수익 비교는 확보된 가격 히스토리 범위 안에서 계산됩니다.")}</p>
    ${comparisonDetails}
    ${skippedDetails}
  `;
}

async function refreshPortfolioAnalysisOverview(options = {}) {
  try {
    const result = await fetchPortfolioAnalysisStatus(token());
    lastPortfolioAnalysisStatus = result;
    renderPortfolioAnalysisOverview(result);
    if (lastDashboard) {
      renderDashboardCards(lastDashboard);
    }
    return result;
  } catch (error) {
    if (!options.silent) {
      setError(error);
    }
    return null;
  }
}

async function refreshPortfolioTeamReportQueue(options = {}) {
  try {
    const result = await fetchPortfolioTeamReportQueue(token());
    lastPortfolioTeamReportQueue = result;
    if (lastDashboard) {
      renderDashboardCards(lastDashboard);
    }
    return result;
  } catch (error) {
    if (!options.silent) {
      setError(error);
    }
    return null;
  }
}

function updatePortfolioSummary(totalValue, rows) {
  const metrics = rows.reduce(
    (summary, row) => {
      if (!rowValue(row, "ticker")) {
        return summary;
      }
      summary.holdingCount += 1;
      if (isCashTicker(rowValue(row, "ticker"))) {
        return summary;
      }
      const marketValue = numericInputValue(row, "market_value") || 0;
      const gainValue = calculateRowGainValue(row, marketValue);
      const investedValue = Math.max(marketValue - gainValue, 0);
      summary.investedValue += investedValue;
      summary.gainValue += gainValue;
      return summary;
    },
    { holdingCount: 0, investedValue: 0, gainValue: 0 }
  );
  const totalReturn =
    metrics.investedValue > 0 ? metrics.gainValue / metrics.investedValue : null;
  if (!elements.portfolioSummary) {
    return;
  }
  elements.portfolioSummary.innerHTML = [
    `<span>총액 <strong>${escapeHtml(formatMoney(totalValue, "KRW", "0원"))}</strong></span>`,
    `<span>보유 <strong>${metrics.holdingCount}개</strong></span>`,
    `<span>투자금 <strong>${escapeHtml(formatMoney(metrics.investedValue, "KRW", "0원"))}</strong></span>`,
    `<span>총 수익 <strong class="${signedPortfolioClass(metrics.gainValue)}">${escapeHtml(formatMoney(metrics.gainValue, "KRW", "0원"))}</strong></span>`,
    `<span>수익률 <strong class="${signedPortfolioClass(totalReturn)}">${escapeHtml(totalReturn === null ? "n/a" : toPercent(totalReturn))}</strong></span>`,
  ].join("");
}

function recalculatePortfolioValues(options = {}) {
  const rows = holdingRows();
  const values = rows.map((row) => inferHoldingMarketValue(row, options.forceMarketValue));
  const totalValue = values.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
  if (totalValue > 0) {
    elements.portfolioForm.elements.portfolioValue.value = formatMoney(totalValue, "KRW", "0원");
    rows.forEach((row, index) => {
      const weight = values[index] / totalValue;
      setRowValue(row, "weight", Number.isFinite(weight) ? weight.toFixed(4) : "");
    });
  }
  rows.forEach((row, index) => {
    syncHoldingGainDisplay(row, values[index]);
  });
  updatePortfolioSummary(totalValue, rows);
  applyPortfolioViewState();
  return totalValue;
}

function collectPortfolioHoldings() {
  recalculatePortfolioValues();
  return [...elements.holdingsEditor.querySelectorAll(".holding-row")]
    .map((row) => ({
      ticker: normalizeTickerDraft(rowValue(row, "ticker")),
      name: rowValue(row, "name") || null,
      quantity: rowNumber(row, "quantity"),
      average_cost: rowNumber(row, "average_cost"),
      current_price: rowNumber(row, "current_price"),
      market_value: rowNumber(row, "market_value"),
      cost_basis: rowNumber(row, "cost_basis"),
      unrealized_gain: rowNumber(row, "unrealized_gain"),
      unrealized_return: parseRowPercentValue(row, "unrealized_return"),
      weight: parseRowPercentValue(row, "weight"),
      sector: rowValue(row, "sector") || "Unknown",
      theme_tags: splitTags(rowValue(row, "theme_tags")),
      currency: rowCurrency(row),
      sync_status: rowValue(row, "sync_status") || null,
      sync_source: rowValue(row, "sync_source") || null,
      sync_checked_at: rowValue(row, "sync_checked_at") || null,
      sync_message: rowValue(row, "sync_message") || null,
    }))
    .filter((item) => item.ticker);
}

function parseExecutionNoticeNumber(text, labels = []) {
  const normalizedLabels = labels.map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(
    `(?:${normalizedLabels.join("|")})\\s*[:：]?\\s*([₩$]?\\s*[\\d,]+(?:\\.\\d+)?)`,
    "i"
  );
  const match = String(text || "").match(pattern);
  return match ? numberOrNull(match[1]) : null;
}

function parsePortfolioExecutionNotice(text) {
  const source = String(text || "").trim();
  if (!source) {
    throw new Error("체결 문자를 먼저 붙여넣으세요.");
  }
  if (/매도/.test(source) && !/매수/.test(source)) {
    throw new Error("현재 자동 반영은 매수 체결만 지원합니다. 매도는 수량을 직접 조정해 주세요.");
  }
  const nameMatch = source.match(/(?:종목명|종목|상품명)\s*[:：]\s*([^\n\r]+)/i);
  const rawName = nameMatch?.[1]?.replace(/\s*\[[^\]]+\]\s*$/, "").trim() || "";
  const tickerMatch = source.match(/(?:티커|종목코드|코드)\s*[:：]\s*([A-Za-z0-9.\-]+)/i);
  const ticker = normalizeTickerDraft(tickerMatch?.[1] || resolveLocalTickerAlias(rawName));
  const quantity = parseExecutionNoticeNumber(source, ["주문수량", "체결수량", "수량"]);
  const price = parseExecutionNoticeNumber(source, ["체결금액", "체결가", "매수단가", "가격"]);
  if (!ticker || !rawName) {
    throw new Error("체결 문자에서 종목명을 인식하지 못했습니다. `종목명: 회사명` 형식이 필요합니다.");
  }
  if (!Number.isFinite(quantity) || quantity <= 0) {
    throw new Error("체결 문자에서 수량을 인식하지 못했습니다.");
  }
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error("체결 문자에서 체결가를 인식하지 못했습니다.");
  }
  const displayName = KOREAN_TICKER_DISPLAY_NAMES[ticker] || rawName;
  return {
    ticker,
    name: displayName,
    quantity,
    price,
    currency: inferCurrencyFromTicker(ticker),
  };
}

function findPortfolioHoldingRowByTicker(ticker) {
  const normalized = normalizeTickerDraft(ticker);
  return holdingRows().find((row) => normalizeTickerDraft(rowValue(row, "ticker")) === normalized);
}

function applyExecutionNoticeToPortfolioRows(execution) {
  let row = findPortfolioHoldingRowByTicker(execution.ticker);
  const isNewHolding = !row;
  if (!row) {
    addEditorRow(elements.holdingsEditor, makePortfolioHoldingRow, {
      ticker: execution.ticker,
      name: execution.name,
      currency: execution.currency,
      sector: "Unknown",
      theme_tags: [],
    });
    row = findPortfolioHoldingRowByTicker(execution.ticker);
  }
  if (!row) {
    throw new Error("체결 반영 행을 만들지 못했습니다.");
  }
  const oldQuantity = numericInputValue(row, "quantity") || 0;
  const oldAverageCost = numericInputValue(row, "average_cost") || 0;
  const currentPrice = numericInputValue(row, "current_price") || execution.price;
  const nextQuantity = oldQuantity + execution.quantity;
  const nextAverageCost =
    oldQuantity > 0 && oldAverageCost > 0
      ? ((oldQuantity * oldAverageCost) + (execution.quantity * execution.price)) / nextQuantity
      : execution.price;
  setRowValue(row, "ticker", execution.ticker);
  setRowValue(row, "name", execution.name);
  setRowValue(row, "quantity", Number(nextQuantity.toFixed(4)));
  setRowMoneyValue(row, "average_cost", nextAverageCost, execution.currency);
  if (!numericInputValue(row, "current_price")) {
    setRowMoneyValue(row, "current_price", execution.price, execution.currency);
  }
  setRowValue(row, "currency", execution.currency);
  setRowValue(row, "sync_status", "manual");
  setRowValue(row, "sync_source", "manual_execution_notice");
  setRowValue(row, "sync_checked_at", new Date().toISOString());
  setRowValue(
    row,
    "sync_message",
    `체결 문자 기준으로 ${formatNumber(execution.quantity)}주, ${formatMoney(execution.price, execution.currency)} 매수 반영`
  );
  row.classList.add("row-unsaved");
  recalculatePortfolioValues({ forceMarketValue: true });
  return {
    isNewHolding,
    oldQuantity,
    nextQuantity,
    nextAverageCost,
    currentPrice,
  };
}

function collectInterestTickerRows(container = elements.interestTickerEditor) {
  return [...container.querySelectorAll(".interest-ticker-row")]
    .map((row) => {
      const verification = parseJsonValue(rowValue(row, "verification"), null);
      return {
        ticker: rowValue(row, "ticker"),
        companyName: rowValue(row, "companyName") || verification?.company_name || null,
        priority: rowValue(row, "priority") || "medium",
        thesis: rowValue(row, "thesis") || null,
        notes: rowValue(row, "notes") || null,
        tags: splitTags(rowValue(row, "tags")),
        verification,
      };
    })
    .filter((item) => item.ticker);
}

function collectInterestTickers() {
  return collectInterestTickerRows(elements.interestTickerEditor);
}

function dashboardCandidateKey(value) {
  return normalizeTickerDraft(resolveLocalTickerAlias(value));
}

function readRecentDashboardTickers() {
  try {
    const raw = window.localStorage?.getItem(DASHBOARD_RECENT_TICKERS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }
    const rows = [];
    const seen = new Set();
    parsed.forEach((item) => {
      const ticker = dashboardCandidateKey(item?.ticker || item?.symbol || item?.company || item?.companyName);
      if (!ticker || seen.has(ticker)) {
        return;
      }
      seen.add(ticker);
      rows.push({
        ticker,
        company:
          item?.company ||
          item?.companyName ||
          KOREAN_TICKER_DISPLAY_NAMES[ticker] ||
          ticker,
        used_at: item?.used_at || "",
      });
    });
    const compact = rows.slice(0, 10);
    if (compact.length !== parsed.length) {
      saveRecentDashboardTickers(compact);
    }
    return compact;
  } catch (error) {
    console.warn("최근 대시보드 종목 이력을 읽지 못했습니다:", error);
    return [];
  }
}

function saveRecentDashboardTickers(items) {
  try {
    const rows = [];
    const seen = new Set();
    (items || []).forEach((item) => {
      const ticker = dashboardCandidateKey(item?.ticker || item?.symbol || item?.company || item?.companyName);
      if (!ticker || seen.has(ticker)) {
        return;
      }
      seen.add(ticker);
      rows.push({
        ticker,
        company:
          item?.company ||
          item?.companyName ||
          KOREAN_TICKER_DISPLAY_NAMES[ticker] ||
          ticker,
        used_at: item?.used_at || "",
      });
    });
    window.localStorage?.setItem(
      DASHBOARD_RECENT_TICKERS_STORAGE_KEY,
      JSON.stringify(rows.slice(0, 10))
    );
  } catch (error) {
    console.warn("최근 대시보드 종목 이력 저장 실패:", error);
  }
}

function addDashboardCandidate(target, sourceMap, item = {}, source = "후보") {
  const ticker = dashboardCandidateKey(
    item.official_symbol || item.ticker || item.symbol || item.code || item.name || item.companyName
  );
  if (!ticker || ticker === "UNKNOWN" || sourceMap.has(ticker)) {
    return;
  }
  const company =
    item.company_name ||
    item.companyName ||
    item.name ||
    item.company ||
    item.verification?.company_name ||
    KOREAN_TICKER_DISPLAY_NAMES[ticker] ||
    ticker;
  target.push({
    ticker,
    company,
    source,
    sourceGroup: source === "최근 사용" || source === "관심종목" ? source : "포트폴리오",
    label: company && company !== ticker ? company : "회사명 확인 필요",
  });
  sourceMap.add(ticker);
}

function displayCompanyName(item, fallback = "회사명 확인 필요") {
  const source = item || {};
  return String(
    source.company_name ||
      source.companyName ||
      source.display_label ||
      source.label ||
      source.scope_label ||
      source.holding_name ||
      source.name ||
      source.company ||
      source.verification?.company_name ||
      source.ticker_verification?.company_name ||
      source.ticker_profile?.company_name ||
      source.profile?.company_name ||
      source.signal?.company_name ||
      fallback
  ).trim();
}

function portfolioDashboardCandidates() {
  const rows = [];
  const seen = new Set();
  savedPortfolios.forEach((portfolio) => {
    (portfolio.holdings || []).forEach((holding) => {
      addDashboardCandidate(rows, seen, holding, portfolio.portfolio_name || "포트폴리오");
    });
  });
  return rows;
}

function interestDashboardCandidates() {
  const rows = [];
  const seen = new Set();
  const tickers = lastInterestList?.tickers || collectInterestTickers();
  tickers
    .filter((item) => item?.verification?.verified)
    .forEach((item) => addDashboardCandidate(rows, seen, item, "관심종목"));
  return rows;
}

function recentDashboardCandidates() {
  const rows = [];
  const seen = new Set();
  readRecentDashboardTickers().forEach((item) => addDashboardCandidate(rows, seen, item, "최근 사용"));
  return rows;
}

function dashboardTickerPickerCandidates() {
  return recentDashboardCandidates().slice(0, 10);
}

function dashboardTickerCandidates() {
  const rows = [];
  const seen = new Set();
  [
    ...dashboardTickerPickerCandidates(),
    ...portfolioDashboardCandidates(),
    ...interestDashboardCandidates(),
  ].forEach(
    (item) => addDashboardCandidate(rows, seen, item, item.source)
  );
  return rows;
}

function rememberDashboardTicker(ticker, company = "") {
  const normalizedTicker = dashboardCandidateKey(ticker);
  if (!normalizedTicker) {
    return;
  }
  const existing = readRecentDashboardTickers().filter(
    (item) => dashboardCandidateKey(item.ticker) !== normalizedTicker
  );
  const next = [
    {
      ticker: normalizedTicker,
      company: company || KOREAN_TICKER_DISPLAY_NAMES[normalizedTicker] || normalizedTicker,
      used_at: new Date().toISOString(),
    },
    ...existing,
  ];
  saveRecentDashboardTickers(next);
  renderDashboardTickerPicker();
}

function renderDashboardTickerPicker() {
  const pickerCandidates = dashboardTickerPickerCandidates();
  const quickCandidates = [
    ...portfolioDashboardCandidates(),
    ...interestDashboardCandidates(),
  ];
  if (elements.dashboardTickerOptions) {
    elements.dashboardTickerOptions.innerHTML = pickerCandidates
      .map(
        (item) =>
          `<option value="${escapeHtml(item.company || item.ticker)}"></option>`
      )
      .join("");
  }
  if (!elements.dashboardTickerSelect) {
    return;
  }
  const current = normalizeTickerDraft(activeTicker);
  elements.dashboardTickerSelect.innerHTML = [
    `<option value="">최근 사용 10개 중 선택</option>`,
    ...(pickerCandidates.length
      ? pickerCandidates.map(
      (item) =>
        `<option value="${escapeHtml(item.ticker)}" data-display="${escapeHtml(
          item.company || item.ticker
        )}" ${item.ticker === current ? "selected" : ""}>${escapeHtml(item.company || item.ticker)}</option>`
      )
      : [`<option value="" disabled>최근 사용 이력 없음</option>`]),
  ].join("");
  renderDashboardTickerQuickList(quickCandidates);
}

function renderDashboardTickerQuickList(candidates = []) {
  if (!elements.dashboardTickerQuickList) {
    return;
  }
  if (!candidates.length) {
    elements.dashboardTickerQuickList.innerHTML = `
      <div class="dashboard-ticker-empty">
        저장된 보유 종목이나 관심종목이 아직 없습니다. 포트폴리오 또는 관심종목/섹터를 저장하면 여기에 바로 표시됩니다.
      </div>
    `;
    return;
  }
  const groups = [
    ["보유 종목", candidates.filter((item) => item.sourceGroup === "포트폴리오")],
    ["관심종목", candidates.filter((item) => item.sourceGroup === "관심종목")],
  ].filter(([, items]) => items.length);

  elements.dashboardTickerQuickList.innerHTML = groups
    .map(
      ([title, items]) => {
        const isLargePortfolioGroup = title === "보유 종목" && items.length > 12;
        const visibleItems = isLargePortfolioGroup && !dashboardTickerGroupsExpanded
          ? items.slice(0, 12)
          : items;
        return `
        <section class="dashboard-ticker-group ${isLargePortfolioGroup && !dashboardTickerGroupsExpanded ? "is-collapsed" : ""}">
          <div class="dashboard-ticker-group-header">
            <strong>${escapeHtml(title)} <small>${escapeHtml(`${items.length}개`)}</small></strong>
            ${
              isLargePortfolioGroup
                ? `<button class="dashboard-ticker-toggle" data-dashboard-ticker-toggle type="button">${
                    dashboardTickerGroupsExpanded ? "간단히 보기" : "전체 보기"
                  }</button>`
                : ""
            }
          </div>
          <div>
            ${items
              .slice(0, visibleItems.length)
              .map((item) => {
                const displayName = item.company || item.label || "회사명 확인 필요";
                const tooltip = item.label || displayName;
                const ariaLabel =
                  item.company && item.company !== item.ticker
                    ? `${item.company}, ${item.source}`
                    : `${displayName}, ${item.source}`;
                return `
                  <button
                    class="dashboard-ticker-chip"
                    data-dashboard-quick-ticker="${escapeHtml(item.ticker)}"
                    data-dashboard-quick-display="${escapeHtml(displayName)}"
                    type="button"
                    title="${escapeHtml(tooltip)} · ${escapeHtml(item.source)}"
                    aria-label="${escapeHtml(ariaLabel)}"
                  >
                    <span>${escapeHtml(displayName)}</span>
                  </button>
                `;
              })
              .join("")}
          </div>
        </section>
      `;
      }
    )
    .join("");
}

function resolveDashboardWorkflowTicker() {
  const selected = elements.dashboardTickerSelect?.value || "";
  const inputValue = elements.dashboardForm?.elements?.ticker?.value || "";
  return normalizeTickerInput(activeTicker || selected || inputValue);
}

function collectInterestSectorRows(container = elements.interestSectorEditor) {
  return [...container.querySelectorAll(".interest-sector-row")]
    .map((row) => ({
      name: rowValue(row, "name"),
      region: rowValue(row, "region") || "KR",
      priority: rowValue(row, "priority") || "medium",
      thesis: rowValue(row, "thesis") || null,
      notes: rowValue(row, "notes") || null,
      tags: splitTags(rowValue(row, "tags")),
    }))
    .filter((item) => item.name);
}

function collectInterestSectors() {
  return collectInterestSectorRows(elements.interestSectorEditor);
}

function resetInterestTickerDraft() {
  renderEditorRows(
    elements.interestTickerDraft,
    [],
    makeInterestTickerRow,
    () => ({ ticker: "", priority: "medium", tags: [] })
  );
}

function resetInterestSectorDraft() {
  renderEditorRows(
    elements.interestSectorDraft,
    [],
    makeInterestSectorRow,
    () => ({ name: "", region: "KR", priority: "medium", tags: [] })
  );
}

function resetInterestDrafts() {
  resetInterestTickerDraft();
  resetInterestSectorDraft();
}

function currentActiveTabLabel() {
  return (
    document.querySelector(".tab.active")?.textContent?.replace(/\s+/g, " ").trim() ||
    "분석 결과"
  );
}

function visibleOutputText() {
  return (elements.output?.innerText || elements.output?.textContent || "").trim();
}

function jsonSafeOutput(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (_error) {
    return String(value ?? "");
  }
}

function triggerFileDownload(blob, filename) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || "research-os-result.xlsx";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

async function downloadVisibleResultAsExcel() {
  const resultText = visibleOutputText();
  if (!resultText || resultText === "대기 중입니다.") {
    setOutput("**엑셀 다운로드 불가**\n\n먼저 분석을 실행해서 결과 창에 내용이 표시되게 해주세요.");
    return;
  }

  syncApiBaseUrl();
  const button = elements.exportResultExcel;
  const originalText = button?.textContent || "엑셀 다운로드";
  if (button) {
    button.disabled = true;
    button.textContent = "변환 중...";
  }
  try {
    const { blob, filename } = await exportResultXlsx(token(), {
      title: `리서치 OS - ${currentActiveTabLabel()}`,
      module: currentActiveTabLabel(),
      resultText,
      resultJson: jsonSafeOutput(lastOutputRaw),
    });
    triggerFileDownload(blob, filename);
    if (button) {
      button.textContent = "다운로드 완료";
      window.setTimeout(() => {
        button.textContent = originalText;
      }, 1600);
    }
  } catch (error) {
    setError(error);
  } finally {
    if (button) {
      window.setTimeout(() => {
        button.disabled = false;
        if (button.textContent !== originalText) {
          button.textContent = originalText;
        }
      }, 1700);
    }
  }
}

function summaryPill(label, value) {
  const pill = document.createElement("span");
  pill.innerHTML = `${escapeHtml(label)} <strong>${escapeHtml(value)}</strong>`;
  return pill;
}

function updateInterestsSummary(response = {}) {
  if (!elements.interestsSummary) {
    return;
  }
  const tickers = response.tickers || collectInterestTickers();
  const sectors = response.sectors || collectInterestSectors();
  const highPriorityTickers = tickers.filter((item) => item.priority === "high").length;
  const highPrioritySectors = sectors.filter((item) => item.priority === "high").length;
  const verifiedTickers = tickers.filter((item) => item.verification?.verified).length;
  elements.interestsSummary.replaceChildren(
    summaryPill("관심종목", `${tickers.length}개`),
    summaryPill("인증 완료", `${verifiedTickers}개`),
    summaryPill("관심섹터", `${sectors.length}개`),
    summaryPill("우선순위 높음", `${highPriorityTickers + highPrioritySectors}개`)
  );
}

function initializeEditableLists() {
  renderEditorRows(
    elements.holdingsEditor,
    [],
    makePortfolioHoldingRow,
    () => ({ ticker: "", sector: "Unknown", theme_tags: [] })
  );
  recalculatePortfolioValues();
  renderEditorRowsExact(
    elements.interestTickerEditor,
    [],
    makeInterestTickerSummaryRow,
    "추가된 관심종목이 없습니다. 위 입력칸에서 1개씩 추가하세요."
  );
  renderEditorRowsExact(
    elements.interestSectorEditor,
    [],
    makeInterestSectorSummaryRow,
    "추가된 관심섹터가 없습니다. 위 입력칸에서 1개씩 추가하세요."
  );
  resetInterestDrafts();
  updateInterestsSummary();
}

function currentPortfolioPayload() {
  const data = formDataObject(elements.portfolioForm);
  const holdings = collectPortfolioHoldings();
  if (!holdings.length) {
    throw new Error("보유 종목을 1개 이상 입력하세요.");
  }
  return {
    portfolioName: data.portfolioName || "default",
    holdings,
    portfolioValue: numberOrNull(data.portfolioValue),
    maxSinglePositionWeight: Number(data.maxSinglePositionWeight || 0.2),
    maxSectorWeight: Number(data.maxSectorWeight || 0.35),
    maxThemeWeight: 0.4,
    notes: data.portfolioNotes || "",
  };
}

function updatePortfolioLoadedAt(portfolio, label = "불러온") {
  if (!elements.portfolioLoadedAt) {
    return;
  }
  if (!portfolio) {
    elements.portfolioLoadedAt.textContent = "최근 불러온 일시: 아직 없음";
    return;
  }
  const loadedAt = formatDateTime(new Date().toISOString());
  const updatedAt =
    portfolio.updated_at ||
    portfolio.updatedAt ||
    portfolio.modified_at ||
    portfolio.modifiedAt ||
    "";
  const parts = [
    `최근 ${label} 일시: ${loadedAt}`,
    updatedAt ? `저장 수정: ${formatDateTime(updatedAt)}` : "",
    portfolio.portfolio_name ? `포트폴리오: ${portfolio.portfolio_name}` : "",
    `보유 종목: ${formatNumber(portfolio.holding_count ?? portfolio.holdings?.length ?? 0)}개`,
  ].filter(Boolean);
  elements.portfolioLoadedAt.textContent = parts.join(" · ");
}

function portfolioStoreFreshnessSummary(portfolio = {}) {
  const updatedAt =
    portfolio.updated_at ||
    portfolio.updatedAt ||
    portfolio.modified_at ||
    portfolio.modifiedAt ||
    "";
  if (!updatedAt) {
    return "수정 미확인 · 갱신 권고";
  }
  const updatedDate = new Date(updatedAt);
  const baseText = `수정 ${formatDateTime(updatedAt)}`;
  if (Number.isNaN(updatedDate.getTime())) {
    return `${baseText} · 갱신 확인 필요`;
  }
  const ageHours = Math.max(0, Math.round((Date.now() - updatedDate.getTime()) / (1000 * 60 * 60)));
  if (ageHours > 24) {
    return `${baseText} · ${formatNumber(ageHours)}시간 경과 · 갱신 권고`;
  }
  return `${baseText} · ${formatNumber(ageHours)}시간 경과`;
}

function portfolioSyncStatusLabel(status) {
  const labels = {
    account_synced: "키움 동기화",
    manual_or_overseas_protected: "수동 보호",
    kiwoom_domestic_missing: "키움 미확인",
    kiwoom_not_configured: "설정 필요",
    unknown: "미확인",
  };
  return labels[status] || "미확인";
}

function summarizePortfolioSyncFromPortfolio(portfolio) {
  const holdings = Array.isArray(portfolio?.holdings) ? portfolio.holdings : [];
  const counts = holdings.reduce(
    (acc, holding) => {
      const status = holding.sync_status || "unknown";
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    },
    {
      account_synced: 0,
      manual_or_overseas_protected: 0,
      kiwoom_domestic_missing: 0,
      kiwoom_not_configured: 0,
      kiwoom_unavailable: 0,
      unknown: 0,
    }
  );
  const latestCheckedAt = holdings
    .map((holding) => holding.sync_checked_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  return {
    holding_count: holdings.length,
    counts,
    latest_checked_at: latestCheckedAt || null,
    last_history_created_at: null,
    last_history_checked_at: null,
    last_history_message: null,
  };
}

function renderPortfolioSyncOverview(payload = {}) {
  if (!elements.portfolioSyncOverview) {
    return;
  }
  const summary = payload.summary || summarizePortfolioSyncFromPortfolio(payload.portfolio || activePortfolioSnapshot);
  const counts = summary.counts || {};
  const synced = counts.account_synced || 0;
  const protectedCount = counts.manual_or_overseas_protected || 0;
  const missing = (counts.kiwoom_domestic_missing || 0) + (counts.kiwoom_not_configured || 0) + (counts.kiwoom_unavailable || 0);
  const unknown = counts.unknown || 0;
  const checkedAt = summary.last_history_checked_at || summary.latest_checked_at || summary.last_history_created_at;
  const holdingCount = summary.holding_count || synced + protectedCount + missing + unknown;
  const statusClass = missing > 0 ? "warning" : synced + protectedCount > 0 ? "ok" : "needs_action";
  elements.portfolioSyncOverview.innerHTML = [
    `<div class="${statusClass}"><span>계좌 동기화</span><strong>${escapeHtml(checkedAt ? formatDateTime(checkedAt) : "확인 전")}</strong><p>${escapeHtml(checkedAt ? "최근 키움 국내 수량 확인 기준" : "최근 동기화 이력이 없습니다.")}</p></div>`,
    `<div class="${synced ? "ok" : "needs_action"}"><span>키움 동기화</span><strong>${formatNumber(synced)}개</strong><p>국내 잔고와 수량/평단 확인</p></div>`,
    `<div class="${protectedCount ? "info" : "ok"}"><span>수동 보호</span><strong>${formatNumber(protectedCount)}개</strong><p>해외주식·수동 관리 수량 보존</p></div>`,
    `<div class="${missing ? "warning" : "ok"}"><span>확인 필요</span><strong>${formatNumber(missing + unknown)}개</strong><p>${escapeHtml(missing ? "국내 잔고 미확인 또는 설정 필요" : "미확인 항목 없음")}</p></div>`,
    `<div><span>전체 종목</span><strong>${formatNumber(holdingCount)}개</strong><p>${escapeHtml(summary.last_history_message || "이력 조회 시 최근 기록을 함께 표시")}</p></div>`,
  ].join("");
}

function portfolioSyncHistoryOutputLines(result = {}) {
  const summary = result.summary || {};
  const counts = summary.counts || {};
  const history = Array.isArray(result.history) ? result.history : [];
  const historyLines = history.slice(0, 10).flatMap((item, index) => {
    const changes = Array.isArray(item.changes) ? item.changes : [];
    const skipped = Array.isArray(item.skipped) ? item.skipped : [];
    const changedNames = changes
      .filter((change) => change.changed)
      .slice(0, 4)
      .map((change) => change.name || "회사명 미확인");
    const protectedNames = skipped
      .filter((entry) => entry.reason === "manual_or_overseas_protected")
      .slice(0, 4)
      .map((entry) => entry.name || "회사명 미확인");
    return [
      `${index + 1}. ${formatDateTime(item.created_at || item.checked_at || "")} · 변경 ${formatNumber(item.updated_count || 0)}개 · 동일 확인 ${formatNumber(item.confirmed_count || 0)}개 · 보존/미확인 ${formatNumber(item.skipped_count || 0)}개`,
      changedNames.length ? `   - 변경: ${changedNames.join(", ")}` : "",
      protectedNames.length ? `   - 수동 보호: ${protectedNames.join(", ")}` : "",
    ].filter(Boolean);
  });
  return [
    "# 최근 계좌 동기화 이력",
    "",
    `- 포트폴리오: ${result.portfolio_name || elements.portfolioSelect?.value || "미선택"}`,
    `- 키움 동기화: ${formatNumber(counts.account_synced || 0)}개`,
    `- 수동 보호: ${formatNumber(counts.manual_or_overseas_protected || 0)}개`,
    `- 확인 필요: ${formatNumber((counts.kiwoom_domestic_missing || 0) + (counts.kiwoom_not_configured || 0) + (counts.kiwoom_unavailable || 0) + (counts.unknown || 0))}개`,
    summary.last_history_checked_at || summary.latest_checked_at
      ? `- 최근 확인 시각: ${formatDateTime(summary.last_history_checked_at || summary.latest_checked_at)}`
      : "- 최근 확인 시각: 아직 없음",
    "",
    historyLines.length ? "이력" : "이력 없음",
    ...historyLines,
  ];
}

function fillPortfolioForm(portfolio) {
  if (!portfolio) {
    return;
  }
  activePortfolioSnapshot = portfolio;
  if (elements.portfolioSelect && portfolio.portfolio_name) {
    elements.portfolioSelect.value = portfolio.portfolio_name;
  }
  updatePortfolioLoadedAt(portfolio);
  renderPortfolioSyncOverview({ portfolio });
  elements.portfolioForm.elements.portfolioName.value =
    portfolio.portfolio_name || "";
  elements.portfolioForm.elements.portfolioValue.value =
    formatMoney(portfolio.portfolio_value, "KRW");
  elements.portfolioForm.elements.maxSinglePositionWeight.value =
    portfolio.max_single_position_weight ?? 0.2;
  elements.portfolioForm.elements.maxSectorWeight.value =
    portfolio.max_sector_weight ?? 0.35;
  elements.portfolioForm.elements.portfolioNotes.value = portfolio.notes || "";
  renderEditorRows(
    elements.holdingsEditor,
    sortHoldingsByMarketValue(portfolio.holdings || []),
    makePortfolioHoldingRow,
    () => ({ ticker: "", sector: "Unknown", theme_tags: [] })
  );
  clearHoldingRowsUnsaved();
  recalculatePortfolioValues();
  applyPortfolioViewState({ sort: true });
  refreshPortfolioSmartTable({ silent: true });
}

function kiwoomSyncSummaryLines(summary = {}) {
  const changes = Array.isArray(summary.changes) ? summary.changes : [];
  const skipped = Array.isArray(summary.skipped) ? summary.skipped : [];
  const changeDetail = (item) => {
    const name = item.name || item.ticker || "회사명 미확인";
    const quantity = `${formatNumber(item.old_quantity ?? 0)}주 → ${formatNumber(item.new_quantity ?? 0)}주`;
    const averageCost = `${formatMoney(item.old_average_cost, "KRW", "n/a")} → ${formatMoney(item.new_average_cost, "KRW", "n/a")}`;
    const marketValue = `${formatMoney(item.old_market_value, "KRW", "n/a")} → ${formatMoney(item.new_market_value, "KRW", "n/a")}`;
    return `- ${name}: 수량 ${quantity} · 평단 ${averageCost} · 평가금액 ${marketValue}`;
  };
  const changedLines = changes
    .filter((item) => item.changed)
    .slice(0, 10)
    .map(changeDetail);
  const confirmedLines = changes
    .filter((item) => !item.changed)
    .slice(0, 5)
    .map((item) => `- ${item.name || item.ticker || "회사명 미확인"}: ${formatNumber(item.new_quantity ?? 0)}주 동일 확인`);
  const protectedLines = skipped
    .filter((item) => item.reason === "manual_or_overseas_protected")
    .slice(0, 8)
    .map((item) => `- ${item.name || item.ticker}: ${formatNumber(item.quantity ?? 0)}주 보존`);
  const missingLines = skipped
    .filter((item) => item.reason !== "manual_or_overseas_protected")
    .slice(0, 8)
    .map((item) => `- ${item.name || item.ticker}: ${syncSkipReasonLabel(item.reason)}`);
  return [
    `- 변경: ${formatNumber(summary.updated_count || 0)}개 / 동일 확인: ${formatNumber(summary.confirmed_count || 0)}개 / 보존·미확인: ${formatNumber(summary.skipped_count || 0)}개`,
    ...(changedLines.length ? ["", "변경 내역", ...changedLines] : []),
    ...(confirmedLines.length ? ["", "동일 확인", ...confirmedLines] : []),
    ...(protectedLines.length ? ["", "해외·수동 종목 보호", ...protectedLines] : []),
    ...(missingLines.length ? ["", "미확인/설정 필요", ...missingLines] : []),
  ];
}

function syncSkipReasonLabel(reason) {
  const labels = {
    manual_or_overseas_protected: "해외·수동 종목이라 기존 수량 보존",
    kiwoom_domestic_missing: "키움 국내 잔고에서 미확인",
    kiwoom_not_configured: "키움 API 키/토큰 설정 필요",
    kiwoom_unavailable: "키움 국내 잔고 API 연결 실패",
  };
  return labels[reason] || "동기화 제외";
}

function clearPendingKiwoomDomesticSync() {
  pendingKiwoomDomesticSync = null;
  if (elements.portfolioKiwoomApplyButton) {
    elements.portfolioKiwoomApplyButton.hidden = true;
    elements.portfolioKiwoomApplyButton.disabled = true;
  }
  if (elements.portfolioKiwoomCancelButton) {
    elements.portfolioKiwoomCancelButton.hidden = true;
    elements.portfolioKiwoomCancelButton.disabled = true;
  }
  if (elements.portfolioKiwoomSyncButton) {
    elements.portfolioKiwoomSyncButton.textContent = "키움 국내 수량 확인";
  }
}

function setPendingKiwoomDomesticSync(portfolioName, result) {
  pendingKiwoomDomesticSync = {
    portfolioName,
    checkedAt: result?.sync_summary?.checked_at || "",
    summary: result?.sync_summary || {},
  };
  if (elements.portfolioKiwoomApplyButton) {
    elements.portfolioKiwoomApplyButton.hidden = false;
    elements.portfolioKiwoomApplyButton.disabled = false;
  }
  if (elements.portfolioKiwoomCancelButton) {
    elements.portfolioKiwoomCancelButton.hidden = false;
    elements.portfolioKiwoomCancelButton.disabled = false;
  }
  if (elements.portfolioKiwoomSyncButton) {
    elements.portfolioKiwoomSyncButton.textContent = "다시 확인";
  }
}

function portfolioRefreshStatusLines(portfolio) {
  const holdings = Array.isArray(portfolio?.holdings) ? portfolio.holdings : [];
  const unavailableTickers = holdings
    .filter((holding) => holding.price_refresh_status === "unavailable")
    .map((holding) => holding.name || holding.ticker)
    .filter(Boolean)
    .slice(0, 8);
  const skippedTickers = holdings
    .filter((holding) => holding.price_refresh_status === "skipped")
    .map((holding) => holding.name || holding.ticker)
    .filter(Boolean)
    .slice(0, 8);
  const counts = holdings.reduce(
    (acc, holding) => {
      const status = holding.price_refresh_status || "unknown";
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    },
    {}
  );
  const checkedCount = (counts.updated || 0) + (counts.confirmed || 0);
  const checkedAt = holdings
    .map((holding) => holding.price_checked_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  return [
    `- 실시간 가격 확인: ${formatNumber(checkedCount)}개 / 갱신 ${formatNumber(counts.updated || 0)}개 / 동일 확인 ${formatNumber(counts.confirmed || 0)}개`,
    counts.unavailable
      ? `- 가격 미확인: ${formatNumber(counts.unavailable)}개는 기존 값을 유지했습니다. ${unavailableTickers.length ? `(${unavailableTickers.join(", ")}${counts.unavailable > unavailableTickers.length ? " 외" : ""})` : ""}`
      : "- 가격 미확인: 없음",
    counts.skipped ? `- 가격 조회 제외: ${formatNumber(counts.skipped)}개 ${skippedTickers.length ? `(${skippedTickers.join(", ")}${counts.skipped > skippedTickers.length ? " 외" : ""})` : ""}` : "",
    checkedAt ? `- 가격 확인 시각: ${formatDateTime(checkedAt)}` : "",
  ].filter(Boolean);
}

function portfolioTableRefreshStatusLines(result) {
  const holdings = Array.isArray(result?.holdings) ? result.holdings : [];
  return portfolioRefreshStatusLines({ holdings });
}

function portfolioCurrencyDiagnosticLines(holdings = []) {
  const usdHoldings = holdings.filter((holding) => normalizeCurrency(holding.currency, holding.ticker) === "USD");
  if (!usdHoldings.length) {
    return [];
  }
  const missingFx = usdHoldings.filter((holding) => !Number.isFinite(Number(holding.fx_rate)) || Number(holding.fx_rate) <= 1);
  return [
    `- 해외 종목 환율 보정: ${formatNumber(usdHoldings.length)}개는 USD 현재가를 원화 평가금액으로 환산했습니다.`,
    missingFx.length
      ? `- 환율 추정 확인 필요: ${missingFx.map((holding) => holding.company_name || holding.name || holding.ticker).slice(0, 6).join(", ")}${missingFx.length > 6 ? " 외" : ""}`
      : "",
  ].filter(Boolean);
}

function activePortfolioNameForSmartTable() {
  return (
    elements.portfolioSelect?.value ||
    activePortfolioSnapshot?.portfolio_name ||
    elements.portfolioForm?.elements?.portfolioName?.value ||
    savedPortfolios[0]?.portfolio_name ||
    ""
  );
}

function smartMetricClass(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "portfolio-neutral";
  }
  if (numeric > 0) {
    return "portfolio-positive";
  }
  if (numeric < 0) {
    return "portfolio-negative";
  }
  return "portfolio-neutral";
}

function week52ProximityClass(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "smart-muted";
  }
  if (numeric >= 0.95) {
    return "smart-proximity-hot";
  }
  if (numeric >= 0.8) {
    return "smart-proximity-near";
  }
  return "smart-proximity-cool";
}

function formatSmartPercent(value, emptyValue = "미등록") {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return emptyValue;
  }
  return `${(Number(value) * 100).toLocaleString("ko-KR", {
    maximumFractionDigits: 1,
  })}%`;
}

function formatSmartPrice(value, currency, emptyValue = "미등록") {
  return formatMoney(value, currency || "KRW", emptyValue);
}

function sortSmartRows(rows) {
  const { key, direction } = portfolioSmartSort;
  const multiplier = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const left = a?.[key];
    const right = b?.[key];
    const leftNumber = Number(left);
    const rightNumber = Number(right);
    if (Number.isFinite(leftNumber) || Number.isFinite(rightNumber)) {
      return ((Number.isFinite(leftNumber) ? leftNumber : -Infinity) -
        (Number.isFinite(rightNumber) ? rightNumber : -Infinity)) * multiplier;
    }
    return String(left ?? "").localeCompare(String(right ?? ""), "ko-KR") * multiplier;
  });
}

function renderPortfolioSmartChart(rows = portfolioSmartRows) {
  if (!elements.portfolioSmartChart) {
    return;
  }
  if (!rows.length) {
    elements.portfolioSmartChart.innerHTML =
      '<p class="empty-state">저장된 포트폴리오를 불러오면 평가금액 그래프와 핵심 지표가 표시됩니다.</p>';
    return;
  }
  const topRows = [...rows]
    .sort((a, b) => (b.market_value || 0) - (a.market_value || 0))
    .slice(0, 8);
  const maxValue = Math.max(...topRows.map((row) => Number(row.market_value) || 0), 1);
  elements.portfolioSmartChart.innerHTML = topRows
    .map((row) => {
      const width = Math.max(4, Math.round(((Number(row.market_value) || 0) / maxValue) * 100));
      const proximity = row.week52_high_proximity === null || row.week52_high_proximity === undefined
        ? "52주 n/a"
        : `52주 ${formatSmartPercent(row.week52_high_proximity)}`;
      const target = row.target_upside === null || row.target_upside === undefined
        ? "목표가 미등록"
        : `목표 여력 ${formatSmartPercent(row.target_upside)}`;
      return `
        <div class="portfolio-chart-row">
          <div class="portfolio-chart-label">
            <strong>${escapeHtml(row.company_name || row.ticker)}</strong>
            <span>${escapeHtml(row.ticker)} · ${escapeHtml(proximity)} · ${escapeHtml(target)}</span>
          </div>
          <div class="portfolio-chart-track" aria-hidden="true">
            <span style="width:${width}%"></span>
          </div>
          <b>${escapeHtml(formatMoney(row.market_value, "KRW", "n/a"))}</b>
        </div>
      `;
    })
    .join("");
}

function smartTableCellClass(column) {
  if (column.align === "right") {
    return "smart-cell-right";
  }
  if (column.align === "center") {
    return "smart-cell-center";
  }
  return "";
}

const PORTFOLIO_SMART_COLUMNS = [
  {
    key: "company_name",
    label: "회사명",
    width: 190,
    render: (row) => row.company_name || row.ticker,
  },
  { key: "ticker", label: "티커", width: 88, align: "center", render: (row) => row.ticker },
  {
    key: "market_value",
    label: "평가금액",
    width: 132,
    align: "right",
    render: (row) => formatMoney(row.market_value, "KRW", "n/a"),
  },
  {
    key: "current_price",
    label: "현재가",
    width: 112,
    align: "right",
    render: (row) => formatSmartPrice(row.current_price, row.currency, "n/a"),
  },
  {
    key: "price_refresh_status",
    label: "가격 확인",
    width: 104,
    align: "center",
    html: true,
    valueClass: (row) => `smart-status-${portfolioRefreshStatusMeta(row.price_refresh_status).tone}`,
    render: (row) => portfolioRefreshStatusBadgeHtml(row),
  },
  {
    key: "freshness_status",
    label: "자료 최신성",
    width: 112,
    align: "center",
    html: true,
    valueClass: (row) => `smart-status-${row.freshness_tone || "muted"}`,
    render: (row) => freshnessStatusBadgeHtml(row),
  },
  {
    key: "average_cost",
    label: "매입가",
    width: 112,
    align: "right",
    render: (row) => formatSmartPrice(row.average_cost, row.currency, "n/a"),
  },
  {
    key: "quantity",
    label: "수량",
    width: 86,
    align: "center",
    render: (row) => formatNumber(row.quantity),
  },
  {
    key: "unrealized_gain",
    label: "수익",
    width: 122,
    align: "right",
    valueClass: (row) => smartMetricClass(row.unrealized_gain),
    render: (row) => formatMoney(row.unrealized_gain, "KRW", "n/a"),
  },
  {
    key: "unrealized_return",
    label: "수익률",
    width: 86,
    align: "center",
    valueClass: (row) => smartMetricClass(row.unrealized_return),
    render: (row) => toPercent(row.unrealized_return),
  },
  {
    key: "week52_high",
    label: "52주 최고가",
    width: 116,
    align: "right",
    render: (row) => formatSmartPrice(row.week52_high, row.currency),
  },
  {
    key: "week52_high_proximity",
    label: "52주 근접도",
    width: 116,
    align: "center",
    valueClass: (row) => week52ProximityClass(row.week52_high_proximity),
    render: (row) => formatSmartPercent(row.week52_high_proximity),
  },
  {
    key: "target_price",
    label: "목표주가",
    width: 108,
    align: "right",
    render: (row) => formatSmartPrice(row.target_price, row.target_price_currency || row.currency),
  },
  {
    key: "target_upside",
    label: "목표 여력",
    width: 98,
    align: "center",
    valueClass: (row) => smartMetricClass(row.target_upside),
    render: (row) => formatSmartPercent(row.target_upside),
  },
  {
    key: "target_price_source_file",
    label: "목표 출처",
    width: 138,
    render: (row) => row.target_price_source_type || row.target_price_source_file || "미등록",
  },
  {
    key: "data_readiness_score",
    label: "데이터 준비도",
    width: 114,
    align: "center",
    valueClass: (row) => week52ProximityClass(row.data_readiness_score),
    render: (row) => formatSmartPercent(row.data_readiness_score),
  },
  {
    key: "rag_connected",
    label: "RAG/논거",
    width: 108,
    align: "center",
    valueClass: (row) => (row.rag_connected && row.thesis_snapshot_connected ? "smart-proximity-near" : "smart-proximity-cool"),
    render: (row) => {
      const rag = row.rag_connected ? `RAG ${row.rag_document_count || 0}` : "RAG 필요";
      const thesis = row.thesis_snapshot_connected ? "논거 있음" : "논거 필요";
      return `${rag} · ${thesis}`;
    },
  },
  {
    key: "next_action",
    label: "다음 액션",
    width: 220,
    render: (row) => row.next_action || "새 자료 유입 시 갱신",
  },
];

function sortConsensusRows(rows) {
  const { key, direction } = consensusScanSort;
  const multiplier = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const left = a?.[key];
    const right = b?.[key];
    const leftNumber = Number(left);
    const rightNumber = Number(right);
    if (Number.isFinite(leftNumber) || Number.isFinite(rightNumber)) {
      return ((Number.isFinite(leftNumber) ? leftNumber : -Infinity) -
        (Number.isFinite(rightNumber) ? rightNumber : -Infinity)) * multiplier;
    }
    return String(left ?? "").localeCompare(String(right ?? ""), "ko-KR") * multiplier;
  });
}

const TARGET_CONSENSUS_COLUMNS = [
  {
    key: "company_name",
    label: "회사명",
    width: 170,
    render: (row) => row.company_name || row.ticker,
  },
  { key: "ticker", label: "티커", width: 82, align: "center", render: (row) => row.ticker },
  {
    key: "current_price",
    label: "현재가",
    width: 108,
    align: "right",
    render: (row) => formatSmartPrice(row.current_price, row.currency, "미확인"),
  },
  {
    key: "consensus_target_price",
    label: "목표주가",
    width: 112,
    align: "right",
    render: (row) => formatSmartPrice(row.consensus_target_price, row.consensus_target_currency || row.currency, "미등록"),
  },
  {
    key: "target_upside",
    label: "상승여력",
    width: 96,
    align: "center",
    valueClass: (row) => smartMetricClass(row.target_upside),
    render: (row) => formatSmartPercent(row.target_upside, "계산 보류"),
  },
  {
    key: "valuation_signal",
    label: "판정",
    width: 126,
    align: "center",
    valueClass: (row) => smartMetricClass(row.target_upside),
    render: (row) => row.valuation_signal || "계산 보류",
  },
  {
    key: "source_count",
    label: "자료수",
    width: 76,
    align: "center",
    render: (row) => formatNumber(row.source_count || 0),
  },
  {
    key: "confidence",
    label: "신뢰도",
    width: 88,
    align: "center",
    valueClass: (row) => week52ProximityClass(row.confidence),
    render: (row) => formatSmartPercent(row.confidence, "n/a"),
  },
  {
    key: "market_value",
    label: "평가금액",
    width: 120,
    align: "right",
    render: (row) => formatMoney(row.market_value, "KRW", "관심"),
  },
  {
    key: "source_scope",
    label: "범위",
    width: 150,
    render: (row) => row.source_scope || (row.interest ? "관심종목" : "저장 데이터"),
  },
  {
    key: "latest_source_file",
    label: "최근 출처",
    width: 180,
    render: (row) => row.latest_source_file || "목표주가 자료 없음",
  },
];

function renderTargetConsensusTable(rows = consensusScanRows) {
  if (!elements.portfolioConsensusTable) {
    return;
  }
  const sortedRows = sortConsensusRows(rows);
  if (!sortedRows.length) {
    elements.portfolioConsensusTable.innerHTML =
      '<p class="empty-state">컨센서스 스캔을 실행하면 현재가 대비 목표주가 상승여력 순으로 표시됩니다.</p>';
    return;
  }
  const headerHtml = TARGET_CONSENSUS_COLUMNS.map((column) => {
    const sorted = consensusScanSort.key === column.key;
    const sortMark = sorted ? (consensusScanSort.direction === "asc" ? " ▲" : " ▼") : "";
    return `
      <th style="width:${column.width}px" data-consensus-sort="${escapeHtml(column.key)}">
        <button type="button">${escapeHtml(column.label + sortMark)}</button>
      </th>
    `;
  }).join("");
  const bodyHtml = sortedRows
    .map((row) => {
      const cells = TARGET_CONSENSUS_COLUMNS.map((column) => {
        const valueClass = column.valueClass ? column.valueClass(row) : "";
        const title = [
          column.key === "latest_source_file" ? row.latest_context : "",
          column.key === "target_upside" ? `목표가 범위 ${formatSmartPrice(row.consensus_target_low, row.currency, "n/a")}~${formatSmartPrice(row.consensus_target_high, row.currency, "n/a")}` : "",
        ].filter(Boolean).join(" · ");
        return `
          <td class="${smartTableCellClass(column)} ${valueClass}" title="${escapeHtml(title)}">
            ${column.html ? column.render(row) : escapeHtml(column.render(row))}
          </td>
        `;
      }).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  elements.portfolioConsensusTable.innerHTML = `
    <div class="smart-table-caption">증권사 목표주가 컨센서스 대비 저평가 순위</div>
    <table class="smart-table">
      <thead><tr>${headerHtml}</tr></thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;
}

function renderPortfolioSmartTable(rows = portfolioSmartRows) {
  if (!elements.portfolioSmartTable) {
    return;
  }
  const sortedRows = sortSmartRows(rows);
  if (!sortedRows.length) {
    elements.portfolioSmartTable.innerHTML =
      '<p class="empty-state">표시할 포트폴리오 지표가 없습니다. 포트폴리오를 저장하거나 불러오세요.</p>';
    return;
  }
  const headerHtml = PORTFOLIO_SMART_COLUMNS.map((column) => {
    const sorted = portfolioSmartSort.key === column.key;
    const sortMark = sorted ? (portfolioSmartSort.direction === "asc" ? " ▲" : " ▼") : "";
    return `
      <th style="width:${column.width}px" data-smart-sort="${escapeHtml(column.key)}">
        <button type="button">${escapeHtml(column.label + sortMark)}</button>
        <span class="column-resizer" data-resize-column="${escapeHtml(column.key)}"></span>
      </th>
    `;
  }).join("");
  const bodyHtml = sortedRows
    .map((row) => {
      const cells = PORTFOLIO_SMART_COLUMNS.map((column) => {
        const valueClass = column.valueClass ? column.valueClass(row) : "";
        const title = [
          column.key === "week52_high_proximity" ? row.week52_status : "",
          column.key === "target_upside" ? row.target_status : "",
          column.key === "target_price" ? row.target_price_source_file : "",
          column.key === "price_refresh_status" ? [
            portfolioRefreshStatusText(row),
            row.price_source ? `출처 ${row.price_source}` : "",
            row.market_value_note || "",
          ].filter(Boolean).join(" · ") : "",
          column.key === "freshness_status" ? row.freshness_summary : "",
          column.key === "rag_connected" ? row.thesis_summary : "",
          column.key === "next_action" ? row.thesis_summary : "",
        ]
          .filter(Boolean)
          .join(" · ");
        return `
          <td class="${smartTableCellClass(column)} ${valueClass}" title="${escapeHtml(title)}">
            ${column.html ? column.render(row) : escapeHtml(column.render(row))}
          </td>
        `;
      }).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  elements.portfolioSmartTable.innerHTML = `
    <table class="smart-table">
      <thead><tr>${headerHtml}</tr></thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;
}

async function runTargetConsensusScan({ silent = false } = {}) {
  if (!elements.portfolioConsensusTable) {
    return null;
  }
  const portfolioName = activePortfolioNameForSmartTable() || "__all__";
  syncApiBaseUrl();
  if (!silent) {
    elements.portfolioConsensusTable.innerHTML =
      '<p class="empty-state">증권사 목표주가와 현재가를 비교하는 중입니다...</p>';
  }
  try {
    const result = await fetchTargetConsensusScan(token(), {
      portfolioName,
      includeInterests: true,
      refreshMissingPrices: false,
    });
    consensusScanRows = result?.rows || [];
    renderTargetConsensusTable(consensusScanRows);
    if (!silent) {
      setOutput(result);
    }
    return result;
  } catch (error) {
    if (!silent) {
      setError(error);
    } else {
      elements.portfolioConsensusTable.innerHTML =
        '<p class="empty-state">컨센서스 스캔을 보류했습니다. 저장된 리포트와 현재가 데이터를 확인하세요.</p>';
    }
    return null;
  }
}

function pricePointToSvg(point, index, points, minPrice, maxPrice, width, height, padding) {
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const price = Number(point.close);
  const spread = maxPrice - minPrice || 1;
  const x = padding + (points.length <= 1 ? 0 : (index / (points.length - 1)) * usableWidth);
  const y = padding + (1 - (price - minPrice) / spread) * usableHeight;
  return `${x.toFixed(2)},${y.toFixed(2)}`;
}

function renderChartVisualization(result) {
  if (!elements.chartVisualization) {
    return;
  }
  if (!result || result.module !== "naver_chart_analysis") {
    elements.chartVisualization.innerHTML =
      '<p class="empty-state">차트 분석을 실행하면 가격 흐름, 거래량, 보조지표 요약 그래프가 표시됩니다.</p>';
    return;
  }
  const prices = (result.recent_prices || []).filter((item) => Number.isFinite(Number(item.close)));
  const indicators = result.latest_indicators || {};
  if (!prices.length) {
    elements.chartVisualization.innerHTML =
      '<p class="empty-state">그래프로 표시할 가격 데이터가 없습니다.</p>';
    return;
  }
  const width = 760;
  const height = 240;
  const padding = 24;
  const closes = prices.map((item) => Number(item.close));
  const volumes = prices.map((item) => Number(item.volume) || 0);
  const minPrice = Math.min(...closes);
  const maxPrice = Math.max(...closes);
  const maxVolume = Math.max(...volumes, 1);
  const linePoints = prices
    .map((point, index) =>
      pricePointToSvg(point, index, prices, minPrice, maxPrice, width, height, padding)
    )
    .join(" ");
  const volumeBars = prices
    .map((point, index) => {
      const x = padding + (prices.length <= 1 ? 0 : (index / (prices.length - 1)) * (width - padding * 2));
      const barHeight = Math.max(2, ((Number(point.volume) || 0) / maxVolume) * 42);
      const y = height - padding - barHeight;
      return `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="5" height="${barHeight.toFixed(2)}" rx="2"></rect>`;
    })
    .join("");
  const first = prices[0];
  const last = prices[prices.length - 1];
  const priceChange = Number(last.close) - Number(first.close);
  const priceChangeRate = Number(first.close) ? priceChange / Number(first.close) : null;
  const rsiClass =
    Number(indicators.rsi14) >= 70
      ? "chart-chip-warning"
      : Number(indicators.rsi14) <= 30
      ? "chart-chip-info"
      : "chart-chip-neutral";
  const bandClass =
    Number(indicators.bollinger_position) >= 0.85
      ? "chart-chip-warning"
      : Number(indicators.bollinger_position) <= 0.15
      ? "chart-chip-info"
      : "chart-chip-neutral";
  const macdClass =
    Number(indicators.macd_histogram) > 0
      ? "chart-chip-positive"
      : Number(indicators.macd_histogram) < 0
      ? "chart-chip-negative"
      : "chart-chip-neutral";
  const dmiClass =
    Number(indicators.plus_di14) > Number(indicators.minus_di14)
      ? "chart-chip-positive"
      : "chart-chip-negative";
  elements.chartVisualization.innerHTML = `
    <div class="chart-visual-header">
      <div>
        <span>네이버 일봉 차트</span>
        <strong>${escapeHtml(result.company_name || result.ticker)} ${escapeHtml(result.ticker ? `(${result.ticker})` : "")}</strong>
      </div>
      <div class="${smartMetricClass(priceChangeRate)}">
        <span>${escapeHtml(last.date || result.as_of || "기준일 미확인")}</span>
        <strong>${escapeHtml(formatMoney(last.close, "KRW", "n/a"))}</strong>
        <small>${escapeHtml(formatMoney(priceChange, "KRW", "0원"))} · ${escapeHtml(formatSmartPercent(priceChangeRate, "n/a"))}</small>
      </div>
    </div>
    <svg class="price-chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="최근 가격과 거래량 그래프">
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" class="chart-axis"></line>
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="chart-axis"></line>
      <g class="chart-volume-bars">${volumeBars}</g>
      <polyline class="chart-price-line" points="${linePoints}"></polyline>
      <circle class="chart-last-dot" cx="${linePoints.split(" ").pop()?.split(",")[0] || 0}" cy="${linePoints.split(" ").pop()?.split(",")[1] || 0}" r="5"></circle>
      <text x="${padding}" y="16" class="chart-label">${escapeHtml(formatMoney(maxPrice, "KRW", "n/a"))}</text>
      <text x="${padding}" y="${height - 6}" class="chart-label">${escapeHtml(formatMoney(minPrice, "KRW", "n/a"))}</text>
    </svg>
    <div class="chart-chip-grid">
      <span class="${rsiClass}"><b>RSI 14</b>${escapeHtml(formatNullable(indicators.rsi14))}</span>
      <span class="${bandClass}"><b>볼린저 위치</b>${escapeHtml(formatSmartPercent(indicators.bollinger_position, "n/a"))}</span>
      <span class="${macdClass}"><b>MACD 히스토그램</b>${escapeHtml(formatNullable(indicators.macd_histogram))}</span>
      <span class="${dmiClass}"><b>DMI</b>+DI ${escapeHtml(formatNullable(indicators.plus_di14))} / -DI ${escapeHtml(formatNullable(indicators.minus_di14))}</span>
      <span class="chart-chip-neutral"><b>20일선</b>${escapeHtml(formatMoney(indicators.ma20, "KRW", "n/a"))}</span>
      <span class="chart-chip-neutral"><b>60일선</b>${escapeHtml(formatMoney(indicators.ma60, "KRW", "n/a"))}</span>
    </div>
  `;
}

function resizeSmartTableColumn(event) {
  const handle = event.target.closest("[data-resize-column]");
  if (!handle) {
    return;
  }
  event.preventDefault();
  const key = handle.dataset.resizeColumn;
  const table = handle.closest("table");
  const header = handle.closest("th");
  const startX = event.clientX;
  const startWidth = header.getBoundingClientRect().width;
  function onMove(moveEvent) {
    const width = Math.max(72, Math.round(startWidth + moveEvent.clientX - startX));
    table.querySelectorAll(`[data-smart-sort="${CSS.escape(key)}"]`).forEach((cell) => {
      cell.style.width = `${width}px`;
    });
    const columnIndex = PORTFOLIO_SMART_COLUMNS.findIndex((column) => column.key === key);
    if (columnIndex >= 0) {
      table.querySelectorAll(`tbody tr`).forEach((row) => {
        const cell = row.children[columnIndex];
        if (cell) {
          cell.style.width = `${width}px`;
        }
      });
    }
  }
  function onUp() {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  }
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp, { once: true });
}

async function refreshPortfolioSmartTable({
  silent = false,
  forcePriceRefresh = false,
  persistRefresh = false,
} = {}) {
  if (!elements.portfolioSmartTable || !elements.portfolioSmartChart) {
    return null;
  }
  const portfolioName = activePortfolioNameForSmartTable();
  if (!portfolioName) {
    portfolioSmartRows = [];
    renderPortfolioSmartChart([]);
    renderPortfolioSmartTable([]);
    return null;
  }
  syncApiBaseUrl();
  if (!silent) {
    elements.portfolioSmartTable.innerHTML =
      '<p class="empty-state">서버에서 최신 현재가와 계산 지표를 불러오는 중입니다...</p>';
  }
  try {
    const result = await fetchPortfolioIntelligentTable(token(), portfolioName, {
      refreshPrices: true,
      forcePriceRefresh,
      persistRefresh,
    });
    portfolioSmartRows = result?.holdings || [];
    renderPortfolioSmartChart(portfolioSmartRows);
    renderPortfolioSmartTable(portfolioSmartRows);
    if (!silent) {
      setOutput(
        [
          "# 지능형 테이블 새로고침 완료",
          "",
          `- 포트폴리오: ${result?.portfolio_name || portfolioName}`,
          `- 보유 종목: ${formatNumber(result?.holding_count || portfolioSmartRows.length)}개`,
          ...portfolioTableRefreshStatusLines(result),
          ...portfolioCurrencyDiagnosticLines(portfolioSmartRows),
          "- 현재가, 평가금액, 52주 최고가 근접도, 목표주가 근접도, RAG/논거 준비도를 다시 계산했습니다.",
        ].join("\n")
      );
    }
    return result;
  } catch (error) {
    if (!silent) {
      setError(error);
    } else {
      elements.portfolioSmartTable.innerHTML =
        '<p class="empty-state">지능형 테이블 계산을 보류했습니다. 포트폴리오 저장 후 다시 시도하세요.</p>';
    }
    return null;
  }
}

async function refreshPortfolioPerformance({ silent = false } = {}) {
  const portfolioName = activePortfolioNameForSmartTable();
  if (!portfolioName) {
    renderPortfolioPerformanceOverview(null);
    if (!silent) {
      setError(new Error("기간 수익 비교를 실행할 저장 포트폴리오를 먼저 선택하세요."));
    }
    return null;
  }
  syncApiBaseUrl();
  if (elements.portfolioPerformanceOverview && !silent) {
    elements.portfolioPerformanceOverview.innerHTML =
      '<p class="empty-state">기간별 가격 히스토리와 현재 평가금액을 비교하는 중입니다...</p>';
  }
  try {
    const result = await fetchPortfolioPerformance(token(), portfolioName);
    renderPortfolioPerformanceOverview(result);
    if (!silent) {
      setOutput(result);
    }
    return result;
  } catch (error) {
    if (elements.portfolioPerformanceOverview) {
      const message = error?.message || "저장 포트폴리오와 가격 데이터 연결을 확인하세요.";
      elements.portfolioPerformanceOverview.innerHTML = `
        <div class="portfolio-performance-header">
          <div>
            <span>기간 수익 비교</span>
            <strong>계산 보류</strong>
            <p>저장 현재가 사용 · 외부 가격 히스토리 응답 지연으로 화면 표시를 우선했습니다.</p>
          </div>
          <div class="portfolio-performance-metrics">
            <span>정확도 <b>확인 필요</b></span>
            <span>가격 차이 <b>확인 보류</b></span>
          </div>
        </div>
        <div class="portfolio-performance-grid">
          ${["최근 1주일", "최근 1개월", "최근 6개월", "최근 1년"].map((label) => `
            <article class="portfolio-performance-card neutral">
              <span>${label}</span>
              <strong>계산 보류</strong>
              <p>가격 히스토리 응답 확인 후 다시 계산합니다.</p>
            </article>
          `).join("")}
        </div>
        <p class="portfolio-performance-note">기간 수익 비교를 불러오지 못했습니다. ${escapeHtml(message)}</p>`;
    }
    if (!silent) {
      setError(error);
    }
    return null;
  }
}

function renderPortfolioOptions(portfolios = [], selectedName = "") {
  if (!elements.portfolioSelect) {
    return;
  }
  const previousSelection = selectedName || elements.portfolioSelect.value || "";
  elements.portfolioSelect.replaceChildren();
  if (elements.tradePortfolioSelect) {
    elements.tradePortfolioSelect.replaceChildren(
      new Option("저장 포트폴리오 자동 선택", ""),
      new Option("직접 입력", "__manual__")
    );
  }
  if (!portfolios.length) {
    elements.portfolioSelect.append(
      new Option("저장된 내 포트폴리오 없음", "")
    );
    return;
  }
  portfolios.forEach((item) => {
    elements.portfolioSelect.append(
      new Option(
        `${item.portfolio_name} · ${item.holding_count || 0}개`,
        item.portfolio_name
      )
    );
    if (elements.tradePortfolioSelect) {
      elements.tradePortfolioSelect.append(
        new Option(
          `${item.portfolio_name} · ${formatMoney(item.portfolio_value, "KRW", "n/a")}`,
          item.portfolio_name
        )
      );
    }
  });
  if (
    previousSelection &&
    portfolios.some((item) => item.portfolio_name === previousSelection)
  ) {
    elements.portfolioSelect.value = previousSelection;
  }
}

function findSavedPortfolioByName(portfolioName = "") {
  const normalizedName = String(portfolioName || "").trim();
  if (!normalizedName) {
    return null;
  }
  return (
    savedPortfolios.find((item) => item.portfolio_name === normalizedName) ||
    null
  );
}

function selectedTradePortfolio() {
  const selectedName = elements.tradePortfolioSelect?.value || "";
  if (selectedName && selectedName !== "__manual__") {
    return savedPortfolios.find((item) => item.portfolio_name === selectedName) || null;
  }
  if (selectedName === "__manual__") {
    return null;
  }
  return activePortfolioSnapshot || savedPortfolios[0] || null;
}

function buildTradePortfolioContext(portfolio, ticker, thresholds = {}) {
  const warningWeightThreshold = Number.isFinite(Number(thresholds.warningWeightThreshold))
    ? Number(thresholds.warningWeightThreshold) / 100
    : 0.1;
  const highWeightThreshold = Number.isFinite(Number(thresholds.highWeightThreshold))
    ? Number(thresholds.highWeightThreshold) / 100
    : 0.2;
  const lossWarningThreshold = Number.isFinite(Number(thresholds.lossWarningThreshold))
    ? Number(thresholds.lossWarningThreshold) / 100
    : -0.15;
  if (!portfolio) {
    return {
      summary: "기준 포트폴리오 없음",
      warnings: ["포트폴리오 기준이 없어서 기존 보유 비중을 반영하지 못했습니다."],
    };
  }
  const normalizedTicker = normalizeTickerDraft(ticker);
  const holding = (portfolio.holdings || []).find(
    (item) => normalizeTickerDraft(item.ticker) === normalizedTicker
  );
  if (!holding) {
    return {
      summary: `${portfolio.portfolio_name || "선택 포트폴리오"}에 현재 보유 없음`,
      warnings: [],
    };
  }
  const weightText = holding.weight === undefined || holding.weight === null
    ? "비중 n/a"
    : `비중 ${toPercent(holding.weight)}`;
  const valueText = formatMoney(holding.market_value, "KRW", "평가금액 n/a");
  const gainText = holding.unrealized_gain === undefined || holding.unrealized_gain === null
    ? "손익 n/a"
    : `손익 ${formatMoney(holding.unrealized_gain, "KRW", "n/a")} (${toPercent(holding.unrealized_return)})`;
  const warnings = [];
  const weight = Number(holding.weight);
  if (Number.isFinite(weight)) {
    if (weight >= highWeightThreshold) {
      warnings.push(`단일 종목 비중이 ${toPercent(weight)}로 높습니다. 추가 진입 전 포트폴리오 리스크 스캔을 먼저 확인하세요.`);
    } else if (weight >= warningWeightThreshold) {
      warnings.push(`단일 종목 비중이 ${toPercent(weight)}입니다. 추가 매수는 분할 진입과 손절 기준을 더 엄격히 적용하세요.`);
    }
  }
  if (Number(holding.unrealized_return) < lossWarningThreshold) {
    warnings.push(`현재 손실률이 ${toPercent(holding.unrealized_return)}입니다. 물타기인지, 투자 논거가 강화된 추가 진입인지 먼저 구분하세요.`);
  }
  return {
    summary: `${portfolio.portfolio_name || "선택 포트폴리오"} 현재 보유: ${holding.name || holding.ticker || normalizedTicker} · ${formatNumber(holding.quantity)}주 · ${weightText} · ${valueText} · ${gainText}`,
    warnings,
  };
}

function syncTradePortfolioSizeFromActivePortfolio() {
  const input = elements.tradeForm?.elements?.portfolioSize;
  if (!input || input.value) {
    return;
  }
  if (elements.tradePortfolioSelect?.value === "__manual__") {
    return;
  }
  const portfolio = selectedTradePortfolio();
  const portfolioValue = Number(portfolio?.portfolio_value);
  if (Number.isFinite(portfolioValue) && portfolioValue > 0) {
    input.value = Math.round(portfolioValue);
    input.title = `${portfolio.portfolio_name || "저장 포트폴리오"} 총액을 자동 적용했습니다.`;
  }
}

async function refreshPortfolioStore(keepOutput = true, preferredPortfolioName = "") {
  syncApiBaseUrl();
  const currentSelection =
    preferredPortfolioName ||
    elements.portfolioSelect?.value ||
    activePortfolioSnapshot?.portfolio_name ||
    elements.portfolioForm?.elements?.portfolioName?.value ||
    "";
  const response = await fetchPortfolios(token());
  const portfolios = response?.portfolios || [];
  savedPortfolios = [...portfolios].sort((a, b) =>
    String(a.portfolio_name || "").localeCompare(String(b.portfolio_name || ""), "ko-KR")
  );
  renderPortfolioOptions(savedPortfolios, currentSelection);
  renderDashboardTickerPicker();
  const portfolioToShow =
    findSavedPortfolioByName(currentSelection) ||
    findSavedPortfolioByName(response?.active_portfolio?.portfolio_name) ||
    response?.active_portfolio ||
    savedPortfolios[0] ||
    null;
  if (portfolioToShow) {
    fillPortfolioForm(portfolioToShow);
  } else {
    activePortfolioSnapshot = null;
    updatePortfolioLoadedAt(null);
  }
  if (lastDashboard) {
    renderDashboardCards(lastDashboard);
  }
  syncTradePortfolioSizeFromActivePortfolio();
  const optionalSummaries = await Promise.allSettled([
    withTimeout(
      refreshPortfolioAnalysisOverview({ silent: true }),
      5000,
      "포트폴리오 연결 상태 조회가 지연되어 초기 화면에서는 건너뜁니다."
    ),
    withTimeout(
      refreshPortfolioTeamReportQueue({ silent: true }),
      5000,
      "기준 리포트 큐 조회가 지연되어 초기 화면에서는 건너뜁니다."
    ),
  ]);
  optionalSummaries
    .filter((result) => result.status === "rejected")
    .forEach((result) => console.warn(result.reason?.message || result.reason));
  if (!keepOutput) {
    setOutput(response);
  }
  return response;
}

async function runRiskScanForPortfolio(portfolio) {
  if (!portfolio) {
    throw new Error("리스크 스캔할 저장 포트폴리오를 선택하세요.");
  }
  return runPortfolioRiskScan(token(), {
    portfolioName: portfolio.portfolio_name,
    holdings: portfolio.holdings || [],
    portfolioValue: portfolio.portfolio_value,
    maxSinglePositionWeight: portfolio.max_single_position_weight ?? 0.2,
    maxSectorWeight: portfolio.max_sector_weight ?? 0.35,
    saveResult: !isClickSmokeMode(),
  });
}

function fillInterestsForm(response) {
  const tickers = response?.tickers || [];
  const sectors = response?.sectors || [];
  lastInterestList = response || { tickers, sectors };
  renderEditorRowsExact(
    elements.interestTickerEditor,
    tickers.map(({ verification, created_at, updated_at, ...item }) => ({
      ...item,
      companyName: verification?.company_name || "",
      verification,
    })),
    makeInterestTickerSummaryRow,
    "추가된 관심종목이 없습니다. 위 입력칸에서 1개씩 추가하세요."
  );
  renderEditorRowsExact(
    elements.interestSectorEditor,
    sectors.map(({ created_at, updated_at, ...item }) => item),
    makeInterestSectorSummaryRow,
    "추가된 관심섹터가 없습니다. 위 입력칸에서 1개씩 추가하세요."
  );
  resetInterestDrafts();
  updateInterestsSummary(response);
  renderDashboardTickerPicker();
}

async function refreshInterestList(keepOutput = true) {
  syncApiBaseUrl();
  const response = await fetchInterests(token());
  fillInterestsForm(response);
  if (!keepOutput) {
    setOutput(response);
  }
  return response;
}

async function normalizeInterestTickersForSave(tickers = []) {
  const normalized = [];
  const seen = new Set();
  for (const item of tickers) {
    const inputValue = String(item.ticker || item.companyName || "").trim();
    if (!inputValue) {
      continue;
    }
    const lookupValue = resolveLocalTickerAlias(inputValue);
    const cachedVerification =
      item.verification && typeof item.verification === "object" ? item.verification : null;
    let verification = cachedVerification?.official_symbol ? cachedVerification : null;
    if (!verification) {
      verification = {
        status: "pending",
        verified: false,
        official_symbol: normalizeTickerDraft(lookupValue || inputValue),
        company_name: item.companyName || inputValue,
        verification_source: "save_first_pending_verification",
        message: "먼저 관심종목에 저장합니다. 공식 인증은 저장 후 백엔드 로컬 사전과 티커 진단에서 보강합니다.",
      };
    }
    const officialSymbol = verification?.verified
      ? normalizeTickerDraft(verification.official_symbol)
      : normalizeTickerDraft(lookupValue || inputValue);
    if (!officialSymbol || seen.has(officialSymbol)) {
      continue;
    }
    const tags = [...(item.tags || [])];
    if (!verification?.verified && !tags.includes("verification_pending")) {
      tags.push("verification_pending");
    }
    seen.add(officialSymbol);
    normalized.push({
      ticker: officialSymbol,
      priority: item.priority || "medium",
      thesis: item.thesis || null,
      notes: item.notes || null,
      tags,
      verification,
    });
  }
  return normalized;
}

async function saveCurrentInterestList({ quiet = false } = {}) {
  syncApiBaseUrl();
  const tickers = await normalizeInterestTickersForSave(collectInterestTickers());
  const result = await saveInterests(token(), {
    tickers,
    sectors: collectInterestSectors(),
  });
  fillInterestsForm(result);
  resetInterestTickerDraft();
  resetInterestSectorDraft();
  if (!quiet) {
    setOutput(
      [
        `# 관심종목/섹터 저장 완료`,
        ``,
        `- 관심종목: ${(result.tickers || []).length}개`,
        `- 관심섹터: ${(result.sectors || []).length}개`,
        `- 저장 위치: ${result.storage_path || "확인 안 됨"}`,
        `- 수정 시각: ${result.updated_at || "미확인"}`,
        ``,
        `상장회사는 티커 또는 회사명으로 입력하면 공식 코드로 인증해 저장합니다.`,
      ].join("\n")
    );
  }
  await runSecondaryRefresh("관심종목/섹터 상태 새로고침", () => refreshStatus(false));
  return result;
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === "") {
    return null;
  }
  const normalized = String(value)
    .replace(/,/g, "")
    .replace(/[₩$]/g, "")
    .replace(/원/g, "")
    .replace(/%/g, "")
    .trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isNaN(parsed) ? null : parsed;
}

function findInjectedDataValue(snapshot, label) {
  const point = (snapshot?.data_points || []).find((item) => item.label === label);
  return point?.value ?? null;
}

function applyLatestSnapshotToForms(snapshot) {
  const lastPrice = Number(findInjectedDataValue(snapshot, "last_price"));
  if (!Number.isFinite(lastPrice) || lastPrice <= 0) {
    return null;
  }
  const currentPriceInput = elements.tradeForm.querySelector(
    'input[name="currentPrice"]'
  );
  if (currentPriceInput) {
    currentPriceInput.value = String(lastPrice);
    currentPriceInput.placeholder = `KIS 현재가 ${lastPrice}`;
  }
  return lastPrice;
}

async function fetchAndApplyLatestPrice(ticker) {
  const snapshot = await fetchLatestDataSnapshot(token(), ticker);
  const lastPrice = applyLatestSnapshotToForms(snapshot);
  return { snapshot, lastPrice };
}

function readTextFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("파일을 읽지 못했습니다."));
    reader.readAsText(file);
  });
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",").pop() : result);
    };
    reader.onerror = () => reject(reader.error || new Error("파일을 읽지 못했습니다."));
    reader.readAsDataURL(file);
  });
}

const TEXT_FILE_EXTENSIONS = new Set([
  "txt",
  "md",
  "markdown",
  "csv",
  "tsv",
  "json",
  "log",
  "xml",
  "html",
  "htm",
  "yaml",
  "yml",
  "ini",
  "rtf",
]);

function isLikelyTextFile(file) {
  const mimeType = String(file?.type || "").toLowerCase();
  if (mimeType.startsWith("text/")) {
    return true;
  }
  if (
    [
      "application/json",
      "application/xml",
      "application/x-ndjson",
      "application/csv",
    ].includes(mimeType)
  ) {
    return true;
  }
  const extension = String(file?.name || "").split(".").pop().toLowerCase();
  return TEXT_FILE_EXTENSIONS.has(extension);
}

function isPdfFile(file) {
  const mimeType = String(file?.type || "").toLowerCase();
  const extension = String(file?.name || "").split(".").pop().toLowerCase();
  return mimeType === "application/pdf" || extension === "pdf";
}

function isImageFile(file) {
  const mimeType = String(file?.type || "").toLowerCase();
  const extension = String(file?.name || "").split(".").pop().toLowerCase();
  return mimeType.startsWith("image/") || ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"].includes(extension);
}

function fileProcessingLabel(file) {
  if (!file) {
    return "";
  }
  if (isImageFile(file)) {
    return "이미지 OCR";
  }
  if (isPdfFile(file)) {
    return "PDF 본문 추출";
  }
  if (isLikelyTextFile(file)) {
    return "텍스트 파일 읽기";
  }
  return "파일 저장";
}

function updateCaptureFileStatus(file, state = "ready", detail = "") {
  if (!elements.captureFileStatus) {
    return;
  }
  if (!file && state !== "processing") {
    elements.captureFileStatus.hidden = true;
    elements.captureFileStatus.classList.remove("is-processing", "is-ready");
    elements.captureFileStatus.innerHTML = "";
    return;
  }
  const label = fileProcessingLabel(file);
  const fileName = file?.name || "선택한 파일";
  const sizeText = file ? formatFileSize(file.size) : "";
  const isProcessing = state === "processing";
  elements.captureFileStatus.hidden = false;
  elements.captureFileStatus.classList.toggle("is-processing", isProcessing);
  elements.captureFileStatus.classList.toggle("is-ready", !isProcessing);
  const message =
    detail ||
    (isProcessing
      ? `${label || "파일"} 분석 중... 창을 닫거나 새로고침하지 말고 잠시 기다려주세요.`
      : `${label || "파일"} 대기 중 · 저장을 누르면 서버 분석을 시작합니다.`);
  elements.captureFileStatus.innerHTML = `
    ${isProcessing ? '<span class="file-processing-spinner" aria-hidden="true"></span>' : ""}
    <span>
      <strong>${escapeHtml(message)}</strong>
      ${file ? `<small>${escapeHtml(fileName)} · ${escapeHtml(sizeText)}</small>` : ""}
    </span>
  `;
}

function setCaptureFormProcessing(isProcessing, file = null) {
  if (!elements.captureForm) {
    return;
  }
  const controls = elements.captureForm.querySelectorAll("button, input, select, textarea");
  controls.forEach((control) => {
    control.disabled = Boolean(isProcessing);
  });
  if (isProcessing) {
    const label = fileProcessingLabel(file);
    updateCaptureFileStatus(
      file,
      "processing",
      file && isImageFile(file)
        ? "이미지 OCR 분석 중... Tesseract 처리 시간이 길어질 수 있습니다."
        : file && isPdfFile(file)
          ? "PDF 본문 추출 중... 문서가 크면 잠시 걸릴 수 있습니다."
          : `${label || "자료"} 처리 중... 잠시 기다려주세요.`
    );
  } else {
    const fileInput = elements.captureForm.querySelector('input[name="researchFile"]');
    updateCaptureFileStatus(fileInput?.files?.[0] || null);
  }
}

async function readResearchFilePayload(file) {
  if (!file) {
    return {
      fileName: null,
      fileMimeType: null,
      fileSize: null,
      fileContentBase64: null,
      extractedText: "",
      extractionNote: "",
    };
  }

  const fileContentBase64 = await readFileAsBase64(file);
  let extractedText = "";
  let extractionNote = "원본 파일을 첨부로 저장했습니다.";
  if (isLikelyTextFile(file)) {
    extractedText = await readTextFile(file);
    if (extractedText.length > 120000) {
      extractedText = `${extractedText.slice(0, 120000)}\n\n[본문이 길어 앞부분 120,000자만 분석에 사용했습니다. 원본 파일은 별도로 저장했습니다.]`;
    }
    extractionNote = "텍스트 본문을 추출해 분석에 사용하고 원본 파일도 저장했습니다.";
  } else if (isPdfFile(file)) {
    extractionNote = "PDF 파일은 서버에서 본문 텍스트 추출을 시도하고, 원본 PDF도 함께 저장합니다.";
  } else if (isImageFile(file)) {
    extractionNote = "이미지 파일은 서버에서 OCR 텍스트 추출을 시도하고, 원본 이미지도 함께 저장합니다.";
  } else {
    extractionNote = "비텍스트 파일로 판단되어 원본 파일을 저장하고 파일 메타데이터를 분석에 사용했습니다.";
  }

  return {
    fileName: file.name,
    fileMimeType: file.type || "application/octet-stream",
    fileSize: file.size,
    fileContentBase64,
    extractedText,
    extractionNote,
  };
}

function applyImportedPortfolioHoldings(holdings = []) {
  if (!holdings.length) {
    return;
  }
  renderEditorRows(
    elements.holdingsEditor,
    sortHoldingsByMarketValue(holdings).map((holding) => ({
      ticker: holding.ticker,
      name: holding.name || "",
      quantity: holding.quantity ?? "",
      average_cost: holding.average_cost ?? "",
      current_price: holding.current_price ?? "",
      market_value: holding.market_value ?? "",
      weight: holding.weight ?? "",
      sector: holding.sector || "Unknown",
      theme_tags: holding.theme_tags || [],
    })),
    makePortfolioHoldingRow,
    () => ({ ticker: "", sector: "Unknown", theme_tags: [] })
  );
  recalculatePortfolioValues();
  applyPortfolioViewState({ sort: true });
}

function normalizeTickerDraft(value) {
  return String(value ?? "").trim().toUpperCase();
}

function resolveLocalTickerAlias(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return "";
  }
  const manualAliases = {
    한국금융지주: "071050",
    한국투자금융지주: "071050",
    KoreaInvestmentHoldings: "071050",
    씨이랩: "189330",
    씨아이랩: "189330",
    XIIlab: "189330",
    XIILAB: "189330",
    오이솔루션: "138080",
    Oesolution: "138080",
    OE솔루션: "138080",
    RF머트리얼즈: "327260",
    알에프머트리얼즈: "327260",
    RFMaterials: "327260",
    "RF Materials": "327260",
    성호전자: "043260",
    SunghoElectronics: "043260",
    "Sungho Electronics": "043260",
  };
  if (manualAliases[raw]) {
    return manualAliases[raw];
  }
  const normalized = normalizeTickerDraft(raw);
  if (manualAliases[normalized]) {
    return manualAliases[normalized];
  }
  if (KOREAN_TICKER_DISPLAY_NAMES[normalized]) {
    return normalized;
  }
  const compactRaw = raw.replace(/\s+/g, "").toLowerCase();
  const matched = Object.entries(KOREAN_TICKER_DISPLAY_NAMES).find(([, name]) => {
    const compactName = String(name || "").replace(/\s+/g, "").toLowerCase();
    return compactName === compactRaw || compactName.includes(compactRaw) || compactRaw.includes(compactName);
  });
  return matched?.[0] || raw;
}

const SPECIAL_MEMORY_KEYS = new Set([
  "MACRO",
  "MARKET",
  "MARKET-US",
  "MARKET-KR",
  "MARKET-GLOBAL",
  "SECTOR",
  "POLICY",
  "RATES",
  "FLOWS",
  "INBOX",
  "CORE-GROWTH",
  "SECTOR-US-BALANCED",
  "COMPOUNDER-KR-ALL-QUALITY-GROWTH",
]);

function normalizeStorageKey(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return activeTicker || DEFAULT_TICKER;
  }
  const upper = raw.toUpperCase();
  if (SPECIAL_MEMORY_KEYS.has(upper)) {
    return upper;
  }
  if (/^[A-Z0-9._-]{1,60}$/.test(upper)) {
    return upper;
  }
  return (
    upper
      .replace(/[^\p{L}\p{N}_-]+/gu, "-")
      .replace(/^-+|-+$/g, "") || upper
  );
}

function isTickerLikeMemoryKey(value) {
  const key = normalizeStorageKey(value);
  if (!key || SPECIAL_MEMORY_KEYS.has(key)) {
    return false;
  }
  return /^\d{6}$/.test(key) || /^[A-Z][A-Z0-9.]{0,9}$/.test(key);
}

async function resolveMemoryLookupKey(value) {
  const key = normalizeStorageKey(value);
  if (!isTickerLikeMemoryKey(key)) {
    return key;
  }
  try {
    const verification = await certifyTickerForWorkflow(key);
    return verification.official_symbol || key;
  } catch (error) {
    console.warn("저장 데이터 티커 인증 실패, 원 입력 키로 조회합니다:", error);
    return key;
  }
}

function normalizeTickerInput(value) {
  const raw = String(value || "").trim();
  const normalized = normalizeTickerDraft(raw);
  if (normalized && normalized !== "UNKNOWN") {
    return normalized;
  }
  return raw || activeTicker || DEFAULT_TICKER;
}

function displayTickerForInput(value) {
  const normalizedTicker = normalizeTickerDraft(value);
  if (!normalizedTicker || normalizedTicker === "UNKNOWN") {
    return String(value || DEFAULT_TICKER_DISPLAY || "");
  }
  if (/^\d{6}$/.test(normalizedTicker) || KOREAN_TICKER_DISPLAY_NAMES[normalizedTicker]) {
    if (lastTickerVerification?.official_symbol === normalizedTicker && lastTickerVerification.company_name) {
      return lastTickerVerification.company_name;
    }
    if (lastTickerProfile?.ticker === normalizedTicker && lastTickerProfile.company_name) {
      return lastTickerProfile.company_name;
    }
    return KOREAN_TICKER_DISPLAY_NAMES[normalizedTicker] || normalizedTicker;
  }
  return normalizedTicker;
}

function tickerLabelForOutput(value) {
  const normalizedTicker = normalizeTickerDraft(value);
  if (!normalizedTicker || normalizedTicker === "UNKNOWN") {
    return String(value || DEFAULT_TICKER_DISPLAY || "");
  }
  const displayName = displayTickerForInput(normalizedTicker);
  return displayName === normalizedTicker ? normalizedTicker : `${displayName}(${normalizedTicker})`;
}

function normalizeTeamStyleValue(value) {
  const raw = String(value || "").trim();
  const styleMap = {
    균형형: "balanced",
    성장주: "growth",
    가치주: "value",
    트레이딩: "trading",
    balanced: "balanced",
    growth: "growth",
    value: "value",
    trading: "trading",
  };
  return styleMap[raw] || "balanced";
}

function syncTickerInputs(ticker, options = {}) {
  const normalizedTicker = normalizeTickerDraft(ticker);
  if (!normalizedTicker && (options.allowEmpty || !activeTicker)) {
    const previousTicker = activeTicker;
    activeTicker = "";
    if (!options.skipDashboardInvalidation) {
      invalidateTickerDashboard(previousTicker, activeTicker);
    }
    renderDashboardTickerPicker();
    return;
  }

  const previousTicker = activeTicker;
  activeTicker = normalizedTicker || activeTicker || DEFAULT_TICKER;
  const displayValue = displayTickerForInput(activeTicker);
  document.querySelectorAll('input[name="ticker"]').forEach((input) => {
    if (input === options.source || input.closest(".editor-list")) {
      return;
    }
    input.value = displayValue;
  });
  if (!options.skipDashboardInvalidation) {
    invalidateTickerDashboard(previousTicker, activeTicker);
  }
  renderDashboardTickerPicker();
}

function confirmTickerForWorkflow(ticker) {
  const normalizedTicker = normalizeTickerInput(ticker);
  const changedTicker = normalizedTicker !== lastConfirmedTicker;
  syncTickerInputs(normalizedTicker);
  if (changedTicker) {
    resetTickerSpecificDrafts(normalizedTicker);
    lastConfirmedTicker = normalizedTicker;
  }
  return normalizedTicker;
}

async function certifyTickerForWorkflow(ticker, options = {}) {
  const normalizedTicker = confirmTickerForWorkflow(ticker);
  const verification = await verifyTickerSymbol(token(), normalizedTicker, {
    fast: options.fast === true,
  });
  setTickerVerificationStatus(verification);
  if (!verification?.verified) {
    throw new Error(verification?.message || `${normalizedTicker} 공식 티커 인증에 실패했습니다.`);
  }
  syncTickerInputs(verification.official_symbol);
  activeTicker = verification.official_symbol;
  lastConfirmedTicker = verification.official_symbol;
  lastTickerProfile = await fetchTickerProfile(token(), verification.official_symbol, {
    refreshExternal: options.refreshExternal !== false,
  });
  syncTickerInputs(verification.official_symbol, { skipDashboardInvalidation: true });
  applyTickerProfileToForms(lastTickerProfile);
  return verification;
}

function setIfBlankOrGeneric(input, value, genericValues = []) {
  if (!input || value === undefined || value === null || value === "") {
    return;
  }
  const currentValue = input.value.trim();
  if (!currentValue || genericValues.includes(currentValue)) {
    input.value = value;
  }
}

function setPlaceholder(input, value) {
  if (input && value) {
    input.placeholder = value;
  }
}

function applyTickerProfileToForms(profile) {
  if (!profile) {
    return;
  }
  const kpis = profile.watch_kpis || [];
  const ticker = profile.ticker || activeTicker;
  const displayName = profile.country === "KR" ? profile.company_name : ticker;
  const latestEarnings = profile.latest_earnings_profile || {};
  const focusInput = elements.teamForm.querySelector('input[name="focusArea"]');
  setIfBlankOrGeneric(focusInput, profile.analysis_focus, [
    "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크",
    "AI 수요, 밸류에이션, 매매 전략, 포트폴리오 리스크",
  ]);
  setPlaceholder(focusInput, profile.analysis_focus || `${ticker} 중점 분석 입력`);

  const chartTicker = elements.chartForm?.querySelector('input[name="ticker"]');
  if (chartTicker && profile.country === "KR") {
    chartTicker.value = profile.company_name || displayTickerForInput(ticker);
    chartTicker.placeholder = "예: 삼양식품 또는 003230";
  }

  const marketStructure = elements.tradeForm.querySelector('input[name="marketStructure"]');
  setPlaceholder(
    marketStructure,
    `${profile.company_name} 시장 구조, 섹터 흐름, 이벤트 리스크 입력`
  );

  const earningsQuarter = elements.earningsForm.querySelector('input[name="quarter"]');
  if (earningsQuarter && profile.latest_reported_quarter) {
    earningsQuarter.value = profile.latest_reported_quarter;
  }
  setPlaceholder(
    earningsQuarter,
    profile.latest_reported_quarter
      ? `${displayName} 최신 발표 실적: ${profile.latest_reported_quarter}`
      : `${displayName} 최근 실적 분기 입력`
  );

  const earningsReportDate = elements.earningsForm.querySelector(
    'input[name="earningsReportDate"]'
  );
  if (earningsReportDate && profile.latest_reported_earnings_date) {
    earningsReportDate.value = profile.latest_reported_earnings_date;
  }

  const previousEarningsDate = elements.earningsForm.querySelector(
    'input[name="previousEarningsDate"]'
  );
  if (previousEarningsDate && profile.previous_earnings_date) {
    previousEarningsDate.value = profile.previous_earnings_date;
  }

  const nextEarningsDate = elements.earningsForm.querySelector(
    'input[name="nextEarningsDate"]'
  );
  if (nextEarningsDate && profile.next_earnings_date) {
    nextEarningsDate.value = profile.next_earnings_date;
  }

  const marketContext = elements.earningsForm.querySelector('input[name="marketContext"]');
  setIfBlankOrGeneric(marketContext, latestEarnings.market_context);
  setPlaceholder(
    marketContext,
    `${profile.industry || profile.sector || ticker} 업종 기대치, 주가 위치, 발표 전 컨센서스`
  );

  const previousSummary = elements.earningsForm.querySelector('[name="previousEarningsSummary"]');
  setIfBlankOrGeneric(previousSummary, latestEarnings.previous_earnings_summary);
  setPlaceholder(
    previousSummary,
    `직전 실적에서 ${kpis.slice(0, 3).join(", ") || "매출, 마진, 현금흐름"} 흐름을 입력`
  );

  const nextGuidance = elements.earningsForm.querySelector('[name="nextEarningsGuidance"]');
  setIfBlankOrGeneric(nextGuidance, latestEarnings.next_earnings_guidance);
  setPlaceholder(
    nextGuidance,
    `${
      profile.next_earnings_date
        ? `다음 실적 예정일(${profile.next_earnings_date}) 전 확인할 KPI`
        : "다음 실적 전 확인할 KPI"
    }: ${kpis.join(", ") || "회사별 핵심 KPI"}`
  );

  const keyNumbers = elements.earningsForm.querySelector('[name="keyNumbers"]');
  if (
    keyNumbers &&
    !keyNumbers.value.trim() &&
    latestEarnings.key_numbers &&
    Object.keys(latestEarnings.key_numbers).length
  ) {
    keyNumbers.value = JSON.stringify(latestEarnings.key_numbers, null, 2);
  }
  const keyNumberExample = kpis.length
    ? `{ "${kpis[0]}": "입력", "${kpis[1] || "가이던스"}": "입력" }`
    : `{ "핵심 KPI": "입력" }`;
  setPlaceholder(keyNumbers, `예: ${keyNumberExample}`);

  const priceReaction = elements.earningsForm.querySelector('input[name="priceReaction"]');
  setIfBlankOrGeneric(priceReaction, latestEarnings.price_reaction);

  const epsReported = elements.earningsForm.querySelector('input[name="epsReported"]');
  setIfBlankOrGeneric(epsReported, latestEarnings.eps_reported);

  const epsExpected = elements.earningsForm.querySelector('input[name="epsExpected"]');
  setIfBlankOrGeneric(epsExpected, latestEarnings.eps_expected);

  const revenueReported = elements.earningsForm.querySelector('input[name="revenueReported"]');
  setIfBlankOrGeneric(revenueReported, latestEarnings.revenue_reported);

  const revenueExpected = elements.earningsForm.querySelector('input[name="revenueExpected"]');
  setIfBlankOrGeneric(revenueExpected, latestEarnings.revenue_expected);

  const guidanceChange = elements.earningsForm.querySelector('select[name="guidanceChange"]');
  if (guidanceChange && latestEarnings.guidance_change) {
    guidanceChange.value = latestEarnings.guidance_change;
  }

  const managementTone = elements.earningsForm.querySelector('input[name="managementTone"]');
  setIfBlankOrGeneric(managementTone, latestEarnings.management_tone);

  const captureContent = elements.captureForm.querySelector('textarea[name="rawContent"]');
  setPlaceholder(
    captureContent,
    `${profile.company_name} 관련 메모 또는 티커 없는 전체 시황, 섹터 전망, 거시 경제 자료를 그대로 붙여넣으세요.`
  );
}

function resetTickerSpecificDrafts(ticker) {
  lastTickerProfile = null;
  const displayName = displayTickerForInput(ticker);
  const focusInput = elements.teamForm.querySelector('input[name="focusArea"]');
  if (focusInput) {
    focusInput.value = "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크";
  }

  const tradePrice = elements.tradeForm.querySelector('input[name="currentPrice"]');
  if (tradePrice) {
    tradePrice.value = "";
    tradePrice.placeholder = `${displayName} 현재가 입력`;
  }

  const marketStructure = elements.tradeForm.querySelector('input[name="marketStructure"]');
  if (marketStructure) {
    marketStructure.value = "";
    marketStructure.placeholder = `${displayName} 시장 구조 입력`;
  }

  const earningsQuarter = elements.earningsForm.querySelector('input[name="quarter"]');
  if (earningsQuarter) {
    earningsQuarter.value = "최신 발표 실적";
    earningsQuarter.placeholder = `${displayName} 공식 최신 발표 실적 기본 사용`;
  }

  ["earningsReportDate", "nextEarningsDate", "previousEarningsDate"].forEach((name) => {
    const input = elements.earningsForm.querySelector(`input[name="${name}"]`);
    if (input) {
      input.value = "";
    }
  });

  const priceReaction = elements.earningsForm.querySelector('input[name="priceReaction"]');
  if (priceReaction) {
    priceReaction.value = "";
    priceReaction.placeholder = "예: +5.2%, -3.1%, 보합";
  }

  ["epsReported", "epsExpected", "revenueReported", "revenueExpected"].forEach((name) => {
    const input = elements.earningsForm.querySelector(`input[name="${name}"]`);
    if (input) {
      input.value = "";
    }
  });

  const managementTone = elements.earningsForm.querySelector('input[name="managementTone"]');
  if (managementTone) {
    managementTone.value = "";
  }
  const marketContext = elements.earningsForm.querySelector('input[name="marketContext"]');
  if (marketContext) {
    marketContext.value = "";
  }

  ["previousEarningsSummary", "nextEarningsGuidance", "keyNumbers"].forEach((name) => {
    const input = elements.earningsForm.querySelector(`[name="${name}"]`);
    if (input) {
      input.value = "";
    }
  });

  const captureContent = elements.captureForm.querySelector('textarea[name="rawContent"]');
  if (captureContent) {
    captureContent.value = "";
    captureContent.placeholder = `${displayName} 관련 자료 또는 티커 없는 거시/섹터/시장/정책/금리/수급 자료를 그대로 붙여넣으세요.`;
  }
}

function tickerSymbolNotice(ticker) {
  if (lastTickerVerification?.verified) {
    return `${lastTickerVerification.official_symbol} 인증: ${lastTickerVerification.company_name} · ${lastTickerVerification.exchange}`;
  }
  if (lastTickerVerification && !lastTickerVerification.verified) {
    return lastTickerVerification.message;
  }
  return "";
}

function translateVerificationSource(source) {
  const labels = {
    local_official_registry: "로컬 공식 등록",
    fmp_company_profile: "FMP 자동 인증",
    dynamic_ticker_cache: "자동 인증 캐시",
    kind_krx_corp_list: "KRX/KIND 상장사 목록",
    nasdaq_trader_nasdaqlisted: "Nasdaq Trader 상장 목록",
    nasdaq_trader_otherlisted: "Nasdaq Trader 기타 상장 목록",
  };
  return labels[source] || source || "출처 미확인";
}

function profileNeedsEnrichment(profile) {
  const limitations = profile?.data_limitations || [];
  return limitations.some((item) =>
    /외부 데이터|후속 보강|전용 KPI|실적 캘린더/.test(String(item))
  );
}

function tickerVerificationCard(dashboard) {
  const verification = dashboard?.ticker_verification;
  const profile = dashboard?.ticker_profile;
  if (!verification?.verified) {
    return `
      <article class="dashboard-card needs_action">
        <span>티커 인증</span>
        <strong>미인증</strong>
        <p>${escapeHtml(verification?.message || "공식 티커 확인이 필요합니다.")}</p>
      </article>
    `;
  }

  const needsEnrichment = profileNeedsEnrichment(profile);
  const source = translateVerificationSource(verification.verification_source);
  return `
    <article class="dashboard-card ${needsEnrichment ? "warning" : "ok"}">
      <span>티커 인증</span>
      <strong>${escapeHtml(source)}</strong>
      <p>${escapeHtml(verification.company_name)} · ${escapeHtml(verification.exchange)}<br />${
        needsEnrichment
          ? "전용 KPI와 실적 캘린더는 추가 보강이 필요합니다."
          : "전용 프로필을 바로 사용할 수 있습니다."
      }</p>
    </article>
  `;
}

async function rawRequest(path) {
  const response = await fetch(`${elements.apiBaseUrl.value.trim()}${path}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function refreshStatus(updateOutput = true) {
  syncApiBaseUrl();
  elements.backendStatus.textContent = "확인 중";
  elements.providerStatus.textContent = "확인 중";
  elements.manifestStatus.textContent = "확인 중";

  try {
    const root = await rawRequest("/");
    elements.backendStatus.textContent = root.message ? "정상" : "응답";
    markBackendHealthy();
  } catch (error) {
    elements.backendStatus.textContent = "오류";
    elements.providerStatus.textContent = "연결 끊김";
    elements.manifestStatus.textContent = "확인 실패";
    lastBackendHealthState = "down";
    setError(error);
    await notifyBackendHealthWarning(error, { source: "root_health_check" });
    return;
  }

  const provider = await fetchDataProviderStatus();
  elements.providerStatus.textContent = provider
    ? `${translateProviderMode(provider.mode)} (${provider.providers?.length || 0})`
    : "오류";
  if (!provider) {
    await notifyBackendHealthWarning(new Error("데이터 프로바이더 상태 조회 실패"), {
      source: "data_provider_status_check",
    });
  }

  const manifest = await fetchResearchManifest(token());
  if (!manifest) {
    elements.manifestStatus.textContent = "오류";
    await notifyBackendHealthWarning(new Error("저장 데이터 Manifest 조회 실패"), {
      source: "manifest_status_check",
    });
  } else {
    elements.manifestStatus.textContent = `${manifest.length}개`;
  }

  if (updateOutput) {
    setOutput({ provider, manifest_count: manifest?.length || 0 });
  }
}
async function loadTickerDashboard(ticker = activeTicker, options = {}) {
  const requestedTicker = normalizeTickerInput(ticker);
  if (!requestedTicker) {
    renderDashboardEmptyState();
    throw new Error("대시보드에서 조회할 종목을 먼저 선택하거나 입력하세요.");
  }
  const verification = await certifyTickerForWorkflow(requestedTicker, {
    fast: true,
    refreshExternal: false,
  });
  if (options.requestId && options.requestId !== dashboardRequestSeq) {
    return null;
  }
  syncTickerInputs(verification.official_symbol, { skipDashboardInvalidation: true });
  const result = await fetchTickerDashboard(token(), verification.official_symbol);
  if (options.requestId && options.requestId !== dashboardRequestSeq) {
    return null;
  }
  lastDashboard = result;
  renderDashboardCards(result);
  rememberDashboardTicker(
    verification.official_symbol,
    verification.company_name || result?.ticker_profile?.company_name || result?.ticker
  );
  if (!options.quiet) {
    setOutput(result);
  }
  await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  return result;
}

async function refreshDashboardCardsOnly(ticker = activeTicker) {
  const requestedTicker = normalizeTickerInput(ticker);
  if (!requestedTicker) {
    renderDashboardEmptyState();
    throw new Error("새로고침할 대시보드 종목을 먼저 선택하거나 입력하세요.");
  }
  const verification = await certifyTickerForWorkflow(requestedTicker, {
    fast: true,
    refreshExternal: false,
  });
  syncTickerInputs(verification.official_symbol, { skipDashboardInvalidation: true });
  const result = await fetchTickerDashboard(token(), verification.official_symbol);
  lastDashboard = result;
  renderDashboardCards(result);
  await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  return result;
}


function summarizeSystemCheckValue(label, value) {
  if (!value) {
    return "응답 없음";
  }
  if (label.includes("데이터 프로바이더")) {
    const providers = Array.isArray(value.providers) ? value.providers : [];
    const ready = providers.filter((provider) => provider.ready).length;
    return `${value.mode || "unknown"} 모드 · 준비 ${ready}/${providers.length}개`;
  }
  if (label.includes("저장 데이터")) {
    const entries = Array.isArray(value)
      ? value
      : Array.isArray(value.files)
        ? value.files
        : Array.isArray(value.entries)
          ? value.entries
          : Array.isArray(value.items)
            ? value.items
            : Array.isArray(value.reports)
              ? value.reports
              : Array.isArray(value.manifest)
                ? value.manifest
                : [];
    const explicitCount = Number(
      value.total_files ?? value.total_count ?? value.file_count ?? value.entry_count ?? entries.length
    );
    const count = Number.isFinite(explicitCount) ? explicitCount : entries.length;
    return `manifest 항목 ${count.toLocaleString("ko-KR")}개`;
  }
  if (label.includes("포트폴리오")) {
    const portfolios = Array.isArray(value.portfolios) ? value.portfolios : [];
    const holdingCount = portfolios.reduce((sum, item) => sum + Number(item.holding_count || 0), 0);
    return `저장 포트폴리오 ${portfolios.length}개 · 연결 보유종목 ${holdingCount}개`;
  }
  if (label.includes("관심종목/섹터")) {
    const tickers = Array.isArray(value.tickers) ? value.tickers.length : 0;
    const sectors = Array.isArray(value.sectors) ? value.sectors.length : 0;
    return `관심종목 ${tickers}개 · 관심섹터 ${sectors}개`;
  }
  if (label.includes("DART")) {
    const failures = Array.isArray(value.last_failures) ? value.last_failures.length : 0;
    const daily = value.daily_check || {};
    const universe = value.target_universe || {};
    const dailyFailures = Number(daily.failure_count || daily.failed_tickers?.length || 0);
    const excludedCount = Number(daily.excluded_count || universe.excluded_tickers?.length || 0);
    const checkedCount = Number(daily.checked_count || 0);
    const currentTargetCount = Number(daily.current_target_count || value.target_tickers?.length || 0);
    const coverageText = currentTargetCount
      ? `커버리지 ${checkedCount}/${currentTargetCount}`
      : "커버리지 대상 없음";
    const reliability = daily.reliability_status || "신뢰도 미확인";
    const dailyState = daily.due
      ? "오늘 점검 필요"
      : dailyFailures
      ? `오늘 점검 부분 완료(실패 ${dailyFailures}개)`
      : "오늘 점검 완료";
    const portfolioCount = universe.portfolio_tickers?.length || 0;
    const interestCount = universe.interest_tickers?.length || 0;
    const failureNames = (value.last_failures || [])
      .slice(0, 3)
      .map((item) => `${item.ticker || "대상 미확인"} ${item.category ? `(${item.category})` : ""}`.trim())
      .join(", ");
    return `감시 대상 ${value.target_tickers?.length || 0}개(보유 ${portfolioCount} · 관심 ${interestCount}) · 제외 ${excludedCount}개 · ${dailyState} · ${reliability} · ${coverageText} · 저장 공시 ${value.entry_count || 0}개 · 최근 실패 ${failures}건${
      failureNames ? ` · 확인: ${failureNames}` : ""
    }`;
  }
  if (label.includes("네이버 리서치")) {
    const pdfCounts = value.pdf_extraction_counts || {};
    const marketJournal = value.market_close_journal || {};
    const sourceLabel = marketJournal.source_origin === "naver_research_auto" ? "자동 반영" : "수동/기타";
    return `캐시 ${value.entry_count || 0}건 · RAG ${value.active_rag_count || 0}건 · 저장 누락 ${value.missing_storage_count || 0}건 · PDF 성공 ${pdfCounts.success || 0}건/미분석 ${pdfCounts.unknown || 0}건 · 시장일지 ${marketJournal.last_run_date || "미실행"} · ${sourceLabel} ${marketJournal.daily_time || "08:30"}`;
  }
  if (label.includes("자동화")) {
    const digest = value.dashboard_digest || {};
    return `Pulls 대상 ${digest.target_count || 0}개 · RAG ${digest.rag_document_count || 0}개 · Dossier ${digest.dossier_count || 0}개`;
  }
  if (label.includes("일일 브리핑")) {
    const nextActions = Array.isArray(value.next_actions) ? value.next_actions.length : 0;
    const priorityReviews = Array.isArray(value.portfolio_overview?.priority_reviews)
      ? value.portfolio_overview.priority_reviews.length
      : 0;
    return `다음 액션 ${nextActions}개 · 우선 검토 ${priorityReviews}개`;
  }
  if (label.includes("OCR")) {
    const state = value?.ready ? "연결됨" : "미연결";
    const languages = value?.languages_ready ? "kor+eng 확인" : "언어팩 확인 필요";
    return `${state} · ${languages} · ${value?.message || value?.next_action || "상태 미확인"} ${
      value?.ready ? "" : `· 조치: ${value?.next_action || "Tesseract 설치 상태 확인"}`
    }`.trim();
  }
  if (label.includes("대표 대시보드")) {
    return `${value.ticker || "대상 미확인"} · 저장 데이터 ${value.file_count || 0}개 · 경고 ${(value.data_warnings || []).length}개`;
  }
  return value.status || value.module || "정상 응답";
}

function formatConsoleSystemCheckResult(payload) {
  const checks = payload.checks || [];
  const failed = checks.filter((item) => item.status !== "성공");
  const ocrCheck = checks.find((item) => item.label.includes("OCR"));
  const dartCheck = checks.find((item) => item.label.includes("DART"));
  const naverCheck = checks.find((item) => item.label.includes("네이버 리서치"));
  const dartValue = dartCheck?.value || {};
  const dartDaily = dartValue.daily_check || {};
  const dartExcluded = dartDaily.excluded_tickers || dartValue.target_universe?.excluded_tickers || [];
  const dartFailures = dartValue.last_failures || [];
  const okCount = checks.length - failed.length;
  const ocrLimits = ocrCheck?.value?.limits || {};
  return [
    `# 전체 시스템 점검 완료`,
    ``,
    `- **점검 시각:** ${formatDateTime(payload.generated_at)}`,
    `- **점검 결과:** ${okCount}/${checks.length}개 정상`,
    `- **대표 대시보드 대상:** ${payload.dashboard_candidate || "선택 가능한 종목 없음"}`,
    ``,
    `## 점검 항목`,
    ...checks.map(
      (item, index) =>
        `${index + 1}. **${item.label}** - ${item.status} (${item.elapsed_ms}ms)\n   ${compactOutputText(item.summary, 220)}`
    ),
    ``,
    `## OCR/이미지 업로드 상태`,
    ocrCheck
      ? `- **현재 상태:** ${ocrCheck.status} · ${ocrCheck.summary}`
      : `- **현재 상태:** OCR 점검 결과를 불러오지 못했습니다.`,
    ocrLimits.message ? `- **처리 한계:** ${ocrLimits.message}` : "",
    `- **미연결 시 저장 방식:** 이미지는 원본 파일과 파일명/크기/이미지 크기 메타데이터로 저장됩니다. 이미지 속 글자는 분석 본문으로 쓰지 않고, 결과에는 OCR 미연결/보강 필요 경고가 표시됩니다.`,
    `- **권장 조치:** Tesseract와 kor+eng 언어팩 설치 여부를 먼저 확인하고, 설치 전에는 이미지 속 본문을 텍스트로 함께 붙여넣으세요.`,
    ``,
    `## DART 공시 감시 상태`,
    dartCheck
      ? `- **현재 상태:** ${dartCheck.status} · ${dartCheck.summary}`
      : `- **현재 상태:** DART 점검 결과를 불러오지 못했습니다.`,
    `- **신뢰도:** ${dartDaily.reliability_status || "미확인"} · ${dartDaily.reliability_message || "점검 커버리지 정보가 없습니다."}`,
    `- **다음 예정:** ${dartDaily.next_check_after ? formatDateTime(dartDaily.next_check_after) : "미확인"}`,
    `- **감시 제외:** ${formatNumber(dartExcluded.length)}개${
      dartExcluded.length
        ? ` · ${dartExcluded
            .slice(0, 6)
            .map((item) => `${item.name || item.ticker || "대상 미확인"}(${item.reason || "제외"})`)
            .join(", ")}${dartExcluded.length > 6 ? " ..." : ""}`
        : ""
    }`,
    ``,
    `## 네이버 리서치/시장일지 상태`,
    naverCheck
      ? `- **현재 상태:** ${naverCheck.status} · ${naverCheck.summary}`
      : `- **현재 상태:** 네이버 리서치 점검 결과를 불러오지 못했습니다.`,
    naverCheck?.value?.market_close_journal
      ? `- **마지막 국내 마감 시황:** ${naverCheck.value.market_close_journal.source_title || "미확인"} · ${naverCheck.value.market_close_journal.last_run_at ? formatDateTime(naverCheck.value.market_close_journal.last_run_at) : "미실행"}`
      : `- **마지막 국내 마감 시황:** 미확인`,
    `- **실패 상세:** ${
      dartFailures.length
        ? dartFailures
            .slice(0, 6)
            .map((item) => `${item.ticker || "대상 미확인"} · ${item.category || "provider_error"} · ${item.next_action || item.error || "확인 필요"}`)
            .join(" / ")
        : "최근 실패 없음"
    }`,
    `- **재점검:** 대시보드 DART 카드의 '공시 재점검' 버튼으로 즉시 다시 확인할 수 있습니다.`,
    ``,
    `## 1번~5번 처리 상태`,
    `- **1. 버튼/화면 회귀 점검:** 상태, 저장 데이터, 포트폴리오, 관심종목/섹터, 자동화, 일일 브리핑, 대표 대시보드를 한 번에 확인했습니다.`,
    `- **2. 문서 추출 품질:** 정보 입력/시장일지/워크플로우 결과에서 품질 점수, 본문 길이, OCR/표형 줄, 다음 조치가 표시되는지 확인 대상으로 묶었습니다.`,
    `- **3. RAG·자동 분류:** RAG 문서 수, Dossier, 중복 제거 상태를 자동화 상태에서 확인했습니다.`,
    `- **4. 포트폴리오·대시보드 연결:** 저장 포트폴리오와 관심종목/섹터 후보를 다시 렌더링하고 대표 대시보드까지 조회했습니다.`,
    `- **5. 일일 리서치 자동화:** 일일 브리핑과 자동화 상태를 확인해 대시보드 전달 가능 상태를 점검했습니다.`,
    failed.length ? `` : ``,
    failed.length ? `## 확인 필요` : `## 다음 단계`,
    ...(failed.length
      ? failed.map((item) => `- ${item.label}: ${item.summary}`)
      : [
          `- 실제 버튼 클릭 회귀 테스트 범위를 넓히려면 이 점검을 기준으로 차트/실적/포트폴리오 개별 실행까지 순차 자동화하면 됩니다.`,
        ]),
  ].join("\n");
}

async function runConsoleSystemCheck() {
  syncApiBaseUrl();
  startOutputLoading("전체 시스템 점검 실행 중", [
    "백엔드와 데이터 프로바이더 확인",
    "저장 데이터와 RAG 상태 확인",
    "OCR/Tesseract 연결 상태 확인",
    "포트폴리오와 관심종목/섹터 후보 갱신",
    "리서치 자동화와 일일 브리핑 확인",
    "대표 종목 대시보드 연결 점검",
  ]);

  const checks = [];
  const runCheck = async (label, callback) => {
    const started = performance.now();
    try {
      const value = await callback();
      const derivedStatus =
        !value ||
        value?.ready === false ||
        value?.ok === false ||
        value?.status === "warning" ||
        value?.daily_check?.due ||
        value?.daily_check?.status === "partial_success"
          ? "확인 필요"
          : "성공";
      checks.push({
        label,
        status: derivedStatus,
        elapsed_ms: Math.max(1, Math.round(performance.now() - started)),
        summary: summarizeSystemCheckValue(label, value),
        value,
      });
      return value;
    } catch (error) {
      checks.push({
        label,
        status: "실패",
        elapsed_ms: Math.max(1, Math.round(performance.now() - started)),
        summary: error?.message || String(error),
      });
      return null;
    }
  };

  const provider = await runCheck("백엔드/데이터 프로바이더", () => fetchDataProviderStatus());
  if (provider?.providers) {
    const ready = provider.providers.filter((item) => item.ready).length;
    elements.backendStatus.textContent = provider.status === "success" ? "정상" : "확인 필요";
    elements.providerStatus.textContent = `${translateProviderMode(provider.mode)} (${ready})`;
    markBackendHealthy();
  }

  await Promise.all([
    runCheck("저장 데이터/RAG Manifest", () => fetchResearchManifest(token())),
    runCheck("OCR/Tesseract 연결", () => fetchOcrStatus()),
    runCheck("포트폴리오 저장소", async () => {
      const result = await fetchPortfolios(token());
      savedPortfolios = [...(result?.portfolios || [])].sort((a, b) =>
        String(a.portfolio_name || "").localeCompare(String(b.portfolio_name || ""), "ko-KR")
      );
      renderPortfolioOptions(savedPortfolios);
      if (savedPortfolios.length && !activePortfolioSnapshot) {
        fillPortfolioForm(savedPortfolios[0]);
      }
      return result;
    }),
    runCheck("관심종목/섹터 저장소", async () => {
      const result = await fetchInterests(token());
      fillInterestsForm(result);
      return result;
    }),
    runCheck("DART 신규 공시 감시", () => fetchDartFilingWatchStatus(token())),
    runCheck("네이버 리서치/시장일지 자동 반영", () => fetchNaverResearchStatus(token())),
    runCheck("리서치 자동화 상태", () => fetchResearchAutomationStatus(token())),
    runCheck("일일 브리핑", () => fetchDailyBriefing(token(), false)),
  ]);

  renderDashboardTickerPicker();
  const candidate = (dashboardTickerCandidates() || []).find((item) => item.ticker)?.ticker || "";
  if (candidate) {
    if (isClickSmokeMode()) {
      checks.push({
        label: "대표 대시보드",
        status: "성공",
        elapsed_ms: 1,
        summary: `${candidate} · 스모크 검증에서는 장시간 재조회 없이 연결 대상만 확인`,
        value: {
          status: "smoke_skipped",
          ticker: candidate,
          file_count: lastDashboard?.file_count || 0,
          data_warnings: lastDashboard?.data_warnings || [],
        },
      });
    } else {
      await runCheck("대표 대시보드", async () => {
        const dashboard = await fetchTickerDashboard(token(), candidate);
        lastDashboard = dashboard;
        activeTicker = dashboard?.ticker || candidate;
        lastConfirmedTicker = activeTicker;
        renderDashboardCards(dashboard);
        return dashboard;
      });
    }
  } else {
    renderDashboardEmptyState();
  }

  setOutput(formatConsoleSystemCheckResult({
    generated_at: new Date().toISOString(),
    dashboard_candidate: candidate,
    checks,
  }));
}

async function handleWorkflowAction(action) {
  syncApiBaseUrl();
  const workflowBaseTicker = resolveDashboardWorkflowTicker();
  if (workflowBaseTicker) {
    syncTickerInputs(workflowBaseTicker);
  }

  if (action === "system-check") {
    await runConsoleSystemCheck();
    return;
  }

  if (action === "dart-refresh") {
    startOutputLoading("DART 공시 재점검 중", [
      "보유/관심종목 감시 대상 정리",
      "ETF/ETN 등 제외 대상 분류",
      "OpenDART 신규 공시 조회",
      "저장 데이터와 상태 카드 갱신",
    ]);
    const result = await refreshDartFilingWatch(token(), { force: true, saveResult: true });
    setOutput(result || "DART 공시 재점검 결과를 불러오지 못했습니다.");
    await runSecondaryRefresh("시스템 상태 새로고침", () => refreshStatus(false));
    if (lastDashboard?.ticker) {
      await runSecondaryRefresh("대시보드 카드 새로고침", () =>
        refreshDashboardCardsOnly(lastDashboard.ticker)
      );
    }
    return;
  }

  if (action === "dashboard-refresh") {
    if (!workflowBaseTicker) {
      throw new Error("대시보드를 새로고침할 종목을 먼저 선택하거나 입력하세요.");
    }
    startOutputLoading(`${workflowBaseTicker} 대시보드 새로고침 중`, [
      "공식 티커 인증",
      "최신 저장 데이터 연결",
      "대시보드 카드 재구성",
    ]);
    await loadTickerDashboard(workflowBaseTicker);
    return;
  }

  if (action === "run-team") {
    if (!workflowBaseTicker) {
      throw new Error("리포트를 실행할 종목을 먼저 선택하거나 입력하세요.");
    }
    activateTab("team", { keepOutput: true });
    startOutputLoading(`${workflowBaseTicker} 리포트 실행 중`, [
      "종목 공식 인증",
      "시장/재무 데이터 자동 주입",
      "7개 스킬 종합 리포트 생성",
      "저장 데이터와 대시보드 갱신",
    ]);
    const data = formDataObject(elements.teamForm);
    const verification = await certifyTickerForWorkflow(workflowBaseTicker);
    const workflowTicker = verification.official_symbol;
    const result = await runCollaborativeTeamReport(token(), {
      ticker: workflowTicker,
      investmentPeriod: data.investmentPeriod,
      region: data.region,
      style: data.style,
      focusArea: data.focusArea,
      autoInjectData: data.autoInjectData === "on",
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("대시보드 새로고침", () =>
      loadTickerDashboard(workflowTicker)
    );
    activateTab("dashboard", { keepOutput: true });
    return;
  }

  if (action === "chart") {
    const chartTicker =
      workflowBaseTicker ||
      elements.chartForm?.elements?.ticker?.value ||
      elements.dashboardForm?.elements?.ticker?.value ||
      "";
    await runChartAnalysisForTicker(chartTicker, { saveResult: true });
    return;
  }

  if (action === "refresh-data") {
    if (!workflowBaseTicker) {
      throw new Error("최신 데이터를 조회할 종목을 먼저 선택하거나 입력하세요.");
    }
    startOutputLoading(`${workflowBaseTicker} 최신 데이터 조회 중`, [
      "공식 티커 인증",
      "KIS/Finnhub/Tiingo 현재가 확인",
      "데이터 스냅샷 정리",
    ]);
    const verification = await certifyTickerForWorkflow(workflowBaseTicker);
    const { snapshot, lastPrice } = await fetchAndApplyLatestPrice(
      verification.official_symbol
    );
    setOutput(snapshot || "최신 데이터 스냅샷을 불러오지 못했습니다.");
    if (lastPrice) {
      elements.providerStatus.textContent = `KIS 현재가 ${lastPrice}`;
    }
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    return;
  }

  if (action === "diagnose-ticker") {
    const ticker = normalizeTickerInput(workflowBaseTicker);
    if (!ticker) {
      throw new Error("진단할 티커 또는 회사명을 먼저 선택하거나 입력하세요.");
    }
    startOutputLoading(`${ticker} 티커 인증 경로 진단 중`, [
      "로컬 공식 레지스트리 확인",
      "자동 인증 캐시 확인",
      "외부 프로필/KIS 경로 점검",
    ]);
    const diagnostics = await fetchTickerDiagnostics(token(), ticker);
    setOutput(diagnostics || "티커 진단 결과를 불러오지 못했습니다.");
    if (diagnostics?.verification?.verified) {
      setTickerVerificationStatus(diagnostics.verification);
      syncTickerInputs(diagnostics.verification.official_symbol);
    }
    return;
  }

  if (action === "optimize-portfolio") {
    activateTab("portfolio", { keepOutput: true });
    if (savedPortfolios.length && !activePortfolioSnapshot) {
      await refreshPortfolioStore(true);
    }
    elements.portfolioOptimizeButton?.click();
    return;
  }

  if (action === "interest-automation") {
    activateTab("interests", { keepOutput: true });
    elements.interestAutomationButton?.click();
    return;
  }

  if (action === "news") {
    activateTab("news", { keepOutput: true });
    elements.newsInboxButton?.click();
    return;
  }

  if (action === "storage-quality") {
    startOutputLoading("저장 데이터 품질 점검 중", [
      "중복 의심 자료 묶기",
      "대표 자료 후보 정리",
      "뉴스 인박스 품질 상태 확인",
    ]);
    const duplicateReview = await runStorageDuplicateReview(token(), {
      limit: 120,
      saveResult: true,
    });
    const qualityDashboard = await fetchStorageQualityDashboard(token());
    const newsInbox = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
    renderNewsInboxCards(newsInbox);
    setOutput([
      "### 저장 데이터 품질 점검 완료",
      "",
      `- 정상 문서: ${formatNumber(qualityDashboard?.normal_count || 0)}개`,
      `- 본문 보강 필요: ${formatNumber(qualityDashboard?.body_missing_count || 0)}개`,
      `- OCR 필요: ${formatNumber(qualityDashboard?.ocr_needed_count || 0)}개`,
      `- 보관 문서: ${formatNumber(qualityDashboard?.archived_count || 0)}개`,
      `- 중복 의심 묶음: ${formatNumber(duplicateReview?.duplicate_group_count || 0)}개`,
      `- 중복 의심 자료: ${formatNumber(duplicateReview?.duplicate_entry_count || 0)}개`,
      `- 뉴스 인박스: ${formatNumber(newsInbox?.count || 0)}개`,
      `- 미승격 뉴스: ${formatNumber(newsInbox?.unpromoted_count || 0)}개`,
      `- 품질 확인 뉴스: ${formatNumber(newsInbox?.quality_issue_count || 0)}개`,
      "",
      `저장 정책: ${qualityDashboard?.policy?.message || "뉴스 원문 본문은 저장하지 않습니다."}`,
      "",
      "다음 액션",
      ...formatBulletList(qualityDashboard?.next_actions, (item) => compactOutputText(item, 180)),
    ].join("\n"));
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    return;
  }

  if (action === "today-research-update") {
    await runTodayResearchUpdate();
    return;
  }

  const actionToTab = {
    team: "team",
    trade: "trade",
    earnings: "earnings",
    sector: "sector",
    compounder: "compounder",
    chart: "chart",
    capture: "capture",
    portfolio: "portfolio",
    checklist: "checklist",
    memory: "memory",
    reportAutomation: "reportAutomation",
    marketData: "marketClose",
  };
  const targetTab = actionToTab[action];
  if (targetTab) {
    activateTab(targetTab);
    if (workflowBaseTicker) {
      syncTickerInputs(workflowBaseTicker);
    }
    if (targetTab === "trade") {
      try {
        const verification = await certifyTickerForWorkflow(activeTicker);
        const { lastPrice } = await fetchAndApplyLatestPrice(
          verification.official_symbol
        );
        if (lastPrice) {
          setOutput(
            `${verification.official_symbol} KIS 현재가 ${lastPrice}를 매매 전략 현재가에 입력했습니다.`
          );
        }
      } catch (error) {
        console.warn("매매 전략 현재가 자동 조회 실패:", error);
      }
    }
  }
}

async function runTeamReportForTicker(ticker, sourceLabel = "") {
  const normalizedTicker = normalizeTickerDraft(ticker || activeTicker);
  if (!normalizedTicker) {
    throw new Error("팀 리포트를 실행할 종목을 확인하지 못했습니다.");
  }
  activateTab("team", { keepOutput: true });
  syncTickerInputs(normalizedTicker);
  const data = formDataObject(elements.teamForm);
  const verification = await certifyTickerForWorkflow(normalizedTicker);
  const workflowTicker = verification.official_symbol || normalizedTicker;
  startOutputLoading(`${workflowTicker} 팀 리포트 실행 중`, [
    sourceLabel || "저장 데이터 맥락 확인",
    "시장/재무 데이터 자동 주입",
    "7개 스킬 종합 의견 생성",
    "저장 데이터와 대시보드 갱신",
  ]);
  const result = await runCollaborativeTeamReport(token(), {
    ticker: workflowTicker,
    investmentPeriod: data.investmentPeriod,
    region: data.region,
    style: data.style,
    focusArea: sourceLabel
      ? `${data.focusArea || ""}\n\n추가 맥락: ${sourceLabel}`.trim()
      : data.focusArea,
    autoInjectData: data.autoInjectData === "on",
    saveResult: true,
  });
  setOutput(result);
  await runSecondaryRefresh("대시보드 새로고침", () =>
    loadTickerDashboard(workflowTicker, { quiet: true })
  );
  return result;
}

async function runChartAnalysisForTicker(ticker, { saveResult = true } = {}) {
  const requestedTicker = String(ticker || activeTicker || "").trim();
  if (!requestedTicker) {
    throw new Error("차트 분석할 국내 종목명 또는 종목코드를 입력하세요.");
  }
  activateTab("chart", { keepOutput: true });
  const verification = await certifyTickerForWorkflow(requestedTicker);
  if (verification.country && verification.country !== "KR") {
    throw new Error(
      `${verification.official_symbol}은 국내 종목이 아닙니다. 네이버 차트 분석은 한국 주식/ETF만 지원합니다.`
    );
  }
  const workflowTicker = verification.official_symbol;
  const displayName = verification.company_name || displayTickerForInput(workflowTicker);
  if (elements.chartForm?.elements?.ticker) {
    elements.chartForm.elements.ticker.value = displayName || workflowTicker;
  }
  startOutputLoading(`${displayName || workflowTicker} 차트 분석 중`, [
    "네이버 증권 일별 시세 수집",
    "거래량, 볼린저 밴드, 이동평균선 계산",
    "MACD, RSI 14, DMI 종합 판정",
    "결과 그래프와 저장 데이터 연결",
  ]);
  const result = await runNaverChartAnalysis(token(), {
    ticker: workflowTicker,
    saveResult,
  });
  renderChartVisualization(result);
  setOutput(result || "네이버 차트 분석 결과를 불러오지 못했습니다.");
  syncTickerInputs(workflowTicker, { skipDashboardInvalidation: true });
  await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  return result;
}

async function openTickerWorkflow(action, ticker) {
  syncApiBaseUrl();
  const workflowTicker = normalizeTickerDraft(ticker || activeTicker);
  if (workflowTicker) {
    syncTickerInputs(workflowTicker);
  }

  if (action === "dashboard") {
    activateTab("dashboard", { keepOutput: true });
    await loadTickerDashboard(workflowTicker || activeTicker);
    return;
  }

  if (action === "memory") {
    activateTab("memory", { keepOutput: true });
    const lookupKey = await resolveMemoryLookupKey(workflowTicker || activeTicker);
    if (elements.memoryForm?.elements?.ticker) {
      elements.memoryForm.elements.ticker.value = lookupKey;
    }
    startOutputLoading("저장 데이터 조회 중", [
      "저장 키 정규화",
      "파일 목록 조회",
      "미리보기 목록 구성",
    ]);
    const memoryResponse = await fetchResearchMemoryFiles(token(), lookupKey, memoryListFetchOptions());
    renderMemoryList(memoryResponse, lookupKey);
    setOutput(memoryResponse);
    return;
  }

  if (action === "dossier") {
    activateTab("memory", { keepOutput: true });
    const lookupKey = await resolveMemoryLookupKey(workflowTicker || activeTicker);
    startOutputLoading(`${lookupKey} Dossier 재합성 중`, [
      "저장 데이터 중복 제거",
      "강세/약세 논거 분리",
      "핵심 쟁점과 확인 지표 정리",
      "대시보드 연결 스냅샷 갱신",
    ]);
    const result = await synthesizeDossier(token(), lookupKey, true);
    setOutput(result || "Dossier 합성 결과를 확인하지 못했습니다.");
    const memoryResponse = await fetchResearchMemoryFiles(token(), lookupKey, memoryListFetchOptions());
    renderMemoryList(memoryResponse, lookupKey);
    await runSecondaryRefresh("대시보드 새로고침", () =>
      loadTickerDashboard(lookupKey, { quiet: true })
    );
    return;
  }

  if (action === "run-team") {
    await runTeamReportForTicker(workflowTicker || activeTicker, "대시보드에서 선택한 종목");
    return;
  }

  if (action === "chart") {
    await runChartAnalysisForTicker(workflowTicker || activeTicker, { saveResult: true });
    return;
  }

  if (action === "nps") {
    const tickerForNps = workflowTicker || activeTicker;
    if (!tickerForNps) {
      throw new Error("국민연금 수급을 확인할 종목을 먼저 선택하세요.");
    }
    startOutputLoading(`${tickerForNps} 국민연금 수급 확인 중`, [
      "공공데이터포털 보유 비중 조회",
      "대량보유 보고 이벤트 매칭",
      "리스크/투자 논거 연결",
    ]);
    const result = await fetchTickerNpsFlow(token(), tickerForNps);
    setOutput(result || "국민연금 수급 결과를 불러오지 못했습니다.");
    await runSecondaryRefresh("대시보드 새로고침", () =>
      loadTickerDashboard(tickerForNps, { quiet: true })
    );
    return;
  }

  await handleWorkflowAction(action);
}

async function openMemoryFile(ticker, fileName) {
  if (!ticker || !fileName) {
    throw new Error("열 저장 데이터의 키 또는 파일명이 비어 있습니다. 저장 데이터 목록을 다시 조회한 뒤 열어주세요.");
  }
  startOutputLoading("저장 리포트 본문을 불러오는 중", [
    "저장 키 확인",
    "파일 본문 읽기",
    "미리보기 렌더링",
  ]);
  const file = await fetchResearchMemoryFile(token(), ticker, fileName);
  if (!file?.content) {
    throw new Error(`${fileName} 본문이 비어 있거나 불러오지 못했습니다.`);
  }
  renderMemoryPreview(file);
  setOutput(
    [
      "저장 리포트 본문",
      "",
      `파일: ${file.file_name}`,
      `저장 키: ${file.ticker || ticker}`,
      `경로: ${file.relative_path || "경로 미확인"}`,
      `상태: ${file.status_label || (file.legacy ? "레거시/검증 전" : "공식 인증")}`,
      "",
      "---",
      "",
      cleanStoredReportContent(file.content),
    ].join("\n")
  );
}

async function handleMemoryArchiveAction(button) {
  const fileName = button?.dataset?.memoryArchive || "";
  const ticker = button?.dataset?.memoryArchiveKey || activeTicker || "";
  const mode = button?.dataset?.memoryArchiveState || "archive";
  if (!ticker || !fileName) {
    throw new Error("보관 상태를 바꿀 저장 데이터 키 또는 파일명이 비어 있습니다.");
  }
  const archived = mode !== "restore";
  const actionLabel = archived ? "보관" : "복원";
  startOutputLoading(`저장 데이터 ${actionLabel} 처리 중`, [
    "파일 경로 확인",
    "manifest 보관 플래그 갱신",
    "JSON sidecar 상태 갱신",
    "목록 다시 불러오기",
  ]);
  const result = await archiveResearchMemoryFile(token(), ticker, fileName, {
    archived,
    reason: archived
      ? "저장 데이터 화면에서 소프트 보관 처리"
      : "저장 데이터 화면에서 보관 해제",
  });
  setOutput({
    status: "success",
    module: "research_memory_archive",
    action: archived ? "archive" : "restore",
    ticker,
    file_name: fileName,
    message: archived
      ? "파일을 삭제하지 않고 보관 처리했습니다. 보관 문서 포함 옵션으로 다시 볼 수 있습니다."
      : "보관 문서를 복원했습니다. 기본 저장 데이터 목록에 다시 표시됩니다.",
    archived: result.archived,
    archived_at: result.archived_at,
  });
  const memoryResponse = await fetchResearchMemoryFiles(token(), ticker, memoryListFetchOptions());
  renderMemoryList(memoryResponse, ticker);
  if (activeMemoryPreviewFile?.file_name === fileName) {
    activeMemoryPreviewFile = null;
    elements.memoryPreview.hidden = true;
    if (elements.memorySupplementForm) {
      elements.memorySupplementForm.hidden = true;
    }
  }
  await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
}

async function handleLegacyArchiveAction(button) {
  const ticker = button?.dataset?.memoryArchiveLegacy || activeTicker || "";
  if (!ticker) {
    throw new Error("레거시 보관을 실행할 저장 데이터 키가 비어 있습니다.");
  }
  startOutputLoading("레거시 파일 일괄 보관 중", [
    "레거시 후보 확인",
    "하드 삭제 없이 보관 플래그 기록",
    "manifest와 RAG 색인 갱신",
    "저장 데이터 목록 다시 불러오기",
  ]);
  const result = await archiveLegacyResearchMemoryFiles(token(), ticker, {
    reason: "레거시 파일 처리 정책에 따라 사용자가 일괄 소프트 보관 실행",
  });
  const memoryResponse = await fetchResearchMemoryFiles(token(), ticker, memoryListFetchOptions());
  renderMemoryList(memoryResponse, ticker);
  setOutput(result);
  await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
}

function portfolioDashboardCard() {
  const portfolio = activePortfolioSnapshot || savedPortfolios[0];
  if (!portfolio) {
    return `
      <article class="dashboard-card warning">
        <span>내 포트폴리오</span>
        <strong>미등록</strong>
        <p>포트폴리오 탭에서 현재 보유 종목을 저장하면 대시보드와 리스크 스캔에 연결됩니다.</p>
      </article>
    `;
  }
  const holdings = sortHoldingsByMarketValue(portfolio.holdings || []);
  const totalValue =
    Number(portfolio.portfolio_value) ||
    holdings.reduce((sum, item) => sum + Number(item.market_value || 0), 0);
  const topHolding = holdings[0];
  const topHoldingText = topHolding
    ? `${topHolding.ticker || topHolding.name || "상위 종목"} ${formatMoney(topHolding.market_value, "KRW", "")} · ${toPercent(topHolding.weight)}`
    : "저장된 보유 종목 상세가 없습니다.";
  return `
    <article class="dashboard-card ok">
      <span>내 포트폴리오</span>
      <strong>${escapeHtml(portfolio.portfolio_name || "이름 없음")}</strong>
      <p>총액 ${escapeHtml(formatMoney(totalValue, "KRW", "0원"))} · 보유 ${holdings.length || portfolio.holding_count || 0}개<br />상위: ${escapeHtml(topHoldingText)}</p>
    </article>
  `;
}

function portfolioAnalysisDashboardCard() {
  const status = lastPortfolioAnalysisStatus;
  if (!status) {
    return `
      <article class="dashboard-card warning">
        <span>포트폴리오 분석 연결</span>
        <strong>확인 전</strong>
        <p>포트폴리오 상태를 불러오면 전체 종목 분석 연결률을 표시합니다.</p>
      </article>
    `;
  }
  const items = status.items || [];
  const holdingCount = status.holding_count || items.length || 0;
  const readyCount = status.ready_count || 0;
  const completion = Number(status.average_completion);
  const missingCounts = portfolioModuleMissingCounts(status);
  const totalMissing = Object.values(missingCounts).reduce((sum, value) => sum + value, 0);
  const tone = readyCount === holdingCount && holdingCount > 0 ? "ok" : totalMissing ? "warning" : "neutral";
  const missingText = totalMissing === 0
    ? "누락 없음"
    : `누락 ${totalMissing}개: 팀 ${missingCounts.team}, 매매 ${missingCounts.trade}, 실적 ${missingCounts.earnings}, 체크 ${missingCounts.checklist}, 정보 ${missingCounts.capture}`;
  return `
    <article class="dashboard-card ${tone}">
      <span>포트폴리오 분석 연결</span>
      <strong>${readyCount}/${holdingCount}</strong>
      <p>평균 완성도 ${escapeHtml(Number.isFinite(completion) ? toPercent(completion) : "n/a")}<br />${escapeHtml(missingText)}</p>
    </article>
  `;
}
function renderLatestReportLine(item) {
  const label = translateReportType(item.type);
  const summary = translateSummary(item.summary || item.file_name);
  const tooltip = item.tooltip || item.impact_reason || "";
  const impactLabel = item.impact_label ? ` · ${translateImpact(item.impact_label)}` : "";
  const tooltipAttrs = tooltip
    ? ` title="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}"`
    : "";
  const className = tooltip ? "latest-report-line has-tooltip" : "latest-report-line";
  return `<span class="${className}"${tooltipAttrs}>${escapeHtml(label)}${escapeHtml(impactLabel)}: ${escapeHtml(summary)}</span>`;
}

function renderDashboardThesisSnapshotCard(snapshot) {
  if (!snapshot?.thesis_summary) {
    return `
      <article class="dashboard-card warning">
        <span>최신 투자 논거</span>
        <strong>합성 필요</strong>
        <p>저장 데이터 검색 합성을 실행하면 강세·약세 논거와 확인할 KPI가 대시보드에 연결됩니다.</p>
      </article>
    `;
  }
  const sourceLabel = translateReportType(snapshot.source_report_type || "research-memory");
  const confidence = Number(snapshot.confidence);
  const confidenceText = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "n/a";
  const bull = (snapshot.bull_triggers || []).slice(0, 2).join(" · ") || "강세 논거 보강 필요";
  const bear = (snapshot.bear_triggers || []).slice(0, 2).join(" · ") || "약세 논거 보강 필요";
  const kpis = (snapshot.watch_kpis || []).slice(0, 3).join(" · ") || "확인 KPI 미정";
  const cruxes = (snapshot.invalidation_conditions || [])
    .slice(0, 2)
    .join(" · ") || "판단을 좌우할 쟁점 보강 필요";
  const observables = (snapshot.watch_items || [])
    .slice(0, 2)
    .map((item) => {
      if (typeof item === "string") return item;
      return item.condition || item.metric || item.action || "";
    })
    .filter(Boolean)
    .join(" · ") || kpis;
  const source = [sourceLabel, snapshot.source_date, confidenceText].filter(Boolean).join(" · ");
  const ticker = snapshot.ticker || activeTicker;
  const sourceButton = snapshot.source_file_name
    ? `<div class="dashboard-card-actions">
        <button
          data-dashboard-memory-key="${escapeHtml(ticker)}"
          data-dashboard-memory-file="${escapeHtml(snapshot.source_file_name)}"
          type="button"
        >합성 보고서 열기</button>
        <button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">Dossier 갱신</button>
        <button data-dashboard-ticker-action="run-team" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">팀 리포트</button>
        <button data-dashboard-ticker-action="memory" data-dashboard-ticker="${escapeHtml(ticker)}" class="secondary" type="button">저장 데이터</button>
      </div>`
    : `<div class="dashboard-card-actions">
        <button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">Dossier 갱신</button>
        <button data-dashboard-ticker-action="run-team" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">팀 리포트</button>
      </div>`;
  return `
    <article class="dashboard-card ok thesis-snapshot-card">
      <span>최신 투자 논거</span>
      <strong>${escapeHtml(compactOutputText(snapshot.thesis_summary, 78))}</strong>
      <p>
        출처 ${escapeHtml(source)}<br />
        강세: ${escapeHtml(compactOutputText(bull, 110))}<br />
        약세: ${escapeHtml(compactOutputText(bear, 110))}<br />
        핵심 쟁점: ${escapeHtml(compactOutputText(cruxes, 120))}<br />
        관찰 지표: ${escapeHtml(compactOutputText(observables, 120))}<br />
        확인: ${escapeHtml(compactOutputText(kpis, 110))}
      </p>
      ${sourceButton}
    </article>
  `;
}

function portfolioOperatingItems() {
  const status = lastPortfolioAnalysisStatus || {};
  const queue = lastPortfolioTeamReportQueue || {};
  const items = Array.isArray(status.items) ? status.items : [];
  const missingCounts = portfolioModuleMissingCounts(status);
  const teamQueue = Array.isArray(queue.queue) ? queue.queue : [];
  const blocked = Array.isArray(queue.blocked) ? queue.blocked : [];
  const holdingCount = status.holding_count || items.length || 0;
  const readyCount = status.ready_count || 0;
  const completion = Number(status.average_completion);
  const topNeeds = (teamQueue.length ? teamQueue : items.filter((item) => item.missing_modules?.length))
    .slice(0, 4)
    .map((item) => ({
      ticker: item.official_symbol || item.ticker || item.key || "",
      label: item.company_name || item.name || "확인 필요",
      missing: item.missing_modules?.length
        ? item.missing_modules.join(", ")
        : item.analysis_focus || "팀 리포트 보강",
    }))
    .filter((item) => item.ticker || item.label);
  const latestDate =
    items
      .map((item) => item.latest_report_date)
      .filter(Boolean)
      .sort()
      .at(-1) || "미확인";

  return {
    holdingCount,
    readyCount,
    completion,
    completionText: Number.isFinite(completion) ? toPercent(completion) : "n/a",
    teamQueueCount: teamQueue.length || missingCounts.team || 0,
    blockedCount: blocked.length,
    topNeeds,
    latestDate,
  };
}

function renderNpsInstitutionalCard(signal) {
  if (!signal || (!signal.domestic_match_found && !(signal.large_holding_events || []).length)) {
    const ticker = signal?.ticker || activeTicker || "";
    return `
      <article class="dashboard-card">
        <span>국민연금 수급</span>
        <strong>자료 없음</strong>
        <p>공공데이터포털 API에서 이 종목의 국민연금 보유/대량보유 자료가 아직 매칭되지 않았습니다.</p>
        <div class="dashboard-card-actions">
          <button data-dashboard-ticker-action="nps" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">수급 재조회</button>
        </div>
      </article>
    `;
  }
  const ticker = signal.ticker || activeTicker || "";
  const events = Array.isArray(signal.large_holding_events) ? signal.large_holding_events : [];
  const ratio = Number(signal.holding_ratio ?? events[0]?.holding_ratio);
  const weight = Number(signal.domestic_weight);
  const amount = Number(signal.amount_100m_krw);
  const eventTextBlob = JSON.stringify(events).toLowerCase();
  const outflowLike = ["감소", "매도", "처분", "축소", "하락", "decrease", "sell", "sold", "reduced"].some((term) =>
    eventTextBlob.includes(term)
  );
  const ratioText = Number.isFinite(ratio) ? `${ratio.toFixed(2)}%` : "미확인";
  const weightText = Number.isFinite(weight) ? `${weight.toFixed(2)}%` : "미확인";
  const amountText = Number.isFinite(amount) ? `${amount.toLocaleString("ko-KR")}억 원` : "미확인";
  const barWidth = Number.isFinite(ratio) ? Math.max(2, Math.min(100, ratio)) : 0;
  const eventText = events.length
    ? `대량보유 보고 ${events.length}건 · 최근 ${events[0]?.base_date || "기준일 미확인"}`
    : "대량보유 변동 이벤트 없음";
  const decisionText = outflowLike
    ? "감소/처분성 표현 감지 · 추가매수 전 수급 이탈 확인"
    : "기관 수급 보조 근거 · 리포트/리스크 스캔에 반영";
  return `
    <article class="dashboard-card ${outflowLike ? "warning" : "ok"} nps-card">
      <span>국민연금 수급</span>
      <strong>지분율 ${escapeHtml(ratioText)}</strong>
      <p>
        ${escapeHtml(decisionText)}<br />
        자산군 비중 ${escapeHtml(weightText)} · 평가액 ${escapeHtml(amountText)}<br />
        ${escapeHtml(eventText)}
      </p>
      <div class="nps-holding-bar" aria-label="국민연금 보유 지분율">
        <i style="width: ${barWidth}%"></i>
      </div>
      <div class="dashboard-card-actions">
        <button data-dashboard-ticker-action="nps" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">수급 상세</button>
      </div>
    </article>
  `;
}

function renderCustomsTradeDashboardCard(reference) {
  const hasReference = reference && (reference.summary || reference.relative_path);
  if (!hasReference) {
    return `
      <article class="dashboard-card warning customs-card">
        <span>관세청 수출입</span>
        <strong>최근 자료 없음</strong>
        <p>1일·11일·21일 발표 자료를 시장 데이터 탭에서 수동 조회하거나 자동화 실행 시 저장할 수 있습니다.</p>
        <div class="dashboard-card-actions">
          <button data-workflow-action="marketData" type="button">시장 데이터</button>
        </div>
      </article>
    `;
  }
  const implications = Array.isArray(reference.sector_implications)
    ? reference.sector_implications.filter(Boolean).slice(0, 2)
    : [];
  const summary = reference.summary || "관세청 수출입 동향 자료가 저장되어 있습니다.";
  return `
    <article class="dashboard-card ok customs-card">
      <span>관세청 수출입</span>
      <strong>${escapeHtml(reference.date || "최근 자료")}</strong>
      <p>
        ${escapeHtml(compactOutputText(summary, 150))}<br />
        발표 주기 ${escapeHtml(reference.release_schedule || "1일, 11일, 21일")}
      </p>
      ${implications.length ? `<ul>${implications.map((item) => `<li>${escapeHtml(compactOutputText(item, 90))}</li>`).join("")}</ul>` : ""}
      <div class="dashboard-card-actions">
        <button data-workflow-action="marketData" type="button">수출입 보기</button>
        <button data-workflow-action="memory" class="secondary" type="button">저장 데이터</button>
      </div>
    </article>
  `;
}

function renderDartFilingSignalCard(signal) {
  if (!signal || !Object.keys(signal).length) {
    return `
      <article class="dashboard-card warning dart-filing-card">
        <span>DART 공시</span>
        <strong>상태 없음</strong>
        <p>신규 공시 감시 상태를 아직 불러오지 못했습니다.</p>
      </article>
    `;
  }
  const tone = signal.tone === "warning" ? "warning" : signal.tone === "ok" ? "ok" : "";
  const recentEntries = Array.isArray(signal.recent_entries) ? signal.recent_entries.slice(0, 3) : [];
  const statusLabel = signal.recent_count
    ? signal.important_count
      ? "주의"
      : "확인"
    : signal.latest_failure
      ? "오류"
      : "정상";
  const counters = [
    ["신규", signal.recent_count || 0],
    ["중요", signal.important_count || 0],
    ["지분/수급", signal.ownership_count || 0],
    ["정기보고", signal.periodic_count || 0],
  ];
  const details = recentEntries.length
    ? recentEntries
        .map((entry) => {
          const filing = entry.filing || {};
          return `<li class="${entry.importance === "높음" ? "warning" : "ok"}"><b>${escapeHtml(
            filing.receipt_date || "날짜 미확인"
          )}</b><span>${escapeHtml(filing.report_name || entry.action || "공시명 미확인")}${
            entry.importance ? ` · ${escapeHtml(entry.importance)}` : ""
          }</span></li>`;
        })
        .join("")
    : signal.latest_failure
      ? `<li class="warning"><b>실패</b><span>${escapeHtml(
          compactOutputText(signal.latest_failure.error || "DART 조회 실패", 90)
        )}</span></li>`
      : `<li><b>신규 없음</b><span>최근 ${escapeHtml(formatNumber(signal.lookback_days || 14))}일 기준 신규 감지 없음</span></li>`;
  return `
    <article class="dashboard-card ${escapeHtml(tone)} dart-filing-card">
      <span>DART 공시</span>
      <strong>${escapeHtml(statusLabel)} · ${escapeHtml(signal.headline || "자동 감시")}</strong>
      <p>${escapeHtml(compactOutputText(signal.summary || "공시 자동 감시 상태를 확인하세요.", 120))}</p>
      <div class="dashboard-mini-metrics">
        ${counters
          .map(([label, value]) => `<b>${escapeHtml(label)} <i>${escapeHtml(formatNumber(value))}</i></b>`)
          .join("")}
      </div>
      <ul class="dashboard-signal-list compact">${details}</ul>
      <div class="dashboard-card-actions">
        <button data-workflow-action="dart-refresh" type="button">공시 재점검</button>
        <button data-workflow-action="system-check" type="button">상태 점검</button>
        <button data-workflow-action="memory" class="secondary" type="button">저장 데이터</button>
      </div>
    </article>
  `;
}

function renderRecentDartFilingStrip(signal) {
  const recentEntries = Array.isArray(signal?.recent_entries) ? signal.recent_entries.slice(0, 4) : [];
  const daily = signal?.daily_check || {};
  const headline = signal?.headline || "보유/관심종목 공시 자동 점검";
  const status = signal?.recent_count
    ? `최근 ${formatNumber(signal.recent_count)}건`
    : signal?.latest_failure
      ? "확인 필요"
      : "신규 공시 없음";
  const targetCount = Number(daily.current_target_count || signal?.target_count || 0);
  const checkedCount = Number(daily.checked_count || 0);
  const dailyText = daily.due
    ? "오늘 점검 필요"
    : daily.failure_count
      ? `부분 완료 · 실패 ${formatNumber(daily.failure_count)}개`
      : "오늘 점검 완료";
  const list = recentEntries.length
    ? recentEntries.map((entry) => {
        const filing = entry.filing || {};
        return `<li class="${entry.importance === "높음" ? "warning" : "ok"}"><b>${escapeHtml(
          filing.corp_name || entry.company_name || "회사명 미확인"
        )}</b><span>${escapeHtml(filing.report_name || "공시명 미확인")} · ${escapeHtml(
          filing.receipt_date || "날짜 미확인"
        )}</span></li>`;
      }).join("")
    : `<li><b>${escapeHtml(status)}</b><span>${escapeHtml(compactOutputText(signal?.summary || "매일 자동 점검 결과를 대시보드에서 바로 확인합니다.", 120))}</span></li>`;
  return `
    <section class="dashboard-dart-strip" aria-label="최근 공시 확인">
      <div>
        <span>DART 최근 공시</span>
        <strong>${escapeHtml(status)} · ${escapeHtml(compactOutputText(headline, 80))}</strong>
        <small>${escapeHtml(dailyText)} · 대상 ${escapeHtml(formatNumber(targetCount))}개 · 확인 ${escapeHtml(formatNumber(checkedCount))}개 · 마지막 ${escapeHtml(daily.checked_at ? formatDateTime(daily.checked_at) : "미확인")}</small>
      </div>
      <ul>${list}</ul>
      <button data-workflow-action="dart-refresh" type="button">공시 재점검</button>
    </section>
  `;
}

function dashboardMetricCard(label, value, hint, tone = "") {
  return `
    <div class="dashboard-metric ${escapeHtml(tone)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <p>${escapeHtml(hint)}</p>
    </div>
  `;
}

function todayTargetPriorityScore(target = {}) {
  let score = 0;
  if (target.source === "portfolio_holding") score += 35;
  if (target.priority === "high") score += 20;
  if (target.thesis_snapshot_connected) score += 8;
  if ((target.market_journal_matches || []).length) score += 12;
  if ((target.rag_document_count || 0) === 0) score += 14;
  if ((target.duplicate_suspected_count || 0) > 0) score += 4;
  if ((target.recent_document_count || 0) > 5) score += 6;
  return score;
}

function todayReviewPriorityScore(item = {}) {
  let score = 0;
  const status = String(item.status || "").toLowerCase();
  const action = String(item.recommended_action || item.summary || "");
  const confidence = Number(item.confidence);
  if (status.includes("위험") || status.includes("risk") || status.includes("warning")) score += 30;
  if (status.includes("확인") || status.includes("보강") || status.includes("needs")) score += 20;
  if (action.includes("실적") || action.includes("리스크") || action.includes("손절") || action.includes("무효화")) score += 16;
  if (Number.isFinite(confidence) && confidence < 0.65) score += 12;
  if (Number.isFinite(confidence) && confidence >= 0.8) score += 5;
  if (item.official_symbol || item.ticker || item.key) score += 4;
  return score;
}

function todayActionPriorityScore(text = "") {
  const value = String(text || "");
  let score = 0;
  if (/실패|오류|지연|확인 필요|보류|위험/.test(value)) score += 30;
  if (/실적|리스크|손절|무효화|가이던스/.test(value)) score += 18;
  if (/RAG|Dossier|팀 리포트|시장일지/.test(value)) score += 10;
  return score;
}

function compactTodayResearchUpdate(result = {}) {
  const board = result.interest_board || {};
  const daily = result.daily_brief || {};
  const automation = result.automation || {};
  const targets = (board.ticker_targets || [])
    .map((target) => ({
      key: target.ticker || target.name || "",
      label: target.company_name || target.name || "대상 미확인",
      query: (target.rag_query_examples || [])[0] || `${target.company_name || target.name || "관심 대상"} 최근 투자 논거`,
      rag_count: target.rag_document_count || 0,
      market_count: (target.market_journal_matches || []).length || 0,
      next_action: target.next_action || "",
      priority_score: todayTargetPriorityScore(target),
      priority_reason: [
        target.source === "portfolio_holding" ? "보유종목" : "관심종목",
        target.priority === "high" ? "우선순위 높음" : "",
        (target.market_journal_matches || []).length ? "시장일지 연결" : "",
        (target.rag_document_count || 0) === 0 ? "RAG 보강 필요" : "",
      ].filter(Boolean).join(" · "),
    }))
    .sort((a, b) => b.priority_score - a.priority_score)
    .slice(0, 12);
  const priorityReviews = (daily.portfolio_overview?.priority_reviews || [])
    .map((item) => ({
      key: item.official_symbol || item.ticker || item.key || "",
      label: item.company_name || item.name || "검토 대상",
      status: item.status || "",
      action: item.recommended_action || item.summary || "",
      confidence: item.confidence,
      priority_score: todayReviewPriorityScore(item),
      priority_reason: [
        item.status ? `상태 ${item.status}` : "",
        item.confidence !== undefined && item.confidence !== null ? `신뢰도 ${toPercent(item.confidence)}` : "",
        item.recommended_action ? "추천 액션 있음" : "",
      ].filter(Boolean).join(" · "),
    }))
    .sort((a, b) => b.priority_score - a.priority_score)
    .slice(0, 8);
  const nextActions = (daily.next_actions || board.next_actions || [])
    .map((item) => ({
      text: String(item || ""),
      priority_score: todayActionPriorityScore(item),
    }))
    .sort((a, b) => b.priority_score - a.priority_score)
    .slice(0, 8);
  return {
    module: "today_research_update_summary",
    saved_at: new Date().toISOString(),
    status: result.status || "unknown",
    steps: (result.steps || []).map((step) => ({
      key: step.key,
      label: step.label,
      status: step.status,
      summary: step.summary,
      elapsed_ms: step.elapsed_ms,
    })),
    target_count: board.target_count || 0,
    rag_updated_count: result.rag_backfill?.updated_count ?? 0,
    dossier_count: automation.dossier_count || 0,
    failed_count: (automation.failed || []).length,
    next_actions: nextActions.map((item) => item.text),
    targets,
    priority_reviews: priorityReviews,
  };
}

function readStoredTodayResearchUpdate() {
  try {
    const raw = window.localStorage?.getItem(TODAY_RESEARCH_UPDATE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    console.warn("오늘 리서치 업데이트 저장값을 읽지 못했습니다:", error);
    return null;
  }
}

function saveStoredTodayResearchUpdate(result) {
  const compact = compactTodayResearchUpdate(result);
  try {
    window.localStorage?.setItem(
      TODAY_RESEARCH_UPDATE_STORAGE_KEY,
      JSON.stringify(compact)
    );
  } catch (error) {
    console.warn("오늘 리서치 업데이트 저장 실패:", error);
  }
  lastTodayResearchUpdate = compact;
  return compact;
}

function interestAutomationDashboardCard() {
  const board = lastInterestAutomationBoard;
  if (!board) {
    return `
      <article class="dashboard-card warning">
        <span>관심종목/섹터 자동 수집</span>
        <strong>보드 생성 전</strong>
        <p>관심종목·보유종목·관심섹터를 수집 대상으로 묶어 RAG 검색어와 시장일지 연결점을 만들 수 있습니다.</p>
        <div class="dashboard-card-actions">
          <button data-workflow-action="interest-automation" type="button">자동 수집 보드</button>
          <button data-workflow-action="today-research-update" class="secondary" type="button">오늘 업데이트</button>
        </div>
      </article>
    `;
  }
  const marketLinks = [
    ...(board.ticker_targets || []),
    ...(board.sector_targets || []),
  ].reduce((sum, item) => sum + ((item.market_journal_matches || []).length || 0), 0);
  return `
    <article class="dashboard-card ok">
      <span>관심종목/섹터 자동 수집</span>
      <strong>${escapeHtml(board.target_count || 0)}개 대상</strong>
      <p>RAG 연결 ${escapeHtml(board.rag_connected_count || 0)}개 · 시장일지 연결 ${escapeHtml(marketLinks)}개 · 중복 의심 ${escapeHtml(board.duplicate_suspected_count || 0)}개</p>
      <div class="dashboard-card-actions">
        <button data-workflow-action="interest-automation" type="button">보드 보기</button>
        <button data-workflow-action="today-research-update" class="secondary" type="button">오늘 업데이트</button>
      </div>
    </article>
  `;
}

function todayResearchTasksDashboardCard() {
  const update = lastTodayResearchUpdate;
  if (!update) {
    return `
      <article class="dashboard-card warning">
        <span>오늘 할 일</span>
        <strong>업데이트 전</strong>
        <p>오늘 리서치 업데이트를 실행하면 단계별 결과와 우선 점검 항목이 여기에 고정됩니다.</p>
        <div class="dashboard-card-actions">
          <button data-workflow-action="today-research-update" type="button">오늘 업데이트 실행</button>
        </div>
      </article>
    `;
  }
  const failedSteps = (update.steps || []).filter((step) => step.status === "failed");
  const primaryReviews = (update.priority_reviews || []).slice(0, 3);
  const targets = (update.targets || []).slice(0, 3);
  const actionLines = [
    ...failedSteps.map((step) => `지연/실패: ${step.label || step.key}`),
    ...primaryReviews.map((item) => `${item.label}: ${compactOutputText(item.action, 60)}${item.priority_reason ? ` (${item.priority_reason})` : ""}`),
    ...targets.map((item) => `${item.label}: ${compactOutputText(item.next_action || item.query, 60)}${item.priority_reason ? ` (${item.priority_reason})` : ""}`),
    ...(update.next_actions || []).slice(0, 2),
  ]
    .filter(Boolean)
    .map((text) => ({ text, score: todayActionPriorityScore(text) }))
    .sort((a, b) => b.score - a.score)
    .map((item) => item.text)
    .slice(0, 5);
  const firstTarget = targets[0];
  const firstReview = primaryReviews[0];
  const savedAt = update.saved_at ? formatDateTime(update.saved_at) : "저장 시각 없음";
  return `
    <article class="dashboard-card ${failedSteps.length ? "warning" : "ok"}">
      <span>오늘 할 일</span>
      <strong>${escapeHtml(actionLines.length || 0)}개</strong>
      <p>${actionLines.length ? actionLines.map((item) => `- ${escapeHtml(item)}`).join("<br />") : "오늘 추가로 표시할 액션이 없습니다."}<br />최근 업데이트: ${escapeHtml(savedAt)}</p>
      <div class="dashboard-card-actions">
        <button data-workflow-action="today-research-update" type="button">다시 업데이트</button>
        <button data-today-action="open-update-board" class="secondary" type="button">결과 카드</button>
        ${
          firstTarget
            ? `<button data-today-action="synthesize" data-query="${escapeHtml(firstTarget.query)}" data-key="${escapeHtml(firstTarget.key)}" type="button">1순위 합성</button>`
            : ""
        }
        ${
          firstReview?.key
            ? `<button data-dashboard-ticker-action="dashboard" data-dashboard-ticker="${escapeHtml(firstReview.key)}" type="button">우선 종목</button>`
            : ""
        }
      </div>
    </article>
  `;
}

function dashboardOperatingOverview() {
  const operating = portfolioOperatingItems();
  const completionTone =
    operating.holdingCount > 0 && operating.readyCount === operating.holdingCount
      ? "ok"
      : operating.teamQueueCount || operating.blockedCount
        ? "warning"
        : "";
  const topNeeds = operating.topNeeds.length
    ? operating.topNeeds
        .map(
          (item) => `
            <button class="dashboard-link-button" data-dashboard-ticker-action="dashboard" data-dashboard-ticker="${escapeHtml(item.ticker)}" type="button">
              <strong>${escapeHtml(item.label || "회사명 확인 필요")}</strong>
              <span>${escapeHtml(item.missing)}</span>
            </button>
          `
        )
        .join("")
    : `<p class="dashboard-empty-text">지금은 보강 대기 종목이 없습니다.</p>`;

  return `
    <section class="dashboard-operations" aria-label="포트폴리오 운영 요약">
      <div class="dashboard-operations-header">
        <div>
          <span>운영 요약</span>
          <strong>포트폴리오 전체 연결 상태</strong>
        </div>
        <div class="dashboard-card-actions">
          <button data-workflow-action="portfolio" type="button">포트폴리오 열기</button>
          <button data-workflow-action="memory" class="secondary" type="button">저장 데이터</button>
        </div>
      </div>
      <div class="dashboard-metric-grid">
        ${dashboardMetricCard("보유 종목", `${operating.holdingCount}개`, `분석 연결 ${operating.readyCount}개`, completionTone)}
        ${dashboardMetricCard("팀 리포트 필요", `${operating.teamQueueCount}개`, "기준 투자 논거 보강 대상", operating.teamQueueCount ? "warning" : "ok")}
        ${dashboardMetricCard("평균 완성도", operating.completionText, "팀·매매·실적·체크·정보 입력 기준", completionTone)}
        ${dashboardMetricCard("인증/데이터 보류", `${operating.blockedCount}개`, "공식 티커 또는 데이터 확인 필요", operating.blockedCount ? "warning" : "ok")}
      </div>
      <div class="dashboard-operating-lists">
        <div>
          <span>우선 보강 후보</span>
          <div class="dashboard-link-list">${topNeeds}</div>
        </div>
        <div>
          <span>최근 갱신</span>
          <p>저장 리포트 기준 최신일: <strong>${escapeHtml(operating.latestDate)}</strong></p>
          <p>대시보드에서 종목을 바꾸면 연결 카드도 같은 티커 기준으로 다시 계산합니다.</p>
        </div>
      </div>
    </section>
  `;
}

function renderAutomationSignalCard(dashboard) {
  const automation = dashboard.latest_automation_summary || null;
  const earningsReference = dashboard.latest_earnings_reference || {};
  const hasAutomation = Boolean(automation);
  const statusClass = hasAutomation ? "ok automation-signal" : "warning automation-signal";
  const title = hasAutomation ? "모델 업데이트 완료" : "모델 업데이트 필요";
  const detail = hasAutomation
    ? compactOutputText(
        translateSummary(automation.summary || automation.file_name || "어닝 콜/공시 자료가 모델 업데이트 노트로 연결됐습니다."),
        170
      )
    : compactOutputText(
        dashboard.latest_earnings_summary ||
          `최신 실적 기준 ${earningsReference.official_quarter || "확인 필요"}에 맞춰 어닝 콜/공시 자료를 업로드하고 노트 초안을 작성하세요.`,
        170
      );
  const dateLine = hasAutomation
    ? `저장일 ${automation.date || "미확인"} · ${translateReportType(automation.type || "earnings-filing-note")}`
    : `발표일 ${earningsReference.official_earnings_report_date || "미입력"} · 다음 예정 ${earningsReference.next_earnings_date || "미입력"}`;
  const statusPill = hasAutomation ? "업데이트 반영" : "업로드 필요";
  const sourceLabel = hasAutomation
    ? translateReportType(automation.type || "earnings-filing-note")
    : "어닝콜/공시 노트";
  return `
    <article class="dashboard-card ${statusClass}">
      <span>보고 자동화</span>
      <strong>${escapeHtml(title)}</strong>
      <div class="automation-status-row">
        <b>${escapeHtml(statusPill)}</b>
        <small>${escapeHtml(sourceLabel)}</small>
      </div>
      <p>${escapeHtml(dateLine)}<br />${escapeHtml(detail)}</p>
      <div class="dashboard-card-actions">
        <button data-workflow-action="reportAutomation" type="button">${hasAutomation ? "노트 갱신" : "노트 작성"}</button>
        <button data-workflow-action="earnings" class="secondary" type="button">실적 분석</button>
      </div>
    </article>
  `;
}

function renderDashboardDecisionCard(dashboard) {
  const warnings = Array.isArray(dashboard.data_warnings) ? dashboard.data_warnings : [];
  const actions = Array.isArray(dashboard.recommended_next_actions) ? dashboard.recommended_next_actions : [];
  const statuses = Array.isArray(dashboard.module_status) ? dashboard.module_status : [];
  const needsAction = statuses.filter((item) => ["warning", "needs_action"].includes(item.tone)).length;
  const earningsReference = dashboard.latest_earnings_reference || {};
  const hasAutomation = Boolean(dashboard.latest_automation_summary);
  const hasThesis = Boolean(dashboard.latest_thesis_snapshot);
  let tone = "ok";
  let headline = "분석 준비 양호";
  if (warnings.length || needsAction >= 3 || !hasThesis) {
    tone = "warning";
    headline = "보강 후 판단 권장";
  }
  if (needsAction >= 5 || (!earningsReference.aligned_with_latest && !hasAutomation)) {
    tone = "needs_action";
    headline = "우선 점검 필요";
  }
  const mainReason = actions[0] || warnings[0] || "현재 저장 데이터 기준으로 후속 분석을 실행할 수 있습니다.";
  const automationText = hasAutomation ? "보고 자동화 반영" : "보고 자동화 대기";
  const thesisText = hasThesis ? "투자 논거 있음" : "투자 논거 필요";
  return `
    <article class="dashboard-card decision-card ${tone}">
      <span>종합 판단</span>
      <strong>${escapeHtml(headline)}</strong>
      <p>${escapeHtml(thesisText)} · ${escapeHtml(automationText)} · 보강 신호 ${needsAction + warnings.length}개<br />${escapeHtml(compactOutputText(mainReason, 170))}</p>
      <div class="dashboard-card-actions">
        <button data-workflow-action="team" type="button">리포트 실행</button>
        <button data-workflow-action="memory" class="secondary" type="button">근거 확인</button>
      </div>
    </article>
  `;
}

function renderAutomationDigestCard(dashboard) {
  const digest = dashboard?.automation_digest || {};
  const tone = digest.tone || (digest.target_count ? "ok" : "warning");
  const headline = digest.headline || (digest.target_count ? "자동화 연결됨" : "자동화 준비 필요");
  const targetCount = Number(digest.target_count || 0);
  const ragCount = Number(digest.rag_document_count || 0);
  const ragConnectedCount = Number(digest.rag_connected_count || 0);
  const duplicateCount = Number(digest.duplicate_suspected_count || 0);
  const dossierCount = Number(digest.dossier_count || 0);
  const newsCount = Number(digest.news_inbox_count || 0);
  const newsUnpromotedCount = Number(digest.news_unpromoted_count || 0);
  const newsQualityIssueCount = Number(digest.news_quality_issue_count || 0);
  const kcifRelatedCount = Number(digest.kcif_related_count || 0);
  const regionalRelatedCount = Number(digest.regional_sources_related_count || 0);
  const connectedRatio = targetCount ? Math.min(100, Math.round((ragConnectedCount / targetCount) * 100)) : 0;
  const digestMetrics = [
    ["수집 대상", `${formatNumber(targetCount)}개`, "관심/보유/섹터"],
    ["RAG 연결", `${formatNumber(ragConnectedCount)}개`, `전체 문서 ${formatNumber(ragCount)}개`],
    ["Dossier", `${formatNumber(dossierCount)}개`, "합성 리포트"],
    [
      "뉴스",
      `${formatNumber(newsCount)}개`,
      newsUnpromotedCount || newsQualityIssueCount
        ? `미승격 ${formatNumber(newsUnpromotedCount)} · 품질 ${formatNumber(newsQualityIssueCount)}`
        : "인박스 정상",
    ],
    [
      "매크로 자료",
      `${formatNumber(kcifRelatedCount + regionalRelatedCount)}개`,
      digest.kcif_due || digest.regional_sources_due ? "일일 점검 필요" : "자동 점검 반영",
    ],
    ["중복 의심", `${formatNumber(duplicateCount)}개`, duplicateCount ? "검토 필요" : "정상"],
  ];
  const targetRows = renderAutomationDigestTargetRows(digest.priority_targets || []);
  const nextActions = Array.isArray(digest.next_actions) ? digest.next_actions.filter(Boolean).slice(0, 3) : [];
  const action = nextActions[0] || "오늘 업데이트를 실행해 자동 수집, 중복 제거, RAG 색인, Dossier 합성을 연결하세요.";
  const runLabel = digest.daily_brief_date ? "업데이트 갱신" : "오늘 업데이트";
  return `
    <article class="dashboard-card automation-digest-card ${escapeHtml(tone)}">
      <div class="automation-digest-head">
        <div>
          <span>자동 리서치 파이프라인</span>
          <strong>${escapeHtml(headline)}</strong>
        </div>
        <b>${escapeHtml(digest.daily_brief_date || "오늘 브리핑 필요")}</b>
      </div>
      <div class="automation-digest-progress" aria-label="RAG 연결률">
        <div style="width: ${connectedRatio}%"></div>
      </div>
      <div class="automation-digest-metrics">
        ${digestMetrics
          .map(
            ([label, value, hint]) => `
              <div>
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(value)}</strong>
                <small>${escapeHtml(hint)}</small>
              </div>
            `
          )
          .join("")}
      </div>
      <p>
        최근 일일 브리핑: ${escapeHtml(digest.daily_brief_date || "미생성")} · 연결률 ${escapeHtml(connectedRatio)}%<br />
        ${targetRows ? "우선 대상별로 바로 실행할 수 있습니다." : escapeHtml(compactOutputText(action, 170))}
      </p>
      <div class="automation-action-strip">
        ${nextActions.length
          ? nextActions
              .map((item, index) => `<span>${escapeHtml(index + 1)}. ${escapeHtml(compactOutputText(item, 86))}</span>`)
              .join("")
          : `<span>${escapeHtml(compactOutputText(action, 120))}</span>`}
      </div>
      ${targetRows}
      <div class="dashboard-card-actions">
        <button data-workflow-action="today-research-update" type="button">${escapeHtml(runLabel)}</button>
        <button data-workflow-action="interest-automation" class="secondary" type="button">수집 보드</button>
      </div>
    </article>
  `;
}

function renderAutomationDigestTargetRows(priorityTargets) {
  const rows = (Array.isArray(priorityTargets) ? priorityTargets : [])
    .slice(0, 4)
    .map((item) => {
      const label = item.label || item.key || "대상 미확인";
      const key = item.key || item.ticker || item.name || label;
      const source = item.source || "interest";
      const priority = translatePriority(item.priority || "medium");
      const recentCount = Number(item.recent_document_count || 0);
      const ragCount = Number(item.rag_document_count || 0);
      const duplicateCount = Number(item.duplicate_suspected_count || 0);
      const isTickerTarget = isTickerLikeMemoryKey(key) || Boolean(item.ticker);
      const rowTone = duplicateCount ? "warning" : ragCount ? "ok" : "needs-action";
      const statusBadge = duplicateCount ? "중복 검토" : ragCount ? "근거 연결" : "근거 보강";
      const actionHint =
        item.next_action ||
        (ragCount ? "저장 근거 확인 후 리포트 갱신" : "오늘 업데이트로 RAG 근거 보강");
      const primaryAction = isTickerTarget
        ? `<button data-dashboard-ticker-action="dashboard" data-dashboard-ticker="${escapeHtml(key)}" type="button">대시보드</button>
           <button data-dashboard-ticker-action="run-team" data-dashboard-ticker="${escapeHtml(key)}" type="button">리포트</button>`
        : `<button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(key)}" type="button">Dossier</button>`;
      return `
        <div class="automation-target-row ${escapeHtml(rowTone)}">
          <div>
            <strong>${escapeHtml(label)} <b>${escapeHtml(statusBadge)}</b></strong>
            <span>${escapeHtml(source)} · 우선순위 ${escapeHtml(priority)} · 저장 ${escapeHtml(formatNumber(recentCount))}개 · RAG ${escapeHtml(formatNumber(ragCount))}개${duplicateCount ? ` · 중복 ${escapeHtml(formatNumber(duplicateCount))}개` : ""}</span>
            <small>${escapeHtml(compactOutputText(actionHint, 120))}</small>
          </div>
          <div>
            ${primaryAction}
            <button data-dashboard-ticker-action="memory" data-dashboard-ticker="${escapeHtml(key)}" class="secondary" type="button">저장 데이터</button>
          </div>
        </div>
      `;
    })
    .join("");
  return rows ? `<div class="automation-target-list">${rows}</div>` : "";
}

function renderTodayPriorityBriefCard(brief) {
  const items = Array.isArray(brief?.items) ? brief.items.slice(0, 5) : [];
  if (!items.length) {
    return `
      <article class="dashboard-card warning today-priority-card">
        <span>오늘 확인할 것</span>
        <strong>대기 중</strong>
        <p>대시보드 조회 후 데이터 경고, 시장일지, Dossier, 파일 추출 품질을 한 카드로 묶어 보여줍니다.</p>
      </article>
    `;
  }
  const tone = items.some((item) => item.tone === "warning" || item.tone === "needs_action") ? "warning" : "ok";
  return `
    <article class="dashboard-card ${tone} today-priority-card">
      <span>${escapeHtml(brief.headline || "오늘 확인할 것")}</span>
      <strong>${escapeHtml(items.length)}개 우선순위</strong>
      <ul class="dashboard-signal-list">
        ${items.map((item) => `
          <li class="${escapeHtml(item.tone || "neutral")}">
            <b>${escapeHtml(item.label || "확인")}</b>
            <span>${escapeHtml(compactOutputText(item.value || item.action || "", 96))}</span>
          </li>
        `).join("")}
      </ul>
      <p>자동화 상태: ${escapeHtml(brief.automation_headline || "확인 중")}</p>
    </article>
  `;
}

function renderDossierPreviewCard(dossier) {
  if (!dossier?.summary) {
    return `
      <article class="dashboard-card warning dossier-preview-card">
        <span>Dossier 합성</span>
        <strong>생성 필요</strong>
        <p>저장 자료를 중복 제거한 뒤 공통 사실, 강세·약세 논거, 핵심 쟁점과 관찰 지표를 하나로 합성하세요.</p>
        <div class="dashboard-card-actions">
          <button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(activeTicker)}" type="button">Dossier 생성</button>
        </div>
      </article>
    `;
  }
  const confidence = Number(dossier.confidence);
  const confidenceText = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : "n/a";
  const consensus = (dossier.consensus_facts || []).slice(0, 2);
  const bull = (dossier.bull_thesis || []).slice(0, 2);
  const bear = (dossier.bear_thesis || []).slice(0, 2);
  const cruxes = (dossier.cruxes || []).slice(0, 2);
  const observables = (dossier.observables || []).slice(0, 3);
  const scenarioBlock = (label, items, className) => `
    <div class="${className}">
      <b>${escapeHtml(label)}</b>
      ${(items.length ? items : ["보강 필요"]).map((item) => `<span>${escapeHtml(compactOutputText(item, 72))}</span>`).join("")}
    </div>
  `;
  return `
    <article class="dashboard-card ok dossier-preview-card">
      <span>Dossier 합성</span>
      <strong>${escapeHtml(compactOutputText(dossier.summary, 94))}</strong>
      <p>고유 자료 ${escapeHtml(formatNumber(dossier.source_count || 0))}개 · 중복 ${escapeHtml(formatNumber(dossier.duplicate_count || 0))}개 · 신뢰도 ${escapeHtml(confidenceText)}</p>
      <div class="dossier-scenario-grid">
        ${scenarioBlock("공통 사실", consensus, "neutral")}
        ${scenarioBlock("강세 논거", bull, "bull")}
        ${scenarioBlock("약세 논거", bear, "bear")}
        ${scenarioBlock("핵심 쟁점", cruxes, "crux")}
        ${scenarioBlock("관찰 지표", observables, "observable")}
      </div>
      <div class="dashboard-card-actions">
        <button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(dossier.ticker || activeTicker)}" type="button">Dossier 갱신</button>
        <button data-dashboard-ticker-action="memory" data-dashboard-ticker="${escapeHtml(dossier.ticker || activeTicker)}" class="secondary" type="button">근거 열기</button>
      </div>
    </article>
  `;
}

function renderDocumentQualityCard(digest) {
  if (!digest?.document_count) {
    return `
      <article class="dashboard-card warning document-quality-card">
        <span>파일 추출 품질</span>
        <strong>자료 없음</strong>
        <p>PDF, 엑셀, 문서, 웹 주소를 정보 입력에 넣으면 본문 추출 품질과 분석 활용도를 표시합니다.</p>
        <div class="dashboard-card-actions">
          <button data-workflow-action="capture" type="button">정보 입력</button>
        </div>
      </article>
    `;
  }
  const latest = digest.latest || {};
  const quality = Number(latest.quality);
  const qualityText = Number.isFinite(quality) ? `${Math.round(quality * 100)}%` : "미평가";
  const usableCount = Number(digest.usable_count || 0);
  const totalCount = Number(digest.document_count || 0);
  const width = Number.isFinite(quality) ? Math.max(4, Math.min(100, Math.round(quality * 100))) : 12;
  const tone = usableCount ? "ok" : "warning";
  const warnings = Array.isArray(latest.warnings) ? latest.warnings.slice(0, 2) : [];
  return `
    <article class="dashboard-card ${tone} document-quality-card">
      <span>파일 추출 품질</span>
      <strong>${escapeHtml(digest.headline || "추출 상태")}</strong>
      <p>${escapeHtml(latest.file_name || latest.title || "최근 문서")}<br />활용 가능 ${escapeHtml(usableCount)}/${escapeHtml(totalCount)}개 · 본문 ${escapeHtml(formatNumber(latest.char_count || 0))}자 · 품질 ${escapeHtml(qualityText)}</p>
      <div class="dashboard-quality-meter"><i style="width: ${width}%"></i></div>
      ${warnings.length ? `<ul class="dashboard-signal-list compact">${warnings.map((item) => `<li class="warning"><b>주의</b><span>${escapeHtml(compactOutputText(item, 80))}</span></li>`).join("")}</ul>` : ""}
      <div class="dashboard-card-actions">
        <button data-workflow-action="capture" type="button">자료 추가</button>
        <button data-workflow-action="memory" class="secondary" type="button">저장 데이터</button>
      </div>
    </article>
  `;
}

function renderMarketJournalReferenceCard(reference) {
  if (!reference?.session_date) {
    return `
      <article class="dashboard-card warning market-journal-reference-card">
        <span>시장일지 자동 활용</span>
        <strong>최근 일지 없음</strong>
        <p>폐장 후 시장 요약이나 웹 주소, 파일을 시장일지에 저장하면 종목·섹터 판단에 자동 연결됩니다.</p>
        <div class="dashboard-card-actions">
          <button data-workflow-action="marketData" type="button">시장일지</button>
        </div>
      </article>
    `;
  }
  const focus = (reference.auto_utilization_focus || reference.portfolio_actions || []).slice(0, 3);
  const drivers = (reference.key_drivers || []).slice(0, 3);
  const tone = reference.risk_level === "높음" ? "warning" : "ok";
  return `
    <article class="dashboard-card ${tone} market-journal-reference-card">
      <span>시장일지 자동 활용</span>
      <strong>${escapeHtml(reference.market || "시장")} · ${escapeHtml(reference.session_date)}</strong>
      <p>심리 ${escapeHtml(reference.sentiment || "미확인")} · 리스크 ${escapeHtml(reference.risk_level || "미확인")} · 장세 ${escapeHtml(reference.regime || "미확인")}</p>
      <ul class="dashboard-signal-list compact">
        ${[...focus, ...drivers].slice(0, 4).map((item) => `<li><b>활용</b><span>${escapeHtml(compactOutputText(item, 92))}</span></li>`).join("")}
      </ul>
      <div class="dashboard-card-actions">
        <button data-workflow-action="marketData" type="button">시장일지 열기</button>
      </div>
    </article>
  `;
}

function renderAutomationStepsCard(digest) {
  const steps = Array.isArray(digest?.automation_steps) ? digest.automation_steps.slice(0, 6) : [];
  if (!steps.length) return "";
  return `
    <article class="dashboard-card ok automation-steps-card">
      <span>자동 수집 보드</span>
      <strong>Pulls → Delivers</strong>
      <ul class="dashboard-signal-list compact">
        ${steps.map((step) => {
          const text = typeof step === "string" ? step : `${step.label || step.key || "단계"}: ${step.summary || step.status || ""}`;
          const [head, ...rest] = text.split(":");
          return `<li><b>${escapeHtml(head.trim())}</b><span>${escapeHtml(compactOutputText(rest.join(":").trim() || text, 86))}</span></li>`;
        }).join("")}
      </ul>
      <div class="dashboard-card-actions">
        <button data-workflow-action="interest-automation" type="button">수집 보드 보기</button>
        <button data-workflow-action="today-research-update" class="secondary" type="button">오늘 업데이트</button>
      </div>
    </article>
  `;
}

function dashboardStatusItem(dashboard, label) {
  return (dashboard?.module_status || []).find((item) => item.label === label) || null;
}

function renderDashboardCleanStatusCard(dashboard, label, fallbackAction = "") {
  const item = dashboardStatusItem(dashboard, label);
  const rawValue = item?.value || "확인 필요";
  const tone = item?.tone || (["있음", "완료"].includes(rawValue) ? "ok" : "warning");
  return `
    <div class="dashboard-clean-status ${escapeHtml(tone)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(translateDashboardStatus(rawValue))}</strong>
      <p>${dashboardCardHint(label, rawValue) || escapeHtml(fallbackAction)}</p>
    </div>
  `;
}

function renderDashboardCleanLatestReports(reports, ticker) {
  const rows = (reports || []).slice(0, 4);
  if (!rows.length) {
    return `
      <div class="dashboard-empty-note">
        <strong>최근 저장 데이터 없음</strong>
        <p>리포트 실행이나 정보 입력으로 첫 투자 근거를 만들면 여기에 표시됩니다.</p>
      </div>
    `;
  }
  return `
    <div class="dashboard-clean-report-list">
      ${rows
        .map(
          (item) => `
            <button
              class="dashboard-clean-report"
              data-dashboard-memory-key="${escapeHtml(ticker)}"
              data-dashboard-memory-file="${escapeHtml(item.file_name || "")}"
              type="button"
              ${item.file_name ? "" : "disabled"}
            >
              <span>${escapeHtml(translateReportType(item.type))}</span>
              <strong>${escapeHtml(compactOutputText(translateSummary(item.summary || item.file_name), 86))}</strong>
              <small>${escapeHtml(item.date || item.source_date || item.modified_at || "날짜 없음")}</small>
            </button>
          `
        )
        .join("")}
    </div>
  `;
}

function renderDashboardCleanSignals(dashboard) {
  const warnings = Array.isArray(dashboard?.data_warnings) ? dashboard.data_warnings.slice(0, 3) : [];
  const actions = Array.isArray(dashboard?.recommended_next_actions)
    ? dashboard.recommended_next_actions.slice(0, 4)
    : [];
  const thesis = dashboard?.latest_thesis_snapshot;
  const earnings = dashboard?.latest_earnings_reference || {};
  const signals = [];

  if (thesis?.thesis_summary) {
    signals.push(["투자 논거", compactOutputText(thesis.thesis_summary, 120), "ok"]);
  } else {
    signals.push(["투자 논거", "팀 리포트 또는 Dossier 합성으로 기준 논거를 먼저 만드세요.", "warning"]);
  }

  if (earnings.official_quarter || earnings.official_earnings_report_date) {
    signals.push([
      "실적 기준",
      `${earnings.official_quarter || "분기 미확인"} · 발표일 ${earnings.official_earnings_report_date || "미입력"}`,
      earnings.aligned_with_latest ? "ok" : "warning",
    ]);
  }

  actions.forEach((item) => signals.push(["다음 액션", compactOutputText(item, 116), "neutral"]));
  warnings.forEach((item) => signals.push(["데이터 경고", compactOutputText(item, 116), "warning"]));

  return signals
    .slice(0, 8)
    .map(
      ([label, text, tone]) => `
        <li class="${escapeHtml(tone)}">
          <b>${escapeHtml(label)}</b>
          <span>${escapeHtml(text)}</span>
        </li>
      `
    )
    .join("");
}

function renderDashboardCleanActionButtons(dashboard) {
  const ticker = dashboard?.ticker || activeTicker || "";
  return `
    <div class="dashboard-clean-actions" aria-label="대시보드 후속 작업">
      <button data-dashboard-ticker-action="run-team" data-dashboard-ticker="${escapeHtml(ticker)}" type="button">리포트 실행</button>
      <button data-dashboard-ticker-action="chart" data-dashboard-ticker="${escapeHtml(ticker)}" class="secondary" type="button">차트 분석</button>
      <button data-workflow-action="capture" class="secondary" type="button">정보 입력</button>
      <button data-dashboard-ticker-action="memory" data-dashboard-ticker="${escapeHtml(ticker)}" class="secondary" type="button">저장 데이터</button>
    </div>
  `;
}

function renderDashboardCards(dashboard) {
  if (!dashboard) {
    setDashboardCards(`
      <article class="dashboard-card warning">
        <span>대시보드</span>
        <strong>조회 실패</strong>
        <p>백엔드 상태와 토큰을 확인하세요.</p>
      </article>
    `);
    return;
  }

  const verification = dashboard.ticker_verification;
  const profile = dashboard.ticker_profile;
  const earningsReference = dashboard.latest_earnings_reference || {};
  const displayName = profile?.company_name || verification?.company_name || dashboard.ticker || "선택 종목";
  const exchange = verification?.exchange || profile?.exchange || "거래소 미확인";
  const industry = profile?.industry || profile?.sector || "산업 정보 보강 필요";
  const businessContext = compactOutputText(profile?.business_context || "회사별 사업 맥락이 아직 등록되지 않았습니다.", 150);
  const warningCount = Array.isArray(dashboard.data_warnings) ? dashboard.data_warnings.length : 0;
  const actionCount = Array.isArray(dashboard.recommended_next_actions) ? dashboard.recommended_next_actions.length : 0;
  const statusWarningCount = (dashboard.module_status || []).filter((item) =>
    ["warning", "needs_action"].includes(item.tone)
  ).length;
  const decisionTone = warningCount || statusWarningCount ? "warning" : "ok";
  const decisionText = warningCount
    ? `데이터 경고 ${warningCount}건을 먼저 확인하세요.`
    : actionCount
      ? `${actionCount}개의 후속 액션이 준비되어 있습니다.`
      : "현재 저장 데이터 기준으로 바로 후속 분석이 가능합니다.";
  const latestReportCount = dashboard.latest_reports?.length || 0;
  const automationDigest = dashboard.automation_digest || {};
  const automationText = automationDigest.headline || (automationDigest.target_count ? "자동화 연결됨" : "자동화 준비 필요");

  setDashboardCards(`
    <section class="dashboard-clean-layout" aria-label="대시보드 요약">
      <section class="dashboard-clean-hero ${escapeHtml(decisionTone)}">
        <div class="dashboard-clean-title">
          <span>현재 조회</span>
          <h2>${escapeHtml(displayName)}</h2>
          <p>${escapeHtml(dashboard.ticker || "티커 미확인")} · ${escapeHtml(exchange)} · ${escapeHtml(industry)}</p>
        </div>
        <div class="dashboard-clean-summary">
          <strong>${escapeHtml(decisionText)}</strong>
          <p>${escapeHtml(businessContext)}</p>
        </div>
        ${renderDashboardCleanActionButtons(dashboard)}
      </section>

      <section class="dashboard-clean-kpis" aria-label="핵심 상태">
        <div>
          <span>저장 데이터</span>
          <strong>${escapeHtml(formatNumber(dashboard.file_count || 0))}개</strong>
          <p>최근 리포트 ${escapeHtml(formatNumber(latestReportCount))}건</p>
        </div>
        <div>
          <span>공식 인증</span>
          <strong>${verification?.verified ? "완료" : "확인 필요"}</strong>
          <p>${escapeHtml(verification?.company_name || "회사명 미확인")}</p>
        </div>
        <div class="${earningsReference.aligned_with_latest ? "ok" : "warning"}">
          <span>실적 기준</span>
          <strong>${escapeHtml(earningsReference.official_quarter || "미확인")}</strong>
          <p>발표일 ${escapeHtml(earningsReference.official_earnings_report_date || "미입력")}</p>
        </div>
        <div class="${warningCount ? "warning" : "ok"}">
          <span>자동화</span>
          <strong>${escapeHtml(automationText)}</strong>
          <p>경고 ${escapeHtml(formatNumber(warningCount))}건 · 액션 ${escapeHtml(formatNumber(actionCount))}개</p>
        </div>
      </section>

      <section class="dashboard-clean-columns">
        <article class="dashboard-clean-panel">
          <div class="dashboard-clean-panel-head">
            <span>최근 저장 데이터</span>
            <button data-dashboard-ticker-action="memory" data-dashboard-ticker="${escapeHtml(dashboard.ticker)}" type="button">전체 보기</button>
          </div>
          ${renderDashboardCleanLatestReports(dashboard.latest_reports, dashboard.ticker)}
        </article>
        <article class="dashboard-clean-panel">
          <div class="dashboard-clean-panel-head">
            <span>판단 신호</span>
            <button data-dashboard-ticker-action="dossier" data-dashboard-ticker="${escapeHtml(dashboard.ticker)}" type="button">합성 갱신</button>
          </div>
          <ul class="dashboard-clean-signal-list">
            ${renderDashboardCleanSignals(dashboard)}
          </ul>
        </article>
      </section>

      ${renderRecentDartFilingStrip(dashboard.dart_filing_signal)}

      <details class="dashboard-clean-details">
        <summary>세부 운영 신호 펼치기</summary>
        <div class="dashboard-clean-detail-grid">
          ${renderNpsInstitutionalCard(dashboard.nps_institutional_signal)}
          ${renderDartFilingSignalCard(dashboard.dart_filing_signal)}
          ${renderCustomsTradeDashboardCard(dashboard.latest_customs_trade_reference)}
          ${renderStorageQualitySignalCard(dashboard)}
          ${renderMarketJournalReferenceCard(dashboard.latest_market_journal_reference)}
        </div>
      </details>
    </section>
  `);
}

function memoryFileNeedsBodySupplement(file) {
  const tags = [
    ...(Array.isArray(file?.tags) ? file.tags : []),
    ...(Array.isArray(file?.json_payload?.tags) ? file.json_payload.tags : []),
    ...(Array.isArray(file?.json_payload?.captured_item?.tags)
      ? file.json_payload.captured_item.tags
      : []),
  ]
    .map((tag) => String(tag || "").trim())
    .filter(Boolean);
  const sourceStatus = String(
    file?.source_url_processing?.status ||
      file?.json_payload?.source_url_processing?.status ||
      ""
  );
  const bodySupplemented = Boolean(
    tags.includes("body_supplemented") ||
      file?.json_payload?.body_supplemented_at ||
      file?.capture_quality?.body_supplemented ||
      file?.json_payload?.capture_quality?.body_supplemented ||
      (Array.isArray(file?.json_payload?.body_supplements) &&
        file.json_payload.body_supplements.length)
  );
  if (bodySupplemented) {
    return false;
  }
  return Boolean(
    file?.needs_body_copy ||
      file?.url_text_unavailable ||
      tags.includes("needs_body_copy") ||
      tags.includes("url_text_unavailable") ||
      ["fetch_failed", "invalid", "empty_text"].includes(sourceStatus)
  );
}

function memoryFileQualityTags(file) {
  const tags = [
    ...(Array.isArray(file?.tags) ? file.tags : []),
    ...(Array.isArray(file?.json_payload?.tags) ? file.json_payload.tags : []),
    ...(Array.isArray(file?.json_payload?.captured_item?.tags)
      ? file.json_payload.captured_item.tags
      : []),
  ]
    .map((tag) => String(tag || "").trim())
    .filter(Boolean);
  const sourceStatus = String(
    file?.source_url_processing?.status ||
      file?.json_payload?.source_url_processing?.status ||
      ""
  );
  const attachment = file?.attachment || file?.json_payload?.attachment || {};
  const captureQuality = file?.capture_quality || file?.json_payload?.capture_quality || {};
  return {
    tags,
    sourceStatus,
    bodyMissing: memoryFileNeedsBodySupplement(file),
    urlOnly:
      Boolean(file?.url_text_unavailable) ||
      tags.includes("url_text_unavailable") ||
      tags.includes("url_only") ||
      ["fetch_failed", "invalid", "empty_text"].includes(sourceStatus),
    ocrNeeded:
      Boolean(attachment?.ocr_required || attachment?.ocr_available === false) ||
      ["ocr_unavailable", "ocr_error", "ocr_not_connected"].includes(String(attachment?.ocr_status || "")) ||
      ["ocr_unavailable", "ocr_error", "ocr_not_connected"].includes(String(captureQuality?.ocr_status || "")),
    legacy: Boolean(file?.legacy),
  };
}

function memoryFileMatchesQualityFilter(file, filterValue) {
  const filter = String(filterValue || "all");
  if (filter === "all") {
    return true;
  }
  const quality = memoryFileQualityTags(file);
  if (filter === "body_missing") {
    return quality.bodyMissing;
  }
  if (filter === "url_only") {
    return quality.urlOnly;
  }
  if (filter === "ocr_needed") {
    return quality.ocrNeeded;
  }
  if (filter === "legacy") {
    return quality.legacy;
  }
  return true;
}

function renderMemoryList(memoryResponse, ticker) {
  const memoryKey = normalizeStorageKey(ticker);
  const allFiles = Array.isArray(memoryResponse) ? memoryResponse : memoryResponse.files || [];
  const bodyMissingOnly = Boolean(
    elements.memoryForm?.querySelector('input[name="showBodyMissingOnly"]')?.checked
  );
  const qualityFilter = elements.memoryForm?.elements?.qualityFilter?.value || "all";
  const bodyMissingCount = allFiles.filter(memoryFileNeedsBodySupplement).length;
  const qualityCounts = {
    body_missing: bodyMissingCount,
    url_only: allFiles.filter((file) => memoryFileQualityTags(file).urlOnly).length,
    ocr_needed: allFiles.filter((file) => memoryFileQualityTags(file).ocrNeeded).length,
    legacy: allFiles.filter((file) => file.legacy).length,
  };
  const files = allFiles.filter((file) => {
    if (bodyMissingOnly && !memoryFileNeedsBodySupplement(file)) {
      return false;
    }
    return memoryFileMatchesQualityFilter(file, qualityFilter);
  });
  const warnings = Array.isArray(memoryResponse) ? [] : memoryResponse.data_warnings || [];
  const archivedFiles = files.filter((file) => file.archived || file.is_deleted);
  const activeFiles = files.filter((file) => !file.archived && !file.is_deleted);
  const officialFiles = activeFiles.filter((file) => !file.legacy);
  const legacyFiles = activeFiles.filter((file) => file.legacy);
  const includeArchived = Boolean(memoryResponse?.include_archived);
  const archivedCount = Number(memoryResponse?.archived_file_count || archivedFiles.length || 0);
  const legacyPolicy = memoryResponse?.legacy_policy || {};
  if (elements.memoryForm?.elements?.ticker) {
    elements.memoryForm.elements.ticker.value = memoryKey;
  }
  if (isTickerLikeMemoryKey(memoryKey)) {
    syncTickerInputs(memoryKey, { skipDashboardInvalidation: true });
  }

  const summaryHtml = `
    <div class="dashboard-card ${allFiles.length ? "ok" : "warning"}">
      <span>저장 데이터 키</span>
      <strong>${escapeHtml(memoryKey)}</strong>
      <p>공식 인증 ${officialFiles.length}개 · 레거시 ${legacyFiles.length}개 · 보관 ${archivedCount}개 · 본문 보강 필요 ${qualityCounts.body_missing}개 · URL-only ${qualityCounts.url_only}개 · OCR 보강 ${qualityCounts.ocr_needed}개${bodyMissingOnly || qualityFilter !== "all" ? ` · 필터 적용 ${files.length}개` : ""} · ${isTickerLikeMemoryKey(memoryKey) ? "종목 저장소" : "시스템/포트폴리오 저장소"}</p>
    </div>
  `;
  const policyHtml = legacyPolicy.policy
    ? `<div class="dashboard-card ${legacyFiles.length ? "warning" : "ok"}">
        <span>레거시 처리 정책</span>
        <strong>${legacyPolicy.hard_delete_allowed === false ? "삭제 금지 · 소프트 보관" : "정책 확인"}</strong>
        <p>${escapeHtml(legacyPolicy.archive_behavior || "레거시 파일은 삭제하지 않고 보관 플래그로 기본 목록에서 숨깁니다.")}</p>
      </div>`
    : "";

  if (!activeFiles.length && !archivedFiles.length) {
    elements.memoryList.innerHTML = `${summaryHtml}${policyHtml}
      <div class="dashboard-card warning">
        <span>${(bodyMissingOnly || qualityFilter !== "all") && allFiles.length ? "필터 결과" : "저장 리포트"}</span>
        <strong>없음</strong>
        <p>${(bodyMissingOnly || qualityFilter !== "all") && allFiles.length
          ? `${escapeHtml(memoryKey)}에는 현재 선택한 품질 필터에 해당하는 자료가 없습니다.`
          : `${escapeHtml(memoryKey)}에 저장된 Markdown 리포트가 아직 없습니다.`}</p>
      </div>
    `;
    activeMemoryPreviewFile = null;
    elements.memoryPreview.hidden = true;
    if (elements.memorySupplementForm) {
      elements.memorySupplementForm.hidden = true;
    }
    return;
  }

  const warningHtml = warnings.length
    ? `<details class="memory-warning-details">
        <summary>저장 데이터 경고 ${warnings.length}개 확인</summary>
        <p>${warnings.map(escapeHtml).join("<br />")}</p>
      </details>`
    : "";

  const renderMemoryFileCard = (file) => {
    const statusLabel = file.status_label || (file.legacy ? "검증 전" : "공식 인증");
    const archived = Boolean(file.archived || file.is_deleted);
    const bodyMissing = memoryFileNeedsBodySupplement(file);
    const sourceStatus = String(
      file.source_url_processing?.status ||
        file.json_payload?.source_url_processing?.status ||
        ""
    );
    const quality = file.capture_quality || {};
    const attachment = file.attachment || {};
    const extractionBadge = attachmentExtractionBadge(attachment);
    const qualityStatus = file.data_quality_status || quality.status;
    const documentType = attachment.document_type || (attachment.file_name ? "첨부 파일" : "");
    const charCount = Number(attachment.extraction_char_count || attachment.extraction_profile?.char_count || 0);
    return `
        <article class="memory-card-shell ${archived ? "archived" : ""}">
        <button class="memory-file-button memory-card ${archived ? "archived" : file.legacy ? "legacy" : "verified"}" data-memory-key="${escapeHtml(memoryKey)}" data-memory-file="${escapeHtml(file.file_name)}" type="button">
          <span class="memory-card-topline">
            <strong>${escapeHtml(file.file_name)}</strong>
            <span class="memory-card-action">열기</span>
          </span>
          <span class="memory-card-meta">
            ${memoryBadge(statusLabel, archived ? "neutral" : file.legacy ? "warning" : "success")}
            ${memoryBadge(translateReportType(file.report_type), "info")}
            ${bodyMissing ? memoryBadge("본문 보강 필요", "danger") : ""}
            ${sourceStatus && sourceStatus !== "success" ? memoryBadge(`URL ${sourceStatus}`, "warning") : ""}
            ${archived ? memoryBadge("소프트 보관", "neutral") : ""}
            ${documentType ? memoryBadge(documentType, "neutral") : ""}
            ${extractionBadge ? memoryBadge(extractionBadge.label, extractionBadge.tone) : ""}
            ${charCount ? memoryBadge(`본문 ${formatNumber(charCount)}자`, "info") : ""}
            ${qualityStatus ? memoryBadge(`품질 ${qualityStatus}`, qualityStatus === "정상" ? "success" : "warning") : ""}
            ${memoryBadge(formatDateTime(file.modified_at), "neutral")}
          </span>
          <small class="memory-card-summary">${escapeHtml(compactOutputText(file.summary || file.relative_path, 240))}</small>
        </button>
        <div class="memory-card-actions memory-archive-actions">
          <button
            class="secondary"
            data-memory-archive="${escapeHtml(file.file_name)}"
            data-memory-archive-key="${escapeHtml(memoryKey)}"
            data-memory-archive-state="${archived ? "restore" : "archive"}"
            type="button"
          >${archived ? "복원" : "보관"}</button>
        </div>
        </article>
      `;
  };
  const officialHtml = officialFiles.length
    ? `<div class="memory-section-heading">
        <span>공식 인증 파일 우선</span>
        <strong>${officialFiles.length}개</strong>
        <p>투자 판단에는 이 목록의 최신 공식 인증 리포트를 먼저 확인하세요.</p>
      </div>
      <div class="memory-card-list">${officialFiles.map(renderMemoryFileCard).join("")}</div>`
    : "";
  const legacyHtml = legacyFiles.length
    ? `<details class="memory-legacy-group"${officialFiles.length ? "" : " open"}>
        <summary>레거시/검증 전 파일 ${legacyFiles.length}개 ${officialFiles.length ? "보기" : "열기"}</summary>
        <p>정책: 레거시 파일은 하드 삭제하지 않고 소프트 보관으로 기본 목록에서 숨깁니다. 본문 확인은 가능하지만 투자 판단에는 공식 인증 리포트를 우선 사용하세요.</p>
        <div class="memory-card-actions">
          <button class="secondary" data-memory-archive-legacy="${escapeHtml(memoryKey)}" type="button">레거시 일괄 보관</button>
        </div>
        <div class="memory-card-list">${legacyFiles.map(renderMemoryFileCard).join("")}</div>
      </details>`
    : "";
  const archivedHtml = includeArchived && archivedFiles.length
    ? `<details class="memory-legacy-group memory-archive-group" open>
        <summary>보관 문서 ${archivedFiles.length}개 보기</summary>
        <p>이 문서는 삭제되지 않았고 화면 기본 목록과 자동 주입 후보에서만 제외됩니다. 필요하면 복원할 수 있습니다.</p>
        <div class="memory-card-list">${archivedFiles.map(renderMemoryFileCard).join("")}</div>
      </details>`
    : "";

  elements.memoryList.innerHTML = `${summaryHtml}${policyHtml}${warningHtml}${officialHtml}${legacyHtml}${archivedHtml}`;
}

function memoryListFetchOptions() {
  return {
    includeArchived: Boolean(
      elements.memoryForm?.querySelector('input[name="includeArchived"]')?.checked
    ),
  };
}

function ragDocumentType(document) {
  return document?.report_type || document?.type || "unknown";
}

function sortRagDocuments(documents) {
  const sorted = [...documents];
  const numberValue = (item, key) => {
    const value = Number(item?.[key]);
    return Number.isFinite(value) ? value : -Infinity;
  };
  if (ragSortMode === "quality_desc") {
    sorted.sort((a, b) => numberValue(b, "quality_score") - numberValue(a, "quality_score"));
  } else if (ragSortMode === "date_desc") {
    sorted.sort((a, b) => String(b.source_date || "").localeCompare(String(a.source_date || "")));
  } else if (ragSortMode === "ticker_asc") {
    sorted.sort((a, b) => String(a.ticker || "").localeCompare(String(b.ticker || "")));
  } else {
    sorted.sort((a, b) => numberValue(b, "relevance_score") - numberValue(a, "relevance_score"));
  }
  return sorted;
}

function filteredRagDocuments(searchResult) {
  const rawDocuments = Array.isArray(searchResult?.documents) ? searchResult.documents : [];
  const typeSet = new Set(rawDocuments.map(ragDocumentType).filter(Boolean));
  const tickerSet = new Set(rawDocuments.map((document) => document.ticker || "GENERAL").filter(Boolean));
  if (ragTypeFilter !== "all" && !typeSet.has(ragTypeFilter)) {
    ragTypeFilter = "all";
  }
  if (ragTickerFilter !== "all" && !tickerSet.has(ragTickerFilter)) {
    ragTickerFilter = "all";
  }
  const filtered = rawDocuments.filter((document) => {
    const matchesType = ragTypeFilter === "all" || ragDocumentType(document) === ragTypeFilter;
    const matchesTicker = ragTickerFilter === "all" || (document.ticker || "GENERAL") === ragTickerFilter;
    const matchesQuality =
      ragQualityFilter === "all" ||
      (ragQualityFilter === "injectable" && document.is_injectable) ||
      (ragQualityFilter === "isolated" && !document.is_injectable);
    return matchesType && matchesTicker && matchesQuality;
  });
  return sortRagDocuments(filtered);
}

function renderRagToolbar(searchResult, visibleCount) {
  const documents = Array.isArray(searchResult?.documents) ? searchResult.documents : [];
  const types = [...new Set(documents.map(ragDocumentType).filter(Boolean))].sort();
  const tickers = [...new Set(documents.map((document) => document.ticker || "GENERAL").filter(Boolean))].sort();
  const typeOptions = [
    `<option value="all"${ragTypeFilter === "all" ? " selected" : ""}>전체 유형</option>`,
    ...types.map(
      (type) =>
        `<option value="${escapeHtml(type)}"${ragTypeFilter === type ? " selected" : ""}>${escapeHtml(
          translateReportType(type)
        )}</option>`
    ),
  ].join("");
  const tickerOptions = [
    `<option value="all"${ragTickerFilter === "all" ? " selected" : ""}>전체 종목/범위</option>`,
    ...tickers.map(
      (ticker) =>
        `<option value="${escapeHtml(ticker)}"${ragTickerFilter === ticker ? " selected" : ""}>${escapeHtml(ticker)}</option>`
    ),
  ].join("");
  return `
    <div class="rag-filter-toolbar">
      <div>
        <span>검색 결과</span>
        <strong>${escapeHtml(visibleCount)} / ${escapeHtml(documents.length)}개 표시</strong>
      </div>
      <label>
        자료 유형
        <select data-rag-filter-type>
          ${typeOptions}
        </select>
      </label>
      <label>
        종목/범위
        <select data-rag-filter-ticker>
          ${tickerOptions}
        </select>
      </label>
      <label>
        품질
        <select data-rag-filter-quality>
          <option value="all"${ragQualityFilter === "all" ? " selected" : ""}>전체 품질</option>
          <option value="injectable"${ragQualityFilter === "injectable" ? " selected" : ""}>자동 주입 가능</option>
          <option value="isolated"${ragQualityFilter === "isolated" ? " selected" : ""}>격리 문서</option>
        </select>
      </label>
      <label>
        정렬
        <select data-rag-sort>
          <option value="relevance_desc"${ragSortMode === "relevance_desc" ? " selected" : ""}>관련도 높은 순</option>
          <option value="quality_desc"${ragSortMode === "quality_desc" ? " selected" : ""}>품질 높은 순</option>
          <option value="date_desc"${ragSortMode === "date_desc" ? " selected" : ""}>최근 날짜 순</option>
          <option value="ticker_asc"${ragSortMode === "ticker_asc" ? " selected" : ""}>종목명 순</option>
        </select>
      </label>
    </div>
  `;
}

function renderRagMemoryList(searchResult) {
  lastRagSearchResult = searchResult || null;
  const documents = filteredRagDocuments(searchResult);
  const allDocuments = searchResult?.documents || [];
  const includeLowQuality = Boolean(searchResult?.include_low_quality);
  const isGlobalSearch = searchResult?.module === "rag_memory_global_search";
  if (!allDocuments.length) {
    elements.memoryList.innerHTML = `
      <div class="dashboard-card warning">
        <span>${isGlobalSearch ? "전체 자연어 검색" : "RAG 검색"}</span>
        <strong>결과 없음</strong>
        <p>${escapeHtml(searchResult?.query || searchResult?.key || activeTicker)} 기준으로 자동 분석에 주입 가능한 문서가 없습니다.${includeLowQuality ? "" : " 격리 문서 포함을 켜면 저품질 문서까지 확인할 수 있습니다."}</p>
      </div>
    `;
    elements.memoryPreview.hidden = true;
    return;
  }

  const summary = `
    <div class="dashboard-card ${includeLowQuality ? "warning" : "ok"}">
      <span>${isGlobalSearch ? "전체 자연어 검색" : "RAG 품질 검색"}</span>
      <strong>${documents.length}개</strong>
      <p>${escapeHtml(isGlobalSearch ? searchResult.query || "검색어 없음" : searchResult.key)} · ${escapeHtml(searchResult.query || "전체")} · ${includeLowQuality ? "격리 문서 포함" : "자동 주입 가능 문서만"}${searchResult.grouped_count ? ` · 과거 버전 ${escapeHtml(searchResult.grouped_count)}개 묶음` : ""}</p>
    </div>
  `;

  const toolbar = renderRagToolbar(searchResult, documents.length);
  const emptyFilter = documents.length
    ? ""
    : `<div class="dashboard-card warning">
        <span>필터 결과</span>
        <strong>표시할 문서 없음</strong>
        <p>자료 유형 필터를 전체로 바꾸거나 다른 검색어를 입력하세요.</p>
      </div>`;

  elements.memoryList.innerHTML = `${summary}${toolbar}${emptyFilter}<div class="memory-card-list rag-card-list">${documents
    .map((document) => {
      const injectable = document.is_injectable;
      const qualityClass = injectable ? "verified" : "legacy";
      const qualityText = injectable ? "자동 주입 가능" : "격리됨";
      const flags = (document.quality_flags || []).map(translateQualityFlag).join(", ");
      const matched = (document.matched_terms || []).join(", ");
      const scoreText = document.relevance_score !== undefined ? ` · 관련도 ${escapeHtml(document.relevance_score)}` : "";
      const matchStrength = document.match_strength ? ` · ${escapeHtml(document.match_strength)} 매칭` : "";
      const tags = (document.tags || []).slice(0, 8).map(translateCaptureTag).filter(Boolean).join(", ");
      const relatedCount = Number(document.related_version_count || 0);
      const relatedText = relatedCount > 0 ? `과거 버전 ${formatNumber(relatedCount)}개 묶음` : "";
      const relatedVersions = (document.related_versions || []).slice(0, 6);
      const title = document.title || document.source_file_name || document.document_id;
      const summary = compactOutputText(document.summary || document.content_excerpt || document.source_relative_path, 300);
      const ticker = document.ticker || searchResult.key || activeTicker;
      const canAnalyzeTicker = isTickerLikeMemoryKey(ticker);
      const qualityBadgeClass = injectable ? "success" : "danger";
      const scoreBadge = document.relevance_score !== undefined ? memoryBadge(`관련도 ${document.relevance_score}`, "accent") : "";
      const matchBadge = document.match_strength ? memoryBadge(`${document.match_strength} 매칭`, "info") : "";
      const relatedBadge = relatedText ? memoryBadge(relatedText, "warning") : "";
      const relatedHtml = relatedVersions.length
        ? `
          <details class="rag-related-versions">
            <summary>과거 버전 ${escapeHtml(relatedVersions.length)}개 보기</summary>
            <div class="rag-related-version-list">
              ${relatedVersions
                .map(
                  (version) => `
                    <button
                      class="rag-related-version-button"
                      data-rag-file="${escapeHtml(version.source_file_name || "")}"
                      data-rag-ticker="${escapeHtml(document.ticker || searchResult.key || activeTicker)}"
                      type="button"
                    >
                      <strong>${escapeHtml(version.title || version.source_file_name || "과거 버전")}</strong>
                      <span>${escapeHtml(version.source_date || "날짜 없음")} · 품질 ${escapeHtml(version.quality_score ?? "n/a")}점${version.relevance_score !== undefined ? ` · 관련도 ${escapeHtml(version.relevance_score)}` : ""}</span>
                      <small>${escapeHtml(compactOutputText(version.summary || version.source_relative_path || "", 220))}</small>
                    </button>
                  `
                )
                .join("")}
            </div>
          </details>
        `
        : "";
      const actionButtons = `
        <div class="memory-card-actions">
          <button data-rag-action="open" data-rag-file="${escapeHtml(document.source_file_name || "")}" data-rag-ticker="${escapeHtml(ticker)}" type="button">저장 파일 열기</button>
          ${
            canAnalyzeTicker
              ? `<button data-rag-action="team" data-rag-ticker="${escapeHtml(ticker)}" data-rag-title="${escapeHtml(title)}" type="button">팀 리포트 실행</button>
                 <button data-rag-action="dossier" data-rag-ticker="${escapeHtml(ticker)}" type="button">Dossier 재합성</button>`
              : ""
          }
          <button data-rag-action="market" data-rag-title="${escapeHtml(title)}" data-rag-summary="${escapeHtml(summary)}" data-rag-url="${escapeHtml(document.source_url || "")}" type="button">시장일지로 반영</button>
        </div>
      `;
      return `
        <article
          class="memory-file-button memory-card rag-document ${qualityClass}"
          data-rag-file="${escapeHtml(document.source_file_name || "")}"
          data-rag-ticker="${escapeHtml(ticker)}"
        >
          <span class="memory-card-topline">
            <strong>${escapeHtml(title)}</strong>
            <span class="memory-card-action">${canAnalyzeTicker ? "분석 가능" : "자료 보관"}</span>
          </span>
          <span class="memory-card-meta">
            ${memoryBadge(ticker || "GENERAL", "neutral")}
            ${memoryBadge(qualityText, qualityBadgeClass)}
            ${memoryBadge(`품질 ${document.quality_score ?? "n/a"}점`, "info")}
            ${scoreBadge}
            ${matchBadge}
            ${memoryBadge(translateReportType(document.report_type), "neutral")}
            ${memoryBadge(document.source_date || "날짜 없음", "neutral")}
            ${relatedBadge}
          </span>
          <small class="memory-card-summary">${escapeHtml(summary)}</small>
          ${matched ? `<span class="memory-chip-row">${matched.split(",").slice(0, 8).map((item) => memoryBadge(item.trim(), "match")).join("")}</span>` : ""}
          ${tags ? `<span class="memory-chip-row">${tags.split(",").slice(0, 8).map((item) => memoryBadge(item.trim(), "tag")).join("")}</span>` : ""}
          ${flags ? `<small class="memory-card-note">품질 플래그: ${escapeHtml(flags)}</small>` : ""}
          ${actionButtons}
        </article>
        ${relatedHtml}
      `;
    })
    .join("")}</div>`;
}

function memoryBadge(label, tone = "neutral") {
  const cleaned = String(label || "").trim();
  if (!cleaned) {
    return "";
  }
  return `<span class="memory-badge ${escapeHtml(tone)}">${escapeHtml(cleaned)}</span>`;
}

function attachmentExtractionBadge(attachment = {}) {
  if (!attachment || !Object.keys(attachment).length) {
    return null;
  }
  const profile = attachment.extraction_profile || {};
  const note = String(
    attachment.extraction_status ||
      attachment.text_extraction ||
      profile.text_extraction ||
      ""
  );
  const charCount = Number(
    attachment.extraction_char_count ??
      profile.char_count ??
      0
  );
  const ocrStatus = profile.ocr_status || "";
  if (note.includes("완료") || ocrStatus === "success") {
    return { label: "OCR/추출 완료", tone: "success" };
  }
  if (ocrStatus === "empty" || note.includes("인식 가능한 텍스트를 찾지 못")) {
    return { label: "OCR 본문 없음", tone: "warning" };
  }
  if (ocrStatus === "error" || note.includes("OCR 실패") || note.includes("OCR 미실행")) {
    return { label: "OCR 오류", tone: "warning" };
  }
  if (ocrStatus === "unavailable" || note.includes("Tesseract OCR 실행 파일을 찾지 못")) {
    return { label: "OCR 미연결", tone: "warning" };
  }
  if (charCount > 0) {
    return { label: "본문 추출", tone: "success" };
  }
  return { label: "본문 없음", tone: "warning" };
}

function attachmentOcrStatusLine(attachment = {}) {
  if (!attachment || !Object.keys(attachment).length) {
    return "OCR 상태: 첨부 파일 없음";
  }
  const profile = attachment.extraction_profile || {};
  const ocrStatus = String(profile.ocr_status || "").trim();
  const language = profile.ocr_language ? ` · 언어 ${profile.ocr_language}` : "";
  const charCount = Number(
    attachment.extraction_char_count ??
      profile.char_count ??
      0
  );
  if (charCount <= 0 && (ocrStatus === "success" || profile.used_ocr)) {
    return `OCR 상태: 보강 필요${language} · OCR 경로는 확인됐지만 추출 본문이 없습니다.`;
  }
  if (ocrStatus === "success" || (profile.used_ocr && charCount > 0)) {
    return `OCR 상태: 완료${language} · 추출 본문 ${formatNumber(charCount)}자`;
  }
  if (ocrStatus === "empty") {
    return `OCR 상태: 본문 없음${language} · 이미지에서 인식 가능한 텍스트를 찾지 못했습니다.`;
  }
  if (ocrStatus === "unavailable") {
    return "OCR 상태: 미연결 · Tesseract 실행 파일 또는 OCR 런타임 확인이 필요합니다.";
  }
  if (ocrStatus === "error") {
    return `OCR 상태: 오류 · ${profile.ocr_error || attachment.text_extraction || "OCR 처리 중 문제가 발생했습니다."}`;
  }
  if (isImageDocumentType(attachment.document_type) || String(attachment.mime_type || "").startsWith("image/")) {
    return `OCR 상태: 확인 필요 · 추출 본문 ${formatNumber(charCount)}자`;
  }
  return `OCR 상태: 해당 없음 · 일반 텍스트/PDF 추출 본문 ${formatNumber(charCount)}자`;
}

function isImageDocumentType(documentType) {
  return /이미지|image/i.test(String(documentType || ""));
}

function needsMemoryBodySupplement(file) {
  if (memoryFileNeedsBodySupplement(file)) {
    return true;
  }
  const tagValues = [
    ...(Array.isArray(file?.tags) ? file.tags : []),
    ...(Array.isArray(file?.json_payload?.captured_item?.tags)
      ? file.json_payload.captured_item.tags
      : []),
    ...(Array.isArray(file?.json_payload?.body_supplements) ? ["body_supplemented"] : []),
  ];
  const manifestTags = Array.isArray(file?.json_payload?.tags) ? file.json_payload.tags : [];
  const text = [
    file?.content,
    file?.summary,
    file?.capture_quality?.status,
    file?.source_url_processing?.status,
    file?.data_quality_status,
    file?.json_payload?.capture_quality?.status,
    file?.json_payload?.source_url_processing?.status,
    ...tagValues,
    ...manifestTags,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (/body_supplemented|본문 보강/.test(text)) {
    return false;
  }
  return /needs_body_copy|url_text_unavailable|empty_text|fetch_failed|웹사이트 url 보관|본문 추출이 제한|보강 필요/.test(text);
}

function renderMemorySupplementControls(file) {
  if (!elements.memorySupplementForm) {
    return;
  }
  const shouldShow = needsMemoryBodySupplement(file);
  elements.memorySupplementForm.hidden = !shouldShow;
  if (!shouldShow) {
    if (elements.memorySupplementBody) {
      elements.memorySupplementBody.value = "";
    }
    if (elements.memorySupplementNote) {
      elements.memorySupplementNote.value = "";
    }
    return;
  }
  elements.memorySupplementForm.dataset.memoryKey = file.ticker || "";
  elements.memorySupplementForm.dataset.memoryFile = file.file_name || "";
  if (elements.memorySupplementHelp) {
    elements.memorySupplementHelp.textContent =
      "웹 본문 추출이 제한된 저장 자료입니다. 원문을 복사해 붙여 넣으면 기존 파일, 메타데이터, RAG 색인을 함께 갱신합니다.";
  }
}

function renderMemoryPreview(file) {
  activeMemoryPreviewFile = file;
  elements.memoryPreview.hidden = false;
  elements.memoryPreviewTitle.textContent = file.file_name;
  const status = file.legacy
    ? "레거시/검증 전 파일입니다. 투자 판단에는 새 공식 인증 리포트를 우선 사용하세요."
    : "공식 인증 리포트";
  const attachmentBadge = attachmentExtractionBadge(file.attachment);
  const extractionText = attachmentBadge ? ` · ${attachmentBadge.label}` : "";
  elements.memoryPreviewMeta.textContent = `${file.ticker} · ${file.status_label || status}${extractionText} · ${file.relative_path} · ${formatDateTime(file.modified_at)}`;
  elements.memoryPreviewContent.textContent = cleanStoredReportContent(file.content);
  renderMemorySupplementControls(file);
}

function renderTickerCache(cache) {
  const entries = cache?.entries || [];
  const visibleEntries = entries.slice(0, 80);
  const hiddenCount = Math.max(0, entries.length - visibleEntries.length);
  const sourceStatus = cache?.source_status || {};
  const sourceSummary = (sourceStatus.sources || [])
    .map(
      (item) =>
        `${translateTickerRegistrySourceName(item.source)} ${formatNumber(item.count || 0)}개`
    )
    .join(" · ");
  if (!elements.tickerCacheList) {
    return;
  }

  if (!entries.length) {
    elements.tickerCacheList.innerHTML = `
      <div class="ticker-cache-card">
        <strong>자동 인증 캐시 없음</strong>
        <span>로컬 공식 등록 ${cache?.local_registry_count || 0}개</span>
        <small>${escapeHtml(sourceSummary || "KRX/KIND, Nasdaq Trader 원천 목록을 조회하면 자동 캐시에 저장됩니다.")}</small>
      </div>
    `;
    return;
  }

  const header = `
    <article class="ticker-cache-card ticker-cache-summary-card">
      <strong>티커 원천 캐시 ${escapeHtml(formatNumber(cache.cache_count || entries.length))}개</strong>
      <span>공식 등록 ${escapeHtml(formatNumber(cache.local_registry_count || 0))}개 · 원천 ${escapeHtml(formatNumber(sourceStatus.success_count || 0))}/${escapeHtml(formatNumber(sourceStatus.source_count || 0))}개 성공</span>
      <small>${escapeHtml(sourceSummary || "KRX/KIND, Nasdaq Trader, 외부 프로필 캐시를 함께 사용합니다.")}${sourceStatus.updated_at ? ` · 갱신 ${escapeHtml(formatDateTime(sourceStatus.updated_at))}` : ""}</small>
    </article>
  `;

  elements.tickerCacheList.innerHTML = header + visibleEntries
    .map(
      (entry) => `
        <article class="ticker-cache-card">
          <strong>${escapeHtml(entry.ticker)} · ${escapeHtml(entry.company_name || "회사명 없음")}</strong>
          <span>${escapeHtml(entry.exchange || "거래소 미확인")} · ${escapeHtml(
            entry.sector || "섹터 미등록"
          )} · ${escapeHtml(translateVerificationSource(entry.verification_source))}</span>
          <small>${escapeHtml(
            (entry.data_limitations || [])[0] ||
              "다음 분석부터 이 인증 정보를 재사용합니다."
          )}</small>
          <div class="ticker-cache-card-actions">
            <button data-cache-load="${escapeHtml(entry.ticker)}" type="button">대시보드</button>
            <button class="secondary" data-cache-delete="${escapeHtml(entry.ticker)}" type="button">캐시 삭제</button>
          </div>
        </article>
      `
    )
    .join("") + (hiddenCount
      ? `
        <article class="ticker-cache-card ticker-cache-summary-card">
          <strong>나머지 ${escapeHtml(formatNumber(hiddenCount))}개는 자동 인증에만 사용</strong>
          <span>화면 속도 보호를 위해 목록 렌더링은 최근/상위 ${escapeHtml(formatNumber(visibleEntries.length))}개로 제한했습니다.</span>
          <small>회사명 또는 티커 입력 시 전체 ${escapeHtml(formatNumber(entries.length))}개 캐시에서 계속 인증합니다.</small>
        </article>
      `
      : "");
}

function dailyRecommendationStatusLabel(status) {
  return {
    success: "저장 완료",
    skipped_existing: "오늘 저장됨",
    pending: "추적 대기",
    complete: "추적 완료",
    price_unavailable: "가격 미확인",
    not_found: "후보 없음",
    warning: "확인 필요",
  }[status] || status || "상태 미확인";
}

function dailyRecommendationEvidenceCategories(record) {
  const text = [
    ...(record?.score_components || []).map((item) => item.label),
    ...(record?.evidence_sources || []),
    ...(record?.reasons || []),
    ...(record?.risk_notes || []),
    ...(record?.score_penalties || []),
    ...(record?.quality_flags || []),
  ].join(" ");
  const categories = [];
  const add = (label, pattern) => {
    if (pattern.test(text) && !categories.includes(label)) {
      categories.push(label);
    }
  };
  add("가격/밸류", /가격|현재가|목표가|밸류|상승여력|valuation/i);
  add("공시", /공시|DART|filing/i);
  add("리포트", /리포트|증권사|컨센서스|목표주가|report/i);
  add("공개 IR/SEC", /공개 IR|IR\/SEC|SEC|EDGAR|public IR|public_ir_sec/i);
  add("수급/보유", /보유|포트폴리오|관심|수급|대량보유|institution/i);
  add("저장/RAG", /저장|RAG|자료|문서|스냅샷|시장일지/i);
  add("리스크", /리스크|위험|감점|확인|보강|미확인|quality|penalt/i);
  if (!categories.length) {
    categories.push("기본 점검");
  }
  return categories.slice(0, 6);
}

function dailyRecommendationChangeText(milestone, currency = "KRW") {
  if (!milestone || milestone.price === null || milestone.price === undefined) {
    return "가격 대기";
  }
  const changePct =
    milestone.price_change_pct === null || milestone.price_change_pct === undefined
      ? ""
      : ` · ${toPercent(milestone.price_change_pct)}`;
  const change =
    milestone.price_change === null || milestone.price_change === undefined
      ? ""
      : ` · ${formatSmartPrice(milestone.price_change, currency, "변동 미확인")}`;
  return `${formatSmartPrice(milestone.price, currency, "가격 미확인")}${change}${changePct}`;
}

function dailyRecommendationMilestoneShortLabel(milestone) {
  const rawLabel = String(milestone?.label || milestone?.key || "").trim();
  const normalized = rawLabel.toLowerCase();
  if (rawLabel.includes("15") || normalized.includes("15d")) {
    return "15일";
  }
  if (rawLabel.includes("6달") || normalized.includes("month_6") || normalized.includes("6m")) {
    return "6달";
  }
  if (rawLabel.includes("3달") || normalized.includes("month_3") || normalized.includes("3m")) {
    return "3달";
  }
  if (rawLabel.includes("1달") || normalized.includes("month_1") || normalized.includes("1m") || normalized.includes("30d")) {
    return "1달";
  }
  if (rawLabel.includes("1주") || rawLabel.includes("7") || normalized.includes("week_1") || normalized.includes("7d")) {
    return "1주";
  }
  return rawLabel || "추적";
}

function dailyRecommendationMilestoneTone(milestone) {
  const status = milestone?.status || "pending";
  const pct = Number(milestone?.price_change_pct);
  if (Number.isFinite(pct)) {
    if (pct > 0) {
      return "up";
    }
    if (pct < 0) {
      return "down";
    }
    return "flat";
  }
  if (status === "complete" || status === "success" || status === "skipped_existing") {
    return "complete";
  }
  if (status === "warning" || status === "price_unavailable") {
    return "warning";
  }
  if (status === "not_found") {
    return "missing";
  }
  return "pending";
}

function dailyRecommendationGroupRecords(records) {
  const groups = new Map();
  records.forEach((record) => {
    const date = record.recommendation_date || "추천일 미확인";
    if (!groups.has(date)) {
      groups.set(date, []);
    }
    groups.get(date).push(record);
  });
  return Array.from(groups.entries())
    .sort(([left], [right]) => String(right).localeCompare(String(left)))
    .map(([date, items]) => ({
      date,
      records: items.slice().sort((left, right) => Number(left.rank || 99) - Number(right.rank || 99)),
    }));
}

function dailyRecommendationMilestoneSummary(records) {
  const order = ["1주", "15일", "1달", "3달", "6달"];
  const summary = order.reduce((acc, label) => {
    acc[label] = {
      label,
      total: 0,
      complete: 0,
      up: 0,
      down: 0,
      flat: 0,
      pending: 0,
      warning: 0,
    };
    return acc;
  }, {});
  records.forEach((record) => {
    (record.tracking_milestones || []).forEach((milestone) => {
      const label = dailyRecommendationMilestoneShortLabel(milestone);
      if (!summary[label]) {
        summary[label] = {
          label,
          total: 0,
          complete: 0,
          up: 0,
          down: 0,
          flat: 0,
          pending: 0,
          warning: 0,
        };
      }
      const tone = dailyRecommendationMilestoneTone(milestone);
      summary[label].total += 1;
      summary[label][tone] = (summary[label][tone] || 0) + 1;
      if (tone === "up" || tone === "down" || tone === "flat" || tone === "complete") {
        summary[label].complete += 1;
      }
      if (tone === "pending" || tone === "warning" || tone === "missing") {
        summary[label].pending += 1;
      }
    });
  });
  return order.map((label) => summary[label]).filter((item) => item.total > 0);
}


function investmentCalendarEventsByDate(payload) {
  const monthly = payload?.monthly || {};
  const events = [...(monthly.KR || []), ...(monthly.US || [])];
  return events.reduce((acc, event) => {
    const dateKey = String(event.date || "").slice(0, 10);
    if (!dateKey) {
      return acc;
    }
    if (!acc.has(dateKey)) {
      acc.set(dateKey, []);
    }
    acc.get(dateKey).push(event);
    return acc;
  }, new Map());
}

function investmentCalendarMonthLabel(calendarMonth) {
  if (!calendarMonth || !/^\d{4}-\d{2}$/.test(calendarMonth)) {
    return "투자 캘린더";
  }
  const [year, month] = calendarMonth.split("-");
  return `${year}년 ${Number(month)}월 투자 캘린더`;
}

function investmentCalendarEventIsEarnings(event) {
  return event?.event_type === "earnings" || /실적|earnings/i.test(`${event?.category || ""} ${event?.title || ""}`);
}

function renderInvestmentCalendar(payload) {
  if (!elements.investmentCalendarMonthly || !elements.investmentCalendarWeekly) {
    return;
  }
  const calendarMonth = payload?.calendar_month || "";
  const title = investmentCalendarMonthLabel(calendarMonth);
  const universe = payload?.universe_summary || {};
  if (elements.investmentCalendarTitle) {
    elements.investmentCalendarTitle.textContent = title;
  }
  if (elements.investmentCalendarMeta) {
    const earningsCount = Number(payload?.earnings_event_count || 0);
    const earningsLabel = earningsCount ? ` · 실적발표 ${formatNumber(earningsCount)}건` : "";
    elements.investmentCalendarMeta.textContent = `보유 ${formatNumber(universe.holdings_count || 0)}개 · 관심 ${formatNumber(universe.interest_count || 0)}개${earningsLabel} · 갱신 ${formatDateTime(payload?.updated_at || payload?.generated_at)}`;
  }
  if (!calendarMonth || !payload?.monthly) {
    elements.investmentCalendarMonthly.innerHTML = `<p class="empty-state">${escapeHtml(payload?.message || "표시할 투자 캘린더가 없습니다.")}</p>`;
    elements.investmentCalendarWeekly.innerHTML = "";
    return;
  }
  const [year, month] = calendarMonth.split("-").map(Number);
  const first = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0).getDate();
  const offset = first.getDay();
  const byDate = investmentCalendarEventsByDate(payload);
  const dayCells = [];
  for (let i = 0; i < offset; i += 1) {
    dayCells.push('<div class="investment-calendar-day is-empty"></div>');
  }
  for (let day = 1; day <= lastDay; day += 1) {
    const dateKey = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const events = (byDate.get(dateKey) || []).slice().sort((left, right) => String(left.market).localeCompare(String(right.market)));
    dayCells.push(`
      <div class="investment-calendar-day${events.length ? " has-events" : ""}">
        <div class="investment-calendar-day-number">${day}</div>
        <div class="investment-calendar-events">
          ${events
            .slice(0, 4)
            .map(
              (event) => `
                <div class="investment-calendar-event market-${escapeHtml(String(event.market || "").toLowerCase())}${investmentCalendarEventIsEarnings(event) ? " is-earnings" : ""}" title="${escapeHtml(`${event.date || ""} · ${event.category || "일정"} · ${event.title || "일정"}`)}">
                  <b>${escapeHtml(event.market || "시장")} · ${escapeHtml(event.category || "일정")}</b>
                  <span>${escapeHtml(compactOutputText(event.title || "일정", 72))}</span>
                  <em>${escapeHtml((event.related || []).slice(0, 2).join(" · ") || "전체")}</em>
                </div>
              `
            )
            .join("")}
          ${events.length > 4 ? `<small>+${events.length - 4}개 더 있음</small>` : ""}
        </div>
      </div>
    `);
  }
  elements.investmentCalendarMonthly.innerHTML = `
    <div class="investment-calendar-weekdays">
      ${["일", "월", "화", "수", "목", "금", "토"].map((day) => `<b>${day}</b>`).join("")}
    </div>
    <div class="investment-calendar-grid">${dayCells.join("")}</div>
  `;
  const weekly = payload.weekly || {};
  elements.investmentCalendarWeekly.innerHTML = Object.entries(weekly)
    .map(([weekName, markets]) => {
      const krEvents = markets.KR || [];
      const usEvents = markets.US || [];
      return `
        <section class="investment-calendar-week">
          <header><strong>${escapeHtml(weekName)}</strong><span>한국 ${formatNumber(krEvents.length)}개 · 미국 ${formatNumber(usEvents.length)}개</span></header>
          <div class="investment-calendar-market-columns">
            ${renderInvestmentCalendarMarketColumn("한국", krEvents)}
            ${renderInvestmentCalendarMarketColumn("미국", usEvents)}
          </div>
        </section>
      `;
    })
    .join("") || '<p class="empty-state">주간 일정이 없습니다.</p>';
}

function renderInvestmentCalendarMarketColumn(label, events) {
  return `
    <div class="investment-calendar-market-column">
      <h3>${escapeHtml(label)}</h3>
      ${events.length
        ? events
            .map(
              (event) => `
                <article class="investment-calendar-list-event${investmentCalendarEventIsEarnings(event) ? " is-earnings" : ""}">
                  <span>${escapeHtml(event.date || "날짜 미확인")} · ${escapeHtml(event.category || "일정")}</span>
                  <strong>${escapeHtml(event.title || "시장 일정")}</strong>
                  <p>${escapeHtml(event.impact || "투자 영향 메모 없음")}</p>
                  <small>${escapeHtml((event.related || []).slice(0, 5).join(" · ") || "보유/관심 전체")}${event.source ? ` · 출처 ${escapeHtml(event.source)}` : ""}</small>
                </article>
              `
            )
            .join("")
        : '<p class="empty-state">관련 일정 없음</p>'}
    </div>
  `;
}

async function loadInvestmentCalendar({ showOutput = false } = {}) {
  syncApiBaseUrl();
  const payload = await fetchInvestmentCalendar(token());
  renderInvestmentCalendar(payload);
  if (showOutput) {
    setOutput(payload || "투자 캘린더를 불러오지 못했습니다.");
  }
  return payload;
}

function renderDailyRecommendationCards(payload) {
  if (!elements.dailyRecommendationCards || !payload || typeof payload !== "object") {
    return;
  }
  const records = (payload.latest_records || payload.records || []).slice(0, 3);
  const allRecords = Array.isArray(payload.records) ? payload.records : records;
  if (!records.length) {
    elements.dailyRecommendationCards.innerHTML = `
      <article class="daily-recommendation-card daily-recommendation-summary warning">
        <span>매일 추천 후보</span>
        <strong>저장된 후보 없음</strong>
        <p>${escapeHtml(payload.message || "오늘 추천 후보 1~3위를 생성하면 이 영역에 저장 이력과 추적 일정이 표시됩니다.")}</p>
      </article>
    `;
    return;
  }
  const milestoneCounts = records.reduce(
    (acc, record) => {
      (record.tracking_milestones || []).forEach((milestone) => {
        const status = milestone.status || "pending";
        acc[status] = (acc[status] || 0) + 1;
      });
      return acc;
    },
    {}
  );
  const performance = payload.performance_summary || {};
  const recommendationDates = Array.isArray(payload.recommendation_dates)
    ? payload.recommendation_dates.slice(0, 6)
    : [];
  const dailyGroups = dailyRecommendationGroupRecords(allRecords).slice(0, 8);
  const milestoneSummary = dailyRecommendationMilestoneSummary(allRecords);
  const qualitySummary = records.reduce(
    (acc, record) => {
      acc.penaltyCount += (record.score_penalties || []).length;
      acc.flagCount += (record.quality_flags || []).length;
      if (record.overseas_tracking?.needs_fx_conversion) {
        acc.overseasCount += 1;
      }
      if (record.portfolio_risk_connection?.linked) {
        acc.portfolioLinkedCount += 1;
      }
      return acc;
    },
    { penaltyCount: 0, flagCount: 0, overseasCount: 0, portfolioLinkedCount: 0 }
  );
  const cards = records
    .map((record) => {
      const reasons = (record.reasons || []).slice(0, 3);
      const evidence = (record.evidence_sources || []).slice(0, 3);
      const scoreComponents = (record.score_components || []).slice(0, 4);
      const scoreWeights = (record.score_explanation?.component_weights || []).slice(0, 3);
      const penalties = (record.score_penalties || []).slice(0, 3);
      const qualityFlags = (record.quality_flags || []).slice(0, 3);
      const totalPositivePoints = (record.score_components || []).reduce(
        (sum, component) => sum + Number(component.points || 0),
        0
      );
      const totalPenaltyCount = (record.score_penalties || []).length + (record.quality_flags || []).length;
      const topScoreComponent = (record.score_components || [])
        .slice()
        .sort((a, b) => Number(b.points || 0) - Number(a.points || 0))[0];
      const overseasTracking = record.overseas_tracking || {};
      const portfolioRisk = record.portfolio_risk_connection || {};
      const milestones = (record.tracking_milestones || []).slice(0, 5);
      const categories = dailyRecommendationEvidenceCategories(record);
      const publicIrSecLinked = categories.includes("공개 IR/SEC");
      return `
        <article class="daily-recommendation-card${publicIrSecLinked ? " has-public-ir-sec" : ""}">
          <span>${escapeHtml(record.recommendation_date || payload.latest_recommendation_date || "추천일 미확인")} · ${escapeHtml(record.rank || "-")}위</span>
          <strong>${escapeHtml(displayCompanyName(record))}</strong>
          ${publicIrSecLinked ? `<div class="daily-recommendation-badges"><em>공개 IR/SEC 근거</em></div>` : ""}
          <p>기준가 ${escapeHtml(formatSmartPrice(record.baseline_price, record.currency || "KRW", "미확인"))} · 점수 ${escapeHtml(record.score ?? "n/a")}</p>
          <p class="daily-recommendation-score-summary">가점 ${escapeHtml(formatNumber(totalPositivePoints))}점 · 확인 ${escapeHtml(formatNumber(totalPenaltyCount))}건 · 핵심 ${escapeHtml(topScoreComponent?.label || "저장 전")}</p>
          <div class="daily-recommendation-score">
            ${scoreComponents
              .map(
                (component) =>
                  `<em>${escapeHtml(component.label)} +${escapeHtml(formatNumber(component.points || 0))}</em>`
              )
              .join("") || "<em>점수 구성 저장 전</em>"}
          </div>
          <small>${escapeHtml(
            scoreWeights.length
              ? `주요 비중: ${scoreWeights
                  .map((component) => `${component.label} ${component.weight_pct}%`)
                  .join(" · ")}`
              : "점수 비중은 다음 추천 생성부터 표시됩니다."
          )}</small>
          <small>${escapeHtml(`근거 분류: ${categories.join(" · ")}`)}</small>
          ${
            penalties.length || qualityFlags.length
              ? `<p class="daily-recommendation-warning">확인/감점: ${escapeHtml(
                  [...penalties, ...qualityFlags].join(" · ")
                )}</p>`
              : ""
          }
          ${
            overseasTracking.needs_fx_conversion
              ? `<p class="daily-recommendation-fx">해외 추적: ${escapeHtml(
                  overseasTracking.currency || record.currency || "USD"
                )} 기준 가격과 USD/KRW 환율 반영 상태를 함께 확인합니다.</p>`
              : ""
          }
          ${
            portfolioRisk.linked
              ? `<p class="daily-recommendation-portfolio">포트폴리오 연결: ${escapeHtml(
                  portfolioRisk.message || "보유/관심 노출과 함께 확인하세요."
                )}</p>`
              : ""
          }
          <ul>
            ${reasons.map((item) => `<li>${escapeHtml(compactOutputText(item, 110))}</li>`).join("") || "<li>근거 요약 없음</li>"}
          </ul>
          <small>${escapeHtml(evidence.join(" · ") || "저장 근거 없음")}</small>
          <div class="daily-recommendation-milestones">
            ${milestones
              .map(
                (milestone) => `
                  <b class="milestone-${escapeHtml(dailyRecommendationMilestoneTone(milestone))}" title="${escapeHtml(milestone.target_date || "")}">
                    ${escapeHtml(dailyRecommendationMilestoneShortLabel(milestone))} · ${escapeHtml(dailyRecommendationStatusLabel(milestone.status))}
                  </b>
                `
              )
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");
  elements.dailyRecommendationCards.innerHTML = `
    <article class="daily-recommendation-card daily-recommendation-summary ok">
      <span>오늘의 추천 결과</span>
      <strong>${escapeHtml(payload.latest_recommendation_date || payload.recommendation_date || "추천일 미확인")}</strong>
      <p>저장 ${escapeHtml(formatNumber(payload.record_count || records.length))}개 · 최근일 대기 ${escapeHtml(formatNumber(milestoneCounts.pending || 0))}개 · 누적 완료 ${escapeHtml(formatNumber(performance.complete_count || 0))}개 · 가격 미확인 ${escapeHtml(formatNumber(performance.price_unavailable_count || 0))}개</p>
      <small>${escapeHtml(
        `품질 가드: 감점 ${formatNumber(qualitySummary.penaltyCount)}개 · 확인 ${formatNumber(qualitySummary.flagCount)}개 · 포트폴리오 연결 ${formatNumber(qualitySummary.portfolioLinkedCount)}개 · 해외 추적 ${formatNumber(qualitySummary.overseasCount)}개`
      )}</small>
      <small>${escapeHtml(recommendationDates.length ? `추천 이력: ${recommendationDates.join(" · ")}` : "추천 이력은 저장 후 누적됩니다.")}</small>
    </article>
    ${cards}
    <article class="daily-recommendation-card daily-recommendation-daily-list">
      <span>일자별 추천 목록</span>
      <strong>매일 1위부터 3위</strong>
      <div class="daily-recommendation-date-groups">
        ${dailyGroups
          .map(
            (group) => `
              <section class="daily-recommendation-date-group">
                <header>
                  <b>${escapeHtml(group.date)}</b>
                  <em>${escapeHtml(formatNumber(group.records.length))}개</em>
                </header>
                <div>
                  ${group.records
                    .map(
                      (record) => `
                        <p class="daily-recommendation-date-row">
                          <span>${escapeHtml(record.rank || "-")}위</span>
                          <strong>${escapeHtml(displayCompanyName(record))}</strong>
                          <em>${escapeHtml(formatSmartPrice(record.baseline_price, record.currency || "KRW", "기준가 미확인"))} · 점수 ${escapeHtml(record.score ?? "n/a")}</em>
                        </p>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
          )
          .join("") || "<p>저장된 일자별 추천 목록이 없습니다.</p>"}
      </div>
    </article>
    <article class="daily-recommendation-card daily-recommendation-progress">
      <span>경과 그래프</span>
      <strong>1주 · 15일 · 1달 · 3달 · 6달</strong>
      <p>완료 ${escapeHtml(formatNumber(performance.complete_count || 0))}개 · 상승 ${escapeHtml(formatNumber(performance.positive_count || 0))}개 · 하락 ${escapeHtml(formatNumber(performance.negative_count || 0))}개 · 대기 ${escapeHtml(formatNumber(performance.pending_count || 0))}개</p>
      <div class="daily-recommendation-progress-grid">
        ${milestoneSummary
          .map((item) => {
            const progress = item.total ? Math.round((item.complete / item.total) * 100) : 0;
            const tone = item.up > item.down ? "up" : item.down > item.up ? "down" : item.complete ? "flat" : "pending";
            return `
              <section class="daily-recommendation-progress-card milestone-${escapeHtml(tone)}">
                <header>
                  <b>${escapeHtml(item.label)}</b>
                  <em>${escapeHtml(formatNumber(item.complete))}/${escapeHtml(formatNumber(item.total))}</em>
                </header>
                <div class="daily-recommendation-progress-bar" aria-label="${escapeHtml(item.label)} 완료율 ${escapeHtml(formatNumber(progress))}%">
                  <i style="width: ${escapeHtml(String(progress))}%"></i>
                </div>
                <small>상승 ${escapeHtml(formatNumber(item.up))} · 하락 ${escapeHtml(formatNumber(item.down))} · 대기 ${escapeHtml(formatNumber(item.pending))}</small>
              </section>
            `;
          })
          .join("") || "<p>경과 그래프를 만들 추적 데이터가 없습니다.</p>"}
      </div>
      <div class="daily-recommendation-timeline">
        ${records
          .map(
            (record) => `
              <section class="daily-recommendation-timeline-row">
                <header>
                  <b>${escapeHtml(record.rank || "-")}위 ${escapeHtml(displayCompanyName(record))}</b>
                  <em>기준 ${escapeHtml(formatSmartPrice(record.baseline_price, record.currency || "KRW", "미확인"))}</em>
                </header>
                <div class="daily-recommendation-timeline-steps">
                  ${(record.tracking_milestones || [])
                    .slice(0, 5)
                    .map((milestone) => {
                      const tone = dailyRecommendationMilestoneTone(milestone);
                      return `
                        <span class="daily-recommendation-timeline-step milestone-${escapeHtml(tone)}" title="${escapeHtml(milestone.target_date || "")}">
                          <b>${escapeHtml(dailyRecommendationMilestoneShortLabel(milestone))}</b>
                          <small>${escapeHtml(milestone.target_date || "일자 미확인")}</small>
                          <em>${escapeHtml(dailyRecommendationChangeText(milestone, record.currency || "KRW"))}</em>
                        </span>
                      `;
                    })
                    .join("")}
                </div>
              </section>
            `
          )
          .join("")}
      </div>
    </article>
  `;
}

function translateTickerRegistrySourceName(source) {
  const labels = {
    krx_kind: "KRX/KIND",
    nasdaq_listed: "NASDAQ",
    nasdaq_other: "NYSE/AMEX 등",
  };
  return labels[source] || source || "출처 미확인";
}

async function loadTickerCache() {
  syncApiBaseUrl();
  startOutputLoading("티커 자동 인증 캐시 조회 중", [
    "저장된 인증 캐시 읽기",
    "회사명과 거래소 정보 정리",
    "화면 렌더링용 대표 항목 구성",
  ]);
  const cache = await fetchTickerRegistryCache(token());
  renderTickerCache(cache);
  setOutput(summarizeTickerCacheForOutput(cache) || "티커 자동 인증 캐시를 불러오지 못했습니다.");
  return cache;
}

function summarizeTickerCacheForOutput(cache) {
  if (!cache || typeof cache !== "object") {
    return cache;
  }
  return {
    ...cache,
    entries: (cache.entries || []).slice(0, 25),
    displayed_entry_count: Math.min((cache.entries || []).length, 25),
    hidden_entry_count: Math.max(0, (cache.entries || []).length - 25),
  };
}

function activateTab(tabName, options = {}) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === tabName);
  });
  if (tabName === "investmentCalendar") {
    loadInvestmentCalendar({ showOutput: false }).catch(setError);
  }
  if (!options.keepOutput) {
    setOutput(tabHelpText(tabName));
  }
}

function buildInterestRagQuery(row, fallbackKey, mode = "ticker") {
  const get = (name) => rowValue(row, name);
  const company = get("companyName") || get("name") || fallbackKey;
  const ticker = get("ticker");
  const tags = get("tags");
  const thesis = get("thesis");
  const notes = get("notes");
  const focus =
    mode === "sector"
      ? "섹터 동향, 수급, 정책, 리스크, 수혜 기업"
      : "최근 뉴스, 실적, 수급, 리스크, 투자 논거 변화";
  return [company, ticker, tags, thesis || notes, focus]
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

async function runInterestRagAction({ query, key, mode }) {
  const normalizedQuery = String(query || "").trim();
  if (!normalizedQuery) {
    throw new Error("검색할 관심 항목 내용을 확인하지 못했습니다.");
  }
  activateTab("memory", { keepOutput: true });
  if (elements.memoryForm?.elements?.ticker) {
    elements.memoryForm.elements.ticker.value = key || normalizedQuery;
  }
  if (elements.memoryForm?.elements?.ragQuery) {
    elements.memoryForm.elements.ragQuery.value = normalizedQuery;
  }
  const includeLowQuality = Boolean(
    elements.memoryForm?.querySelector('input[name="includeLowQuality"]')?.checked
  );

  if (mode === "synthesis") {
    startOutputLoading("관심 항목 검색 결과 합성 중", [
      "저장 데이터 전체 검색",
      "중복 자료 묶음 반영",
      "강세·약세 논거 분리",
      "핵심 쟁점과 관찰 지표 저장",
    ]);
    const result = await synthesizeRagSearchResults(token(), {
      query: normalizedQuery,
      limit: 15,
      includeLowQuality,
      saveResult: true,
    });
    if (!result) {
      throw new Error("관심 항목 검색 합성 결과를 생성하지 못했습니다.");
    }
    setOutput(result);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
    return result;
  }

  startOutputLoading("관심 항목 저장 데이터 검색 중", [
    "전체 RAG 색인 확인",
    "관심 이유와 태그를 검색어에 반영",
    "관련 저장 데이터 카드 구성",
  ]);
  const result = await searchAllRagMemoryDocuments(token(), {
    query: normalizedQuery,
    limit: 15,
    includeLowQuality,
  });
  if (!result) {
    throw new Error("관심 항목 저장 데이터 검색 결과를 불러오지 못했습니다.");
  }
  renderRagMemoryList(result);
  setOutput(result);
  return result;
}

function researchUpdateStepSummary(key, result) {
  if (!result) {
    return "결과 없음";
  }
  if (key === "interest_board") {
    return `수집 대상 ${result.target_count || 0}개 · RAG 연결 ${result.rag_connected_count || 0}개`;
  }
  if (key === "rag_backfill") {
    return `갱신 문서 ${result.updated_count ?? 0}개 · 종목 ${(result.tickers || []).length || 0}개`;
  }
  if (key === "automation") {
    return `Dossier ${result.dossier_count || 0}개 · 실패 ${(result.failed || []).length}개`;
  }
  if (key === "daily_brief") {
    return `${result.date || "날짜 미확인"} · 최근 자료 ${result.recent_entry_count || 0}개`;
  }
  if (key === "interest_save") {
    return `관심종목 ${(result.tickers || []).length || 0}개 · 관심섹터 ${(result.sectors || []).length || 0}개`;
  }
  if (key === "status_refresh") {
    return "대시보드/저장 개수 갱신";
  }
  return "완료";
}

async function runResearchUpdateStep(steps, key, label, callback) {
  const startedAt = Date.now();
  const runningStep = {
    key,
    label,
    status: "running",
    summary: "실행 중입니다.",
    elapsed_ms: 0,
  };
  steps.push(runningStep);
  renderTodayResearchUpdateCards({
    status: "running",
    module: "today_research_update",
    steps,
    interest_board: lastInterestAutomationBoard,
  });
  try {
    const result = await callback();
    Object.assign(runningStep, {
      status: "success",
      summary: researchUpdateStepSummary(key, result),
      elapsed_ms: Date.now() - startedAt,
    });
    renderTodayResearchUpdateCards({
      status: "running",
      module: "today_research_update",
      steps,
      interest_board: lastInterestAutomationBoard,
    });
    return result;
  } catch (error) {
    Object.assign(runningStep, {
      status: "failed",
      summary: error?.message || String(error),
      elapsed_ms: Date.now() - startedAt,
    });
    renderTodayResearchUpdateCards({
      status: "running",
      module: "today_research_update",
      steps,
      interest_board: lastInterestAutomationBoard,
    });
    console.warn(`${label} 실패:`, error);
    return null;
  }
}

function withTimeout(promise, timeoutMs, timeoutMessage) {
  if (!timeoutMs) {
    return promise;
  }
  let timeoutId = null;
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  });
}

async function fetchPortfolioWithAbortTimeout(portfolioName, options = {}, timeoutMs = 45000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchPortfolio(token(), portfolioName, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function isAbortTimeoutError(error) {
  const message = String(error?.message || error || "").toLowerCase();
  return (
    error?.name === "AbortError" ||
    message.includes("abort") ||
    message.includes("aborted") ||
    message.includes("signal is aborted")
  );
}

function renderInterestAutomationBoardCards(board) {
  if (!elements.memoryList || !board) {
    return;
  }
  const tickerTargets = (board.ticker_targets || []).slice(0, 16);
  const sectorTargets = (board.sector_targets || []).slice(0, 8);
  const cardForTarget = (target) => {
    const label = target.company_name || target.name || target.ticker || "대상 미확인";
    const key = target.ticker || target.name || "MARKET";
    const query = (target.rag_query_examples || [])[0] || `${label} 최근 투자 논거`;
    const marketMatches = target.market_journal_matches || [];
    const marketHint = marketMatches[0]
      ? compactOutputText(marketMatches[0].summary || marketMatches[0].session_date, 150)
      : "연결된 시장일지 단서가 아직 없습니다.";
    return `
      <article class="memory-card verified">
        <span class="memory-card-topline">
          <strong>${escapeHtml(label)}</strong>
          <span class="memory-card-action">${escapeHtml(target.source === "portfolio_holding" ? "보유" : target.scope === "sector" ? "섹터" : "관심")}</span>
        </span>
        <span class="memory-card-meta">
          ${memoryBadge(key, "neutral")}
          ${memoryBadge(`RAG ${target.rag_document_count || 0}개`, "info")}
          ${memoryBadge(`저장 ${target.recent_document_count || 0}개`, "neutral")}
          ${target.duplicate_suspected_count ? memoryBadge(`중복 의심 ${target.duplicate_suspected_count}개`, "warning") : ""}
          ${marketMatches.length ? memoryBadge(`시장일지 ${marketMatches.length}개`, "match") : ""}
        </span>
        <small class="memory-card-summary">${escapeHtml(marketHint)}</small>
        <div class="memory-card-actions">
          <button data-interest-board-action="rag-search" data-query="${escapeHtml(query)}" data-key="${escapeHtml(key)}" type="button">저장 검색</button>
          <button data-interest-board-action="rag-synthesis" data-query="${escapeHtml(query)}" data-key="${escapeHtml(key)}" type="button">검색 합성</button>
          <button data-interest-board-action="market" data-query="${escapeHtml(marketHint)}" data-key="${escapeHtml(key)}" type="button">시장일지 단서</button>
        </div>
      </article>
    `;
  };
  elements.memoryList.innerHTML = `
    <div class="dashboard-card ok">
      <span>관심종목/섹터 자동 수집 보드</span>
      <strong>${escapeHtml(board.target_count || 0)}개 대상</strong>
      <p>보유종목·관심종목·관심섹터를 RAG 검색, 합성, 시장일지 연결로 바로 실행할 수 있습니다.</p>
    </div>
    <div class="memory-card-list interest-automation-card-list">
      ${tickerTargets.map(cardForTarget).join("")}
      ${sectorTargets.map((item) => cardForTarget({ ...item, scope: "sector" })).join("")}
    </div>
  `;
}

function renderTodayResearchUpdateCards(result) {
  if (!elements.memoryList || !result) {
    return;
  }
  const steps = result.steps || [];
  const board = result.interest_board || {};
  const daily = result.daily_brief || {};
  const automation = result.automation || {};
  const failedCount = steps.filter((step) => step.status === "failed").length;
  const runningCount = steps.filter((step) => step.status === "running").length;
  const stepCards = steps
    .map((step) => {
      const ok = step.status === "success";
      const running = step.status === "running";
      const elapsed = step.elapsed_ms ? `${Math.round(step.elapsed_ms / 100) / 10}초` : "시간 미확인";
      return `
        <article class="memory-card ${ok ? "verified" : running ? "" : "legacy"}">
          <span class="memory-card-topline">
            <strong>${escapeHtml(step.label || step.key || "실행 단계")}</strong>
            <span class="memory-card-action">${ok ? "완료" : running ? "진행 중" : "확인 필요"}</span>
          </span>
          <span class="memory-card-meta">
            ${memoryBadge(ok ? "성공" : running ? "처리 중" : "실패", ok ? "success" : running ? "info" : "danger")}
            ${memoryBadge(elapsed, "neutral")}
          </span>
          <small class="memory-card-summary">${escapeHtml(step.summary || "결과 요약 없음")}</small>
        </article>
      `;
    })
    .join("");

  const priorityTargets = (board.ticker_targets || [])
    .slice()
    .sort((a, b) => todayTargetPriorityScore(b) - todayTargetPriorityScore(a))
    .slice(0, 8)
    .map((target) => {
      const label = target.company_name || target.ticker || "대상 미확인";
      const key = target.ticker || label;
      const query = (target.rag_query_examples || [])[0] || `${label} 최근 투자 논거`;
      const marketMatches = target.market_journal_matches || [];
      const score = todayTargetPriorityScore(target);
      return `
        <article class="memory-card verified">
          <span class="memory-card-topline">
            <strong>${escapeHtml(label)}</strong>
            <span class="memory-card-action">우선 ${escapeHtml(score)}점</span>
          </span>
          <span class="memory-card-meta">
            ${memoryBadge(key, "neutral")}
            ${memoryBadge(target.source === "portfolio_holding" ? "보유종목" : "관심종목", "accent")}
            ${memoryBadge(`RAG ${target.rag_document_count || 0}개`, "info")}
            ${marketMatches.length ? memoryBadge(`시장일지 ${marketMatches.length}개`, "match") : ""}
          </span>
          <small class="memory-card-summary">${escapeHtml(compactOutputText(target.next_action || query, 180))}</small>
          <div class="memory-card-actions">
            <button data-interest-board-action="rag-search" data-query="${escapeHtml(query)}" data-key="${escapeHtml(key)}" type="button">저장 검색</button>
            <button data-interest-board-action="rag-synthesis" data-query="${escapeHtml(query)}" data-key="${escapeHtml(key)}" type="button">검색 합성</button>
            <button data-brief-action="dashboard" data-brief-ticker="${escapeHtml(key)}" type="button">대시보드</button>
          </div>
        </article>
      `;
    })
    .join("");

  const priorityReviews = (daily.portfolio_overview?.priority_reviews || [])
    .slice()
    .sort((a, b) => todayReviewPriorityScore(b) - todayReviewPriorityScore(a))
    .slice(0, 6)
    .map((item) => {
      const ticker = item.official_symbol || item.ticker || item.key || "";
      const label = item.company_name || item.name || ticker || "검토 대상";
      const score = todayReviewPriorityScore(item);
      return `
        <article class="memory-card ${ticker ? "verified" : ""}">
          <span class="memory-card-topline">
            <strong>${escapeHtml(label)}</strong>
            <span class="memory-card-action">우선 ${escapeHtml(score)}점</span>
          </span>
          <span class="memory-card-meta">
            ${memoryBadge(ticker || "시장/섹터", "neutral")}
            ${item.status ? memoryBadge(item.status, "info") : ""}
            ${item.confidence !== undefined && item.confidence !== null ? memoryBadge(`신뢰도 ${toPercent(item.confidence)}`, "accent") : ""}
          </span>
          <small class="memory-card-summary">${escapeHtml(compactOutputText(item.recommended_action || item.summary || "다음 확인 항목을 점검하세요.", 190))}</small>
          <div class="memory-card-actions">
            ${ticker ? `<button data-brief-action="dashboard" data-brief-ticker="${escapeHtml(ticker)}" type="button">대시보드</button>
            <button data-brief-action="dossier" data-brief-ticker="${escapeHtml(ticker)}" type="button">Dossier</button>` : ""}
            <button data-brief-action="memory" data-brief-ticker="${escapeHtml(ticker || "MARKET")}" type="button">저장 데이터</button>
          </div>
        </article>
      `;
    })
    .join("");

  elements.memoryList.innerHTML = `
    <div class="dashboard-card ${failedCount ? "warning" : runningCount ? "" : "ok"}">
      <span>오늘 리서치 업데이트</span>
      <strong>${runningCount ? "진행 중" : failedCount ? "부분 완료" : "정상 완료"}</strong>
      <p>수집 대상 ${escapeHtml(board.target_count || 0)}개 · RAG 갱신 ${escapeHtml(result.rag_backfill?.updated_count ?? 0)}개 · Dossier ${escapeHtml(automation.dossier_count || 0)}개 · 진행 ${escapeHtml(runningCount)}단계 · 실패 ${escapeHtml(failedCount)}단계</p>
    </div>
    <div class="memory-card-list">${stepCards}</div>
    <div class="dashboard-card ok">
      <span>바로 이어서 볼 대상</span>
      <strong>${escapeHtml((board.ticker_targets || []).length || 0)}개 후보</strong>
      <p>저장 검색 또는 검색 합성으로 강세·약세 논거를 바로 확인할 수 있습니다.</p>
    </div>
    <div class="memory-card-list">${priorityTargets || `<article class="memory-card legacy"><strong>표시할 수집 대상 없음</strong><small class="memory-card-summary">관심종목/섹터 또는 포트폴리오를 저장한 뒤 다시 실행하세요.</small></article>`}</div>
    <div class="dashboard-card">
      <span>일일 브리핑 우선 점검</span>
      <strong>${escapeHtml((daily.portfolio_overview?.priority_reviews || []).length || 0)}개</strong>
      <p>대시보드, Dossier, 저장 데이터로 이어지는 후속 검토 카드입니다.</p>
    </div>
    <div class="memory-card-list">${priorityReviews || `<article class="memory-card legacy"><strong>브리핑 카드 없음</strong><small class="memory-card-summary">일일 브리핑이 생성되지 않았거나 우선 점검 항목이 없습니다.</small></article>`}</div>
  `;
}

async function runTodayResearchUpdate() {
  syncApiBaseUrl();
  activateTab("memory", { keepOutput: true });
  startOutputLoading("오늘 리서치 업데이트 실행 중", [
    "관심종목/섹터 자동 수집 보드 생성",
    "RAG 색인 갱신",
    "보유/관심 종목 자동화 실행",
    "일일 브리핑 저장",
    "대시보드 연결 상태 갱신",
  ]);
  const steps = [];
  await runResearchUpdateStep(steps, "interest_save", "관심종목/섹터 저장", () =>
    saveCurrentInterestList({ quiet: true })
  );
  const interestBoard = await runResearchUpdateStep(steps, "interest_board", "관심종목/섹터 자동 수집 보드", () =>
    withTimeout(
      fetchInterestAutomationBoard(token(), true),
      20000,
      "관심종목/섹터 자동 수집 보드 생성이 지연되어 다음 단계로 넘어갑니다. 잠시 뒤 다시 보드만 실행해 확인하세요."
    )
  );
  lastInterestAutomationBoard = interestBoard || null;
  if (interestBoard) {
    renderInterestAutomationBoardCards(interestBoard);
  }
  const ragBackfill = await runResearchUpdateStep(steps, "rag_backfill", "RAG 색인 갱신", () =>
    withTimeout(
      backfillRagMemoryDocuments(token()),
      30000,
      "RAG 색인 갱신이 지연되어 다음 단계로 넘어갑니다. 백그라운드 처리 후 저장 데이터에서 다시 확인하세요."
    )
  );
  const automation = await runResearchUpdateStep(steps, "automation", "전체 리서치 자동화", () =>
    withTimeout(
      runResearchAutomation(token(), { limit: 30, saveResult: true }),
      60000,
      "전체 자동화가 오래 걸려 일단 다음 단계로 넘어갑니다. 일부 Dossier는 서버에서 계속 처리 중일 수 있습니다."
    )
  );
  const dailyBrief = await runResearchUpdateStep(steps, "daily_brief", "일일 브리핑 저장", () =>
    withTimeout(
      fetchDailyBriefing(token(), true),
      30000,
      "일일 브리핑 생성이 지연되어 결과를 기다리지 않고 다음 단계로 넘어갑니다."
    )
  );
  if (dailyBrief) {
    renderDailyBriefCards(dailyBrief);
  }
  await runResearchUpdateStep(steps, "status_refresh", "저장 보고서 수 새로고침", () =>
    withTimeout(refreshStatus(false), 12000, "상단 상태 갱신이 지연되어 건너뜁니다.")
  );
  const result = {
    status: steps.some((step) => step.status === "failed") ? "partial" : "success",
    module: "today_research_update",
    steps,
    interest_board: interestBoard,
    rag_backfill: ragBackfill,
    automation,
    daily_brief: dailyBrief,
  };
  saveStoredTodayResearchUpdate(result);
  setOutput(result);
  renderTodayResearchUpdateCards(result);
  if (lastDashboard) {
    renderDashboardCards(lastDashboard);
  }
  return result;
}

async function handleRagCardAction(button) {
  syncApiBaseUrl();
  const action = button.dataset.ragAction;
  const ticker = normalizeStorageKey(button.dataset.ragTicker || activeTicker);
  const title = button.dataset.ragTitle || "선택한 저장 자료";

  if (action === "open") {
    await openMemoryFile(ticker, button.dataset.ragFile);
    return;
  }

  if (action === "team") {
    await runTeamReportForTicker(ticker, `RAG 저장 자료 기반: ${title}`);
    return;
  }

  if (action === "dossier") {
    await openTickerWorkflow("dossier", ticker);
    return;
  }

  if (action === "market") {
    activateTab("marketClose", { keepOutput: true });
    const form = elements.marketCloseForm;
    const rawSummary = [title, button.dataset.ragSummary, button.dataset.ragUrl]
      .filter(Boolean)
      .join("\n\n");
    if (form?.elements?.rawSummary) {
      form.elements.rawSummary.value = rawSummary;
    }
    if (form?.elements?.sourceUrl && button.dataset.ragUrl) {
      form.elements.sourceUrl.value = button.dataset.ragUrl;
    }
    setOutput(
      "선택한 저장 자료를 시장일지 입력칸에 반영했습니다.\n\n시장 요약을 확인한 뒤 '시장 상황 평가 저장'을 누르면 누적 시장일지와 대시보드에 연결됩니다."
    );
  }
}

async function handleBriefCardAction(button) {
  const action = button.dataset.briefAction;
  const ticker = normalizeStorageKey(button.dataset.briefTicker || activeTicker);
  if (action === "dashboard") {
    await openTickerWorkflow("dashboard", ticker);
  } else if (action === "memory") {
    await openTickerWorkflow("memory", ticker);
  } else if (action === "dossier") {
    await openTickerWorkflow("dossier", ticker);
  } else if (action === "team") {
    await runTeamReportForTicker(ticker, "일일 브리핑 우선 검토 카드");
  }
}

function renderDailyBriefCards(result) {
  const overview = result?.portfolio_overview || result?.portfolioOverview || {};
  const rawItems = overview.priority_reviews || overview.items || result?.priority_reviews || [];
  const items = Array.isArray(rawItems) ? rawItems.slice(0, 12) : [];
  if (!items.length) {
    elements.memoryList.innerHTML = `
      <div class="dashboard-card warning">
        <span>일일 브리핑 카드</span>
        <strong>검토 카드 없음</strong>
        <p>포트폴리오와 관심종목/섹터를 저장하면 일일 브리핑에서 우선 검토 종목을 카드로 표시합니다.</p>
      </div>
    `;
    return;
  }

  const cards = items
    .map((item) => {
      const ticker = item.official_symbol || item.ticker || item.key || item.symbol || "";
      const label = item.company_name || item.name || item.label || ticker || "확인 필요";
      const summary = compactOutputText(
        item.summary || item.reason || item.latest_summary || item.action_reason || "최근 저장 데이터와 시장 상황을 확인하세요.",
        220
      );
      const badges = [
        memoryBadge(ticker || "GENERAL", "neutral"),
        item.priority ? memoryBadge(`우선순위 ${item.priority}`, "warning") : "",
        item.risk_level ? memoryBadge(`리스크 ${translateDashboardStatus(item.risk_level)}`, "danger") : "",
        item.status ? memoryBadge(translateDashboardStatus(item.status), "info") : "",
      ].join("");
      const canAnalyzeTicker = isTickerLikeMemoryKey(ticker);
      return `
        <article class="memory-file-button memory-card daily-brief-card ${canAnalyzeTicker ? "verified" : ""}">
          <span class="memory-card-topline">
            <strong>${escapeHtml(label)}</strong>
            <span class="memory-card-action">우선 검토</span>
          </span>
          <span class="memory-card-meta">${badges}</span>
          <small class="memory-card-summary">${escapeHtml(summary)}</small>
          <div class="memory-card-actions">
            ${
              canAnalyzeTicker
                ? `<button data-brief-action="dashboard" data-brief-ticker="${escapeHtml(ticker)}" type="button">대시보드</button>
                   <button data-brief-action="team" data-brief-ticker="${escapeHtml(ticker)}" type="button">팀 리포트</button>
                   <button data-brief-action="dossier" data-brief-ticker="${escapeHtml(ticker)}" type="button">Dossier</button>
                   <button data-brief-action="memory" data-brief-ticker="${escapeHtml(ticker)}" type="button">저장 데이터</button>`
                : `<button data-brief-action="memory" data-brief-ticker="${escapeHtml(ticker || "MARKET")}" type="button">관련 자료</button>`
            }
          </div>
        </article>
      `;
    })
    .join("");

  elements.memoryList.innerHTML = `
    <div class="dashboard-card ok">
      <span>일일 브리핑 액션 보드</span>
      <strong>${items.length}개 우선 검토</strong>
      <p>카드에서 대시보드, 팀 리포트, Dossier, 저장 데이터를 바로 실행할 수 있습니다.</p>
    </div>
    <div class="memory-card-list">${cards}</div>
  `;
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

document.addEventListener("input", (event) => {
  if (event.target.matches('input[name="ticker"]')) {
    const draftTicker = normalizeTickerDraft(event.target.value);
    if (event.target.value !== draftTicker) {
      event.target.value = draftTicker;
    }
    if (event.target.closest(".editor-list")) {
      return;
    }
    if (draftTicker) {
      syncTickerInputs(draftTicker, { source: event.target });
      scheduleDashboardSync(draftTicker);
    } else {
      syncTickerInputs("", { allowEmpty: true, source: event.target });
      window.clearTimeout(dashboardSyncTimer);
    }
  }
});

elements.statusButton.addEventListener("click", () => {
  startOutputLoading("상태 확인 실행 중", [
    "백엔드 연결 확인",
    "데이터 프로바이더 상태 확인",
    "저장 데이터 목록 확인",
  ]);
  refreshStatus().catch(setError);
});

elements.clearOutput.addEventListener("click", () => {
  setOutput("대기 중입니다.");
});

elements.exportResultExcel?.addEventListener("click", () => {
  downloadVisibleResultAsExcel().catch(setError);
});

attachButtonActionFeedback(elements.dashboardForm, {
  submit: "대시보드 조회를 시작했습니다.",
  "refresh-data": "최신 데이터 조회를 시작했습니다.",
  "run-team": "리포트 실행을 시작했습니다.",
  "diagnose-ticker": "티커 진단을 시작했습니다.",
  chart: "차트 분석 화면/작업을 열고 있습니다.",
  capture: "정보 입력 화면을 열고 있습니다.",
  memory: "저장 데이터 화면을 열고 있습니다.",
  "dart-refresh": "DART 공시 재점검을 시작했습니다.",
  "system-check": "시스템 점검을 시작했습니다.",
});

attachButtonActionFeedback(elements.captureForm, {
  submit: "정보 입력 저장을 시작했습니다.",
  captureUrlPreviewButton: "본문 미리보기를 시작했습니다.",
});

attachButtonActionFeedback(document.querySelector("#portfolio"), {
  submit: "포트폴리오 리스크 스캔을 시작했습니다.",
  portfolioLoadButton: "포트폴리오 가격 갱신 불러오기를 시작했습니다.",
  portfolioKiwoomSyncButton: "키움 국내 수량 변경 예정 목록을 확인합니다.",
  portfolioKiwoomApplyButton: "확인한 키움 국내 수량 변경을 적용합니다.",
  portfolioKiwoomCancelButton: "키움 국내 수량 적용 대기를 취소합니다.",
  portfolioSyncHistoryButton: "최근 계좌 동기화 이력을 조회합니다.",
  portfolioPerformanceButton: "기간 수익 비교를 시작했습니다.",
  portfolioSaveButton: "포트폴리오 저장을 시작했습니다.",
  portfolioQuickRiskButton: "선택 리스크 스캔을 시작했습니다.",
  portfolioConnectivityButton: "전체 연결 점검을 시작했습니다.",
  portfolioNpsFlowButton: "국민연금 수급 확인을 시작했습니다.",
  portfolioAnalysisStatusButton: "전체 분석 현황 점검을 시작했습니다.",
  portfolioTeamQueueButton: "기준 리포트 큐 정리를 시작했습니다.",
  portfolioRunTopTeamButton: "상위 1개 리포트 실행을 시작했습니다.",
  portfolioOptimizeButton: "포트폴리오 정책 최적화를 시작했습니다.",
  portfolioDeleteButton: "포트폴리오 삭제를 시작했습니다.",
  portfolioImportPickButton: "포트폴리오 파일 선택을 시작했습니다.",
  portfolioImportButton: "포트폴리오 파일 불러오기를 시작했습니다.",
  addHoldingButton: "보유 종목 행을 추가했습니다.",
  addCashButton: "현금 행을 추가했습니다.",
  recalculatePortfolioButton: "포트폴리오 금액 재계산을 시작했습니다.",
  portfolioSmartRefreshButton: "포트폴리오 스마트 표 새로고침을 시작했습니다.",
  portfolioConsensusScanButton: "목표가/컨센서스 스캔을 시작했습니다.",
});

attachButtonActionFeedback(document.querySelector("#interests"), {
  submit: "관심종목/섹터 저장을 시작했습니다.",
  interestsLoadButton: "관심종목/섹터 불러오기를 시작했습니다.",
  interestAutomationButton: "관심종목/섹터 자동 수집 보드를 생성합니다.",
  addInterestTickerButton: "관심종목 추가를 시작했습니다.",
  addInterestSectorButton: "관심섹터 추가를 시작했습니다.",
});

document.querySelectorAll("[data-workflow-action]").forEach((button) => {
  button.addEventListener("click", (event) => {
    if (!button.closest("#dashboardForm")) {
      const message = `${actionLabelFromButton(button)} 화면/작업을 열고 있습니다.`;
      if (!registerActionClick(button, message, event)) {
        return;
      }
    }
    handleWorkflowAction(button.dataset.workflowAction).catch(setError);
  });
});

elements.dashboardCards.addEventListener("click", (event) => {
  const todayActionButton = event.target.closest("[data-today-action]");
  if (todayActionButton) {
    const action = todayActionButton.dataset.todayAction;
    if (action === "open-update-board") {
      activateTab("memory", { keepOutput: true });
      if (lastTodayResearchUpdate) {
        renderTodayResearchUpdateCards({
          ...lastTodayResearchUpdate,
          interest_board: {
            target_count: lastTodayResearchUpdate.target_count,
            ticker_targets: lastTodayResearchUpdate.targets || [],
          },
          rag_backfill: {
            updated_count: lastTodayResearchUpdate.rag_updated_count,
          },
          automation: {
            dossier_count: lastTodayResearchUpdate.dossier_count,
            failed: [],
          },
          daily_brief: {
            next_actions: lastTodayResearchUpdate.next_actions || [],
            portfolio_overview: {
              priority_reviews: lastTodayResearchUpdate.priority_reviews || [],
            },
          },
        });
        setOutput(lastTodayResearchUpdate);
      } else {
        setOutput("오늘 리서치 업데이트 기록이 아직 없습니다.");
      }
      return;
    }
    if (action === "synthesize") {
      runInterestRagAction({
        query: todayActionButton.dataset.query || "",
        key: todayActionButton.dataset.key || "MARKET",
        mode: "synthesis",
      }).catch(setError);
      return;
    }
  }
  const memoryFileButton = event.target.closest("[data-dashboard-memory-file]");
  if (memoryFileButton) {
    const key = memoryFileButton.dataset.dashboardMemoryKey || activeTicker;
    const fileName = memoryFileButton.dataset.dashboardMemoryFile;
    activateTab("memory", { keepOutput: true });
    fetchResearchMemoryFiles(token(), key, memoryListFetchOptions())
      .then((memoryResponse) => {
        renderMemoryList(memoryResponse, key);
        return openMemoryFile(key, fileName);
      })
      .catch(setError);
    return;
  }
  const workflowTickerButton = event.target.closest("[data-dashboard-ticker-action]");
  if (workflowTickerButton) {
    openTickerWorkflow(
      workflowTickerButton.dataset.dashboardTickerAction,
      workflowTickerButton.dataset.dashboardTicker
    ).catch(setError);
    return;
  }
  const button = event.target.closest("[data-workflow-action]");
  if (button) {
    if (!button.closest("#dashboardForm")) {
      const message = `${actionLabelFromButton(button)} 화면/작업을 열고 있습니다.`;
      if (!registerActionClick(button, message, event)) {
        return;
      }
    }
    handleWorkflowAction(button.dataset.workflowAction).catch(setError);
  }
});

elements.memoryList.addEventListener("click", (event) => {
  const feedbackButton = event.target.closest(
    "[data-interest-board-action], [data-rag-action], [data-brief-action], [data-memory-file], [data-rag-file], [data-memory-archive], [data-memory-archive-legacy]"
  );
  if (feedbackButton) {
    const message = `${actionLabelFromButton(feedbackButton)} 작업을 시작했습니다.`;
    if (!registerActionClick(feedbackButton, message, event)) {
      return;
    }
  }

  const interestBoardActionButton = event.target.closest("[data-interest-board-action]");
  if (interestBoardActionButton) {
    const action = interestBoardActionButton.dataset.interestBoardAction;
    const query = interestBoardActionButton.dataset.query || "";
    const key = interestBoardActionButton.dataset.key || "MARKET";
    if (action === "market") {
      activateTab("marketClose", { keepOutput: true });
      if (elements.marketCloseForm?.elements?.rawSummary && query) {
        elements.marketCloseForm.elements.rawSummary.value = query;
      }
      setOutput("자동 수집 보드의 시장일지 단서를 시장일지 입력칸에 반영했습니다.");
      return;
    }
    runInterestRagAction({
      query,
      key,
      mode: action === "rag-synthesis" ? "synthesis" : "search",
    }).catch(setError);
    return;
  }
  const ragActionButton = event.target.closest("[data-rag-action]");
  if (ragActionButton) {
    handleRagCardAction(ragActionButton).catch(setError);
    return;
  }
  const briefActionButton = event.target.closest("[data-brief-action]");
  if (briefActionButton) {
    handleBriefCardAction(briefActionButton).catch(setError);
    return;
  }
  const archiveButton = event.target.closest("[data-memory-archive]");
  if (archiveButton) {
    handleMemoryArchiveAction(archiveButton).catch(setError);
    return;
  }
  const legacyArchiveButton = event.target.closest("[data-memory-archive-legacy]");
  if (legacyArchiveButton) {
    handleLegacyArchiveAction(legacyArchiveButton).catch(setError);
    return;
  }
  const button = event.target.closest("[data-memory-file]");
  if (button) {
    openMemoryFile(button.dataset.memoryKey || activeTicker, button.dataset.memoryFile).catch(setError);
    return;
  }
  const ragButton = event.target.closest("[data-rag-file]");
  if (ragButton && ragButton.dataset.ragFile) {
    openMemoryFile(ragButton.dataset.ragTicker || activeTicker, ragButton.dataset.ragFile).catch(setError);
  }
});

elements.tickerCacheList.addEventListener("click", async (event) => {
  const loadButton = event.target.closest("[data-cache-load]");
  const deleteButton = event.target.closest("[data-cache-delete]");

  if (loadButton) {
    const message = `${loadButton.dataset.cacheLoad} 대시보드 불러오기를 시작했습니다.`;
    if (!registerActionClick(loadButton, message, event)) {
      return;
    }
    activateTab("dashboard", { keepOutput: true });
    loadTickerDashboard(loadButton.dataset.cacheLoad).catch(setError);
    return;
  }

  if (deleteButton) {
    const message = `${deleteButton.dataset.cacheDelete} 캐시 삭제를 시작했습니다.`;
    if (!registerActionClick(deleteButton, message, event)) {
      return;
    }
    syncApiBaseUrl();
    const ticker = deleteButton.dataset.cacheDelete;
    startOutputLoading(`${ticker} 자동 인증 캐시 삭제 중`, [
      "캐시 항목 확인",
      "선택 항목 삭제",
      "캐시 목록 다시 렌더링",
    ]);
    try {
      const result = await deleteTickerRegistryCacheEntry(token(), ticker);
      renderTickerCache(result);
      setOutput(result || `${ticker} 캐시 삭제 결과를 확인하지 못했습니다.`);
    } catch (error) {
      setError(error);
    }
  }
});

elements.dashboardTickerSelect?.addEventListener("change", async (event) => {
  const select = event.currentTarget;
  const ticker = select.value;
  if (!ticker) {
    syncTickerInputs("", { allowEmpty: true });
    renderDashboardEmptyState();
    setOutput("대시보드에서 조회할 종목을 선택하거나 직접 입력하세요.");
    return;
  }
  const display = select.selectedOptions?.[0]?.dataset?.display || displayTickerForInput(ticker);
  if (elements.dashboardForm?.elements?.ticker) {
    elements.dashboardForm.elements.ticker.value = display;
  }
  syncTickerInputs(ticker, { skipDashboardInvalidation: true });
  startOutputLoading("대시보드 조회 중", ["티커 인증", "저장 데이터 연결", "대시보드 카드 구성"]);
  try {
    await loadTickerDashboard(ticker);
  } catch (error) {
    await setTickerAwareError(error, ticker);
  }
});

elements.dashboardTickerQuickList?.addEventListener("click", async (event) => {
  const toggleButton = event.target.closest("[data-dashboard-ticker-toggle]");
  if (toggleButton) {
    dashboardTickerGroupsExpanded = !dashboardTickerGroupsExpanded;
    renderDashboardTickerQuickList([
      ...portfolioDashboardCandidates(),
      ...interestDashboardCandidates(),
    ]);
    return;
  }
  const button = event.target.closest("[data-dashboard-quick-ticker]");
  if (!button) {
    return;
  }
  const ticker = button.dataset.dashboardQuickTicker || "";
  const display = button.dataset.dashboardQuickDisplay || ticker;
  if (!ticker) {
    return;
  }
  if (elements.dashboardForm?.elements?.ticker) {
    elements.dashboardForm.elements.ticker.value = display;
  }
  if (elements.dashboardTickerSelect) {
    elements.dashboardTickerSelect.value = ticker;
  }
  syncTickerInputs(ticker, { skipDashboardInvalidation: true });
  startOutputLoading(`${display} 대시보드 조회 중`, [
    "공식 티커 인증",
    "저장 데이터와 포트폴리오 연결",
    "후속 모듈 이동 준비",
  ]);
  try {
    await loadTickerDashboard(ticker);
  } catch (error) {
    await setTickerAwareError(error, ticker);
  }
});

elements.dashboardForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const data = formDataObject(form);
  const selectedDashboardTicker = elements.dashboardTickerSelect?.value || "";
  const selectedDisplay =
    elements.dashboardTickerSelect?.selectedOptions?.[0]?.dataset?.display || "";
  let requestedTicker = String(data.ticker || "").trim();
  if (selectedDashboardTicker && requestedTicker === selectedDisplay) {
    requestedTicker = selectedDashboardTicker;
  }
  if (!requestedTicker) {
    renderDashboardEmptyState();
    setOutput("**종목 선택 필요**\n\n포트폴리오/관심종목 후보에서 선택하거나 티커 또는 회사명을 직접 입력하세요.");
    form.elements.ticker?.focus();
    return;
  }
  startOutputLoading("티커 대시보드 조회 중", ["티커 인증", "저장 데이터 연결", "대시보드 카드 구성"]);
  try {
    await loadTickerDashboard(requestedTicker);
  } catch (error) {
    await setTickerAwareError(error, requestedTicker);
  }
});

elements.teamForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("팀 리포트 실행 중", [
    "종목 공식 인증",
    "시장/재무 데이터 자동 주입",
    "7개 스킬 종합 의견 생성",
    "보고서 저장 및 대시보드 갱신",
  ]);
  const data = formDataObject(form);
  try {
    const verification = await certifyTickerForWorkflow(data.ticker);
    const workflowTicker = verification.official_symbol;
    const result = await runCollaborativeTeamReport(token(), {
      ticker: workflowTicker,
      investmentPeriod: data.investmentPeriod,
      region: data.region,
      style: data.style,
      focusArea: data.focusArea,
      autoInjectData: data.autoInjectData === "on",
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("대시보드 카드 새로고침", () =>
      refreshDashboardCardsOnly(workflowTicker)
    );
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

elements.tradeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("스마트 매매 전략 생성 중", [
    "종목 공식 인증",
    "현재가와 포트폴리오 규모 확인",
    "진입/손절/목표가 계산",
    "저장 데이터 연결",
  ]);
  const data = formDataObject(form);
  try {
    const verification = await certifyTickerForWorkflow(data.ticker);
    const workflowTicker = verification.official_symbol;
    const selectedPortfolioMode = elements.tradePortfolioSelect?.value || "";
    const portfolio = selectedTradePortfolio();
    let portfolioSize = null;
    let portfolioSourceName = "";
    if (selectedPortfolioMode !== "__manual__" && portfolio) {
      const portfolioValue = Number(portfolio?.portfolio_value);
      portfolioSize = Number.isFinite(portfolioValue) && portfolioValue > 0 ? portfolioValue : null;
      portfolioSourceName = portfolioSize ? (portfolio?.portfolio_name || "저장 포트폴리오") : "";
    } else {
      portfolioSize = data.portfolioSize ? Number(data.portfolioSize) : null;
      portfolioSourceName = portfolioSize ? "직접 입력" : "";
    }
    let currentPrice = Number(data.currentPrice);
    if (!Number.isFinite(currentPrice) || currentPrice <= 0) {
      const latest = await fetchAndApplyLatestPrice(workflowTicker);
      currentPrice = Number(latest.lastPrice);
    }
    if (!Number.isFinite(currentPrice) || currentPrice <= 0) {
      throw new Error(
        `${workflowTicker} 현재가를 확인하지 못했습니다. KIS 상태를 확인하거나 현재가를 직접 입력하세요.`
      );
    }
    const result = await runSmartTradeSetup(token(), {
      ticker: workflowTicker,
      currentPrice,
      style: data.style,
      riskTolerance: data.riskTolerance,
      portfolioSize,
      riskPerTradePct: Number(data.riskPerTradePct) / 100,
      marketStructure: data.marketStructure || null,
      autoInjectData: data.autoInjectData === "on",
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("대시보드 카드 새로고침", () =>
      refreshDashboardCardsOnly(workflowTicker)
    );
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

elements.tradePortfolioSelect?.addEventListener("change", (event) => {
  const input = elements.tradeForm?.elements?.portfolioSize;
  if (!input) {
    return;
  }
  if (event.target.value === "__manual__") {
    input.value = "";
    input.placeholder = "직접 입력";
    input.title = "직접 입력 모드입니다.";
    input.focus();
    setOutput("포트폴리오 규모를 직접 입력하도록 전환했습니다.");
    return;
  }
  input.value = "";
  input.placeholder = "선택 포트폴리오 총액 자동 사용";
  input.title = "";
  syncTradePortfolioSizeFromActivePortfolio();
  setOutput("저장 포트폴리오 규모 자동 사용으로 전환했습니다.");
});

elements.portfolioSelect?.addEventListener("change", async (event) => {
  const selectedPortfolio = findSavedPortfolioByName(event.target.value);
  if (!selectedPortfolio) {
    return;
  }
  fillPortfolioForm(selectedPortfolio);
  updatePortfolioLoadedAt(selectedPortfolio, "선택 후 불러온");
  await refreshPortfolioSmartTable({ silent: true });
  setOutput(
    [
      "# 포트폴리오 선택 완료",
      "",
      `- 포트폴리오: ${selectedPortfolio.portfolio_name}`,
      `- 보유 종목: ${selectedPortfolio.holding_count ?? selectedPortfolio.holdings?.length ?? 0}개`,
      `- 총액: ${formatMoney(selectedPortfolio.portfolio_value, "KRW", "n/a")}`,
      "- 최신 가격까지 다시 확인하려면 `포트폴리오 가격 갱신 불러오기`를 누르세요.",
    ].join("\n")
  );
});

elements.chartForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const formData = new FormData(elements.chartForm);
  try {
    await runChartAnalysisForTicker(formData.get("ticker"), {
      saveResult: formData.get("saveResult") === "on",
    });
  } catch (error) {
    await setTickerAwareError(error, formData.get("ticker"));
  }
});

elements.memoryList.addEventListener("change", (event) => {
  if (event.target.matches("[data-rag-filter-type]")) {
    ragTypeFilter = event.target.value || "all";
    if (lastRagSearchResult) {
      renderRagMemoryList(lastRagSearchResult);
      setOutput("저장 데이터 유형 필터를 적용했습니다.");
    }
    return;
  }
  if (event.target.matches("[data-rag-filter-ticker]")) {
    ragTickerFilter = event.target.value || "all";
    if (lastRagSearchResult) {
      renderRagMemoryList(lastRagSearchResult);
      setOutput("저장 데이터 종목 필터를 적용했습니다.");
    }
    return;
  }
  if (event.target.matches("[data-rag-filter-quality]")) {
    ragQualityFilter = event.target.value || "all";
    if (lastRagSearchResult) {
      renderRagMemoryList(lastRagSearchResult);
      setOutput("저장 데이터 품질 필터를 적용했습니다.");
    }
    return;
  }
  if (event.target.matches("[data-rag-sort]")) {
    ragSortMode = event.target.value || "relevance_desc";
    if (lastRagSearchResult) {
      renderRagMemoryList(lastRagSearchResult);
      setOutput("저장 데이터 정렬 기준을 적용했습니다.");
    }
  }
});

elements.earningsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("실적 발표 반응 분석 중", [
    "종목 공식 인증",
    "최근 발표 실적과 다음 예정일 확인",
    "주가 반응과 가이던스 변화 평가",
    "저장 데이터 연결",
  ]);
  const data = formDataObject(form);
  try {
    const verification = await certifyTickerForWorkflow(data.ticker);
    const workflowTicker = verification.official_symbol;
    const keyNumbers = data.keyNumbers ? JSON.parse(data.keyNumbers) : {};
    const result = await runEarningsReactionAnalyzer(token(), {
      ticker: workflowTicker,
      quarter: data.quarter,
      earningsReportDate: data.earningsReportDate || null,
      priceReaction: data.priceReaction || "",
      previousEarningsDate: data.previousEarningsDate || null,
      previousEarningsSummary: data.previousEarningsSummary || null,
      nextEarningsDate: data.nextEarningsDate || null,
      nextEarningsGuidance: data.nextEarningsGuidance || null,
      epsReported: numberOrNull(data.epsReported),
      epsExpected: numberOrNull(data.epsExpected),
      revenueReported: numberOrNull(data.revenueReported),
      revenueExpected: numberOrNull(data.revenueExpected),
      guidanceChange: data.guidanceChange,
      managementTone: data.managementTone || null,
      marketContext: data.marketContext || null,
      keyNumbers,
      autoInjectData: data.autoInjectData === "on",
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("대시보드 카드 새로고침", () =>
      refreshDashboardCardsOnly(workflowTicker)
    );
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

elements.macroForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("매크로 분석 실행 중", [
    "지역과 분석 기간 확인",
    "금리·환율·정책·수급 변수 정리",
    "저장 데이터와 시장 메모 연결",
    "유리한 섹터와 리스크 체크포인트 계산",
  ]);
  const data = formDataObject(form);
  try {
    const result = await runSectorOpportunityFinder(token(), {
      macroEnvironment: data.macroEnvironment,
      period: data.period,
      region: data.region,
      style: data.style,
      focusTheme: data.focusTheme || "매크로 전체",
      autoInjectData: data.autoInjectData === "on",
      saveResult: !isClickSmokeMode(),
    });
    setOutput({
      ...result,
      display_mode: "macro_analysis",
    });
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

async function runKcifReportsWatch({ refresh = false } = {}) {
  syncApiBaseUrl();
  startOutputLoading(refresh ? "KCIF 보고서 새로 확인 중" : "KCIF 보고서 Watch 조회 중", [
    "KCIF 공개 목록 메타데이터 확인",
    "본문/PDF 자동 저장 제외",
    "보유종목·관심종목·관심섹터 키워드 매칭",
    "매크로 테마와 시장일지 후보 정리",
  ]);
  try {
    const result = refresh
      ? await refreshKcifReportsWatch(token(), { limit: 30, saveResult: !isClickSmokeMode() })
      : await fetchKcifReportsWatch(token(), {
          limit: 30,
          refresh: false,
          saveResult: !isClickSmokeMode(),
        });
    setOutput(result);
    await runSecondaryRefresh("자동화 상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
}

elements.kcifReportsWatchButton?.addEventListener("click", () => {
  runKcifReportsWatch({ refresh: false });
});

elements.kcifReportsRefreshButton?.addEventListener("click", () => {
  runKcifReportsWatch({ refresh: true });
});

async function runRegionalBusinessSourcesWatch({ refresh = false } = {}) {
  syncApiBaseUrl();
  startOutputLoading(refresh ? "EMERiCs/CSF/KIEP 새로 확인 중" : "EMERiCs/CSF/KIEP Watch 조회 중", [
    "EMERiCs 신흥지역 비즈니스 정보 확인",
    "CSF 중국 비즈니스 정보 확인",
    "KIEP 대외경제정책연구원 보고서 확인",
    "원문 본문 자동 저장 제외",
    "보유종목·관심종목·관심섹터 키워드 매칭",
    "매크로/시장일지 후보 정리",
  ]);
  try {
    const result = refresh
      ? await refreshRegionalBusinessSourcesWatch(token(), {
          limit: 40,
          saveResult: !isClickSmokeMode(),
        })
      : await fetchRegionalBusinessSourcesWatch(token(), {
          limit: 40,
          refresh: false,
          saveResult: !isClickSmokeMode(),
        });
    setOutput(result);
    await runSecondaryRefresh("자동화 상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
}

elements.regionalBusinessSourcesWatchButton?.addEventListener("click", () => {
  runRegionalBusinessSourcesWatch({ refresh: false });
});

elements.regionalBusinessSourcesRefreshButton?.addEventListener("click", () => {
  runRegionalBusinessSourcesWatch({ refresh: true });
});

elements.sectorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("산업군 동향 리포트 생성 중", [
    "매크로 입력과 저장 데이터 연결",
    "보유종목·관심종목을 섹터별로 분류",
    "섹터 흐름과 주도주 점수 계산",
    "투자 솔루션과 체크포인트 정리",
  ]);
  const data = formDataObject(form);
  try {
    const result = await runSectorOpportunityFinder(token(), {
      macroEnvironment: data.macroEnvironment,
      period: data.period,
      region: data.region,
      style: data.style,
      focusTheme: data.focusTheme,
      autoInjectData: data.autoInjectData === "on",
      saveResult: !isClickSmokeMode(),
    });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

elements.compounderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("장기 복리 성장주 발굴 중", [
    "지역/섹터/시가총액 조건 확인",
    "성장성·마진·FCF·경쟁우위 스코어링",
    "후보 기업 숏리스트 정리",
    "저장 데이터 연결",
  ]);
  const data = formDataObject(form);
  try {
    if (isClickSmokeMode()) {
      const regionLabel = String(data.region || "").toUpperCase().startsWith("KR") ? "한국" : "미국";
      setOutput([
        "## 장기 복리 성장주 발굴",
        "",
        `지역: ${regionLabel}`,
        "섹터: 전체",
        "스타일: 퀄리티 성장",
        "",
        "## 요약",
        "",
        "저장 데이터 결합은 클릭 검증에서 생략하고, 화면 계약과 회사명 중심 표시를 확인했습니다.",
        "",
        "## 후보 기업",
        "",
        "1. SK하이닉스 (78/100) - HBM 경쟁력과 AI 메모리 수요가 장기 성장 논거입니다.",
        "2. 삼성바이오로직스 (75/100) - CDMO 생산 역량과 장기 계약 구조가 안정적입니다.",
        "",
        "## 핵심 지표",
        "",
        "- SK하이닉스: 매출 성장률 26%, 매출총이익률 45%, FCF 마진 10%, 경쟁 우위 82/100",
        "- 삼성바이오로직스: 매출 성장률 18%, 매출총이익률 41%, FCF 마진 12%, 경쟁 우위 79/100",
      ].join("\n"));
      return;
    }
    const result = await runLongTermCompounderFinder(token(), {
      screeningCriteria: data.screeningCriteria,
      minMarketCap: numberOrNull(data.minMarketCap),
      maxMarketCap: numberOrNull(data.maxMarketCap),
      sector: data.sector,
      region: data.region,
      style: data.style,
      autoInjectData: data.autoInjectData === "on",
      saveResult: !isClickSmokeMode(),
    });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    await setTickerAwareError(error, data.ticker);
  }
});

elements.compounderForm.elements.region?.addEventListener("change", (event) => {
  const minMarketCapInput = elements.compounderForm.elements.minMarketCap;
  if (!minMarketCapInput) {
    return;
  }
  const region = String(event.target.value || "").toUpperCase();
  minMarketCapInput.value = region.startsWith("KR") ? "3000" : "5000";
});

async function previewFormSourceUrl(form, label) {
  syncApiBaseUrl();
  const sourceUrl = String(form?.elements?.sourceUrl?.value || "").trim();
  if (!sourceUrl) {
    setOutput(`**웹사이트 주소 입력 필요**\n\n${label}에 미리보기할 URL을 입력하세요.`);
    return;
  }
  startOutputLoading("웹사이트 본문 미리보기 중", [
    "웹사이트 접속",
    "본문 후보 추출",
    "메뉴·광고·추천기사 제거",
    "해외 문서는 한국어 분석 메모로 변환",
    "저장 없이 미리보기 표시",
  ]);
  try {
    const result = await previewSourceUrl(token(), sourceUrl);
    setOutput(result, { skipCompletionBanner: true });
  } catch (error) {
    setError(error);
  }
}

elements.captureUrlPreviewButton?.addEventListener("click", () =>
  previewFormSourceUrl(elements.captureForm, "정보 입력")
);

elements.captureForm
  ?.querySelector('input[name="researchFile"]')
  ?.addEventListener("change", (event) => {
    updateCaptureFileStatus(event.currentTarget.files?.[0] || null);
  });

elements.newsUrlPreviewButton?.addEventListener("click", () =>
  previewFormSourceUrl(elements.newsForm, "뉴스 인박스")
);

elements.captureForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const data = formDataObject(form);
  const sourceUrl = String(data.sourceUrl || "").trim();
  const destination = String(data.destination || "auto").trim();
  const fileInput = elements.captureForm.querySelector('input[name="researchFile"]');
  const file = fileInput?.files?.[0] || null;
  setCaptureFormProcessing(true, file);
  startOutputLoading("자료 자동 분류 및 저장 중", [
    "입력 텍스트와 첨부 파일 읽기",
    "웹사이트 주소가 있으면 본문 추출",
    file && isImageFile(file) ? "이미지 OCR 분석 대기" : "첨부 파일 처리 상태 확인",
    "티커, 거시, 섹터, 시장, 정책, 금리, 수급 자료 여부 분류",
    "출처 유형과 신뢰도 자동 추정",
    "기존 투자 논거와 새 메모 비교",
    "리서치 메모리에 저장하고 결과 정리",
  ]);
  try {
    const filePayload = await readResearchFilePayload(file);
    if (file) {
      updateCaptureFileStatus(
        file,
        "processing",
        isImageFile(file)
          ? "이미지 OCR 분석 중... 서버에서 텍스트 추출을 시도하고 있습니다."
          : isPdfFile(file)
            ? "PDF 본문 추출 중... 서버에서 텍스트 레이어를 확인하고 있습니다."
            : "첨부 파일 저장 및 분석 중..."
      );
    }
    const fileContext = file
      ? [
          "[첨부 파일]",
          `파일명: ${filePayload.fileName}`,
          `MIME: ${filePayload.fileMimeType}`,
          `크기: ${filePayload.fileSize} bytes`,
          `처리: ${filePayload.extractionNote}`,
        ].join("\n")
      : "";
    const rawContent = [data.rawContent, filePayload.extractedText, fileContext]
      .filter((value) => String(value || "").trim())
      .join("\n\n--- 첨부 파일 내용 ---\n\n");
    if (!rawContent.trim() && !filePayload.fileContentBase64 && !sourceUrl) {
      throw new Error("저장할 텍스트, 웹사이트 주소를 입력하거나 파일을 선택하세요.");
    }
    if (destination === "news") {
      const result = await ingestNewsInbox(token(), {
        rawContent,
        sourceUrl,
        confidence: 0.78,
      });
      setOutput(result);
      resetFormSafely(form);
      resetCaptureInputScreen();
      activateTab("news", { keepOutput: true });
      const inbox = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
      renderNewsInboxCards(inbox);
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
      return;
    }
    if (destination === "market") {
      const result = await saveMarketCloseReview(token(), {
        market: "GLOBAL",
        sessionDate: null,
        rawSummary: rawContent,
        sourceUrl,
        fileName: filePayload.fileName,
        fileMimeType: filePayload.fileMimeType,
        fileSize: filePayload.fileSize,
        fileContentBase64: filePayload.fileContentBase64,
        saveResult: true,
      });
      setOutput(result);
      resetFormSafely(form);
      resetCaptureInputScreen();
      activateTab("marketClose", { keepOutput: true });
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
      return;
    }
    const result = await autoCaptureResearchItem(token(), {
      rawContent,
      sourceUrl,
      fileName: filePayload.fileName,
      fileMimeType: filePayload.fileMimeType,
      fileSize: filePayload.fileSize,
      fileContentBase64: filePayload.fileContentBase64,
      runThesisImpact: data.runThesisImpact === "on",
      saveResult: true,
    });
    setOutput(result);
    resetFormSafely(form);
    resetCaptureInputScreen();
    const capturedTicker = result?.captured_item?.ticker;
    const nonTickerScopes = ["INBOX", "MACRO", "SECTOR", "MARKET", "POLICY", "RATES", "FLOWS"];
    if (capturedTicker && !nonTickerScopes.includes(capturedTicker)) {
      syncTickerInputs(capturedTicker);
      await runSecondaryRefresh("대시보드 카드 새로고침", () =>
        refreshDashboardCardsOnly(capturedTicker)
      );
    } else {
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    }
  } catch (error) {
    setError(error);
  } finally {
    setCaptureFormProcessing(false);
  }
});

elements.newsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }
  startOutputLoading("뉴스 인박스 저장 중", [
    "URL 제목과 메타데이터 확인",
    "뉴스 범위와 태그 자동 분류",
    "중복 뉴스 확인",
    "본문 품질 점검",
    "저작권 안전 모드로 뉴스 인박스 저장",
  ]);
  try {
    const data = formDataObject(form);
    const rawContent = String(data.rawContent || "").trim();
    const sourceUrl = String(data.sourceUrl || "").trim();
    if (!rawContent && !sourceUrl) {
      throw new Error("뉴스 본문을 붙여넣거나 뉴스 URL을 입력하세요.");
    }
    const result = await ingestNewsInbox(token(), {
      rawContent,
      sourceUrl,
    });
    setOutput(result);
    resetFormSafely(form);
    resetNewsInputScreen();
    const inbox = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
    renderNewsInboxCards(inbox);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});

elements.newsInboxButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("뉴스 인박스 조회 중", ["뉴스 저장소 조회", "미승격 자료 정리", "품질 경고 확인"]);
  try {
    const result = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
    renderNewsInboxCards(result);
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.newsInboxFilter?.addEventListener("change", () => {
  showActionAccepted("뉴스 인박스 필터를 적용합니다.");
  elements.newsInboxButton?.click();
});

elements.newsPromoteLatestButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("최근 뉴스 승격 중", ["뉴스 인박스 조회", "미승격 자료 선택", "저장 데이터/RAG 메모리 승격"]);
  try {
    const inbox = await fetchNewsInbox(token(), 20, "unpromoted");
    const item = (inbox?.items || []).find((entry) => !entry.promoted);
    if (!item?.id) {
      setOutput("**승격할 뉴스가 없습니다.**\n\n뉴스 인박스에 미승격 자료가 없습니다.");
      return;
    }
    const result = await promoteNewsInboxItem(token(), item.id);
    setOutput(result);
    const updatedInbox = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
    renderNewsInboxCards(updatedInbox);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.newsInboxList?.addEventListener("click", async (event) => {
  const actionButton = event.target.closest("[data-news-action]");
  if (!actionButton) {
    return;
  }
  const card = actionButton.closest("[data-news-id]");
  const itemId = card?.dataset.newsId;
  const action = actionButton.dataset.newsAction;
  if (!itemId || !action) {
    return;
  }
  syncApiBaseUrl();
  const labels = {
    promote: "뉴스 승격 중",
    market_journal: "시장일지 후보 지정 중",
    hold: "뉴스 보류 처리 중",
    delete: "뉴스 삭제 중",
  };
  startOutputLoading(labels[action] || "뉴스 처리 중", [
    "뉴스 인박스 항목 확인",
    "처리 상태 저장",
    "대시보드 상태 갱신",
  ]);
  try {
    const result =
      action === "promote"
        ? await promoteNewsInboxItem(token(), itemId)
        : await updateNewsInboxItem(token(), itemId, action);
    setOutput(result);
    const inbox = await fetchNewsInbox(token(), 30, currentNewsInboxFilter());
    renderNewsInboxCards(inbox);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.llmPromptForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const prompt = ensureLlmPromptPreview();
  setOutput(
    [
      "**LLM 수동 연동 프롬프트를 생성했습니다.**",
      "",
      "1. `프롬프트 복사`를 눌러 ChatGPT 또는 Gemini 웹 채팅창에 붙여넣으세요.",
      "2. 생성된 응답을 이 탭의 `LLM 응답 붙여넣기`에 다시 넣으세요.",
      "3. `응답 저장 및 분석`을 누르면 기존 정보입력 파이프라인으로 자동 분류/저장됩니다.",
      "",
      `프롬프트 길이: ${prompt.length.toLocaleString("ko-KR")}자`,
    ].join("\n")
  );
});

elements.copyLlmPromptButton?.addEventListener("click", async (event) => {
  if (
    !registerActionClick(
      event.currentTarget,
      "LLM 프롬프트 복사를 시작했습니다.",
      event
    )
  ) {
    return;
  }
  try {
    const prompt = elements.llmPromptOutput?.value.trim() || ensureLlmPromptPreview();
    await copyTextToClipboard(prompt);
    showActionFeedback("LLM 프롬프트를 복사했습니다. ChatGPT 또는 Gemini에 붙여넣으세요.");
    showOutputStatus("복사 완료", "complete", 2400);
    setOutput("**프롬프트를 복사했습니다.**\n\nChatGPT 또는 Gemini 웹 채팅창에 붙여넣고, 생성된 응답을 다시 이 콘솔에 붙여넣으세요.");
  } catch (error) {
    elements.llmPromptOutput?.focus();
    elements.llmPromptOutput?.select();
    showActionFeedback("브라우저 복사 권한이 제한되어 프롬프트를 선택했습니다. Ctrl+C로 복사하세요.");
    showOutputStatus("직접 복사 필요", "pending", 3600);
    renderPlainOutput(
      [
        "**직접 복사 필요**",
        "",
        error?.message || "브라우저 클립보드 권한이 제한되어 자동 복사하지 못했습니다.",
        "",
        "생성된 프롬프트 영역을 선택해 두었습니다. `Ctrl+C`로 복사한 뒤 ChatGPT 또는 Gemini에 붙여넣으세요.",
      ].join("\n")
    );
  }
});

elements.llmStorageStatusButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("LLM 저장/RAG 상태 확인 중", [
    "최근 수동 LLM 응답 저장 파일 확인",
    "원 프롬프트와 LLM 응답 본문 보존 여부 점검",
    "RAG 색인 연결 상태 대조",
  ]);
  try {
    const result = await fetchLlmBridgeStorageStatus(token(), 10);
    setOutput(result || "LLM 저장/RAG 상태를 확인하지 못했습니다.");
  } catch (error) {
    setError(error);
  }
});

elements.llmResultForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  startOutputLoading("LLM 응답 저장 및 분석 중", [
    "수동 LLM 응답 구조화",
    "대상 티커 또는 시장/섹터 범위 재분류",
    "신뢰도와 출처 유형 추정",
    "기존 투자 논거 영향 비교",
    "저장 데이터와 RAG 메모리에 연결",
  ]);
  try {
    const resultData = formDataObject(form);
    const promptData = elements.llmPromptForm ? formDataObject(elements.llmPromptForm) : {};
    const llmResult = String(resultData.llmResult || "").trim();
    if (!llmResult) {
      throw new Error("저장할 LLM 응답을 붙여넣으세요.");
    }
    const prompt = elements.llmPromptOutput?.value.trim() || buildManualLlmPrompt(promptData);
    const rawContent = [
      "[수동 LLM 분석 응답]",
      `대상: ${promptData.target || "미입력"}`,
      `사용 LLM: ${promptData.provider || "미입력"}`,
      `작업 유형: ${promptData.taskType || "미입력"}`,
      `응답 형식: ${promptData.outputStyle || "미입력"}`,
      "",
      "[LLM 응답]",
      llmResult,
      "",
      "[원 프롬프트]",
      prompt,
    ].join("\n");
    const result = await autoCaptureResearchItem(token(), {
      rawContent,
      runThesisImpact: resultData.runThesisImpact === "on",
      saveResult: true,
    });
    setOutput(result);
    resetLlmBridgeInputScreen();
    const capturedTicker = result?.captured_item?.ticker;
    const nonTickerScopes = ["INBOX", "MACRO", "SECTOR", "MARKET", "POLICY", "RATES", "FLOWS"];
    if (capturedTicker && !nonTickerScopes.includes(capturedTicker)) {
      syncTickerInputs(capturedTicker);
      await runSecondaryRefresh("대시보드 카드 새로고침", () =>
        refreshDashboardCardsOnly(capturedTicker)
      );
    } else {
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    }
  } catch (error) {
    setError(error);
  } finally {
    submitButton.disabled = false;
  }
});

elements.earningsFilingNoteForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }
  startOutputLoading("어닝 콜/공시 기반 노트 초안 작성 중", [
    "종목 공식 인증",
    "어닝 콜과 공시 자료 핵심 문장 추출",
    "모델 업데이트 항목 분류",
    "투자 노트 초안과 미확인 질문 생성",
    "저장 데이터에 연결",
  ]);
  try {
    const data = formDataObject(form);
    const fileInput = form.querySelector('input[name="earningsFile"]');
    const filePayload = await readResearchFilePayload(fileInput?.files?.[0] || null);
    const result = await runEarningsFilingNoteWorkflow(token(), {
      ticker: data.ticker,
      earningsCall: data.earningsCall,
      filingMaterial: data.filingMaterial,
      modelNotes: data.modelNotes,
      fileName: filePayload.fileName,
      fileMimeType: filePayload.fileMimeType,
      fileSize: filePayload.fileSize,
      fileContentBase64: filePayload.fileContentBase64,
      autoInjectData: data.autoInjectData === "on",
      saveResult: true,
    });
    setOutput(result);
    if (result?.ticker) {
      syncTickerInputs(result.ticker);
      await runSecondaryRefresh("대시보드 카드 새로고침", () =>
        refreshDashboardCardsOnly(result.ticker)
      );
    } else {
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    }
    resetWorkflowDraftForm(form, "earningsFile");
  } catch (error) {
    setError(error);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});

elements.gpLpStagingForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }
  startOutputLoading("GP 패키지/LP 보고 스테이징 중", [
    "GP 패키지 요약",
    "밸류에이션 템플릿 입력 항목 정리",
    "LP 보고 초안 구성",
    "리스크 플래그와 검수 체크리스트 생성",
    "저장 데이터에 스테이징 파일 적재",
  ]);
  try {
    const data = formDataObject(form);
    const fileInput = form.querySelector('input[name="gpPackageFile"]');
    const filePayload = await readResearchFilePayload(fileInput?.files?.[0] || null);
    const result = await runGpLpStagingWorkflow(token(), {
      fundName: data.fundName,
      gpPackage: data.gpPackage,
      valuationMethod: data.valuationMethod,
      baseCase: data.baseCase,
      fileName: filePayload.fileName,
      fileMimeType: filePayload.fileMimeType,
      fileSize: filePayload.fileSize,
      fileContentBase64: filePayload.fileContentBase64,
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    resetWorkflowDraftForm(form, "gpPackageFile");
  } catch (error) {
    setError(error);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});

elements.marketCloseUrlPreviewButton?.addEventListener("click", () =>
  previewFormSourceUrl(elements.marketCloseForm, "시장일지")
);

elements.marketCloseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }
  startOutputLoading("폐장 후 시장 상황 평가 중", [
    "입력 텍스트와 첨부 파일 읽기",
    "웹사이트 주소가 있으면 본문만 추출",
    "시장 요약 구조화",
    "심리·리스크·장세 판정",
    "누적 시장 일지와 비교",
    "투자 활용 액션 저장",
  ]);
  try {
    const data = formDataObject(form);
    const sourceUrl = String(data.sourceUrl || "").trim();
    const fileInput = elements.marketCloseForm.querySelector('input[name="marketCloseFile"]');
    const file = fileInput?.files?.[0] || null;
    const filePayload = await readResearchFilePayload(file);
    const rawSummary = [data.rawSummary, filePayload.extractedText]
      .filter((value) => String(value || "").trim())
      .join("\n\n--- 첨부 파일 본문 ---\n\n");
    if (!rawSummary.trim() && !filePayload.fileContentBase64 && !sourceUrl) {
      throw new Error("시장 요약, 웹사이트 주소를 입력하거나 파일을 선택하세요.");
    }
    const result = await saveMarketCloseReview(token(), {
      market: data.market,
      sessionDate: data.sessionDate || null,
      rawSummary,
      sourceUrl,
      fileName: filePayload.fileName,
      fileMimeType: filePayload.fileMimeType,
      fileSize: filePayload.fileSize,
      fileContentBase64: filePayload.fileContentBase64,
      saveResult: true,
    });
    setOutput(result);
    resetFormSafely(form);
    resetMarketCloseInputScreen();
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
});

elements.marketCloseHistoryButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  const data = formDataObject(elements.marketCloseForm);
  startOutputLoading("누적 시장 일지 조회 중", ["저장소 조회", "최근 기록 정리"]);
  try {
    const result = await fetchMarketCloseJournal(token(), data.market || "ALL");
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.customsTradeSnapshotButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("관세청 수출입 동향 조회 중", [
    "1일·11일·21일 발표 주기 확인",
    "전략 품목 수출입 실적 조회",
    "빈 응답 저장 차단 기준 확인",
    "재고 부담 가능성 추정",
    "섹터/포트폴리오 활용 메모 저장",
    "RAG 검색 데이터 연결",
  ]);
  try {
    const result = await fetchCustomsTradeSnapshot(token(), { saveResult: true });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  startOutputLoading("내 포트폴리오 리스크 스캔 중", [
    "보유 종목 입력값 검증",
    "집중도 계산",
    "리스크 경고 저장",
  ]);
  try {
    const data = currentPortfolioPayload();
    const result = await runPortfolioRiskScan(token(), {
      portfolioName: data.portfolioName,
      holdings: data.holdings,
      portfolioValue: data.portfolioValue,
      maxSinglePositionWeight: data.maxSinglePositionWeight,
      maxSectorWeight: data.maxSectorWeight,
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioQuickRiskButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setError(new Error("리스크 스캔할 저장 포트폴리오를 선택하세요."));
    return;
  }
  startOutputLoading("선택 포트폴리오 리스크 스캔 중", [
    "저장 포트폴리오 불러오기",
    "보유 종목과 평가금액 확인",
    "집중도와 테마 노출 계산",
    "리스크 경고 저장",
  ]);
  try {
    const response = await fetchPortfolio(token(), portfolioName, isClickSmokeMode()
      ? { refreshPrices: false, persistRefresh: false }
      : {});
    const portfolio = response?.active_portfolio;
    if (!portfolio) {
      throw new Error(`${portfolioName} 포트폴리오를 찾을 수 없습니다.`);
    }
    fillPortfolioForm(portfolio);
    const result = await runRiskScanForPortfolio(portfolio);
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioPerformanceButton?.addEventListener("click", async () => {
  const portfolioName = activePortfolioNameForSmartTable();
  if (!portfolioName) {
    setError(new Error("기간 수익 비교를 실행할 저장 포트폴리오를 선택하세요."));
    return;
  }
  startOutputLoading("포트폴리오 기간 수익 비교 중", [
    "현재 화면 수량/평단 저장",
    "저장 포트폴리오 확인",
    "최근 1주일/1개월/6개월/1년 기준일 계산",
    "국내 가격 히스토리 조회",
    "기간별 순수익과 수익률 비교",
  ]);
  try {
    if (!isClickSmokeMode()) {
      const payload = currentPortfolioPayload();
      const result = await savePortfolio(token(), payload);
      await refreshPortfolioStore(true);
      if (result?.active_portfolio) {
        if (elements.portfolioSelect) {
          elements.portfolioSelect.value = result.active_portfolio.portfolio_name || payload.portfolioName;
        }
        fillPortfolioForm(result.active_portfolio);
      }
    }
    await refreshPortfolioPerformance({ silent: false });
  } catch (error) {
    setError(error);
  }
});

elements.portfolioConnectivityButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("포트폴리오 전체 종목 연결 점검 중", [
    "저장된 포트폴리오 목록 확인",
    "고유 보유 종목 추출",
    "공식 티커와 회사 프로필 연결 확인",
    "저장 리포트와 RAG 검색 문서 연결 확인",
    "최신 투자 논거 스냅샷 확인",
    "현재가와 분석 라우팅 상태 정리",
  ]);
  try {
    const result = await fetchPortfolioConnectivity(token());
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.portfolioNpsFlowButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setError(new Error("국민연금 수급을 확인할 저장 포트폴리오를 선택하세요."));
    return;
  }
  startOutputLoading("국민연금 수급 데이터 확인 중", [
    "저장 포트폴리오 불러오기",
    "국내 보유 종목만 선별",
    "공공데이터포털 보유/대량보유 내역 매칭",
    "수급 경고와 대시보드 보조 근거 정리",
  ]);
  try {
    const result = await fetchPortfolioNpsFlow(token(), portfolioName);
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.portfolioAnalysisStatusButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("포트폴리오 전체 분석 현황 점검 중", [
    "저장 포트폴리오의 고유 보유 종목 추출",
    "티커별 저장 리포트 manifest 조회",
    "기준 리포트, 매매 전략, 실적 분석, 체크리스트 상태 계산",
    "다음 실행 우선순위 정리",
  ]);
  try {
    const result = await fetchPortfolioAnalysisStatus(token());
    lastPortfolioAnalysisStatus = result;
    renderPortfolioAnalysisOverview(result);
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.portfolioTeamQueueButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("기준 리포트 생성 큐 정리 중", [
    "저장 포트폴리오의 고유 보유 종목 추출",
    "공식 인증 기준 팀 리포트 존재 여부 확인",
    "평가금액 기준 우선순위 정렬",
    "다음 실행 대상과 중점 분석 정리",
  ]);
  try {
    const result = await fetchPortfolioTeamReportQueue(token());
    lastPortfolioTeamReportQueue = result;
    if (lastDashboard) {
      renderDashboardCards(lastDashboard);
    }
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.portfolioRunTopTeamButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("상위 1개 기준 리포트 자동 실행 중", [
    "기준 리포트 큐 조회",
    "평가금액 최상위 미작성 종목 선택",
    "공식 티커 인증과 입력값 동기화",
    "7개 스킬 팀 리포트 생성 및 저장",
  ]);
  try {
    const queueResult = await fetchPortfolioTeamReportQueue(token());
    const target = queueResult?.queue?.[0];
    if (!target) {
      setOutput({
        status: "success",
        module: "portfolio_team_report_queue",
        summary: "기준 리포트가 필요한 보유 종목이 없습니다.",
        queue: [],
        already_ready: queueResult?.already_ready || [],
        blocked: queueResult?.blocked || [],
      });
      return;
    }
    const verification = await certifyTickerForWorkflow(target.official_symbol || target.ticker);
    const workflowTicker = verification.official_symbol;
    syncTickerInputs(workflowTicker);
    if (elements.teamForm) {
      elements.teamForm.elements.ticker.value = workflowTicker;
      elements.teamForm.elements.investmentPeriod.value = target.investment_period || "3년";
      elements.teamForm.elements.region.value = target.region || "US";
      elements.teamForm.elements.style.value = normalizeTeamStyleValue(target.style);
      elements.teamForm.elements.focusArea.value =
        target.analysis_focus || "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크";
    }
    const result = await runCollaborativeTeamReport(token(), {
      ticker: workflowTicker,
      investmentPeriod: target.investment_period || "3년",
      region: target.region || "US",
      style: normalizeTeamStyleValue(target.style),
      focusArea:
        target.analysis_focus || "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크",
      autoInjectData: true,
      saveResult: true,
    });
    result.auto_queue_source = {
      queue_rank: 1,
      portfolio_names: target.portfolios || [],
      market_value: target.market_value,
      recommended_action: target.recommended_action,
    };
    setOutput(result);
    await runSecondaryRefresh("포트폴리오 상태 새로고침", () => refreshPortfolioStore(true));
    await runSecondaryRefresh("대시보드 카드 새로고침", () =>
      refreshDashboardCardsOnly(workflowTicker)
    );
  } catch (error) {
    setError(error);
  }
});

elements.portfolioOptimizeButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("강화학습형 포트폴리오 정책 최적화 중", [
    "포트폴리오 상태 변수 구성",
    "최근 시장일지와 시장 상태 비교",
    "행동 공간과 보상 함수 적용",
    "비중 조정 후보 생성",
  ]);
  try {
    const data = currentPortfolioPayload();
    const result = await runReinforcementPortfolioOptimizer(token(), {
      portfolioName: data.portfolioName,
      holdings: data.holdings,
      marketState: elements.policyMarketState?.value || "",
      objective: elements.policyObjective?.value || "risk_adjusted_return",
      riskProfile: elements.policyRiskProfile?.value || "balanced",
      learningHorizonDays: Number(elements.policyLearningHorizonDays?.value || 90),
      maxPositionWeight: data.maxSinglePositionWeight,
      saveResult: Boolean(elements.policySaveResult?.checked),
    });
    result.portfolio_source_name = portfolioSourceName || "미입력";
    const portfolioContext = buildTradePortfolioContext(
      portfolioSourceName === "직접 입력" ? null : portfolio,
      workflowTicker,
      {
        warningWeightThreshold: Number(data.warningWeightThreshold),
        highWeightThreshold: Number(data.highWeightThreshold),
        lossWarningThreshold: Number(data.lossWarningThreshold),
      }
    );
    result.portfolio_context_summary = portfolioContext.summary;
    result.portfolio_context_warnings = portfolioContext.warnings;
    setOutput(result);
    if (result?.storage) {
      await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
    }
  } catch (error) {
    setError(error);
  }
});

elements.portfolioSaveButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("포트폴리오 저장 중", [
    "입력값 검증",
    "공식 티커 확인",
    "저장소 업데이트",
  ]);
  try {
    const result = await savePortfolio(token(), currentPortfolioPayload());
    await refreshPortfolioStore(true);
    if (result?.active_portfolio) {
      if (elements.portfolioSelect) {
        elements.portfolioSelect.value = result.active_portfolio.portfolio_name || "";
      }
      fillPortfolioForm(result.active_portfolio);
      updatePortfolioLoadedAt(result.active_portfolio, "저장 후 불러온");
    }
    await refreshPortfolioSmartTable({ silent: true });
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioKiwoomSyncButton?.addEventListener("click", async () => {
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setOutput("동기화할 내 포트폴리오가 없습니다.");
    return;
  }
  syncApiBaseUrl();
  elements.portfolioKiwoomSyncButton.disabled = true;
  startOutputLoading("키움 국내 수량 변경 예정 확인 중", [
    "저장 포트폴리오 조회",
    "키움 국내 계좌평가잔고 조회",
    "국내 종목 변경 예정 목록 구성",
    "해외·수동 종목 보호 목록 표시",
  ]);
  try {
    const result = await previewKiwoomDomesticPortfolioSync(token(), portfolioName);
    const activePortfolio = result?.active_portfolio;
    if (activePortfolio) {
      if (elements.portfolioSelect) {
        elements.portfolioSelect.value = activePortfolio.portfolio_name || portfolioName;
      }
      fillPortfolioForm(activePortfolio);
      updatePortfolioLoadedAt(activePortfolio, "키움 국내 미리보기 후 불러온");
    }
    const summary = result?.sync_summary || {};
    if (["not_configured", "kiwoom_unavailable"].includes(summary.status)) {
      clearPendingKiwoomDomesticSync();
    } else {
      setPendingKiwoomDomesticSync(portfolioName, result);
    }
    renderPortfolioSyncOverview({
      portfolio: activePortfolio,
      summary: {
        ...summarizePortfolioSyncFromPortfolio(activePortfolio),
        latest_checked_at: summary.checked_at || summarizePortfolioSyncFromPortfolio(activePortfolio).latest_checked_at,
      },
    });
    setOutput(
      [
        summary.status === "not_configured"
          ? "# 키움 국내 수량 동기화 설정 필요"
          : summary.status === "kiwoom_unavailable"
            ? "# 키움 국내 수량 확인 연결 실패"
          : "# 키움 국내 수량 변경 예정",
        "",
        `- 포트폴리오: ${activePortfolio?.portfolio_name || portfolioName}`,
        `- 범위: 국내주식/ETF 잔고만 갱신`,
        "- 아직 저장하지 않았습니다. 내용을 확인한 뒤 `변경 적용`을 누르면 저장됩니다.",
        "- PL 같은 해외주식과 수동 관리 종목은 기존 수량을 덮어쓰지 않습니다.",
        summary.message ? `- 상태: ${summary.message}` : "",
        ...kiwoomSyncSummaryLines(summary),
      ]
        .filter(Boolean)
        .join("\n")
    );
    await refreshPortfolioSmartTable({ silent: true });
  } catch (error) {
    setError(error);
  } finally {
    elements.portfolioKiwoomSyncButton.disabled = false;
  }
});

elements.portfolioKiwoomApplyButton?.addEventListener("click", async () => {
  const portfolioName = pendingKiwoomDomesticSync?.portfolioName || elements.portfolioSelect.value;
  if (!portfolioName) {
    setOutput("적용할 키움 국내 수량 확인 결과가 없습니다.");
    return;
  }
  syncApiBaseUrl();
  elements.portfolioKiwoomApplyButton.disabled = true;
  elements.portfolioKiwoomCancelButton.disabled = true;
  startOutputLoading("키움 국내 수량 변경 적용 중", [
    "최신 키움 국내 잔고 재조회",
    "국내 종목 변경 저장",
    "해외·수동 종목 수량 보존",
    "동기화 이력 기록",
  ]);
  try {
    const result = await syncKiwoomDomesticPortfolio(token(), portfolioName);
    await refreshPortfolioStore(true);
    const activePortfolio = result?.active_portfolio;
    if (activePortfolio) {
      if (elements.portfolioSelect) {
        elements.portfolioSelect.value = activePortfolio.portfolio_name || portfolioName;
      }
      fillPortfolioForm(activePortfolio);
      updatePortfolioLoadedAt(activePortfolio, "키움 국내 적용 후 불러온");
    }
    const summary = result?.sync_summary || {};
    clearPendingKiwoomDomesticSync();
    renderPortfolioSyncOverview({
      portfolio: activePortfolio,
      summary: {
        ...summarizePortfolioSyncFromPortfolio(activePortfolio),
        latest_checked_at: summary.checked_at || summarizePortfolioSyncFromPortfolio(activePortfolio).latest_checked_at,
        last_history_checked_at: summary.checked_at || "",
        last_history_message: summary.message || "",
      },
    });
    setOutput(
      [
        summary.status === "not_configured"
          ? "# 키움 국내 수량 동기화 설정 필요"
          : summary.status === "kiwoom_unavailable"
            ? "# 키움 국내 수량 확인 연결 실패"
          : "# 키움 국내 수량 변경 적용 완료",
        "",
        `- 포트폴리오: ${activePortfolio?.portfolio_name || portfolioName}`,
        "- 적용 이력은 `research_vault/_system/portfolio_sync_history.jsonl`에 기록했습니다.",
        "- PL 같은 해외주식과 수동 관리 종목은 기존 수량을 덮어쓰지 않았습니다.",
        summary.message ? `- 상태: ${summary.message}` : "",
        ...kiwoomSyncSummaryLines(summary),
      ]
        .filter(Boolean)
        .join("\n")
    );
    await refreshPortfolioSmartTable({ silent: true });
  } catch (error) {
    setError(error);
    if (elements.portfolioKiwoomApplyButton) {
      elements.portfolioKiwoomApplyButton.disabled = false;
    }
    if (elements.portfolioKiwoomCancelButton) {
      elements.portfolioKiwoomCancelButton.disabled = false;
    }
  }
});

elements.portfolioKiwoomCancelButton?.addEventListener("click", async () => {
  const portfolioName = pendingKiwoomDomesticSync?.portfolioName || elements.portfolioSelect.value;
  clearPendingKiwoomDomesticSync();
  if (portfolioName) {
    try {
      const result = await fetchPortfolio(token(), portfolioName, {
        refreshPrices: false,
        persistRefresh: false,
      });
      fillPortfolioForm(result?.active_portfolio);
      updatePortfolioLoadedAt(result?.active_portfolio, "키움 미리보기 취소 후 불러온");
    } catch (error) {
      setError(error);
      return;
    }
  }
  setOutput("키움 국내 수량 변경 적용을 취소했습니다. 저장 데이터는 변경하지 않았습니다.");
});

elements.portfolioSyncHistoryButton?.addEventListener("click", async () => {
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setOutput("동기화 이력을 조회할 내 포트폴리오가 없습니다.");
    return;
  }
  syncApiBaseUrl();
  elements.portfolioSyncHistoryButton.disabled = true;
  startOutputLoading("최근 계좌 동기화 이력 조회 중", [
    "저장 포트폴리오 확인",
    "키움 국내 동기화 이력 읽기",
    "수동 보호/미확인 상태 요약",
  ]);
  try {
    const result = await fetchPortfolioSyncHistory(token(), portfolioName, { limit: 10 });
    renderPortfolioSyncOverview(result);
    setOutput(portfolioSyncHistoryOutputLines(result).join("\n"));
  } catch (error) {
    setError(error);
  } finally {
    elements.portfolioSyncHistoryButton.disabled = false;
  }
});

elements.portfolioLoadButton.addEventListener("click", async () => {
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setOutput("불러올 내 포트폴리오가 없습니다.");
    return;
  }
  syncApiBaseUrl();
  startOutputLoading("내 포트폴리오 가격 갱신 불러오기 중", [
    "저장 포트폴리오 조회",
    "KIS/Finnhub/Tiingo 최신 현재가 조회",
    "평가금액과 수익률 재계산",
    "입력 폼과 그래프 테이블 갱신",
  ]);
  try {
    let liveRefreshTimedOut = false;
    let result = null;
    try {
      result = await fetchPortfolioWithAbortTimeout(
        portfolioName,
        {
          refreshPrices: true,
          persistRefresh: true,
        },
        45000
      );
    } catch (error) {
      if (!isAbortTimeoutError(error)) {
        throw error;
      }
      liveRefreshTimedOut = true;
      result = await fetchPortfolio(token(), portfolioName, {
        refreshPrices: false,
        persistRefresh: false,
      });
    }
    fillPortfolioForm(result?.active_portfolio);
    updatePortfolioLoadedAt(
      result?.active_portfolio,
      liveRefreshTimedOut ? "저장 데이터 우선 불러온" : "실시간 갱신 후 불러온"
    );
    const activePortfolio = result?.active_portfolio;
    setOutput(
      [
        liveRefreshTimedOut
          ? "# 포트폴리오 저장 데이터 우선 불러오기 완료"
          : "# 포트폴리오 실시간 불러오기 완료",
        "",
        `- 포트폴리오: ${activePortfolio?.portfolio_name || portfolioName}`,
        `- 보유 종목: ${activePortfolio?.holding_count ?? activePortfolio?.holdings?.length ?? 0}개`,
        `- 총액: ${formatMoney(activePortfolio?.portfolio_value, "KRW", "n/a")}`,
        ...portfolioRefreshStatusLines(activePortfolio),
        liveRefreshTimedOut
          ? "- 실시간 가격 갱신이 45초를 넘겨 중단되어 저장된 현재가 기준 데이터를 먼저 표시했습니다."
          : "- 저장된 현재가 캐시를 우회해 최신 데이터로 평가금액과 수익률을 다시 계산했습니다.",
        liveRefreshTimedOut
          ? "- 가격 제공자가 느릴 때도 선택한 포트폴리오와 보유 종목 수가 전체 포트폴리오로 바뀌지 않도록 보호했습니다."
          : "",
        "- 수량과 평단은 저장 포트폴리오 기준입니다. 실제 계좌 수량 자동 동기화는 아직 연결되지 않았습니다.",
        "- PL처럼 수량이 바뀐 종목은 해당 행의 수량 칸을 수정한 뒤 같은 행의 저장 버튼을 누르세요.",
      ].filter(Boolean).join("\n")
    );
    withTimeout(
      refreshPortfolioSmartTable({ silent: true }),
      8000,
      "그래프/지능형 테이블 갱신이 지연되어 포트폴리오 불러오기 완료 후 백그라운드로 넘겼습니다."
    ).catch((error) => console.warn(error?.message || error));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioDeleteButton.addEventListener("click", async () => {
  const portfolioName = elements.portfolioSelect.value;
  if (!portfolioName) {
    setOutput("삭제할 내 포트폴리오가 없습니다.");
    return;
  }
  syncApiBaseUrl();
  startOutputLoading("내 포트폴리오 삭제 중", ["저장소 조회", "선택 항목 삭제"]);
  try {
    const result = await deletePortfolio(token(), portfolioName);
    await refreshPortfolioStore(true);
    setOutput(result);
    await runSecondaryRefresh("상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.portfolioImportPickButton.addEventListener("click", () => {
  elements.portfolioImportFile.click();
  setOutput("포트폴리오 파일 선택 창을 열었습니다.");
});

elements.portfolioImportFile.addEventListener("change", () => {
  const file = elements.portfolioImportFile.files?.[0];
  if (elements.portfolioImportStatus) {
    elements.portfolioImportStatus.textContent = file
      ? `선택 파일: ${file.name}`
      : "텍스트, CSV, TSV, JSON, XLSX, PDF, 이미지 등 모든 파일을 선택할 수 있습니다.";
  }
});

elements.portfolioImportButton.addEventListener("click", async () => {
  const file = elements.portfolioImportFile.files?.[0];
  if (!file) {
    setOutput("불러올 포트폴리오 파일을 먼저 선택하세요.");
    return;
  }
  syncApiBaseUrl();
  startOutputLoading("포트폴리오 파일 불러오는 중", [
    "파일 내용 읽기",
    "티커, 수량, 평가금액 열 자동 인식",
    "보유 종목 편집표에 반영",
  ]);
  try {
    const result = await importPortfolioFile(token(), {
      fileName: file.name,
      contentBase64: await readFileAsBase64(file),
    });
    applyImportedPortfolioHoldings(result?.imported_holdings || []);
    renderPortfolioSmartChart([]);
    renderPortfolioSmartTable([]);
    const importedCount = result?.imported_holdings?.length || 0;
    if (elements.portfolioImportStatus) {
      elements.portfolioImportStatus.textContent = importedCount
        ? `${file.name}에서 보유 종목 ${importedCount}개를 불러왔습니다.`
        : `${file.name}에서 보유 종목을 인식하지 못했습니다.`;
    }
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.portfolioApplyExecutionButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  const text = elements.portfolioExecutionText?.value || "";
  startOutputLoading("체결 문자 반영 중", [
    "종목명, 수량, 체결가 인식",
    "기존 보유 종목과 병합",
    "평단과 평가금액 재계산",
    "저장 포트폴리오 업데이트",
  ]);
  try {
    const execution = parsePortfolioExecutionNotice(text);
    const summary = applyExecutionNoticeToPortfolioRows(execution);
    const result = await savePortfolio(token(), currentPortfolioPayload());
    await refreshPortfolioStore(true);
    const activePortfolio = result?.active_portfolio;
    if (activePortfolio) {
      if (elements.portfolioSelect) {
        elements.portfolioSelect.value = activePortfolio.portfolio_name || "";
      }
      fillPortfolioForm(activePortfolio);
      updatePortfolioLoadedAt(activePortfolio, "체결 저장 후 불러온");
    }
    if (elements.portfolioExecutionText) {
      elements.portfolioExecutionText.value = "";
    }
    setOutput(
      [
        "# 체결 반영 완료",
        "",
        `- 종목: ${execution.name}`,
        `- 반영 방식: ${summary.isNewHolding ? "신규 보유 추가" : "기존 보유에 추가 매수 병합"}`,
        `- 추가 수량: ${formatNumber(execution.quantity)}주`,
        `- 체결가: ${formatMoney(execution.price, execution.currency)}`,
        `- 저장 수량: ${formatNumber(summary.nextQuantity)}주`,
        `- 저장 평단: ${formatMoney(summary.nextAverageCost, execution.currency)}`,
        "- 예수금은 반영하지 않았습니다.",
      ].join("\n")
    );
  } catch (error) {
    setError(error);
  }
});

elements.addHoldingButton.addEventListener("click", () => {
  addEditorRow(elements.holdingsEditor, makePortfolioHoldingRow, {
    ticker: "",
    sector: "Unknown",
    theme_tags: [],
  });
  recalculatePortfolioValues();
  setOutput("보유 종목 입력 행을 추가했습니다.");
});

elements.addCashButton.addEventListener("click", () => {
  addEditorRow(elements.holdingsEditor, makePortfolioHoldingRow, {
    ticker: "CASH",
    name: "현금",
    sector: "Cash",
    theme_tags: ["Cash"],
  });
  recalculatePortfolioValues();
  setOutput("현금 입력 행을 추가했습니다.");
});

elements.recalculatePortfolioButton.addEventListener("click", () => {
  recalculatePortfolioValues({ forceMarketValue: true });
  applyPortfolioViewState({ sort: true });
  setOutput("내 포트폴리오 총액을 다시 계산했습니다.");
});

elements.portfolioFilter?.addEventListener("input", () => {
  applyPortfolioFilter();
});

elements.portfolioSort?.addEventListener("change", () => {
  applyPortfolioViewState({ sort: true });
  setOutput("포트폴리오 정렬 기준을 적용했습니다.");
});

elements.portfolioSmartRefreshButton?.addEventListener("click", async () => {
  startOutputLoading("포트폴리오 지능형 테이블 계산 중", [
    "저장 포트폴리오 불러오기",
    "최신 현재가 캐시 우회 조회",
    "52주 최고가 조회",
    "목표주가 근접도 계산",
    "그래프와 정렬 테이블 갱신",
  ]);
  try {
    await refreshPortfolioSmartTable({
      silent: false,
      forcePriceRefresh: true,
      persistRefresh: true,
    });
  } catch (error) {
    setError(error);
  }
});

elements.portfolioConsensusScanButton?.addEventListener("click", async () => {
  startOutputLoading("컨센서스 저평가 스캔 중", [
    "포트폴리오와 관심종목 후보 수집",
    "저장 리포트에서 목표주가 추출",
    "현재가 대비 상승여력 계산",
    "저평가 순위 정렬",
  ]);
  try {
    await runTargetConsensusScan({ silent: false });
  } catch (error) {
    setError(error);
  }
});

elements.portfolioSmartTable?.addEventListener("click", (event) => {
  const sortHeader = event.target.closest("[data-smart-sort]");
  if (!sortHeader || event.target.closest("[data-resize-column]")) {
    return;
  }
  const key = sortHeader.dataset.smartSort;
  portfolioSmartSort = {
    key,
    direction:
      portfolioSmartSort.key === key && portfolioSmartSort.direction === "desc"
        ? "asc"
        : "desc",
  };
  renderPortfolioSmartTable(portfolioSmartRows);
  setOutput("지능형 테이블 정렬을 적용했습니다.");
});

elements.portfolioSmartTable?.addEventListener("pointerdown", resizeSmartTableColumn);

elements.portfolioConsensusTable?.addEventListener("click", (event) => {
  const sortHeader = event.target.closest("[data-consensus-sort]");
  if (!sortHeader) {
    return;
  }
  const key = sortHeader.dataset.consensusSort;
  consensusScanSort = {
    key,
    direction:
      consensusScanSort.key === key && consensusScanSort.direction === "desc"
        ? "asc"
        : "desc",
  };
  renderTargetConsensusTable(consensusScanRows);
  setOutput("컨센서스 테이블 정렬을 적용했습니다.");
});

elements.holdingsEditor.addEventListener("click", async (event) => {
  const actionButton = event.target.closest("[data-holding-action]");
  if (actionButton) {
    const row = actionButton.closest(".holding-row");
    if (actionButton.dataset.holdingAction === "save") {
      syncApiBaseUrl();
      const changedName = rowValue(row, "name") || rowValue(row, "ticker") || "보유 종목";
      startOutputLoading(`${changedName} 수량/평단 저장 중`, [
        "현재 화면 포트폴리오 입력값 수집",
        "공식 티커 확인",
        "현재가 재계산",
        "저장소 업데이트",
      ]);
      try {
        const result = await savePortfolio(token(), currentPortfolioPayload());
        await refreshPortfolioStore(true);
        const activePortfolio = result?.active_portfolio;
        if (activePortfolio) {
          if (elements.portfolioSelect) {
            elements.portfolioSelect.value = activePortfolio.portfolio_name || "";
          }
          fillPortfolioForm(activePortfolio);
          updatePortfolioLoadedAt(activePortfolio, "수량 저장 후 불러온");
        }
        const savedHolding = (activePortfolio?.holdings || []).find(
          (holding) => normalizeTickerDraft(holding.ticker) === normalizeTickerDraft(rowValue(row, "ticker"))
        );
        setOutput(
          [
            "# 보유 수량 저장 완료",
            "",
            `- 종목: ${savedHolding?.name || changedName}`,
            `- 수량: ${formatNumber(savedHolding?.quantity ?? rowValue(row, "quantity"))}`,
            `- 현재가: ${formatMoney(savedHolding?.current_price, savedHolding?.currency || rowCurrency(row), "n/a")}`,
            `- 평가금액: ${formatMoney(savedHolding?.market_value, "KRW", "n/a")}`,
            "- 이후 불러오기와 기간 수익 비교는 이 저장 수량을 기준으로 계산합니다.",
          ].join("\n")
        );
      } catch (error) {
        setError(error);
      }
      return;
    }
    const ticker = normalizeTickerDraft(rowValue(row, "ticker"));
    if (!ticker || isCashTicker(ticker)) {
      setError(new Error("분석할 보유 종목 티커를 먼저 입력하세요."));
      return;
    }
    startOutputLoading(`${ticker} 보유 종목 분석 연결 중`, [
      "공식 티커 인증",
      "대시보드 입력값 동기화",
      "저장 데이터와 최신 데이터 조회",
    ]);
    try {
      const verification = await certifyTickerForWorkflow(ticker);
      activateTab("dashboard", { keepOutput: true });
      await loadTickerDashboard(verification.official_symbol);
    } catch (error) {
      await setTickerAwareError(error, ticker);
    }
    return;
  }

  const removeButton = event.target.closest("[data-editor-remove]");
  if (!removeButton) {
    return;
  }
  const row = removeButton.closest(".editor-row");
  row?.remove();
  if (!elements.holdingsEditor.querySelector(".editor-row")) {
    addEditorRow(elements.holdingsEditor, makePortfolioHoldingRow, {
      ticker: "",
      sector: "Unknown",
      theme_tags: [],
    });
  }
  recalculatePortfolioValues();
  setOutput("보유 종목 입력 행을 삭제했습니다.");
});

elements.holdingsEditor.addEventListener("input", (event) => {
  const row = event.target.closest(".holding-row");
  if (!row) {
    return;
  }
  if (event.target.name === "ticker") {
    const draftTicker = normalizeTickerDraft(event.target.value);
    if (event.target.value !== draftTicker) {
      event.target.value = draftTicker;
    }
    normalizeHoldingCashFields(row);
  }
  if (event.target.name === "name") {
    syncCompanyNameAlignment(row);
  }
  const forceMarketValue = ["quantity", "current_price"].includes(event.target.name);
  recalculatePortfolioValues({ forceMarketValue });
  if (["quantity", "average_cost", "current_price", "market_value"].includes(event.target.name)) {
    markHoldingRowUnsaved(row);
  }
});

elements.interestsLoadButton.addEventListener("click", async () => {
  elements.interestsLoadButton.disabled = true;
  startOutputLoading("관심종목/섹터 불러오는 중", ["관심 종목 조회", "관심 섹터 조회"]);
  try {
    await refreshInterestList(false);
  } catch (error) {
    setError(error);
  } finally {
    elements.interestsLoadButton.disabled = false;
  }
});

elements.interestAutomationButton?.addEventListener("click", async () => {
  elements.interestAutomationButton.disabled = true;
  startOutputLoading("관심종목/섹터 자동 수집 보드 생성 중", [
    "보유종목·관심종목·관심섹터 수집 대상 정리",
    "최근 저장 자료 중복 제거 상태 점검",
    "RAG 검색어와 시장일지 연결 포인트 생성",
  ]);
  try {
    await saveCurrentInterestList({ quiet: true });
    const result = await fetchInterestAutomationBoard(token(), true);
    lastInterestAutomationBoard = result || null;
    renderInterestAutomationBoardCards(result);
    setOutput(result);
    if (lastDashboard) {
      renderDashboardCards(lastDashboard);
    }
  } catch (error) {
    setError(error);
  } finally {
    elements.interestAutomationButton.disabled = false;
  }
});

elements.interestsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  elements.interestsSaveButton.disabled = true;
  const draftTicker = collectInterestTickerRows(elements.interestTickerDraft)[0];
  const draftSector = collectInterestSectorRows(elements.interestSectorDraft)[0];
  try {
    if (draftTicker?.ticker) {
      const added = await addInterestTickerDraftToList({ autoSave: false, announce: false });
      if (!added) {
        return;
      }
    }
    if (draftSector?.name) {
      const added = await addInterestSectorDraftToList({ autoSave: false, announce: false });
      if (!added) {
        return;
      }
    }
    const tickers = collectInterestTickers();
    const sectors = collectInterestSectors();
    if (!tickers.length && !sectors.length) {
      setError(new Error("관심종목 또는 관심섹터를 1개 이상 입력하세요."));
      elements.interestTickerDraft.querySelector('[name="ticker"]')?.focus();
      return;
    }
    startOutputLoading("관심종목/섹터 저장 중", [
      "향후 매수 관심종목 공식 티커 인증",
      "관심 섹터 정리",
      "저장소 업데이트",
    ]);
    await saveCurrentInterestList();
  } catch (error) {
    setError(error);
  } finally {
    elements.interestsSaveButton.disabled = false;
  }
});

function appendLocalInterestTickerDraft(draft, verification, officialSymbol, verified = false) {
  elements.interestTickerEditor.querySelector(".editor-empty-state")?.remove();
  const existingRow = [...elements.interestTickerEditor.querySelectorAll(".interest-ticker-row")].find(
    (row) => normalizeTickerDraft(rowValue(row, "ticker")) === normalizeTickerDraft(officialSymbol)
  );
  const nextRow = makeInterestTickerSummaryRow({
    ...draft,
    ticker: officialSymbol,
    companyName: verification?.company_name || draft.ticker || officialSymbol,
    tags: verified ? draft.tags : [...(draft.tags || []), "verification_pending"],
    verification,
  });
  if (existingRow) {
    existingRow.replaceWith(nextRow);
  } else {
    elements.interestTickerEditor.append(nextRow);
  }
  resetInterestTickerDraft();
  nextRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
  updateInterestsSummary();
  elements.interestTickerDraft.querySelector('[name="ticker"]')?.focus();
  return nextRow;
}

async function addInterestTickerDraftToList({ autoSave = true, announce = true } = {}) {
  const draft = collectInterestTickerRows(elements.interestTickerDraft)[0];
  if (!draft?.ticker) {
    setError(new Error("추가할 관심종목의 티커 또는 회사명을 입력하세요."));
    elements.interestTickerDraft.querySelector('[name="ticker"]')?.focus();
    return false;
  }
  if (announce) {
    startOutputLoading("관심종목 1개 인증 중", [
      "입력값을 공식 티커로 변환",
      "회사명 확인",
      "관심종목에 추가",
    ]);
  }
  const lookupValue = resolveLocalTickerAlias(draft.ticker);
  const officialSymbol = normalizeTickerDraft(lookupValue || draft.ticker);
  const fallbackVerification = {
    status: "pending",
    verified: false,
    official_symbol: officialSymbol,
    company_name: draft.ticker,
    verification_source: "save_first_pending_verification",
    message: "먼저 관심종목에 저장합니다. 공식 인증은 저장 후 백엔드 로컬 사전과 티커 진단에서 보강합니다.",
  };
  const fallbackVerified = Boolean(fallbackVerification?.verified);
  try {
    if (autoSave) {
      const result = await addInterestTicker(token(), {
        ticker: draft.ticker,
        query: draft.ticker,
        priority: draft.priority || "medium",
        thesis: draft.thesis || null,
        notes: draft.notes || null,
        tags: draft.tags || [],
      });
      fillInterestsForm(result);
      if (announce) {
        const added = (result.tickers || []).find(
          (item) =>
            normalizeTickerDraft(item.ticker) === officialSymbol ||
            String(item.verification?.requested_symbol || "").trim() === String(draft.ticker || "").trim()
        );
        const label =
          added?.verification?.company_name ||
          added?.ticker ||
          resolveLocalTickerAlias(draft.ticker) ||
          draft.ticker;
        const statusLine = added?.verification?.verified
          ? "공식 티커 인증까지 완료했습니다."
          : "먼저 관심종목에 저장했습니다. 공식 인증이 필요한 종목은 티커 진단이나 자료 입력으로 보강합니다.";
        setOutput(`관심종목에 **${label}**${koreanObjectParticle(label)} 추가하고 저장했습니다.\n\n${statusLine}\n\n현재 저장된 관심종목: ${(result.tickers || []).length}개`);
      }
      await runSecondaryRefresh("관심종목/섹터 상태 새로고침", () => refreshStatus(false));
      return true;
    }
    appendLocalInterestTickerDraft(draft, fallbackVerification, officialSymbol, fallbackVerified);
    if (announce) {
      const label = fallbackVerification?.company_name || draft.ticker || officialSymbol;
      const statusLine = fallbackVerified
        ? "공식 티커 인증까지 완료했습니다."
        : "공식 인증은 보류했지만 관심종목 목록에는 저장했습니다. 이후 티커 진단이나 자료 입력으로 보강할 수 있습니다.";
      setOutput(`관심종목에 **${label}**${koreanObjectParticle(label)} 추가하고 저장했습니다.\n\n${statusLine}\n\n아래 목록에서 우선순위와 메모를 바로 편집할 수 있습니다.`);
    }
    return true;
  } catch (error) {
    appendLocalInterestTickerDraft(draft, fallbackVerification, officialSymbol, fallbackVerified);
    try {
      await saveCurrentInterestList({ quiet: true });
      if (announce) {
        const label = fallbackVerification?.company_name || draft.ticker || officialSymbol;
        setOutput(`관심종목에 **${label}**${koreanObjectParticle(label)} 우선 저장했습니다.\n\n백엔드 인증/동기화 중 오류가 있었지만 입력값은 목록에 남겼습니다. 저장 버튼을 다시 누르면 재동기화됩니다.\n\n오류: ${error.message || error}`);
      }
      return true;
    } catch (saveError) {
      setError(saveError);
      return false;
    }
  }
}

async function addInterestSectorDraftToList({ autoSave = true, announce = true } = {}) {
  const draft = collectInterestSectorRows(elements.interestSectorDraft)[0];
  if (!draft?.name) {
    setError(new Error("추가할 관심섹터 또는 테마명을 입력하세요."));
    elements.interestSectorDraft.querySelector('[name="name"]')?.focus();
    return false;
  }
  if (autoSave) {
    if (announce) {
      startOutputLoading("관심섹터 추가 저장 중", [
        String(draft.name || "관심섹터") + " 항목을 관심섹터 목록에 반영",
        "지역과 우선순위 정리",
        "저장소 업데이트 후 화면 새로고침",
      ]);
    }
    try {
      const result = await addInterestSector(token(), draft);
      fillInterestsForm(result);
      resetInterestSectorDraft();
      updateInterestsSummary(result);
      let addedRow = [...elements.interestSectorEditor.querySelectorAll(".interest-sector-row")].find(
        (row) => rowValue(row, "name").trim().toLowerCase() === draft.name.trim().toLowerCase()
      );
      if (!addedRow) {
        elements.interestSectorEditor.querySelector(".editor-empty-state")?.remove();
        addedRow = addEditorRow(
          elements.interestSectorEditor,
          () => makeInterestSectorSummaryRow(draft)
        );
        await saveCurrentInterestList({ quiet: true });
        addedRow = [...elements.interestSectorEditor.querySelectorAll(".interest-sector-row")].find(
          (row) => rowValue(row, "name").trim().toLowerCase() === draft.name.trim().toLowerCase()
        ) || addedRow;
      }
      addedRow?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      if (announce) {
        setOutput(`관심섹터에 **${draft.name}**${koreanObjectParticle(draft.name)} 추가하고 저장했습니다.\n\n아래 목록에서 지역, 우선순위, 태그, 관심 이유를 바로 편집할 수 있습니다.`);
      }
      await runSecondaryRefresh("관심종목/섹터 상태 새로고침", () => refreshStatus(false));
      elements.interestSectorDraft.querySelector('[name="name"]')?.focus();
      return true;
    } catch (error) {
      setError(error);
      return false;
    }
  }
  elements.interestSectorEditor.querySelector(".editor-empty-state")?.remove();
  const existingRow = [...elements.interestSectorEditor.querySelectorAll(".interest-sector-row")].find(
    (row) => rowValue(row, "name").trim().toLowerCase() === draft.name.trim().toLowerCase()
  );
  const nextRow = makeInterestSectorSummaryRow(draft);
  const row = existingRow
    ? existingRow.replaceWith(nextRow) || nextRow
    : addEditorRow(elements.interestSectorEditor, () => nextRow);
  resetInterestSectorDraft();
  row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  updateInterestsSummary();
  elements.interestSectorDraft.querySelector('[name="name"]')?.focus();
  return true;
}

elements.addInterestTickerButton.addEventListener("click", () => {
  elements.addInterestTickerButton.disabled = true;
  addInterestTickerDraftToList()
    .catch(setError)
    .finally(() => {
      elements.addInterestTickerButton.disabled = false;
    });
});

elements.interestTickerDraft?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  const target = event.target;
  if (!target || target.tagName === "TEXTAREA") {
    return;
  }
  event.preventDefault();
  elements.addInterestTickerButton?.click();
});

elements.addInterestSectorButton.addEventListener("click", () => {
  elements.addInterestSectorButton.disabled = true;
  addInterestSectorDraftToList()
    .catch(setError)
    .finally(() => {
      elements.addInterestSectorButton.disabled = false;
    });
});

elements.interestSectorDraft?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  const target = event.target;
  if (!target || target.tagName === "TEXTAREA") {
    return;
  }
  event.preventDefault();
  elements.addInterestSectorButton?.click();
});

elements.interestTickerEditor.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-interest-action]");
  if (actionButton) {
    const ticker = actionButton.dataset.interestTicker;
    const interestAction = actionButton.dataset.interestAction;
    if (interestAction === "rag-search" || interestAction === "rag-synthesis") {
      const row = actionButton.closest(".interest-ticker-row");
      const query = buildInterestRagQuery(row, ticker, "ticker");
      runInterestRagAction({
        query,
        key: ticker,
        mode: interestAction === "rag-synthesis" ? "synthesis" : "search",
      }).catch(setError);
      return;
    }
    const action = interestAction === "team" ? "run-team" : "dashboard";
    openTickerWorkflow(action, ticker).catch(setError);
    return;
  }
  const button = event.target.closest("[data-editor-remove]");
  if (!button) {
    return;
  }
  button.closest(".interest-ticker-row, .editor-row")?.remove();
  if (!elements.interestTickerEditor.querySelector(".interest-ticker-row")) {
    renderEditorRowsExact(
      elements.interestTickerEditor,
      [],
      makeInterestTickerSummaryRow,
      "추가된 관심종목이 없습니다. 위 입력칸에서 1개씩 추가하세요."
    );
  }
  updateInterestsSummary();
  saveCurrentInterestList({ quiet: true })
    .then(() => setOutput("관심종목을 삭제하고 저장했습니다."))
    .catch(setError);
});

elements.interestTickerEditor.addEventListener("input", (event) => {
  clearEditorInputWarning(event);
  updateInterestsSummary();
});

elements.interestTickerEditor.addEventListener("change", (event) => {
  clearEditorInputWarning(event);
  updateInterestsSummary();
  saveCurrentInterestList({ quiet: true }).catch(setError);
});

elements.interestTickerDraft.addEventListener("input", clearEditorInputWarning);
elements.interestTickerDraft.addEventListener("change", clearEditorInputWarning);

elements.interestSectorEditor.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-interest-action]");
  if (actionButton) {
    const sector = actionButton.dataset.interestSector;
    const row = actionButton.closest(".interest-sector-row");
    const action = actionButton.dataset.interestAction;
    const query = buildInterestRagQuery(row, sector, "sector");
    runInterestRagAction({
      query,
      key: sector || "MARKET",
      mode: action === "sector-rag-synthesis" ? "synthesis" : "search",
    }).catch(setError);
    return;
  }
  const button = event.target.closest("[data-editor-remove]");
  if (!button) {
    return;
  }
  button.closest(".interest-sector-row, .editor-row")?.remove();
  if (!elements.interestSectorEditor.querySelector(".interest-sector-row")) {
    renderEditorRowsExact(
      elements.interestSectorEditor,
      [],
      makeInterestSectorSummaryRow,
      "추가된 관심섹터가 없습니다. 위 입력칸에서 1개씩 추가하세요."
    );
  }
  updateInterestsSummary();
  saveCurrentInterestList({ quiet: true })
    .then(() => setOutput("관심섹터를 삭제하고 저장했습니다."))
    .catch(setError);
});

elements.interestSectorEditor.addEventListener("input", (event) => {
  clearEditorInputWarning(event);
  updateInterestsSummary();
});

elements.interestSectorEditor.addEventListener("change", (event) => {
  clearEditorInputWarning(event);
  updateInterestsSummary();
  saveCurrentInterestList({ quiet: true }).catch(setError);
});

elements.interestSectorDraft.addEventListener("input", clearEditorInputWarning);
elements.interestSectorDraft.addEventListener("change", clearEditorInputWarning);

elements.checklistForm.addEventListener("change", updateChecklistProgress);

elements.checklistForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("체크리스트 투자 준비도 분석 중", [
    "종목 공식 인증",
    "16개 체크 항목 완료율 계산",
    "투자 준비도와 다음 단계 정리",
    "저장 데이터 연결",
  ]);
  const data = formDataObject(form);
  try {
    const verification = await certifyTickerForWorkflow(data.ticker);
    const workflowTicker = verification.official_symbol;
    const checkedItems = getCheckedChecklistItems();
    const result = await assessResearchChecklist(token(), {
      ticker: workflowTicker,
      checkedItems,
      notes: data.notes,
      saveResult: true,
    });
    setOutput(result);
    await runSecondaryRefresh("대시보드 카드 새로고침", () =>
      refreshDashboardCardsOnly(workflowTicker)
    );
  } catch (error) {
    setError(error);
  }
});

const MEMORY_ACTION_MESSAGES = {
  ragNaturalSearchButton: "전체 자연어 검색을 시작했습니다.",
  ragSynthesisButton: "검색 결과 합성을 시작했습니다.",
  ragSearchButton: "현재 키 RAG 검색을 시작했습니다.",
  dossierButton: "Dossier 합성을 시작했습니다.",
  todayResearchUpdateButton: "오늘 리서치 업데이트를 시작했습니다.",
  naverResearchStatusButton: "네이버 리서치 상태를 조회합니다.",
  naverResearchRepairButton: "네이버 리서치 캐시 정리와 PDF 신호 백필을 시작했습니다.",
  naverMarketJournalButton: "네이버 국내 마감 시황을 시장일지에 반영합니다.",
  dailyBriefButton: "일일 브리핑 생성을 시작했습니다.",
  dailyRecommendationsButton: "오늘 추천 후보 1~3위 생성과 추적 저장을 시작했습니다.",
  dailyRecommendationsStatusButton: "추천 후보와 사후 추적 상태를 조회합니다.",
  researchAutomationButton: "전체 자동화를 시작했습니다.",
  researchAutomationStatusButton: "자동화 상태 점검을 시작했습니다.",
  codeKnowledgeGraphButton: "시스템 구조 맵을 조회합니다.",
  ragBackfillButton: "RAG 색인 갱신을 시작했습니다.",
  ocrReprocessButton: "저장 데이터 OCR 재처리를 시작했습니다.",
  storageCleanupButton: "저장 데이터 정리를 시작했습니다.",
  dedupedDossierRefreshButton: "중복 종목 Dossier 갱신을 시작했습니다.",
  manifestButton: "전체 저장 목록 조회를 시작했습니다.",
  tickerCacheButton: "티커 캐시 조회를 시작했습니다.",
  publicIrSecCollectButton: "공개 IR/SEC 자료 수집을 시작했습니다.",
  publicIrSecStatusButton: "공개 IR/SEC 저장 상태를 조회합니다.",
  investmentCalendarRefreshButton: "투자 캘린더를 새로고침합니다.",
};


elements.investmentCalendarRefreshButton?.addEventListener("click", async () => {
  startOutputLoading("투자 캘린더 불러오는 중", [
    "최근 생성된 월간 캘린더 확인",
    "한국/미국 시장 일정 분리",
    "보유/관심 종목 관련 일정 렌더링",
  ]);
  try {
    await loadInvestmentCalendar({ showOutput: true });
  } catch (error) {
    setError(error);
  }
});

elements.memoryForm.addEventListener(
  "click",
  (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) {
      return;
    }
    const message =
      MEMORY_ACTION_MESSAGES[button.id] ||
      `${actionLabelFromButton(button)} 요청을 시작했습니다.`;
    registerActionClick(button, message, event);
  },
  { capture: true }
);

elements.memoryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseUrl();
  const form = event.currentTarget;
  startOutputLoading("저장 데이터 조회 중", [
    "저장 키 정규화",
    "파일 목록 조회",
    "미리보기 목록 구성",
  ]);
  const data = formDataObject(form);
  const requestedKey = String(data.ticker || activeTicker || "전체").trim() || "전체";
  if (elements.memoryList) {
    elements.memoryList.innerHTML = `
      <div class="memory-status-card">
        <h3>저장 데이터 키</h3>
        <strong>${escapeHtml(requestedKey)}</strong>
        <p>파일 목록과 품질 필터를 불러오는 중입니다.</p>
      </div>
    `;
  }
  try {
    const workflowKey = await resolveMemoryLookupKey(data.ticker);
    const memoryResponse = await fetchResearchMemoryFiles(token(), workflowKey, memoryListFetchOptions());
    renderMemoryList(memoryResponse, workflowKey);
    setOutput(memoryResponse);
  } catch (error) {
    setError(error);
  }
});

elements.memoryForm.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLSelectElement)) {
    return;
  }
  if (!["includeArchived", "showBodyMissingOnly", "qualityFilter"].includes(target.name)) {
    return;
  }
  showActionAccepted("저장 데이터 필터를 다시 적용합니다.");
  elements.memoryForm.requestSubmit();
});

if (elements.memorySupplementForm) {
  elements.memorySupplementForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    syncApiBaseUrl();
    const currentFile = activeMemoryPreviewFile;
    const ticker = currentFile?.ticker || elements.memorySupplementForm.dataset.memoryKey;
    const fileName = currentFile?.file_name || elements.memorySupplementForm.dataset.memoryFile;
    const bodyText = String(elements.memorySupplementBody?.value || "").trim();
    const note = String(elements.memorySupplementNote?.value || "").trim();
    if (!ticker || !fileName) {
      setError(new Error("본문을 보강할 저장 파일을 먼저 열어주세요."));
      return;
    }
    if (!bodyText) {
      setError(new Error("보강할 본문을 입력한 뒤 저장하세요."));
      elements.memorySupplementBody?.focus();
      return;
    }
    const submitButton = elements.memorySupplementForm.querySelector('button[type="submit"]');
    if (
      submitButton &&
      !registerActionClick(submitButton, "본문 보강 저장 요청을 시작했습니다.", event)
    ) {
      return;
    }
    startOutputLoading("본문 보강 저장 중", [
      "저장 파일 확인",
      "Markdown/메타데이터 갱신",
      "RAG 색인 업데이트",
      "미리보기 새로고침",
    ]);
    try {
      const updatedFile = await supplementResearchMemoryFile(token(), ticker, fileName, {
        bodyText,
        note,
      });
      renderMemoryPreview(updatedFile);
      if (elements.memorySupplementBody) {
        elements.memorySupplementBody.value = "";
      }
      if (elements.memorySupplementNote) {
        elements.memorySupplementNote.value = "";
      }
      const memoryResponse = await fetchResearchMemoryFiles(token(), ticker, memoryListFetchOptions());
      renderMemoryList(memoryResponse, ticker);
      setOutput({
        status: "success",
        module: "research_memory_body_supplement",
        ticker,
        file_name: updatedFile.file_name,
        message: "본문 보강 저장이 완료되었습니다. 기존 저장 파일과 RAG 색인이 갱신되었습니다.",
        modified_at: updatedFile.modified_at,
      });
    } catch (error) {
      setError(error);
    }
  });
}

elements.ragSearchButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  const data = formDataObject(elements.memoryForm);
  const key = await resolveMemoryLookupKey(data.ticker || activeTicker || "INBOX");
  const query = String(data.ragQuery || "").trim() || null;
  const includeLowQuality = Boolean(
    elements.memoryForm.querySelector('input[name="includeLowQuality"]')?.checked
  );
  startOutputLoading("RAG 문서 품질 검색 중", [
    "저장 manifest 색인 확인",
    "문서 품질 점수 계산",
    "자동 주입 가능 문서 선별",
  ]);
  try {
    const result = await searchRagMemoryDocuments(token(), {
      key,
      query,
      limit: 10,
      includeLowQuality,
    });
    if (!result) {
      throw new Error("RAG 검색 결과를 불러오지 못했습니다.");
    }
    renderRagMemoryList(result);
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.ragNaturalSearchButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  const data = formDataObject(elements.memoryForm);
  const query = String(data.ragQuery || data.ticker || "").trim();
  const includeLowQuality = Boolean(
    elements.memoryForm.querySelector('input[name="includeLowQuality"]')?.checked
  );
  if (!query) {
    setOutput("**검색어 필요**\n\n예: `삼양식품 수출`, `PL 악재`, `AI 전력기기 수급`처럼 찾고 싶은 내용을 입력하세요.");
    elements.memoryForm.querySelector('input[name="ragQuery"]')?.focus();
    return;
  }
  startOutputLoading("전체 저장 데이터 자연어 검색 중", [
    "전체 RAG 색인 확인",
    "검색어와 문서 관련도 계산",
    "관련 저장 데이터 카드 구성",
  ]);
  try {
    const result = await searchAllRagMemoryDocuments(token(), {
      query,
      limit: 15,
      includeLowQuality,
    });
    if (!result) {
      throw new Error("전체 RAG 검색 결과를 불러오지 못했습니다.");
    }
    renderRagMemoryList(result);
    setOutput(result);
  } catch (error) {
    setError(error);
  }
});

elements.ragSynthesisButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  const data = formDataObject(elements.memoryForm);
  const query = String(data.ragQuery || data.ticker || "").trim();
  const includeLowQuality = Boolean(
    elements.memoryForm.querySelector('input[name="includeLowQuality"]')?.checked
  );
  if (!query) {
    setOutput("**합성할 검색어 필요**\n\n예: `삼양식품 수출`, `PL 악재`, `AI 전력기기 수급`처럼 저장 데이터에서 합성할 주제를 입력하세요.");
    elements.memoryForm.querySelector('input[name="ragQuery"]')?.focus();
    return;
  }
  startOutputLoading("검색 결과 합성 중", [
    "전체 저장 데이터 검색",
    "중복 묶음과 관련도 반영",
    "공통 사실·강세·약세 논거 분리",
    "핵심 쟁점과 관찰 지표 저장",
  ]);
  try {
    const result = await synthesizeRagSearchResults(token(), {
      query,
      limit: 15,
      includeLowQuality,
      saveResult: true,
    });
    if (!result) {
      throw new Error("검색 결과 합성 보고서를 생성하지 못했습니다.");
    }
    setOutput(result);
    const storageKey =
      result.storage?.relative_path?.split("/")?.[1] ||
      result.payload?.tickers?.[0] ||
      "SEARCH";
    const memoryResponse = await fetchResearchMemoryFiles(token(), storageKey, memoryListFetchOptions());
    renderMemoryList(memoryResponse, storageKey);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.dossierButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  const data = formDataObject(elements.memoryForm);
  const key = await resolveMemoryLookupKey(data.ticker || activeTicker || DEFAULT_TICKER_DISPLAY);
  startOutputLoading("Dossier 합성 중", [
    "저장 데이터 중복 제거",
    "강세/약세 논거 분리",
    "RAG 투자 논거 스냅샷 갱신",
    "저장 데이터 목록 갱신",
  ]);
  try {
    const result = await synthesizeDossier(token(), key, true);
    setOutput(result || "Dossier 합성 결과를 확인하지 못했습니다.");
    const memoryResponse = await fetchResearchMemoryFiles(token(), key, memoryListFetchOptions());
    renderMemoryList(memoryResponse, key);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.dailyBriefButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("일일 리서치 브리핑 생성 중", [
    "보유/관심 종목 스냅샷 확인",
    "최근 시장·종목 자료 요약",
    "다음 액션 정리",
  ]);
  try {
    const result = await fetchDailyBriefing(token(), true);
    renderDailyBriefCards(result);
    setOutput(result || "일일 브리핑 결과를 확인하지 못했습니다.");
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

async function runDailyRecommendationsFlow() {
  syncApiBaseUrl();
  activateTab("memory");
  startOutputLoading("오늘 추천 후보 생성 중", [
    "보유/관심 종목과 저장 리포트 확인",
    "목표가·공시·RAG 근거 점수화",
    "추천 후보 1~3위 저장",
    "1주/15일/1달/3달/6달 추적표 갱신",
  ]);
  try {
    const result = await runDailyRecommendations(token(), { force: false, saveResult: true });
    renderDailyRecommendationCards(result);
    setOutput(result || "오늘 추천 후보 결과를 확인하지 못했습니다.");
    await runSecondaryRefresh("자동화 상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
}

async function runDailyRecommendationsStatusFlow() {
  syncApiBaseUrl();
  activateTab("memory");
  startOutputLoading("추천 추적 상태 조회 중", [
    "저장된 추천 후보 확인",
    "도래한 추적일 확인",
    "현재가 기준 사후 성과 갱신",
  ]);
  try {
    await trackDailyRecommendations(token());
    const result = await fetchDailyRecommendationsStatus(token());
    renderDailyRecommendationCards(result);
    setOutput(result || "추천 추적 상태를 확인하지 못했습니다.");
  } catch (error) {
    setError(error);
  }
}

async function runRecentWeeklyBriefFlow() {
  syncApiBaseUrl();
  activateTab("dashboard");
  startOutputLoading("최근 1주 자료 조회 중", [
    "보유/관심종목 기준 공시 확인",
    "저장 리포트와 RAG 반영 자료 집계",
    "관세청 수출입 저장 자료 확인",
    "자동 점검 상태 정리",
  ]);
  try {
    const result = await fetchRecentWeeklyResearchBrief(token(), { days: 7, refreshIfDue: true });
    setOutput(result || "최근 1주 자료를 확인하지 못했습니다.");
    await runSecondaryRefresh("DART/자동화 상태 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
}

[elements.dailyRecommendationsButton, elements.dailyRecommendationsQuickButton]
  .filter(Boolean)
  .forEach((button) => button.addEventListener("click", runDailyRecommendationsFlow));

[elements.dailyRecommendationsStatusButton, elements.dailyRecommendationsStatusQuickButton]
  .filter(Boolean)
  .forEach((button) => button.addEventListener("click", runDailyRecommendationsStatusFlow));

elements.recentWeeklyBriefButton?.addEventListener("click", runRecentWeeklyBriefFlow);

elements.publicIrSecCollectButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  const sourceUrl = elements.publicIrSecUrl?.value?.trim() || "";
  if (!sourceUrl) {
    setOutput("**입력 필요**\n\n공개 IR/SEC URL을 입력한 뒤 수집 버튼을 누르세요.");
    elements.publicIrSecUrl?.focus();
    return;
  }
  startOutputLoading("공개 IR/SEC 자료 수집 중", [
    "공개 URL 안전성 확인",
    "본문/메타데이터 추출",
    "저장 데이터와 RAG 색인 반영",
  ]);
  try {
    const result = await collectPublicIrSec(token(), { url: sourceUrl, targetKey: "PUBLIC_IR_SEC", saveResult: true });
    setOutput(result || "공개 IR/SEC 수집 결과를 확인하지 못했습니다.");
    if (result?.storage?.relative_path && elements.publicIrSecUrl) {
      elements.publicIrSecUrl.value = "";
    }
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.publicIrSecStatusButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("공개 IR/SEC 저장 상태 조회 중", [
    "저장 manifest 확인",
    "본문 보강 필요 자료 집계",
    "최근 수집 자료 표시",
  ]);
  try {
    const result = await fetchPublicIrSecStatus(token(), 12);
    setOutput(result || "공개 IR/SEC 상태를 확인하지 못했습니다.");
  } catch (error) {
    setError(error);
  }
});

elements.researchAutomationButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("전체 리서치 자동화 실행 중", [
    "신한·네이버 리서치 캐시 확인",
    "RAG 문서 색인 갱신",
    "보유/관심 종목 Dossier 합성",
    "일일 브리핑 저장",
  ]);
  try {
    const result = await runResearchAutomation(token(), { limit: 30, saveResult: true });
    setOutput(result || "전체 자동화 실행 결과를 확인하지 못했습니다.");
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.todayResearchUpdateButton?.addEventListener("click", async () => {
  try {
    await runTodayResearchUpdate();
  } catch (error) {
    setError(error);
  }
});

function renderNaverResearchStatusText(result) {
  if (!result) {
    return "네이버 리서치 상태 응답이 없습니다.";
  }
  const pdfCounts = result.pdf_extraction_counts || {};
  const priorityCounts = result.priority_counts || {};
  const marketJournal = result.market_close_journal || {};
  const duplicateArchive = result.duplicate_archive || {};
  return [
    "## 네이버 리서치 자동 수집 상태",
    "",
    `- 전체 캐시: ${result.entry_count || 0}건`,
    `- RAG 활성: ${result.active_rag_count || 0}건`,
    `- 저장 파일: ${result.stored_file_count || 0}건`,
    `- 캐시 전용: ${result.cache_only_count || 0}건`,
    `- 저장 파일 누락: ${result.missing_storage_count || 0}건`,
    `- PDF 구조화: 성공 ${pdfCounts.success || 0}건 · 미분석 ${pdfCounts.unknown || 0}건 · PDF 없음 ${pdfCounts.no_pdf || 0}건 · 실패 ${pdfCounts.failed || 0}건`,
    `- 보유/관심 우선 항목: ${priorityCounts["보유/관심"] || 0}건`,
    `- 중복 시장일지 후보: ${duplicateArchive.duplicate_candidate_count || 0}건 (${duplicateArchive.policy || "soft_archive"})`,
    "",
    "## 국내 마감 시황 시장일지",
    "",
    `- 자동 반영: ${marketJournal.enabled ? "사용" : "중지"}`,
    `- 실행 시간: ${marketJournal.daily_time || "08:30"}`,
    `- 마지막 실행: ${marketJournal.last_run_at || "없음"}`,
    `- 마지막 리포트: ${marketJournal.source_title || "없음"}`,
    `- 리포트 발행일: ${marketJournal.source_published_at || "미확인"}`,
  ].join("\n");
}

function renderMarketCloseJournalDigest(result) {
  const entries = Array.isArray(result?.entries) ? result.entries : [];
  const latest = entries
    .filter((entry) => entry?.market === "KR" || entry?.market === "ALL" || entry?.market === "MARKET-KR")
    .sort((a, b) => String(b.session_date || "").localeCompare(String(a.session_date || "")))[0]
    || entries.sort((a, b) => String(b.session_date || "").localeCompare(String(a.session_date || "")))[0];
  if (!latest) {
    return [
      "## 시장일지 화면 연결",
      "",
      "- 최근 시장일지: 아직 표시할 항목이 없습니다.",
      "- 입력 구분: 미확인 · 시장일지 데이터가 들어오면 자동 반영/수동 입력 여부를 표시합니다.",
      "- 다음 조치: `시황 시장일지 반영`을 실행하면 이곳에 최신 항목이 나타납니다.",
    ].join("\n");
  }
  const focus = Array.isArray(latest.auto_utilization_focus)
    ? latest.auto_utilization_focus.slice(0, 3)
    : [];
  const implications = Array.isArray(latest.interest_implications)
    ? latest.interest_implications.slice(0, 3)
    : [];
  const sourceOrigin = latest.source_origin === "naver_research_auto" ? "자동 반영" : "수동 입력";
  const sourceTitle = latest.source_title || latest.source_provider || "출처 제목 미확인";
  return [
    "## 시장일지 화면 연결",
    "",
    `- 최근 반영: ${latest.market || "시장"} ${latest.session_date || "날짜 미확인"}`,
    `- 입력 구분: ${sourceOrigin} · ${sourceTitle}`,
    `- 장세: ${latest.regime || "미확인"} · 심리: ${latest.sentiment || "미확인"} · 리스크: ${latest.risk_level || "미확인"}`,
    focus.length ? `- 자동 활용 초점: ${focus.join(" / ")}` : "- 자동 활용 초점: 미확인",
    implications.length ? `- 보유/관심 영향: ${implications.join(" / ")}` : "- 보유/관심 영향: 아직 연결 단서가 없습니다.",
  ].join("\n");
}

function renderNaverMarketCloseTaskStatusText(result) {
  if (!result) {
    return "## 08:30 자동 작업 로그\n\n- 상태 응답이 없습니다.";
  }
  const state = result.state || {};
  const log = result.task_log || {};
  const duplicateArchive = result.duplicate_archive || {};
  const recentLines = Array.isArray(log.recent_lines) ? log.recent_lines.slice(-5) : [];
  return [
    "## 08:30 자동 작업 로그",
    "",
    `- 작업 상태: ${result.status || "미확인"} · 다음 조치: ${result.next_action || "확인 필요"}`,
    `- 작업 이름: ${result.scheduled_task_name || "미확인"}`,
    `- 실행 시간: ${result.daily_time || "08:30"} · 오늘 실행 필요: ${result.due_now ? "예" : "아니오"}`,
    `- 마지막 실행: ${state.last_run_at || "없음"}`,
    `- 마지막 반영 리포트: ${state.source_title || "없음"}`,
    `- 로그 파일: ${log.exists ? "확인됨" : "아직 없음"} (${log.line_count || 0}줄)`,
    `- 중복 시장일지 후보: ${duplicateArchive.duplicate_candidate_count || 0}건`,
    recentLines.length ? "" : "",
    ...(
      recentLines.length
        ? ["최근 로그:", ...recentLines.map((line) => `- ${line}`)]
        : ["최근 로그: 아직 표시할 로그가 없습니다."]
    ),
  ].join("\n");
}

async function readOptionalWithTimeout(label, promise, timeoutMs, errors = []) {
  try {
    return await withTimeout(promise, timeoutMs, `${label} 응답이 지연되었습니다.`);
  } catch (error) {
    errors.push(`${label}: ${error?.message || error}`);
    return null;
  }
}

function renderNaverMarketJournalSmokeStatus({ result = null, status = null, journal = null, taskStatus = null, errors = [] } = {}) {
  const statusText = status
    ? renderNaverResearchStatusText(status)
    : [
        "## 국내 마감 시황 시장일지",
        "",
        "- 상태: 스모크 검증용 캐시 확인",
        "- 자동 반영: 실제 저장 호출은 건너뛰고 연결 상태만 확인했습니다.",
        "- 다음 조치: 운영 실행에서는 `시황 시장일지 반영` 버튼이 저장까지 수행합니다.",
      ].join("\n");
  const taskText = taskStatus
    ? renderNaverMarketCloseTaskStatusText(taskStatus)
    : [
        "## 08:30 자동 작업 로그",
        "",
        "- 작업 상태: 캐시 확인",
        "- 작업 이름: 국내 주식 마감 시황",
        "- 최근 로그: 스모크 검증에서는 지연된 백엔드 조회를 생략할 수 있습니다.",
      ].join("\n");
  const journalText = journal
    ? renderMarketCloseJournalDigest(journal)
    : [
        "## 시장일지 화면 연결",
        "",
        "- 최근 시장일지: 캐시 확인 중",
        "- 입력 구분: 스모크 검증 · 실제 저장은 운영 클릭에서 수행합니다.",
        "- 다음 조치: 저장이 필요한 경우 스모크 모드가 아닌 일반 화면에서 다시 실행하세요.",
      ].join("\n");
  return [
    statusText,
    taskText,
    journalText,
    errors.length ? `## 지연/오류\n\n${errors.map((item) => `- ${item}`).join("\n")}` : "",
    "```json",
    JSON.stringify(result || { status: "smoke_cached", module: "naver_market_close_journal_refresh", save_result: false }, null, 2),
    "```",
  ].filter(Boolean).join("\n\n");
}

function renderNaverResearchSmokeStatus({ result = null, journal = null, taskStatus = null, errors = [] } = {}) {
  const statusText = result
    ? renderNaverResearchStatusText(result)
    : [
        "## 네이버 리서치 자동 수집 상태",
        "",
        "- 상태: 스모크 검증용 캐시 확인",
        "- 중복 시장일지 후보: 확인 생략 (soft_archive)",
        "- 다음 조치: 운영 조회에서는 캐시/RAG/시장일지 상태를 최신 값으로 다시 확인합니다.",
        "",
        "## 국내 마감 시황 시장일지",
        "",
        "- 자동 반영: 스모크 검증 중",
        "- 실행 시간: 08:30",
      ].join("\n");
  const taskText = taskStatus
    ? renderNaverMarketCloseTaskStatusText(taskStatus)
    : [
        "## 08:30 자동 작업 로그",
        "",
        "- 작업 상태: 캐시 확인",
        "- 작업 이름: 국내 주식 마감 시황",
        "- 최근 로그: 스모크 검증에서는 장시간 대기 없이 연결 여부만 확인합니다.",
      ].join("\n");
  const journalText = journal
    ? renderMarketCloseJournalDigest(journal)
    : [
        "## 시장일지 화면 연결",
        "",
        "- 최근 시장일지: 캐시 확인 중",
        "- 입력 구분: 스모크 검증 · 저장된 시장일지 화면 연결만 확인합니다.",
        "- 다음 조치: 일반 조회에서 최신 시장일지 내용을 다시 불러오세요.",
      ].join("\n");
  return [
    statusText,
    taskText,
    journalText,
    errors.length ? `## 지연/오류\n\n${errors.map((item) => `- ${item}`).join("\n")}` : "",
  ].filter(Boolean).join("\n\n");
}

elements.naverResearchStatusButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("네이버 리서치 상태 조회 중", [
    "캐시/RAG 저장 건수 확인",
    "PDF 구조화 분석 상태 집계",
    "08:30 시장일지 자동 반영 상태 확인",
  ]);
  const smokeMode = isClickSmokeMode();
  const errors = [];
  if (smokeMode) {
    setOutput(renderNaverResearchSmokeStatus());
  }
  const [result, journal, taskStatus] = smokeMode
    ? await Promise.all([
        readOptionalWithTimeout("네이버 리서치 상태", fetchNaverResearchStatus(token()), 8000, errors),
        readOptionalWithTimeout("시장일지 화면 연결", fetchMarketCloseJournal(token(), "KR"), 5000, errors),
        readOptionalWithTimeout("08:30 자동 작업 로그", fetchNaverMarketCloseTaskStatus(token(), 20), 5000, errors),
      ])
    : [
        await readOptionalWithTimeout("네이버 리서치 상태", fetchNaverResearchStatus(token()), 30000, errors),
        await readOptionalWithTimeout("시장일지 화면 연결", fetchMarketCloseJournal(token(), "KR"), 15000, errors),
        await readOptionalWithTimeout("08:30 자동 작업 로그", fetchNaverMarketCloseTaskStatus(token(), 20), 15000, errors),
      ];
  const statusText = result
    ? renderNaverResearchStatusText(result)
    : [
        "## 네이버 리서치 자동 수집 상태",
        "",
        "- 상태: 확인 지연",
        "- 중복 시장일지 후보: 확인 지연 (soft_archive)",
        "- 다음 조치: 백엔드 상태가 안정되면 다시 조회하세요.",
      ].join("\n");
  const taskText = taskStatus
      ? renderNaverMarketCloseTaskStatusText(taskStatus)
      : [
        "## 08:30 자동 작업 로그",
        "",
        "- 작업 상태: 확인 지연",
        "- 작업 이름: 국내 주식 마감 시황",
        "- 최근 로그: 백엔드 응답 지연으로 이번 조회에서는 생략했습니다.",
      ].join("\n");
  const journalText = journal
    ? renderMarketCloseJournalDigest(journal)
    : [
        "## 시장일지 화면 연결",
        "",
        "- 최근 시장일지: 확인 지연",
        "- 입력 구분: 확인 지연 · 시장일지 응답이 오면 자동 반영/수동 입력 여부를 표시합니다.",
        "- 다음 조치: `시황 시장일지 반영` 또는 상태 조회를 다시 실행하세요.",
      ].join("\n");
  setOutput(
    [
      statusText,
      taskText,
      journalText,
      errors.length ? `## 지연/오류\n\n${errors.map((item) => `- ${item}`).join("\n")}` : "",
      result ? `\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\`` : "",
    ].filter(Boolean).join("\n\n")
  );
});

elements.naverResearchRepairButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("네이버 리서치 정리 중", [
    "새 파서로 제목/증권사 메타데이터 재확인",
    "보유/관심 우선순위 재계산",
    "PDF 구조화 신호 백필",
    "캐시 상태 재집계",
  ]);
  try {
    const smokeMode = isClickSmokeMode();
    const result = await repairNaverResearchCache(token(), {
      pdfBackfillLimit: smokeMode ? 0 : 30,
      refreshMetadata: !smokeMode,
      saveResult: false,
      archiveDuplicates: true,
    });
    const status = await fetchNaverResearchStatus(token());
    const journal = await fetchMarketCloseJournal(token(), "KR");
    const taskStatus = await fetchNaverMarketCloseTaskStatus(token(), 20);
    const duplicateArchive = result?.duplicate_archive || {};
    const repairSummary = [
      "## 네이버 리서치 캐시 정리 완료",
      "",
      `- 리서치 캐시 정리: 메타데이터 ${formatNumber(result?.metadata_updated_count || 0)}건 / 저장 보강 ${formatNumber(result?.missing_storage_saved_count || 0)}건`,
      `- PDF 신호 백필: ${formatNumber(result?.pdf_backfilled_count || 0)}건`,
      `- 중복 리포트/시장일지 후보: ${formatNumber(duplicateArchive.duplicate_candidate_count || 0)}건 · 정책 ${duplicateArchive.policy || "soft_archive"}`,
      "- 소프트 보관 정책: 중복/레거시 자료는 삭제하지 않고 숨김/보관으로 처리합니다.",
    ].join("\n");
    setOutput(`${repairSummary}

${renderNaverResearchStatusText(status)}

${renderNaverMarketCloseTaskStatusText(taskStatus)}

${renderMarketCloseJournalDigest(journal)}

\`\`\`json
${JSON.stringify(result, null, 2)}
\`\`\``);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.naverMarketJournalButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("국내 마감 시황 시장일지 반영 중", [
    "네이버 시황정보 최신 리포트 확인",
    "저작권 안전 요약/메타데이터 구성",
    "시장일지 저장",
    "상태 카드 갱신",
  ]);
  try {
    const smokeMode = isClickSmokeMode();
    if (smokeMode) {
      const errors = [];
      const [status, journal, taskStatus] = await Promise.all([
        readOptionalWithTimeout("네이버 리서치 상태", fetchNaverResearchStatus(token()), 8000, errors),
        readOptionalWithTimeout("시장일지 화면 연결", fetchMarketCloseJournal(token(), "KR"), 5000, errors),
        readOptionalWithTimeout("08:30 자동 작업 로그", fetchNaverMarketCloseTaskStatus(token(), 20), 5000, errors),
      ]);
      setOutput(renderNaverMarketJournalSmokeStatus({
        result: { status: "smoke_cached", module: "naver_market_close_journal_refresh", save_result: false },
        status,
        journal,
        taskStatus,
        errors,
      }));
      return;
    }
    const result = await refreshNaverMarketCloseJournal(token(), true);
    const status = await fetchNaverResearchStatus(token());
    const journal = await fetchMarketCloseJournal(token(), "KR");
    const taskStatus = await fetchNaverMarketCloseTaskStatus(token(), 20);
    setOutput(`${renderNaverResearchStatusText(status)}\n\n${renderNaverMarketCloseTaskStatusText(taskStatus)}\n\n${renderMarketCloseJournalDigest(journal)}\n\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\``);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.storageCleanupButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("저장 데이터 중복 리뷰 생성 중", [
    "저장 manifest와 원문 텍스트 점검",
    "source_url/content_hash 같은 자료 묶기",
    "제목·본문 유사 자료 묶기",
    "Dossier 재합성 우선순위 정리",
  ]);
  try {
    const result = await runStorageDuplicateReview(token(), { limit: 80, saveResult: true });
    setOutput(result || "저장 데이터 정리 결과를 확인하지 못했습니다.");
    const data = formDataObject(elements.memoryForm);
    const key = await resolveMemoryLookupKey(data.ticker || activeTicker || DEFAULT_TICKER_DISPLAY);
    const memoryResponse = await fetchResearchMemoryFiles(token(), key, memoryListFetchOptions());
    renderMemoryList(memoryResponse, key);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.dedupedDossierRefreshButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("중복 종목 Dossier 갱신 중", [
    "중복 리뷰 우선순위 종목 선별",
    "대표 자료 기준 Dossier 재합성",
    "최신 투자 논거 스냅샷 갱신",
    "자동화 상태 반영",
  ]);
  try {
    const result = await runDedupedDossierRefresh(token(), { limit: 8, saveResult: true });
    setOutput(result || "Dossier 갱신 결과를 확인하지 못했습니다.");
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.researchAutomationStatusButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("리서치 자동화 상태 점검 중", [
    "수집·중복 제거 연결 확인",
    "RAG 색인과 Dossier 상태 확인",
    "일일 브리핑·대시보드 전달 상태 정리",
  ]);
  try {
    const result = await fetchResearchAutomationStatus(token());
    setOutput(result || "리서치 자동화 상태를 확인하지 못했습니다.");
  } catch (error) {
    setError(error);
  }
});

function codeKnowledgeGraphOutput(result = {}) {
  const summary = result.summary || {};
  const flows = Array.isArray(result.flows) ? result.flows : [];
  const layerLines = Object.entries(summary.files_by_layer || {})
    .map(([label, count]) => `- ${label}: ${count}개`)
    .join("\n");
  const typeLines = Object.entries(summary.nodes_by_type || {})
    .map(([label, count]) => `- ${label}: ${count}개`)
    .join("\n");
  const flowLines = flows.map((flow) => {
    const status = flow.status === "ok" ? "정상" : "확인 필요";
    const files = (flow.sample_files || []).slice(0, 4).join(", ");
    return `- ${flow.label || flow.id}: ${status} · 연결 파일 ${flow.matched_file_count || 0}개${files ? ` · 예: ${files}` : ""}`;
  });
  const signals = Array.isArray(result.operation_signals) ? result.operation_signals : [];
  const signalSummary = result.signal_summary || {};
  const readiness = result.operation_readiness || {};
  const readinessScore = Number(readiness.score);
  const readinessText = Number.isFinite(readinessScore) ? `${readinessScore.toFixed(1)}%` : "n/a";
  const readinessTarget = Number(readiness.target_score || 95);
  const signalLines = signals.map((signal) => {
    const status = signal.status === "ok" ? "정상" : signal.status === "error" ? "오류" : "주의";
    const nextAction = signal.next_action ? ` · 다음: ${signal.next_action}` : "";
    return `- ${signal.label || signal.id}: ${status} · ${signal.message || "상태 메시지 없음"}${nextAction}`;
  });
  return [
    "# 시스템 구조 맵",
    "",
    result.message || "코드 지식 그래프 상태를 확인했습니다.",
    "",
    `- 생성 시각: ${result.generated_at || "미생성"}`,
    `- 노드/엣지: ${formatNumber(result.node_count || 0)}개 / ${formatNumber(result.edge_count || 0)}개`,
    `- 저장 위치: ${result.storage_path || "확인 안 됨"}`,
    "",
    "## 운영 흐름 연결",
    ...(flowLines.length ? flowLines : ["- 표시할 운영 흐름이 없습니다."]),
    "",
    "## 운영 준비도",
    `${readinessText} / 목표 ${readinessTarget.toFixed(0)}% · ${readiness.label || "상태 미확인"}`,
    readiness.next_action ? `다음 조치: ${readiness.next_action}` : "",
    "",
    "## 운영 주의 신호",
    `정상 ${formatNumber(signalSummary.ok || 0)}개 · 주의 ${formatNumber(signalSummary.warning || 0)}개 · 오류 ${formatNumber(signalSummary.error || 0)}개`,
    ...(signalLines.length ? signalLines : ["- 표시할 운영 신호가 없습니다."]),
    "",
    "## 파일 계층",
    layerLines || "- 계층 요약 없음",
    "",
    "## 노드 유형",
    typeLines || "- 노드 유형 요약 없음",
    "",
    "다음 구조 변경 전에는 `python tools\\check_code_knowledge_graph.py --strict`로 영향 범위를 먼저 확인하세요.",
  ].join("\n");
}

elements.codeKnowledgeGraphButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("시스템 구조 맵 조회 중", [
    "코드 지식 그래프 읽기",
    "운영 흐름 연결 상태 확인",
    "추천·저장품질·포트폴리오 운영 신호 요약",
    "파일 계층과 API/버튼 관계 요약",
  ]);
  try {
    const result = await fetchCodeKnowledgeGraph(token());
    setOutput(codeKnowledgeGraphOutput(result));
  } catch (error) {
    setError(error);
  }
});

elements.ragBackfillButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("RAG 색인 갱신 중", [
    "저장 manifest 읽기",
    "Markdown 본문 요약 색인",
    "품질 검색 준비",
  ]);
  try {
    const result = await backfillRagMemoryDocuments(token());
    setOutput(result || "RAG 색인 갱신 결과를 확인하지 못했습니다.");
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.ocrReprocessButton?.addEventListener("click", async () => {
  syncApiBaseUrl();
  const includeArchived = Boolean(
    elements.memoryForm?.querySelector('input[name="includeArchived"]')?.checked
  );
  startOutputLoading("저장 데이터 OCR 재처리 중", [
    "OCR 런타임과 언어팩 확인",
    "본문 0자/미연결 첨부 후보 선별",
    "Markdown/JSON/Manifest 갱신",
    "RAG 색인 다시 반영",
  ]);
  try {
    const result = await reprocessResearchMemoryOcr(token(), {
      includeArchived,
      force: false,
      saveResult: true,
    });
    setOutput(result || "OCR 재처리 결과를 확인하지 못했습니다.");
    const data = formDataObject(elements.memoryForm);
    const lookupKey = await resolveMemoryLookupKey(data.ticker || activeTicker || "POLICY");
    const memoryResponse = await fetchResearchMemoryFiles(token(), lookupKey, memoryListFetchOptions());
    renderMemoryList(memoryResponse, lookupKey);
    await runSecondaryRefresh("저장 보고서 수 새로고침", () => refreshStatus(false));
  } catch (error) {
    setError(error);
  }
});

elements.manifestButton.addEventListener("click", async () => {
  syncApiBaseUrl();
  startOutputLoading("전체 저장 목록 조회 중", [
    "저장 Manifest 읽기",
    "최근 보고서 목록 정리",
    "결과창에 표시",
  ]);
  try {
    const manifest = await fetchResearchManifest(token());
    setOutput(manifest);
  } catch (error) {
    setError(error);
  }
});

elements.tickerCacheButton.addEventListener("click", () => {
  loadTickerCache().catch(setError);
});

initializeEditableLists();
applyKoreanInputDefaults();
lastTodayResearchUpdate = readStoredTodayResearchUpdate();
syncTickerInputs("", { allowEmpty: true, skipDashboardInvalidation: true });
renderDashboardEmptyState();
renderDashboardTickerPicker();
updateChecklistProgress();

async function initializeConsole() {
  startOutputLoading("초기 데이터를 불러오는 중", [
    "백엔드 상태 확인",
    "저장 포트폴리오 불러오기",
    "관심종목/섹터 불러오기",
    "대시보드 후보 구성",
  ]);
  const steps = [
    refreshStatus(false),
    refreshPortfolioStore(true),
    refreshInterestList(true),
  ];
  const results = await Promise.allSettled(steps);
  const failed = results.find((result) => result.status === "rejected");
  if (failed) {
    setError(failed.reason);
    return;
  }
  renderDashboardEmptyState();
  renderDashboardTickerPicker();
  setOutput("대시보드 준비 완료\n\n티커 입력칸은 비워두었습니다. 최근 사용/보유/관심종목/섹터에서 종목을 선택하거나 회사명을 직접 입력해 조회하세요.");
}

initializeConsole();

function compactOutputText(text, maxLength = 220) {
  const cleaned = cleanOutputText(text);
  if (!cleaned) {
    return "요약 없음";
  }
  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength - 3)}...` : cleaned;
}

function cleanOutputText(text) {
  return String(text || "")
    .replace(/\[네이버 금융 리서치 자동 수집\]\s*/g, "")
    .replace(/DataSourceType\.[A-Z_]+\s*\/\s*[^:：]+[:：]\s*/g, "")
    .replace(/\b(source_url|source_type|source_file|source_relative_path|content_hash|json_relative_path|json_file_name|latest_thesis_snapshot|rag_memory_document)\b[^|\n]*/gi, "")
    .replace(/태그:\s*(?:auto_[^,\n]+|naver_[^,\n]+|growth|market|risk|sector|macro|flows|earnings|valuation|margin|policy|rates|file_input)(?:,\s*)*/gi, "")
    .replace(/분류:\s*[^ \n]+\s*/g, "")
    .replace(/제목:\s*/g, "")
    .replace(/분류 근거:\s*[^ \n]+\s*/g, "")
    .replace(/증권사:\s*[^ \n]+\s*/g, "")
    .replace(/종목명:\s*[^ \n]+\s*/g, "")
    .replace(/종목코드:\s*[^ \n]+\s*/g, "")
    .replace(/발행일:\s*\d{4}-\d{2}-\d{2}\s*/g, "")
    .replace(/저장 범위:\s*[^ \n]+\s*/g, "")
    .replace(/원문 링크:\s*\S+\s*/g, "")
    .replace(/PDF 링크:\s*\S+\s*/gi, "")
    .replace(/해당 없음/g, "")
    .replace(/\s+없음\s+없음/g, " ")
    .replace(/\s+활용\s+\.\.\./g, "...")
    .replace(/강세는\s+강세는/g, "강세는")
    .replace(/약세는\s+약세는/g, "약세는")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanDocumentPreviewText(text) {
  const exactNoiseLines = new Set([
    "로그인",
    "회원가입",
    "뉴스",
    "전체기사",
    "검색",
    "홈",
    "오피니언",
    "반도체",
    "디스플레이",
    "배터리",
    "방산ㆍ에너지",
    "바이오",
    "완성품",
    "금융",
    "ITㆍ게임",
    "통신",
    "모빌리티",
    "생활경제",
    "헬스케어",
    "부동산",
    "테크",
    "마켓",
    "영상",
    "포토",
    "오늘의 주요뉴스",
    "이 시각 주요뉴스",
    "기사목록",
    "본문듣기",
    "닫기",
    "공유",
    "스크랩",
    "인쇄",
    "메일",
    "중국산업동향",
    "전자엔지니어",
    "컨콜전문",
    "회사소개",
    "광고문의",
    "개인정보처리방침",
  ]);
  const noisePattern =
    /(source_url|source_type|source_file|content_hash|json_file_name|원문 링크|PDF 링크|관련기사|추천기사|인기기사|많이 본 뉴스|본문 바로가기|전체 메뉴|댓글|공유하기|구독|이 기사를 공유|기사제보|무단전재|재배포 금지|copyright|all rights reserved|좋아요|북마크|프린트|목록|광고|newsletter|subscribe)/i;
  const seen = new Set();
  return String(text || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.replace(/[ \u00a0]+/g, " ").replace(/\t+/g, "\t").trim())
    .filter((line) => {
      if (!line || line.length <= 1) return false;
      if (/^[-=─_]{3,}$/.test(line)) return false;
      if (exactNoiseLines.has(line)) return false;
      if (noisePattern.test(line)) return false;
      if (/^(다음|이전)\s*(기사|뉴스)/.test(line)) return false;
      if (/^(AD|Advertisement|Sponsored)$/i.test(line)) return false;
      if (/^https?:\/\//i.test(line)) return false;
      const key = line.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanStoredReportContent(text) {
  const noisyLinePattern =
    /(DataSourceType\.|source_url|source_type|source_file|source_relative_path|content_hash|json_relative_path|json_file_name|latest_thesis_snapshot|rag_memory_document|auto_ingested|naver_research|원문 링크:|PDF 링크:)/i;
  return String(text || "")
    .split(/\r?\n/)
    .map((line) =>
      line
        .replace(/DataSourceType\.[A-Z_]+\s*\/\s*[^:：]+[:：]\s*/g, "")
        .replace(/\s+없음\s+없음/g, " ")
        .trimEnd()
    )
    .filter((line) => !noisyLinePattern.test(line))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatBulletList(items, mapper = (item) => item, empty = "표시할 항목이 없습니다.") {
  if (!Array.isArray(items) || items.length === 0) {
    return [`- ${empty}`];
  }
  return items.map((item) => `- ${mapper(item)}`);
}

function formatFileProcessingLines(fileProcessing) {
  if (!fileProcessing) {
    return ["- 첨부 파일 없음"];
  }
  const profile = fileProcessing.extraction_profile || {};
  const quality = Number(fileProcessing.extraction_quality);
  const qualityText = Number.isFinite(quality) ? `${Math.round(quality * 100)}%` : "미평가";
  const qualityLabel = describeExtractionQuality(fileProcessing);
  const charCount = Number(profile.char_count || fileProcessing.extraction_char_count || 0);
  const previewText = String(fileProcessing.extraction_preview || "").trim();
  const lineCount = Number(profile.line_count || 0) || (previewText ? previewText.split(/\r?\n/).filter((line) => line.trim()).length : 0);
  const numericTokenCount = Number(profile.numeric_token_count || 0);
  const tableLineCount = Number(profile.table_like_line_count || 0);
  const qualityGuide = buildExtractionQualityGuide(fileProcessing);
  const lines = [
    `- 처리 판정: ${qualityLabel}`,
    `- 파일명: ${fileProcessing.file_name || "파일명 없음"}`,
    `- 문서 유형: ${fileProcessing.document_type || "미확인"}`,
    `- 추출 상태: ${fileProcessing.text_extraction || "처리 상태 없음"}`,
    `- 추출 품질: ${qualityText} / 본문 ${formatNumber(charCount)}자 / 줄 ${formatNumber(lineCount)}개 / 숫자 ${formatNumber(numericTokenCount)}개`,
    `- 구조 신호: 표형 줄 ${formatNumber(tableLineCount)}개${profile.used_ocr ? " / OCR 사용" : ""}${profile.truncated ? " / 앞부분만 사용" : ""}`,
    `- 저장 경로: ${fileProcessing.relative_path || "경로 없음"}`,
    `- 분석 활용: ${profile.use_case || qualityGuide.useCase}`,
    `- 다음 조치: ${profile.next_action || qualityGuide.nextAction}`,
  ];
  const warnings = Array.isArray(fileProcessing.extraction_warnings)
    ? fileProcessing.extraction_warnings.filter(Boolean)
    : [];
  if (warnings.length) {
    lines.push(`- 추출 경고: ${warnings.join(" / ")}`);
  }
  if (fileProcessing.extraction_preview) {
    const cleanedPreview = cleanDocumentPreviewText(fileProcessing.extraction_preview);
    if (cleanedPreview) {
      lines.push("", "문서 추출 미리보기", compactOutputText(cleanedPreview, 1200));
    }
  }
  return lines;
}

function buildDocumentExtractionReport(attachment) {
  if (!attachment) {
    return ["- 첨부 파일 없음", "- 분석 활용도: 파일 없이 텍스트 입력 또는 웹사이트 본문만 사용했습니다."];
  }
  const profile = attachment.extraction_profile || {};
  const quality = Number(attachment.extraction_quality);
  const qualityText = Number.isFinite(quality) ? `${Math.round(quality * 100)}%` : "미평가";
  const qualityGuide = buildExtractionQualityGuide(attachment);
  const charCount = Number(profile.char_count || attachment.extraction_char_count || 0);
  const lineCount = Number(profile.line_count || 0);
  const numericTokenCount = Number(profile.numeric_token_count || 0);
  const tableLineCount = Number(profile.table_like_line_count || 0);
  const imageSize = profile.image_size ? ` / 이미지 ${profile.image_size}` : "";
  const processFlags = [
    profile.used_ocr || profile.ocr_available ? `OCR 사용${profile.ocr_language ? `(${profile.ocr_language})` : ""}` : "텍스트 레이어/일반 추출",
    profile.truncated ? "앞부분만 분석" : "저장 범위 전체 반영",
  ];
  const drivers = Array.isArray(profile.quality_drivers)
    ? profile.quality_drivers.filter(Boolean)
    : [];
  const warnings = Array.isArray(attachment.extraction_warnings)
    ? attachment.extraction_warnings.filter(Boolean)
    : [];
  return [
    `- **품질 판정:** ${profile.quality_label || describeExtractionQuality(attachment)} (${qualityText})`,
    `- **분석 활용도:** ${profile.analysis_readiness || "미평가"} · ${profile.use_case || qualityGuide.useCase}`,
    `- **추출 구조:** 본문 ${formatNumber(charCount)}자 · 줄 ${formatNumber(lineCount)}개 · 숫자 ${formatNumber(numericTokenCount)}개 · 표형 줄 ${formatNumber(tableLineCount)}개${imageSize}`,
    `- **OCR 상태:** ${attachmentOcrStatusLine(attachment).replace(/^OCR 상태:\s*/, "")}`,
    `- **처리 방식:** ${processFlags.join(" / ")}`,
    `- **판정 근거:** ${drivers.length ? drivers.join(" / ") : "기본 품질 규칙 적용"}`,
    `- **권장 조치:** ${profile.next_action || qualityGuide.nextAction}`,
    `- **경고:** ${warnings.length ? warnings.join(" / ") : "없음"}`,
  ];
}

function buildExtractionQualityGuide(fileProcessing) {
  const quality = Number(fileProcessing?.extraction_quality);
  const charCount = Number(fileProcessing?.extraction_char_count || 0);
  const documentType = String(fileProcessing?.document_type || "");
  const warningCount = Array.isArray(fileProcessing?.extraction_warnings)
    ? fileProcessing.extraction_warnings.filter(Boolean).length
    : 0;
  if (!charCount) {
    return {
      useCase: "원본 보관 중심",
      nextAction: "PDF/OCR 또는 원문 텍스트를 추가로 넣어 분석 근거를 보강하세요.",
    };
  }
  if (Number.isFinite(quality) && quality >= 0.85 && charCount >= 1200 && !warningCount) {
    return {
      useCase: `${documentType || "문서"} 본문을 RAG와 투자 논거 분석에 바로 사용`,
      nextAction: "저장 데이터에서 관련 종목/섹터와 연결해 리포트 또는 시장일지에 반영하세요.",
    };
  }
  if (charCount >= 400) {
    return {
      useCase: "핵심 문장과 표제 중심으로 분석 가능",
      nextAction: "숫자 표, 목표가, 실적 수치가 빠졌는지 결과 미리보기에서 확인하세요.",
    };
  }
  return {
    useCase: "요약 신호로만 제한 활용",
    nextAction: "본문이 짧아 원문 복사, OCR, 다른 파일 형식 업로드 중 하나로 보강하세요.",
  };
}

function describeExtractionQuality(fileProcessing) {
  if (!fileProcessing) {
    return "첨부 없음";
  }
  const quality = Number(fileProcessing.extraction_quality);
  const charCount = Number(fileProcessing.extraction_char_count || 0);
  const extraction = String(fileProcessing.text_extraction || "").toLowerCase();
  if (extraction.includes("failed") || extraction.includes("error")) {
    return "확인 필요 - 본문 추출 실패";
  }
  if (Number.isFinite(quality)) {
    if (quality >= 0.85) return "좋음 - 분석에 바로 사용 가능";
    if (quality >= 0.55) return "보통 - 핵심 문장 중심으로 사용";
    if (quality > 0) return "낮음 - 원문 확인 병행 필요";
  }
  if (charCount >= 1200) return "좋음 - 충분한 본문 확보";
  if (charCount >= 250) return "보통 - 요약 분석 가능";
  if (charCount > 0) return "낮음 - 본문이 짧아 보강 권장";
  return "본문 없음 - 파일 원문만 저장";
}

function translateLanguage(language) {
  const labels = {
    ko: "한국어",
    ja: "일본어",
    en: "영어",
    zh: "중국어",
    unknown: "미확인",
  };
  return labels[language] || language || "미확인";
}

function buildSourceUrlLines(sourceInfo) {
  if (!sourceInfo) {
    return ["- 웹사이트 입력 없음"];
  }
  const languageLabels = {
    ko: "한국어",
    ja: "일본어",
    en: "영어",
    zh: "중국어",
    unknown: "미확인",
  };
  const translationLabels = {
    not_needed: "한국어 원문",
    local_digest: "한국어 분석용 변환",
    official_korean_summary: "공식 URL 보조 한국어 요약",
    skipped: "원문 유지",
    empty: "본문 없음",
  };
  const status = sourceInfo.status || "처리 상태 미확인";
  const title = sourceInfo.title || "제목 없음";
  const contentType = sourceInfo.content_type || "콘텐츠 유형 미확인";
  const textLength = String(sourceInfo.text || "").trim().length;
  const textStatus = textLength
    ? `본문 ${formatNumber(textLength)}자 추출`
    : "본문 추출 없음";
  const lines = [
    `- 처리 상태: ${status}`,
    `- 제목: ${title}`,
    `- 유형: ${contentType}`,
    `- 본문: ${textStatus}`,
  ];
  if (sourceInfo.language) {
    lines.push(`- 원문 언어: ${languageLabels[sourceInfo.language] || sourceInfo.language}`);
  }
  if (sourceInfo.translation_status) {
    lines.push(
      `- 한국어 처리: ${
        translationLabels[sourceInfo.translation_status] || sourceInfo.translation_status
      }`
    );
  }
  if (sourceInfo.final_url || sourceInfo.source_url) {
    lines.push(`- 주소: ${sourceInfo.final_url || sourceInfo.source_url}`);
  }
  if (sourceInfo.translation_note || sourceInfo.note) {
    lines.push(`- 안내: ${sourceInfo.translation_note || sourceInfo.note}`);
  }
  return lines;
}

function buildCaptureQualityLines(quality) {
  if (!quality) {
    return ["- 품질 상태: 미확인"];
  }
  const warnings = Array.isArray(quality.warnings) ? quality.warnings : [];
  return [
    `- 품질 상태: ${quality.status || "미확인"}`,
    `- 확보 본문 길이: ${formatNumber(quality.text_length || 0)}자`,
    `- 분석 준비도: ${quality.readiness || "미확인"}`,
    `- 웹 추출 상태: ${quality.url_status || "해당 없음"}`,
    ...(warnings.length ? warnings.map((item) => `- 보강 안내: ${item}`) : ["- 보강 안내: 없음"]),
  ];
}

function newsItemTone(item) {
  if (item?.promoted) return "ok";
  if ((item?.capture_quality || {}).status && (item.capture_quality || {}).status !== "정상") return "warning";
  if (item?.review_status === "보류") return "muted";
  return "needs-action";
}

function currentNewsInboxFilter() {
  return elements.newsInboxFilter?.value || "all";
}

function renderNewsInboxFilterSummary(payload) {
  const counts = payload?.filter_counts || {};
  if (!counts || !Object.keys(counts).length) {
    return "";
  }
  return `
    <div class="news-filter-summary">
      <b>전체 ${escapeHtml(formatNumber(counts.all || payload?.count || 0))}</b>
      <span>승격 전 ${escapeHtml(formatNumber(counts.unpromoted || 0))}</span>
      <span>본문 보강 ${escapeHtml(formatNumber(counts.needs_body || 0))}</span>
      <span>URL-only ${escapeHtml(formatNumber(counts.url_only || 0))}</span>
      <span>시장일지 ${escapeHtml(formatNumber(counts.market_journal || 0))}</span>
      <span>품질 확인 ${escapeHtml(formatNumber(counts.quality_issue || 0))}</span>
    </div>
  `;
}

function renderNewsInboxCards(payload) {
  if (!elements.newsInboxList) {
    return;
  }
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!items.length) {
    elements.newsInboxList.innerHTML =
      `${renderNewsInboxFilterSummary(payload)}<div class="news-inbox-empty">현재 필터에 표시할 뉴스가 없습니다. 필터를 전체로 바꾸거나 새 메모/URL을 저장하세요.</div>`;
    return;
  }
  elements.newsInboxList.innerHTML = renderNewsInboxFilterSummary(payload) + items
    .slice(0, 30)
    .map((item) => {
      const tone = newsItemTone(item);
      const quality = item.capture_quality || {};
      const status = item.promoted ? "승격 완료" : item.review_status || "대기";
      const policy = item.copyright_policy?.message || "뉴스 원문 본문은 저장하지 않는 안전 모드";
      const sourceUrl = item.source_url
        ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">원문</a>`
        : "";
      return `
        <article class="news-inbox-card ${escapeHtml(tone)}" data-news-id="${escapeHtml(item.id || "")}">
          <div>
            <span>${escapeHtml(status)} · ${escapeHtml(item.scope_label || item.scope || "일반 뉴스")}</span>
            <strong>${escapeHtml(item.title || "제목 없음")}</strong>
            <p>${escapeHtml(compactOutputText(item.summary || item.input_preview || "", 240))}</p>
            <small>품질 ${escapeHtml(quality.status || "미확인")} · 저장 메모 ${escapeHtml(formatNumber(quality.text_length || 0))}자 · 신뢰도 ${escapeHtml(toPercent(item.confidence))} ${sourceUrl}</small>
            <em>${escapeHtml(policy)}</em>
          </div>
          <div class="news-inbox-actions">
            <button data-news-action="promote" type="button" ${item.promoted ? "disabled" : ""}>저장 데이터로 반영</button>
            <button data-news-action="market_journal" class="secondary" type="button">시장일지로 보내기</button>
            <button data-news-action="hold" class="secondary" type="button">보류</button>
            <button data-news-action="delete" class="secondary danger" type="button">삭제</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderStorageQualitySignalCard(dashboard) {
  const digest = dashboard?.automation_digest || {};
  const documentQuality = dashboard?.document_quality_digest || {};
  const duplicateCount = Number(digest.duplicate_suspected_count || 0);
  const newsUnpromoted = Number(digest.news_unpromoted_count || 0);
  const newsQuality = Number(digest.news_quality_issue_count || 0);
  const latest = documentQuality.latest || {};
  const quality = Number(latest.quality);
  const qualityText = Number.isFinite(quality) ? `${Math.round(quality * 100)}%` : "미평가";
  const tone = duplicateCount || newsQuality ? "warning" : newsUnpromoted ? "needs-action" : "ok";
  const headline = duplicateCount || newsQuality ? "품질 점검 필요" : newsUnpromoted ? "뉴스 승격 대기" : "저장 품질 정상";
  return `
    <article class="dashboard-card storage-quality-signal ${tone}">
      <span>저장 데이터 품질</span>
      <strong>${escapeHtml(headline)}</strong>
      <p>중복 의심 ${escapeHtml(formatNumber(duplicateCount))}개 · 미승격 뉴스 ${escapeHtml(formatNumber(newsUnpromoted))}개 · 뉴스 품질 ${escapeHtml(formatNumber(newsQuality))}개<br />최근 문서 품질 ${escapeHtml(qualityText)}</p>
      <div class="dashboard-card-actions">
        <button data-workflow-action="news" type="button">뉴스 검토</button>
        <button data-workflow-action="storage-quality" class="secondary" type="button">품질 점검</button>
      </div>
    </article>
  `;
}

function formatKoreanResult(value) {
  if (typeof value === "string") {
    return value;
  }
  if (!value) {
    return "결과가 없습니다.";
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "조회된 항목이 없습니다.";
    }
    return value.map((item, index) => formatListItem(item, index)).join("\n\n");
  }

  if (value.module === "news_inbox" || value.module === "news_promotion") {
    const item = value.item || {};
    const qualityLines = buildCaptureQualityLines(item.capture_quality || value.capture?.capture_quality);
    return [
      value.module === "news_promotion" ? `### 뉴스 승격 완료` : `### 뉴스 인박스 저장`,
      ``,
      `- **제목:** ${item.title || "제목 없음"}`,
      `- **분류:** ${item.scope_label || item.scope || "일반 뉴스"}`,
      item.source_url ? `- **원문:** ${item.source_url}` : "",
      `- **중복:** ${value.duplicate_check?.is_duplicate_suspected ? "중복 의심" : "신규"}`,
      `- **신뢰도:** ${toPercent(item.confidence)}`,
      item.copyright_policy?.message ? `- **저장 정책:** ${item.copyright_policy.message}` : "",
      item.promoted_storage?.relative_path ? `- **승격 저장:** ${item.promoted_storage.relative_path}` : "",
      ``,
      `### 요약`,
      compactOutputText(item.summary || "", 520),
      ``,
      `### 본문 품질`,
      ...qualityLines,
      ``,
      `### 태그`,
      (item.tags || []).join(", ") || "태그 없음",
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (entry) => compactOutputText(entry, 180), "추가 액션이 없습니다."),
      value.module === "news_inbox" ? "- 필요하면 `최근 뉴스 승격` 버튼으로 저장 데이터/RAG 메모리에 반영하세요." : "",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "news_inbox_list") {
    const items = value.items || [];
    renderNewsInboxCards(value);
    return [
      `### 뉴스 인박스`,
      ``,
      `- **전체:** ${formatNumber(value.count || 0)}개`,
      `- **현재 필터:** ${value.filter || "all"} / 표시 ${formatNumber(value.filtered_count || items.length)}개`,
      `- **미승격:** ${formatNumber(value.unpromoted_count || 0)}개`,
      `- **품질 확인 필요:** ${formatNumber(value.quality_issue_count || 0)}개`,
      `- **본문 보강 필요:** ${formatNumber(value.filter_counts?.needs_body || 0)}개`,
      `- **URL-only:** ${formatNumber(value.filter_counts?.url_only || 0)}개`,
      ``,
      `### 최근 뉴스`,
      ...formatBulletList(
        items,
        (item) =>
          `${item.promoted ? "[승격]" : "[대기]"} **${item.title || "제목 없음"}** · ${
            item.scope_label || item.scope || "일반 뉴스"
          } · ${item.capture_quality?.status || "품질 미확인"}\n  ${compactOutputText(
            item.summary || "",
            220
          )}`,
        "저장된 뉴스가 없습니다."
      ),
      ``,
      `### 사용법`,
      "- 뉴스는 여기서 먼저 중복과 품질을 확인합니다.",
      "- 뉴스/기사 원문 본문은 저장하지 않고 링크와 짧은 메모 중심으로 보관합니다.",
      "- 투자 논거로 쓸 자료만 `최근 뉴스 승격`으로 저장 데이터에 반영합니다.",
    ].join("\n");
  }

  if (value.module === "news_inbox_action") {
    const item = value.item || {};
    const journal = value.market_journal || {};
    const journalEntry = journal.entry || item.market_journal_entry || {};
    const journalStorage = journal.storage || item.market_journal_storage || {};
    return [
      `### 뉴스 처리 완료`,
      ``,
      `- **처리:** ${value.message || value.action || "완료"}`,
      item.title ? `- **제목:** ${item.title}` : value.item_id ? `- **뉴스 ID:** ${value.item_id}` : "",
      item.scope_label ? `- **분류:** ${item.scope_label}` : "",
      item.review_status ? `- **상태:** ${item.review_status}` : "",
      journalEntry.session_date
        ? `- **시장일지 반영:** ${journalEntry.market || "시장"} ${journalEntry.session_date} · ${journalEntry.regime || "판정 미확정"}`
        : "",
      journalStorage.relative_path ? `- **시장일지 저장:** ${journalStorage.relative_path}` : "",
      ``,
      `### 다음 액션`,
      journalEntry.session_date
        ? "- 시장일지 화면에서 누적 기록을 조회해 오늘 장세 판단에 반영됐는지 확인하세요."
        : "- 뉴스 인박스를 다시 조회해 현재 상태를 확인하세요.",
      "- 종목 논거로도 쓸 자료라면 `승격`을 눌러 저장 데이터/RAG에도 반영하세요.",
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "storage_quality_dashboard") {
    const bodyMissingItems = value.body_missing_items || [];
    const ocrNeededItems = value.ocr_needed_items || [];
    const publicIrSecItems = value.public_ir_sec_items || [];
    return [
      `### 저장 데이터 품질 대시보드`,
      ``,
      `- **전체 저장 문서:** ${formatNumber(value.manifest_count || 0)}개`,
      `- **정상 문서:** ${formatNumber(value.normal_count || 0)}개`,
      `- **본문 보강 필요:** ${formatNumber(value.body_missing_count || 0)}개`,
      `- **OCR 필요:** ${formatNumber(value.ocr_needed_count || 0)}개`,
      `- **공개 IR/SEC:** ${formatNumber(value.public_ir_sec_count || 0)}개 · 본문 보강 ${formatNumber(value.public_ir_sec_needs_body_count || 0)}개`,
      `- **보관 문서:** ${formatNumber(value.archived_count || 0)}개`,
      `- **중복/레거시 의심:** ${formatNumber(value.legacy_or_duplicate_count || 0)}개`,
      bodyMissingItems.length ? `` : "",
      bodyMissingItems.length ? `### 본문 보강 대상` : "",
      ...bodyMissingItems.map(
        (item) =>
          `- ${displayCompanyName(item)} · ${item.file_name || item.relative_path || "파일 미확인"} · ${item.quality_status || "본문 보강 필요"}`
      ),
      publicIrSecItems.length ? `` : "",
      publicIrSecItems.length ? `### 공개 IR/SEC 품질` : "",
      ...publicIrSecItems.map(
        (item) =>
          `- ${item.file_name || item.relative_path || "파일 미확인"} · ${item.quality_status || "품질 미확인"}`
      ),
      ocrNeededItems.length ? `` : "",
      ocrNeededItems.length ? `### OCR 보강 대상` : "",
      ...ocrNeededItems.map(
        (item) =>
          `- ${displayCompanyName(item)} · ${item.file_name || item.relative_path || "파일 미확인"} · ${item.ocr_status || "OCR 필요"}`
      ),
      ``,
      `### 뉴스 인박스`,
      `- 승격 전 ${formatNumber(value.news_filter_counts?.unpromoted || 0)}개`,
      `- 본문 보강 ${formatNumber(value.news_filter_counts?.needs_body || 0)}개`,
      `- URL-only ${formatNumber(value.news_filter_counts?.url_only || 0)}개`,
      `- 시장일지 후보 ${formatNumber(value.news_filter_counts?.market_journal || 0)}개`,
      ``,
      `### 저장 정책`,
      value.policy?.message || "뉴스 원문 본문은 저장하지 않습니다.",
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180)),
    ].join("\n");
  }

  if (value.module === "research_memory_ocr_reprocess") {
    const runtime = value.ocr_runtime || {};
    const limits = runtime.limits || {};
    const samples = value.samples || [];
    return [
      `### 저장 데이터 OCR 재처리`,
      ``,
      `- **점검 파일:** ${formatNumber(value.checked_count || 0)}개`,
      `- **재처리 후보:** ${formatNumber(value.candidate_count || 0)}개`,
      `- **재처리 완료:** ${formatNumber(value.reprocessed_count || 0)}개`,
      `- **누락 파일:** ${formatNumber(value.missing_file_count || 0)}개`,
      `- **실패:** ${formatNumber(value.failed_count || 0)}개`,
      `- **RAG 갱신:** ${formatNumber(value.rag_updated_count || value.rag_backfill?.updated_count || 0)}개`,
      runtime.message ? `- **OCR 런타임:** ${runtime.ready ? "연결됨" : "확인 필요"} · ${runtime.message}` : "",
      limits.message ? `- **처리 한계:** ${limits.message}` : "",
      ``,
      `### 재처리 샘플`,
      ...formatBulletList(
        samples.slice(0, 10),
        (item) =>
          `${displayCompanyName(item, item.key || "저장 키 미확인")} · ${item.file_name || "파일명 없음"} · 본문 ${formatNumber(item.char_count || 0)}자 · ${item.ocr_status || "텍스트 추출"}`,
        "이번 실행에서 새로 재처리한 파일이 없습니다."
      ),
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180)),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "storage_duplicate_review") {
    const groups = value.groups || [];
    const tickerBreakdown = value.ticker_breakdown || [];
    const policy = value.representative_policy || {};
    const usage = value.dossier_usage_summary || {};
    const policyLabel =
      policy.dossier_usage === "representative_only" ? "대표 자료만 사용" : policy.dossier_usage || "정책 미확인";
    const duplicateLabel =
      policy.duplicate_usage === "excluded_from_dossier"
        ? "중복 의심 자료 제외"
        : policy.duplicate_usage || "중복 처리 미확인";
    return [
      `### 저장 데이터 중복 리뷰`,
      ``,
      `- **점검 자료:** ${formatNumber(value.checked_count || 0)}개`,
      `- **대표 자료:** ${formatNumber(value.unique_representative_count || 0)}개`,
      `- **중복 묶음:** ${formatNumber(value.duplicate_group_count || 0)}개`,
      `- **중복 의심 자료:** ${formatNumber(value.duplicate_entry_count || 0)}개`,
      `- **Dossier 사용 정책:** ${policyLabel} · ${duplicateLabel}`,
      `- **Dossier 반영 요약:** 대표 ${formatNumber(
        usage.representative_count ?? value.unique_representative_count ?? 0
      )}개 · 중복 제외 ${formatNumber(
        usage.duplicate_excluded_count ?? value.duplicate_entry_count ?? 0
      )}개 · 보관 제외 ${formatNumber(usage.archived_excluded_count ?? value.skipped_archived_count ?? 0)}개`,
      policy.message ? `- **정책 메모:** ${compactOutputText(policy.message, 180)}` : "",
      value.storage?.relative_path ? `- **저장 위치:** ${value.storage.relative_path}` : "",
      ``,
      `### 우선 정리 종목`,
      ...formatBulletList(
        tickerBreakdown.slice(0, 8),
        (item) =>
          `${displayCompanyName(item, "대상 미확인")} · 중복 자료 ${
            item.duplicate_entry_count || 0
          }개 / 묶음 ${item.duplicate_group_count || 0}개`,
        "중복 의심이 많은 종목이 없습니다."
      ),
      ``,
      `### 대표 자료 기준 중복 묶음`,
      ...formatBulletList(
        groups.slice(0, 10),
        (group) => {
          const rep = group.representative || {};
          const duplicates = group.duplicates || [];
          const sample = duplicates[0] || {};
          const groupPolicy =
            group.dossier_usage === "representative_only" ? "대표 자료만 Dossier 반영" : "Dossier 정책 미확인";
          const excludedCount = group.excluded_duplicate_count ?? group.duplicate_count ?? 0;
          return `**${group.company_name || group.ticker || "공통 자료"}** · 중복 ${
            group.duplicate_count || 0
          }개 · Dossier 제외 ${excludedCount}개 · ${groupPolicy} · 대표: ${compactOutputText(
            rep.title || rep.file_name,
            120
          )}\n  예: ${sample.title || sample.file_name || "샘플 없음"} · ${translateDuplicateReason(
            sample.duplicate_reason
          )}`;
        },
        "중복 묶음이 없습니다."
      ),
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180), "추가 액션이 없습니다."),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "research_memory_legacy_archive") {
    const policy = value.policy || {};
    const files = value.archived_files || [];
    return [
      `### 레거시 파일 소프트 보관`,
      ``,
      `- **저장 키:** ${displayCompanyName(value, "미확인")}`,
      `- **정책:** ${policy.policy === "soft_archive" ? "삭제 금지 · 소프트 보관" : policy.policy || "정책 미확인"}`,
      `- **보관 후보:** ${formatNumber(value.candidate_count || 0)}개`,
      `- **보관 완료:** ${formatNumber(value.archived_count || 0)}개`,
      `- **오류:** ${formatNumber(value.error_count || 0)}개`,
      `- **메시지:** ${value.message || "처리 결과 없음"}`,
      ``,
      `### 보관 처리 파일`,
      ...formatBulletList(
        files.slice(0, 12),
        (item) => `${item.file_name} · ${item.archive_reason || "소프트 보관"}`,
        "보관 처리된 레거시 파일이 없습니다."
      ),
      ``,
      `### 운영 규칙`,
      `- ${policy.archive_behavior || "레거시 파일은 삭제하지 않고 보관 플래그로 숨깁니다."}`,
      `- ${policy.restore_behavior || "보관 문서 포함 옵션으로 다시 확인하고 복원할 수 있습니다."}`,
    ].join("\n");
  }

  if (value.module === "deduped_dossier_refresh_queue") {
    return [
      `### 중복 리뷰 기반 Dossier 갱신`,
      ``,
      `- **후보:** ${formatNumber(value.candidate_count || 0)}개`,
      `- **갱신 완료:** ${formatNumber(value.refreshed_count || 0)}개`,
      `- **스킵:** ${formatNumber(value.skipped_count || 0)}개`,
      `- **실패:** ${formatNumber(value.failed_count || 0)}개`,
      ``,
      `### 갱신된 종목`,
      ...formatBulletList(
        value.refreshed,
        (item) =>
          `${displayCompanyName(item)} · 고유 자료 ${item.source_count || 0}개 · 중복 제외 ${
            item.duplicate_count || 0
          }개 · 신뢰도 ${toPercent(item.confidence)}${
            item.storage?.relative_path ? `\n  저장: ${item.storage.relative_path}` : ""
          }`,
        "갱신된 종목이 없습니다."
      ),
      ``,
      value.skipped?.length ? `### 스킵된 종목` : "",
      ...(value.skipped?.length
        ? formatBulletList(value.skipped, (item) => `${displayCompanyName(item)} · ${item.reason}`)
        : []),
      value.failed?.length ? `` : "",
      value.failed?.length ? `### 실패한 종목` : "",
      ...(value.failed?.length
        ? formatBulletList(value.failed, (item) => `${displayCompanyName(item)} · ${item.error}`)
        : []),
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180), "추가 액션이 없습니다."),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (
    value.module === "recent_weekly_research_brief"
  ) {
    const counts = value.counts || {};
    const daily = value.daily_watch?.dart || {};
    const watch = value.watch_summary || {};
    const headlineForItem = (item) => {
      const target = (item.related_targets || []).slice(0, 2).join(", ") || item.company_name || "관련 대상";
      const type = translateReportType(item.report_type || item.category);
      const importance = item.importance ? ` · ${item.importance}` : "";
      const summary = compactOutputText(item.summary || item.action || item.title || "요약 없음", 90);
      return `${item.date || "날짜 미확인"} · ${target} · ${type}${importance} · ${summary}`;
    };
    const lineForItem = (item) => {
      const target = (item.related_targets || []).slice(0, 2).join(", ") || item.company_name || "관련 대상";
      const source = item.source_url ? ` · 원문 ${item.source_url}` : "";
      const storage = item.relative_path ? ` · 저장 ${item.relative_path}` : "";
      const importance = item.importance ? ` · 중요도 ${item.importance}` : "";
      const publicIrSecSource = item.category === "public_ir_sec"
        ? [item.source_provider, item.filing_form, item.source_reliability].filter(Boolean).join(" · ")
        : "";
      const publicIrSecQuality = item.category === "public_ir_sec"
        ? ` · ${publicIrSecSource || "출처 미확인"} · ${item.recommendation_guard || item.quality_status || "품질 미확인"}`
        : "";
      return `${item.date || "날짜 미확인"} · ${target} · ${translateReportType(item.report_type || item.category)}${importance}${publicIrSecQuality} · ${compactOutputText(item.summary || item.action || "요약 없음", 180)}${storage}${source}`;
    };
    const sourceLines = (value.daily_watch?.source_schedule || []).map((item) => {
      const status = item.due ? "점검 필요" : "최신";
      const nextCheck = item.next_check_after ? ` · 다음 ${formatDateTime(item.next_check_after)}` : "";
      const failure = item.last_error ? ` · 오류 ${compactOutputText(item.last_error, 90)}` : "";
      return `${item.label || item.key || "외부 소스"} · ${status} · 자동 ${item.auto_refresh ? "켜짐" : "꺼짐"} · 최근 ${formatDateTime(item.last_checked_at)}${nextCheck}${failure}`;
    });
    const categoryGroupLines = Array.isArray(value.category_groups)
      ? value.category_groups
          .filter((group) => group && (group.count || group.visible_count))
          .map((group) => {
            const targets = Array.isArray(group.target_names) && group.target_names.length
              ? ` · 관련 ${group.target_names.slice(0, 4).join(", ")}`
              : "";
            const quality = group.quality_summary || {};
            const qualityLine = group.key === "public_ir_sec"
              ? ` · 추천 가능 ${formatNumber(quality.usable_for_recommendation || 0)}건 / 본문 보강 ${formatNumber(quality.needs_body_copy || quality.blocked_or_needs_review || 0)}건`
              : "";
            const note = group.note ? ` · ${compactOutputText(group.note, 80)}` : "";
            return `**${group.label || group.key || "자료"}** · ${formatNumber(group.count || 0)}건${qualityLine}${targets}${note}`;
          })
      : [];
    const targetDigest = new Map();
    const collectTargetDigest = (items, label) => {
      (items || []).forEach((item) => {
        const targets = (item.related_targets || []).length
          ? item.related_targets
          : [item.company_name || "시장/섹터 공통"];
        targets.slice(0, 3).forEach((target) => {
          const key = target || "시장/섹터 공통";
          const current = targetDigest.get(key) || { filing: 0, report: 0, publicIrSec: 0, customs: 0, market: 0 };
          current[label] = (current[label] || 0) + 1;
          targetDigest.set(key, current);
        });
      });
    };
    collectTargetDigest(value.important_filings || value.filings, "filing");
    collectTargetDigest(value.display_reports || value.reports, "report");
    collectTargetDigest(value.public_ir_sec_items, "publicIrSec");
    collectTargetDigest(value.customs_exports, "customs");
    collectTargetDigest(value.market_context, "market");
    const targetDigestSource = Array.isArray(value.target_digest) && value.target_digest.length
      ? value.target_digest.slice(0, 12).map((item) => ({
          target: item.target || "시장/섹터 공통",
          total: item.total || 0,
          countsForTarget: {
            filing: item.filing || 0,
            report: item.report || 0,
            publicIrSec: item.public_ir_sec || 0,
            customs: item.customs || 0,
            market: item.market || 0,
          },
        }))
      : Array.from(targetDigest.entries())
          .map(([target, countsForTarget]) => ({
            target,
            total:
              (countsForTarget.filing || 0) +
              (countsForTarget.report || 0) +
              (countsForTarget.publicIrSec || 0) +
              (countsForTarget.customs || 0) +
              (countsForTarget.market || 0),
            countsForTarget,
          }))
          .sort((a, b) => b.total - a.total || a.target.localeCompare(b.target, "ko"))
          .slice(0, 12);
    const targetDigestLines = targetDigestSource
      .map(({ target, countsForTarget, total }) => {
        const chips = [
          countsForTarget.filing ? `공시 ${countsForTarget.filing}` : "",
          countsForTarget.report ? `리포트 ${countsForTarget.report}` : "",
          countsForTarget.publicIrSec ? `공개 IR/SEC ${countsForTarget.publicIrSec}` : "",
          countsForTarget.customs ? `수출입 ${countsForTarget.customs}` : "",
          countsForTarget.market ? `시장 ${countsForTarget.market}` : "",
        ].filter(Boolean);
        return `${target} · 총 ${total}건 · ${chips.join(" / ") || "분류 없음"}`;
      });
    const dartLastChecked = daily.last_checked_at || daily.checked_at || daily.updated_at;
    const dartNextCheck = daily.next_check_after;
    const noRecentSignal =
      !counts.ownership_filings &&
      !counts.important_filings &&
      !counts.display_reports &&
      !counts.public_ir_sec &&
      !counts.customs_exports &&
      !counts.market_context;
    return [
      `### 최근 1주 자료`,
      ``,
      `- **기간:** ${value.period_start || "미확인"} ~ ${value.period_end || "미확인"}`,
      `- **기준 시각:** ${formatDateTime(value.as_of)}`,
      `- **대상:** 보유/관심 종목 ${formatNumber(value.target_scope?.holding_and_interest_ticker_count || 0)}개`,
      `- **DART 일일 점검:** ${daily.reliability_message || daily.status || "상태 미확인"}`,
      `- **DART 점검 시각:** 최근 ${formatDateTime(dartLastChecked)} · 다음 ${dartNextCheck ? formatDateTime(dartNextCheck) : "미확인"}`,
      `- **자동 점검:** ${watch.status || "상태 미확인"} · 점검 필요 소스 ${formatNumber(watch.due_source_count || 0)}개 · 실패 소스 ${formatNumber(watch.failed_source_count || 0)}개`,
      `- **집계:** 공시 ${formatNumber(counts.filings || 0)}건(중요 ${formatNumber(counts.important_filings || 0)}건, 수급/대량보유 ${formatNumber(counts.ownership_filings || 0)}건) / 핵심 리포트 ${formatNumber(counts.display_reports || 0)}건 / 공개 IR·SEC ${formatNumber(counts.public_ir_sec || 0)}건 / 숨김 ${formatNumber(counts.hidden_low_signal_reports || 0)}건 / 수출입 ${formatNumber(counts.customs_exports || 0)}건 / 시장자료 ${formatNumber(counts.market_context || 0)}건`,
      noRecentSignal ? `- **자료 없음 판정:** 최근 점검은 완료됐지만 보유/관심종목과 직접 연결된 공시·리포트·공개 IR/SEC·수출입·시장 자료가 없습니다.` : "",
      ``,
      `### 핵심 요약`,
      `- **수급/대량보유:** ${formatNumber(counts.ownership_filings || 0)}건 · 상위 ${Math.min((value.ownership_filings || []).length, 3)}건 먼저 확인`,
      `- **중요 공시:** ${formatNumber(counts.important_filings || 0)}건 · DART 일일 점검 ${(daily.coverage_rate === 1 || daily.coverage_rate === 1.0) ? "100%" : daily.status || "확인 필요"}`,
      `- **핵심 리포트:** ${formatNumber(counts.display_reports || 0)}건 · 보유/관심 종목 연결 자료만 우선 표시`,
      `- **공개 IR/SEC:** ${formatNumber(counts.public_ir_sec || 0)}건 · 추천 가산 가능 ${formatNumber(counts.public_ir_sec_usable || 0)}건 · 본문 보강 ${formatNumber(counts.public_ir_sec_needs_body || counts.public_ir_sec_blocked || 0)}건`,
      `- **자동화 상태:** 점검 필요 ${formatNumber(watch.due_source_count || 0)}개 · 실패 ${formatNumber(watch.failed_source_count || 0)}개 · 최근 신호 ${formatNumber(watch.recent_signal_count || counts.total || 0)}건`,
      ``,
      `### 자료 유형별 묶음`,
      ...formatBulletList(categoryGroupLines, (item) => item, "최근 1주 내 표시할 자료 유형 묶음이 없습니다."),
      ``,
      `### 종목별 자료 묶음`,
      ...formatBulletList(targetDigestLines, (item) => item, "최근 1주 내 보유/관심 대상별로 묶을 자료가 없습니다."),
      ``,
      `### 바로 볼 상위 항목`,
      ...formatBulletList(
        [
          ...(value.ownership_filings || []).slice(0, 3),
          ...(value.display_reports || []).slice(0, 3),
          ...(value.public_ir_sec_items || []).slice(0, 2),
        ],
        headlineForItem,
        "바로 볼 핵심 항목이 없습니다."
      ),
      ``,
      `### 수급/대량보유 핵심 공시`,
      ...formatBulletList(value.ownership_filings, lineForItem, "최근 1주일 내 수급/대량보유 핵심 공시가 없습니다."),
      ``,
      `### 중요 공시`,
      ...formatBulletList(value.important_filings || value.filings, lineForItem, "최근 1주일 내 중요 공시가 없습니다."),
      ``,
      `### 핵심 리포트`,
      ...formatBulletList(value.display_reports || value.reports, lineForItem, "최근 1주일 내 보유/관심종목 핵심 리포트가 없습니다."),
      ``,
      `### 공개 IR/SEC 자료`,
      ...formatBulletList(value.public_ir_sec_items, lineForItem, "최근 1주일 내 보유/관심종목과 연결된 공개 IR/SEC 자료가 없습니다."),
      ``,
      `### 수출입/시장 공통 자료`,
      ...formatBulletList([...(value.customs_exports || []), ...(value.market_context || [])], lineForItem, "최근 1주일 내 표시할 수출입/시장 공통 자료가 없습니다."),
      ``,
      `### 자동 점검 상태`,
      ...formatBulletList(sourceLines, (item) => item, "자동 점검 상태가 없습니다."),
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180)),
    ].join("\n");
  }

  if (value.module === "recent_weekly_research_brief_route_missing") {
    return [
      `### 최근 1주 자료를 바로 불러오지 못했습니다`,
      ``,
      `- **상태:** 백엔드 재시작 필요`,
      `- **원인:** ${value.message || "실행 중인 백엔드에 최신 API가 없습니다."}`,
      `- **요청 경로:** ${value.requested_path || "미확인"}`,
      ``,
      `### 조치 방법`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 180)),
      ``,
      `백엔드를 재시작하면 보유/관심종목 기준 최근 공시, 리포트, 수출입 자료가 이 화면에 표시됩니다.`,
    ].join("\n");
  }

  if (
    value.module === "daily_stock_recommendations" ||
    value.module === "daily_recommendation_tracking"
  ) {
    const records = value.records || value.latest_records || [];
    const state = value.state || {};
    const recommendationLines = records.slice(0, 3).map((item) => {
      const reasons = (item.reasons || []).slice(0, 2).join(" / ");
      const evidence = (item.evidence_sources || []).slice(0, 2).join(" / ");
      const scoreComponents = (item.score_components || [])
        .slice(0, 4)
        .map((component) => `${component.label} +${formatNumber(component.points || 0)}`)
        .join(" / ");
      const weights = (item.score_explanation?.component_weights || [])
        .slice(0, 3)
        .map((component) => `${component.label} ${component.weight_pct}%`)
        .join(" / ");
      const penalties = (item.score_penalties || []).slice(0, 2).join(" / ");
      const weeklyGroups = (item.weekly_evidence_groups || [])
        .slice(0, 3)
        .map((group) => {
          const quality = group.quality_summary || {};
          const qualityText = group.key === "public_ir_sec"
            ? ` (추천 가능 ${formatNumber(quality.usable_for_recommendation || 0)} / 보강 ${formatNumber(quality.needs_body_copy || quality.blocked_or_needs_review || 0)})`
            : "";
          return `${group.label || group.key || "자료"} ${formatNumber(group.count || 0)}건${qualityText}`;
        })
        .join(" / ");
      const overseas = item.overseas_tracking?.needs_fx_conversion
        ? `\n  해외 추적: ${item.overseas_tracking.currency || item.currency || "USD"} 기준 가격 + USD/KRW 환율 확인`
        : "";
      const portfolioRisk = item.portfolio_risk_connection?.linked
        ? `\n  포트폴리오 연결: ${item.portfolio_risk_connection.message || "보유/관심 노출과 함께 확인"}`
        : "";
      const baseline = formatSmartPrice(item.baseline_price, item.currency || "KRW", "기준가 미확인");
      return `${item.rank || "-"}위. ${displayCompanyName(item)} · 기준가 ${baseline} · 점수 ${
        item.score ?? "n/a"
      }\n  점수 구성: ${scoreComponents || "구성 저장 전"}${
        weights ? `\n  비중: ${weights}` : ""
      }${penalties ? `\n  감점/확인: ${penalties}` : ""}${weeklyGroups ? `\n  최근 1주 묶음: ${weeklyGroups}` : ""}${overseas}${portfolioRisk}\n  근거: ${
        reasons || "근거 요약 없음"
      }\n  출처: ${evidence || "저장 근거 없음"}`;
    });
    const milestones = [];
    records.forEach((record) => {
      (record.tracking_milestones || []).forEach((milestone) => {
        milestones.push({
          company_name: record.company_name,
          ticker: record.ticker,
          currency: record.currency,
          ...milestone,
        });
      });
    });
    const milestoneLines = milestones.slice(0, 12).map((item) => {
      const price = item.price === null || item.price === undefined
        ? "가격 미확인"
        : formatSmartPrice(item.price, item.currency || "KRW", "가격 미확인");
      const change = item.price_change_pct === null || item.price_change_pct === undefined
        ? ""
        : ` · 변동 ${toPercent(item.price_change_pct)}`;
      return `${displayCompanyName(item)} · ${item.label || item.key || "추적"} · ${
        item.target_date || "일자 미확인"
      } · ${item.status || "pending"} · ${price}${change}`;
    });
    const performance = value.performance_summary || {};
    return [
      `### 매일 추천 후보 1~3위`,
      ``,
      `- **상태:** ${value.status || "미확인"}`,
      `- **추천일:** ${value.recommendation_date || value.latest_recommendation_date || state.last_run_date || "미확인"}`,
      `- **저장 위치:** ${value.storage_path || "미확인"}`,
      value.message ? `- **메시지:** ${value.message}` : "",
      value.disclaimer ? `- **주의:** ${value.disclaimer}` : "",
      ``,
      `### 추천 후보`,
      ...formatBulletList(recommendationLines, (item) => item, "저장된 추천 후보가 없습니다."),
      ``,
      `### 사후 추적`,
      value.tracking
        ? `- 갱신: 도래 ${formatNumber(value.tracking.due_count || 0)}개 / 대기 ${formatNumber(
            value.tracking.pending_count || 0
          )}개 / 가격 미확인 ${formatNumber(value.tracking.price_unavailable_count || 0)}개`
        : `- 추적 상태: ${formatNumber(value.due_or_pending_milestones?.length || 0)}개 대기`,
      `- 누적 성과: 완료 ${formatNumber(performance.complete_count || 0)}개 / 상승 ${formatNumber(
        performance.positive_count || 0
      )}개 / 하락 ${formatNumber(performance.negative_count || 0)}개 / 대기 ${formatNumber(
        performance.pending_count || 0
      )}개`,
      ...formatBulletList(milestoneLines, (item) => item, "표시할 추적 마일스톤이 없습니다."),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "research_automation_feature_status") {
    const statusLabel = (status) =>
      ({
        active: "활성",
        partial: "부분 적용",
        pending: "대기",
        inactive: "비활성",
      }[status] || status || "미확인");
    const featureLine = (item) => {
      const counters = [
        item.document_count !== undefined ? `RAG 문서 ${item.document_count}개` : "",
        item.snapshot_count !== undefined ? `스냅샷 ${item.snapshot_count}개` : "",
        item.tag_count !== undefined ? `태그 ${item.tag_count}개` : "",
        item.dossier_count !== undefined ? `Dossier ${item.dossier_count}개` : "",
        item.daily_brief_count !== undefined ? `브리핑 ${item.daily_brief_count}개` : "",
        item.duplicate_count !== undefined ? `중복 제외 기록 ${item.duplicate_count}개` : "",
      ].filter(Boolean);
      return `**${item.name}** · ${statusLabel(item.status)}${
        counters.length ? ` · ${counters.join(" · ")}` : ""
      }\n  ${compactOutputText(item.detail, 220)}`;
    };
    const lastRun = value.last_run || {};
    const digest = value.dashboard_digest || {};
    const duplicateReview = value.duplicate_review || {};
    const refreshQueue = value.dossier_refresh_queue || digest.last_deduped_dossier_refresh || {};
    const dailyRecommendations = digest.daily_recommendations || {};
    const dailyState = dailyRecommendations.state || {};
    const sourceSchedule = Array.isArray(value.source_schedule)
      ? value.source_schedule
      : Array.isArray(digest.source_schedule)
        ? digest.source_schedule
        : [];
    const sourceScheduleLines = sourceSchedule.map((item) => {
      const status = item.due ? "점검 필요" : "최신";
      const auto = item.auto_refresh ? `자동 ${item.refresh_hours || 24}시간` : "자동 꺼짐";
      return `${item.label || item.key || "외부 소스"} · ${status} · ${auto} · 관련 ${item.related_count || 0}개 · 최근 ${formatDateTime(item.last_checked_at)}`;
    });
    const sourceQualityDashboard = Array.isArray(digest.source_quality_dashboard)
      ? digest.source_quality_dashboard
      : [];
    const sourceQualityLines = sourceQualityDashboard.map(
      (item) =>
        `${item.source || "소스 미확인"} · ${item.status || "미확인"} · 관련 ${formatNumber(
          item.related_count || 0
        )}개 · 저작권: ${item.copyright_policy || "정책 미확인"} · 중복: ${
          item.duplicate_guard || "가드 미확인"
        } · 활용: ${item.detail || "시장일지/RAG/추천 후보 점검"} · 최근 ${formatDateTime(item.last_checked_at)}`
    );
    const priorityTargets = (digest.priority_targets || [])
      .slice(0, 5)
      .map(
        (item) =>
          `${item.label || item.key || "대상 미확인"} · 저장 ${item.recent_document_count || 0}개 · RAG ${
            item.rag_document_count || 0
          }개 · 중복 ${item.duplicate_suspected_count || 0}개`
      );
    return [
      `리서치 자동화 적용 상태`,
      ``,
      `기준 시각: ${formatDateTime(value.as_of)}`,
      ``,
      `자동화 요약`,
      `- 상태: ${digest.headline || "요약 없음"}`,
      `- Pulls 대상: ${digest.target_count || 0}개 / 포트폴리오 연결 ${digest.portfolio_linked_count || 0}개`,
      `- De-dupes 중복 의심: ${digest.duplicate_suspected_count || 0}개`,
      duplicateReview.as_of
        ? `- 최근 중복 리뷰: 묶음 ${duplicateReview.duplicate_group_count || 0}개 / 자료 ${
            duplicateReview.duplicate_entry_count || 0
          }개 · ${formatDateTime(duplicateReview.as_of)}`
        : `- 최근 중복 리뷰: 아직 생성되지 않음`,
      refreshQueue.as_of || refreshQueue.updated_at
        ? `- 중복 종목 Dossier 갱신: 완료 ${refreshQueue.refreshed_count || 0}개 / 실패 ${
            refreshQueue.failed_count || 0
          }개 · ${formatDateTime(refreshQueue.as_of || refreshQueue.updated_at)}`
        : `- 중복 종목 Dossier 갱신: 아직 실행되지 않음`,
      `- RAG 문서: ${digest.rag_document_count || 0}개 / 연결 대상 ${digest.rag_connected_count || 0}개`,
      `- 뉴스 인박스: ${digest.news_inbox_count || 0}개 / 미승격 ${digest.news_unpromoted_count || 0}개 / 품질 확인 ${digest.news_quality_issue_count || 0}개`,
      `- 매크로/외부 소스: 점검 필요 ${digest.source_schedule_due_count || sourceSchedule.filter((item) => item.due).length}개`,
      `- Dossier: ${digest.dossier_count || 0}개 / 실패 ${digest.failed_count || 0}개`,
      `- Delivers 일일 브리핑: ${digest.daily_brief_date || "미생성"}`,
      `- 추천 후보: ${dailyRecommendations.latest_recommendation_date || "미생성"} · ${formatNumber(
        dailyRecommendations.record_count || 0
      )}개 저장 · ${dailyRecommendations.due ? "오늘 실행 필요" : "오늘 상태 확인"}${
        dailyState.last_tracking_at ? ` · 추적 ${formatDateTime(dailyState.last_tracking_at)}` : ""
      }`,
      ``,
      `외부 소스 자동 점검`,
      ...formatBulletList(sourceScheduleLines, (item) => item, "외부 소스 자동 점검 상태가 없습니다."),
      ``,
      `수집 품질 대시보드`,
      ...formatBulletList(sourceQualityLines, (item) => item, "소스 품질 대시보드가 없습니다."),
      ``,
      `우선 점검 대상`,
      ...formatBulletList(priorityTargets, (item) => item, "우선 점검 대상이 없습니다."),
      ``,
      `기능별 상태`,
      ...formatBulletList(value.features, featureLine, "상태 항목이 없습니다."),
      ``,
      `마지막 전체 자동화 실행`,
      lastRun.updated_at
        ? `- ${formatDateTime(lastRun.updated_at)} · Dossier ${lastRun.dossier_count || 0}개 · 실패 ${lastRun.failed_count || 0}개 · RAG 갱신 ${lastRun.rag_updated_count || 0}개`
        : "- 아직 전체 자동화 실행 기록이 없습니다.",
      ``,
      `다음 액션`,
      ...formatBulletList(digest.next_actions, (item) => compactOutputText(item, 180), "추가 액션이 없습니다."),
    ].join("\n");
  }

  if (value.module === "rag_memory_global_search" || value.module === "rag_memory_search") {
    const documents = value.documents || [];
    const title = value.module === "rag_memory_global_search" ? "전체 저장 데이터 자연어 검색" : "현재 키 RAG 검색";
    return [
      title,
      ``,
      `검색어: ${value.query || "전체"}`,
      value.key ? `저장 키: ${value.key}` : "",
      `결과: ${documents.length}개`,
      value.grouped_count ? `묶은 과거 버전: ${value.grouped_count}개` : "",
      `범위: ${value.include_low_quality ? "격리 문서 포함" : "자동 주입 가능 문서"}`,
      ``,
      `검색 결과`,
      ...formatBulletList(
        documents,
        (item) => {
          const score = item.relevance_score !== undefined ? ` · 관련도 ${item.relevance_score}` : "";
          const matched = item.matched_terms?.length ? ` · 매칭 ${item.matched_terms.join(", ")}` : "";
          const strength = item.match_strength ? ` · ${item.match_strength} 매칭` : "";
          const related = item.related_version_count ? ` · 과거 버전 ${item.related_version_count}개 묶음` : "";
          return `**${item.ticker || "GENERAL"}** · ${translateReportType(item.report_type)} · 품질 ${item.quality_score ?? "n/a"}점${score}${matched}${strength}${related}\n  ${compactOutputText(item.summary || item.content_excerpt || item.title, 220)}`;
        },
        "검색 결과가 없습니다."
      ),
    ].filter(Boolean).join("\n");
  }

  if (value.module === "rag_query_synthesis") {
    const payload = value.payload || value;
    const sourceDocuments = payload.source_documents || [];
    return [
      `### 저장 데이터 검색 합성 보고서`,
      ``,
      `- **검색어:** ${payload.query || value.query || "미확인"}`,
      `- **원천 문서:** ${payload.source_count || 0}개`,
      payload.candidate_count ? `- **검색 후보:** ${payload.candidate_count}개` : "",
      payload.grouped_count ? `- **중복 묶음 반영:** ${payload.grouped_count}개` : "",
      `- **관련 범위:** ${(payload.tickers || []).join(", ") || "시장/섹터"}`,
      `- **합성 신뢰도:** ${toPercent(payload.confidence)}`,
      value.storage?.relative_path ? `- **저장 위치:** ${value.storage.relative_path}` : "",
      ``,
      `### 요약`,
      compactOutputText(payload.summary, 420),
      ``,
      `### 합의된 사실`,
      ...formatBulletList(payload.consensus_facts, (item) => compactOutputText(item, 220)),
      ``,
      `### 강세 논거`,
      ...formatBulletList(payload.bull_thesis, (item) => compactOutputText(item, 220)),
      ``,
      `### 약세 논거`,
      ...formatBulletList(payload.bear_thesis, (item) => compactOutputText(item, 220)),
      ``,
      `### 핵심 쟁점`,
      ...formatBulletList(payload.cruxes, (item) => compactOutputText(item, 220)),
      ``,
      `### 앞으로 확인할 관찰 지표`,
      ...formatBulletList(payload.observables, (item) => compactOutputText(item, 180)),
      ``,
      `### 다음 액션`,
      ...formatBulletList(payload.next_actions, (item) => compactOutputText(item, 200)),
      ``,
      `### 사용한 저장 데이터`,
      ...formatBulletList(
        sourceDocuments.slice(0, 8),
        (item) =>
          `${displayCompanyName(item, "전체/공통 자료")} · ${translateReportType(item.report_type)} · ${
            item.source_date || "날짜 없음"
          } · ${compactOutputText(item.title || item.source_file_name || item.summary, 160)}`,
        "사용한 저장 데이터가 없습니다."
      ),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (value.module === "dossier_synthesis") {
    return [
      `### Dossier 합성 보고서`,
      ``,
      `- **종목:** ${displayCompanyName(value)}`,
      `- **기준일:** ${value.date || "미확인"}`,
      `- **고유 자료:** ${value.source_count || 0}개`,
      `- **중복 제외:** ${value.duplicate_count || 0}개`,
      `- **합성 신뢰도:** ${toPercent(value.confidence)}`,
      ``,
      `### 요약`,
      compactOutputText(value.thesis_summary, 360),
      ``,
      `### 합의된 사실`,
      ...formatBulletList(value.consensus_facts, (item) => compactOutputText(item, 180)),
      ``,
      `### 강세 논거`,
      ...formatBulletList(value.bull_thesis, (item) => compactOutputText(item, 180)),
      ``,
      `### 약세 논거`,
      ...formatBulletList(value.bear_thesis, (item) => compactOutputText(item, 180)),
      ``,
      `### 핵심 쟁점`,
      ...formatBulletList(value.cruxes),
      ``,
      `### 다음 관찰 지표`,
      ...formatBulletList(value.observables),
      ``,
      `### 무효화 조건`,
      ...formatBulletList(value.invalidation_conditions),
      ``,
      `### 최근 반영 자료`,
      ...formatBulletList(
        value.latest_changes,
        (item) =>
          `${item.date || "날짜 없음"} · ${translateReportType(item.type)} · ${compactOutputText(
            item.summary || item.file_name,
            150
          )}`,
        "최근 반영 자료가 없습니다."
      ),
      ``,
      `- **저장 데이터:** ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "daily_research_briefing") {
    const portfolioOverview = value.portfolio_overview || {};
    const primarySnapshots =
      Array.isArray(portfolioOverview.items) && portfolioOverview.items.length
        ? portfolioOverview.items
        : value.snapshots || [];
    return [
      `### 일일 리서치 브리핑`,
      ``,
      `- **기준일:** ${value.date || "미확인"}`,
      `- **생성 시각:** ${formatDateTime(value.generated_at)}`,
      `- **추적 종목:** ${(value.portfolio_tickers || []).length}개`,
      `- **논거 스냅샷:** ${value.snapshot_count || 0}개`,
      `- **포트폴리오 논거 연결:** ${portfolioOverview.snapshot_connected_count || 0}/${portfolioOverview.holding_count || 0}개`,
      `- **최근 입력 자료:** ${value.recent_entry_count || 0}개`,
      ``,
      `### 시장/거시 자료`,
      ...formatBulletList(
        value.market_entries,
        (item) =>
          `${translateReportType(item.type)} · ${compactOutputText(item.summary, 180)}`,
        "오늘 반영된 시장/거시 자료가 없습니다."
      ),
      ``,
      `### 주요 종목 스냅샷`,
      ...formatBulletList(
        primarySnapshots.slice(0, 12),
        (item) => {
          const confidence = item.confidence === null || item.confidence === undefined ? "n/a" : toPercent(item.confidence);
          const status = item.status ? ` · ${item.status}` : "";
          const action = item.recommended_action ? ` · ${compactOutputText(item.recommended_action, 90)}` : "";
          return `${displayCompanyName(item)} · 신뢰도 ${confidence}${status} · ${compactOutputText(item.summary, 170)}${action}`;
        },
        "표시할 종목 스냅샷이 없습니다."
      ),
      ``,
      `### 포트폴리오 우선 점검`,
      ...formatBulletList(
        portfolioOverview.priority_reviews,
        (item) => {
          const kpis = (item.watch_kpis || []).slice(0, 3).join(", ") || "KPI 미정";
          const confidence = item.confidence === null || item.confidence === undefined ? "n/a" : toPercent(item.confidence);
          const bear = (item.bear_triggers || []).length
            ? ` · 약세: ${compactOutputText((item.bear_triggers || []).join(" / "), 110)}`
            : "";
          return `${displayCompanyName(item)} · ${item.status || "상태 미확인"} · 신뢰도 ${confidence} · 확인 KPI ${kpis} · ${compactOutputText(item.recommended_action, 120)}${bear}`;
        },
        "우선 점검 종목이 없습니다."
      ),
      ``,
      `### 최근 저장 자료`,
      ...formatBulletList(
        value.recent_entries,
        (item) =>
          `${item.date || "날짜 없음"} · ${item.ticker || "범위 미확인"} · ${translateReportType(
            item.type
          )} · ${compactOutputText(item.summary, 140)}`,
        "최근 저장 자료가 없습니다."
      ),
      ``,
      `### 다음 액션`,
      ...formatBulletList(value.next_actions),
      ``,
      `- **저장 데이터:** ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "research_automation_pipeline") {
    const sourceLines = (value.source_results || []).map((item) => {
      const result = item.result || {};
      return `${item.source}: 저장 ${result.saved_count ?? 0}개, 중복/스킵 ${
        result.skipped_count ?? 0
      }개, 실패 ${result.failed_count ?? 0}개`;
    });
    const board = value.interest_board || {};
    const digest = value.automation_digest || {};
    return [
      `전체 리서치 자동화 실행 결과`,
      ``,
      `상태: ${value.status === "success" ? "정상 완료" : value.status || "미확인"}`,
      `Pulls 대상: ${board.target_count || digest.target_count || 0}개 (보유 연결 ${board.portfolio_linked_count || digest.portfolio_linked_count || 0}개)`,
      `De-dupes 중복 의심: ${board.duplicate_suspected_count || digest.duplicate_suspected_count || 0}개`,
      `Embeds/RAG: 연결 대상 ${board.rag_connected_count || digest.rag_connected_count || 0}개 · 전체 문서 ${digest.rag_document_count || value.rag_backfill?.updated_count || 0}개`,
      `뉴스 인박스: 전체 ${value.news_inbox?.count || digest.news_inbox_count || 0}개 · 미승격 ${value.news_inbox?.unpromoted_count || digest.news_unpromoted_count || 0}개 · 품질 확인 ${value.news_inbox?.quality_issue_count || digest.news_quality_issue_count || 0}개`,
      `Dossier 합성: ${value.dossier_count || 0}개`,
      `실패: ${(value.failed || []).length}개`,
      `RAG 갱신: 문서 ${value.rag_backfill?.updated_count ?? 0}개, 종목 ${
        value.rag_backfill?.ticker_count ?? 0
      }개`,
      ``,
      `자동화 단계`,
      ...formatBulletList(board.automation_steps || digest.automation_steps, (item) => item, "자동화 단계가 없습니다."),
      ``,
      `수집 소스`,
      ...formatBulletList(sourceLines),
      ``,
      `합성된 Dossier`,
      ...formatBulletList(
        value.dossiers,
        (item) =>
          `${displayCompanyName(item)} · 고유 자료 ${item.source_count || 0}개 · 중복 ${
            item.duplicate_count || 0
          }개 · 신뢰도 ${toPercent(item.confidence)}`,
        "이번 실행에서 합성된 Dossier가 없습니다."
      ),
      ``,
      `일일 브리핑`,
      value.daily_brief
        ? `- ${value.daily_brief.date || "날짜 없음"} · 스냅샷 ${
            value.daily_brief.snapshot_count || 0
          }개 · 포트폴리오 논거 ${
            value.daily_brief.portfolio_snapshot_count || 0
          }/${value.daily_brief.portfolio_holding_count || 0}개 · 최근 자료 ${value.daily_brief.recent_entry_count || 0}개`
        : "- 일일 브리핑이 생성되지 않았습니다.",
      ``,
      `다음 액션`,
      ...formatBulletList(digest.next_actions || board.next_actions, (item) => compactOutputText(item, 180), "다음 액션이 없습니다."),
      ``,
      `실패 항목`,
      ...formatBulletList(
        value.failed,
        (item) => `${displayCompanyName(item, item.source || "대상 미확인")} · ${item.error || item.reason || "원인 미확인"}`,
        "실패 항목이 없습니다."
      ),
    ].join("\n");
  }

  if (value.module === "today_research_update") {
    const board = value.interest_board || {};
    const automation = value.automation || {};
    const daily = value.daily_brief || {};
    const rag = value.rag_backfill || {};
    const stepLine = (step) => {
      const status = step.status === "success" ? "완료" : "실패";
      const elapsed = step.elapsed_ms ? ` · ${Math.round(step.elapsed_ms / 100) / 10}초` : "";
      return `${status} · ${step.label || step.key}: ${step.summary || "결과 없음"}${elapsed}`;
    };
    return [
      `### 오늘 리서치 업데이트`,
      ``,
      `- **상태:** ${value.status === "success" ? "정상 완료" : "부분 완료"}`,
      `- **관심/보유 수집 대상:** ${board.target_count || 0}개`,
      `- **RAG 색인 갱신:** ${rag.updated_count ?? 0}개`,
      `- **Dossier 합성:** ${automation.dossier_count || 0}개`,
      `- **자동화 실패:** ${(automation.failed || []).length}개`,
      `- **일일 브리핑:** ${daily.date || "생성일 미확인"} · 최근 자료 ${daily.recent_entry_count || 0}개`,
      ``,
      `### 단계별 실행 결과`,
      ...formatBulletList(value.steps, stepLine, "실행 단계 기록이 없습니다."),
      ``,
      `### 수집 보드 요약`,
      `- 종목 대상 ${board.ticker_target_count || 0}개 · 섹터 대상 ${board.sector_target_count || 0}개`,
      `- RAG 연결 ${board.rag_connected_count || 0}개 · 논거 스냅샷 ${board.thesis_connected_count || 0}개`,
      `- 중복 의심 자료 ${board.duplicate_suspected_count || 0}개`,
      ``,
      `### 자동화 단계`,
      ...formatBulletList(board.automation_steps, (item) => item, "자동화 단계가 없습니다."),
      ``,
      `### 다음 액션`,
      ...formatBulletList(
        daily.next_actions || board.next_actions,
        (item) => compactOutputText(item, 180),
        "다음 액션이 없습니다."
      ),
      ``,
      `### 실패 항목`,
      ...formatBulletList(
        automation.failed,
        (item) => `${item.ticker || item.source || "대상 미확인"} · ${item.error || item.reason || "원인 미확인"}`,
        "실패 항목이 없습니다."
      ),
    ].join("\n");
  }

  if (value.module === "naver_chart_analysis") {
    const indicators = value.latest_indicators || {};
    const support = value.support_resistance || {};
    const money = (amount) =>
      amount === null || amount === undefined || Number.isNaN(Number(amount))
        ? "미확인"
        : `${Number(amount).toLocaleString("ko-KR", {
            maximumFractionDigits: 0,
          })}원`;
    const number = (amount, digits = 2) =>
      amount === null || amount === undefined || Number.isNaN(Number(amount))
        ? "미확인"
        : Number(amount).toLocaleString("ko-KR", {
            maximumFractionDigits: digits,
          });

    return [
      `네이버 차트 분석`,
      ``,
      `종목: ${displayCompanyName(value)}`,
      `기준일: ${value.as_of || "미확인"}`,
      `데이터: ${value.data_points || 0}개 일봉`,
      `종합 판단: ${value.overall_signal || "미확인"}`,
      `매매 관점: ${value.trade_bias || "미확인"}`,
      ``,
      `6개 핵심 보조지표`,
      `- 거래량: ${number(indicators.volume, 0)}주 / 20일 평균 대비 ${number(
        indicators.volume_ratio_to_ma20,
        2
      )}배`,
      `- 볼린저 밴드: 하단 ${money(indicators.bollinger_lower)}, 중심 ${money(
        indicators.bollinger_middle
      )}, 상단 ${money(indicators.bollinger_upper)}, 위치 ${number(
        indicators.bollinger_position,
        2
      )}`,
      `- 이동평균선: 5일 ${money(indicators.ma5)}, 20일 ${money(
        indicators.ma20
      )}, 60일 ${money(indicators.ma60)}, 20일선 방향 ${
        indicators.ma20_trend || "미확인"
      }`,
      `- MACD: ${number(indicators.macd, 2)} / 시그널 ${number(
        indicators.macd_signal,
        2
      )} / 히스토그램 ${number(indicators.macd_histogram, 2)}`,
      `- RSI 14: ${number(indicators.rsi14, 2)}`,
      `- DMI 14: +DI ${number(indicators.plus_di14, 2)} / -DI ${number(
        indicators.minus_di14,
        2
      )} / ADX ${number(indicators.adx14, 2)}`,
      ``,
      `가격 구간`,
      `- 최근 20일 지지선: ${money(support.recent_20d_support)}`,
      `- 최근 20일 저항선: ${money(support.recent_20d_resistance)}`,
      ``,
      `긍정 신호`,
      ...((value.signals || []).length
        ? value.signals.map((item) => `- ${item}`)
        : ["- 긍정 신호가 아직 뚜렷하지 않습니다."]),
      ``,
      `주의 신호`,
      ...((value.cautions || []).length
        ? value.cautions.map((item) => `- ${item}`)
        : ["- 현재 표시할 주의 신호가 없습니다."]),
      ``,
      `다음 행동`,
      ...((value.next_actions || []).length
        ? value.next_actions.map((item) => `- ${item}`)
        : ["- 다음 행동이 없습니다."]),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "ticker_dashboard") {
    const verification = value.ticker_verification;
    const profile = value.ticker_profile;
    const earningsReference = value.latest_earnings_reference || {};
    const warnings = value.data_warnings || [];
    const actions = value.recommended_next_actions || [];
    const statusWarnings = (value.module_status || []).filter((item) =>
      ["warning", "needs_action"].includes(item.tone)
    );
    const latestReportText = (value.latest_reports || [])
      .slice(0, 3)
      .map(
        (item, index) =>
          `${index + 1}. ${translateReportType(item.type)} | ${item.date || "날짜 없음"} | ${
            item.summary ? translateSummary(item.summary) : item.file_name
          }`
      );
    return [
      `티커 대시보드`,
      ``,
      `종목: ${displayCompanyName({ ...value, company_name: profile?.company_name || verification?.company_name })}`,
      verification?.company_name
        ? `공식 인증: ${verification.company_name} · ${verification.exchange || "거래소 미확인"}`
        : `공식 인증: 확인 정보 없음`,
      `저장 데이터: 공식 ${value.verified_report_count || 0}개 / 전체 ${value.file_count || 0}개 / 레거시 ${value.legacy_report_count || 0}개`,
      `실적 기준: ${earningsReference.official_quarter || "미등록"} · 발표일 ${earningsReference.official_earnings_report_date || "미입력"}`,
      `체크리스트: ${
        value.checklist_completion_rate !== null &&
        value.checklist_completion_rate !== undefined
          ? `${toPercent(value.checklist_completion_rate)} / ${translateReadiness(
              value.checklist_readiness
            )}`
          : "미작성"
      }`,
      ``,
      `먼저 볼 항목`,
      ...(warnings.length
        ? warnings.slice(0, 2).map((item) => `- 경고: ${translateSummary(item)}`)
        : ["- 경고: 현재 표시할 데이터 경고가 없습니다."]),
      ...(statusWarnings.length
        ? statusWarnings
            .slice(0, 3)
            .map((item) => `- 보강 필요: ${item.label} ${translateDashboardStatus(item.value)}`)
        : ["- 보강 필요: 주요 모듈 상태 양호"]),
      ``,
      `최근 리포트`,
      ...(latestReportText.length ? latestReportText : ["- 최근 리포트 없음"]),
      ``,
      `다음 액션`,
      ...(actions.length ? actions.slice(0, 3).map((item) => `- ${item}`) : ["- 다음 액션 없음"]),
      ``,
      `세부 신호는 위 대시보드 카드의 '세부 운영 신호 펼치기'와 '저장 데이터'에서 확인하세요.`,
    ].join("\n");
  }

  if (value.content && value.file_name && value.relative_path) {
    return [
      `저장 리포트 미리보기`,
      ``,
      `대상: ${displayCompanyName(value, "전체/공통 자료")}`,
      `파일: ${value.file_name}`,
      `경로: ${value.relative_path}`,
      `수정일: ${formatDateTime(value.modified_at)}`,
      ``,
      cleanStoredReportContent(value.content),
    ].join("\n");
  }

  if (value.module === "collaborative_research_team") {
    const queueSource = value.auto_queue_source;
    return [
      `종합 팀 리포트`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      ...(queueSource
        ? [
            `자동 실행 출처: 포트폴리오 기준 리포트 큐 ${queueSource.queue_rank || 1}순위`,
            `포함 포트폴리오: ${(queueSource.portfolio_names || []).join(", ") || "미확인"}`,
            `평가금액 기준: ${formatMoney(queueSource.market_value, "KRW", "0원")}`,
          ]
        : []),
      `투자 기간: ${translatePeriod(value.investment_period)}`,
      `투자 스타일: ${translateStyle(value.style)}`,
      `데이터 품질: ${translateQuality(value.data_quality?.data_quality)}`,
      `출처 신뢰도: ${toPercent(value.data_quality?.source_confidence)}`,
      `부족한 데이터: ${(value.data_quality?.missing_data || []).join(", ") || "없음"}`,
      `오래된/모의 데이터 경고: ${value.data_quality?.stale_data_warning ? "있음" : "없음"}`,
      `Dossier 갱신: ${translateDossierRefreshStatus(value.dossier_refresh_status)}`,
      ``,
      `요약`,
      `${value.executive_summary}`,
      ``,
      `통합 의견`,
      ...(value.consensus || []).map((item) => `- ${item}`),
      ``,
      `충돌/주의점`,
      ...(value.conflicts || []).map(
        (item) => `- ${item.topic}: ${item.resolution}`
      ),
      ``,
      `무효화 조건`,
      ...(value.invalidation_conditions || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "data_provider_snapshot") {
    const providerWarnings = (value.data_points || []).filter((item) =>
      String(item.label || "").includes("provider_warning") ||
      item.label === "data_provider_limitation"
    );
    const dataLines = (value.data_points || []).map(
      (item) =>
        `- ${translateDataLabel(item.label)}: ${item.value} (${translateSourceType(item.source_type)}, 기준 ${item.as_of || "날짜 없음"}, 신뢰도 ${toPercent(item.confidence)})`
    );
    return [
      `최신 데이터 스냅샷`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      `프로바이더 모드: ${translateProviderMode(value.provider_mode)}`,
      `자동 주입: ${value.auto_inject_analysis_data ? "켜짐" : "꺼짐"}`,
      ``,
      `프로바이더 상태`,
      ...(value.providers || []).map(
        (item) =>
          `- ${item.name}: ${translateProviderMode(item.mode)} / ${item.ready ? "준비됨" : "설정 필요"} / ${item.message}`
      ),
      ``,
      `데이터 경고`,
      ...(providerWarnings.length
        ? providerWarnings.map((item) => `- ${item.value}`)
        : ["- 표시할 데이터 경고가 없습니다."]),
      ``,
      `수집 데이터`,
      ...(dataLines.length ? dataLines : ["- 수집된 데이터가 없습니다."]),
    ].join("\n");
  }

  if (value.module === "ticker_registry_cache") {
    const sourceStatus = value.source_status || {};
    const sourceLines = (sourceStatus.sources || []).map(
      (item) =>
        `- ${translateTickerRegistrySourceName(item.source)}: ${formatNumber(item.count || 0)}개 · ${translateLookupStatus(item.status)}${item.fetched_at ? ` · ${formatDateTime(item.fetched_at)}` : ""}`
    );
    return [
      `티커 자동 인증 캐시`,
      ``,
      `로컬 공식 등록: ${formatNumber(value.local_registry_count || 0)}개`,
      `자동 인증 캐시: ${formatNumber(value.cache_count || 0)}개`,
      `원천 갱신: ${formatNumber(sourceStatus.success_count || 0)}/${formatNumber(sourceStatus.source_count || 0)}개 성공`,
      sourceStatus.updated_at ? `최근 갱신: ${formatDateTime(sourceStatus.updated_at)}` : `최근 갱신: 확인 안 됨`,
      `캐시 경로: ${value.cache_path || "미확인"}`,
      ``,
      `원천별 확보 현황`,
      ...(sourceLines.length ? sourceLines : ["- 아직 원천별 갱신 이력이 없습니다."]),
      ``,
      `캐시 항목`,
      ...((value.entries || []).length
        ? value.entries.map(
            (item, index) =>
              `${index + 1}. ${displayCompanyName(item)} · ${item.exchange || "거래소 미확인"} · ${translateVerificationSource(item.verification_source)}`
          )
        : ["- 현재 자동 인증 캐시에 저장된 티커가 없습니다."]),
      value.hidden_entry_count
        ? `- 화면 속도 보호를 위해 결과 출력은 ${formatNumber(value.displayed_entry_count || 0)}개만 표시하고, 나머지 ${formatNumber(value.hidden_entry_count)}개는 자동 인증 캐시로만 사용합니다.`
        : "",
      ``,
      `사용 방식`,
      `- 한국 상장사는 KRX/KIND 목록, 미국 상장사는 Nasdaq Trader 목록을 우선 사용합니다.`,
      `- 로컬 공식 등록에 없는 티커도 원천 목록 또는 외부 프로필에서 확인되면 자동 캐시에 저장됩니다.`,
      `- 숫자만 있고 6자리가 아닌 값은 공식 티커로 보지 않아 10 같은 오분류를 차단합니다.`,
    ].join("\n");
  }

  if (value.module === "llm_bridge_storage_status") {
    const entries = value.latest_entries || [];
    return [
      `LLM 연동 저장/RAG 상태`,
      ``,
      `저장된 LLM 응답: ${formatNumber(value.saved_count || 0)}개`,
      `활성 LLM 응답: ${formatNumber(value.active_count || 0)}개`,
      `RAG 연결 응답: ${formatNumber(value.rag_connected_count || 0)}개 / 활성 ${formatNumber(value.active_rag_connected_count || 0)}개`,
      `전체 RAG 문서: ${formatNumber(value.rag_document_count || 0)}개`,
      `저장 정책: ${value.storage_policy || "LLM 응답과 원 프롬프트를 저장 데이터로 보관합니다."}`,
      `다음 조치: ${value.next_action || "최근 항목을 확인하세요."}`,
      ``,
      `최근 저장 항목`,
      ...(entries.length
        ? entries.map((item, index) => {
            const promptStatus = item.raw_content_includes_prompt ? "프롬프트 저장" : "프롬프트 확인 필요";
            const responseStatus = item.raw_content_includes_llm_response ? "응답 저장" : "응답 확인 필요";
            const ragStatus = item.rag_status_label || (item.rag_connected ? "RAG 연결" : "RAG 제외/보관");
            const scopeText = item.scope_label ? ` · ${item.scope_label}` : "";
            return `${index + 1}. ${displayCompanyName(item)}${scopeText} · ${item.file_name || item.relative_path || "파일 미확인"} · ${promptStatus} · ${responseStatus} · ${ragStatus}`;
          })
        : ["- 최근 LLM 저장 항목이 없습니다."]),
    ].join("\n");
  }

  if (value.module === "ticker_diagnostics") {
    return [
      `티커 인증 진단`,
      ``,
      `대상: ${displayCompanyName(value.verification || value)}`,
      `상태: ${value.verification?.verified ? "인증 완료" : "인증 실패"}`,
      `해결 경로: ${translateVerificationSource(value.resolution)}`,
      `회사: ${value.verification?.company_name || "확인 안 됨"}`,
      `거래소: ${value.verification?.exchange || "확인 안 됨"}`,
      `메시지: ${value.verification?.message || "메시지 없음"}`,
      ``,
      `확인 단계`,
      ...(value.checks || []).map(
        (item) => `- ${item.passed ? "통과" : "미통과"} · ${item.name}: ${item.message}`
      ),
      ``,
      `외부 데이터 조회 로그`,
      ...((value.provider_attempts || []).length
        ? value.provider_attempts.map(
            (item) =>
              `- ${item.source}/${item.endpoint}: ${translateLookupStatus(item.status)} · ${item.message}`
          )
        : ["- 외부 데이터 조회가 필요하지 않았거나 아직 시도 로그가 없습니다."]),
      ``,
      `다음 조치`,
      ...(value.next_steps || []).map((item) => `- ${item}`),
      ``,
      `캐시 경로: ${value.cache_path || "미확인"}`,
    ].join("\n");
  }

  if (value.module === "smart_trade_setup") {
    const tradeCurrency = inferCurrencyFromTicker(value.ticker);
    return [
      `스마트 매매 전략`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      `현재가: ${formatTradePrice(value.current_price, tradeCurrency)}`,
      `스타일: ${translateTradeStyle(value.style)}`,
      `허용 리스크: ${value.risk_tolerance}`,
      `1회 거래 리스크: ${toPercent(value.risk_per_trade_pct)}`,
      `포트폴리오 기준: ${value.portfolio_source_name || "미확인"}${value.portfolio_size ? ` · ${formatMoney(value.portfolio_size, "KRW", "")}` : ""}`,
      `보유 맥락: ${value.portfolio_context_summary || "미확인"}`,
      ...((value.portfolio_context_warnings || []).length
        ? ["", "포트폴리오 경고", ...(value.portfolio_context_warnings || []).map((item) => `- ${item}`)]
        : []),
      `시장 구조: ${value.market_structure}`,
      `세팅 품질: ${value.setup_quality}`,
      ``,
      `진입 구간`,
      ...(value.entry_zone || []).map(
        (item) => `- ${item.label}: ${formatTradePrice(item.price, tradeCurrency)} (${item.rationale})`
      ),
      ``,
      `손절`,
      `- ${value.stop_loss?.label}: ${formatTradePrice(value.stop_loss?.price, tradeCurrency)} (${value.stop_loss?.rationale})`,
      ``,
      `목표가`,
      ...(value.targets || []).map(
        (item) =>
          `- ${item.label}: ${formatTradePrice(item.price, tradeCurrency)} / 손익비 ${item.risk_reward}:1 / 조치: ${item.action}`
      ),
      ``,
      `포지션 가이드`,
      `${value.position_sizing_guidance}`,
      ``,
      `실행 계획`,
      ...(value.trade_plan || []).map((item) => `- ${item}`),
      ``,
      `무효화 조건`,
      ...(value.invalidation_conditions || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "earnings_reaction") {
    return [
      `실적 발표 반응 분석`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      `분기: ${value.quarter}`,
      `기준 상태: ${value.earnings_reference_status || "확인 필요"}`,
      `공식 최신 발표 분기: ${value.official_latest_quarter || "미등록"}`,
      `공식 최신 발표일: ${value.official_latest_earnings_report_date || "미등록"}`,
      `캘린더 출처: ${value.earnings_calendar_source || "미등록"}`,
      `실적 발표일: ${value.earnings_report_date || "미입력"}`,
      `주가 반응: ${value.price_reaction}`,
      `다음 실적 예정일: ${value.next_earnings_date || "미입력"}`,
      `반응 유형: ${value.reaction_type}`,
      `센티먼트 변화: ${value.sentiment_shift}`,
      `증거 상태: ${value.evidence_status || "확인 필요"}`,
      ``,
      `데이터 경고`,
      ...sourceWarningLines(value.injected_data),
      ``,
      `보강 필요 입력`,
      ...((value.missing_inputs || []).length
        ? value.missing_inputs.map((item) => `- ${item}`)
        : ["- 없음"]),
      ``,
      `핵심 판단`,
      `${value.headline_assessment}`,
      ``,
      `가이던스 평가`,
      `${value.guidance_assessment}`,
      ``,
      `직전 실적 주요 내용`,
      `직전 실적일: ${value.previous_earnings_date || "미입력"}`,
      ...(value.previous_earnings_key_takeaways || []).map((item) => `- ${item}`),
      ``,
      `다음 실적 가이던스`,
      `${value.next_earnings_guidance}`,
      ``,
      `주요 수치`,
      ...(value.metrics || []).map(
        (item) =>
          `- ${item.name}: 발표 ${formatNullable(item.reported)} / 예상 ${formatNullable(
            item.expected
          )} / 서프라이즈 ${item.surprise || "n/a"} - ${item.interpretation}`
      ),
      ``,
      `시장 반응 패턴`,
      `${value.market_reaction_pattern}`,
      ``,
      `다음 실적 전 확인할 항목`,
      ...(value.watch_before_next_earnings || []).map((item) => `- ${item}`),
      ``,
      `투자 논거 영향`,
      ...(value.thesis_implications || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "kcif_reports_watch") {
    const relatedReports = Array.isArray(value.related_reports) ? value.related_reports : [];
    const reports = relatedReports.length
      ? relatedReports
      : Array.isArray(value.reports)
        ? value.reports.slice(0, 8)
        : [];
    const policy = value.policy || {};
    return [
      `KCIF 보고서 Watch`,
      ``,
      `상태: ${value.source_status || "확인"}`,
      `로그인: ${value.auth_status === "authenticated" ? "사용 중" : "미사용 또는 미설정"} / 상세 확인: ${value.detail_status || "미확인"}`,
      `접속 방식: ${value.connection_mode || "확인 불가"}`,
      `공개 목록: ${formatNumber(value.report_count || 0)}개 / 관련 후보 ${formatNumber(value.related_count || 0)}개`,
      `매칭 대상: ${formatNumber(value.target_count || 0)}개`,
      `저장 정책: ${policy.message || "원문/PDF는 자동 저장하지 않고 메타데이터와 자체 분석만 저장합니다."}`,
      ``,
      `관련 보고서`,
      ...(reports.length
        ? reports.slice(0, 10).map((item, index) => {
            const targets = (item.matched_targets || [])
              .map((target) => target.label)
              .filter(Boolean)
              .slice(0, 3)
              .join(", ");
            const themes = (item.matched_themes || []).slice(0, 4).join(", ") || "테마 미확인";
            const targetText = targets ? ` · 연결: ${targets}` : "";
            const detail = item.detail_analysis || {};
            const detailLines = Array.isArray(detail.derived_points)
              ? detail.derived_points.slice(0, 3).map((point) => `   - ${point}`).join("\n")
              : "";
            const detailText = detailLines ? `\n   상세 신호\n${detailLines}` : "";
            return `${index + 1}. ${item.title} (${item.published_at || "일자 미확인"})\n   분류: ${item.category || "KCIF"} · 점수 ${item.relevance_score || 0}/100 · ${themes}${targetText}\n   조치: ${item.recommended_action || "사용자가 원문을 직접 확인한 뒤 핵심 메모만 저장하세요."}${detailText}`;
          })
        : ["- 표시할 관련 보고서가 없습니다."]),
      ``,
      `다음 조치`,
      ...((value.next_actions || []).map((item) => `- ${item}`)),
      ...((value.warnings || []).length ? [``, `경고`, ...(value.warnings || []).map((item) => `- ${item}`)] : []),
    ].join("\n");
  }

  if (value.module === "regional_business_sources_watch") {
    const relatedItems = Array.isArray(value.related_items) ? value.related_items : [];
    const items = relatedItems.length
      ? relatedItems
      : Array.isArray(value.items)
        ? value.items.slice(0, 10)
        : [];
    const policy = value.policy || {};
    const sourceLines = Array.isArray(value.source_results)
      ? value.source_results.map((item) => {
          const status = item.status === "success" ? "정상" : item.status || "미확인";
          return `${item.provider || item.source_key || "소스"} · ${status}`;
        })
      : [];
    return [
      `EMERiCs/CSF/KIEP 자료 Watch`,
      ``,
      `상태: ${value.source_status || "확인"}`,
      `자료 목록: ${formatNumber(value.item_count || 0)}개 / 관련 후보 ${formatNumber(value.related_count || 0)}개`,
      `매칭 대상: ${formatNumber(value.target_count || 0)}개`,
      `저장 정책: ${policy.message || "원문 본문은 자동 저장하지 않고 메타데이터와 자체 분석만 저장합니다."}`,
      ``,
      `소스 상태`,
      ...formatBulletList(sourceLines, (item) => item, "소스 상태가 없습니다."),
      ``,
      `관련 자료`,
      ...(items.length
        ? items.slice(0, 12).map((item, index) => {
            const targets = (item.target_matches || [])
              .map((target) => target.label)
              .filter(Boolean)
              .slice(0, 3)
              .join(", ");
            const themes = (item.matched_themes || []).slice(0, 4).join(", ") || "테마 미확인";
            const targetText = targets ? ` · 연결: ${targets}` : "";
            return `${index + 1}. ${item.title || "제목 없음"} (${item.published_at || "일자 미확인"})\n   출처: ${item.source_provider || "기관 미확인"} · ${item.agency || "발행기관 미확인"} · 점수 ${item.relevance_score || 0}/100 · ${themes}${targetText}\n   링크: ${item.detail_url || item.source_url || "링크 없음"}`;
          })
        : ["- 표시할 관련 자료가 없습니다."]),
      ``,
      `다음 조치`,
      ...((value.next_actions || []).map((item) => `- ${item}`)),
      ...((value.warnings || []).length ? [``, `경고`, ...(value.warnings || []).map((item) => `- ${item}`)] : []),
    ].join("\n");
  }

  if (value.module === "sector_opportunity") {
    const isMacroAnalysis = value.display_mode === "macro_analysis";
    const companyDisplayName = (item) =>
      String(item?.company_name || item?.name || item?.label || "회사명 확인 필요").trim();
    const leaderNamesForTrend = (item) => {
      const names = (item.leader_companies || []).map(companyDisplayName);
      return Array.from(new Set(names.filter(Boolean))).join(", ") || "회사명 확인 필요";
    };
    return [
      isMacroAnalysis ? `매크로 분석` : `섹터 기회 발굴`,
      ``,
      `저장 키: ${value.research_key}`,
      `지역: ${translateRegion(value.region)}`,
      `기간: ${value.period}`,
      `스타일: ${value.style}`,
      isMacroAnalysis ? `중점 변수: ${value.focus_theme || "매크로 전체"}` : `입력 테마: ${value.focus_theme || "미입력"}`,
      ``,
      `매크로 요약`,
      `${value.macro_summary}`,
      ``,
      `산업 개요`,
      ...((value.industry_overview || []).length
        ? (value.industry_overview || []).map((item) => `- ${item}`)
        : ["- 입력된 섹터/테마 기준 산업 개요가 없습니다."]),
      ``,
      `경쟁 구도`,
      ...((value.competitive_landscape || []).length
        ? (value.competitive_landscape || []).map((item) => `- ${item}`)
        : ["- 경쟁 구도 분석이 없습니다."]),
      ``,
      `피어 비교`,
      ...((value.peer_comparison || []).length
        ? (value.peer_comparison || []).map(
            (item, index) =>
              `${index + 1}. ${companyDisplayName(item)} · ${item.role} · 적합도 ${item.fit_score}/100\n   강점: ${(item.strengths || []).join(" / ") || "없음"}\n   리스크: ${(item.risks || []).join(" / ") || "없음"}`
          )
        : ["- 표시할 피어 비교가 없습니다."]),
      ``,
      `아이디어 숏리스트`,
      ...((value.idea_shortlist || []).length
        ? (value.idea_shortlist || []).map(
            (item, index) =>
              `${index + 1}. ${companyDisplayName(item)} · ${item.sector} · 적합도 ${item.fit_score}/100 - ${item.thesis}`
          )
        : ["- 표시할 아이디어 후보가 없습니다."]),
      ``,
      `유망 섹터`,
      ...(value.ranked_sectors || []).map(
        (item, index) =>
          `${index + 1}. ${item.sector} (${item.score}/100) - ${item.rationale}`
      ),
      ``,
      `산업군별 동향 분석`,
      ...((value.sector_trends || []).length
        ? (value.sector_trends || []).map(
            (item, index) =>
              [
                `${index + 1}. ${item.sector} - ${item.trend_label} (${item.flow_score}/100)`,
                `   흐름: ${item.market_flow}`,
                `   대응: ${item.investment_solution}`,
                `   주도 기업: ${leaderNamesForTrend(item)}`,
                `   근거: ${(item.evidence || []).join(" / ") || "없음"}`,
              ].join("\n")
          )
        : ["- 표시할 산업군 동향이 없습니다."]),
      ``,
      `섹터 주도주`,
      ...((value.sector_leaders || []).length
        ? (value.sector_leaders || []).slice(0, 10).map(
            (item, index) =>
              `${index + 1}. ${companyDisplayName(item)} · ${item.sector} · ${item.leader_score}/100 - ${item.thesis}`
          )
        : ["- 표시할 주도주 후보가 없습니다."]),
      ``,
      `애널리스트 종합 의견`,
      ...((value.analyst_report || []).length
        ? (value.analyst_report || []).map((item) => `- ${item}`)
        : ["- 종합 의견이 없습니다."]),
      ``,
      `후보 기업`,
      ...(value.recommended_companies || []).map(
        (item) =>
          `- ${companyDisplayName(item)}: ${item.thesis} (적합도 ${item.fit_score}/100)`
      ),
      ``,
      `배분 관점`,
      `${value.allocation_view}`,
      ``,
      `확인할 지표`,
      ...(value.watch_items || []).map((item) => `- ${item}`),
      ``,
      `주요 리스크`,
      ...(value.key_risks || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "earnings_filing_note") {
    const fileProcessing = value.file_processing || null;
    const ragDocument = value.rag_document || null;
    return [
      `어닝 콜/공시 기반 모델 업데이트 노트`,
      ``,
      `종목: ${displayCompanyName(value)}`,
      `저장/RAG: ${ragDocument ? "연결 완료" : "저장 후 연결 대기"}`,
      ``,
      `첨부 파일 처리`,
      ...formatFileProcessingLines(fileProcessing),
      ``,
      `모델 업데이트 항목`,
      ...((value.model_updates || []).map(
        (item) =>
          `- ${item.item}: ${item.model_action} / 근거: ${item.signal} / 상태: ${item.status}`
      )),
      ``,
      `노트 초안`,
      ...((value.note_draft || []).map(
        (section) => `## ${section.title}\n${section.body}`
      )),
      ``,
      `미확인 질문`,
      ...((value.open_questions || []).map((item) => `- ${item}`)),
      ``,
      `다음 액션`,
      ...((value.next_actions || []).map((item) => `- ${item}`)),
      ``,
      `RAG 문서: ${ragDocument?.document_id || "없음"}`,
      `RAG 품질: ${ragDocument?.quality?.quality_score ?? "미평가"}`,
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "gp_lp_staging") {
    const fileProcessing = value.file_processing || null;
    const ragDocument = value.rag_document || null;
    return [
      `GP 패키지 / LP 보고 스테이징`,
      ``,
      `펀드/패키지: ${value.fund_name}`,
      `밸류에이션 템플릿: ${value.valuation_method}`,
      `저장/RAG: ${ragDocument ? "연결 완료" : "저장 후 연결 대기"}`,
      ``,
      `첨부 파일 처리`,
      ...formatFileProcessingLines(fileProcessing),
      ``,
      `GP 패키지 요약`,
      `${value.gp_package_summary || "요약 없음"}`,
      ``,
      `밸류에이션 템플릿 결과`,
      ...((value.valuation_template_output || []).map((item) => `- ${item}`)),
      ``,
      `밸류에이션 입력표`,
      ...((value.valuation_template_rows || []).map(
        (item) =>
          `- ${item.line_item}: ${item.input_status} / ${item.model_action} / LP 메모: ${item.lp_note}`
      )),
      ``,
      `LP 보고 초안`,
      ...((value.lp_report_draft || []).map(
        (section) => `## ${section.title}\n${section.body}`
      )),
      ``,
      `리스크 플래그`,
      ...((value.lp_risk_flags || []).map((item) => `- ${item}`)),
      ``,
      `스테이징 체크리스트`,
      ...((value.staging_checklist || []).map((item) => `- ${item}`)),
      ``,
      `RAG 문서: ${ragDocument?.document_id || "없음"}`,
      `RAG 품질: ${ragDocument?.quality?.quality_score ?? "미평가"}`,
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "korea_customs_trade_snapshot") {
    const hasValidData = Boolean(value.has_valid_data);
    const storageStatus = value.storage_skipped
      ? "건너뜀"
      : value.rag_document
        ? "연결 완료"
        : hasValidData
          ? "저장 후 연결 대기"
          : "실제 수치 없음";
    return [
      `관세청 수출입 동향 투자 참고자료`,
      ``,
      `기간: ${value.start_yymm || "미확인"} ~ ${value.end_yymm || "미확인"}`,
      `발표 주기: ${value.release_schedule || "1일, 11일, 21일"}`,
      `현재 기준: ${value.release_cycle || "미확인"}`,
      `상태: ${value.status === "warning" ? "확인 필요" : "완료"}`,
      `데이터 품질: ${value.data_quality_label || (value.data_quality === "no_valid_trade_rows" ? "실제 수출입 수치 없음" : "수치 확인됨")}`,
      `유효 행 수: ${formatNumber(value.valid_row_count || 0)}개`,
      `저장 정책: ${value.storage_policy || "실제 수출입 수치가 있는 자료만 저장합니다."}`,
      `저장/RAG: ${storageStatus}`,
      value.storage_skip_reason ? `저장 제외 사유: ${value.storage_skip_reason}` : "",
      value.next_action ? `다음 조치: ${value.next_action}` : "",
      ``,
      `핵심 신호`,
      ...((value.key_takeaways || []).map((item) => `- ${item}`)),
      ``,
      `품목별 요약`,
      ...((value.aggregates || []).map(
        (item) =>
          item.row_count
            ? `- ${item.label}(${item.item_code}): ${item.signal} / 수출 $${Math.round(item.export_value_usd || 0).toLocaleString()} / 수입 $${Math.round(item.import_value_usd || 0).toLocaleString()} / ${item.inventory_signal}`
            : `- ${item.label}(${item.item_code}): 실제 수출입 수치 없음 / 투자 신호 반영 제외`
      )),
      ``,
      `섹터 시사점`,
      ...((value.sector_implications || []).map((item) => `- ${item}`)),
      ``,
      `포트폴리오 활용`,
      ...((value.portfolio_usage || []).map((item) => `- ${item}`)),
      ``,
      `데이터 경고`,
      ...((value.warnings || []).map((item) => `- ${item}`)),
      ...(value.total_trend_status
        ? [
            ``,
            `수출입총괄 진단`,
            `- 상태: ${value.total_trend_status.authorized ? "연결 가능" : "권한/연결 확인 필요"}`,
            `- HTTP: ${value.total_trend_status.http_status_code || "미확인"}`,
            `- 메시지: ${value.total_trend_status.message || "미확인"}`,
            `- 다음 조치: ${value.total_trend_status.next_action || "data.go.kr 활용 승인 상태 확인"}`,
          ]
        : []),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].filter((line) => line !== "").join("\n");
  }

  if (value.module === "korea_customs_trade_total_trend_status") {
    return [
      `관세청 수출입총괄(GW) 진단`,
      ``,
      `기간: ${value.start_yymm || "미확인"} ~ ${value.end_yymm || "미확인"}`,
      `발표 주기: ${value.release_cycle || "미확인"}`,
      `상태: ${value.status === "success" ? "연결 가능" : "확인 필요"}`,
      `권한 상태: ${value.authorized ? "승인됨" : "확인 필요"}`,
      `HTTP 상태: ${value.http_status_code || "미확인"}`,
      `행 수: ${formatNumber(value.row_count || 0)}개`,
      `저장 정책: ${value.storage_policy || "진단 전용"}`,
      ``,
      `확인 메시지`,
      `- ${value.message || "확인 필요"}`,
      ...((value.warnings || []).map((item) => `- ${item}`)),
      ``,
      `다음 조치`,
      `- ${value.next_action || "data.go.kr 활용 승인 상태와 인증키 권한을 확인하세요."}`,
      ``,
      `문서: ${value.docs_url || "미확인"}`,
      `API: ${value.source_url || "미확인"}`,
    ].join("\n");
  }

  if (value.module === "long_term_compounder") {
    const candidateName = (item) => item.company_name || item.name || item.ticker || "회사명 미확인";
    return [
      `장기 복리 성장주 발굴`,
      ``,
      `저장 키: ${value.research_key}`,
      `지역: ${translateRegion(value.region)}`,
      `섹터: ${value.sector}`,
      `스타일: ${value.style}`,
      `최소 시가총액: ${formatCompounderMarketCap(value.min_market_cap, value.region, "제한 없음")}`,
      `최대 시가총액: ${formatCompounderMarketCap(value.max_market_cap, value.region, "제한 없음")}`,
      ``,
      `요약`,
      `${value.summary}`,
      ``,
      `후보 기업`,
      ...(value.candidates || []).map(
        (item, index) =>
          `${index + 1}. ${candidateName(item)} (${item.compounder_score}/100, 시가총액 ${formatCompounderMarketCap(item.market_cap, value.region)}) - ${item.thesis}`
      ),
      ``,
      `핵심 지표`,
      ...(value.candidates || []).map(
        (item) =>
          `- ${candidateName(item)}: 매출 성장률 ${toPercent(item.revenue_growth)}, 매출총이익률 ${toPercent(item.gross_margin)}, FCF 마진 ${toPercent(item.free_cash_flow_margin)}, 경쟁 우위 ${item.moat_score}/100`
      ),
      ``,
      `제외/주의 사유`,
      ...(value.rejected_reasons || []).map((item) => `- ${item}`),
      ``,
      `포트폴리오 구성 메모`,
      ...(value.portfolio_construction_notes || []).map((item) => `- ${item}`),
      ``,
      `다음 액션`,
      ...(value.next_actions || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "public_ir_sec_collection") {
    const quality = value.capture_quality || {};
    const ragText = value.rag_document?.document_id
      ? `RAG 색인 완료 · ${value.rag_document.document_id}`
      : value.status === "skipped_existing" ? "기존 저장 데이터 사용" : "RAG 색인 대기";
    const storagePath = value.storage?.relative_path || value.existing_entry?.relative_path || "저장 안 됨";
    return [
      `### 공개 IR/SEC 수집`,
      `상태: ${value.status || "미확인"}`,
      `제목: ${value.title || value.existing_entry?.title || "제목 미확인"}`,
      `출처: ${value.source_provider || value.existing_entry?.source_provider || "공개 자료"}`,
      `URL: ${value.source_url || "미확인"}`,
      `본문 글자 수: ${formatNumber(value.body_chars || value.existing_entry?.body_chars || 0)}자`,
      `품질 상태: ${quality.status || value.existing_entry?.capture_quality_status || "미확인"}`,
      `저장/RAG: ${ragText}`,
      `저장 데이터: ${storagePath}`,
      `정책: ${value.copyright_policy || "공개 자료만 수집하고 제한 자료는 URL/메타데이터 중심으로 보관합니다."}`,
      quality.recommended_action ? `다음 조치: ${quality.recommended_action}` : "",
      value.message ? `메시지: ${value.message}` : "",
    ].filter(Boolean).join("\n");
  }

  if (value.module === "public_ir_sec_status") {
    const entries = Array.isArray(value.recent_entries) ? value.recent_entries : [];
    const entryLines = entries.length
      ? entries.slice(0, 12).map((item, index) => `${index + 1}. ${item.title || item.file_name || "제목 없음"} · ${item.date || "날짜 없음"} · ${item.source_provider || "출처 미확인"} · ${item.capture_quality_status || item.capture_quality?.status || "품질 미확인"}`)
      : [value.empty_state?.title || "아직 수집된 공개 IR/SEC 자료가 없습니다."];
    return [
      `### 공개 IR/SEC 저장 상태`,
      `전체 저장: ${formatNumber(value.entry_count || 0)}건`,
      `본문 보강 필요: ${formatNumber(value.needs_body_copy_count || 0)}건`,
      `저장 키: ${value.storage_key || "PUBLIC_IR_SEC"}`,
      `정책: ${value.policy || "공개 자료만 수집합니다."}`,
      value.empty_state?.message ? `상태: ${value.empty_state.message}` : "",
      ``,
      `최근 자료`,
      ...entryLines,
      ``,
      `다음 액션`,
      ...formatBulletList(value.next_actions, (item) => compactOutputText(item, 160), "공개 IR/SEC 수집 URL을 입력하세요."),
    ].filter(Boolean).join("\n");
  }

  if (value.module === "source_url_preview") {
    const sourceUrlLines = buildSourceUrlLines(value.source_url_processing);
    const previewText = truncateDisplayText(
      cleanDocumentPreviewText(value.analysis_preview || value.preview || ""),
      5000
    );
    const originalPreviewText = truncateDisplayText(
      cleanDocumentPreviewText(value.original_preview || ""),
      1600
    );
    const hasSeparateOriginal =
      Boolean(originalPreviewText) && originalPreviewText !== previewText;
    return [
      `# 웹사이트 본문 미리보기`,
      ``,
      `## 처리 상태`,
      `- **주소:** ${value.final_url || value.source_url || "미확인"}`,
      `- **제목:** ${value.title || "제목 없음"}`,
      value.original_title ? `- **원문 제목:** ${value.original_title}` : "",
      `- **언어:** ${translateLanguage(value.language || "unknown")}`,
      `- **한국어 변환:** ${value.translation_status || "unknown"} · ${value.translation_note || "메모 없음"}`,
      `- **콘텐츠 유형:** ${value.content_type || "unknown"}`,
      `- **본문 길이:** ${formatNumber(value.text_length || 0)}자`,
      ``,
      `## 웹사이트 처리 로그`,
      ...sourceUrlLines,
      ``,
      `## 본문 미리보기`,
      ...(previewText ? formatPreviewBlock(previewText) : ["본문을 추출하지 못했습니다."]),
      ...(hasSeparateOriginal
        ? [
            ``,
            `## 원문 보관 상태`,
            `- 해외 원문은 저장 데이터에 함께 보관하지만, 화면 분석에는 위의 한국어 분석 메모를 우선 사용합니다.`,
            `- 원문 전체 확인이 필요하면 저장 데이터의 원문/첨부 항목에서 다시 열어보세요.`,
          ]
        : []),
      ``,
      `## 추천 저장 경로`,
      `- 종목·섹터 투자 논거: 정보 입력에서 **저장 위치 = 자동 분류 저장 데이터**로 저장`,
      `- 기사 링크 검토/중복 확인: 정보 입력에서 **저장 위치 = 뉴스 인박스**로 저장`,
      `- 전체 시황·거시·정책·수급 자료: 정보 입력에서 **저장 위치 = 시장일지**로 저장`,
      ``,
      `저장 데이터는 아직 만들지 않았습니다. 내용이 맞으면 원하는 저장 위치를 선택한 뒤 저장 버튼을 누르세요.`,
    ]
      .filter((line) => line !== "")
      .join("\n");
  }

  if (value.module === "research_quick_capture") {
    const capturedTicker = value.captured_item?.ticker;
    const scopeLabels = {
      MACRO: "거시/경제 전망 자료",
      SECTOR: "섹터/산업 전망 자료",
      MARKET: "전체 시황/투자 동향 자료",
      POLICY: "정책/규제 전망 자료",
      RATES: "금리/물가 전망 자료",
      FLOWS: "수급/자금 흐름 자료",
      INBOX: "미분류 투자 자료",
    };
    const classification = scopeLabels[capturedTicker] || `종목 자료 · ${capturedTicker || "미확정"}`;
    const tags = value.captured_item?.tags || [];
    const workLines = buildResearchCaptureWorkLines(value, scopeLabels);
    const inputPreview = truncateDisplayText(value.input_preview || "", 2200);
    const rawDocumentPreview = value.document_preview || value.attachment?.extracted_text || "";
    const documentPreview = truncateDisplayText(cleanDocumentPreviewText(rawDocumentPreview), 2600);
    const attachmentLines = buildAttachmentLines(value.attachment);
    const extractionReportLines = buildDocumentExtractionReport(value.attachment);
    const sourceUrlLines = buildSourceUrlLines(value.source_url_processing);
    const thesisImpact = translateImpact(value.linked_impact?.overall_impact);
    const sourceType = translateSourceType(value.captured_item?.source_type);
    const tagText = formatCaptureTagList(tags);
    const storagePath = value.storage?.relative_path || "저장 안 됨";
    const duplicateCheck = value.duplicate_check || null;
    const duplicateText = duplicateCheck?.is_duplicate_suspected
      ? `중복 의심 · ${translateDuplicateReason(duplicateCheck.reason)} · 유사도 ${toPercent(duplicateCheck.similarity)}`
      : `중복 없음 · 기존 ${formatNumber(duplicateCheck?.checked_count || 0)}개와 비교`;
    const ragText = value.rag_document?.document_id
      ? `RAG 색인 완료 · ${value.rag_document.document_id}`
      : "RAG 색인 미반영";
    return [
      `# 투자 정보 캡처 완료`,
      ``,
      `## 처리 결과`,
      `- **분류:** ${classification}`,
      `- **제목:** ${value.captured_item?.title || "제목 없음"}`,
      `- **자동 출처 분류:** ${sourceType}`,
      `- **신뢰도:** ${toPercent(value.captured_item?.confidence)}`,
      `- **기존 투자 논거 영향:** ${thesisImpact}`,
      `- **중복 점검:** ${duplicateText}`,
      `- **검색 색인:** ${ragText}`,
      `- **저장 데이터:** ${storagePath}`,
      ``,
      `## 요약`,
      `${value.captured_item?.summary || "요약 없음"}`,
      ``,
      `## 자동 분류 근거`,
      `- **범위 판정:** ${buildCaptureClassificationReason(value, scopeLabels)}`,
      `- **출처 판정:** ${sourceType} 키워드와 파일명/본문 단서를 함께 확인했습니다.`,
      `- **분석 가중치:** 신뢰도 ${toPercent(value.captured_item?.confidence)}를 기존 논거 평가에 반영했습니다.`,
      `- **시스템 태그:** ${tagText}`,
      ``,
      `## 작업한 내용`,
      ...workLines.map((item) => `- ${item}`),
      ``,
      `## 입력 원문 미리보기`,
      ...formatPreviewBlock(inputPreview || "텍스트 입력 없음"),
      ``,
      `## 웹사이트 처리`,
      ...sourceUrlLines,
      ``,
      `## 문서 추출 품질 리포트`,
      ...buildCaptureQualityLines(value.capture_quality),
      ...extractionReportLines,
      ``,
      `## 문서/파일 처리`,
      ...attachmentLines,
      ...(documentPreview
        ? [``, `## 문서 추출 미리보기`, ...formatPreviewBlock(documentPreview)]
        : ["", "문서에서 추출해 표시할 본문이 없습니다."]),
      ``,
      `## 후속 활용`,
      `- 저장 데이터는 같은 티커/범위의 후속 팀 리포트, 실적 분석, 시장일지, RAG 검색에 재사용됩니다.`,
      `- 분류가 잘못되면 저장 데이터에서 해당 파일을 확인한 뒤 티커 레지스트리 또는 관심 범위를 보정하면 됩니다.`,
    ].join("\n");
  }
  if (value.module === "portfolio_store") {
    const activeHoldings = value.active_portfolio?.holdings || [];
    const activeLines = activeHoldings.length
      ? activeHoldings.map((item, index) => {
          const gainText =
            item.unrealized_gain === undefined || item.unrealized_gain === null
              ? "손익 n/a"
              : `손익 ${formatMoney(item.unrealized_gain, "KRW", "n/a")} (${toPercent(item.unrealized_return)})`;
      const priceText =
        item.current_price === undefined || item.current_price === null
          ? "현재가 미확인"
          : `현재가 ${formatMoney(item.current_price, item.currency || "KRW", "n/a")}`;
          return `${index + 1}. ${displayCompanyName(item, "이름 없음")} · 평가금액 ${formatMoney(item.market_value, "KRW", "n/a")} · ${priceText} · ${gainText}`;
        })
      : ["- 선택 포트폴리오의 종목 내역 없음"];
    return [
      `내 포트폴리오 저장소`,
      ``,
      `현재 보유 포트폴리오: ${(value.portfolios || []).length}개`,
      value.active_portfolio
        ? `선택 항목: ${value.active_portfolio.portfolio_name} · 현재 보유 ${value.active_portfolio.holding_count || 0}개`
        : `현재 항목: 선택 없음`,
      `저장 위치: ${value.storage_path || "확인 안 됨"}`,
      ``,
      `현재 보유 포트폴리오 목록`,
      ...((value.portfolios || []).map(
        (item, index) =>
          `${index + 1}. ${item.portfolio_name} · 보유 ${item.holding_count || 0}개 · 총액 ${formatMoney(item.portfolio_value, "KRW", "n/a")} · ${portfolioStoreFreshnessSummary(item)}`
      )),
      ``,
      `선택 포트폴리오 종목`,
      ...activeLines,
    ].join("\n");
  }

  if (value.module === "portfolio_intelligent_table") {
    const holdings = value.holdings || [];
    const lines = holdings.slice(0, 12).map((item, index) => {
      const week52Text =
        item.week52_high_proximity === undefined || item.week52_high_proximity === null
          ? `52주 근접도 미등록 (${item.week52_status || "상태 없음"})`
          : `52주 근접도 ${formatSmartPercent(item.week52_high_proximity)} · 최고가 ${formatSmartPrice(item.week52_high, item.currency)}`;
      const targetText =
        item.target_upside === undefined || item.target_upside === null
          ? `목표가 미등록 (${item.target_status || "상태 없음"})`
          : `목표 여력 ${formatSmartPercent(item.target_upside)} · 목표주가 ${formatSmartPrice(item.target_price, item.target_price_currency || item.currency)}`;
      return [
        `${index + 1}. ${displayCompanyName(item)} · 평가금액 ${formatMoney(item.market_value, "KRW", "n/a")}`,
        `   현재가 ${formatSmartPrice(item.current_price, item.currency, "n/a")} · 수익 ${formatMoney(item.unrealized_gain, "KRW", "n/a")} (${toPercent(item.unrealized_return)})`,
        `   ${week52Text}`,
        `   ${targetText}`,
      ].join("\n");
    });
    return [
      `포트폴리오 그래프 & 지능형 데이터 테이블`,
      ``,
      value.summary || `서버 계산 지표를 생성했습니다.`,
      `포트폴리오: ${value.portfolio_name || "미확인"}`,
      `총액: ${formatMoney(value.portfolio_value, "KRW", "n/a")}`,
      `보유 종목: ${value.holding_count || holdings.length}개`,
      ``,
      `서버 계산 지표`,
      `- 52주 최고가 근접도: 현재가 / 최근 52주 최고가`,
      `- 목표주가 근접도와 목표 여력: 저장된 매매전략/체크리스트/논거 메모에서 목표가를 추출해 계산`,
      ``,
      `상위 표시`,
      ...(lines.length ? lines : ["- 표시할 종목이 없습니다."]),
      ``,
      `경고`,
      ...((value.warnings || []).length ? value.warnings.map((item) => `- ${item}`) : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "portfolio_performance_comparison") {
    const periodLines = (value.periods || []).map((period) => {
      const gainers =
        (period.top_gainers || [])
          .slice(0, 2)
          .map((item) => `${displayCompanyName(item)} ${formatMoney(item.net_profit, "KRW", "n/a")}`)
          .join(", ") || "없음";
      return [
        `- **${period.label}**: 순수익 ${formatMoney(period.net_profit, "KRW", "n/a")} / 수익률 ${
          period.return_rate === null || period.return_rate === undefined ? "n/a" : toPercent(period.return_rate)
        }`,
        `  가격 기준 ${period.price_as_of || value.price_data_as_of || "미확인"} · 비교 기준 ${period.target_date || "미확인"} · 포함 ${period.included_count || 0}개 · 커버리지 ${
          period.coverage_rate === null || period.coverage_rate === undefined ? "n/a" : toPercent(period.coverage_rate)
        }`,
        `  기여 상위: ${gainers}`,
      ].join("\n");
    });
    const skippedLines = (value.skipped_holdings || []).slice(0, 8).map(
      (item) => {
        const manualReturn = item.manual_unrealized_return === null || item.manual_unrealized_return === undefined
          ? ""
          : ` / 수동 수익률 ${toPercent(item.manual_unrealized_return)}`;
        const manualGain = item.manual_unrealized_gain === null || item.manual_unrealized_gain === undefined
          ? ""
          : ` / 수동 손익 ${formatMoney(item.manual_unrealized_gain, "KRW", "n/a")}`;
        const categoryLabel = item.category === "overseas_or_unsupported_history"
          ? "해외/미지원 히스토리"
          : item.category === "price_history_live_lookup_deferred" ? "실시간 히스토리 보류" : "히스토리 제한";
        return `- ${displayCompanyName(item)}: 기간 수익 제외 / ${categoryLabel} / ${item.reason || "기간 가격 데이터 없음"} / ${item.impact || "기간 비교에서 제외"}${manualGain}${manualReturn}`;
      }
    );
    const priceCache = value.price_history_cache || {};
    const resultCache = value.result_cache || {};
    const priceRefresh = value.current_price_refresh || {};
    const quality = value.performance_quality || {};
    const priceComparison = value.current_price_comparison || {};
    const priceComparisonLines = (priceComparison.items || []).slice(0, 8).map(
      (item) =>
        `- ${displayCompanyName(item)}: 저장 ${formatSmartPrice(item.stored_current_price, "KRW", "n/a")} / 최신 종가 ${formatSmartPrice(item.history_latest_close, "KRW", "n/a")} / 차이 ${toPercent(item.difference_rate)}`
    );
    const cacheLine = resultCache.enabled
      ? `결과 캐시 사용`
      : `결과 캐시 없음, 가격 히스토리 ${priceCache.enabled ? `메모리 캐시 사용(hit ${priceCache.hit_count || 0}, miss ${priceCache.miss_count || 0})` : "캐시 없음"}`;
    const refreshLine = priceRefresh.enabled
      ? `현재가 강제 갱신: 업데이트 ${priceRefresh.updated || 0}개 · 확인 ${priceRefresh.confirmed || 0}개 · 미확인 ${priceRefresh.unavailable || 0}개 · 기준 ${formatDateTime(priceRefresh.latest_checked_at)}`
      : `저장 현재가 사용: ${priceRefresh.description || "빠른 응답을 위해 제공자 강제 갱신은 생략했습니다."}`;
    return [
      `포트폴리오 기간 수익 비교`,
      ``,
      `포트폴리오: ${value.portfolio_name || "미확인"}`,
      `기준 시각: ${formatDateTime(value.as_of)} · 가격 기준일: ${value.price_data_as_of || "미확인"}`,
      `현재 평가금액: ${formatMoney(value.portfolio_value, "KRW", "n/a")}`,
      `현재 누적 미실현 손익: ${formatMoney(value.current_unrealized_gain, "KRW", "n/a")} (${toPercent(value.current_unrealized_return)})`,
      `정확도: ${quality.confidence_label || "확인 전"} · 최소 커버리지 ${
        quality.min_coverage_rate === null || quality.min_coverage_rate === undefined ? "n/a" : toPercent(quality.min_coverage_rate)
      } · 가격 기준 ${value.price_basis || quality.price_basis || "저장 현재가"}`,
      `저장 현재가 확인: ${formatDateTime(value.latest_stored_price_checked_at || quality.latest_stored_price_checked_at)} · 가격 차이 ${priceComparison.difference_count || 0}개`,
      ``,
      `기간별 순수익/수익률`,
      ...(periodLines.length ? periodLines : ["- 계산된 기간 수익이 없습니다."]),
      ``,
      `계산 방식`,
      `- ${value.method || "현재 수량과 기간별 과거 종가를 비교했습니다."}`,
      `- ${refreshLine}`,
      `- ${value.coverage_note || "가격 히스토리가 확인된 종목만 기간 수익률에 반영했습니다."}`,
      `- 계산/캐시: ${value.calculation_mode === "recomputed_on_request" ? "요청 시 현재 저장 포트폴리오 기준으로 재계산" : value.calculation_mode || "미확인"} / ${cacheLine}`,
      `- 해외/미지원 제외: ${value.unsupported_history_count || 0}개, ${formatMoney(value.unsupported_history_market_value, "KRW", "0원")}`,
      `- ${value.price_refresh_guidance || "가격 갱신 불러오기를 먼저 실행하면 저장 현재가 기준 정확도가 올라갑니다."}`,
      ...((value.data_limitations || []).map((item) => `- 한계: ${item}`)),
      ``,
      `저장 현재가와 국내 최신 종가 차이`,
      ...(priceComparisonLines.length ? priceComparisonLines : ["- 큰 차이 없음"]),
      ``,
      `제외/보류 종목`,
      ...(skippedLines.length ? skippedLines : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "target_consensus_scanner") {
    const rows = value.rows || [];
    const best = value.best_undervalued;
    const lines = rows.slice(0, 12).map((item, index) => {
      const targetText = item.consensus_target_price === undefined || item.consensus_target_price === null
        ? "목표주가 미등록"
        : `${formatSmartPrice(item.consensus_target_price, item.consensus_target_currency || item.currency)} · 상승여력 ${formatSmartPercent(item.target_upside, "계산 보류")}`;
      return [
        `${index + 1}. ${displayCompanyName(item)} · ${item.valuation_signal || "계산 보류"}`,
        `   현재가 ${formatSmartPrice(item.current_price, item.currency, "미확인")} · ${targetText}`,
        `   자료수 ${item.source_count || 0}개 · 신뢰도 ${formatSmartPercent(item.confidence, "n/a")} · 범위 ${item.source_scope || "저장 데이터"}`,
      ].join("\n");
    });
    return [
      `증권사 컨센서스 목표주가 저평가 스캔`,
      ``,
      value.summary || "목표주가와 현재가를 비교했습니다.",
      `가격 기준: ${value.price_refresh_mode === "stored_prices_only" ? "저장 현재가만 사용" : "누락 현재가 보강"}`,
      `대상: ${value.universe_count || rows.length}개 · 계산 완료: ${value.calculated_count || 0}개`,
      best
        ? `가장 저평가 후보: ${displayCompanyName(best)} · 상승여력 ${formatSmartPercent(best.target_upside)}`
        : "가장 저평가 후보: 계산 가능한 종목 없음",
      ``,
      `저평가 순위`,
      ...(lines.length ? lines : ["- 표시할 종목이 없습니다."]),
      ``,
      `경고`,
      ...((value.warnings || []).length ? value.warnings.map((item) => `- ${item}`) : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "portfolio_nps_institutional_flow") {
    const signals = value.signals || [];
    const matched = signals.filter((item) => item.matched);
    const chart = value.visualization || {};
    const ratioChart = chart.ratio_chart || [];
    const exposureChart = chart.portfolio_exposure_chart || [];
    const alerts = value.institutional_flow_alerts || [];
    const researchNotes = value.research_assist_notes || [];
    const barLine = (label, rawValue, maxValue, suffix = "%") => {
      const valueNumber = Number(rawValue || 0);
      const maxNumber = Math.max(Number(maxValue || 0), 0.0001);
      const fill = Math.max(1, Math.min(18, Math.round((valueNumber / maxNumber) * 18)));
      const bar = "█".repeat(fill) + "░".repeat(18 - fill);
      return `- ${label}: ${bar} ${valueNumber.toLocaleString("ko-KR", {
        maximumFractionDigits: 2,
      })}${suffix}`;
    };
    const ratioMax = Math.max(...ratioChart.map((item) => Number(item.nps_holding_ratio || 0)), 0);
    const exposureMax = Math.max(...exposureChart.map((item) => Number(item.portfolio_weight || 0)), 0);
    const ratioLines = ratioChart.slice(0, 8).map((item) =>
      barLine(
        displayCompanyName(item),
        item.nps_holding_ratio,
        ratioMax,
        "%"
      )
    );
    const exposureLines = exposureChart.slice(0, 8).map((item) =>
      barLine(
        displayCompanyName(item),
        Number(item.portfolio_weight || 0) * 100,
        exposureMax * 100,
        "%"
      )
    );
    const matchedLines = matched.map((item, index) => {
      const ratioText =
        item.latest_holding_ratio === undefined || item.latest_holding_ratio === null
          ? "지분율 미확인"
          : `지분율 ${Number(item.latest_holding_ratio).toFixed(2)}%`;
      const weightText =
        item.portfolio_weight === undefined || item.portfolio_weight === null
          ? "비중 n/a"
          : `포트폴리오 비중 ${toPercent(item.portfolio_weight)}`;
      return `${index + 1}. ${displayCompanyName(item)} · ${ratioText} · 최근 기준일 ${item.latest_event_date || "미확인"} · ${weightText} · 평가금액 ${formatMoney(item.market_value, "KRW", "n/a")}`;
    });
    const unmatchedCount = signals.length - matched.length;
    return [
      `국민연금 수급 매칭`,
      ``,
      value.summary || `저장 포트폴리오의 국내 보유 종목을 점검했습니다.`,
      `포트폴리오: ${value.portfolio_name || "미확인"}`,
      `점검 종목: ${value.checked_count || signals.length}개`,
      `매칭 종목: ${value.matched_count || matched.length}개`,
      `경고: ${value.warning_count || 0}개`,
      ``,
      `매칭된 종목`,
      ...(matchedLines.length ? matchedLines : ["- 현재 국민연금 보유/대량보유 신호가 매칭된 종목이 없습니다."]),
      ``,
      `국민연금 보유 지분율 시각화`,
      ...(ratioLines.length ? ratioLines : ["- 지분율을 표시할 매칭 자료가 없습니다."]),
      ``,
      `내 포트폴리오 노출 시각화`,
      ...(exposureLines.length ? exposureLines : ["- 포트폴리오 노출을 표시할 매칭 자료가 없습니다."]),
      ``,
      `수급 이탈 모니터링`,
      ...(alerts.length
        ? alerts.slice(0, 8).map(
            (item, index) =>
              `${index + 1}. [${translateSeverity(item.severity)}] ${displayCompanyName(item)} · ${item.reason} 조치: ${item.action}`
          )
        : ["- 현재 대형 수급 이탈 경고는 없습니다."]),
      ``,
      `리포트 작성 보조 논거`,
      ...(researchNotes.length ? researchNotes.map((item) => `- ${item}`) : ["- 국민연금 수급 보조 논거가 없습니다."]),
      ``,
      `다음 액션`,
      ...((value.next_actions || []).length ? value.next_actions.map((item) => `- ${item}`) : ["- 없음"]),
      ``,
      `미매칭`,
      `- ${unmatchedCount}개 종목은 현재 공공데이터포털 보유/대량보유 레코드와 직접 매칭되지 않았습니다.`,
      `- ETF와 해외주식은 국민연금 개별 국내주식 보유자료와 성격이 달라 정상적으로 제외될 수 있습니다.`,
    ].join("\n");
  }

  if (value.module === "nps_institutional_flow") {
    const signal = value.signal || {};
    const events = signal.large_holding_events || [];
    const context = value.context || [];
    const ratio =
      signal.holding_ratio === undefined || signal.holding_ratio === null
        ? "미확인"
        : `${Number(signal.holding_ratio).toFixed(2)}%`;
    const weight =
      signal.domestic_weight === undefined || signal.domestic_weight === null
        ? "미확인"
        : `${Number(signal.domestic_weight).toFixed(2)}%`;
    const amount =
      signal.amount_100m_krw === undefined || signal.amount_100m_krw === null
        ? "미확인"
        : `${Number(signal.amount_100m_krw).toLocaleString("ko-KR")}억 원`;
    return [
      `국민연금 수급 상세`,
      ``,
      `종목: ${displayCompanyName(signal.company_name ? signal : value, "미확인")}`,
      `매칭 상태: ${signal.domestic_match_found || events.length ? "자료 확인" : "직접 매칭 없음"}`,
      `국민연금 지분율: ${ratio}`,
      `국내주식 내 비중: ${weight}`,
      `평가액: ${amount}`,
      ``,
      `대량보유 보고 이벤트`,
      ...(events.length
        ? events.slice(0, 8).map((item, index) => {
            const eventRatio =
              item.holding_ratio === undefined || item.holding_ratio === null
                ? "지분율 미확인"
                : `지분율 ${Number(item.holding_ratio).toFixed(2)}%`;
            return `${index + 1}. 기준일 ${item.base_date || "미확인"} · ${eventRatio} · ${item.report_reason || item.change_reason || "사유 미확인"}`;
          })
        : ["- 확인된 대량보유 이벤트가 없습니다."]),
      ``,
      `투자 활용`,
      ...(context.length
        ? context.slice(0, 5).map((item) => `- ${item}`)
        : [
            "- 리포트 작성 시 기관 수급 논거로 활용합니다.",
            "- 포트폴리오 리스크 스캔에서 대형 수급 이탈 가능성을 함께 확인합니다.",
          ]),
      ``,
      `경고`,
      ...((signal.warnings || value.warnings || []).length
        ? (signal.warnings || value.warnings).map((item) => `- ${item}`)
        : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "portfolio_connectivity") {
    const items = value.items || [];
    const connected = items.filter((item) => item.connected);
    const needsWork = items.filter((item) => !item.connected);
    const itemLines = items.map((item, index) => {
      const status = item.connected ? "연결 완료" : "보강 필요";
      const portfolioText = (item.portfolios || []).join(", ") || "포트폴리오 미확인";
      const priceText =
        item.stored_current_price === undefined || item.stored_current_price === null
          ? "현재가 미확인"
          : `현재가 ${formatMoney(item.stored_current_price, item.currency || "KRW", "n/a")}`;
      const missingText = (item.missing_fields || []).length
        ? ` · 보강: ${(item.missing_fields || []).join(", ")}`
        : "";
      const memoryText = `저장 ${item.research_memory_count || 0}건`;
      const ragText = item.rag_connected ? "RAG 연결" : "RAG 미연결";
      const thesisText = item.thesis_snapshot_connected ? "논거 스냅샷 있음" : "논거 스냅샷 없음";
      return `${index + 1}. ${status} · ${displayCompanyName(item)} · ${item.exchange || "거래소 미확인"} · ${item.sector || "섹터 미분류"} · ${priceText} · ${memoryText} · ${ragText} · ${thesisText} · 포함: ${portfolioText}${missingText}`;
    });
    return [
      `포트폴리오 전체 종목 시스템 연결 점검`,
      ``,
      value.summary || `고유 종목 ${items.length}개를 점검했습니다.`,
      `공식 티커 인증: ${value.verified_count || 0}/${value.holding_count || items.length}`,
      `RAG 검색 연결: ${value.rag_connected_count || 0}/${value.holding_count || items.length}`,
      `투자 논거 스냅샷: ${value.thesis_snapshot_count || 0}/${value.holding_count || items.length}`,
      `시스템 연결 완료: ${value.connected_count || connected.length}/${value.holding_count || items.length}`,
      `보강 필요: ${needsWork.length}개`,
      ``,
      `종목별 연결 상태`,
      ...(itemLines.length ? itemLines : ["- 저장된 보유 종목이 없습니다."]),
    ].join("\n");
  }

  if (value.module === "portfolio_analysis_status") {
    const items = value.items || [];
    const lines = items.map((item, index) => {
      const state = item.module_state || {};
      const marks = [
        `팀 ${state.team_report ? "완료" : "필요"}`,
        `매매 ${state.trade_setup ? "완료" : "필요"}`,
        `실적 ${state.earnings_reaction ? "완료" : "필요"}`,
        `모델 ${state.model_update_note ? "완료" : "필요"}`,
        `체크 ${state.checklist ? "완료" : "필요"}`,
        `정보 ${state.recent_capture ? "있음" : "없음"}`,
      ].join(" · ");
      const portfolioText = (item.portfolios || []).join(", ") || "포트폴리오 미확인";
      const missingText = (item.missing_modules || []).length
        ? `부족: ${(item.missing_modules || []).join(", ")}`
        : "필수 분석 연결 완료";
      return [
        `${index + 1}. ${displayCompanyName(item)} · 완료율 ${toPercent(item.completion_rate)}`,
        `   ${marks}`,
        `   포함: ${portfolioText}`,
        `   ${missingText}`,
        `   다음 액션: ${item.next_action || "없음"}`,
      ].join("\n");
    });
    return [
      `포트폴리오 전체 분석 현황`,
      ``,
      value.summary || `고유 보유 종목 ${items.length}개를 점검했습니다.`,
      `분석 준비 완료: ${value.ready_count || 0}/${value.holding_count || items.length}`,
      `평균 완료율: ${toPercent(value.average_completion)}`,
      `기준 리포트 필요: ${value.needs_team_report_count || 0}개`,
      ``,
      `종목별 현황`,
      ...(lines.length ? lines : ["- 저장된 보유 종목이 없습니다."]),
    ].join("\n");
  }

  if (value.module === "portfolio_team_report_queue") {
    const queue = value.queue || [];
    const ready = value.already_ready || [];
    const blocked = value.blocked || [];
    const queueLines = queue.map((item, index) => {
      const portfolioText = (item.portfolios || []).join(", ") || "포트폴리오 미확인";
      const kpiText = (item.watch_kpis || []).slice(0, 4).join(", ") || "핵심 KPI 미등록";
      return [
        `${index + 1}. ${displayCompanyName(item)} · ${formatMoney(item.market_value, "KRW", "0원")}`,
        `   포함: ${portfolioText}`,
        `   중점 분석: ${item.analysis_focus || "사업 모델, 성장성, 리스크"}`,
        `   확인 KPI: ${kpiText}`,
        `   실행값: 투자 기간 ${item.investment_period || "3년"} · 지역 ${item.region || "US"} · 스타일 ${item.style || "균형형"}`,
      ].join("\n");
    });
    const readyLines = ready.slice(0, 8).map(
      (item, index) =>
        `${index + 1}. ${displayCompanyName(item)} · ${item.latest_team_report_date || "날짜 미확인"} · ${item.latest_team_report_file || "파일 미확인"}`
    );
    const blockedLines = blocked.map(
      (item, index) =>
        `${index + 1}. ${displayCompanyName(item)} · ${item.reason || "보류"} · ${item.message || "세부 메시지 없음"}`
    );
    return [
      `포트폴리오 기준 리포트 생성 큐`,
      ``,
      value.summary || `기준 리포트 생성 대상을 점검했습니다.`,
      `생성 필요: ${value.queue_count || queue.length}개`,
      `이미 준비: ${value.ready_count || ready.length}개`,
      `인증 보류: ${value.blocked_count || blocked.length}개`,
      ``,
      `우선 생성 대상`,
      ...(queueLines.length ? queueLines : ["- 기준 리포트가 필요한 보유 종목이 없습니다."]),
      ``,
      `이미 준비된 종목`,
      ...(readyLines.length ? readyLines : ["- 없음"]),
      ``,
      `인증 보류`,
      ...(blockedLines.length ? blockedLines : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "portfolio_import") {
    const warnings = value.warnings || [];
    const holdings = value.imported_holdings || [];
    return [
      `포트폴리오 파일 불러오기`,
      ``,
      `파일: ${value.file_name}`,
      `읽은 행: ${value.raw_rows || 0}개`,
      `인식한 보유 종목: ${holdings.length}개`,
      ``,
      `불러온 종목`,
      ...(holdings.length
        ? holdings.map(
            (item, index) =>
              `${index + 1}. ${displayCompanyName(item, "이름 없음")} · 평가금액 ${formatMoney(item.market_value, "KRW", "n/a")} · 비중 ${toPercent(item.weight)}`
          )
        : ["- 없음"]),
      ``,
      `안내`,
      ...(warnings.length ? warnings.map((item) => `- ${item}`) : ["- 없음"]),
    ].join("\n");
  }

  if (value.module === "interest_list") {
    return [
      `관심종목/섹터 저장 완료`,
      ``,
      `향후 매수 관심종목: ${(value.tickers || []).length}개`,
      `관심 섹터: ${(value.sectors || []).length}개`,
      `수정 시각: ${value.updated_at || "미확인"}`,
      `저장 위치: ${value.storage_path || "확인 안 됨"}`,
      ``,
      `향후 매수 관심종목`,
      ...((value.tickers || []).map(
        (item, index) =>
          `${index + 1}. ${displayCompanyName(item)} · ${translatePriority(item.priority)} · ${item.thesis || item.notes || "메모 없음"}`
      )),
      ``,
      `관심 섹터`,
      ...((value.sectors || []).map(
        (item, index) =>
          `${index + 1}. ${item.name} · ${item.region || "지역 미지정"} · ${translatePriority(item.priority)} · ${item.thesis || item.notes || "메모 없음"}`
      )),
    ].join("\n");
  }

  if (value.module === "interest_automation_board") {
    const tickerLines = (value.ticker_targets || []).slice(0, 12).map((item, index) => {
      const matches = item.market_journal_matches || [];
      const marketMatches = matches.length;
      const latestMarket = matches[0]
        ? `   시장일지 단서: ${compactOutputText(matches[0].summary || matches[0].title || matches[0].session_date, 150)}`
        : "";
      return [
        `${index + 1}. ${displayCompanyName(item)} · ${translatePriority(item.priority)} · ${item.source === "portfolio_holding" ? "보유종목" : "관심종목"}`,
        `   저장 자료 ${item.recent_document_count || 0}개 / RAG ${item.rag_document_count || 0}개 / 중복 의심 ${item.duplicate_suspected_count || 0}개 / 시장일지 연결 ${marketMatches}개`,
        `   검색 예시: ${(item.rag_query_examples || []).slice(0, 2).join(" · ") || "없음"}`,
        latestMarket,
        `   다음 액션: ${item.next_action || "후속 점검"}`,
      ].filter(Boolean).join("\n");
    });
    const sectorLines = (value.sector_targets || []).slice(0, 10).map((item, index) => {
      const matches = item.market_journal_matches || [];
      return [
        `${index + 1}. ${item.name} · ${item.region || "GLOBAL"} · ${translatePriority(item.priority)}`,
        `   저장 자료 ${item.recent_document_count || 0}개 / 중복 의심 ${item.duplicate_suspected_count || 0}개 / 시장일지 연결 ${matches.length}개`,
        `   검색 예시: ${(item.rag_query_examples || []).slice(0, 2).join(" · ") || "없음"}`,
        matches[0] ? `   시장일지 단서: ${compactOutputText(matches[0].summary || matches[0].title || matches[0].session_date, 150)}` : "",
      ].filter(Boolean).join("\n");
    });
    return [
      `관심종목/섹터 자동 수집 보드`,
      ``,
      `수집 대상: ${value.target_count || 0}개`,
      `관심/보유 종목: ${value.ticker_target_count || 0}개`,
      `관심 섹터: ${value.sector_target_count || 0}개`,
      `RAG 연결 종목: ${value.rag_connected_count || 0}개`,
      `논거 스냅샷 연결: ${value.thesis_connected_count || 0}개`,
      `최근 중복 의심 자료: ${value.duplicate_suspected_count || 0}개`,
      `저장 위치: ${value.storage_path || "저장 안 됨"}`,
      ``,
      `종목 수집 대상`,
      ...(tickerLines.length ? tickerLines : ["- 종목 수집 대상이 없습니다."]),
      ``,
      `섹터 수집 대상`,
      ...(sectorLines.length ? sectorLines : ["- 섹터 수집 대상이 없습니다."]),
      ``,
      `자동화 단계`,
      ...((value.automation_steps || []).map((item) => `- ${item}`)),
      ``,
      `다음 액션`,
      ...((value.next_actions || []).map((item) => `- ${item}`)),
    ].join("\n");
  }

  if (value.module === "market_close_review") {
    const entry = value.entry || {};
    const sourceOrigin = entry.source_origin === "naver_research_auto" ? "자동 반영" : "수동 입력";
    const marketAttachment = value.attachment || entry.attachment || null;
    const marketDocumentPreview = truncateDisplayText(
      cleanDocumentPreviewText(marketAttachment?.extracted_text || marketAttachment?.extraction_preview || ""),
      2200
    );
    return [
      `폐장 후 시장 리뷰`,
      ``,
      `시장: ${translateMarket(entry.market)}`,
      `기준일: ${entry.session_date || "미입력"}`,
      `입력 구분: ${sourceOrigin}${entry.source_title ? ` · ${entry.source_title}` : ""}`,
      `시장 심리: ${entry.sentiment || "확인 필요"}`,
      `리스크 레벨: ${entry.risk_level || "확인 필요"}`,
      `장세 판정: ${entry.regime || "확인 필요"}`,
      `누적 기록: ${value.history_count || 0}개`,
      ``,
      `핵심 동인`,
      ...((entry.key_drivers || []).map((item) => `- ${item}`)),
      ``,
      `섹터/테마 시사점`,
      ...((entry.sector_implications || []).map((item) => `- ${item}`)),
      ``,
      `시스템 자동 활용 초점`,
      ...((entry.auto_utilization_focus || []).map((item) => `- ${item}`)),
      ``,
      `관심종목/섹터 영향`,
      ...((entry.interest_implications || []).map((item) => `- ${item}`)),
      ``,
      `포트폴리오 활용`,
      ...((entry.portfolio_actions || []).map((item) => `- ${item}`)),
      ``,
      `누적 패턴`,
      ...((value.cumulative_patterns || []).map((item) => `- ${item}`)),
      ``,
      `다음 장 체크포인트`,
      ...((entry.next_session_watch || []).map((item) => `- ${item}`)),
      ``,
      `웹사이트 처리`,
      ...buildSourceUrlLines(value.source_url_processing),
      ``,
      `문서 추출 품질 리포트`,
      ...buildCaptureQualityLines(value.capture_quality),
      ...buildDocumentExtractionReport(marketAttachment),
      ``,
      `첨부 파일`,
      ...buildAttachmentLines(marketAttachment),
      ...(marketDocumentPreview
        ? [``, `문서 추출 미리보기`, ...formatPreviewBlock(marketDocumentPreview)]
        : []),
      ``,
      `태그: ${(entry.tags || []).join(", ") || "없음"}`,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "market_close_history") {
    return [
      `누적 시장 일지`,
      ``,
      `시장: ${translateMarket(value.market)}`,
      `기록 수: ${(value.entries || []).length}개`,
      `저장 위치: ${value.storage_path || "확인 안 됨"}`,
      ``,
      `최근 기록`,
      ...((value.entries || []).slice(0, 20).map(
        (entry, index) => {
          const sourceOrigin = entry.source_origin === "naver_research_auto" ? "자동" : "수동";
          return `${index + 1}. ${entry.session_date} · ${translateMarket(entry.market)} · ${sourceOrigin} · ${entry.regime} · 심리 ${entry.sentiment} · 리스크 ${entry.risk_level} · 태그 ${(entry.tags || []).join(", ") || "없음"}`;
        }
      )),
    ].join("\n");
  }

  if (value.module === "portfolio_risk_scan") {
    return [
      `포트폴리오 리스크 스캔`,
      ``,
      `포트폴리오: ${value.portfolio_name}`,
      `총액: ${formatMoney(value.portfolio_value, "KRW", "n/a")}`,
      `리스크 점수: ${value.risk_score}/100`,
      `상위 5개 비중: ${toPercent(value.top_five_weight)}`,
      ``,
      `주요 경고`,
      ...(value.warnings || []).map(
        (item) =>
          `- [${translateSeverity(item.severity)}] ${item.message} 조치: ${
            item.action
          }`
      ),
      ``,
      `섹터 집중도`,
      ...(value.sector_concentration || []).map(
        (item) => `- ${item.name}: ${toPercent(item.weight)}`
      ),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "reinforcement_portfolio_optimizer") {
    return [
      `강화학습형 포트폴리오 정책 최적화`,
      ``,
      `포트폴리오: ${value.portfolio_name}`,
      `목표 함수: ${translatePolicyObjective(value.objective)}`,
      `위험 성향: ${translatePolicyRiskProfile(value.risk_profile)}`,
      `학습 모드: ${translateLearningMode(value.learning_mode)}`,
      ``,
      `상태 변수`,
      ...((value.state_features || []).map((item) => `- ${item}`)),
      ``,
      `행동 공간`,
      ...((value.action_space || []).map((item) => `- ${item}`)),
      ``,
      `보상 함수`,
      ...((value.reward_function || []).map((item) => `- ${item}`)),
      ``,
      `정책 요약`,
      `${value.learned_policy_summary || "요약 없음"}`,
      ``,
      `비중 조정 후보`,
      ...((value.allocation_adjustments || []).length
        ? value.allocation_adjustments.map(
            (item, index) =>
              `${index + 1}. ${displayCompanyName(item)}: ${item.action} · 현재 ${toPercent(
                item.current_weight
              )} → 제안 ${toPercent(item.suggested_weight)} · ${item.rationale}`
          )
        : ["- 조정 후보 없음"]),
      ``,
      `리스크 가드레일`,
      ...((value.risk_guardrails || []).map((item) => `- ${item}`)),
      ``,
      `다음 학습 데이터`,
      ...((value.next_training_data_needed || []).map((item) => `- ${item}`)),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.module === "investor_research_checklist") {
    return [
      `리서치 체크리스트 투자 준비도 평가`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      `완료 항목: ${value.completed_count}/${value.total_count}`,
      `완료율: ${toPercent(value.completion_rate)}`,
      `준비도: ${translateReadiness(value.readiness_level)}`,
      ``,
      `평가`,
      `${value.readiness_summary}`,
      ``,
      `완료된 항목`,
      ...(value.completed_items || []).map((item) => `- ${item.label}`),
      ``,
      `다음 보강 항목`,
      ...(value.next_steps || []).map((item) => `- ${item}`),
      ``,
      `저장 데이터: ${value.storage?.relative_path || "저장 안 됨"}`,
    ].join("\n");
  }

  if (value.status === "success" && Array.isArray(value.documents) && value.key) {
    return [
      `RAG 문서 품질 검색`,
      ``,
      `키: ${value.key}`,
      `검색어: ${value.query || "전체"}`,
      `격리 문서 포함: ${value.include_low_quality ? "예" : "아니오"}`,
      `결과: ${value.count || 0}개`,
      ``,
      `문서`,
      ...((value.documents || []).length
        ? value.documents.map(
            (item, index) =>
              `${index + 1}. ${item.is_injectable ? "[자동 주입 가능]" : "[격리]"} 품질 ${
                item.quality_score ?? "n/a"
              }점 · ${translateReportType(item.report_type)} · ${
                item.source_date || "날짜 없음"
              } · ${item.title || item.source_file_name}\n   요약: ${translateSummary(
                item.summary || item.content_excerpt || "요약 없음"
              )}\n   플래그: ${
                (item.quality_flags || []).map(translateQualityFlag).join(", ") ||
                "없음"
              }`
          )
        : ["- 조회된 문서가 없습니다."]),
    ].join("\n");
  }

  if (value.status === "success" && Array.isArray(value.documents) && value.updated_count !== undefined) {
    return [
      `RAG 문서 색인 갱신`,
      ``,
      `갱신 문서: ${value.updated_count}개`,
      `대상 키: ${(value.ticker_names || value.company_names || []).join(", ") || "저장 키 기준 갱신"}`,
      ``,
      `최근 색인`,
      ...((value.documents || []).slice(0, 12).map((item, index) => `${index + 1}. ${item}`)),
    ].join("\n");
  }

  if (value.provider) {
    return [
      `상태 확인 결과`,
      ``,
      `데이터 프로바이더: ${value.provider.mode}`,
      `자동 주입: ${
        value.provider.auto_inject_analysis_data ? "켜짐" : "꺼짐"
      }`,
      `저장된 보고서 수: ${value.manifest_count}`,
      ``,
      `상세 원본`,
      JSON.stringify(value, null, 2),
    ].join("\n");
  }

  if (value.files && value.ticker) {
    return [
      `저장 데이터`,
      ``,
      `대상: ${displayCompanyName(value)}`,
      `공식 인증 파일: ${value.verified_file_count || 0}개`,
      `레거시 파일: ${value.legacy_file_count || 0}개`,
      ``,
      `경고`,
      ...((value.data_warnings || []).length
        ? value.data_warnings.map((item) => `- ${item}`)
        : ["- 표시할 경고가 없습니다."]),
      ``,
      `저장 데이터`,
      ...((value.files || []).map(
        (file, index) =>
          `${index + 1}. [${file.status_label || "상태 미확인"}] ${translateReportType(file.report_type)} | ${file.file_name}`
      )),
    ].join("\n");
  }

  return `\`\`\`json\n${JSON.stringify(value, null, 2)}\n\`\`\``;
}

function tabHelpText(tabName) {
  const messages = {
    dashboard:
      "대시보드 탭입니다.\n\n티커를 입력하면 저장된 리포트, 체크리스트 준비도, 최근 캡처, 매매/실적 분석 상태와 다음 추천 액션을 한 화면에서 봅니다.",
    team:
      "팀 리포트 탭입니다.\n\n티커를 입력하고 `7개 스킬 팀 리포트 실행`을 누르면 데이터 자동 주입, 7개 스킬 분석, 투자 논거 저장까지 실행됩니다.",
    trade:
      "매매 전략 탭입니다.\n\n현재가, 스타일, 허용 리스크를 입력하면 진입 구간, 손절, 목표가, 손익비와 포지션 가이드를 생성합니다.",
    chart:
      "차트분석 탭입니다.\n\n네이버 증권 국내 종목 일별 시세로 거래량, 볼린저 밴드, 이동평균선, MACD, RSI 14, DMI를 계산해 매매전략에 쓸 차트 상태를 저장합니다.",
    earnings:
      "실적 분석 탭입니다.\n\n분기 실적 수치, 주가 반응, 가이던스 변경을 입력하면 시장 반응 패턴과 다음 실적 전 추적 항목을 생성합니다.",
    macro:
      "매크로 분석 탭입니다.\n\n금리, 환율, 정책, 수급, 원자재 같은 거시 변수를 정리하고 유리한 섹터와 리스크 체크포인트를 연결합니다.",
    sector:
      "섹터 발굴 탭입니다.\n\n금리, AI, 에너지 가격 같은 매크로 환경을 입력하면 유망 섹터와 후보 기업을 저장 가능한 리포트로 생성합니다.",
    compounder:
      "복리 성장주 탭입니다.\n\n매출 성장, 마진, 경쟁 우위, 확장성, 시가총액 조건으로 장기 복리 후보를 선별합니다.",
    capture:
      "정보 입력 탭입니다.\n\n종목 뉴스, 리포트 요약, 직접 메모뿐 아니라 티커 없는 전체 시황, 섹터 전망, 거시 경제, 정책, 금리, 수급 자료도 자동 분류해 저장합니다.",
    news:
      "뉴스 탭입니다.\n\n기사와 뉴스 링크를 독립 인박스에 먼저 저장해 중복과 본문 품질을 확인하고, 필요한 자료만 투자 논거와 RAG 메모리로 승격합니다.",
    llmBridge:
      "LLM 연동 탭입니다.\n\nChatGPT/Gemini 웹 채팅창을 자동 조작하지 않고, 분석 프롬프트 생성과 응답 붙여넣기 저장 흐름으로 안전하게 리서치 메모리에 연결합니다.",
    marketClose:
      "시장 일지 탭입니다.\n\n한국/미국 폐장 후 시장 요약을 입력하면 심리, 리스크, 장세를 판정하고 누적 패턴을 투자 액션으로 연결합니다.",
    portfolio:
      "내 포트폴리오 탭입니다.\n\n현재 매수해서 보유 중인 종목을 저장/불러오기/편집하고, 같은 입력값으로 단일 종목, 섹터, 테마 집중도와 리스크 점수를 계산합니다.",
    interests:
      "관심종목/섹터 탭입니다.\n\n아직 보유하지 않았지만 향후 매수를 기대하는 종목과 관심 섹터를 지역·우선순위·투자 논거와 함께 관리합니다.",
    checklist:
      "체크리스트 탭입니다.\n\n16개 항목을 체크하면 완료율이 즉시 바뀌고, `완성된 항목 분석`으로 투자 준비도와 다음 보강 단계를 생성합니다.",
    memory:
      "저장 데이터 탭입니다.\n\n티커나 포트폴리오 키를 입력해 저장 데이터를 조회하거나 전체 저장 목록을 확인합니다.",
  };
  return messages[tabName] || "작업을 선택하세요.";
}

function dashboardCardHint(label, value) {
  const hints = {
    "기준 리포트": value === "있음" ? "기준 투자 논거가 저장되어 있습니다." : "팀 리포트로 투자 논거를 먼저 만드세요.",
    "체크리스트": value === "미작성" ? "16개 항목을 체크해 준비도를 확인하세요." : "완료율과 준비도 기준으로 보강하세요.",
    "매매 전략": value === "있음" ? "진입, 손절, 목표가 계획이 있습니다." : "현재가 기준 매매 계획이 필요합니다.",
    "실적 분석": value === "있음" ? "실적 반응과 추적 항목이 있습니다." : "최근 실적 반응을 연결하세요.",
    "최근 캡처": value === "있음" ? "새 정보가 기존 논거에 연결되어 있습니다." : "뉴스나 메모를 저장해 논거 변화를 추적하세요.",
    "정책 최적화": value === "있음" ? "포트폴리오 비중 조정 후보가 저장되어 있습니다." : "저장 포트폴리오 기준 정책 최적화를 실행하세요.",
  };
  return escapeHtml(hints[label] || "상태를 확인하세요.");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function translateQuality(value) {
  const map = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return map[value] || value || "확인 필요";
}

function translateQualityFlag(value) {
  const map = {
    low_data_quality: "데이터 품질 낮음",
    missing_inputs: "입력 누락",
    insufficient_data: "데이터 부족",
    deferred_judgement: "판정 보류",
    sufficient_evidence: "증거 충분",
    missing_earnings_date: "실적일 누락",
    missing_price_reaction: "주가 반응 누락",
    missing_next_guidance: "다음 가이던스 누락",
  };
  return map[value] || value || "플래그 없음";
}

function translateImpact(value) {
  const map = {
    강화: "강화",
    약화: "약화",
    혼합: "혼합",
    중립: "중립",
    "데이터 부족": "데이터 부족",
    strengthens: "강화",
    weakens: "약화",
    mixed: "혼합",
    neutral: "중립",
    insufficient_data: "데이터 부족",
  };
  return map[value] || "분석 안 함";
}

function translateReadiness(value) {
  const map = {
    High: "높음",
    Medium: "보통",
    Low: "낮음",
    높음: "높음",
    보통: "보통",
    낮음: "낮음",
  };
  return map[value] || value || "확인 필요";
}

function translateSeverity(value) {
  const map = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return map[value] || value || "확인 필요";
}

function translatePriority(value) {
  const map = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return map[String(value || "").toLowerCase()] || value || "보통";
}

function translatePolicyObjective(value) {
  const map = {
    risk_adjusted_return: "위험조정수익률",
    drawdown_control: "낙폭 통제",
    compound_growth: "장기 복리 성장",
  };
  return map[value] || value || "확인 필요";
}

function translatePolicyRiskProfile(value) {
  const map = {
    balanced: "균형형",
    conservative: "보수적",
    aggressive: "공격적",
  };
  return map[value] || value || "확인 필요";
}

function translateLearningMode(value) {
  const map = {
    offline_policy_scaffold: "오프라인 정책 학습 준비",
  };
  return map[value] || value || "확인 필요";
}

function formatListItem(item, index) {
  const summary = item.summary ? translateSummary(item.summary) : null;
  return [
    `${index + 1}. ${item.file_name || item.type || item.ticker || "항목"}`,
    item.relative_path ? `경로: ${item.relative_path}` : null,
    summary ? `요약: ${summary}` : null,
  ]
    .filter(Boolean)
    .join("\n");
}

function translateProviderMode(value) {
  const map = {
    mock: "모의 데이터",
    fmp: "FMP 실제 데이터",
  };
  return map[value] || value || "확인 필요";
}

function translateLookupStatus(value) {
  const map = {
    success: "성공",
    failed: "실패",
    empty: "빈 응답",
    skipped: "건너뜀",
  };
  return map[value] || value || "확인 필요";
}

function translateDataLabel(value) {
  const map = {
    official_company_profile: "공식 회사 프로필",
    linked_workspace_reports: "연결 저장 리포트",
    latest_thesis_snapshot: "최신 투자 논거 스냅샷",
    rag_memory_document_1: "연결 리서치 메모리 1",
    rag_memory_document_2: "연결 리서치 메모리 2",
    rag_memory_document_3: "연결 리서치 메모리 3",
    rag_memory_document_4: "연결 리서치 메모리 4",
    rag_cross_scope_market: "누적 시장 메모리",
    rag_cross_scope_macro: "누적 거시 메모리",
    rag_cross_scope_sector: "누적 섹터 메모리",
    rag_cross_scope_policy: "누적 정책 메모리",
    rag_cross_scope_rates: "누적 금리 메모리",
    rag_cross_scope_flows: "누적 수급 메모리",
    last_price: "최근 가격",
    market_cap: "시가총액",
    volume: "거래량",
    average_volume: "평균 거래량",
    estimated_volatility: "추정 변동성",
    revenue: "매출",
    revenue_growth: "매출 성장률",
    gross_margin: "매출총이익률",
    operating_margin: "영업이익률",
    net_margin: "순이익률",
    free_cash_flow_margin: "잉여현금흐름 마진",
    net_debt_to_ebitda: "순부채/EBITDA",
    pe_ratio: "PER",
    market_data_provider_warning: "시장 데이터 경고",
    financial_data_provider_warning: "재무 데이터 경고",
    data_provider_limitation: "데이터 제한",
  };
  return map[value] || value || "알 수 없음";
}

function translateSourceType(value) {
  const map = {
    official_filing: "공식 공시",
    earnings_release: "실적 발표",
    ir_presentation: "IR 자료",
    market_price: "시장 가격",
    financial_data: "재무 데이터",
    news: "뉴스",
    analyst_report: "애널리스트 리포트",
    user_memo: "직접 메모",
    macro_research: "거시/경제 전망",
    sector_research: "섹터/산업 전망",
    market_research: "전체 시황/투자 동향",
    policy_research: "정책/규제 전망",
    rates_research: "금리/물가 전망",
    flows_research: "수급/자금 흐름",
    unassigned_inbox: "미분류 자료",
    research_memory: "리서치 메모리",
    other: "기타",
  };
  return map[value] || value || "출처 미확인";
}

function translateDossierRefreshStatus(value) {
  const map = {
    deferred: "후속 큐로 분리",
    refreshed: "완료",
    failed: "실패 - 오류 로그 확인 필요",
  };
  return map[value] || value || "후속 큐로 분리";
}

function translateDashboardStatus(value) {
  const map = {
    "있음": "있음",
    "필요": "필요",
    "미작성": "미작성",
    "없음": "없음",
  };
  return map[value] || value || "확인 필요";
}

function translateReportType(value) {
  const map = {
    "collaborative-team-report": "팀 리포트",
    "institutional-stock-breakdown": "기관급 분석",
    "smart-trade-setup": "매매 전략",
    "earnings-reaction": "실적 분석",
    "research-capture": "정보 입력",
    "thesis-impact-review": "투자 논거 영향도",
    "rag-query-synthesis": "검색 결과 합성",
    "research-checklist": "체크리스트",
    "portfolio-risk-scan": "포트폴리오 리스크",
    "reinforcement-portfolio-optimizer": "정책 최적화",
    "sector-opportunity": "섹터 발굴",
    "long-term-compounder": "복리 성장주",
    "compounder-finder": "복리 성장주",
    "market-close-review": "시장일지",
    "dossier-synthesis": "Dossier 합성",
    "chart-analysis": "차트 분석",
    "daily-dossier-brief": "일일 브리핑",
  };
  return map[value] || value || "알 수 없음";
}

function translateStyle(value) {
  const map = {
    growth: "성장주",
    balanced: "균형형",
    value: "가치주",
    trading: "트레이딩",
  };
  return map[value] || value || "확인 필요";
}

function translateRegion(value) {
  const map = {
    US: "미국",
    KR: "한국",
  };
  return map[value] || value || "확인 필요";
}

function translateMarket(value) {
  const map = {
    US: "미국",
    KR: "한국",
    GLOBAL: "글로벌",
    ALL: "전체",
  };
  return map[value] || value || "확인 필요";
}

function translateTradeStyle(value) {
  const map = {
    scalp: "아주 짧게 매매",
    day: "하루 안에 매매",
    swing: "단기 보유(며칠~몇 주)",
    position: "중기 보유(몇 주~몇 달)",
  };
  return map[value] || value || "확인 필요";
}

function translatePeriod(value) {
  if (!value) {
    return "확인 필요";
  }
  return String(value)
    .replace("years", "년")
    .replace("year", "년")
    .replace("months", "개월")
    .replace("month", "개월");
}

function translateSummary(value) {
  return String(value)
    .replace(/risk score ([0-9]+)\/100, top five weight ([0-9]+)%/i, "리스크 점수 $1/100, 상위 5개 비중 $2%")
    .replace(/'strengthens'로 분류되었습니다\./i, "'강화'로 분류되었습니다.")
    .replace(/'weakens'로 분류되었습니다\./i, "'약화'로 분류되었습니다.")
    .replace(/'mixed'로 분류되었습니다\./i, "'혼합'으로 분류되었습니다.")
    .replace(/'neutral'로 분류되었습니다\./i, "'중립'으로 분류되었습니다.")
    .replace(/'insufficient_data'로 분류되었습니다\./i, "'데이터 부족'으로 분류되었습니다.")
    .replace(/classified as 'strengthens'/i, "'강화'로 분류")
    .replace(/classified as 'weakens'/i, "'약화'로 분류")
    .replace(/classified as 'mixed'/i, "'혼합'으로 분류")
    .replace(/classified as 'neutral'/i, "'중립'으로 분류")
    .replace(/Strong demand commentary and margin expansion appear positive for the bull case\./i, "강한 수요와 마진 개선은 강세 시나리오에 긍정적인 정보입니다.")
    .replace(/bull case/gi, "강세 시나리오")
    .replace(/Bull\/Base\/Bear/g, "강세/기준/약세");
}

function sourceWarningLines(injectedData = []) {
  const warnings = injectedData
    .filter((item) => item.label === "data_provider_limitation")
    .map((item) => `- ${item.value}`);
  return warnings.length ? warnings : ["- 표시할 데이터 경고가 없습니다."];
}

function translateCaptureTag(tag) {
  const labels = {
    auto_classified: "자동 분류",
    file_input: "파일 입력",
    earnings: "실적",
    valuation: "밸류에이션",
    risk: "리스크",
    growth: "성장",
    macro: "거시",
    rates: "금리/물가",
    flows: "수급",
    market: "시장",
    sector: "섹터",
    policy: "정책",
    margin: "마진",
  };
  const value = String(tag || "").trim();
  if (!value) {
    return "";
  }
  if (labels[value]) {
    return labels[value];
  }
  if (value.startsWith("research_scope:")) {
    return `자료 범위 ${value.replace("research_scope:", "").toUpperCase()}`;
  }
  if (value.startsWith("auto_ticker:")) {
    return `분류 단서 ${value.replace("auto_ticker:", "")}`;
  }
  return value;
}

function formatCaptureTagList(tags = []) {
  const translated = tags.map(translateCaptureTag).filter(Boolean);
  return translated.length ? translated.join(", ") : "없음";
}

function buildCaptureClassificationReason(value, scopeLabels = {}) {
  const capturedTicker = value.captured_item?.ticker;
  const tags = value.captured_item?.tags || [];
  const autoTag = tags.find((tag) => String(tag || "").startsWith("auto_ticker:"));
  const autoReason = autoTag ? autoTag.replace("auto_ticker:", "") : "본문/파일명 단서";
  if (scopeLabels[capturedTicker]) {
    return `${scopeLabels[capturedTicker]}로 분류했습니다. 단서: ${autoReason}.`;
  }
  if (capturedTicker) {
    return `${capturedTicker} 관련 종목 자료로 분류했습니다. 단서: ${autoReason}.`;
  }
  return `명확한 티커를 찾지 못해 미분류 투자 자료로 보관했습니다. 단서: ${autoReason}.`;
}

function translateDuplicateReason(reason) {
  const labels = {
    source_url_exact_match: "같은 원문 URL",
    content_hash_exact_match: "같은 본문",
    title_body_similarity: "제목·본문 유사",
    exact_match: "정확 일치",
    no_match: "일치 없음",
  };
  return labels[reason] || reason || "미확인";
}

function buildResearchCaptureWorkLines(value, scopeLabels = {}) {
  const capturedTicker = value.captured_item?.ticker;
  const classification = scopeLabels[capturedTicker] || `종목 자료 · ${capturedTicker || "미확정"}`;
  const attachment = value.attachment || null;
  const lines = [];

  if (value.input_preview) {
    lines.push(`텍스트 입력 ${formatNumber(String(value.input_preview).length)}자를 수집했습니다.`);
  } else {
    lines.push("텍스트 입력 없이 첨부 파일 중심으로 처리했습니다.");
  }

  if (attachment) {
    lines.push(
      `첨부 파일 ${attachment.file_name || "이름 없음"}을 저장하고 메타데이터를 분석했습니다.`
    );
    if (attachment.text_extraction) {
      lines.push(`문서 처리: ${attachment.text_extraction}`);
    }
    if (value.document_preview || attachment.extracted_text) {
      lines.push("문서 본문을 추출해 자동 분류와 요약, 기존 논거 영향도 평가에 반영했습니다.");
    }
  }

  lines.push(`자동 분류 결과를 ${classification}로 확정했습니다.`);
  lines.push(`출처 유형을 ${translateSourceType(value.captured_item?.source_type)}로 판정했습니다.`);
  lines.push(
    `신뢰도 ${toPercent(value.captured_item?.confidence)} 값을 분석 가중치로 반영했습니다.`
  );

  if (value.linked_impact) {
    lines.push(
      `기존 투자 논거와 비교해 영향도를 ${translateImpact(value.linked_impact.overall_impact)}로 평가했습니다.`
    );
  } else {
    lines.push("종목 영향도 분석은 실행하지 않았거나, 시장/섹터 자료로 별도 메모리에 적재했습니다.");
  }

  if (value.duplicate_check?.is_duplicate_suspected) {
    lines.push(
      `기존 저장 자료와 ${translateDuplicateReason(value.duplicate_check.reason)} 기준으로 중복 가능성을 표시했습니다.`
    );
  } else if (value.duplicate_check) {
    lines.push(`기존 저장 자료 ${formatNumber(value.duplicate_check.checked_count || 0)}개와 중복 여부를 점검했습니다.`);
  }

  if (value.storage?.relative_path) {
    lines.push(`저장 데이터를 생성했습니다: ${value.storage.relative_path}`);
  } else {
    lines.push("저장 데이터는 생성되지 않았습니다.");
  }

  if (value.rag_document?.document_id) {
    lines.push("저장 직후 RAG 검색 색인에 반영했습니다.");
  }

  return lines;
}

function buildAttachmentLines(attachment) {
  if (!attachment) {
    return ["- 첨부 파일 없음"];
  }
  const quality = Number(attachment.extraction_quality);
  const scopeLines = buildInferredInvestmentScopeLines(attachment.inferred_investment_scope);
  const lines = [
    `- 처리 판정: ${describeExtractionQuality(attachment)}`,
    `- 파일명: ${attachment.file_name || "이름 없음"}`,
    `- MIME: ${attachment.mime_type || "알 수 없음"}`,
    `- 문서 유형: ${attachment.document_type || "미확인"}`,
    `- 크기: ${formatFileSize(attachment.size || attachment.declared_size)}`,
    `- 저장 경로: ${attachment.relative_path || "저장 경로 없음"}`,
    `- 텍스트 추출: ${attachment.text_extraction || "추출 정보 없음"}`,
    `- ${attachmentOcrStatusLine(attachment)}`,
  ];
  if (Number.isFinite(quality)) {
    lines.push(`- 추출 품질: ${Math.round(quality * 100)}% / 본문 ${formatNumber(attachment.extraction_char_count || 0)}자`);
  }
  if (Array.isArray(attachment.extraction_warnings) && attachment.extraction_warnings.length) {
    lines.push(`- 추출 경고: ${attachment.extraction_warnings.join(" / ")}`);
  }
  if (scopeLines.length) {
    lines.push(...scopeLines);
  }
  return lines;
}

function buildInferredInvestmentScopeLines(scope) {
  if (!scope || typeof scope !== "object") {
    return [];
  }
  const themeLabels = Array.isArray(scope.theme_candidates)
    ? scope.theme_candidates.map((item) => item?.label).filter(Boolean)
    : [];
  const interests = Array.isArray(scope.matched_interest_tickers)
    ? scope.matched_interest_tickers.map((item) => item?.company_name || item?.ticker).filter(Boolean)
    : [];
  const sectors = Array.isArray(scope.matched_interest_sectors)
    ? scope.matched_interest_sectors.map((item) => item?.name).filter(Boolean)
    : [];
  const holdings = Array.isArray(scope.matched_portfolio_holdings)
    ? scope.matched_portfolio_holdings.map((item) => item?.company_name || item?.ticker).filter(Boolean)
    : [];
  const lines = [];
  if (themeLabels.length) {
    lines.push(`- 관심 범위 추정: ${uniqueList(themeLabels).join(", ")}`);
  }
  if (interests.length) {
    lines.push(`- 관심종목 매칭: ${uniqueList(interests).slice(0, 10).join(", ")}`);
  }
  if (sectors.length) {
    lines.push(`- 관심섹터 매칭: ${uniqueList(sectors).slice(0, 10).join(", ")}`);
  }
  if (holdings.length) {
    lines.push(`- 보유종목 매칭: ${uniqueList(holdings).slice(0, 10).join(", ")}`);
  }
  if (scope.next_action) {
    lines.push(`- 투자 반영 다음 조치: ${scope.next_action}`);
  }
  return lines;
}

function uniqueList(values = []) {
  return Array.from(new Set(values.map((value) => String(value || "").trim()).filter(Boolean)));
}

function truncateDisplayText(value, maxChars = 1800) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  if (text.length <= maxChars) {
    return text;
  }
  return `${text.slice(0, maxChars).trim()}\n\n[화면 미리보기는 앞부분 ${formatNumber(maxChars)}자만 표시합니다. 전체 원문은 저장 데이터에 보관했습니다.]`;
}

function formatPreviewBlock(value) {
  const text = String(value || "").replace(/```/g, "'''");
  return ["```text", text, "```"];
}

function formatFileSize(value) {
  const size = Number(value);
  if (!Number.isFinite(size) || size < 0) {
    return "n/a";
  }
  if (size < 1024) {
    return `${formatNumber(size)} bytes`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toLocaleString("ko-KR", { maximumFractionDigits: 1 })} KB`;
  }
  return `${(size / (1024 * 1024)).toLocaleString("ko-KR", { maximumFractionDigits: 1 })} MB`;
}

function toPercent(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return `${Math.round(Number(value) * 100).toLocaleString("ko-KR")}%`;
}

function formatNumber(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toLocaleString("ko-KR");
}

function formatCompounderMarketCap(value, region, emptyValue = "n/a") {
  if (value === undefined || value === null || value === "" || Number.isNaN(Number(value))) {
    return emptyValue;
  }
  const unit = String(region || "").toUpperCase().startsWith("KR") || String(region || "").includes("한국")
    ? "억원"
    : "백만 달러";
  return `${formatNumber(value)} ${unit}`;
}

function formatMoney(value, currency = "KRW", emptyValue = "") {
  if (value === undefined || value === null || value === "" || Number.isNaN(Number(value))) {
    return emptyValue;
  }
  const numeric = Number(value);
  const normalizedCurrency = normalizeCurrency(currency);
  const absoluteValue = Math.abs(numeric);
  const formatted = absoluteValue.toLocaleString("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: normalizedCurrency === "USD" ? 4 : 0,
  });
  const sign = numeric < 0 ? "-" : "";
  if (normalizedCurrency === "USD") {
    return `${sign}$${formatted}`;
  }
  return `${sign}${formatted}원`;
}

function formatTradePrice(value, currency = "KRW") {
  return formatMoney(value, currency, "n/a");
}

function formatNullable(value) {
  if (value === undefined || value === null || value === "") {
    return "n/a";
  }
  if (!Number.isNaN(Number(value))) {
    return formatNumber(value);
  }
  return String(value);
}

function formatDateTime(value) {
  if (!value) {
    return "날짜 없음";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getCheckedChecklistItems() {
  return Array.from(
    elements.checklistForm.querySelectorAll('input[name="checkedItems"]:checked')
  ).map((item) => item.value);
}

function updateChecklistProgress() {
  const completed = getCheckedChecklistItems().length;
  const percent = Math.round((completed / CHECKLIST_TOTAL) * 100);
  elements.checklistProgressText.textContent = `${completed}/${CHECKLIST_TOTAL} 완료`;
  elements.checklistProgressPercent.textContent = `${percent}%`;
  elements.checklistProgressBar.style.width = `${percent}%`;
}
