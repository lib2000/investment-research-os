"""Write-action smoke tests for the research console.

The script creates only QA-TEST-* data, exercises user-facing save/delete
buttons, and cleans up the reversible records it creates. It intentionally uses
the standard-library Chrome DevTools helper from smoke_research_console_clicks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

from smoke_research_console_clicks import CdpClient, assert_project_root, chrome_path, wait_for_page


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=write-actions"
DEFAULT_API_BASE = "http://127.0.0.1:8001"
DEFAULT_TOKEN = "dev-local-token"


def api_request(
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    api_base: str = DEFAULT_API_BASE,
    token: str = DEFAULT_TOKEN,
    timeout: float = 30,
) -> object:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def has_qa_marker(value: object) -> bool:
    return "QA-TEST-" in json.dumps(value, ensure_ascii=False)


def cleanup_qa_artifacts(api_base: str = DEFAULT_API_BASE, token: str = DEFAULT_TOKEN) -> dict:
    """Remove reversible QA state and soft-archive QA research-memory files."""
    assert_project_root()
    result = {
        "portfoliosDeleted": 0,
        "newsDeleted": 0,
        "interestTickersRemoved": 0,
        "interestSectorsRemoved": 0,
        "researchFilesArchived": 0,
    }

    try:
        portfolios_payload = api_request("/api/v1/portfolios", api_base=api_base, token=token)
        for portfolio in portfolios_payload.get("portfolios", []) if isinstance(portfolios_payload, dict) else []:
            name = str(portfolio.get("portfolio_name") or "")
            if name.startswith("QA-TEST-"):
                api_request(
                    f"/api/v1/portfolios/{urllib.parse.quote(name, safe='')}",
                    method="DELETE",
                    api_base=api_base,
                    token=token,
                )
                result["portfoliosDeleted"] += 1
    except Exception as exc:  # noqa: BLE001 - cleanup should report partial progress.
        result["portfolioCleanupError"] = str(exc)

    try:
        interests_payload = api_request("/api/v1/interests", api_base=api_base, token=token)
        if isinstance(interests_payload, dict):
            tickers = interests_payload.get("tickers") or []
            sectors = interests_payload.get("sectors") or []
            kept_tickers = [item for item in tickers if not has_qa_marker(item)]
            kept_sectors = [item for item in sectors if not has_qa_marker(item)]
            result["interestTickersRemoved"] = len(tickers) - len(kept_tickers)
            result["interestSectorsRemoved"] = len(sectors) - len(kept_sectors)
            if result["interestTickersRemoved"] or result["interestSectorsRemoved"]:
                api_request(
                    "/api/v1/interests",
                    method="PUT",
                    body={"tickers": kept_tickers, "sectors": kept_sectors},
                    api_base=api_base,
                    token=token,
                )
    except Exception as exc:  # noqa: BLE001
        result["interestCleanupError"] = str(exc)

    try:
        news_payload = api_request("/api/v1/news/inbox?limit=200&filter=all", api_base=api_base, token=token)
        for item in news_payload.get("items", []) if isinstance(news_payload, dict) else []:
            if item.get("id") and has_qa_marker(item):
                api_request(
                    "/api/v1/news/inbox/action",
                    method="POST",
                    body={"id": item["id"], "action": "delete"},
                    api_base=api_base,
                    token=token,
                )
                result["newsDeleted"] += 1
    except Exception as exc:  # noqa: BLE001
        result["newsCleanupError"] = str(exc)

    try:
        manifest_payload = api_request("/api/v1/research-memory", api_base=api_base, token=token)
        for entry in manifest_payload.get("entries", []) if isinstance(manifest_payload, dict) else []:
            if not has_qa_marker(entry):
                continue
            if entry.get("is_deleted") or str(entry.get("status") or "").lower() == "archived":
                continue
            ticker = str(entry.get("ticker") or "").strip()
            file_name = str(entry.get("file_name") or "").strip()
            if not ticker or not file_name:
                continue
            api_request(
                "/api/v1/research-memory/"
                f"{urllib.parse.quote(ticker, safe='')}/files/{urllib.parse.quote(file_name, safe='')}/archive",
                method="PATCH",
                body={"archived": True, "reason": "QA smoke test artifact cleanup"},
                api_base=api_base,
                token=token,
            )
            result["researchFilesArchived"] += 1
    except Exception as exc:  # noqa: BLE001
        result["researchArchiveError"] = str(exc)

    return result


def run_write_action_smoke(url: str) -> dict:
    assert_project_root()
    pre_cleanup = cleanup_qa_artifacts()
    port = 9225
    marker = f"QA-TEST-{int(time.time())}"
    with tempfile.TemporaryDirectory(prefix="research-console-write-chrome-", ignore_cleanup_errors=True) as profile_dir:
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
                  const marker = {json.dumps(marker)};
                  const runtimeErrors = [];
                  window.addEventListener("error", (event) => runtimeErrors.push(event.message || String(event.error || "runtime error")));
                  window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(event.reason?.message || String(event.reason || "unhandled rejection")));
                  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
                  const waitFor = async (predicate, timeout = 30000, label = "condition") => {{
                    const started = Date.now();
                    while (Date.now() - started < timeout) {{
                      const value = predicate();
                      if (value) return value;
                      await sleep(250);
                    }}
                    const output = document.querySelector("#output")?.innerText || "";
                    throw new Error(`Timed out waiting for ${{label}}. Output: ${{output.split("\\n").slice(0, 10).join(" / ")}}`);
                  }};
                  const clickTab = async (tab) => {{
                    document.querySelector(`[data-tab="${{tab}}"]`).click();
                    await waitFor(() => document.querySelector(`#${{tab}}`)?.classList.contains("active"), 8000, `${{tab}} active`);
                  }};
                  const outputText = () => document.querySelector("#output")?.innerText || "";
                  const assertNoRuntimeErrors = (label) => {{
                    if (runtimeErrors.length) {{
                      throw new Error(`${{label}} runtime errors: ${{runtimeErrors.join(" | ")}}`);
                    }}
                  }};
                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#statusButton") && document.querySelector("#captureForm"), 15000, "console controls");
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 20000, "backend status");

                  const results = {{ marker }};

                  await clickTab("capture");
                  const captureForm = document.querySelector("#captureForm");
                  captureForm.elements.rawContent.value = `${{marker}} 자동 분류 저장 버튼 검증용 메모입니다. 저장 후 입력창 초기화를 확인합니다.`;
                  captureForm.elements.sourceUrl.value = "";
                  captureForm.elements.destination.value = "auto";
                  captureForm.querySelector('button[type="submit"]').click();
                  const captureOutput = await waitFor(
                    () => /정보 입력 저장 실행이 완료|저장 데이터|처리 결과/.test(outputText()) ? outputText() : "",
                    70000,
                    "capture save"
                  );
                  results.captureSaved = captureOutput.includes(marker) || /저장 데이터|처리 결과/.test(captureOutput);
                  results.captureReset = captureForm.elements.rawContent.value === "" && captureForm.elements.sourceUrl.value === "";
                  if (!results.captureReset) {{
                    throw new Error("정보 입력 저장 후 입력창이 비워지지 않았습니다.");
                  }}
                  assertNoRuntimeErrors("capture");

                  await clickTab("news");
                  const newsForm = document.querySelector("#newsForm");
                  newsForm.elements.rawContent.value = `${{marker}} 뉴스 인박스 저장/보류/삭제 버튼 검증용 짧은 자체 메모입니다.`;
                  newsForm.elements.sourceUrl.value = "";
                  newsForm.querySelector('button[type="submit"]').click();
                  await waitFor(
                    () => {{
                      const fieldsReset = newsForm.elements.rawContent.value === "" && newsForm.elements.sourceUrl.value === "";
                      const hasSavedOutput = !/처리 중|저장 중/.test(outputText()) && /뉴스|인박스|처리 결과/.test(outputText());
                      return fieldsReset && hasSavedOutput ? outputText() : "";
                    }},
                    70000,
                    "news save and reset"
                  );
                  results.newsInputReset = newsForm.elements.rawContent.value === "" && newsForm.elements.sourceUrl.value === "";
                  if (!results.newsInputReset) {{
                    throw new Error("뉴스 저장 후 입력창이 비워지지 않았습니다.");
                  }}
                  document.querySelector("#newsInboxButton").click();
                  await waitFor(() => (document.querySelector("#newsInboxList")?.innerText || "").includes(marker), 30000, "QA news card");
                  const findQaCard = () => [...document.querySelectorAll("#newsInboxList [data-news-id]")].find((card) => card.innerText.includes(marker));
                  const qaCard = findQaCard();
                  results.newsCardFound = Boolean(qaCard);
                  if (!qaCard) {{
                    throw new Error("QA 뉴스 카드가 인박스에 표시되지 않았습니다.");
                  }}
                  qaCard.querySelector('[data-news-action="hold"]').click();
                  await waitFor(() => !/처리 중/.test(outputText()) && /보류|완료|뉴스 인박스/.test(outputText()), 30000, "news hold");
                  results.newsHeld = /보류|완료|뉴스 인박스/.test(outputText());
                  document.querySelector("#newsInboxButton").click();
                  await waitFor(() => (document.querySelector("#newsInboxList")?.innerText || "").includes(marker), 30000, "QA news card reload");
                  findQaCard().querySelector('[data-news-action="delete"]').click();
                  await waitFor(() => !/처리 중/.test(outputText()) && /삭제|완료|뉴스 인박스/.test(outputText()), 30000, "news delete");
                  document.querySelector("#newsInboxButton").click();
                  await waitFor(() => !(document.querySelector("#newsInboxList")?.innerText || "").includes(marker), 30000, "QA news removed");
                  results.newsDeleted = true;
                  assertNoRuntimeErrors("news");

                  await clickTab("llmBridge");
                  const llmPromptForm = document.querySelector("#llmPromptForm");
                  const llmResultForm = document.querySelector("#llmResultForm");
                  llmPromptForm.elements.target.value = "";
                  llmPromptForm.elements.sourceContext.value = `${{marker}} LLM 프롬프트 생성 후 응답 저장 초기화 검증 자료입니다.`;
                  llmPromptForm.querySelector('button[type="submit"]').click();
                  await waitFor(() => (document.querySelector("#llmPromptOutput")?.value || "").includes(marker), 10000, "llm prompt");
                  llmResultForm.elements.llmResult.value = `${{marker}} LLM 응답 저장 검증입니다. 요약, 근거, 다음 액션을 저장합니다.`;
                  llmResultForm.querySelector('button[type="submit"]').click();
                  await waitFor(
                    () => {{
                      const resetValues = [
                        llmPromptForm.elements.target.value,
                        llmPromptForm.elements.sourceContext.value,
                        document.querySelector("#llmPromptOutput").value,
                        llmResultForm.elements.llmResult.value,
                      ];
                      const fieldsReset = resetValues.every((value) => value === "");
                      const hasSavedOutput = !/처리 중|저장 중|분석 중/.test(outputText()) && /정보 입력 저장 실행이 완료|저장 데이터|처리 결과/.test(outputText());
                      return fieldsReset && hasSavedOutput ? outputText() : "";
                    }},
                    70000,
                    "llm save and reset"
                  );
                  results.llmReset = {{
                    target: llmPromptForm.elements.target.value,
                    sourceContext: llmPromptForm.elements.sourceContext.value,
                    prompt: document.querySelector("#llmPromptOutput").value,
                    result: llmResultForm.elements.llmResult.value,
                  }};
                  if (Object.values(results.llmReset).some((value) => value !== "")) {{
                    throw new Error(`LLM 저장 후 입력값이 남아 있습니다: ${{JSON.stringify(results.llmReset)}}`);
                  }}
                  assertNoRuntimeErrors("llm");

                  await clickTab("interests");
                  document.querySelector("#interestsLoadButton").click();
                  await waitFor(() => (document.querySelector("#interests")?.innerText || "").includes("관심종목 목록"), 30000, "interests loaded");
                  const interestTickerName = `${{marker}} 관심종목`;
                  document.querySelectorAll("#interests details.interest-add-panel")[0].open = true;
                  const tickerDraft = document.querySelector("#interestTickerDraft");
                  tickerDraft.querySelector('[name="ticker"]').value = interestTickerName;
                  tickerDraft.querySelector('[name="priority"]').value = "medium";
                  tickerDraft.querySelector('[name="thesis"]').value = `${{marker}} 관심종목 추가/삭제 검증`;
                  document.querySelector("#addInterestTickerButton").click();
                  await waitFor(() => (document.querySelector("#interestTickerEditor")?.innerText || "").includes(interestTickerName), 90000, "interest ticker added");
                  results.interestTickerAdded = true;
                  const addedTickerRow = [...document.querySelectorAll("#interestTickerEditor .interest-ticker-row")]
                    .find((row) => row.innerText.includes(interestTickerName));
                  if (!addedTickerRow) {{
                    throw new Error("QA 관심종목 행을 찾지 못했습니다.");
                  }}
                  addedTickerRow.querySelector("details")?.setAttribute("open", "");
                  addedTickerRow.querySelector("[data-editor-remove]").click();
                  await waitFor(() => !(document.querySelector("#interestTickerEditor")?.innerText || "").includes(interestTickerName), 60000, "interest ticker removed");
                  await waitFor(() => /관심종목을 삭제하고 저장했습니다/.test(outputText()), 60000, "interest ticker delete saved");
                  results.interestTickerDeleted = true;
                  const interestName = `${{marker}} 관심섹터`;
                  document.querySelectorAll("#interests details.interest-add-panel")[1].open = true;
                  const sectorDraft = document.querySelector("#interestSectorDraft");
                  sectorDraft.querySelector('[name="name"]').value = interestName;
                  sectorDraft.querySelector('[name="region"]').value = "KR";
                  sectorDraft.querySelector('[name="thesis"]').value = `${{marker}} 관심섹터 추가/삭제 검증`;
                  document.querySelector("#addInterestSectorButton").click();
                  await waitFor(() => (document.querySelector("#interestSectorEditor")?.innerText || "").includes(interestName), 90000, "interest sector added");
                  results.interestSectorAdded = true;
                  const addedSectorRow = [...document.querySelectorAll("#interestSectorEditor .interest-sector-row")]
                    .find((row) => row.innerText.includes(interestName));
                  if (!addedSectorRow) {{
                    throw new Error("QA 관심섹터 행을 찾지 못했습니다.");
                  }}
                  addedSectorRow.querySelector("details").open = true;
                  addedSectorRow.querySelector("[data-editor-remove]").click();
                  await waitFor(() => !(document.querySelector("#interestSectorEditor")?.innerText || "").includes(interestName), 60000, "interest sector removed");
                  await waitFor(() => /관심섹터를 삭제하고 저장했습니다/.test(outputText()), 60000, "interest sector delete saved");
                  results.interestSectorDeleted = true;
                  results.interestDraftRegionDefaultKr = sectorDraft.querySelector('[name="region"]')?.value === "KR";
                  assertNoRuntimeErrors("interests");

                  await clickTab("portfolio");
                  const portfolioForm = document.querySelector("#portfolioForm");
                  await waitFor(() => document.querySelector("#holdingsEditor .holding-row"), 15000, "portfolio rows");
                  const portfolioName = `${{marker}} 포트폴리오`;
                  portfolioForm.elements.portfolioName.value = portfolioName;
                  portfolioForm.elements.portfolioValue.value = "10,000원";
                  portfolioForm.elements.portfolioNotes.value = `${{marker}} 포트폴리오 저장/삭제 버튼 검증`;
                  const portfolioRows = [...document.querySelectorAll("#holdingsEditor .holding-row")];
                  portfolioRows.slice(1).forEach((row) => row.remove());
                  const qaHoldingRow = portfolioRows[0];
                  const setQaRowValue = (name, value) => {{
                    const field = qaHoldingRow.querySelector(`[name="${{name}}"]`);
                    if (field) {{
                      field.value = value;
                      field.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    }}
                  }};
                  setQaRowValue("name", "현금");
                  setQaRowValue("ticker", "CASH");
                  setQaRowValue("market_value", "10,000원");
                  setQaRowValue("current_price", "10,000원");
                  setQaRowValue("average_cost", "10,000원");
                  setQaRowValue("quantity", "1");
                  setQaRowValue("unrealized_gain", "0원");
                  setQaRowValue("unrealized_return", "0%");
                  setQaRowValue("currency", "KRW");
                  setQaRowValue("sector", "Cash");
                  setQaRowValue("cost_basis", "10,000원");
                  setQaRowValue("fx_rate", "1");
                  setQaRowValue("theme_tags", "Cash");
                  document.querySelector("#output").textContent = "";
                  document.querySelector("#portfolioSaveButton").click();
                  await waitFor(() => [...document.querySelector("#portfolioSelect").options].some((option) => option.value === portfolioName), 90000, "QA portfolio option");
                  results.portfolioSaved = true;
                  document.querySelector("#portfolioSelect").value = portfolioName;
                  document.querySelector("#portfolioSelect").dispatchEvent(new Event("change", {{ bubbles: true }}));
                  document.querySelector("#output").textContent = "";
                  document.querySelector("#portfolioDeleteButton").click();
                  await waitFor(() => ![...document.querySelector("#portfolioSelect").options].some((option) => option.value === portfolioName), 90000, "QA portfolio removed");
                  results.portfolioDeleted = true;
                  assertNoRuntimeErrors("portfolio");

                  return results;
                }})()
                """,
                timeout=420,
            )
            required_true = [
                "captureSaved",
                "captureReset",
                "newsInputReset",
                "newsCardFound",
                "newsHeld",
                "newsDeleted",
                "interestTickerAdded",
                "interestTickerDeleted",
                "interestSectorAdded",
                "interestSectorDeleted",
                "interestDraftRegionDefaultKr",
                "portfolioSaved",
                "portfolioDeleted",
            ]
            missing = [key for key in required_true if not result.get(key)]
            if missing:
                raise AssertionError(f"Write-action smoke failed: {missing}")
            post_cleanup = cleanup_qa_artifacts()
            result["preCleanup"] = pre_cleanup
            result["postCleanup"] = post_cleanup
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--cleanup-only", action="store_true")
    args = parser.parse_args()
    if args.cleanup_only:
        result = cleanup_qa_artifacts()
        print(json.dumps({"status": "success", "cleanup": result}, ensure_ascii=False, indent=2))
        return
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = run_write_action_smoke(args.url)
            break
        except RuntimeError as exc:
            last_error = exc
            if "Execution context was destroyed" not in str(exc) or attempt:
                raise
            cleanup_qa_artifacts()
            time.sleep(1.0)
    else:
        raise last_error or RuntimeError("write-action smoke failed")
    print(json.dumps({"status": "success", **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
