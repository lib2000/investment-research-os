export function createPortfolioApi(apiClient) {
  return {
    list() {
      return apiClient.request("/api/v1/portfolios");
    },
    get(portfolioName) {
      return apiClient.request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}`);
    },
    save({
      portfolioName,
      holdings = [],
      portfolioValue = null,
      maxSinglePositionWeight = 0.2,
      maxSectorWeight = 0.35,
      maxThemeWeight = 0.4,
      notes = "",
    }) {
      return apiClient.request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}`, {
        method: "POST",
        body: JSON.stringify({
          portfolio_name: portfolioName,
          holdings,
          portfolio_value: portfolioValue,
          max_single_position_weight: maxSinglePositionWeight,
          max_sector_weight: maxSectorWeight,
          max_theme_weight: maxThemeWeight,
          notes,
        }),
      });
    },
    delete(portfolioName) {
      return apiClient.request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}`, {
        method: "DELETE",
      });
    },
    riskScan({
      portfolioName,
      holdings,
      portfolioValue = null,
      maxSinglePositionWeight = 0.2,
      maxSectorWeight = 0.35,
      maxThemeWeight = 0.4,
      saveResult = true,
    }) {
      return apiClient.request("/api/v1/portfolio/risk-scan", {
        method: "POST",
        body: JSON.stringify({
          portfolio_name: portfolioName,
          holdings,
          portfolio_value: portfolioValue,
          max_single_position_weight: maxSinglePositionWeight,
          max_sector_weight: maxSectorWeight,
          max_theme_weight: maxThemeWeight,
          save_result: saveResult,
        }),
      });
    },
    connectivity() {
      return apiClient.request("/api/v1/portfolios/connectivity");
    },
    analysisStatus() {
      return apiClient.request("/api/v1/portfolios/analysis-status");
    },
    teamReportQueue() {
      return apiClient.request("/api/v1/portfolios/team-report-queue");
    },
    importFile({ fileName, contentBase64 }) {
      return apiClient.request("/api/v1/portfolios/import-file", {
        method: "POST",
        body: JSON.stringify({
          file_name: fileName,
          content_base64: contentBase64,
        }),
      });
    },
  };
}
