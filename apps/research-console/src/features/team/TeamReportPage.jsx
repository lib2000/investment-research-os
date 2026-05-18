import { useEffect, useState } from "react";

const DEFAULT_FOCUS =
  "위성 이미지 데이터 수요, 정부·상업 고객 계약, 매출 성장, 매출총이익률, 조정 EBITDA와 현금 소진, 경쟁 리스크";

export function TeamReportPage({ researchApi, initialTicker = "PL" }) {
  const [ticker, setTicker] = useState(initialTicker || "PL");
  const [investmentPeriod, setInvestmentPeriod] = useState("3년");
  const [region, setRegion] = useState("US");
  const [style, setStyle] = useState("balanced");
  const [focusArea, setFocusArea] = useState(DEFAULT_FOCUS);
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const isLoading = status === "loading";
  const dataQuality = result?.data_quality || {};
  const thesis = result?.investment_thesis || {};
  const contributions = Array.isArray(result?.team_contributions) ? result.team_contributions : [];

  useEffect(() => {
    setTicker(String(initialTicker || "PL").trim().toUpperCase());
  }, [initialTicker]);

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);

    try {
      const response = await researchApi.runTeamReport({
        ticker,
        investmentPeriod,
        region,
        style,
        focusArea,
        autoInjectData,
      });
      setResult(response);
      setStatus("success");
    } catch (requestError) {
      setError(requestError);
      setStatus("error");
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>팀 리포트</h2>
          <p>7개 분석 스킬이 협업해 기준 투자 논거, 시나리오, 매매 계획, 추적 항목을 생성합니다.</p>
        </div>
        <span className="status-pill">
          {isLoading ? "분석 중" : result ? "저장 완료" : "대기 중"}
        </span>
      </div>

      <form className="team-form" onSubmit={handleSubmit}>
        <div className="team-form-grid">
          <label>
            티커
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <label>
            투자 기간
            <input value={investmentPeriod} onChange={(event) => setInvestmentPeriod(event.target.value)} />
          </label>
          <label>
            지역
            <select value={region} onChange={(event) => setRegion(event.target.value)}>
              <option value="US">미국</option>
              <option value="KR">한국</option>
              <option value="GLOBAL">글로벌</option>
            </select>
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
        </div>

        <label>
          중점 분석
          <textarea
            value={focusArea}
            onChange={(event) => setFocusArea(event.target.value)}
            placeholder="사업 모델, 수익 동력, 경쟁 우위, 리스크, 밸류에이션, 실적 포인트"
          />
        </label>

        <label className="check-row">
          <input
            type="checkbox"
            checked={autoInjectData}
            onChange={(event) => setAutoInjectData(event.target.checked)}
          />
          시장/재무 데이터 자동 주입
        </label>

        <div className="action-row">
          <button type="submit" disabled={isLoading || !ticker.trim()}>
            {isLoading ? "7개 스킬 분석 중..." : "7개 스킬 팀 리포트 실행"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="warning-box">
          오류가 발생했습니다: {error.message || "팀 리포트 실행에 실패했습니다."}
        </div>
      ) : null}

      {result ? (
        <div className="team-result">
          <div className="risk-metrics">
            <Metric label="티커" value={result.ticker || ticker} />
            <Metric label="투자 기간" value={result.investment_period || investmentPeriod} />
            <Metric label="데이터 품질" value={translateQuality(dataQuality.data_quality)} />
            <Metric label="출처 신뢰도" value={formatPercent(dataQuality.source_confidence)} />
          </div>

          <section className="result-card">
            <h3>핵심 요약</h3>
            <p>{result.executive_summary || "요약이 없습니다."}</p>
          </section>

          <section className="dashboard-section">
            <h3>스킬별 기여</h3>
            <div className="report-list">
              {contributions.map((item) => (
                <article className="report-item" key={`${item.skill_id}-${item.skill_name}`}>
                  <strong>
                    {item.skill_id}. {item.skill_name} · {item.persona}
                  </strong>
                  <small>신뢰도 {formatPercent(item.confidence)}</small>
                  <p>{item.summary}</p>
                  <InlineList label="핵심 산출" values={item.key_outputs} />
                </article>
              ))}
            </div>
          </section>

          <div className="result-grid">
            <section className="result-card">
              <h3>통합 의견</h3>
              <p>{result.synthesized_view || "통합 의견이 없습니다."}</p>
            </section>
            <section className="result-card">
              <h3>투자 논거</h3>
              <p>{thesis.thesis || "투자 논거가 없습니다."}</p>
              <InlineList label="강세 트리거" values={thesis.bull_triggers} />
              <InlineList label="약세 트리거" values={thesis.bear_triggers} />
            </section>
          </div>

          <div className="result-grid">
            <ListBlock title="합의된 의견" items={result.consensus} />
            <ConflictBlock conflicts={result.conflicts} />
            <ListBlock title="시나리오 맵" items={result.scenario_map} />
            <ListBlock title="매매 계획" items={result.trade_plan} />
            <ListBlock title="복리 성장주 관점" items={result.compounder_notes} />
            <ListBlock title="무효화 조건" items={result.invalidation_conditions} />
            <ListBlock title="추적 항목" items={(result.watch_items || []).map(formatWatchItem)} />
            <ListBlock title="다음 행동" items={result.next_actions} />
          </div>

          {Array.isArray(dataQuality.missing_data) && dataQuality.missing_data.length ? (
            <section className="dashboard-section">
              <ListBlock title="부족한 데이터" items={dataQuality.missing_data} />
            </section>
          ) : null}

          {result.storage?.relative_path ? (
            <p className="saved-path">저장 데이터: {result.storage.relative_path}</p>
          ) : null}
        </div>
      ) : null}
    </section>
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

function ListBlock({ title, items }) {
  const normalized = Array.isArray(items) ? items.filter(Boolean) : [];

  return (
    <section className="list-block">
      <h3>{title}</h3>
      {normalized.length > 0 ? (
        <ul>
          {normalized.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 항목이 없습니다.</p>
      )}
    </section>
  );
}

function ConflictBlock({ conflicts }) {
  const normalized = Array.isArray(conflicts) ? conflicts : [];
  return (
    <section className="list-block">
      <h3>충돌/주의점</h3>
      {normalized.length > 0 ? (
        <ul>
          {normalized.map((item) => (
            <li key={item.topic}>
              {item.topic}: {item.resolution}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 충돌이 없습니다.</p>
      )}
    </section>
  );
}

function InlineList({ label, values }) {
  const normalized = Array.isArray(values) ? values.filter(Boolean) : [];
  if (normalized.length === 0) {
    return null;
  }

  return (
    <small>
      {label}: {normalized.join(", ")}
    </small>
  );
}

function formatWatchItem(item) {
  if (!item) {
    return "";
  }
  return `${item.metric}: ${item.condition}이면 ${item.action} (${translatePriority(item.priority)})`;
}

function translatePriority(priority) {
  const labels = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return labels[priority] || priority || "보통";
}

function translateQuality(value) {
  const labels = {
    high: "높음",
    medium: "보통",
    low: "낮음",
  };
  return labels[value] || value || "-";
}

function formatPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return `${Math.round(numeric * 100)}%`;
}
