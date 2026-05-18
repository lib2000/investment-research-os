import { useRef, useState } from "react";

export function CapturePage({ researchApi }) {
  const [rawContent, setRawContent] = useState("");
  const [runThesisImpact, setRunThesisImpact] = useState(true);
  const [status, setStatus] = useState("대기");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [selectedFileName, setSelectedFileName] = useState("");
  const fileInputRef = useRef(null);

  async function submitCapture(event) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0] || null;
    if (!rawContent.trim() && !file) {
      setStatus("저장 보류");
      setError("텍스트를 입력하거나 파일을 선택하세요.");
      return;
    }

    setStatus("자동 분류 저장 중");
    setError("");
    setResult(null);
    try {
      const filePayload = file ? await readFilePayload(file) : {};
      const response = await researchApi.autoCapture({
        rawContent: rawContent.trim(),
        fileName: filePayload.fileName || null,
        fileMimeType: filePayload.fileMimeType || null,
        fileSize: filePayload.fileSize || null,
        fileContentBase64: filePayload.fileContentBase64 || null,
        runThesisImpact,
        saveResult: true,
      });
      setResult(response);
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

  return (
    <section className="panel capture-panel">
      <div className="panel-heading">
        <div>
          <h2>정보입력</h2>
          <p>뉴스, PDF, 리포트, 메모를 넣으면 종목/시장/섹터/정책 자료를 자동 분류하고 저장합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <form className="capture-form" onSubmit={submitCapture}>
        <label>
          텍스트 입력
          <textarea
            value={rawContent}
            onChange={(event) => setRawContent(event.target.value)}
            placeholder="종목 메모, 전체 시황, 섹터 전망, 거시경제 자료를 그대로 붙여넣으세요. 티커가 없어도 자동 분류합니다."
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
        <label className="check-row capture-check">
          <input
            type="checkbox"
            checked={runThesisImpact}
            onChange={(event) => setRunThesisImpact(event.target.checked)}
          />
          종목이 확인되면 기존 투자 논거 영향도까지 분석
        </label>
        <button type="submit">자동 분류 저장</button>
      </form>

      {error ? <div className="warning-box">{error}</div> : null}
      {result ? <CaptureResult result={result} /> : <CaptureGuide />}
    </section>
  );
}

function CaptureGuide() {
  return (
    <section className="dashboard-section">
      <div className="info-card">
        <span>처리 방식</span>
        <strong>자동 분류</strong>
        <p>종목 자료는 티커별 리서치 메모리에 저장하고, 전체 시황/섹터/정책/금리/수급 자료는 별도 범위로 분류합니다.</p>
      </div>
    </section>
  );
}

function CaptureResult({ result }) {
  const item = result.captured_item || {};
  const impact = result.linked_impact || null;
  const storagePath = result.storage?.path || result.storage?.relative_path || "";
  return (
    <div className="capture-result">
      <section className="dashboard-section">
        <h3>작업 결과</h3>
        <div className="dashboard-card-grid">
          <InfoMetric label="분류" value={classificationLabel(item.ticker)} text={item.ticker || "미확인"} />
          <InfoMetric label="제목" value={item.title || "제목 없음"} text={sourceLabel(item.source_type)} />
          <InfoMetric label="신뢰도" value={formatConfidence(item.confidence)} text="AI 프롬프트 가중치에 반영" />
          <InfoMetric label="논거 영향" value={impact?.overall_impact || "해당 없음"} text={impact?.summary || "종목 미확정 자료는 영향도 분석을 생략합니다."} />
        </div>
      </section>

      <section className="dashboard-section">
        <h3>요약</h3>
        <div className="report-item">
          <p>{item.summary || "요약 없음"}</p>
          <small>태그: {(item.tags || []).join(", ") || "없음"}</small>
          {storagePath ? <small>저장 데이터: {storagePath}</small> : null}
        </div>
      </section>

      {impact ? (
        <section className="dashboard-section two-column">
          <ListBlock title="영향도 근거" items={(impact.findings || []).map(formatFinding)} />
          <ListBlock title="다음 액션" items={impact.next_actions} />
        </section>
      ) : null}

      <section className="dashboard-section two-column">
        <PreviewBlock title="입력 내용" content={result.input_preview} />
        <PreviewBlock title="문서 추출 내용" content={result.document_preview} />
      </section>
    </div>
  );
}

function InfoMetric({ label, value, text }) {
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

function PreviewBlock({ title, content }) {
  return (
    <div className="preview-block">
      <h3>{title}</h3>
      <pre>{content || "표시할 내용이 없습니다."}</pre>
    </div>
  );
}

function classificationLabel(ticker) {
  const labels = {
    INBOX: "미분류 보관",
    MACRO: "거시경제 자료",
    SECTOR: "섹터 자료",
    MARKET: "시장 자료",
    POLICY: "정책 자료",
    RATES: "금리 자료",
    FLOWS: "수급 자료",
  };
  return labels[ticker] || "종목 자료";
}

function sourceLabel(sourceType) {
  const labels = {
    user_memo: "직접 메모",
    earnings: "실적 발표",
    macro: "거시경제",
    sector: "섹터/산업",
    market: "시장 동향",
    policy: "정책/규제",
    rates: "금리/채권",
    flows: "수급/자금 흐름",
  };
  return labels[sourceType] || sourceType || "출처 미확인";
}

function formatConfidence(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "미확인";
  }
  return `${Math.round(number * 100).toLocaleString("ko-KR")}%`;
}

function formatFinding(finding) {
  if (typeof finding === "string") {
    return finding;
  }
  const impact = finding.impact ? `[${finding.impact}] ` : "";
  return `${impact}${finding.summary || finding.evidence || finding.metric || JSON.stringify(finding)}`;
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
