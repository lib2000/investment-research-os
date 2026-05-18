import { useEffect, useState } from "react";
import { parseNumberInput } from "../../shared/format/money.js";

export function EarningsPage({ researchApi, initialTicker = "PL" }) {
  const [ticker, setTicker] = useState(initialTicker || "PL");
  const [quarter, setQuarter] = useState("최신 발표 실적");
  const [earningsReportDate, setEarningsReportDate] = useState("");
  const [priceReaction, setPriceReaction] = useState("");
  const [previousEarningsDate, setPreviousEarningsDate] = useState("");
  const [nextEarningsDate, setNextEarningsDate] = useState("");
  const [guidanceChange, setGuidanceChange] = useState("유지");
  const [epsReported, setEpsReported] = useState("");
  const [epsExpected, setEpsExpected] = useState("");
  const [revenueReported, setRevenueReported] = useState("");
  const [revenueExpected, setRevenueExpected] = useState("");
  const [managementTone, setManagementTone] = useState("");
  const [marketContext, setMarketContext] = useState("");
  const [previousEarningsSummary, setPreviousEarningsSummary] = useState("");
  const [nextEarningsGuidance, setNextEarningsGuidance] = useState("");
  const [keyNumbers, setKeyNumbers] = useState("");
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [status, setStatus] = useState("대기");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [latestReference, setLatestReference] = useState(null);

  useEffect(() => {
    setTicker(String(initialTicker || "PL").trim().toUpperCase());
  }, [initialTicker]);

  async function fillLatestEarnings() {
    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      setError("티커를 입력하세요.");
      return;
    }
    setStatus("최신 실적 조회 중");
    setError("");
    try {
      const dashboard = await researchApi.dashboard(normalizedTicker);
      const profile = dashboard?.ticker_profile || {};
      const latest = profile.latest_earnings_profile || {};
      setLatestReference(dashboard?.latest_earnings_reference || latest);
      setQuarter(latest.quarter || profile.latest_reported_quarter || "최신 발표 실적");
      setEarningsReportDate(latest.earnings_report_date || profile.latest_reported_earnings_date || "");
      setPreviousEarningsDate(profile.previous_earnings_date || "");
      setNextEarningsDate(profile.next_earnings_date || latest.next_earnings_date || "");
      setPriceReaction(latest.price_reaction || "");
      setGuidanceChange(latest.guidance_change || "유지");
      setEpsReported(valueOrBlank(latest.eps_reported));
      setEpsExpected(valueOrBlank(latest.eps_expected));
      setRevenueReported(valueOrBlank(latest.revenue_reported));
      setRevenueExpected(valueOrBlank(latest.revenue_expected));
      setManagementTone(latest.management_tone || "");
      setMarketContext(latest.market_context || "");
      setPreviousEarningsSummary(latest.previous_earnings_summary || "");
      setNextEarningsGuidance(latest.next_earnings_guidance || "");
      setKeyNumbers(latest.key_numbers ? JSON.stringify(latest.key_numbers, null, 2) : "");
      setStatus("최신 실적 자동 채움 완료");
    } catch (nextError) {
      setStatus("최신 실적 조회 실패");
      setError(nextError.message);
    }
  }

  async function submitEarnings(event) {
    event.preventDefault();
    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      setStatus("실행 보류");
      setError("티커를 입력하세요.");
      return;
    }
    setStatus("실적 반응 분석 중");
    setError("");
    setResult(null);
    try {
      const parsedKeyNumbers = parseKeyNumbers(keyNumbers);
      const response = await researchApi.runEarningsReaction({
        ticker: normalizedTicker,
        quarter: quarter || "최신 발표 실적",
        earningsReportDate: earningsReportDate || null,
        priceReaction,
        previousEarningsDate: previousEarningsDate || null,
        previousEarningsSummary: previousEarningsSummary || null,
        nextEarningsDate: nextEarningsDate || null,
        nextEarningsGuidance: nextEarningsGuidance || null,
        epsReported: parseOptionalNumber(epsReported),
        epsExpected: parseOptionalNumber(epsExpected),
        revenueReported: parseOptionalNumber(revenueReported),
        revenueExpected: parseOptionalNumber(revenueExpected),
        guidanceChange,
        managementTone: managementTone || null,
        marketContext: marketContext || null,
        keyNumbers: parsedKeyNumbers,
        autoInjectData,
        saveResult: true,
      });
      setResult(response);
      setStatus("실적 분석 완료");
    } catch (nextError) {
      setStatus("실적 분석 실패");
      setError(nextError.message);
    }
  }

  return (
    <section className="panel earnings-panel">
      <div className="panel-heading">
        <div>
          <h2>실적분석</h2>
          <p>가장 최근 발표 실적을 기준으로 주가 반응, 가이던스, 다음 실적 전 확인 항목을 정리합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <form className="earnings-form" onSubmit={submitEarnings}>
        <div className="earnings-form-grid">
          <label>
            티커
            <input value={ticker} onChange={(event) => setTicker(event.target.value)} />
          </label>
          <label>
            분기
            <input value={quarter} onChange={(event) => setQuarter(event.target.value)} />
          </label>
          <label>
            실적 발표일
            <input type="date" value={earningsReportDate} onChange={(event) => setEarningsReportDate(event.target.value)} />
          </label>
          <label>
            다음 실적 예정일
            <input type="date" value={nextEarningsDate} onChange={(event) => setNextEarningsDate(event.target.value)} />
          </label>
          <label>
            직전 실적일
            <input type="date" value={previousEarningsDate} onChange={(event) => setPreviousEarningsDate(event.target.value)} />
          </label>
          <label>
            주가 반응
            <input value={priceReaction} onChange={(event) => setPriceReaction(event.target.value)} placeholder="예: 발표 후 시간외 +22%, 정규장 +8.7%" />
          </label>
          <label>
            가이던스 변화
            <select value={guidanceChange} onChange={(event) => setGuidanceChange(event.target.value)}>
              <option value="상향">상향</option>
              <option value="유지">유지</option>
              <option value="하향">하향</option>
              <option value="혼합">혼합</option>
            </select>
          </label>
          <label>
            EPS 발표
            <input value={epsReported} onChange={(event) => setEpsReported(event.target.value)} />
          </label>
          <label>
            EPS 예상
            <input value={epsExpected} onChange={(event) => setEpsExpected(event.target.value)} />
          </label>
          <label>
            매출 발표
            <input value={revenueReported} onChange={(event) => setRevenueReported(event.target.value)} />
          </label>
          <label>
            매출 예상
            <input value={revenueExpected} onChange={(event) => setRevenueExpected(event.target.value)} />
          </label>
          <label className="wide-field">
            경영진 톤
            <input value={managementTone} onChange={(event) => setManagementTone(event.target.value)} />
          </label>
          <label className="wide-field">
            시장 맥락
            <input value={marketContext} onChange={(event) => setMarketContext(event.target.value)} />
          </label>
          <label className="wide-field">
            직전 실적 주요 내용
            <textarea value={previousEarningsSummary} onChange={(event) => setPreviousEarningsSummary(event.target.value)} />
          </label>
          <label className="wide-field">
            다음 실적 가이던스
            <textarea value={nextEarningsGuidance} onChange={(event) => setNextEarningsGuidance(event.target.value)} />
          </label>
          <label className="wide-field">
            추가 핵심 수치 JSON
            <textarea value={keyNumbers} onChange={(event) => setKeyNumbers(event.target.value)} placeholder='예: {"FY2026 Q4 매출": "8,680만 달러"}' />
          </label>
        </div>
        <label className="check-row earnings-check">
          <input
            type="checkbox"
            checked={autoInjectData}
            onChange={(event) => setAutoInjectData(event.target.checked)}
          />
          시장/재무 데이터 자동 주입
        </label>
        <div className="dashboard-button-row earnings-buttons">
          <button className="secondary-button" type="button" onClick={fillLatestEarnings}>
            최신 실적 자동 채움
          </button>
          <button type="submit">실적 반응 분석</button>
        </div>
      </form>

      {error ? <div className="warning-box">{error}</div> : null}
      {latestReference ? <LatestReference reference={latestReference} /> : null}
      {result ? <EarningsResult result={result} /> : <EarningsGuide />}
    </section>
  );
}

function LatestReference({ reference }) {
  return (
    <section className="dashboard-section">
      <div className="info-card ok">
        <span>최신 실적 기준</span>
        <strong>{reference.official_quarter || reference.quarter || "확인됨"}</strong>
        <p>
          발표일 {reference.official_earnings_report_date || reference.earnings_report_date || "미등록"} · 다음{" "}
          {reference.next_earnings_date || "미등록"}
        </p>
      </div>
    </section>
  );
}

function EarningsGuide() {
  return (
    <section className="dashboard-section">
      <div className="info-card">
        <span>권장 흐름</span>
        <strong>최신 실적 자동 채움</strong>
        <p>먼저 버튼을 눌러 공식 최신 발표일, 직전 실적일, 다음 실적 예정일과 주요 수치를 채운 뒤 분석하세요.</p>
      </div>
    </section>
  );
}

function EarningsResult({ result }) {
  return (
    <div className="earnings-result">
      <section className="dashboard-section">
        <h3>실적 반응 요약</h3>
        <div className="dashboard-card-grid">
          <Metric label="티커" value={result.ticker} text={result.quarter} />
          <Metric label="공식 최신 발표일" value={result.official_latest_earnings_report_date || "미등록"} text={result.official_latest_quarter || "분기 미등록"} />
          <Metric label="실적 발표일" value={result.earnings_report_date || "미입력"} text={`다음 ${result.next_earnings_date || "미입력"}`} />
          <Metric label="반응 유형" value={result.reaction_type || "미확인"} text={result.sentiment_shift || "센티먼트 미확인"} />
        </div>
      </section>

      <section className="dashboard-section">
        <div className="report-item">
          <strong>핵심 판단</strong>
          <p>{result.headline_assessment}</p>
          <small>기준 상태: {result.earnings_reference_status} · 증거 상태: {result.evidence_status}</small>
          <small>캘린더 출처: {result.earnings_calendar_source || "미등록"}</small>
        </div>
      </section>

      <section className="dashboard-section two-column">
        <ListBlock title="직전 실적 주요 내용" items={withDatePrefix(result.previous_earnings_date, result.previous_earnings_key_takeaways)} />
        <ListBlock title="다음 실적 전 확인할 항목" items={result.watch_before_next_earnings} />
      </section>

      <section className="dashboard-section two-column">
        <div className="report-item">
          <strong>가이던스 평가</strong>
          <p>{result.guidance_assessment}</p>
          <small>{result.next_earnings_guidance}</small>
        </div>
        <ListBlock title="투자 논거 영향" items={result.thesis_implications} />
      </section>

      <section className="dashboard-section">
        <h3>주요 수치</h3>
        <table className="mini-table">
          <thead>
            <tr>
              <th>항목</th>
              <th>발표</th>
              <th>예상</th>
              <th>해석</th>
            </tr>
          </thead>
          <tbody>
            {(result.metrics || []).map((metric) => (
              <tr key={metric.name}>
                <td>{metric.name}</td>
                <td>{formatNullable(metric.reported)}</td>
                <td>{formatNullable(metric.expected)}</td>
                <td>{metric.interpretation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="dashboard-section two-column">
        <ListBlock title="보강 필요 입력" items={result.missing_inputs} emptyText="없음" />
        <ListBlock title="다음 액션" items={result.next_actions} />
      </section>
      {result.storage?.relative_path || result.storage?.path ? (
        <section className="dashboard-section">
          <div className="report-item">
            <strong>저장 데이터</strong>
            <small>{result.storage.relative_path || result.storage.path}</small>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Metric({ label, value, text }) {
  return (
    <article className="info-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </article>
  );
}

function ListBlock({ title, items, emptyText = "표시할 항목이 없습니다." }) {
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
        <p className="muted-text">{emptyText}</p>
      )}
    </div>
  );
}

function parseOptionalNumber(value) {
  const parsed = parseNumberInput(value);
  return parsed === null ? null : parsed;
}

function parseKeyNumbers(value) {
  if (!value.trim()) {
    return {};
  }
  return JSON.parse(value);
}

function valueOrBlank(value) {
  return value === null || value === undefined ? "" : String(value);
}

function formatNullable(value) {
  return value === null || value === undefined || value === "" ? "n/a" : String(value);
}

function withDatePrefix(date, items) {
  const list = Array.isArray(items) ? items : [];
  if (!date) {
    return list;
  }
  return [`직전 실적일: ${date}`, ...list];
}
