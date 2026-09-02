const feedUrl = "./data/public-daily-research.json";
const publicationArchiveStart = "2026-09-01";

const elements = {
  headerStatus: document.querySelector("#headerStatus"),
  publicationNote: document.querySelector("#publicationNote"),
  latestTitle: document.querySelector("#latestTitle"),
  latestCard: document.querySelector("#latestCard"),
  methodGrid: document.querySelector("#methodGrid"),
  sourceLedger: document.querySelector("#sourceLedger"),
  archiveNote: document.querySelector("#archiveNote"),
  archiveList: document.querySelector("#archiveList"),
  footerDisclaimer: document.querySelector("#footerDisclaimer"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "날짜 확인 중";
  const parsed = new Date(`${value}T00:00:00+09:00`);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Asia/Seoul",
  }).format(parsed);
}

function formatTimestamp(value) {
  if (!value) return "생성 시각 확인 중";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Seoul",
  }).format(parsed);
}

function publicationStartDate(publication) {
  const value = String(publication?.archive_start_date || "");
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : publicationArchiveStart;
}

function isPublicIssue(value, startDate) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || "")) && String(value) >= startDate;
}

function stateLabel(state) {
  const labels = {
    published: { label: "오늘 발행", className: "published" },
    awaiting_daily_refresh: { label: "오늘 리서치 준비 중", className: "pending" },
    awaiting_first_issue: { label: "첫 공개 발행 준비 중", className: "pending" },
    review_hold: { label: "근거 보강 중", className: "hold" },
    unavailable: { label: "발행 준비 중", className: "hold" },
  };
  return labels[state] || labels.unavailable;
}

function renderUnavailable(publication, state) {
  elements.latestCard.innerHTML = `
    <section class="research-state" aria-label="발행 대기 상태">
      <div>
        <strong>${escapeHtml(state.label)}</strong>
        <p>${escapeHtml(publication?.message || "공개 리서치 카드 준비 중.")}</p>
      </div>
    </section>
  `;
}

function renderLatest(feed) {
  const publication = feed.publication || {};
  const startDate = publicationStartDate(publication);
  const rawCard = feed.latest;
  const card = rawCard && isPublicIssue(rawCard.report_date, startDate) ? rawCard : null;
  const stateKey = rawCard && !card ? "awaiting_first_issue" : publication.state;
  const state = stateLabel(stateKey);
  const firstIssueMessage = `공개 발행 이력은 ${formatDate(startDate)}부터. 첫 리서치 준비 중.`;

  elements.headerStatus.textContent = state.label;
  elements.publicationNote.textContent = stateKey === "awaiting_first_issue" ? firstIssueMessage : publication.message || "";
  elements.latestTitle.textContent = stateKey === "awaiting_first_issue" ? "첫 공개 리서치" : "오늘의 공개 리서치";

  if (!card) {
    renderUnavailable(
      { ...publication, message: stateKey === "awaiting_first_issue" ? firstIssueMessage : publication.message },
      state,
    );
    return;
  }

  const metrics = Array.isArray(card.metrics) ? card.metrics : [];
  const reasons = Array.isArray(card.reasons) ? card.reasons : [];
  const risks = Array.isArray(card.risks) ? card.risks : [];
  const sourceTypes = Array.isArray(card.evidence?.source_types) ? card.evidence.source_types : [];
  const sourceLedger = Array.isArray(card.evidence?.source_ledger) && card.evidence.source_ledger.length
    ? card.evidence.source_ledger
    : sourceTypes.map((sourceType, index) => ({
        sequence: String(index + 1).padStart(2, "0"),
        source_type: sourceType,
        purpose: "공개 자료 대조",
        publication_basis: "공개 자료 기준",
        role: "검증 근거",
      }));
  const researchSignals = Array.isArray(card.research_signals) ? card.research_signals : [];
  const referencePrice = card.reference_price || {};
  const issueDate = formatDate(card.report_date);
  const publishedAt = formatTimestamp(card.published_at);

  elements.latestCard.innerHTML = `
    <article class="featured-card" aria-label="${escapeHtml(card.company_name)} 공개 리서치 카드">
      <header class="card-utility-bar">
        <span>X10THINK DAILY RESEARCH · PUBLIC EVIDENCE DOSSIER</span>
        <span>${escapeHtml(issueDate)} · ${escapeHtml(card.edition_label || state.label)}</span>
      </header>
      <div class="card-main">
        <section class="card-identity">
          <div class="issue-kicker">
            <span class="issue-state ${escapeHtml(state.className)}">${escapeHtml(card.edition_label || state.label)}</span>
            <span>${escapeHtml(card.market || "시장 확인 중")}</span>
          </div>
          <div class="company-line">
            <h3>${escapeHtml(card.company_name)}</h3>
            <span class="ticker">${escapeHtml(card.ticker)}</span>
          </div>
          <p class="stance">${escapeHtml(card.stance || "근거 우선 검토")}</p>
          <p class="identity-meta">발행 시각 ${escapeHtml(publishedAt)}</p>
        </section>
        <section class="thesis-panel" aria-label="리서치 핵심 테마">
          <span>RESEARCH THESIS</span>
          <p>${escapeHtml(card.headline)}</p>
          <div class="reference-price">
            <span>REFERENCE PRICE</span>
            <strong>${escapeHtml(referencePrice.value || "확인 필요")}</strong>
            <small>${escapeHtml(referencePrice.detail || "리서치 기준 정보")}</small>
          </div>
        </section>
        <aside class="evidence-grade-panel" aria-label="근거 품질">
          <span>EVIDENCE GRADE</span>
          <strong>${escapeHtml(card.evidence?.grade || "검토")}</strong>
          <p>문서 ${escapeHtml(card.evidence?.document_count ?? 0)}건 · 최근 30일 ${escapeHtml(card.evidence?.recent_30d_count ?? 0)}건</p>
          <small>${escapeHtml(card.evidence?.review_gate || "핵심 원문 재확인 뒤 검토")}</small>
        </aside>
        <section class="metric-grid" aria-label="핵심 리서치 지표">
          ${metrics
            .map(
              (metric, index) => `
                <div class="metric">
                  <span>${String(index + 1).padStart(2, "0")} · ${escapeHtml(metric.label)}</span>
                  <strong>${escapeHtml(metric.value)}</strong>
                  <small>${escapeHtml(metric.detail)}</small>
                </div>
              `,
            )
            .join("")}
        </section>
        <section class="detail-columns" aria-label="핵심 논거와 리스크">
          <section class="detail-block">
            <span>WHAT MATTERS</span>
            <h4>핵심 논거</h4>
            <ul>${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
          </section>
          <section class="detail-block risk">
            <span>RISK CHECK</span>
            <h4>리스크</h4>
            <ul>${risks.map((risk) => `<li>${escapeHtml(risk)}</li>`).join("")}</ul>
          </section>
        </section>
        <section class="signal-rail" aria-label="검토 기준">
          <header>
            <span>RESEARCH CHECKPOINTS</span>
            <strong>검토 기준</strong>
          </header>
          <div class="signal-list">
            ${researchSignals
              .map(
                (signal) => `
                  <div class="signal-item">
                    <span>${escapeHtml(signal.label)}</span>
                    <strong>${escapeHtml(signal.value)}</strong>
                    <small>${escapeHtml(signal.detail)}</small>
                  </div>
                `,
              )
              .join("")}
          </div>
        </section>
        <section class="evidence-ledger" aria-label="근거 및 출처 장부">
          <header>
            <div>
              <span>EVIDENCE LEDGER</span>
              <h4>근거 및 출처 장부</h4>
            </div>
            <p>원문 제목·URL·비공개 메모는 공개하지 않습니다.</p>
          </header>
          <div class="ledger-table" role="table" aria-label="공개 근거 범주와 역할">
            <div class="ledger-row ledger-head" role="row">
              <span role="columnheader">구분</span>
              <span role="columnheader">출처 범주</span>
              <span role="columnheader">확인 목적</span>
              <span role="columnheader">발행 기준</span>
              <span role="columnheader">근거 역할</span>
            </div>
            ${sourceLedger
              .map(
                (entry) => `
                  <div class="ledger-row" role="row">
                    <span role="cell" data-label="구분">${escapeHtml(entry.sequence)}</span>
                    <span role="cell" data-label="출처 범주">${escapeHtml(entry.source_type)}</span>
                    <span role="cell" data-label="확인 목적">${escapeHtml(entry.purpose)}</span>
                    <span role="cell" data-label="발행 기준">${escapeHtml(entry.publication_basis)}</span>
                    <span role="cell" data-label="근거 역할">${escapeHtml(entry.role)}</span>
                  </div>
                `,
              )
              .join("")}
          </div>
        </section>
      </div>
      <footer class="card-disclaimer">${escapeHtml(card.disclaimer || feed.disclaimer || "")}</footer>
    </article>
  `;
}

function renderMethod(feed) {
  const methodology = feed.methodology || {};
  const steps = Array.isArray(methodology.steps) ? methodology.steps : [];
  if (steps.length === 3) {
    const headings = ["원문 수집", "근거 품질 점검", "리스크와 다음 일정"];
    elements.methodGrid.innerHTML = steps
      .map(
        (step, index) => `
          <article>
            <span>0${index + 1}</span>
            <h3>${escapeHtml(headings[index])}</h3>
            <p>${escapeHtml(step)}</p>
          </article>
        `,
      )
      .join("");
  }

  const freshness = feed.data_freshness || {};
  const sourceCategories = Array.isArray(freshness.source_categories) ? freshness.source_categories : [];
  elements.sourceLedger.innerHTML = `
    <p>
      <strong>${escapeHtml(freshness.source_refresh_status || "점검 이력 준비 중")}</strong><br />
      ${escapeHtml(formatTimestamp(freshness.evidence_refreshed_at))}
    </p>
    <ul>${sourceCategories.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
  `;
}

function renderArchive(feed) {
  const startDate = publicationStartDate(feed.publication);
  const archive = (Array.isArray(feed.archive) ? feed.archive : []).filter((item) =>
    isPublicIssue(item?.report_date, startDate),
  );
  elements.archiveNote.textContent = `공개 발행 이력: ${formatDate(startDate)} 시작`;
  if (!archive.length) {
    elements.archiveList.innerHTML = `<p class="archive-empty">첫 공개 리서치 발행 뒤 이력 표시.</p>`;
    return;
  }
  elements.archiveList.innerHTML = archive
    .map(
      (item) => `
        <article class="archive-row">
          <span class="archive-date">${escapeHtml(formatDate(item.report_date))}</span>
          <div class="archive-name">
            <strong>${escapeHtml(item.company_name)}</strong>
            <span>${escapeHtml(item.ticker)}</span>
          </div>
          <span class="archive-meta">${escapeHtml(item.market)}</span>
          <span class="archive-grade">근거 ${escapeHtml(item.evidence_grade)}</span>
        </article>
      `,
    )
    .join("");
}

function renderFeed(feed) {
  const siteName = feed.site?.name || "X10THINK Daily Research";
  document.title = siteName;
  renderLatest(feed);
  renderMethod(feed);
  renderArchive(feed);
  elements.footerDisclaimer.textContent = feed.disclaimer || elements.footerDisclaimer.textContent;
}

function renderLoadError() {
  elements.headerStatus.textContent = "발행 데이터 준비 중";
  elements.publicationNote.textContent = "공개 발행 데이터 준비 중";
  elements.latestCard.innerHTML = `
    <section class="research-state error" aria-label="발행 데이터 준비 상태">
      <div>
        <strong>발행 데이터 준비 중</strong>
        <p>검토 완료 뒤 이곳에 공개.</p>
      </div>
    </section>
  `;
  elements.archiveList.innerHTML = `<p class="archive-empty">첫 공개 리서치 발행 뒤 이력 표시.</p>`;
  elements.sourceLedger.innerHTML = `<p>근거 자료 점검 이력 준비 중.</p>`;
}

async function loadFeed() {
  try {
    const response = await fetch(feedUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`feed request failed: ${response.status}`);
    const feed = await response.json();
    if (!feed || typeof feed !== "object") throw new Error("invalid feed payload");
    renderFeed(feed);
  } catch (error) {
    console.warn("Public Daily Research feed is unavailable.", error);
    renderLoadError();
  }
}

loadFeed();
