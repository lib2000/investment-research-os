"""Targeted headless QA for the Kiwoom interest-group console workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time

from smoke_research_console_clicks import (
    CdpClient,
    assert_project_root,
    chrome_path,
    free_devtools_port,
    wait_for_page,
)


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=kiwoom-interest"


def run_check(url: str) -> dict:
    assert_project_root()
    port = free_devtools_port()
    started_at = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="kiwoom-interest-console-", ignore_cleanup_errors=True) as profile_dir:
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
                  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                  const waitFor = async (predicate, timeout = 30000, label = "condition") => {
                    const started = Date.now();
                    while (Date.now() - started < timeout) {
                      const value = predicate();
                      if (value) return value;
                      await sleep(250);
                    }
                    throw new Error(`Timed out waiting for ${label}`);
                  };
                  const runtimeErrors = [];
                  window.addEventListener("error", (event) => runtimeErrors.push(event.message));
                  window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(String(event.reason)));
                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#kiwoomInterestGroupsButton"), 15000, "interest controls");
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton")?.click();
                  await waitFor(() => {
                    const text = [
                      document.querySelector("#backendStatus")?.textContent || "",
                      document.querySelector("#providerStatus")?.textContent || "",
                      document.querySelector("#output")?.innerText || "",
                    ].join(" ");
                    return /정상|kis|활성|완료/.test(text);
                  }, 20000, "backend status");
                  document.querySelector('[data-tab="interests"]')?.click();
                  await waitFor(() => document.querySelector("#interests")?.classList.contains("active"), 5000, "interests tab");
                  document.querySelector("#kiwoomInterestGroupsButton").click();
                  const panelText = await waitFor(() => {
                    const panel = document.querySelector("#kiwoomInterestCandidatePanel");
                    const text = panel?.innerText || "";
                    return panel && !panel.hidden && text.includes("키움 추가 후보") ? text : "";
                  }, 120000, "kiwoom interest candidate panel");
                  const rows = [...document.querySelectorAll(".kiwoom-interest-candidate-row")];
                  const reviewRows = [...document.querySelectorAll(".kiwoom-interest-candidate-row.is-review")];
                  const enabledRows = rows.filter((row) => !row.querySelector("input")?.disabled);
                  const disabledReviewRows = reviewRows.filter((row) => row.querySelector("input")?.disabled);
                  const checkedBeforeSync = [...document.querySelectorAll('input[name="kiwoomInterestCandidate"]:checked')].length;
                  if (!rows.length) throw new Error("No Kiwoom candidate rows rendered.");
                  if (!panelText.includes("확인 필요")) throw new Error("Review-needed count is not visible.");
                  if (!reviewRows.length) throw new Error("Review-needed rows are not rendered.");
                  if (disabledReviewRows.length !== reviewRows.length) {
                    throw new Error("Some review-needed rows are selectable.");
                  }
                  if (enabledRows.length && checkedBeforeSync !== enabledRows.length) {
                    throw new Error("Selectable add candidates are not checked by default.");
                  }
                  let syncText = "";
                  let syncSkippedNoAddCandidates = false;
                  if (enabledRows.length) {
                    document.querySelector("#kiwoomInterestSyncButton").click();
                    syncText = await waitFor(() => {
                      const button = document.querySelector("#kiwoomInterestSyncButton");
                      const text = [
                        document.querySelector("#kiwoomInterestCandidatePanel")?.innerText || "",
                        document.querySelector("#kiwoomInterestSyncStatus")?.innerText || "",
                        document.querySelector("#output")?.innerText || "",
                      ].join("\\n");
                      return button && !button.disabled && (
                        text.includes("방금 저장") ||
                        text.includes("write_mode") ||
                        text.includes("sync_result") ||
                        text.includes("저장")
                      ) ? text : "";
                    }, 120000, "kiwoom sync");
                  } else {
                    syncSkippedNoAddCandidates = true;
                    syncText = "이미 저장 가능한 신규 후보가 없습니다.";
                  }
                  const savedCountText = document.querySelector("#kiwoomInterestCandidatePanel")?.innerText || "";
                  return {
                    status: "success",
                    panelShowsAddCandidates: panelText.includes("키움 추가 후보"),
                    panelShowsReviewCount: panelText.includes("확인 필요"),
                    candidateRowCount: rows.length,
                    selectableRowCount: enabledRows.length,
                    reviewRowCount: reviewRows.length,
                    disabledReviewRowCount: disabledReviewRows.length,
                    checkedBeforeSync,
                    syncSkippedNoAddCandidates,
                    syncShowsSavedCount: savedCountText.includes("방금 저장"),
                    syncOutputMentionsWorkflow: /후보 저장|동기화|preview_only|저장|신규 후보가 없습니다/.test(syncText),
                    runtimeErrors,
                  };
                })()
                """,
                timeout=300,
            )
            result["elapsedSeconds"] = round(time.monotonic() - started_at, 2)
            runtime_errors = result.get("runtimeErrors") or []
            if runtime_errors:
                raise AssertionError(f"runtime errors: {' | '.join(runtime_errors)}")
            if result["reviewRowCount"] != result["disabledReviewRowCount"]:
                raise AssertionError("확인 필요 행 중 선택 가능한 항목이 있습니다.")
            if result["checkedBeforeSync"] != result["selectableRowCount"]:
                raise AssertionError("저장 가능한 후보가 기본 선택 상태가 아닙니다.")
            return result
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiwoom interest console workflow QA")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다. 기본 출력도 JSON입니다.")
    args = parser.parse_args()
    try:
        result = run_check(args.url)
    except (AssertionError, RuntimeError, TimeoutError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failure", "errorType": type(exc).__name__, "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
