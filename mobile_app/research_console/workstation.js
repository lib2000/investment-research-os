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

const SIDEBAR_KEY = "research-console-sidebar-collapsed";
const OUTPUT_KEY = "research-console-output-collapsed";
const OUTPUT_WIDTH_KEY = "research-console-output-width";

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
  if (typeof settingsDialog.showModal === "function") {
    settingsDialog.showModal();
  } else {
    settingsDialog.setAttribute("open", "");
  }
  window.requestAnimationFrame(() => document.querySelector("#apiBaseUrl")?.focus());
}

function closeSettings() {
  if (!settingsDialog) return;
  if (typeof settingsDialog.close === "function") {
    settingsDialog.close();
  } else {
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

navigation?.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    if (isCompactViewport()) setNavigationOpen(false);
  });
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

window.addEventListener("resize", () => {
  if (!isCompactViewport()) setNavigationOpen(false);
});
