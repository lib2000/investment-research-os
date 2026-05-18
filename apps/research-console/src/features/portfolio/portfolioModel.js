import { normalizeCurrency, parseNumberInput } from "../../shared/format/money.js";
import { parsePercentInput } from "../../shared/format/percent.js";

export function normalizeHolding(holding = {}, { usdKrw = null } = {}) {
  const ticker = normalizeText(holding.ticker).toUpperCase();
  const currency = normalizeCurrency(holding.currency, ticker);
  const quantity = parseNumberInput(holding.quantity) ?? 0;
  const currentPrice = parseNumberInput(holding.current_price ?? holding.currentPrice);
  const averageCost = parseNumberInput(holding.average_cost ?? holding.averageCost);
  const explicitMarketValue = parseNumberInput(holding.market_value ?? holding.marketValue);
  const explicitCostBasis = parseNumberInput(holding.cost_basis ?? holding.costBasis);
  const fxRate = currency === "USD" ? parseNumberInput(usdKrw) : 1;
  const marketValue =
    explicitMarketValue ??
    (currentPrice !== null && quantity && fxRate ? currentPrice * quantity * fxRate : null);
  const costBasis =
    explicitCostBasis ??
    (averageCost !== null && quantity && fxRate ? averageCost * quantity * fxRate : null);
  const unrealizedGain =
    parseNumberInput(holding.unrealized_gain ?? holding.unrealizedGain) ??
    (marketValue !== null && costBasis !== null ? marketValue - costBasis : null);
  const unrealizedReturn =
    parsePercentInput(holding.unrealized_return ?? holding.unrealizedReturn) ??
    (unrealizedGain !== null && costBasis ? unrealizedGain / costBasis : null);

  return {
    ...holding,
    ticker,
    name: normalizeText(holding.name),
    sector: normalizeText(holding.sector),
    currency,
    quantity,
    current_price: currentPrice,
    average_cost: averageCost,
    market_value: marketValue,
    cost_basis: costBasis,
    unrealized_gain: unrealizedGain,
    unrealized_return: unrealizedReturn,
    theme_tags: normalizeTags(holding.theme_tags),
  };
}

export function normalizePortfolio(portfolio = {}, options = {}) {
  const holdings = (portfolio.holdings || [])
    .map((holding) => normalizeHolding(holding, options))
    .filter((holding) => holding.ticker || holding.name);
  const sortedHoldings = sortHoldings(holdings, portfolio.sortBy || "market_value_desc");
  const summary = summarizeHoldings(sortedHoldings);
  return {
    ...portfolio,
    portfolio_name: portfolio.portfolio_name || portfolio.portfolioName || "내 포트폴리오",
    holdings: sortedHoldings,
    summary,
  };
}

export function summarizeHoldings(holdings = []) {
  const totalMarketValue = sumBy(holdings, "market_value");
  const totalCostBasis = sumBy(holdings, "cost_basis");
  const totalGain =
    holdings.some((holding) => holding.unrealized_gain !== null && holding.unrealized_gain !== undefined)
      ? sumBy(holdings, "unrealized_gain")
      : totalMarketValue - totalCostBasis;
  const totalReturn = totalCostBasis ? totalGain / totalCostBasis : null;
  return {
    total_market_value: totalMarketValue,
    total_cost_basis: totalCostBasis,
    total_gain: totalGain,
    total_return: totalReturn,
    holding_count: holdings.length,
  };
}

export function sortHoldings(holdings = [], sortBy = "market_value_desc") {
  const copy = [...holdings];
  if (sortBy === "name_asc") {
    return copy.sort((a, b) => compareText(a.name || a.ticker, b.name || b.ticker));
  }
  if (sortBy === "ticker_asc") {
    return copy.sort((a, b) => compareText(a.ticker, b.ticker));
  }
  if (sortBy === "gain_desc") {
    return copy.sort((a, b) => compareNumber(b.unrealized_gain, a.unrealized_gain));
  }
  if (sortBy === "return_desc") {
    return copy.sort((a, b) => compareNumber(b.unrealized_return, a.unrealized_return));
  }
  return copy.sort((a, b) => compareNumber(b.market_value, a.market_value));
}

export function validatePortfolioDraft(portfolio = {}) {
  const errors = [];
  const holdings = portfolio.holdings || [];
  if (!normalizeText(portfolio.portfolio_name || portfolio.portfolioName)) {
    errors.push("포트폴리오 이름을 입력하세요.");
  }
  if (!holdings.length) {
    errors.push("보유 종목을 1개 이상 입력하세요.");
  }
  holdings.forEach((holding, index) => {
    const label = `${index + 1}번째 보유 종목`;
    if (!normalizeText(holding.ticker) && !normalizeText(holding.name)) {
      errors.push(`${label}: 회사명 또는 티커가 필요합니다.`);
    }
    if ((parseNumberInput(holding.quantity) ?? 0) <= 0) {
      errors.push(`${label}: 수량은 0보다 커야 합니다.`);
    }
  });
  return errors;
}

function sumBy(items, key) {
  return items.reduce((sum, item) => sum + (parseNumberInput(item[key]) ?? 0), 0);
}

function compareNumber(a, b) {
  return (parseNumberInput(a) ?? -Infinity) - (parseNumberInput(b) ?? -Infinity);
}

function compareText(a, b) {
  return normalizeText(a).localeCompare(normalizeText(b), "ko-KR");
}

function normalizeText(value) {
  return String(value || "").trim();
}

function normalizeTags(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeText).filter(Boolean);
  }
  return String(value || "")
    .split(",")
    .map(normalizeText)
    .filter(Boolean);
}
