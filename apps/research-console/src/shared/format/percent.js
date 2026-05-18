export function parsePercentInput(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  const raw = String(value).trim();
  const cleaned = raw.replace(/[,%\s]/g, "");
  if (!cleaned) {
    return null;
  }
  const parsed = Number(cleaned);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return raw.includes("%") ? parsed / 100 : parsed;
}

export function formatPercent(value, emptyValue = "") {
  const number = parsePercentInput(value);
  if (number === null) {
    return emptyValue;
  }
  return `${Math.round(number * 100).toLocaleString("ko-KR")}%`;
}

export function signedTone(value) {
  const number = parsePercentInput(value);
  if (number === null || number === 0) {
    return "neutral";
  }
  return number > 0 ? "positive" : "negative";
}
