import { useRef, useState } from "react";

export function MarketClosePage({ researchApi }) {
  const [market, setMarket] = useState("US");
  const [sessionDate, setSessionDate] = useState("");
  const [rawSummary, setRawSummary] = useState("");
  const [selectedFileName, setSelectedFileName] = useState("");
  const [status, setStatus] = useState("대기");
  const [error, setError] = useState("");
  const [review, setReview] = useState(null);
  const [history, setHistory] = useState(null);
  const fileInputRef = useRef(null);

  async function saveReview(event) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0] || null;
    if (!rawSummary.trim() && !file) {
      setStatus("저장 보류");
      setError("시장 요약을 입력하거나 파일을 선택하세요.");
      return;
    }
    setStatus("시장 상황 평가 중");
    setError("");
    setReview(null);
    try {
      const filePayload = file ? await readFilePayload(file) : {};
      const result = await researchApi.saveMarketCloseReview({
        market,
        sessionDate: sessionDate || null,
        rawSummary: rawSummary.trim(),
        fileName: filePayload.fileName || null,
        fileMimeType: filePayload.fileMimeType || null,
        fileSize: filePayload.fileSize || null,
        fileContentBase64: filePayload.fileContentBase64 || null,
        saveResult: true,
      });
      setReview(result);
      setStatus("저장 완료");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setSelectedFileName("");
    } catch (nextError) {
      setStatus("저장 실패");
      setError(nextError.message);
    }
  }

  async function loadHistory() {
    setStatus("누적 시장일지 조회 중");
    setError("");
    try {
      const result = await researchApi.marketCloseHistory(market || "ALL");
      setHistory(result);
      setStatus("누적 조회 완료");
    } catch (nextError) {
      setStatus("조회 실패");
      setError(nextError.message);
    }
  }

  return (
    <section className="panel market-panel">
      <div className="panel-heading">
        <div>
          <h2>시장일지</h2>
          <p>폐장 후 시장 요약을 저장하면 시스템이 심리, 리스크, 장세와 투자 활용 포인트를 자동 정리합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <form className="market-form" onSubmit={saveReview}>
        <div className="market-form-grid">
          <label>
            시장
            <select value={market} onChange={(event) => setMarket(event.target.value)}>
              <option value="US">미국</option>
              <option value="KR">한국</option>
              <option value="GLOBAL">글로벌</option>
              <option value="ALL">전체 조회용</option>
            </select>
          </label>
          <label>
            폐장 기준일
            <input type="date" value={sessionDate} onChange={(event) => setSessionDate(event.target.value)} />
          </label>
        </div>
        <label>
          폐장 후 시장 요약
          <textarea
            value={rawSummary}
            onChange={(event) => setRawSummary(event.target.value)}
            placeholder="지수 흐름, 금리/환율/유가, 수급, 주도 섹터, 주요 뉴스, 내 판단 메모를 그대로 입력하세요. 기호는 서버에서 정리해 텍스트 중심으로 반영합니다."
          />
        </label>
        <label>
          파일 입력 (모든 파일)
          <input
            ref={fileInputRef}
            type="file"
            onChange={(event) => setSelectedFileName(event.target.files?.[0]?.name || "")}
          />
        </label>
        {selectedFileName ? <p className="selected-file">선택 파일: {selectedFileName}</p> : null}
        <div className="dashboard-button-row market-buttons">
          <button type="submit">시장 상황 평가 저장</button>
          <button className="secondary-button" type="button" onClick={loadHistory}>
            누적 시장 일지 조회
          </button>
        </div>
      </form>

      {error ? <div className="warning-box">{error}</div> : null}
      {review ? <MarketReviewResult result={review} /> : null}
      {history ? <MarketHistory result={history} /> : null}
      {!review && !history ? <MarketGuide /> : null}
    </section>
  );
}

function MarketGuide() {
  return (
    <section className="dashboard-section">
      <div className="info-card">
        <span>자동 활용</span>
        <strong>누적 시장 메모리</strong>
        <p>시장일지는 향후 섹터 발굴, 매매 전략, 포트폴리오 리스크 판단에 자동으로 활용됩니다.</p>
      </div>
    </section>
  );
}

function MarketReviewResult({ result }) {
  const entry = result.entry || {};
  return (
    <div className="market-result">
      <section className="dashboard-section">
        <h3>시장 판단 결과</h3>
        <div className="dashboard-card-grid">
          <Metric label="기준일" value={entry.session_date || "미확인"} text={entry.market || "시장 미확인"} />
          <Metric label="시장 심리" value={entry.sentiment || "미확인"} text="입력 요약 기반 자동 판정" />
          <Metric label="리스크 레벨" value={entry.risk_level || "미확인"} text="누적 일지와 현재 요약 비교" />
          <Metric label="장세 판단" value={entry.regime || "미확인"} text={`누적 기록 ${result.history_count || 0}개`} />
        </div>
      </section>

      <section className="dashboard-section two-column">
        <ListBlock title="핵심 동인" items={entry.key_drivers} />
        <ListBlock title="섹터/테마 시사점" items={entry.sector_implications} />
      </section>
      <section className="dashboard-section two-column">
        <ListBlock title="포트폴리오 액션" items={entry.portfolio_actions} />
        <ListBlock title="다음 장 체크포인트" items={entry.next_session_watch} />
      </section>
      <section className="dashboard-section two-column">
        <ListBlock title="시스템 자동 활용 초점" items={entry.auto_utilization_focus} />
        <ListBlock title="누적 패턴" items={result.cumulative_patterns} />
      </section>
      <section className="dashboard-section">
        <h3>정리된 시장 요약</h3>
        <div className="preview-block">
          <pre>{entry.raw_summary || "표시할 요약이 없습니다."}</pre>
        </div>
      </section>
      {result.storage?.path || result.storage_path ? (
        <section className="dashboard-section">
          <div className="report-item">
            <strong>저장 데이터</strong>
            <small>{result.storage?.path || result.storage_path}</small>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function MarketHistory({ result }) {
  const entries = Array.isArray(result.entries) ? result.entries : [];
  return (
    <section className="dashboard-section">
      <h3>누적 시장 일지</h3>
      <div className="report-list">
        {entries.slice(0, 12).map((entry) => (
          <article className="report-item" key={entry.entry_id}>
            <strong>
              {entry.session_date} · {entry.market} · {entry.regime}
            </strong>
            <p>
              심리 {entry.sentiment} · 리스크 {entry.risk_level}
            </p>
            <small>{(entry.key_drivers || []).slice(0, 2).join(" / ") || "핵심 동인 없음"}</small>
          </article>
        ))}
        {!entries.length ? <p className="muted-text">저장된 시장일지가 없습니다.</p> : null}
      </div>
    </section>
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

function readFilePayload(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve({
        fileName: file.name,
        fileMimeType: file.type || "application/octet-stream",
        fileSize: file.size,
        fileContentBase64: result.includes(",") ? result.split(",").pop() : result,
      });
    };
    reader.onerror = () => reject(reader.error || new Error("파일 읽기 실패"));
    reader.readAsDataURL(file);
  });
}
