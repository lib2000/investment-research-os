import assert from "node:assert/strict";
import { formatMoney } from "../../shared/format/money.js";
import { formatPercent } from "../../shared/format/percent.js";
import {
  normalizeHolding,
  normalizePortfolio,
  summarizeHoldings,
  validatePortfolioDraft,
} from "./portfolioModel.js";

const krHolding = normalizeHolding({
  ticker: "003230",
  name: "삼양식품",
  currency: "KRW",
  quantity: "18",
  current_price: "1,360,000원",
  average_cost: "85,000원",
});

assert.equal(krHolding.market_value, 24480000);
assert.equal(krHolding.cost_basis, 1530000);
assert.equal(krHolding.unrealized_gain, 22950000);
assert.equal(formatMoney(krHolding.market_value, "KRW"), "24,480,000원");
assert.equal(formatPercent(krHolding.unrealized_return), "1,500%");

const usHolding = normalizeHolding(
  {
    ticker: "PL",
    name: "Planet Labs PBC",
    currency: "USD",
    quantity: "217",
    current_price: "$39.04",
    average_cost: "$1.84",
  },
  { usdKrw: 1464 }
);

assert.equal(Math.round(usHolding.market_value), 12402540);
assert.equal(formatMoney(usHolding.current_price, "USD"), "$39.04");

const portfolio = normalizePortfolio({
  portfolio_name: "가족 합산",
  holdings: [usHolding, krHolding],
});

assert.equal(portfolio.holdings[0].ticker, "003230");
assert.equal(portfolio.summary.holding_count, 2);
assert.equal(summarizeHoldings(portfolio.holdings).total_market_value > 36000000, true);
assert.deepEqual(validatePortfolioDraft(portfolio), []);
assert.equal(validatePortfolioDraft({ portfolio_name: "", holdings: [] }).length, 2);

console.log("portfolioModel tests passed");
