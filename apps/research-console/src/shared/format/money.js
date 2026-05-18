export function parseNumberInput(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const cleaned = String(value)
    .replace(/[,\s]/g, "")
    .replace(/[₩원$%]/g, "")
    .trim();
  if (!cleaned) {
    return null;
  }
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumber(value, { maximumFractionDigits = 0 } = {}) {
  const number = parseNumberInput(value);
  if (number === null) {
    return "";
  }
  return number.toLocaleString("ko-KR", { maximumFractionDigits });
}

export function formatMoney(value, currency = "KRW", emptyValue = "") {
  const number = parseNumberInput(value);
  if (number === null) {
    return emptyValue;
  }
  const sign = number < 0 ? "-" : "";
  const absolute = Math.abs(number);
  if (String(currency).toUpperCase() === "USD") {
    return `${sign}$${absolute.toLocaleString("ko-KR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
  return `${sign}${Math.round(absolute).toLocaleString("ko-KR")}원`;
}

export function normalizeCurrency(value, fallbackTicker = "") {
  const normalized = String(value || "").trim().toUpperCase();
  if (normalized === "KRW" || normalized === "USD") {
    return normalized;
  }
  const ticker = String(fallbackTicker || "").trim().toUpperCase();
  if (/^\d{6}$/.test(ticker) || ticker.endsWith(".KS") || ticker.endsWith(".KQ")) {
    return "KRW";
  }
  return "USD";
}
