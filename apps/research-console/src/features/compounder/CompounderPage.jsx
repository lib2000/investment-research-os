import { useMemo, useState } from "react";

const DEFAULT_CRITERIA =
  "강력한 매출 성장, 높은 매출총이익률, 높은 FCF 마진, 지속 가능한 경쟁 우위, 확장 가능한 플랫폼 모델을 가진 기업을 찾습니다.";

export function CompounderPage({ researchApi }) {
  const [region, setRegion] = useState("KR");
  const [sector, setSector] = useState("전체");
  const [style, setStyle] = useState("퀄리티 성장");
  const [minMarketCap, setMinMarketCap] = useState("1000");
  const [maxMarketCap, setMaxMarketCap] = useState("");
  const [screeningCriteria, setScreeningCriteria] = useState(DEFAULT_CRITERIA);
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const isLoading = status === "loading";
  const isKoreanRegion = region === "KR";
  const marketCapUnit = isKoreanRegion ? "억원" : "백만 달러";
  const candidates = Array.isArray(result?.candidates) ? result.candidates : [];
  const topCandidate = candidates[0];

  const normalizedRejectedReasons = useMemo(
    () => (Array.isArray(result?.rejected_reasons) ? result.rejected_reasons : []),
    [result]
  );

  function handleRegionChange(nextRegion) {
    setRegion(nextRegion);
    if (nextRegion === "KR") {
      setMinMarketCap("1000");
    } else {
      setMinMarketCap("1000");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);

    try {
      const response = await researchApi.runLongTermCompounder({
        screeningCriteria,
        minMarketCap: parseOptionalNumber(minMarketCap),
        maxMarketCap: parseOptionalNumber(maxMarketCap),
        sector,
        region,
        style,
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
          <h2>복리 성장주</h2>
          <p>매출 성장, 마진, 현금흐름, 경쟁 우위, 확장성을 기준으로 장기 후보를 선별합니다.</p>
        </div>
        <span className="status-pill">
          {isLoading ? "분석 중" : result ? "분석 완료" : "대기 중"}
        </span>
      </div>

      <form className="compounder-form" onSubmit={handleSubmit}>
        <div className="compounder-form-grid">
          <label>
            지역
            <select value={region} onChange={(event) => handleRegionChange(event.target.value)}>
              <option value="KR">한국</option>
              <option value="US">미국</option>
            </select>
          </label>
          <label>
            섹터
            <select value={sector} onChange={(event) => setSector(event.target.value)}>
              <option value="전체">전체</option>
              <option value="기술">기술</option>
              <option value="헬스케어">헬스케어</option>
              <option value="소비재">소비재</option>
              <option value="금융">금융</option>
              <option value="산업재">산업재</option>
            </select>
          </label>
          <label>
            스타일
            <select value={style} onChange={(event) => setStyle(event.target.value)}>
              <option value="퀄리티 성장">퀄리티 성장</option>
              <option value="고성장">고성장</option>
              <option value="방어 성장">방어 성장</option>
            </select>
          </label>
          <label>
            최소 시가총액 ({marketCapUnit})
            <input
              inputMode="decimal"
              value={minMarketCap}
              onChange={(event) => setMinMarketCap(event.target.value)}
            />
          </label>
          <label>
            최대 시가총액 ({marketCapUnit})
            <input
              inputMode="decimal"
              value={maxMarketCap}
              onChange={(event) => setMaxMarketCap(event.target.value)}
              placeholder="제한 없음"
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
        </div>

        <label>
          스크리닝 기준
          <textarea
            value={screeningCriteria}
            onChange={(event) => setScreeningCriteria(event.target.value)}
            placeholder="예: 높은 매출 성장, 높은 매출총이익률, 넓은 경쟁 우위, 낮은 자본 집약도"
          />
        </label>

        <div className="action-row">
          <button type="submit" disabled={isLoading || !screeningCriteria.trim()}>
            {isLoading ? "복리 후보 분석 중..." : "복리 성장주 발굴"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="warning-box">
          오류가 발생했습니다: {error.message || "복리 성장주 분석 요청에 실패했습니다."}
        </div>
      ) : null}

      {result ? (
        <div className="compounder-result">
          <div className="risk-metrics">
            <Metric label="저장 키" value={result.research_key || "-"} />
            <Metric label="지역/섹터" value={`${result.region || region} · ${result.sector || sector}`} />
            <Metric label="스타일" value={result.style || style} />
            <Metric
              label="최우선 후보"
              value={topCandidate ? `${topCandidate.ticker} (${topCandidate.compounder_score}/100)` : "-"}
            />
          </div>

          <section className="result-card">
            <h3>요약</h3>
            <p>{result.summary || "요약이 없습니다."}</p>
          </section>

          <section className="dashboard-section">
            <h3>후보 기업</h3>
            <div className="report-list">
              {candidates.map((candidate) => (
                <article className="report-item" key={`${candidate.ticker}-${candidate.company_name}`}>
                  <strong>
                    {candidate.ticker} · {candidate.company_name} · 복리 점수 {candidate.compounder_score}/100
                  </strong>
                  <small>
                    {candidate.sector} · 시가총액 {formatMarketCap(candidate.market_cap, result.region || region)}
                  </small>
                  <div className="mini-metric-row">
                    <MiniMetric label="매출 성장" value={formatPercent(candidate.revenue_growth)} />
                    <MiniMetric label="매출총이익률" value={formatPercent(candidate.gross_margin)} />
                    <MiniMetric label="FCF 마진" value={formatPercent(candidate.free_cash_flow_margin)} />
                    <MiniMetric label="경쟁 우위" value={`${candidate.moat_score}/100`} />
                    <MiniMetric label="확장성" value={`${candidate.scalability_score}/100`} />
                  </div>
                  <p>{candidate.thesis}</p>
                  <InlineList label="재투자 활주로" values={[candidate.reinvestment_runway]} />
                  <InlineList label="핵심 리스크" values={candidate.key_risks} />
                  <InlineList label="추적 KPI" values={candidate.watch_kpis} />
                </article>
              ))}
              {candidates.length === 0 ? <p className="muted-text">표시할 후보 기업이 없습니다.</p> : null}
            </div>
          </section>

          <div className="result-grid">
            <ListBlock title="제외/주의 사유" items={normalizedRejectedReasons} />
            <ListBlock title="포트폴리오 구성 메모" items={result.portfolio_construction_notes} />
            <ListBlock title="다음 행동" items={result.next_actions} />
            <ListBlock
              title="주입 데이터"
              items={(result.injected_data || []).map((item) => `${item.label}: ${item.value}`)}
            />
          </div>

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

function MiniMetric({ label, value }) {
  return (
    <span className="mini-metric">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
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

function parseOptionalNumber(value) {
  const normalized = String(value || "").replaceAll(",", "").trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return `${Math.round(numeric * 100)}%`;
}

function formatMarketCap(value, region) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  const unit = String(region || "").toUpperCase().startsWith("KR") ? "억원" : "백만 달러";
  return `${numeric.toLocaleString("ko-KR", { maximumFractionDigits: 0 })} ${unit}`;
}
