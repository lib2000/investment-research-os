import { useEffect, useMemo, useState } from "react";

const EMPTY_TICKER = {
  ticker: "",
  priority: "medium",
  thesis: "",
  notes: "",
  tagsText: "",
};

const EMPTY_SECTOR = {
  name: "",
  region: "US",
  priority: "medium",
  thesis: "",
  notes: "",
  tagsText: "",
};

export function InterestsPage({ researchApi }) {
  const [tickers, setTickers] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [tickerDraft, setTickerDraft] = useState(EMPTY_TICKER);
  const [sectorDraft, setSectorDraft] = useState(EMPTY_SECTOR);
  const [status, setStatus] = useState("대기 중");
  const [error, setError] = useState("");
  const [storagePath, setStoragePath] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  const [activeEditor, setActiveEditor] = useState("tickers");

  const tickerCount = tickers.length;
  const sectorCount = sectors.length;
  const highPriorityCount = useMemo(
    () =>
      [...tickers, ...sectors].filter((item) => normalizePriority(item.priority) === "high").length,
    [tickers, sectors]
  );

  useEffect(() => {
    loadInterests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [researchApi]);

  async function loadInterests() {
    setStatus("관심목록 불러오는 중");
    setError("");
    try {
      const response = await researchApi.fetchInterests();
      applyResponse(response);
      setStatus("불러오기 완료");
    } catch (nextError) {
      setStatus("불러오기 실패");
      setError(nextError.message);
    }
  }

  async function saveAll(nextTickers = tickers, nextSectors = sectors) {
    setStatus("저장 중");
    setError("");
    try {
      const response = await researchApi.saveInterests({
        tickers: nextTickers.map(toTickerPayload),
        sectors: nextSectors.map(toSectorPayload),
      });
      applyResponse(response);
      setStatus("저장 완료");
    } catch (nextError) {
      setStatus("저장 실패");
      setError(nextError.message);
    }
  }

  function applyResponse(response) {
    setTickers((response.tickers || []).map(fromTickerPayload));
    setSectors((response.sectors || []).map(fromSectorPayload));
    setStoragePath(response.storage_path || "");
    setUpdatedAt(response.updated_at || "");
  }

  function addTicker() {
    const normalizedTicker = tickerDraft.ticker.trim().toUpperCase();
    if (!normalizedTicker) {
      setError("관심 종목 티커를 입력해야 추가할 수 있습니다.");
      return;
    }
    setError("");
    setTickers((current) => [
      ...current,
      {
        ...tickerDraft,
        ticker: normalizedTicker,
      },
    ]);
    setTickerDraft(EMPTY_TICKER);
  }

  function addSector() {
    const name = sectorDraft.name.trim();
    if (!name) {
      setError("관심 섹터 이름을 입력해야 추가할 수 있습니다.");
      return;
    }
    setError("");
    setSectors((current) => [
      ...current,
      {
        ...sectorDraft,
        name,
      },
    ]);
    setSectorDraft(EMPTY_SECTOR);
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>관심목록</h2>
          <p>보유 포트폴리오와 분리해서 향후 매수 후보 종목과 관심 섹터를 관리합니다.</p>
        </div>
        <span className="status-pill">{status}</span>
      </div>

      <div className="risk-metrics">
        <Metric label="관심 종목" value={`${tickerCount}개`} />
        <Metric label="관심 섹터" value={`${sectorCount}개`} />
        <Metric label="높은 우선순위" value={`${highPriorityCount}개`} />
        <Metric label="최근 저장" value={updatedAt || "-"} />
      </div>

      <div className="interest-tabs">
        <button
          className={activeEditor === "tickers" ? "" : "secondary-button"}
          type="button"
          onClick={() => setActiveEditor("tickers")}
        >
          관심 종목
        </button>
        <button
          className={activeEditor === "sectors" ? "" : "secondary-button"}
          type="button"
          onClick={() => setActiveEditor("sectors")}
        >
          관심 섹터
        </button>
        <button className="secondary-button" type="button" onClick={loadInterests}>
          불러오기
        </button>
        <button type="button" onClick={() => saveAll()}>
          전체 저장
        </button>
      </div>

      {error ? <div className="warning-box">{error}</div> : null}

      {activeEditor === "tickers" ? (
        <TickerEditor
          draft={tickerDraft}
          setDraft={setTickerDraft}
          tickers={tickers}
          setTickers={setTickers}
          addTicker={addTicker}
          saveAll={saveAll}
        />
      ) : (
        <SectorEditor
          draft={sectorDraft}
          setDraft={setSectorDraft}
          sectors={sectors}
          setSectors={setSectors}
          addSector={addSector}
          saveAll={saveAll}
        />
      )}

      {storagePath ? <p className="saved-path">저장 위치: {storagePath}</p> : null}
    </section>
  );
}

function TickerEditor({ draft, setDraft, tickers, setTickers, addTicker, saveAll }) {
  return (
    <div className="interest-editor">
      <div className="interest-add-grid">
        <label>
          티커
          <input
            value={draft.ticker}
            onChange={(event) => setDraft({ ...draft, ticker: event.target.value.toUpperCase() })}
            placeholder="예: JOBY"
          />
        </label>
        <PrioritySelect value={draft.priority} onChange={(priority) => setDraft({ ...draft, priority })} />
        <label>
          태그
          <input
            value={draft.tagsText}
            onChange={(event) => setDraft({ ...draft, tagsText: event.target.value })}
            placeholder="AI, 우주, 성장"
          />
        </label>
        <div className="interest-add-button">
          <button type="button" onClick={addTicker}>
            관심 종목 추가
          </button>
        </div>
        <label className="wide-field">
          투자 논거
          <input
            value={draft.thesis}
            onChange={(event) => setDraft({ ...draft, thesis: event.target.value })}
            placeholder="관심을 둔 핵심 이유"
          />
        </label>
        <label className="wide-field">
          메모
          <input
            value={draft.notes}
            onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
            placeholder="매수 조건, 확인할 이벤트, 리스크"
          />
        </label>
      </div>

      <EditableTickerList tickers={tickers} setTickers={setTickers} />
      <div className="action-row">
        <button type="button" onClick={() => saveAll()}>
          관심 종목 저장
        </button>
      </div>
    </div>
  );
}

function SectorEditor({ draft, setDraft, sectors, setSectors, addSector, saveAll }) {
  return (
    <div className="interest-editor">
      <div className="interest-add-grid">
        <label>
          섹터명
          <input
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            placeholder="예: 전력 인프라"
          />
        </label>
        <label>
          지역
          <select value={draft.region} onChange={(event) => setDraft({ ...draft, region: event.target.value })}>
            <option value="US">미국</option>
            <option value="KR">한국</option>
            <option value="GLOBAL">글로벌</option>
          </select>
        </label>
        <PrioritySelect value={draft.priority} onChange={(priority) => setDraft({ ...draft, priority })} />
        <div className="interest-add-button">
          <button type="button" onClick={addSector}>
            관심 섹터 추가
          </button>
        </div>
        <label className="wide-field">
          투자 논거
          <input
            value={draft.thesis}
            onChange={(event) => setDraft({ ...draft, thesis: event.target.value })}
            placeholder="관심 섹터로 보는 이유"
          />
        </label>
        <label className="wide-field">
          태그/메모
          <input
            value={draft.tagsText}
            onChange={(event) => setDraft({ ...draft, tagsText: event.target.value })}
            placeholder="AI, 전력망, 정책"
          />
        </label>
      </div>

      <EditableSectorList sectors={sectors} setSectors={setSectors} />
      <div className="action-row">
        <button type="button" onClick={() => saveAll()}>
          관심 섹터 저장
        </button>
      </div>
    </div>
  );
}

function EditableTickerList({ tickers, setTickers }) {
  if (tickers.length === 0) {
    return <p className="muted-text">저장된 관심 종목이 없습니다.</p>;
  }

  return (
    <div className="interest-list">
      {tickers.map((item, index) => (
        <article className="interest-row" key={`${item.ticker}-${index}`}>
          <input
            className="center-input"
            value={item.ticker}
            onChange={(event) => updateItem(setTickers, index, { ticker: event.target.value.toUpperCase() })}
          />
          <PrioritySelect value={item.priority} onChange={(priority) => updateItem(setTickers, index, { priority })} />
          <input
            value={item.thesis || ""}
            onChange={(event) => updateItem(setTickers, index, { thesis: event.target.value })}
            placeholder="투자 논거"
          />
          <input
            value={item.notes || ""}
            onChange={(event) => updateItem(setTickers, index, { notes: event.target.value })}
            placeholder="메모"
          />
          <input
            value={item.tagsText || ""}
            onChange={(event) => updateItem(setTickers, index, { tagsText: event.target.value })}
            placeholder="태그"
          />
          <button className="secondary-button" type="button" onClick={() => removeItem(setTickers, index)}>
            삭제
          </button>
        </article>
      ))}
    </div>
  );
}

function EditableSectorList({ sectors, setSectors }) {
  if (sectors.length === 0) {
    return <p className="muted-text">저장된 관심 섹터가 없습니다.</p>;
  }

  return (
    <div className="interest-list">
      {sectors.map((item, index) => (
        <article className="interest-row sector-interest-row" key={`${item.name}-${index}`}>
          <input
            value={item.name}
            onChange={(event) => updateItem(setSectors, index, { name: event.target.value })}
          />
          <select value={item.region} onChange={(event) => updateItem(setSectors, index, { region: event.target.value })}>
            <option value="US">미국</option>
            <option value="KR">한국</option>
            <option value="GLOBAL">글로벌</option>
          </select>
          <PrioritySelect value={item.priority} onChange={(priority) => updateItem(setSectors, index, { priority })} />
          <input
            value={item.thesis || ""}
            onChange={(event) => updateItem(setSectors, index, { thesis: event.target.value })}
            placeholder="투자 논거"
          />
          <input
            value={item.tagsText || ""}
            onChange={(event) => updateItem(setSectors, index, { tagsText: event.target.value })}
            placeholder="태그"
          />
          <button className="secondary-button" type="button" onClick={() => removeItem(setSectors, index)}>
            삭제
          </button>
        </article>
      ))}
    </div>
  );
}

function PrioritySelect({ value, onChange }) {
  return (
    <label>
      우선순위
      <select value={normalizePriority(value)} onChange={(event) => onChange(event.target.value)}>
        <option value="high">높음</option>
        <option value="medium">보통</option>
        <option value="low">낮음</option>
      </select>
    </label>
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

function updateItem(setter, index, patch) {
  setter((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
}

function removeItem(setter, index) {
  setter((current) => current.filter((_, itemIndex) => itemIndex !== index));
}

function normalizePriority(value) {
  return ["high", "medium", "low"].includes(value) ? value : "medium";
}

function splitTags(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function fromTickerPayload(item) {
  return {
    ticker: item.ticker || "",
    priority: normalizePriority(item.priority),
    thesis: item.thesis || "",
    notes: item.notes || "",
    tagsText: (item.tags || []).join(", "),
    verification: item.verification || null,
  };
}

function fromSectorPayload(item) {
  return {
    name: item.name || "",
    region: item.region || "US",
    priority: normalizePriority(item.priority),
    thesis: item.thesis || "",
    notes: item.notes || "",
    tagsText: (item.tags || []).join(", "),
  };
}

function toTickerPayload(item) {
  return {
    ticker: item.ticker,
    priority: normalizePriority(item.priority),
    thesis: item.thesis || null,
    notes: item.notes || null,
    tags: splitTags(item.tagsText),
  };
}

function toSectorPayload(item) {
  return {
    name: item.name,
    region: item.region || "US",
    priority: normalizePriority(item.priority),
    thesis: item.thesis || null,
    notes: item.notes || null,
    tags: splitTags(item.tagsText),
  };
}
