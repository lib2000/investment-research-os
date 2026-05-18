import { useMemo, useState } from "react";
import { createApiClient } from "../shared/api/client.js";
import { createPortfolioApi } from "../shared/api/portfolioApi.js";
import { createResearchApi } from "../shared/api/researchApi.js";
import { ChecklistPage } from "../features/checklist/ChecklistPage.jsx";
import { CompounderPage } from "../features/compounder/CompounderPage.jsx";
import { CapturePage } from "../features/capture/CapturePage.jsx";
import { DashboardPage } from "../features/dashboard/DashboardPage.jsx";
import { EarningsPage } from "../features/earnings/EarningsPage.jsx";
import { InterestsPage } from "../features/interests/InterestsPage.jsx";
import { MarketClosePage } from "../features/market/MarketClosePage.jsx";
import { PortfolioPage } from "../features/portfolio/PortfolioPage.jsx";
import { SectorOpportunityPage } from "../features/sector/SectorOpportunityPage.jsx";
import { StoragePage } from "../features/storage/StoragePage.jsx";
import { TeamReportPage } from "../features/team/TeamReportPage.jsx";
import { TradeSetupPage } from "../features/trade/TradeSetupPage.jsx";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001";
const DEFAULT_TOKEN = "dev-local-token";

export function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [accessToken, setAccessToken] = useState(DEFAULT_TOKEN);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedTicker, setSelectedTicker] = useState("PL");
  const apiClient = useMemo(
    () =>
      createApiClient({
        baseUrl: apiBaseUrl,
        accessToken,
      }),
    [apiBaseUrl, accessToken]
  );
  const portfolioApi = useMemo(() => createPortfolioApi(apiClient), [apiClient]);
  const researchApi = useMemo(() => createResearchApi(apiClient), [apiClient]);

  function openModuleWithTicker(moduleName, ticker) {
    const normalizedTicker = String(ticker || "PL").trim().toUpperCase();
    setSelectedTicker(normalizedTicker);
    setActiveTab(moduleName);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">투자 리서치 OS</p>
          <h1>React 리서치 콘솔</h1>
        </div>
        <div className="connection-panel" aria-label="API 연결 설정">
          <label>
            API 주소
            <input
              value={apiBaseUrl}
              onChange={(event) => setApiBaseUrl(event.target.value)}
              spellCheck="false"
            />
          </label>
          <label>
            개발 토큰
            <input
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              spellCheck="false"
            />
          </label>
        </div>
      </header>

      <nav className="tabs" aria-label="장기 이관 화면">
        <button
          className={`tab ${activeTab === "dashboard" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("dashboard")}
        >
          대시보드
        </button>
        <button
          className={`tab ${activeTab === "portfolio" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("portfolio")}
        >
          포트폴리오
        </button>
        <button
          className={`tab ${activeTab === "team" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("team")}
        >
          팀리포트
        </button>
        <button
          className={`tab ${activeTab === "trade" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("trade")}
        >
          매매전략
        </button>
        <button
          className={`tab ${activeTab === "earnings" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("earnings")}
        >
          실적분석
        </button>
        <button
          className={`tab ${activeTab === "sector" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("sector")}
        >
          섹터발굴
        </button>
        <button
          className={`tab ${activeTab === "compounder" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("compounder")}
        >
          복리성장주
        </button>
        <button
          className={`tab ${activeTab === "capture" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("capture")}
        >
          정보입력
        </button>
        <button
          className={`tab ${activeTab === "market" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("market")}
        >
          시장일지
        </button>
        <button
          className={`tab ${activeTab === "interests" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("interests")}
        >
          관심목록
        </button>
        <button
          className={`tab ${activeTab === "checklist" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("checklist")}
        >
          체크리스트
        </button>
        <button
          className={`tab ${activeTab === "storage" ? "active" : ""}`}
          type="button"
          onClick={() => setActiveTab("storage")}
        >
          저장 데이터
        </button>
      </nav>

      {activeTab === "dashboard" ? (
        <DashboardPage
          researchApi={researchApi}
          portfolioApi={portfolioApi}
          initialTicker={selectedTicker}
          onOpenModule={openModuleWithTicker}
        />
      ) : null}
      {activeTab === "portfolio" ? <PortfolioPage portfolioApi={portfolioApi} onOpenModule={openModuleWithTicker} /> : null}
      {activeTab === "team" ? <TeamReportPage researchApi={researchApi} initialTicker={selectedTicker} /> : null}
      {activeTab === "capture" ? <CapturePage researchApi={researchApi} /> : null}
      {activeTab === "market" ? <MarketClosePage researchApi={researchApi} /> : null}
      {activeTab === "interests" ? <InterestsPage researchApi={researchApi} /> : null}
      {activeTab === "trade" ? (
        <TradeSetupPage researchApi={researchApi} portfolioApi={portfolioApi} initialTicker={selectedTicker} />
      ) : null}
      {activeTab === "earnings" ? <EarningsPage researchApi={researchApi} initialTicker={selectedTicker} /> : null}
      {activeTab === "sector" ? <SectorOpportunityPage researchApi={researchApi} /> : null}
      {activeTab === "compounder" ? <CompounderPage researchApi={researchApi} /> : null}
      {activeTab === "checklist" ? <ChecklistPage researchApi={researchApi} /> : null}
      {activeTab === "storage" ? (
        <StoragePage
          researchApi={researchApi}
          initialResearchKey={selectedTicker}
          onOpenModule={openModuleWithTicker}
        />
      ) : null}
    </main>
  );
}
