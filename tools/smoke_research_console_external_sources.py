"""Headless smoke test for external source buttons in the research console."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile

from smoke_research_console_clicks import CdpClient, assert_project_root, chrome_path, wait_for_page


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=clicks&sourceSmoke=1"


def run_external_source_smoke(url: str) -> dict:
    assert_project_root()
    port = 9225
    with tempfile.TemporaryDirectory(prefix="research-console-source-chrome-", ignore_cleanup_errors=True) as profile_dir:
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
                """
                (async () => {
                  const runtimeErrors = [];
                  window.addEventListener("error", (event) => runtimeErrors.push(event.message || String(event.error || "runtime error")));
                  window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(event.reason?.message || String(event.reason || "unhandled rejection")));
                  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                  const visible = (el) => Boolean(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
                  const waitFor = async (predicate, timeout = 90000, label = "condition") => {
                    const started = Date.now();
                    while (Date.now() - started < timeout) {
                      const value = predicate();
                      if (value) return value;
                      await sleep(300);
                    }
                    throw new Error(`Timed out waiting for ${label}`);
                  };
                  const outputText = () => document.querySelector("#output")?.innerText || "";
                  const outputStatus = () => document.querySelector("#outputStatus")?.textContent || "";
                  const feedbackText = () => document.querySelector("#actionFeedback")?.textContent || "";
                  const hardErrorPattern = /is not defined|ReferenceError|TypeError|Cannot read|Failed to fetch|HTTP error/i;

                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#statusButton") && document.querySelector("#apiBaseUrl"), 15000, "console controls");
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");

                  const openTab = async (key) => {
                    const button = document.querySelector(`button.tab[data-tab="${key}"]`);
                    if (!button) throw new Error(`Tab not found: ${key}`);
                    button.click();
                    await waitFor(() => document.querySelector(`#${CSS.escape(key)}`)?.classList.contains("active"), 8000, `${key} active`);
                    await sleep(300);
                  };

                  const clickButtonAndWait = async ({ tabKey, selector, label, expected }) => {
                    await openTab(tabKey);
                    const candidates = [...document.querySelectorAll(selector)].filter(visible);
                    if (candidates.length !== 1) {
                      return { label, ok: false, reason: `visible candidates=${candidates.length}` };
                    }
                    const beforeErrorCount = runtimeErrors.length;
                    const beforeOutput = outputText();
                    candidates[0].click();
                    await waitFor(() => {
                      const text = outputText();
                      const status = outputStatus();
                      const feedback = feedbackText();
                      return text !== beforeOutput || /완료|오류|처리 중|진행 중|요청 접수/.test(`${status} ${feedback} ${text}`);
                    }, 90000, `${label} output start`);
                    await waitFor(() => expected.every((item) => outputText().includes(item)), 120000, `${label} expected output`);
                    const text = outputText();
                    const hardError = hardErrorPattern.test(text);
                    return {
                      label,
                      ok: !hardError && runtimeErrors.length === beforeErrorCount,
                      status: outputStatus(),
                      feedback: feedbackText(),
                      preview: text.split("\\n").slice(0, 12).join("\\n"),
                      runtimeErrors: runtimeErrors.slice(beforeErrorCount),
                    };
                  };

                  const checks = [];
                  checks.push(await clickButtonAndWait({
                    tabKey: "macro",
                    selector: "#kcifReportsWatchButton",
                    label: "KCIF 보고서 Watch",
                    expected: ["KCIF 보고서 Watch", "저장 정책", "관련 보고서"],
                  }));
                  checks.push(await clickButtonAndWait({
                    tabKey: "macro",
                    selector: "#regionalBusinessSourcesWatchButton",
                    label: "EMERiCs/CSF/KIEP Watch",
                    expected: ["EMERiCs/CSF/KIEP 자료 Watch", "저장 정책", "소스 상태"],
                  }));
                  checks.push(await clickButtonAndWait({
                    tabKey: "memory",
                    selector: "#researchAutomationStatusButton",
                    label: "자동화 상태",
                    expected: ["리서치 자동화 적용 상태", "외부 소스 자동 점검", "EMERiCs/CSF/KIEP", "Joby IR"],
                  }));

                  return {
                    status: checks.every((item) => item.ok) ? "success" : "failed",
                    checks,
                    runtimeErrors,
                  };
                })()
                """,
                timeout=150,
            )
            return result
        finally:
            if client is not None:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    result = run_external_source_smoke(args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
