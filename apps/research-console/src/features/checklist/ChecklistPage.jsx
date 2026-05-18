import { useMemo, useState } from "react";

const CHECKLIST_ITEMS = [
  ["business_model", "비즈니스 모델 이해"],
  ["revenue_drivers", "수익 동력"],
  ["market_size", "시장 규모와 성장성"],
  ["competitive_advantage", "경쟁 우위"],
  ["financial_growth", "매출/이익 성장률"],
  ["margin_quality", "마진 구조"],
  ["cash_flow", "현금흐름과 FCF"],
  ["balance_sheet", "재무 건전성"],
  ["capital_allocation", "자본 배분"],
  ["management_quality", "경영진 평가"],
  ["valuation", "밸류에이션"],
  ["ownership_flow", "수급과 주주 구조"],
  ["industry_cycle", "산업 사이클"],
  ["regulatory_risk", "규제 리스크"],
  ["red_flags", "위험 신호"],
  ["exit_criteria", "투자 철회 기준"],
];

export function ChecklistPage({ researchApi }) {
  const [ticker, setTicker] = useState("PL");
  const [checkedItems, setCheckedItems] = useState(() => new Set());
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const isLoading = status === "loading";
  const checkedCount = checkedItems.size;
  const completionRate = checkedCount / CHECKLIST_ITEMS.length;
  const completionPercent = Math.round(completionRate * 100);
  const checkedItemKeys = useMemo(() => Array.from(checkedItems), [checkedItems]);

  function toggleItem(key) {
    setCheckedItems((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function setAll(value) {
    setCheckedItems(value ? new Set(CHECKLIST_ITEMS.map(([key]) => key)) : new Set());
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("loading");
    setError(null);

    try {
      const response = await researchApi.assessResearchChecklist({
        ticker,
        checkedItems: checkedItemKeys,
        notes: notes.trim() || null,
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
          <h2>리서치 체크리스트</h2>
          <p>16개 항목을 체크하면 완료율이 즉시 갱신되고, 준비도 평가와 다음 단계가 생성됩니다.</p>
        </div>
        <span className="status-pill">
          {isLoading ? "분석 중" : result ? "분석 완료" : `${completionPercent}% 완료`}
        </span>
      </div>

      <form className="checklist-form" onSubmit={handleSubmit}>
        <div className="checklist-controls">
          <label>
            티커
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <div className="progress-panel">
            <div className="progress-label">
              <strong>{completionPercent}%</strong>
              <span>
                {checkedCount}/{CHECKLIST_ITEMS.length}개 완료
              </span>
            </div>
            <div className="progress-track" aria-label="체크리스트 완료율">
              <span style={{ width: `${completionPercent}%` }} />
            </div>
          </div>
          <div className="action-row checklist-quick-actions">
            <button className="secondary-button" type="button" onClick={() => setAll(true)}>
              전체 선택
            </button>
            <button className="secondary-button" type="button" onClick={() => setAll(false)}>
              전체 해제
            </button>
          </div>
        </div>

        <div className="checklist-grid">
          {CHECKLIST_ITEMS.map(([key, label]) => (
            <label className={`check-card ${checkedItems.has(key) ? "checked" : ""}`} key={key}>
              <input
                type="checkbox"
                checked={checkedItems.has(key)}
                onChange={() => toggleItem(key)}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>

        <label>
          보강 메모
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="아직 불확실한 항목, 확인한 출처, 다음에 점검할 질문을 적어두세요."
          />
        </label>

        <div className="action-row">
          <button type="submit" disabled={isLoading || !ticker.trim()}>
            {isLoading ? "투자 준비도 평가 중..." : "완성된 항목 분석"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="warning-box">
          오류가 발생했습니다: {error.message || "체크리스트 평가 요청에 실패했습니다."}
        </div>
      ) : null}

      {result ? (
        <div className="checklist-result">
          <div className="risk-metrics">
            <Metric label="티커" value={result.ticker || ticker} />
            <Metric label="완료율" value={`${Math.round((result.completion_rate || 0) * 100)}%`} />
            <Metric label="완료 항목" value={`${result.completed_count}/${result.total_count}`} />
            <Metric label="투자 준비도" value={result.readiness_level || "-"} />
          </div>

          <section className="result-card">
            <h3>준비도 평가</h3>
            <p>{result.readiness_summary || "평가 요약이 없습니다."}</p>
          </section>

          <div className="result-grid">
            <ListBlock
              title="완료된 항목"
              items={(result.completed_items || []).map((item) => item.label)}
            />
            <ListBlock
              title="미완료 항목"
              items={(result.missing_items || []).map((item) => item.label)}
            />
            <ListBlock title="다음 단계" items={result.next_steps} />
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
