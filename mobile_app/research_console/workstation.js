const shell = document.querySelector(".workstation-shell");
const navigation = document.querySelector("#workspaceNavigation");
const navigationToggle = document.querySelector("#navigationToggle");
const navigationCollapse = document.querySelector("#navigationCollapse");
const outputPane = document.querySelector("#workspaceOutput");
const outputToggle = document.querySelector("#outputPaneToggle");
const outputClose = document.querySelector("#outputPaneClose");
const outputResizeHandle = document.querySelector("#outputResizeHandle");
const settingsDialog = document.querySelector("#settingsDialog");
const settingsOpenButton = document.querySelector("#settingsOpenButton");
const settingsCloseButton = document.querySelector("#settingsCloseButton");
const statusRefreshCompact = document.querySelector("#statusRefreshCompact");
const globalTickerInput = document.querySelector("#globalTickerInput");
const workspaceSectionLabel = document.querySelector("#workspaceSectionLabel");
const workspaceModuleTitle = document.querySelector("#workspaceModuleTitle");
const workspaceModuleDescription = document.querySelector("#workspaceModuleDescription");
const workspaceTickerContext = document.querySelector("#workspaceTickerContext");
const workspaceTickerFocus = document.querySelector("#workspaceTickerFocus");

const SIDEBAR_KEY = "research-console-sidebar-collapsed";
const OUTPUT_KEY = "research-console-output-collapsed";
const OUTPUT_WIDTH_KEY = "research-console-output-width";

const MODULE_META = {
  dashboard: ["오늘", "대시보드", "보유·관심종목과 오늘 실행할 리서치 흐름을 한곳에서 확인합니다."],
  team: ["오늘", "팀 리포트", "사업·재무·밸류에이션·위험 근거를 결합한 종목 리포트를 생성합니다."],
  news: ["오늘", "뉴스", "수집한 뉴스의 중복과 근거 품질을 확인하고 투자 논거로 연결합니다."],
  marketClose: ["오늘", "시장 일지", "장 종료 후 시장 요약과 관찰 근거를 저장하고 다음 세션에 연결합니다."],
  investmentCalendar: ["오늘", "투자 캘린더", "실적·공시·리밸런싱 일정을 확인하고 누락된 후속 점검을 찾습니다."],
  trade: ["분석", "매매 전략", "현재가·위험 한도·포트폴리오 맥락으로 연구용 진입·손절·목표 구간을 계산합니다."],
  chart: ["분석", "차트 분석", "가격·거래량과 여섯 개 보조지표를 계산해 기술적 상태를 기록합니다."],
  earnings: ["분석", "실적 분석", "발표 실적과 시장 반응을 비교해 기존 투자 논거의 변화를 점검합니다."],
  insider: ["분석", "내부자 거래", "미국 Form 4와 한국 공시를 동일한 여섯 축으로 정규화해 비교합니다."],
  dartAnnualLab: ["분석", "사업보고서 랩", "DART 사업보고서의 지배구조·사업 내용·변화 신호를 근거 중심으로 분석합니다."],
  macro: ["분석", "매크로 분석", "금리·물가·환율·정책 흐름을 종목과 포트폴리오 위험에 연결합니다."],
  sector: ["분석", "섹터 발굴", "산업 수요·정책·수급과 기업별 수혜 강도를 비교합니다."],
  compounder: ["분석", "복리 성장주", "성장성·현금흐름·경쟁 우위 기준으로 장기 후보를 선별합니다."],
  portfolio: ["자산", "포트폴리오", "가족별 보유자산과 계좌 연결 상태, 수익·위험·리밸런싱 괴리를 확인합니다."],
  interests: ["자산", "관심종목/섹터", "한국·미국 관심종목과 섹터의 우선순위·메모·자동 수집 상태를 관리합니다."],
  checklist: ["자산", "체크리스트", "투자 전 필수 근거와 누락 데이터를 항목별로 검토합니다."],
  capture: ["운영", "정보 입력", "뉴스·보고서·메모를 자동 분류해 종목과 리서치 저장소에 연결합니다."],
  llmBridge: ["운영", "LLM 연동", "외부 LLM용 프롬프트를 만들고 검토한 응답만 연구 기록으로 저장합니다."],
  reportAutomation: ["운영", "보고 자동화", "정기 보고서의 생성·검증·전달 준비 상태를 확인합니다."],
  memory: ["운영", "저장 데이터", "RAG 문서와 근거 원문을 검색하고 품질·중복·연결 상태를 점검합니다."],
};

function activeModuleName() {
  return navigation?.querySelector(".tab.active")?.dataset.tab || "dashboard";
}

function updateWorkspaceContext() {
  const [section, title, description] = MODULE_META[activeModuleName()] || MODULE_META.dashboard;
  if (workspaceSectionLabel) workspaceSectionLabel.textContent = section;
  if (workspaceModuleTitle) workspaceModuleTitle.textContent = title;
  if (workspaceModuleDescription) workspaceModuleDescription.textContent = description;
  if (workspaceTickerContext) {
    const ticker = String(globalTickerInput?.value || "").trim();
    workspaceTickerContext.textContent = ticker ? `현재 종목 · ${ticker}` : "종목 미선택";
    workspaceTickerContext.classList.toggle("is-empty", !ticker);
  }
}

function readPreference(key, fallback = "") {
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function writePreference(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Private browsing can disable storage. The workstation still works in-memory.
  }
}

function isCompactViewport() {
  return window.matchMedia("(max-width: 759px)").matches;
}

function setNavigationOpen(open) {
  shell?.classList.toggle("navigation-open", open);
  navigationToggle?.setAttribute("aria-expanded", String(open));
  navigationToggle?.setAttribute("aria-label", open ? "탐색 메뉴 닫기" : "탐색 메뉴 열기");
}

function setSidebarCollapsed(collapsed, { persist = true } = {}) {
  shell?.classList.toggle("sidebar-collapsed", collapsed);
  navigationCollapse?.setAttribute("aria-label", collapsed ? "사이드바 펼치기" : "사이드바 접기");
  if (navigationCollapse) {
    navigationCollapse.firstChild.textContent = collapsed ? "› " : "‹ ";
  }
  if (persist) {
    writePreference(SIDEBAR_KEY, collapsed ? "true" : "false");
  }
}

function setOutputCollapsed(collapsed, { persist = true } = {}) {
  shell?.classList.toggle("output-collapsed", collapsed);
  outputToggle?.setAttribute("aria-expanded", String(!collapsed));
  outputToggle?.setAttribute("aria-label", collapsed ? "결과 패널 펼치기" : "결과 패널 접기");
  if (persist) {
    writePreference(OUTPUT_KEY, collapsed ? "true" : "false");
  }
}

function openSettings() {
  if (!settingsDialog) return;
  if (!settingsDialog.open) {
    try {
      if (typeof settingsDialog.showModal === "function") {
        settingsDialog.showModal();
      } else {
        settingsDialog.setAttribute("open", "");
      }
    } catch {
      settingsDialog.setAttribute("open", "");
    }
  }
  window.requestAnimationFrame(() => document.querySelector("#apiBaseUrl")?.focus());
}

function closeSettings() {
  if (!settingsDialog) return;
  if (!settingsDialog.open) return;
  try {
    if (typeof settingsDialog.close === "function") {
      settingsDialog.close();
    } else {
      settingsDialog.removeAttribute("open");
    }
  } catch {
    settingsDialog.removeAttribute("open");
  }
  settingsOpenButton?.focus();
}

function statusTone(text) {
  const value = String(text || "").trim().toLowerCase();
  if (!value || /대기|확인 중|불러오는 중/.test(value)) return "pending";
  if (/오류|실패|중단|연결 안|unavailable|error|failed/.test(value)) return "error";
  if (/주의|경고|필요|미설정|지연|부분|stale|degraded/.test(value)) return "warning";
  return "ok";
}

function updateStatusTone(statusElement) {
  const item = statusElement?.closest("div, button");
  if (!item) return;
  item.dataset.tone = statusTone(statusElement.textContent);
}

document.querySelectorAll(".workstation-statusbar strong").forEach((statusElement) => {
  updateStatusTone(statusElement);
  new MutationObserver(() => updateStatusTone(statusElement)).observe(statusElement, {
    childList: true,
    characterData: true,
    subtree: true,
  });
});

navigationToggle?.addEventListener("click", () => {
  setNavigationOpen(!shell?.classList.contains("navigation-open"));
});

navigationCollapse?.addEventListener("click", () => {
  if (isCompactViewport()) {
    setNavigationOpen(false);
    return;
  }
  setSidebarCollapsed(!shell?.classList.contains("sidebar-collapsed"));
});

function activateWorkspacePanel(button) {
  const tabName = button?.dataset.tab;
  if (!tabName) return false;
  const panel = document.getElementById(tabName);
  if (!panel) return false;
  document.querySelectorAll(".tab[data-tab]").forEach((item) => {
    const active = item === button;
    item.classList.toggle("active", active);
    item.setAttribute("aria-current", active ? "page" : "false");
  });
  document.querySelectorAll(".panel").forEach((item) => {
    item.classList.toggle("active", item === panel);
  });
  updateWorkspaceContext();
  return true;
}

navigation?.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    activateWorkspacePanel(button);
    if (isCompactViewport()) setNavigationOpen(false);
    window.requestAnimationFrame(updateWorkspaceContext);
  });
});

if (navigation) {
  new MutationObserver(updateWorkspaceContext).observe(navigation, {
    attributes: true,
    attributeFilter: ["class"],
    subtree: true,
  });
}

globalTickerInput?.addEventListener("input", updateWorkspaceContext);
globalTickerInput?.addEventListener("change", updateWorkspaceContext);
workspaceTickerFocus?.addEventListener("click", () => {
  globalTickerInput?.focus();
  globalTickerInput?.select();
});

document.addEventListener("pointerdown", (event) => {
  if (!isCompactViewport() || !shell?.classList.contains("navigation-open")) return;
  if (navigation?.contains(event.target) || navigationToggle?.contains(event.target)) return;
  setNavigationOpen(false);
});

outputToggle?.addEventListener("click", () => {
  setOutputCollapsed(!shell?.classList.contains("output-collapsed"));
});
outputClose?.addEventListener("click", () => setOutputCollapsed(true));

settingsOpenButton?.addEventListener("click", openSettings);
document.querySelectorAll("[data-open-settings]").forEach((button) => {
  button.addEventListener("click", openSettings);
});
settingsCloseButton?.addEventListener("click", (event) => {
  event.preventDefault();
  closeSettings();
});
settingsDialog?.addEventListener("click", (event) => {
  if (event.target === settingsDialog) closeSettings();
});

statusRefreshCompact?.addEventListener("click", () => {
  document.querySelector("#statusButton")?.click();
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    globalTickerInput?.focus();
    globalTickerInput?.select();
  }
  if (event.key === "Escape" && shell?.classList.contains("navigation-open")) {
    setNavigationOpen(false);
  }
});

function setOutputWidth(width) {
  const clamped = Math.max(320, Math.min(720, Math.round(width)));
  shell?.style.setProperty("--output-pane-width", `${clamped}px`);
  outputResizeHandle?.setAttribute("aria-valuenow", String(clamped));
  writePreference(OUTPUT_WIDTH_KEY, String(clamped));
}

outputResizeHandle?.addEventListener("pointerdown", (event) => {
  if (window.matchMedia("(max-width: 1179px)").matches) return;
  event.preventDefault();
  outputResizeHandle.setPointerCapture(event.pointerId);
  document.body.classList.add("is-resizing-pane");
  const startX = event.clientX;
  const startWidth = outputPane?.getBoundingClientRect().width || 420;
  const move = (moveEvent) => setOutputWidth(startWidth + startX - moveEvent.clientX);
  const stop = () => {
    document.body.classList.remove("is-resizing-pane");
    outputResizeHandle.removeEventListener("pointermove", move);
    outputResizeHandle.removeEventListener("pointerup", stop);
    outputResizeHandle.removeEventListener("pointercancel", stop);
  };
  outputResizeHandle.addEventListener("pointermove", move);
  outputResizeHandle.addEventListener("pointerup", stop);
  outputResizeHandle.addEventListener("pointercancel", stop);
});

outputResizeHandle?.addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
  event.preventDefault();
  const current = outputPane?.getBoundingClientRect().width || 420;
  setOutputWidth(current + (event.key === "ArrowLeft" ? 24 : -24));
});

const savedWidth = Number(readPreference(OUTPUT_WIDTH_KEY, "420"));
if (Number.isFinite(savedWidth)) setOutputWidth(savedWidth);
setSidebarCollapsed(readPreference(SIDEBAR_KEY) === "true", { persist: false });
setOutputCollapsed(readPreference(OUTPUT_KEY) === "true", { persist: false });
updateWorkspaceContext();

window.addEventListener("resize", () => {
  if (!isCompactViewport()) setNavigationOpen(false);
});
