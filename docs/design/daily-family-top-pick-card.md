# Family Daily Top Pick Card

- Status: implemented design note
- Updated: 2026-08-31
- Owner: Investment Research OS

## Objective

Turn the existing daily review ranking into one evidence-first, shareable research snapshot for the current family-wide holdings and watchlist. It is a human-review artifact, not a trading signal or order workflow.

## User flow

1. The daily recommendation process stores Korean and US review candidates.
2. The top-pick process reuses that saved result, checks it against the current individual family portfolios and watchlist, and excludes candidates marked `blocks_buy_decision` when possible.
3. The console shows the selected candidate at the top of the dashboard and allows an SVG copy to be downloaded.
4. The in-process scheduler saves the daily recommendation at 07:00, then the independent 07:10 card gate reuses that saved result. A forced manual recommendation refresh may synchronize the local card immediately; it never sends a message or places an order.

## Selection contract

- Scope: all individual family holdings, deduplicated by ticker, plus all current watchlist tickers. The derived `가족 합산` view is never treated as an additional owner portfolio.
- Source: persisted daily recommendation records only; the card generator does not call prices, an LLM, broker APIs, Telegram, or order endpoints.
- Sort: eligible candidate score, evidence-quality score, evidence-document count, ticker. A candidate with `blocks_buy_decision` is excluded unless every scoped candidate is blocked; that fallback is rendered as a review-hold card rather than a promising pick.
- Missing price, financial metrics, or evidence are shown as `확인 필요`; no estimated values are placed on the card.

## Visual contract

- The console stays warm and neutral. The snapshot itself is a contained navy/teal evidence card inspired by the supplied earnings-card hierarchy, not a copy of its artwork or brand.
- The card is 1080×1350 SVG for clean sharing and contains four metrics, thesis, risks, evidence strength, next review, and the no-trade disclaimer.
- At narrow widths the interactive console card becomes one column, preserves phrase-level Korean wrapping, uses 44px action controls, and does not create horizontal overflow.

## Safety and verification

- No order, broker mutation, account data, Telegram delivery, or external model request is made.
- Every card includes the research-only disclaimer and the evidence guardrail.
- Unit tests cover scope filtering, evidence holds, persistence, and SVG escaping. Browser checks cover desktop and 390×844 rendering.
- Schedule checks cover the 07:00 recommendation gate and the once-per-day 07:10 card gate; the card does not issue a second market-data request.
