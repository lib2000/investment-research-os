"""Headless menu smoke test for the research console.

This check verifies that every top-level menu opens, visible controls render,
and the safe dashboard shortcut buttons do not raise client-side/runtime errors.
It avoids destructive actions by default.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from smoke_research_console_clicks import CdpClient, assert_project_root, chrome_path, wait_for_page


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=menus"


def run_menu_smoke(url: str, include_write_actions: bool = False) -> dict:
    assert_project_root()
    port = 9224
    with tempfile.TemporaryDirectory(prefix="research-console-menu-chrome-", ignore_cleanup_errors=True) as profile_dir:
        process = subprocess.Popen(
            [
                chrome_path(),
                "--headless=new",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile_dir}",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        client: CdpClient | None = None
        try:
            page = wait_for_page(port)
            client = CdpClient(page["webSocketDebuggerUrl"])
            client.call("Runtime.enable")
            client.call("Page.enable")
            result = client.evaluate(
                f"""
                (async () => {{
                  const includeWriteActions = {str(include_write_actions).lower()};
                  const runtimeErrors = [];
                  window.addEventListener("error", (event) => runtimeErrors.push(event.message || String(event.error || "runtime error")));
                  window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(event.reason?.message || String(event.reason || "unhandled rejection")));
                  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                  const visible = (el) => Boolean(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
                  const hardErrorPattern = /is not defined|Failed to fetch|HTTP error|Cannot read|ReferenceError|TypeError/i;
                  const waitFor = async (predicate, timeout = 30000, label = "condition") => {{
                    const started = Date.now();
                    while (Date.now() - started < timeout) {{
                      const value = predicate();
                      if (value) return value;
                      await sleep(250);
                    }}
                    throw new Error(`Timed out waiting for ${{label}}`);
                  }};
                  const activeTabKey = () => [...document.querySelectorAll("button.tab.active")]
                    .map((item) => item.dataset.tab || item.textContent.trim())[0] || "";
                  const activePanelKey = () => [...document.querySelectorAll(".panel.active, section.active, .tab-panel.active")]
                    .map((item) => item.id).filter(Boolean)[0] || "";
                  const dashboardCommandLayout = () => [...document.querySelectorAll(".dashboard-command-bar button")]
                    .filter(visible)
                    .map((button) => ({{
                      label: button.textContent.trim(),
                      width: button.clientWidth,
                      scrollWidth: button.scrollWidth,
                      height: button.clientHeight,
                      scrollHeight: button.scrollHeight,
                      clipped: button.scrollWidth > button.clientWidth || button.scrollHeight > button.clientHeight,
                    }}));
                  const outputText = () => document.querySelector("#output")?.innerText || "";
                  const outputStatus = () => document.querySelector("#outputStatus")?.textContent || "";
                  const actionFeedbackText = () => document.querySelector("#actionFeedback")?.textContent || "";
                  const panelSummary = (panel) => {{
                    const visibleButtons = panel
                      ? [...panel.querySelectorAll("button")].filter(visible).map((button) => (button.textContent || button.id || "").trim()).filter(Boolean).slice(0, 14)
                      : [];
                    const visibleInputs = panel ? [...panel.querySelectorAll("input, textarea, select")].filter(visible).length : 0;
                    return {{
                      visibleButtons,
                      visibleInputs,
                      preview: (panel?.innerText || "").split("\\n").map((line) => line.trim()).filter(Boolean).slice(0, 8).join(" / "),
                    }};
                  }};

                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#statusButton") && document.querySelector("#dashboardForm"), 15000, "console controls");
                  await sleep(800);
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");

                  const tabs = [...document.querySelectorAll("button.tab[data-tab]")].map((button) => ({{
                    key: button.dataset.tab,
                    label: button.textContent.trim(),
                  }}));
                  const menuResults = [];
                  for (const item of tabs) {{
                    const beforeErrorCount = runtimeErrors.length;
                    const button = document.querySelector(`button.tab[data-tab="${{item.key}}"]`);
                    button.click();
                    await waitFor(() => document.querySelector(`#${{CSS.escape(item.key)}}`)?.classList.contains("active"), 8000, `${{item.key}} active`);
                    await sleep(250);
                    const panel = document.querySelector(`#${{CSS.escape(item.key)}}`);
                    const summary = panelSummary(panel);
                    const hardOutputError = hardErrorPattern.test(outputText());
                    menuResults.push({{
                      key: item.key,
                      label: item.label,
                      activeButton: button.classList.contains("active"),
                      activePanel: panel?.classList.contains("active") && visible(panel),
                      visibleButtons: summary.visibleButtons,
                      visibleInputs: summary.visibleInputs,
                      preview: summary.preview,
                      newRuntimeErrors: runtimeErrors.slice(beforeErrorCount),
                      outputErrorVisible: hardOutputError,
                    }});
                  }}

                  const setDashboardTicker = async () => {{
                    document.querySelector('button.tab[data-tab="dashboard"]').click();
                    await waitFor(() => document.querySelector("#dashboard")?.classList.contains("active"), 5000, "dashboard active");
                    const tickerInput = document.querySelector('#dashboard input[name="ticker"]');
                    tickerInput.value = "삼양식품";
                    tickerInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    tickerInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    await sleep(250);
                  }};

                  const waitForActionFeedback = async (previousOutput, timeout = 70000) => {{
                    const started = Date.now();
                    while (Date.now() - started < timeout) {{
                      const text = outputText();
                      const status = outputStatus();
                      const feedback = actionFeedbackText();
                      if (
                        activeTabKey() !== "dashboard" ||
                        text !== previousOutput ||
                        /완료|오류|처리 중|진행 중|요청 접수/.test(`${{status}} ${{feedback}} ${{text}}`)
                      ) {{
                        return {{ text, status, feedback, activeTab: activeTabKey(), activePanel: activePanelKey() }};
                      }}
                      await sleep(300);
                    }}
                    return {{ text: outputText(), status: outputStatus(), feedback: actionFeedbackText(), activeTab: activeTabKey(), activePanel: activePanelKey(), timeout: true }};
                  }};

                  const clickVisibleAction = async (selector, label, timeout = 70000) => {{
                    await setDashboardTicker();
                    const candidates = [...document.querySelectorAll(selector)]
                      .filter((button) => visible(button) && (!label || button.textContent.trim() === label));
                    if (candidates.length !== 1) {{
                      return {{ selector, label, ok: false, reason: `visible candidates=${{candidates.length}}` }};
                    }}
                    const beforeErrorCount = runtimeErrors.length;
                    const beforeOutput = outputText();
                    candidates[0].click();
                    const observed = await waitForActionFeedback(beforeOutput, timeout);
                    const hardError = hardErrorPattern.test(observed.text);
                    const feedbackOk = /완료|오류|처리 중|진행 중|요청 접수/.test(`${{observed.status}} ${{observed.feedback}} ${{observed.text}}`);
                    return {{
                      selector,
                      label,
                      ok: feedbackOk && !hardError && runtimeErrors.length === beforeErrorCount,
                      status: observed.status,
                      feedback: observed.feedback,
                      feedbackOk,
                      activeTab: observed.activeTab,
                      activePanel: observed.activePanel,
                      timeout: Boolean(observed.timeout),
                      outputPreview: observed.text.split("\\n").slice(0, 8).join("\\n"),
                      newRuntimeErrors: runtimeErrors.slice(beforeErrorCount),
                    }};
                  }};

                  const loadDashboardCards = async () => {{
                    await setDashboardTicker();
                    document.querySelector("#dashboardForm button[type='submit']").click();
                    await waitFor(() => {{
                      const cardsText = document.querySelector("#dashboardCards")?.innerText || "";
                      const visibleCardActions = [...document.querySelectorAll("#dashboard .dashboard-card-actions [data-workflow-action]")]
                        .filter(visible);
                      return (
                        visibleCardActions.length >= 5 ||
                        (cardsText.includes("현재 조회") && cardsText.includes("저장 데이터"))
                      );
                    }}, 120000, "dashboard cards");
                  }};

                  const clickCardAction = async (selector, label, timeout = 70000) => {{
                    await loadDashboardCards();
                    const candidates = [...document.querySelectorAll(selector)]
                      .filter((button) => visible(button) && (!label || button.textContent.trim() === label));
                    if (candidates.length !== 1) {{
                      return {{ selector, label, ok: false, reason: `visible candidates=${{candidates.length}}` }};
                    }}
                    const beforeErrorCount = runtimeErrors.length;
                    const beforeOutput = outputText();
                    candidates[0].click();
                    const observed = await waitForActionFeedback(beforeOutput, timeout);
                    const hardError = hardErrorPattern.test(observed.text);
                    const feedbackOk = /완료|오류|처리 중|진행 중|요청 접수/.test(`${{observed.status}} ${{observed.feedback}} ${{observed.text}}`);
                    return {{
                      selector,
                      label,
                      ok: feedbackOk && !hardError && runtimeErrors.length === beforeErrorCount,
                      status: observed.status,
                      feedback: observed.feedback,
                      feedbackOk,
                      activeTab: observed.activeTab,
                      activePanel: observed.activePanel,
                      timeout: Boolean(observed.timeout),
                      outputPreview: observed.text.split("\\n").slice(0, 8).join("\\n"),
                      newRuntimeErrors: runtimeErrors.slice(beforeErrorCount),
                    }};
                  }};

                  const shortcutPlan = [
                    ['#dashboard .dashboard-command-bar [data-workflow-action="refresh-data"]', '최신 데이터 조회', 90000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="diagnose-ticker"]', '티커 진단', 60000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="chart"]', '차트 분석', 30000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="capture"]', '정보 입력', 30000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="memory"]', '저장 데이터 보기', 30000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="system-check"]', '시스템 점검', 120000, false],
                    ['#dashboard .dashboard-command-bar [data-workflow-action="run-team"]', '리포트 실행', 120000, true],
                    ['#recentWeeklyEvidenceSynthesisButton', '추천 근거 요약', 120000, true],
                  ];
                  await setDashboardTicker();
                  const initialDashboardCommandLayout = dashboardCommandLayout();
                  const clippedDashboardCommands = initialDashboardCommandLayout.filter((item) => item.clipped);

                  const shortcutResults = [];
                  for (const [selector, label, timeout, writeAction] of shortcutPlan) {{
                    if (writeAction && !includeWriteActions) {{
                      shortcutResults.push({{ selector, label, ok: true, skipped: true, reason: "write action skipped by default" }});
                      continue;
                    }}
                    shortcutResults.push(await clickVisibleAction(selector, label, timeout));
                  }}

                  await loadDashboardCards();
                  const cardActionPlan = [
                    ['#dashboard .dashboard-card-actions [data-workflow-action="memory"]', '저장 데이터', 30000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="marketData"]', '시장 데이터', 30000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="news"]', '뉴스 검토', 30000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="storage-quality"]', '품질 점검', 60000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="marketData"]', '시장일지 열기', 30000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="system-check"]', '상태 점검', 120000],
                    ['#dashboard .dashboard-card-actions [data-workflow-action="dart-refresh"]', '공시 재점검', 120000],
                  ];
                  const cardActionResults = [];
                  for (const [selector, label, timeout] of cardActionPlan) {{
                    cardActionResults.push(await clickCardAction(selector, label, timeout));
                  }}

                  const failedMenus = menuResults.filter((item) =>
                    !item.activeButton ||
                    !item.activePanel ||
                    (!item.visibleButtons.length && !item.visibleInputs && !item.preview) ||
                    item.outputErrorVisible ||
                    item.newRuntimeErrors.length
                  );
                  const failedShortcuts = shortcutResults.filter((item) => !item.ok);
                  const failedCardActions = cardActionResults.filter((item) => !item.ok);
                  return {{
                    backendStatus: document.querySelector("#backendStatus")?.textContent || "",
                    menuCount: menuResults.length,
                    menuOkCount: menuResults.length - failedMenus.length,
                    failedMenus,
                    menuResults,
                    shortcutResults,
                    cardActionResults,
                    failedShortcuts,
                    failedCardActions,
                    dashboardCommandLayout: initialDashboardCommandLayout,
                    clippedDashboardCommands,
                    runtimeErrors,
                  }};
                }})()
                """,
                timeout=420,
            )
            if result["failedMenus"]:
                raise AssertionError(f"메뉴 전환 실패: {result['failedMenus']}")
            if result["failedShortcuts"]:
                raise AssertionError(f"대시보드 빠른 버튼 실패: {result['failedShortcuts']}")
            if result.get("clippedDashboardCommands"):
                raise AssertionError(f"대시보드 메뉴 버튼 잘림: {result["clippedDashboardCommands"]}")
            if result["failedCardActions"]:
                raise AssertionError(f"대시보드 카드 버튼 실패: {result['failedCardActions']}")
            if result["runtimeErrors"]:
                raise AssertionError(f"브라우저 런타임 오류: {result['runtimeErrors']}")
            return result
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Research console menu smoke test")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--include-write-actions",
        action="store_true",
        help="리포트 실행처럼 저장될 수 있는 버튼까지 포함합니다.",
    )
    args = parser.parse_args()
    result = run_menu_smoke(args.url, include_write_actions=args.include_write_actions)
    print(json.dumps({"status": "success", **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
