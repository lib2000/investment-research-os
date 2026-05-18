import { useEffect, useMemo, useState } from "react";

export function StoragePage({ researchApi, initialResearchKey = "PL", onOpenModule }) {
  const [researchKey, setResearchKey] = useState(initialResearchKey || "PL");
  const [searchText, setSearchText] = useState("");
  const [fileList, setFileList] = useState(null);
  const [manifest, setManifest] = useState(null);
  const [ragResult, setRagResult] = useState(null);
  const [backfillResult, setBackfillResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const filteredManifest = useMemo(() => {
    const entries = manifest?.entries ?? [];
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) return entries.slice(0, 40);
    return entries
      .filter((entry) => {
        const haystack = [
          entry.ticker,
          entry.research_key,
          entry.key,
          entry.file_name,
          entry.report_type,
          entry.summary,
          entry.relative_path,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(keyword);
      })
      .slice(0, 40);
  }, [manifest, searchText]);

  useEffect(() => {
    setResearchKey(String(initialResearchKey || "PL").trim().toUpperCase());
  }, [initialResearchKey]);

  async function loadFiles() {
    setStatus("loading-files");
    setError(null);
    setSelectedFile(null);
    try {
      const response = await researchApi.fetchResearchMemoryFiles(researchKey);
      setFileList(response);
      setStatus("files-loaded");
    } catch (fetchError) {
      setError(formatError(fetchError));
      setStatus("error");
    }
  }

  async function loadManifest() {
    setStatus("loading-manifest");
    setError(null);
    try {
      const response = await researchApi.fetchResearchManifest();
      setManifest(response);
      setStatus("manifest-loaded");
    } catch (fetchError) {
      setError(formatError(fetchError));
      setStatus("error");
    }
  }

  async function backfillRagIndex() {
    setStatus("backfilling-rag");
    setError(null);
    try {
      const response = await researchApi.backfillRagMemoryDocuments();
      setBackfillResult(response);
      setStatus("rag-backfilled");
    } catch (fetchError) {
      setError(formatError(fetchError));
      setStatus("error");
    }
  }

  async function searchRagIndex() {
    setStatus("searching-rag");
    setError(null);
    try {
      const response = await researchApi.searchRagMemoryDocuments({
        key: researchKey,
        query: searchText,
        limit: 8,
        includeLowQuality: true,
      });
      setRagResult(response);
      setStatus("rag-searched");
    } catch (fetchError) {
      setError(formatError(fetchError));
      setStatus("error");
    }
  }

  async function openFile(fileName) {
    setStatus("opening-file");
    setError(null);
    try {
      const response = await researchApi.fetchResearchMemoryFile({ key: researchKey, fileName });
      setSelectedFile(response);
      setStatus("file-opened");
    } catch (fetchError) {
      setError(formatError(fetchError));
      setStatus("error");
    }
  }

  const isBusy =
    status.startsWith("loading") || status === "opening-file" || status === "backfilling-rag" || status === "searching-rag";
  const canOpenTickerModule = isLikelyTicker(researchKey);

  return (
    <section className="panel storage-panel">
      <div className="panel-heading">
        <div>
          <h2>저장 데이터</h2>
          <p>자동 저장된 보고서, 캡처, 시장일지, 분석 결과를 같은 워크스페이스에서 다시 불러옵니다.</p>
        </div>
        <span className="status-pill">{statusLabel(status)}</span>
      </div>

      <div className="storage-controls">
        <label>
          조회 키
          <input
            value={researchKey}
            onChange={(event) => setResearchKey(event.target.value)}
            placeholder="예: PL, NVDA, MARKET-US"
            spellCheck="false"
          />
        </label>
        <label>
          매니페스트 검색
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="티커, 파일명, 요약 검색"
          />
        </label>
        <button type="button" disabled={isBusy || !researchKey.trim()} onClick={loadFiles}>
          저장 파일 조회
        </button>
        <button type="button" className="secondary-button" disabled={isBusy} onClick={loadManifest}>
          전체 목록 조회
        </button>
      </div>

      <div className="storage-rag-actions">
        <button type="button" disabled={isBusy} onClick={backfillRagIndex}>
          검색 인덱스 갱신
        </button>
        <button type="button" className="secondary-button" disabled={isBusy || !researchKey.trim()} onClick={searchRagIndex}>
          근거 검색
        </button>
        <p>
          저장된 리포트와 메모를 검색 인덱스에 반영한 뒤, 조회 키와 검색어로 후속 분석 근거를 찾습니다.
        </p>
      </div>

      <div className="storage-module-actions">
        <span>후속 분석 연결</span>
        <button type="button" className="secondary-button" disabled={!canOpenTickerModule} onClick={() => onOpenModule?.("dashboard", researchKey)}>
          대시보드로 이동
        </button>
        <button type="button" className="secondary-button" disabled={!canOpenTickerModule} onClick={() => onOpenModule?.("team", researchKey)}>
          팀리포트로 이동
        </button>
        <button type="button" className="secondary-button" disabled={!canOpenTickerModule} onClick={() => onOpenModule?.("trade", researchKey)}>
          매매전략으로 이동
        </button>
        <button type="button" className="secondary-button" disabled={!canOpenTickerModule} onClick={() => onOpenModule?.("earnings", researchKey)}>
          실적분석으로 이동
        </button>
        {!canOpenTickerModule ? <p>시장·섹터 키는 저장 데이터 검색에는 사용할 수 있지만 종목 분석 모듈 이동은 제한됩니다.</p> : null}
      </div>

      {error ? <div className="warning-box">오류: {error}</div> : null}

      <div className="storage-summary">
        <SummaryItem label="조회 키" value={fileList?.ticker ?? researchKey} />
        <SummaryItem label="저장 파일" value={`${fileList?.files?.length ?? 0}개`} />
        <SummaryItem label="검증 파일" value={`${fileList?.verified_file_count ?? 0}개`} />
        <SummaryItem label="전체 목록" value={`${manifest?.entries?.length ?? 0}개`} />
        <SummaryItem label="검색 결과" value={`${ragResult?.count ?? 0}개`} />
      </div>

      {backfillResult ? (
        <div className="storage-backfill">
          검색 인덱스 갱신 완료: <strong>{backfillResult.updated_count ?? 0}개</strong> 문서 반영 · 키{" "}
          <strong>{(backfillResult.tickers ?? []).length}개</strong>
        </div>
      ) : null}

      {ragResult ? (
        <div className="storage-column">
          <h3>근거 검색 결과</h3>
          <div className="storage-list rag-result-list">
            {(ragResult.documents ?? []).map((document) => (
              <article className="storage-file-card" key={document.document_id || document.relative_path}>
                <div>
                  <strong>{document.title || document.file_name || "제목 없음"}</strong>
                  <small>{document.relative_path || document.file_name || "경로 없음"}</small>
                </div>
                <p>{document.summary || document.content_excerpt || "요약 없음"}</p>
                <div className="storage-tags">
                  <span>{document.ticker || ragResult.key}</span>
                  <span>{translateReportType(document.report_type)}</span>
                  <span>품질 {document.quality_score ?? "-"}</span>
                  <span>{document.is_injectable ? "분석 주입 가능" : "참고용"}</span>
                  <span>신뢰도 {formatConfidence(document.confidence)}</span>
                </div>
              </article>
            ))}
            {!(ragResult.documents ?? []).length ? (
              <p className="muted-text">검색 가능한 근거가 없습니다. 먼저 검색 인덱스를 갱신해 보세요.</p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="storage-layout">
        <div className="storage-column">
          <h3>조회 키 저장 파일</h3>
          {(fileList?.data_warnings ?? []).length ? (
            <div className="warning-box">{fileList.data_warnings.join("\n")}</div>
          ) : null}
          <div className="storage-list">
            {(fileList?.files ?? []).map((file) => (
              <article className="storage-file-card" key={file.file_name}>
                <div>
                  <strong>{file.file_name}</strong>
                  <small>{file.relative_path}</small>
                </div>
                <p>{file.summary || "요약 없음"}</p>
                <div className="storage-tags">
                  <span>{translateReportType(file.report_type)}</span>
                  <span>{file.status_label || (file.verified ? "검증됨" : "레거시")}</span>
                  <span>{formatDate(file.modified_at)}</span>
                </div>
                <button type="button" onClick={() => openFile(file.file_name)} disabled={isBusy}>
                  열기
                </button>
              </article>
            ))}
            {fileList && !(fileList.files ?? []).length ? (
              <p className="muted-text">이 키로 저장된 파일이 없습니다.</p>
            ) : null}
          </div>
        </div>

        <div className="storage-column">
          <h3>전체 저장 목록</h3>
          <div className="storage-list">
            {filteredManifest.map((entry, index) => (
              <article className="storage-file-card compact" key={`${entry.relative_path ?? entry.file_name}-${index}`}>
                <div>
                  <strong>{entry.file_name || "이름 없음"}</strong>
                  <small>{entry.relative_path || entry.path || "경로 없음"}</small>
                </div>
                <p>{entry.summary || "요약 없음"}</p>
                <div className="storage-tags">
                  <span>{entry.ticker || entry.research_key || entry.key || "공통"}</span>
                  <span>{translateReportType(entry.report_type || entry.type)}</span>
                  <span>{formatDate(entry.created_at || entry.modified_at || entry.date)}</span>
                </div>
              </article>
            ))}
            {manifest && !filteredManifest.length ? <p className="muted-text">검색 결과가 없습니다.</p> : null}
          </div>
        </div>
      </div>

      {selectedFile ? (
        <div className="preview-block storage-preview">
          <h3>{selectedFile.file_name}</h3>
          <p>
            저장 경로: <strong>{selectedFile.relative_path}</strong>
          </p>
          <p>
            유형: <strong>{translateReportType(selectedFile.report_type)}</strong> · 상태:{" "}
            <strong>{selectedFile.status_label || (selectedFile.verified ? "검증됨" : "레거시")}</strong> · 수정:{" "}
            <strong>{formatDate(selectedFile.modified_at)}</strong>
          </p>
          <pre>{selectedFile.content}</pre>
        </div>
      ) : null}
    </section>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function statusLabel(status) {
  const labels = {
    idle: "대기",
    "loading-files": "파일 조회 중",
    "files-loaded": "파일 조회 완료",
    "loading-manifest": "전체 목록 조회 중",
    "manifest-loaded": "전체 목록 조회 완료",
    "opening-file": "파일 여는 중",
    "file-opened": "파일 열림",
    "backfilling-rag": "검색 인덱스 갱신 중",
    "rag-backfilled": "검색 인덱스 갱신 완료",
    "searching-rag": "근거 검색 중",
    "rag-searched": "근거 검색 완료",
    error: "오류",
  };
  return labels[status] ?? status;
}

function translateReportType(value) {
  const labels = {
    collaborative_team_report: "팀 리포트",
    research_capture: "정보 입력",
    thesis_impact_review: "논거 영향",
    portfolio_risk_scan: "리스크 스캔",
    earnings_reaction: "실적 분석",
    smart_trade_setup: "매매 전략",
    sector_opportunity: "섹터 발굴",
    long_term_compounder: "복리 성장주",
    market_close_review: "시장일지",
    checklist_readiness: "체크리스트",
  };
  return labels[value] ?? value ?? "미분류";
}

function formatDate(value) {
  if (!value) return "날짜 없음";
  return String(value).replace("T", " ").replace(/\.\d+/, "");
}

function formatConfidence(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return "-";
  return `${Math.round(numericValue * 100)}%`;
}

function isLikelyTicker(value) {
  return /^[A-Za-z0-9.]{1,10}$/.test(String(value || "").trim());
}

function formatError(error) {
  if (error?.message) return error.message;
  return String(error);
}
