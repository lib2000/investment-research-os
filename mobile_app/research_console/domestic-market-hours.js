const statusElement = document.querySelector("#domesticMarketStatus");
const detailElement = document.querySelector("#domesticMarketHours");
const apiInput = document.querySelector("#apiBaseUrl");
const statusButton = document.querySelector("#statusButton");

function apiBaseUrl() {
  return String(apiInput?.value || "http://127.0.0.1:8001").trim().replace(/\/$/, "");
}

function activeSessionText(payload) {
  const sessions = Array.isArray(payload?.current_trading_sessions)
    ? payload.current_trading_sessions
    : [];
  if (sessions.length) {
    return sessions.map((session) => session.label).join(" · ");
  }
  const accepting = Array.isArray(payload?.current_sessions) ? payload.current_sessions : [];
  if (accepting.length && payload?.market_state === "order_acceptance") {
    return accepting.map((session) => `${session.label} 호가접수`).join(" · ");
  }
  return payload?.market_state_label || "상태 확인 필요";
}

function scheduleText(payload) {
  if (!payload) {
    return "KRX·NXT 거래시간을 확인할 수 없습니다.";
  }
  const caveat = payload.holiday_status === "not_verified" ? "휴장일·종목별 제한은 별도 확인" : "";
  return `KRX 09:00–15:30 · 16:00–20:00 / NXT 08:00–08:50 · 09:00:30–15:20 · 15:40–20:00${caveat ? ` · ${caveat}` : ""}`;
}

async function refreshDomesticMarketHours() {
  if (!statusElement || !detailElement) {
    return;
  }
  statusElement.textContent = "확인 중";
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/market/domestic-hours`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    statusElement.textContent = activeSessionText(payload);
    detailElement.textContent = scheduleText(payload);
    detailElement.title = payload.operational_note || "";
  } catch (_error) {
    statusElement.textContent = "확인 실패";
    detailElement.textContent = "백엔드 연결 뒤 거래시간을 다시 확인하세요.";
  }
}

statusButton?.addEventListener("click", () => {
  void refreshDomesticMarketHours();
});
apiInput?.addEventListener("change", () => {
  void refreshDomesticMarketHours();
});

void refreshDomesticMarketHours();
window.setInterval(() => void refreshDomesticMarketHours(), 60_000);
