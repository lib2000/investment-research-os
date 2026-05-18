import { useEffect, useMemo, useState } from "react";

const DEFAULT_TICKER = "PL";

export function DashboardPage({ researchApi, portfolioApi, initialTicker = DEFAULT_TICKER, onOpenModule }) {
  const [ticker, setTicker] = useState(initialTicker || DEFAULT_TICKER);
  const [investmentPeriod, setInvestmentPeriod] = useState("3년");
  const [region, setRegion] = useState("US");
  const [style, setStyle] = useState("balanced");
  const [focusArea, setFocusArea] = useState(
    "위성 이미지 데이터 수요, 정부·상업 고객 계약, 매출 성장, 매출총이익률, 조정 EBITDA와 현금 소진, 경쟁 리스크"
  );
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [portfolioStatus, setPortfolioStatus] = useState(null);
  const [teamQueue, setTeamQueue] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [status, setStatus] = useState("대기");
  const [opsStatus, setOpsStatus] = useState("운영 상태 대기");
  const [error, setError] = useState("");
  const [opsError, setOpsError] = useState("");

  const normalizedTicker = useMemo(() => ticker.trim().toUpperCase() || DEFAULT_TICKER, [ticker]);

  useEffect(() => {
    const nextTicker = String(initialTicker || DEFAULT_TICKER).trim().toUpperCase();
    setTicker(nextTicker);
    loadDashboardForTicker(nextTicker, { silent: true });
    loadOperatingStatus({ silent: true });
    // 저장 데이터/다른 모듈에서 넘어온 티커만 자동 조회합니다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTicker, researchApi, portfolioApi]);

  async function loadDashboard({ silent = false } = {}) {
    return loadDashboardForTicker(normalizedTicker, { silent });
  }

  async function loadDashboardForTicker(tickerValue, { silent = false } = {}) {
    const targetTicker = String(tickerValue || DEFAULT_TICKER).trim().toUpperCase();
    if (!targetTicker) {
      setError("티커를 입력하세요.");
      return;
    }
    if (!silent) {
      setStatus("대시보드 조회 중");
      setError("");
    }
    try {
      const result = await researchApi.dashboard(targetTicker);
      setDashboard(result);
      setRunResult(null);
      setStatus("대시보드 조회 완료");
    } catch (nextError) {
      setStatus("조회 실패");
      setError(nextError.message);
    }
  }

  async function runTeamReport() {
    setStatus("팀 리포트 실행 중");
    setError("");
    try {
      const result = await researchApi.runTeamReport({
        ticker: normalizedTicker,
        investmentPeriod,
        region,
        style,
        focusArea,
        autoInjectData,
      });
      setRunResult(result);
      setStatus("팀 리포트 저장 완료");
      await loadDashboard({ silent: true });
    } catch (nextError) {
      setStatus("팀 리포트 실패");
      setError(nextError.message);
    }
  }

  async function loadOperatingStatus({ silent = false } = {}) {
    if (!portfolioApi) {
      return;
    }
    if (!silent) {
      setOpsStatus("운영 상태 조회 중");
      setOpsError("");
    }
    try {
      const [analysis, queue] = await Promise.all([
        portfolioApi.analysisStatus(),
        portfolioApi.teamReportQueue(),
      ]);
      setPortfolioStatus(analysis);
      setTeamQueue(queue);
      setOpsStatus("운영 상태 조회 완료");
    } catch (nextError) {
      setOpsStatus("운영 상태 조회 실패");
      setOpsError(nextError.message);
    }
  }

  return (
    <section className="panel dashboard-panel">
      <div className="panel-heading">
        <div>
          <h2>대시보드</h2>
          <p>티커 인증, 저장 리서치, 최신 실적 기준, 다음 액션을 한 화면에서 확인합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <div className="dashboard-controls">
        <label>
          티커
          <input value={ticker} onChange={(event) => setTicker(event.target.value)} />
        </label>
        <label>
          투자 기간
          <input value={investmentPeriod} onChange={(event) => setInvestmentPeriod(event.target.value)} />
        </label>
        <label>
          지역
          <input value={region} onChange={(event) => setRegion(event.target.value)} />
        </label>
        <label>
          스타일
          <select value={style} onChange={(event) => setStyle(event.target.value)}>
            <option value="balanced">균형형</option>
            <option value="growth">성장주</option>
            <option value="value">가치주</option>
            <option value="trading">트레이딩</option>
          </select>
        </label>
        <label className="wide-field">
          중점 분석
          <input value={focusArea} onChange={(event) => setFocusArea(event.target.value)} />
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            checked={autoInjectData}
            onChange={(event) => setAutoInjectData(event.target.checked)}
          />
          시장/재무 데이터 자동 주입
        </label>
        <div className="dashboard-button-row">
          <button type="button" onClick={() => loadDashboard()}>
            대시보드 조회
          </button>
          <button className="secondary-button" type="button" onClick={() => loadOperatingStatus()}>
            운영 상태 갱신
          </button>
          <button type="button" onClick={runTeamReport}>
            7개 스킬 팀 리포트 실행
          </button>
        </div>
      </div>

      {error ? <div className="warning-box">{error}</div> : null}
      {opsError ? <div className="warning-box">운영 상태 오류: {opsError}</div> : null}

      <OperatingOverview
        portfolioStatus={portfolioStatus}
        teamQueue={teamQueue}
        opsStatus={opsStatus}
        onOpenModule={onOpenModule}
      />
      {dashboard ? <DashboardCards dashboard={dashboard} onOpenModule={onOpenModule} /> : <EmptyDashboard />}
      {runResult ? <TeamRunResult result={runResult} /> : null}
    </section>
  );
}

function OperatingOverview({ portfolioStatus, teamQueue, opsStatus, onOpenModule }) {
  const analysis = portfolioStatus || {};
  const queue = teamQueue || {};
  const items = Array.isArray(analysis.items) ? analysis.items : [];
  const incomplete = items
    .filter((item) => Number(item.completion_rate) < 1 || (item.missing_modules || []).length)
    .slice(0, 5);
  const recent = items
    .filter((item) => item.latest_report_date)
    .slice()
    .sort((a, b) => String(b.latest_report_date).localeCompare(String(a.latest_report_date)))
    .slice(0, 5);

  return (
    <section className="dashboard-section operating-overview">
      <div className="panel-heading compact-heading">
        <div>
          <h3>운영 요약</h3>
          <p>{analysis.summary || "포트폴리오 분석 준비 상태를 조회하면 오늘 볼 항목이 정리됩니다."}</p>
        </div>
        <span className="status-pill">{opsStatus}</span>
      </div>
      <div className="dashboard-card-grid">
        <InfoCard label="고유 보유 종목" value={`${analysis.holding_count ?? 0}개`} text={`저장 포트폴리오 ${analysis.portfolio_count ?? 0}개`} />
        <InfoCard tone={(analysis.needs_team_report_count ?? 0) ? "warning" : "ok"} label="팀리포트 필요" value={`${analysis.needs_team_report_count ?? 0}개`} text={`준비 완료 ${analysis.ready_count ?? 0}개`} />
        <InfoCard label="평균 완료율" value={`${Math.round(Number(analysis.average_completion || 0) * 100)}%`} text="팀리포트·매매전략·실적·체크리스트·최근정보 기준" />
        <InfoCard tone={(queue.blocked_count ?? 0) ? "warning" : "ok"} label="인증 보류" value={`${queue.blocked_count ?? 0}개`} text={`큐 ${queue.queue_count ?? 0}개 · 준비 ${queue.ready_count ?? 0}개`} />
      </div>
      <div className="two-column dashboard-section">
        <ActionListBlock
          title="우선 보강 후보"
          items={incomplete.map((item) => ({
            ticker: item.official_symbol || item.ticker,
            text: `${item.company_name || item.ticker}: ${formatMissingModules(item.missing_modules)}`,
            primaryModule: "team",
          }))}
          onOpenModule={onOpenModule}
        />
        <ActionListBlock
          title="최근 갱신"
          items={recent.map((item) => ({
            ticker: item.official_symbol || item.ticker,
            text: `${item.company_name || item.ticker}: ${item.latest_report_date} · ${truncateText(item.latest_report_summary)}`,
            primaryModule: "dashboard",
          }))}
          onOpenModule={onOpenModule}
        />
      </div>
    </section>
  );
}

function EmptyDashboard() {
  return (
    <div className="dashboard-card-grid">
      <article className="info-card warning">
        <span>대기</span>
        <strong>조회 전</strong>
        <p>PL 또는 원하는 공식 티커를 입력하고 대시보드 조회를 실행하세요.</p>
      </article>
    </div>
  );
}

function DashboardCards({ dashboard, onOpenModule }) {
  const profile = dashboard.ticker_profile || {};
  const verification = dashboard.ticker_verification || profile.verification || {};
  const earnings = dashboard.latest_earnings_reference || {};
  const moduleStatus = Array.isArray(dashboard.module_status) ? dashboard.module_status : [];
  const reports = Array.isArray(dashboard.latest_reports) ? dashboard.latest_reports : [];

  return (
    <>
      <div className="dashboard-card-grid">
        <InfoCard
          tone={verification.verified ? "ok" : "warning"}
          label="공식 티커"
          value={verification.official_symbol || dashboard.ticker}
          text={`${verification.company_name || profile.company_name || "회사명 미확인"} · ${
            verification.exchange || profile.exchange || "거래소 미확인"
          }`}
        />
        <InfoCard
          label="저장 데이터"
          value={`${Number(dashboard.file_count || 0).toLocaleString("ko-KR")}개`}
          text={`공식 인증 리포트 ${Number(dashboard.verified_report_count || 0).toLocaleString("ko-KR")}개`}
        />
        <InfoCard
          tone={earnings.aligned_with_latest ? "ok" : "warning"}
          label="최근 실적 기준"
          value={earnings.official_quarter || profile.latest_reported_quarter || "미등록"}
          text={`발표일 ${earnings.official_earnings_report_date || profile.latest_reported_earnings_date || "미입력"} · 다음 ${
            earnings.next_earnings_date || profile.next_earnings_date || "미입력"
          }`}
        />
        <InfoCard
          label="체크리스트"
          value={`${Math.round(Number(dashboard.checklist_completion_rate || 0) * 100)}%`}
          text={dashboard.checklist_readiness || "상태 미확인"}
        />
      </div>

      <section className="dashboard-section">
        <h3>모듈 상태</h3>
        <div className="module-status-grid">
          {moduleStatus.map((item) => (
            <InfoCard key={item.label} tone={item.tone} label={item.label} value={item.value} text={cardHint(item)} />
          ))}
        </div>
      </section>

      <section className="dashboard-section two-column">
        <ListBlock title="다음 액션" items={dashboard.recommended_next_actions} />
        <ListBlock title="추적 항목" items={dashboard.open_watch_items} />
      </section>

      <section className="dashboard-section">
        <h3>최근 저장 리포트</h3>
        <div className="report-list">
          {reports.slice(0, 6).map((report) => (
            <article className="report-item" key={`${report.type}-${report.file_name}`} title={report.tooltip || ""}>
              <strong>{translateReportType(report.type)} · {report.date || "날짜 없음"}</strong>
              <p>{report.summary || "요약 없음"}</p>
              <small>{report.file_name}</small>
              <div className="inline-actions report-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onOpenModule?.("storage", dashboard.ticker)}
                >
                  저장 데이터
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onOpenModule?.("team", dashboard.ticker)}
                >
                  팀리포트
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {Array.isArray(dashboard.data_warnings) && dashboard.data_warnings.length ? (
        <section className="dashboard-section">
          <ListBlock title="데이터 경고" items={dashboard.data_warnings} />
        </section>
      ) : null}
    </>
  );
}

function InfoCard({ label, value, text, tone = "neutral" }) {
  return (
    <article className={`info-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </article>
  );
}

function ListBlock({ title, items }) {
  const list = Array.isArray(items) ? items.filter(Boolean).slice(0, 8) : [];
  return (
    <div className="list-block">
      <h3>{title}</h3>
      {list.length ? (
        <ul>
          {list.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 항목이 없습니다.</p>
      )}
    </div>
  );
}

function ActionListBlock({ title, items, onOpenModule }) {
  const list = Array.isArray(items) ? items.filter((item) => item?.text).slice(0, 8) : [];
  return (
    <div className="list-block action-list-block">
      <h3>{title}</h3>
      {list.length ? (
        <ul>
          {list.map((item, index) => (
            <li key={`${title}-${item.ticker}-${index}`}>
              <span>{item.text}</span>
              <div className="inline-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onOpenModule?.("dashboard", item.ticker)}
                >
                  대시보드
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onOpenModule?.(item.primaryModule || "team", item.ticker)}
                >
                  {item.primaryModule === "dashboard" ? "다시 보기" : "팀리포트"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 항목이 없습니다.</p>
      )}
    </div>
  );
}

function TeamRunResult({ result }) {
  return (
    <section className="dashboard-section">
      <h3>방금 생성한 팀 리포트</h3>
      <div className="report-item">
        <strong>{result.ticker || result.input?.ticker || "티커 미확인"}</strong>
        <p>{result.summary || result.integrated_view || result.output || "팀 리포트가 저장되었습니다."}</p>
        <small>{result.storage?.path || result.saved_file || result.file_name || "저장 경로는 대시보드 최신 리포트에서 확인하세요."}</small>
      </div>
    </section>
  );
}

function cardHint(item) {
  const label = item?.label || "";
  if (label.includes("실적")) {
    return "최근 발표 실적과 저장 분석의 기준 일치 여부";
  }
  if (label.includes("매매")) {
    return "현재 기준 매매 계획 보유 여부";
  }
  if (label.includes("체크")) {
    return "16개 리서치 항목 완료율";
  }
  return "저장 데이터 기준 상태";
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

function truncateText(value, maxLength = 80) {
  const text = String(value || "요약 없음").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function translateReportType(type) {
  const labels = {
    "collaborative-team-report": "팀 리포트",
    "smart-trade-setup": "매매 전략",
    "earnings-reaction": "실적 분석",
    "research-capture": "정보 입력",
    "thesis-impact-review": "논거 영향",
    "research-checklist": "체크리스트",
  };
  return labels[type] || type || "리포트";
}
