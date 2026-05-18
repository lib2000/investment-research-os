import { useEffect, useMemo, useRef, useState } from "react";
import { formatMoney, parseNumberInput } from "../../shared/format/money.js";
import { formatPercent, signedTone } from "../../shared/format/percent.js";
import { normalizeHolding, normalizePortfolio, validatePortfolioDraft } from "./portfolioModel.js";

const FX_RATE = 1464;

const SAMPLE_PORTFOLIO = {
  portfolio_name: "샘플 포트폴리오",
  holdings: [
    {
      name: "삼양식품",
      ticker: "003230",
      currency: "KRW",
      quantity: 18,
      current_price: 1360000,
      average_cost: 85000,
    },
    {
      name: "Planet Labs PBC",
      ticker: "PL",
      currency: "USD",
      quantity: 217,
      current_price: 39.04,
      average_cost: 1.84,
    },
  ],
};

export function PortfolioPage({ portfolioApi, onOpenModule }) {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedName, setSelectedName] = useState("");
  const [portfolioName, setPortfolioName] = useState(SAMPLE_PORTFOLIO.portfolio_name);
  const [holdings, setHoldings] = useState(() => prepareHoldings(SAMPLE_PORTFOLIO.holdings));
  const [status, setStatus] = useState("대기");
  const [error, setError] = useState("");
  const [sortBy, setSortBy] = useState("market_value_desc");
  const [riskResult, setRiskResult] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [teamReportQueue, setTeamReportQueue] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [selectedRowId, setSelectedRowId] = useState("");
  const fileInputRef = useRef(null);

  const normalizedPortfolio = useMemo(
    () =>
      normalizePortfolio(
        {
          portfolio_name: portfolioName,
          holdings,
          sortBy,
        },
        { usdKrw: FX_RATE }
      ),
    [portfolioName, holdings, sortBy]
  );
  const selectedHolding = useMemo(
    () => normalizedPortfolio.holdings.find((holding) => holding.row_id === selectedRowId) || null,
    [normalizedPortfolio.holdings, selectedRowId]
  );

  useEffect(() => {
    let ignore = false;
    async function loadPortfolios() {
      setStatus("저장 포트폴리오 조회 중");
      setError("");
      try {
        const result = await portfolioApi.list();
        if (ignore) {
          return;
        }
        const items = result?.portfolios || result?.items || [];
        setPortfolios(items);
        const firstName = items[0]?.portfolio_name || items[0]?.name || "";
        if (firstName) {
          setSelectedName(firstName);
          await loadPortfolio(firstName, { silent: true });
        } else {
          setStatus("저장 포트폴리오 없음");
        }
      } catch (nextError) {
        if (!ignore) {
          setStatus("샘플 표시");
          setError(`백엔드 조회 실패: ${nextError.message}`);
        }
      }
    }
    loadPortfolios();
    return () => {
      ignore = true;
    };
    // portfolioApi는 API 주소/토큰 변경 시 새로 만들어집니다.
  }, [portfolioApi]);

  async function refreshPortfolioList() {
    const result = await portfolioApi.list();
    setPortfolios(result?.portfolios || result?.items || []);
  }

  async function loadPortfolio(portfolioNameToLoad = selectedName, { silent = false } = {}) {
    if (!portfolioNameToLoad) {
      setError("불러올 포트폴리오를 선택하세요.");
      return;
    }
    if (!silent) {
      setStatus("포트폴리오 불러오는 중");
      setError("");
    }
    try {
      const result = await portfolioApi.get(portfolioNameToLoad);
      const nextPortfolio = result?.portfolio || result?.active_portfolio || result;
      const normalized = normalizePortfolio(nextPortfolio, { usdKrw: FX_RATE });
      setPortfolioName(normalized.portfolio_name);
      setHoldings(prepareHoldings(normalized.holdings));
      setSelectedRowId("");
      setComparison(buildServerComparison(nextPortfolio, normalized));
      setStatus("정상");
    } catch (nextError) {
      setStatus("불러오기 실패");
      setError(nextError.message);
    }
  }

  function updateHolding(rowId, field, value) {
    setHoldings((current) =>
      current.map((holding) => (holding.row_id === rowId ? { ...holding, [field]: value } : holding))
    );
  }

  function addHolding() {
    const rowId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    setHoldings((current) => [
      ...current,
      createDraftHolding({
        row_id: rowId,
        name: "",
        ticker: "",
        currency: "KRW",
        quantity: 1,
        current_price: "",
        average_cost: "",
      }),
    ]);
    setSelectedRowId(rowId);
    setStatus("보유 종목 추가됨");
  }

  function deleteHolding(rowId) {
    setHoldings((current) => current.filter((holding) => holding.row_id !== rowId));
    setSelectedRowId((current) => (current === rowId ? "" : current));
    setStatus("보유 종목 삭제됨");
  }

  async function saveCurrentPortfolio() {
    setError("");
    const errors = validatePortfolioDraft({
      portfolio_name: portfolioName,
      holdings: normalizedPortfolio.holdings,
    });
    if (errors.length) {
      setStatus("저장 보류");
      setError(errors.join("\n"));
      return;
    }
    setStatus("저장 중");
    try {
      const result = await portfolioApi.save({
        portfolioName,
        holdings: normalizedPortfolio.holdings,
        portfolioValue: normalizedPortfolio.summary.total_market_value,
      });
      await refreshPortfolioList();
      setSelectedName(portfolioName);
      setStatus("저장 완료");
      setComparison(buildServerComparison(result?.active_portfolio || result?.portfolio, normalizedPortfolio));
    } catch (nextError) {
      setStatus("저장 실패");
      setError(nextError.message);
    }
  }

  async function importFile(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setStatus("파일 불러오는 중");
    setError("");
    try {
      const contentBase64 = await readFileAsBase64(file);
      const result = await portfolioApi.importFile({
        fileName: file.name,
        contentBase64,
      });
      const importedHoldings = result?.imported_holdings || result?.holdings || [];
      if (!importedHoldings.length) {
        throw new Error("파일에서 보유 종목을 찾지 못했습니다.");
      }
      setHoldings(prepareHoldings(importedHoldings));
      setSelectedRowId("");
      setPortfolioName(result?.portfolio_name || portfolioName || "불러온 포트폴리오");
      setStatus(`파일 불러오기 완료 · ${importedHoldings.length.toLocaleString("ko-KR")}개`);
    } catch (nextError) {
      setStatus("파일 불러오기 실패");
      setError(nextError.message);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function runRiskScan() {
    setStatus("리스크 스캔 중");
    setError("");
    setRiskResult(null);
    try {
      const result = await portfolioApi.riskScan({
        portfolioName: normalizedPortfolio.portfolio_name,
        holdings: normalizedPortfolio.holdings,
        portfolioValue: normalizedPortfolio.summary.total_market_value,
      });
      setRiskResult(result);
      setStatus("리스크 스캔 완료");
    } catch (nextError) {
      setStatus("리스크 스캔 실패");
      setError(nextError.message);
    }
  }

  async function loadAnalysisStatus() {
    setStatus("분석 현황 조회 중");
    setError("");
    try {
      const [connectivity, analysis] = await Promise.all([
        portfolioApi.connectivity(),
        portfolioApi.analysisStatus(),
      ]);
      setAnalysisStatus({ connectivity, analysis });
      setStatus("분석 현황 조회 완료");
    } catch (nextError) {
      setStatus("분석 현황 조회 실패");
      setError(nextError.message);
    }
  }

  async function loadTeamReportQueue() {
    setStatus("팀리포트 큐 조회 중");
    setError("");
    try {
      const result = await portfolioApi.teamReportQueue();
      setTeamReportQueue(result);
      setStatus("팀리포트 큐 조회 완료");
    } catch (nextError) {
      setStatus("팀리포트 큐 조회 실패");
      setError(nextError.message);
    }
  }

  return (
    <section className="panel portfolio-panel">
      <div className="panel-heading">
        <div>
          <h2>포트폴리오</h2>
          <p>편집, 저장, 파일 불러오기, 리스크 스캔까지 React 구조에서 처리합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <div className="toolbar portfolio-toolbar">
        <label>
          포트폴리오 이름
          <input value={portfolioName} onChange={(event) => setPortfolioName(event.target.value)} />
        </label>
        <label>
          저장 포트폴리오
          <select value={selectedName} onChange={(event) => setSelectedName(event.target.value)}>
            <option value="">선택</option>
            {portfolios.map((item) => {
              const name = item.portfolio_name || item.name;
              return (
                <option key={name} value={name}>
                  {name}
                </option>
              );
            })}
          </select>
        </label>
        <label>
          정렬
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="market_value_desc">평가금액 높은 순</option>
            <option value="gain_desc">수익 높은 순</option>
            <option value="return_desc">수익률 높은 순</option>
            <option value="name_asc">회사명 가나다 순</option>
            <option value="ticker_asc">티커 순</option>
          </select>
        </label>
        <button type="button" onClick={() => loadPortfolio()}>
          불러오기
        </button>
        <button type="button" onClick={saveCurrentPortfolio}>
          저장
        </button>
      </div>

      <div className="action-row">
        <input ref={fileInputRef} type="file" onChange={importFile} />
        <button type="button" onClick={addHolding}>
          보유 종목 추가
        </button>
        <button type="button" onClick={runRiskScan}>
          리스크 스캔
        </button>
        <button type="button" onClick={loadAnalysisStatus}>
          분석 현황
        </button>
        <button type="button" onClick={loadTeamReportQueue}>
          팀리포트 큐
        </button>
      </div>

      {error ? <div className="warning-box">{error}</div> : null}

      <PortfolioSummary portfolio={normalizedPortfolio} comparison={comparison} />
      <PortfolioModuleActions holding={selectedHolding} onOpenModule={onOpenModule} />
      <PortfolioEditor
        holdings={normalizedPortfolio.holdings}
        onChange={updateHolding}
        onDelete={deleteHolding}
        selectedRowId={selectedRowId}
        onSelect={setSelectedRowId}
      />

      <ResultPanels riskResult={riskResult} analysisStatus={analysisStatus} teamReportQueue={teamReportQueue} />
    </section>
  );
}

function PortfolioModuleActions({ holding, onOpenModule }) {
  const ticker = String(holding?.ticker || "").trim().toUpperCase();
  const label = holding ? `${holding.name || ticker} ${ticker ? `(${ticker})` : ""}` : "선택된 종목 없음";
  const disabled = !ticker;

  return (
    <div className="portfolio-module-actions">
      <div>
        <span>선택 종목</span>
        <strong>{label}</strong>
      </div>
      <button type="button" className="secondary-button" disabled={disabled} onClick={() => onOpenModule?.("dashboard", ticker)}>
        대시보드
      </button>
      <button type="button" className="secondary-button" disabled={disabled} onClick={() => onOpenModule?.("team", ticker)}>
        팀리포트
      </button>
      <button type="button" className="secondary-button" disabled={disabled} onClick={() => onOpenModule?.("trade", ticker)}>
        매매전략
      </button>
      <button type="button" className="secondary-button" disabled={disabled} onClick={() => onOpenModule?.("earnings", ticker)}>
        실적분석
      </button>
    </div>
  );
}

function PortfolioSummary({ portfolio, comparison }) {
  const summary = portfolio.summary;
  return (
    <div className="summary-strip">
      <SummaryItem label="이름" value={portfolio.portfolio_name} />
      <SummaryItem label="총액" value={formatMoney(summary.total_market_value, "KRW", "0원")} />
      <SummaryItem label="투자금" value={formatMoney(summary.total_cost_basis, "KRW", "0원")} />
      <SummaryItem
        label="총 수익"
        value={formatMoney(summary.total_gain, "KRW", "0원")}
        tone={signedTone(summary.total_return)}
      />
      <SummaryItem
        label="수익률"
        value={formatPercent(summary.total_return, "0%")}
        tone={signedTone(summary.total_return)}
      />
      <SummaryItem label="보유" value={`${summary.holding_count.toLocaleString("ko-KR")}개`} />
      <SummaryItem
        label="검증"
        value={comparison?.message || "화면 계산 기준"}
        tone={comparison?.tone || "neutral"}
      />
    </div>
  );
}

function SummaryItem({ label, value, tone = "neutral" }) {
  return (
    <div className={`summary-item tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PortfolioEditor({ holdings, onChange, onDelete, selectedRowId, onSelect }) {
  return (
    <div className="portfolio-table-wrap">
      <table className="portfolio-table portfolio-editor-table">
        <thead>
          <tr>
            <th>회사명</th>
            <th>티커</th>
            <th className="number">평가금액</th>
            <th className="number">현재가</th>
            <th className="number">매입가(평단)</th>
            <th className="center">수량</th>
            <th className="number">수익</th>
            <th className="center">수익률</th>
            <th className="center">관리</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr
              key={holding.row_id}
              className={holding.row_id === selectedRowId ? "selected-row" : ""}
              onClick={() => onSelect(holding.row_id)}
            >
              <td className="company">
                <input
                  className="cell-input text-input"
                  value={holding.name || ""}
                  onChange={(event) => onChange(holding.row_id, "name", event.target.value)}
                />
              </td>
              <td>
                <input
                  className="cell-input center-input"
                  value={holding.ticker || ""}
                  onChange={(event) => onChange(holding.row_id, "ticker", event.target.value)}
                />
              </td>
              <td className="number">{formatMoney(holding.market_value, "KRW", "0원")}</td>
              <td>
                <input
                  className="cell-input number-input"
                  value={holding.current_price ?? ""}
                  onChange={(event) => onChange(holding.row_id, "current_price", event.target.value)}
                />
              </td>
              <td>
                <input
                  className="cell-input number-input"
                  value={holding.average_cost ?? ""}
                  onChange={(event) => onChange(holding.row_id, "average_cost", event.target.value)}
                />
              </td>
              <td>
                <input
                  className="cell-input center-input"
                  value={holding.quantity ?? ""}
                  onChange={(event) => onChange(holding.row_id, "quantity", event.target.value)}
                />
              </td>
              <td className={`number tone-${signedTone(holding.unrealized_return)}`}>
                {formatMoney(holding.unrealized_gain, "KRW", "0원")}
              </td>
              <td className={`center tone-${signedTone(holding.unrealized_return)}`}>
                {formatPercent(holding.unrealized_return, "0%")}
              </td>
              <td className="center">
                <button className="secondary-button" type="button" onClick={() => onDelete(holding.row_id)}>
                  삭제
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultPanels({ riskResult, analysisStatus, teamReportQueue }) {
  if (!riskResult && !analysisStatus && !teamReportQueue) {
    return null;
  }
  const warnings = extractRiskWarnings(riskResult);
  const topHoldings = extractExposureRows(riskResult, "single_position_concentration");
  const sectors = extractExposureRows(riskResult, "sector_concentration");
  const themes = extractExposureRows(riskResult, "theme_concentration");

  return (
    <div className="result-grid">
      {riskResult ? (
        <article className="result-card">
          <h3>리스크 스캔 결과</h3>
          <div className="risk-metrics">
            <Metric label="포트폴리오" value={riskResult.portfolio_name || "미확인"} />
            <Metric label="리스크 점수" value={formatRiskScore(riskResult.risk_score ?? riskResult.score)} />
            <Metric label="상위 5개 비중" value={formatPercent(riskResult.top_five_weight, "미확인")} />
            <Metric label="평가 총액" value={formatMoney(riskResult.portfolio_value, "KRW", "미확인")} />
          </div>
          <RiskSection title="주요 경고" items={warnings} emptyText="집중도 한도를 초과한 항목은 없습니다." />
          <ExposureTable title="상위 종목 집중도" rows={topHoldings} />
          <ExposureTable title="섹터 집중도" rows={sectors} />
          <ExposureTable title="테마 집중도" rows={themes} />
          <RiskSection title="다음 액션" items={normalizeTextList(riskResult.next_actions)} emptyText="추가 액션 없음" />
          {riskResult.storage?.path || riskResult.saved_file ? (
            <p className="saved-path">저장 위치: {riskResult.storage?.path || riskResult.saved_file}</p>
          ) : null}
        </article>
      ) : null}
      {analysisStatus ? (
        <AnalysisStatusCard analysisStatus={analysisStatus} />
      ) : null}
      {teamReportQueue ? (
        <TeamReportQueueCard queueResult={teamReportQueue} />
      ) : null}
    </div>
  );
}

function AnalysisStatusCard({ analysisStatus }) {
  const analysis = analysisStatus.analysis || {};
  const items = Array.isArray(analysis.items) ? analysis.items : [];
  const visibleItems = items.slice(0, 12);

  return (
    <article className="result-card portfolio-status-card">
      <h3>보유 종목 분석 현황</h3>
      <p>{analysis.summary || "분석 현황 요약이 없습니다."}</p>
      <div className="risk-metrics">
        <Metric label="고유 종목" value={`${analysis.holding_count ?? items.length}개`} />
        <Metric label="준비 완료" value={`${analysis.ready_count ?? 0}개`} />
        <Metric label="평균 완료율" value={formatPercent(analysis.average_completion, "0%")} />
        <Metric label="팀리포트 필요" value={`${analysis.needs_team_report_count ?? 0}개`} />
      </div>
      <table className="mini-table portfolio-status-table">
        <thead>
          <tr>
            <th>종목</th>
            <th className="number">평가금액</th>
            <th className="center">완료율</th>
            <th>누락</th>
            <th>최근 저장</th>
          </tr>
        </thead>
        <tbody>
          {visibleItems.map((item) => (
            <tr key={item.ticker}>
              <td>
                <strong>{item.company_name || item.ticker}</strong>
                <small>{item.official_symbol || item.ticker}</small>
              </td>
              <td className="number">{formatMoney(item.market_value, "KRW", "0원")}</td>
              <td className="center">{formatPercent(item.completion_rate, "0%")}</td>
              <td>{formatMissingModules(item.missing_modules)}</td>
              <td>{item.latest_report_date || "없음"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length > visibleItems.length ? (
        <p className="muted-text">상위 {visibleItems.length}개만 표시했습니다. 전체 {items.length}개는 API 기준으로 관리됩니다.</p>
      ) : null}
    </article>
  );
}

function TeamReportQueueCard({ queueResult }) {
  const queue = Array.isArray(queueResult.queue) ? queueResult.queue : [];
  const ready = Array.isArray(queueResult.already_ready) ? queueResult.already_ready : [];
  const visibleQueue = queue.length ? queue.slice(0, 8) : ready.slice(0, 8);

  return (
    <article className="result-card portfolio-status-card">
      <h3>팀리포트 큐</h3>
      <p>{queueResult.summary || "팀리포트 큐 요약이 없습니다."}</p>
      <div className="risk-metrics">
        <Metric label="생성 필요" value={`${queueResult.queue_count ?? queue.length}개`} />
        <Metric label="준비 완료" value={`${queueResult.ready_count ?? ready.length}개`} />
        <Metric label="인증 보류" value={`${queueResult.blocked_count ?? 0}개`} />
        <Metric label="포트폴리오" value={`${queueResult.portfolio_count ?? 0}개`} />
      </div>
      <table className="mini-table portfolio-status-table">
        <thead>
          <tr>
            <th>종목</th>
            <th className="number">평가금액</th>
            <th>중점 분석</th>
            <th>최신 리포트</th>
          </tr>
        </thead>
        <tbody>
          {visibleQueue.map((item) => (
            <tr key={item.ticker}>
              <td>
                <strong>{item.company_name || item.ticker}</strong>
                <small>{item.official_symbol || item.ticker}</small>
              </td>
              <td className="number">{formatMoney(item.market_value, "KRW", "0원")}</td>
              <td>{item.analysis_focus || "미등록"}</td>
              <td>{item.latest_team_report_date || (queue.length ? "생성 필요" : "준비 완료")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RiskSection({ title, items, emptyText }) {
  const rows = items.filter(Boolean).slice(0, 8);
  return (
    <section className="risk-section">
      <h4>{title}</h4>
      {rows.length ? (
        <ul>
          {rows.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">{emptyText}</p>
      )}
    </section>
  );
}

function ExposureTable({ title, rows }) {
  const visibleRows = rows.slice(0, 6);
  if (!visibleRows.length) {
    return null;
  }
  return (
    <section className="risk-section">
      <h4>{title}</h4>
      <table className="mini-table">
        <thead>
          <tr>
            <th>항목</th>
            <th className="number">비중</th>
            <th className="number">평가금액</th>
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => (
            <tr key={`${title}-${row.name}`}>
              <td>{row.name}</td>
              <td className="number">{formatPercent(row.weight, "0%")}</td>
              <td className="number">{formatMoney(row.market_value, "KRW", "0원")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function extractRiskWarnings(result) {
  return normalizeTextList(result?.risk_warnings || result?.warnings || result?.alerts).map((item) => {
    if (typeof item === "string") {
      return item;
    }
    const severity = item.severity ? `[${translateSeverity(item.severity)}] ` : "";
    const message = item.message || item.summary || item.reason || "";
    const action = item.action ? ` 조치: ${item.action}` : "";
    return `${severity}${message}${action}`.trim();
  });
}

function extractExposureRows(result, key) {
  const rows = result?.[key];
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row) => ({
      name: row.name || row.ticker || row.label || "미확인",
      weight: parseNumberInput(row.weight),
      market_value: parseNumberInput(row.market_value),
    }))
    .filter((row) => row.name && row.weight !== null)
    .sort((a, b) => (b.weight || 0) - (a.weight || 0));
}

function normalizeTextList(value) {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value;
  }
  return [value];
}

function translateSeverity(severity) {
  const labels = {
    low: "낮음",
    medium: "보통",
    high: "높음",
  };
  return labels[severity] || severity;
}

function formatRiskScore(value) {
  const number = parseNumberInput(value);
  return number === null ? "미확인" : `${number.toLocaleString("ko-KR")}/100`;
}

function prepareHoldings(items = []) {
  return items.map((item) => createDraftHolding(item));
}

function createDraftHolding(item = {}) {
  const normalized = normalizeHolding(item, { usdKrw: FX_RATE });
  return {
    ...normalized,
    row_id: item.row_id || globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`,
  };
}

function buildServerComparison(serverPortfolio, normalizedPortfolio) {
  const serverValue = parseNumberInput(
    serverPortfolio?.portfolio_value ?? serverPortfolio?.summary?.total_market_value
  );
  if (serverValue === null) {
    return { message: "화면 계산 기준", tone: "neutral" };
  }
  const diff = Math.abs(serverValue - normalizedPortfolio.summary.total_market_value);
  if (diff <= 100) {
    return { message: "서버값 일치", tone: "positive" };
  }
  return { message: `차이 ${formatMoney(diff, "KRW")}`, tone: "negative" };
}

function summarizeAnalysisStatus(status) {
  const connectivity = status.connectivity?.items || status.connectivity?.tickers || [];
  const analysis = status.analysis?.items || status.analysis?.tickers || [];
  return [
    ...connectivity.slice(0, 3).map((item) => `연결: ${item.official_symbol || item.ticker || item.name || "미확인"}`),
    ...analysis.slice(0, 3).map((item) => `분석: ${item.official_symbol || item.ticker || item.name || "미확인"}`),
  ];
}

function formatMissingModules(value) {
  const modules = Array.isArray(value) ? value : [];
  if (!modules.length) {
    return "없음";
  }
  const labels = {
    team_report: "팀리포트",
    trade_setup: "매매전략",
    earnings_reaction: "실적분석",
    checklist: "체크리스트",
    recent_capture: "최근정보",
  };
  return modules.map((item) => labels[item] || item).join(", ");
}

function countItems(value) {
  return Array.isArray(value) ? value.length.toLocaleString("ko-KR") : "0";
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",").pop() : result);
    };
    reader.onerror = () => reject(reader.error || new Error("파일 읽기 실패"));
    reader.readAsDataURL(file);
  });
}
