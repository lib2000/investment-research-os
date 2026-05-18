import { useState } from "react";

const DEFAULT_MACRO =
  "AI CAPEX가 강하고 금리 인하 기대가 살아 있으며, 전력 인프라 수요와 에너지 가격 변동성이 함께 커지고 있습니다.";

export function SectorOpportunityPage({ researchApi }) {
  const [region, setRegion] = useState("US");
  const [period, setPeriod] = useState("6개월");
  const [style, setStyle] = useState("균형형");
  const [macroEnvironment, setMacroEnvironment] = useState(DEFAULT_MACRO);
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const isLoading = status === "loading";
  const rankedSectors = Array.isArray(result?.ranked_sectors) ? result.ranked_sectors : [];
  const companies = Array.isArray(result?.recommended_companies) ? result.recommended_companies : [];
  const topSector = rankedSectors[0];

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);

    try {
      const response = await researchApi.runSectorOpportunity({
        macroEnvironment,
        period,
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
          <h2>섹터 기회 발굴</h2>
          <p>금리, AI 투자, 에너지 가격 같은 거시 환경을 바탕으로 유망 섹터와 후보 기업을 찾습니다.</p>
        </div>
        <span className="status-pill">
          {isLoading ? "분석 중" : result ? "분석 완료" : "대기 중"}
        </span>
      </div>

      <form className="sector-form" onSubmit={handleSubmit}>
        <div className="sector-form-grid">
          <label>
            지역
            <select value={region} onChange={(event) => setRegion(event.target.value)}>
              <option value="US">미국</option>
              <option value="KR">한국</option>
              <option value="GLOBAL">글로벌</option>
            </select>
          </label>
          <label>
            기간
            <input value={period} onChange={(event) => setPeriod(event.target.value)} />
          </label>
          <label>
            스타일
            <select value={style} onChange={(event) => setStyle(event.target.value)}>
              <option value="균형형">균형형</option>
              <option value="성장">성장</option>
              <option value="가치">가치</option>
              <option value="방어">방어</option>
            </select>
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
          거시 환경
          <textarea
            value={macroEnvironment}
            onChange={(event) => setMacroEnvironment(event.target.value)}
            placeholder="예: 금리 인하 기대, AI 인프라 투자, 원자재 가격, 에너지 가격, 환율, 정책 변화"
          />
        </label>

        <div className="action-row">
          <button type="submit" disabled={isLoading || !macroEnvironment.trim()}>
            {isLoading ? "섹터 분석 중..." : "섹터 기회 발굴"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="warning-box">
          오류가 발생했습니다: {error.message || "섹터 분석 요청에 실패했습니다."}
        </div>
      ) : null}

      {result ? (
        <div className="sector-result">
          <div className="risk-metrics">
            <Metric label="저장 키" value={result.research_key || "-"} />
            <Metric label="지역/기간" value={`${result.region || region} · ${result.period || period}`} />
            <Metric label="스타일" value={result.style || style} />
            <Metric label="최우선 섹터" value={topSector ? `${topSector.sector} (${topSector.score}/100)` : "-"} />
          </div>

          <div className="result-grid">
            <section className="result-card">
              <h3>거시 요약</h3>
              <p>{result.macro_summary || "요약이 없습니다."}</p>
            </section>
            <section className="result-card">
              <h3>배분 관점</h3>
              <p>{result.allocation_view || "배분 관점이 없습니다."}</p>
            </section>
          </div>

          <section className="dashboard-section">
            <h3>유망 섹터 순위</h3>
            <div className="report-list">
              {rankedSectors.map((sector) => (
                <article className="report-item" key={sector.sector}>
                  <strong>
                    {sector.sector} · {sector.score}/100
                  </strong>
                  <p>{sector.rationale}</p>
                  <InlineList label="순풍" values={sector.macro_tailwinds} />
                  <InlineList label="리스크" values={sector.key_risks} />
                  <InlineList label="우선 확인 종목" values={sector.preferred_tickers} />
                </article>
              ))}
              {rankedSectors.length === 0 ? <EmptyMessage message="표시할 섹터 후보가 없습니다." /> : null}
            </div>
          </section>

          <section className="dashboard-section">
            <h3>후보 기업</h3>
            <div className="report-list">
              {companies.map((company) => (
                <article className="report-item" key={`${company.ticker}-${company.company_name}`}>
                  <strong>
                    {company.ticker} · {company.company_name} · 적합도 {company.fit_score}/100
                  </strong>
                  <small>{company.sector}</small>
                  <p>{company.thesis}</p>
                  <InlineList label="촉매" values={company.catalysts} />
                  <InlineList label="리스크" values={company.risks} />
                </article>
              ))}
              {companies.length === 0 ? <EmptyMessage message="표시할 후보 기업이 없습니다." /> : null}
            </div>
          </section>

          <div className="result-grid">
            <ListBlock title="관찰 항목" items={result.watch_items} />
            <ListBlock title="핵심 리스크" items={result.key_risks} />
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

function EmptyMessage({ message }) {
  return <p className="muted-text">{message}</p>;
}
