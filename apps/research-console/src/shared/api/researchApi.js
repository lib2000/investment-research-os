export function createResearchApi(apiClient) {
  return {
    dashboard(ticker) {
      return apiClient.request(`/api/v1/dashboard/${encodeURIComponent(normalizeTicker(ticker))}`);
    },
    runTeamReport({
      ticker,
      investmentPeriod = "3년",
      region = "US",
      style = "balanced",
      focusArea = "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크",
      autoInjectData = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/analysis/team-report/run", {
        method: "POST",
        body: JSON.stringify({
          ticker: normalizeTicker(ticker),
          investment_period: investmentPeriod,
          region,
          style,
          focus_area: focusArea,
          include_trade_setup: true,
          include_compounder_screen: true,
          auto_inject_data: autoInjectData,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
    autoCapture({
      rawContent,
      fileName = null,
      fileMimeType = null,
      fileSize = null,
      fileContentBase64 = null,
      runThesisImpact = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/research-memory/auto-capture", {
        method: "POST",
        body: JSON.stringify({
          raw_content: rawContent,
          file_name: fileName,
          file_mime_type: fileMimeType,
          file_size: fileSize,
          file_content_base64: fileContentBase64,
          run_thesis_impact: runThesisImpact,
          save_result: saveResult,
        }),
      });
    },
    saveMarketCloseReview({
      market = "US",
      sessionDate = null,
      rawSummary,
      fileName = null,
      fileMimeType = null,
      fileSize = null,
      fileContentBase64 = null,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/market-close-journal/review", {
        method: "POST",
        body: JSON.stringify({
          market,
          session_date: sessionDate,
          raw_summary: rawSummary,
          file_name: fileName,
          file_mime_type: fileMimeType,
          file_size: fileSize,
          file_content_base64: fileContentBase64,
          save_result: saveResult,
        }),
      });
    },
    marketCloseHistory(market = "ALL") {
      return apiClient.request(`/api/v1/market-close-journal?market=${encodeURIComponent(market)}`);
    },
    fetchInterests() {
      return apiClient.request("/api/v1/interests");
    },
    saveInterests({ tickers = [], sectors = [] }) {
      return apiClient.request("/api/v1/interests", {
        method: "PUT",
        body: JSON.stringify({ tickers, sectors }),
      });
    },
    fetchResearchMemoryFiles(key = "PL") {
      return apiClient.request(`/api/v1/research-memory/${encodeURIComponent(normalizeResearchKey(key))}`);
    },
    fetchResearchMemoryFile({ key = "PL", fileName }) {
      return apiClient.request(
        `/api/v1/research-memory/${encodeURIComponent(normalizeResearchKey(key))}/files/${encodeURIComponent(
          fileName
        )}`
      );
    },
    fetchResearchManifest() {
      return apiClient.request("/api/v1/research-memory");
    },
    backfillRagMemoryDocuments() {
      return apiClient.request("/api/v1/rag/memory/backfill", {
        method: "POST",
      });
    },
    searchRagMemoryDocuments({ key = "PL", query = "", limit = 8, includeLowQuality = false }) {
      const params = new URLSearchParams({
        limit: String(limit),
        include_low_quality: String(Boolean(includeLowQuality)),
      });
      if (query?.trim()) {
        params.set("query", query.trim());
      }
      return apiClient.request(`/api/v1/rag/memory/search/${encodeURIComponent(normalizeResearchKey(key))}?${params}`);
    },
    runSmartTradeSetup({
      ticker,
      currentPrice,
      style = "swing",
      riskTolerance = "보통",
      portfolioSize = null,
      riskPerTradePct = 0.01,
      marketStructure = null,
      autoInjectData = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/analysis/modules/smart-trade-setup/run", {
        method: "POST",
        body: JSON.stringify({
          ticker: normalizeTicker(ticker),
          current_price: currentPrice,
          style,
          risk_tolerance: riskTolerance,
          portfolio_size: portfolioSize,
          risk_per_trade_pct: riskPerTradePct,
          market_structure: marketStructure,
          auto_inject_data: autoInjectData,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
    runEarningsReaction({
      ticker,
      quarter,
      earningsReportDate = null,
      priceReaction = "",
      previousEarningsDate = null,
      previousEarningsSummary = null,
      nextEarningsDate = null,
      nextEarningsGuidance = null,
      epsReported = null,
      epsExpected = null,
      revenueReported = null,
      revenueExpected = null,
      guidanceChange = "유지",
      managementTone = null,
      marketContext = null,
      keyNumbers = {},
      autoInjectData = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/analysis/modules/earnings-reaction/run", {
        method: "POST",
        body: JSON.stringify({
          ticker: normalizeTicker(ticker),
          quarter,
          earnings_report_date: earningsReportDate,
          price_reaction: priceReaction,
          previous_earnings_date: previousEarningsDate,
          previous_earnings_summary: previousEarningsSummary,
          next_earnings_date: nextEarningsDate,
          next_earnings_guidance: nextEarningsGuidance,
          eps_reported: epsReported,
          eps_expected: epsExpected,
          revenue_reported: revenueReported,
          revenue_expected: revenueExpected,
          guidance_change: guidanceChange,
          management_tone: managementTone,
          market_context: marketContext,
          key_numbers: keyNumbers,
          auto_inject_data: autoInjectData,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
    runSectorOpportunity({
      macroEnvironment,
      period = "6개월",
      region = "US",
      style = "균형형",
      autoInjectData = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/analysis/modules/sector-opportunity/run", {
        method: "POST",
        body: JSON.stringify({
          macro_environment: macroEnvironment,
          period,
          region,
          style,
          auto_inject_data: autoInjectData,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
    runLongTermCompounder({
      screeningCriteria,
      minMarketCap = null,
      maxMarketCap = null,
      sector = "전체",
      region = "US",
      style = "퀄리티 성장",
      autoInjectData = true,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/analysis/modules/long-term-compounder/run", {
        method: "POST",
        body: JSON.stringify({
          screening_criteria: screeningCriteria,
          min_market_cap: minMarketCap,
          max_market_cap: maxMarketCap,
          sector,
          region,
          style,
          auto_inject_data: autoInjectData,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
    assessResearchChecklist({
      ticker,
      checkedItems,
      notes = null,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/research/checklist/assess", {
        method: "POST",
        body: JSON.stringify({
          ticker: normalizeTicker(ticker),
          checked_items: checkedItems,
          notes,
          realtime_data: [],
          save_result: saveResult,
        }),
      });
    },
  };
}

function normalizeTicker(value) {
  return String(value || "PL").trim().toUpperCase();
}

function normalizeResearchKey(value) {
  return String(value || "PL").trim();
}
