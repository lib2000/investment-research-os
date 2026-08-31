# Scheduled Validation Reliability

- Status: implemented
- Updated: 2026-08-31
- Scope: daily Research OS operations and the 08:45 strategy simulation task

## Objective

Keep scheduled research verification recoverable after a PC restart or a
transient local service failure, while preserving the boundary that all work is
research and simulation only.

## Decisions

1. The daily operations wrapper treats a child command's exit code as the
   completion contract. Its verification child uses the same rule, so
   non-fatal native stderr diagnostics are retained in task output but do not
   fail a successful regression suite.
2. The strategy task probes all three local services twice before calling the
   backtester, avoiding a request to a port that only briefly became ready.
3. A closed/reset local backtester connection is retried at most once after a
   short pause and a service-health check. HTTP failures and non-transport
   backtest failures are not retried.
4. Every retry and the final attempt count are written to the local task log;
   the research store receives only the final simulation result.
5. Boot Catch-up invokes the family aggregate audit through the project-owned
   Windows Python executable, not the task session's global PATH, and changes
   into the asserted project root before any relative-path tool runs.

## Safety and verification

- No retry invokes strategy execution, broker orders, account updates, or
  Telegram delivery.
- The task still requires the existing Docker and Lean image checks.
- Verification consists of contract tests, an isolated operations run, one
  local simulation backtest, and Scheduled Task state inspection.

## Non-goals

- This does not make a failed strategy profitable, replace the human review
  gate, or retry external market-data/business-rule errors indefinitely.
