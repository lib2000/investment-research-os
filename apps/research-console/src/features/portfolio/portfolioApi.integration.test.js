import assert from "node:assert/strict";
import { formatMoney, parseNumberInput } from "../../shared/format/money.js";
import { normalizePortfolio } from "./portfolioModel.js";

const API_BASE_URL = process.env.RESEARCH_OS_API_BASE_URL || "http://127.0.0.1:8001";
const ACCESS_TOKEN = process.env.RESEARCH_OS_TOKEN || "dev-local-token";
const EXPECTED_PORTFOLIOS = ["가족 합산", "김효경", "이지원", "이형주"];
const VALUE_TOLERANCE_KRW = 1;

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${ACCESS_TOKEN}`,
    },
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${JSON.stringify(payload)}`);
  }
  return payload;
}

const listPayload = await request("/api/v1/portfolios");
const portfolios = listPayload.portfolios || [];
const portfolioNames = portfolios.map((item) => item.portfolio_name);

for (const expectedName of EXPECTED_PORTFOLIOS) {
  assert.ok(
    portfolioNames.includes(expectedName),
    `저장 포트폴리오 목록에 '${expectedName}'이 없습니다. 현재: ${portfolioNames.join(", ")}`
  );
}

const lines = [];

for (const portfolio of portfolios.filter((item) => EXPECTED_PORTFOLIOS.includes(item.portfolio_name))) {
  const detailPayload = await request(`/api/v1/portfolios/${encodeURIComponent(portfolio.portfolio_name)}`);
  const detail = detailPayload.portfolio || detailPayload.active_portfolio || detailPayload;
  const normalized = normalizePortfolio(detail);
  const serverValue = parseNumberInput(detail.portfolio_value);
  const calculatedValue = normalized.summary.total_market_value;
  const diff = Math.abs((serverValue ?? 0) - calculatedValue);

  assert.equal(
    normalized.summary.holding_count,
    detail.holding_count || detail.holdings.length,
    `${detail.portfolio_name}: 보유 종목 수가 다릅니다.`
  );
  assert.ok(
    diff <= VALUE_TOLERANCE_KRW,
    `${detail.portfolio_name}: 서버 총액 ${formatMoney(serverValue, "KRW")} / React 계산 ${formatMoney(calculatedValue, "KRW")} / 차이 ${formatMoney(diff, "KRW")}`
  );

  lines.push(
    `${detail.portfolio_name}: ${normalized.summary.holding_count}개, ${formatMoney(calculatedValue, "KRW")} 검증 완료`
  );
}

console.log(["portfolio API integration tests passed", ...lines].join("\n"));
