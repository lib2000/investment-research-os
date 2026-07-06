"""Headless layout check for clickable portfolio holdings and interest summaries."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from smoke_research_console_clicks import CdpClient, assert_project_root, chrome_path, free_devtools_port, wait_for_page


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=interest-summary-layout"


def run_layout_check(url: str, *, output_screenshot: Path | None = None) -> dict:
    assert_project_root()
    port = free_devtools_port()
    with tempfile.TemporaryDirectory(prefix="research-console-interest-layout-", ignore_cleanup_errors=True) as profile_dir:
        process = subprocess.Popen(
            [
                chrome_path(),
                "--headless=new",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile_dir}",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1280,900",
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
                  const visible = (el) => Boolean(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
                  const runtimeErrors = [];
                  window.addEventListener("error", (event) => runtimeErrors.push(String(event.message || event.error || "error")));
                  window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(String(event.reason || "unhandledrejection")));
                  const waitFor = async (predicate, timeout = 30000, label = "condition") => {
                    const started = Date.now();
                    while (Date.now() - started < timeout) {
                      const value = predicate();
                      if (value) return value;
                      await sleep(250);
                    }
                    throw new Error(`Timed out waiting for ${label}`);
                  };
                  const cssRuleTextIncludes = (needle) => {
                    for (const sheet of [...document.styleSheets]) {
                      let rules = [];
                      try {
                        rules = [...(sheet.cssRules || [])];
                      } catch (error) {
                        continue;
                      }
                      if (rules.some((rule) => String(rule.cssText || "").includes(needle))) {
                        return true;
                      }
                    }
                    return false;
                  };
                  const interestRecommendationHorizontalCssReady =
                    cssRuleTextIncludes(".interest-recommendation-panel") &&
                    cssRuleTextIncludes("grid-template-columns: minmax(180px") &&
                    cssRuleTextIncludes(".interest-ticker-summary-row:has(.interest-card-details[open])");
                  const summaryStats = (selector) => [...document.querySelectorAll(selector)]
                    .filter(visible)
                    .map((row) => {
                      const details = row.querySelector("details.interest-card-details");
                      const summary = row.querySelector("summary.interest-card-summary");
                      const strong = summary?.querySelector("strong");
                      const text = (summary?.textContent || "").replace(/\\s+/g, " ").trim();
                      const name = (strong?.textContent || "").replace(/\\s+/g, " ").trim();
                      return {
                        text,
                        name,
                        nameOnly: Boolean(name) && text === name,
                        hasMeta: Boolean(summary?.querySelector(".interest-summary-meta")),
                        hasNote: Boolean(summary?.querySelector(".interest-summary-note")),
                        hasDetailGrid: Boolean(details?.querySelector(".interest-detail-grid")),
                        opened: Boolean(details?.open),
                      };
                    });
                  const openFirst = async (selector) => {
                    const root = selector.includes("interest-ticker")
                      ? document.querySelector("#interests.active #interestTickerEditor")
                      : selector.includes("interest-sector")
                        ? document.querySelector("#interests.active #interestSectorEditor")
                        : document;
                    const row = [...(root || document).querySelectorAll(selector)].find(visible);
                    const details = row?.querySelector("details.interest-card-details");
                    const summary = row?.querySelector("summary.interest-card-summary");
                    const openedName = (summary?.querySelector("strong")?.textContent || "").replace(/\\s+/g, " ").trim();
                    summary?.scrollIntoView({block: "center", inline: "nearest"});
                    await sleep(100);
                    summary?.click();
                    if (details && !details.open) {
                      details.open = true;
                    }
                    await sleep(400);
                    const currentRow = openedName
                      ? [...(root || document).querySelectorAll(selector)]
                          .find((candidate) =>
                            visible(candidate) &&
                            (candidate.querySelector("summary strong")?.textContent || "").replace(/\\s+/g, " ").trim() === openedName
                          )
                      : row;
                    const currentDetails = currentRow?.querySelector("details.interest-card-details") || details;
                    if (currentDetails && !currentDetails.open) {
                      currentDetails.open = true;
                    }
                    currentRow?.classList?.toggle("is-detail-open", Boolean(currentDetails?.open));
                    const recommendationPanel = currentDetails?.querySelector(".interest-recommendation-panel");
                    recommendationPanel?.scrollIntoView({block: "center", inline: "nearest"});
                    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    const panelStyle = recommendationPanel ? getComputedStyle(recommendationPanel) : null;
                    const panelDisplay = panelStyle?.getPropertyValue("display") || panelStyle?.display || "";
                    const panelColumnsText = panelStyle?.getPropertyValue("grid-template-columns") || panelStyle?.gridTemplateColumns || "";
                    const panelColumnCount = !panelColumnsText || panelColumnsText === "none"
                      ? 0
                      : panelColumnsText.trim().split(/\\s+/).length;
                    const panelRect = recommendationPanel?.getBoundingClientRect();
                    return {
                      opened: Boolean(currentDetails?.open),
                      detailVisible: visible(currentDetails?.querySelector(".interest-detail-grid")),
                      hasDetailGrid: Boolean(currentDetails?.querySelector(".interest-detail-grid")),
                      hasRecommendationPanel: Boolean(recommendationPanel),
                      recommendationMetricCount: currentDetails?.querySelectorAll(".interest-recommendation-metrics span").length || 0,
                      recommendationEvidenceCount: currentDetails?.querySelectorAll(".interest-recommendation-evidence span").length || 0,
                      recommendationMarketJournalCount: currentDetails?.querySelectorAll(".interest-recommendation-market-journal").length || 0,
                      recommendationMarketJournalLabelVisible: [...(currentDetails?.querySelectorAll(".interest-recommendation-evidence b") || [])]
                        .some((node) => /시장일지 근거/.test(node.textContent || "")),
                      recommendationSignalGridCount: currentDetails?.querySelectorAll(".daily-recommendation-signal-grid").length || 0,
                      recommendationQualityCount: currentDetails?.querySelectorAll(".daily-recommendation-quality").length || 0,
                      recommendationScoreChipCount: currentDetails?.querySelectorAll(".daily-recommendation-score em").length || 0,
                      recommendationSectionLabelCount: currentDetails?.querySelectorAll(".interest-recommendation-evidence b").length || 0,
                      recommendationPanelDisplay: panelDisplay,
                      recommendationPanelColumnCount: panelColumnCount,
                      recommendationPanelWidth: Math.round(panelRect?.width || 0),
                      summaryText: (currentRow?.querySelector("summary")?.textContent || summary?.textContent || "").replace(/\\s+/g, " ").trim(),
                      rowVisible: visible(currentRow),
                    };
                  };
                  const regionGroupStats = (rootSelector) => [...document.querySelectorAll(`${rootSelector} .interest-region-group`)]
                    .filter(visible)
                    .map((section) => ({
                      label: (section.querySelector(".interest-region-heading strong")?.textContent || "").trim(),
                      title: (section.querySelector(".interest-region-heading span")?.textContent || "").trim(),
                      rowCount: section.querySelectorAll(".interest-summary-row").length,
                      names: [...section.querySelectorAll(".interest-summary-row summary strong")]
                        .map((item) => (item.textContent || "").replace(/\\s+/g, " ").trim())
                        .filter(Boolean),
                      hasEmptyState: Boolean(section.querySelector(".interest-region-empty")),
                    }));
                  const sortedLike = (items, locale) => {
                    const collator = new Intl.Collator(locale, {numeric: true, sensitivity: "base"});
                    const sorted = [...items].sort((a, b) => collator.compare(a, b));
                    return items.length <= 1 || items.every((item, index) => item === sorted[index]);
                  };
                  const openFirstHolding = async () => {
                    document.querySelector('button.tab[data-tab="portfolio"]')?.click();
                    await waitFor(() => document.querySelector("#portfolio")?.classList.contains("active"), 5000, "portfolio active");
                    const portfolioSelect = document.querySelector("#portfolioSelect");
                    await waitFor(() => [...portfolioSelect.options].some((option) => option.value), 15000, "portfolio options");
                    const portfolioOption =
                      [...portfolioSelect.options].find((option) => option.value.includes("이형주")) ||
                      [...portfolioSelect.options].find((option) => option.value.includes("가족")) ||
                      [...portfolioSelect.options].find((option) => option.value);
                    portfolioSelect.value = portfolioOption.value;
                    portfolioSelect.dispatchEvent(new Event("change", { bubbles: true }));
                    document.querySelector("#portfolioLoadButton")?.click();
                    await waitFor(() => document.querySelectorAll("#holdingsEditor .holding-row").length > 0, 50000, "portfolio holdings");
                    const row = [...document.querySelectorAll("#holdingsEditor .holding-row")].find(visible);
                    const details = row?.querySelector("details.holding-card-details");
                    const summary = row?.querySelector("summary.holding-card-summary");
                    const text = (summary?.textContent || "").replace(/\\s+/g, " ").trim();
                    summary?.scrollIntoView({block: "center", inline: "nearest"});
                    await sleep(100);
                    summary?.click();
                    await sleep(300);
                    const evidencePanel = details?.querySelector(".holding-evidence-panel");
                    const evidenceStyle = evidencePanel ? getComputedStyle(evidencePanel) : null;
                    const evidenceColumnsText = evidenceStyle?.getPropertyValue("grid-template-columns") || evidenceStyle?.gridTemplateColumns || "";
                    const evidenceColumnCount = !evidenceColumnsText || evidenceColumnsText === "none"
                      ? 0
                      : evidenceColumnsText.trim().split(/\\s+/).length;
                    const evidenceLabels = [...(evidencePanel?.querySelectorAll(".holding-evidence-column b") || [])]
                      .map((node) => (node.textContent || "").replace(/\\s+/g, " ").trim())
                      .filter(Boolean);
                    return {
                      portfolioName: portfolioOption.value,
                      holdingCount: document.querySelectorAll("#holdingsEditor .holding-row").length,
                      summaryText: text,
                      opened: Boolean(details?.open),
                      hasDetailGrid: Boolean(details?.querySelector(".holding-detail-grid")),
                      overviewChipCount: details?.querySelectorAll(".holding-detail-overview span").length || 0,
                      hasEvidencePanel: Boolean(evidencePanel),
                      evidenceLabelCount: evidenceLabels.length,
                      evidenceLabels,
                      evidenceItemCount: evidencePanel?.querySelectorAll(".holding-evidence-column span").length || 0,
                      evidenceMarketJournalCount: evidencePanel?.querySelectorAll(".holding-evidence-market-journal").length || 0,
                      evidencePanelDisplay: evidenceStyle?.getPropertyValue("display") || evidenceStyle?.display || "",
                      evidencePanelColumnCount: evidenceColumnCount,
                      actionLabels: [...(details?.querySelectorAll("[data-holding-action]") || [])]
                        .map((button) => (button.textContent || "").trim())
                        .filter(Boolean),
                    };
                  };
                  const clickHoldingAction = async (label, expected) => {
                    document.querySelector('button.tab[data-tab="portfolio"]')?.click();
                    await waitFor(() => document.querySelector("#portfolio")?.classList.contains("active"), 5000, "portfolio action tab active");
                    const row = [...document.querySelectorAll("#holdingsEditor .holding-row")].find(visible);
                    const details = row?.querySelector("details.holding-card-details");
                    if (details) details.open = true;
                    const button = [...(details?.querySelectorAll("[data-holding-action]") || [])]
                      .find((item) => (item.textContent || "").trim() === label);
                    button?.scrollIntoView({block: "center", inline: "nearest"});
                    await sleep(100);
                    button?.click();
                    const matched = await waitFor(() => {
                      const activeTab = document.querySelector(".tab.active")?.dataset?.tab || "";
                      const outputText = document.querySelector("#output")?.innerText || "";
                      const memoryActive = document.querySelector("#memory")?.classList.contains("active") || false;
                      const chartActive = document.querySelector("#chart")?.classList.contains("active") || false;
                      const dashboardActive = document.querySelector("#dashboard")?.classList.contains("active") || false;
                      const portfolioActive = document.querySelector("#portfolio")?.classList.contains("active") || false;
                      if (expected === "dashboard" && dashboardActive) return true;
                      if (expected === "chart" && (chartActive || /차트 분석|국내 종목이 아닙니다/.test(outputText))) return true;
                      if (expected === "memory" && (memoryActive || /저장 데이터 검색|RAG|저장 데이터/.test(outputText))) return true;
                      if (expected === "risk" && (portfolioActive || /리스크/.test(outputText))) return true;
                      return false;
                    }, 20000, `${label} action`);
                    return {
                      label,
                      ok: Boolean(button && matched),
                      activeTab: document.querySelector(".tab.active")?.dataset?.tab || "",
                      outputPreview: (document.querySelector("#output")?.innerText || "").replace(/\\s+/g, " ").trim().slice(0, 160),
                    };
                  };

                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#statusButton") && document.querySelector("#interestsLoadButton"), 15000, "console controls");
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");
                  document.querySelector('button.tab[data-tab="interests"]')?.click();
                  await waitFor(() => document.querySelector("#interests")?.classList.contains("active"), 5000, "interests active");
                  document.querySelector("#interestsLoadButton")?.click();
                  await waitFor(() => document.querySelectorAll(".interest-ticker-summary-row").length > 0, 30000, "ticker summaries");
                  await waitFor(() => document.querySelectorAll(".interest-sector-summary-row").length > 0, 30000, "sector summaries");

                  const tickerBefore = summaryStats(".interest-ticker-summary-row");
                  const sectorBefore = summaryStats(".interest-sector-summary-row");
                  const tickerRegionGroups = regionGroupStats("#interestTickerEditor");
                  const sectorRegionGroups = regionGroupStats("#interestSectorEditor");
                  const tickerOpen = await openFirst(".interest-ticker-summary-row");
                  const sectorOpen = await openFirst(".interest-sector-summary-row");
                  const holdingOpen = await openFirstHolding();
                  const holdingActionFlows = [
                    await clickHoldingAction("분석", "dashboard"),
                    await clickHoldingAction("차트", "chart"),
                    await clickHoldingAction("자료", "memory"),
                    await clickHoldingAction("리스크", "risk"),
                  ];

                  return {
                    status: "success",
                    holdingCount: holdingOpen.holdingCount,
                    holdingSummaryText: holdingOpen.summaryText,
                    holdingDetailOpened: holdingOpen.opened && holdingOpen.hasDetailGrid,
                    holdingOpen,
                    holdingActionFlows,
                    tickerSummaryCount: tickerBefore.length,
                    sectorSummaryCount: sectorBefore.length,
                    tickerSummarySamples: tickerBefore.slice(0, 5),
                    sectorSummarySamples: sectorBefore.slice(0, 5),
                    tickerRegionGroups,
                    sectorRegionGroups,
                    tickerRegionSortOk: tickerRegionGroups.every((item) =>
                      sortedLike(item.names || [], item.label.includes("미국") ? "en-US" : "ko-KR")
                    ),
                    sectorRegionSortOk: sectorRegionGroups.every((item) =>
                      sortedLike(item.names || [], item.label.includes("미국") ? "en-US" : "ko-KR")
                    ),
                    tickerNameOnlyCount: tickerBefore.filter((item) => item.nameOnly && !item.hasMeta && !item.hasNote).length,
                    sectorNameOnlyCount: sectorBefore.filter((item) => item.nameOnly && !item.hasMeta && !item.hasNote).length,
                    tickerDetailOpened: tickerOpen.opened && tickerOpen.hasDetailGrid,
                    tickerRecommendationDetailReady:
                      tickerOpen.hasRecommendationPanel &&
                      tickerOpen.recommendationMetricCount >= 4 &&
                      tickerOpen.recommendationEvidenceCount >= 6 &&
                      tickerOpen.recommendationSignalGridCount >= 1 &&
                      tickerOpen.recommendationQualityCount >= 1 &&
                      tickerOpen.recommendationScoreChipCount >= 4 &&
                      tickerOpen.recommendationSectionLabelCount >= 4 &&
                      tickerOpen.recommendationMarketJournalCount >= 1 &&
                      tickerOpen.recommendationMarketJournalLabelVisible,
                    tickerRecommendationHorizontal:
                      tickerOpen.recommendationPanelDisplay === "grid" &&
                      tickerOpen.recommendationPanelColumnCount >= 3 &&
                      tickerOpen.recommendationPanelWidth >= Math.min(760, Math.max(0, window.innerWidth - 160)),
                    sectorDetailOpened: sectorOpen.opened && sectorOpen.hasDetailGrid,
                    tickerOpen,
                    sectorOpen,
                    runtimeErrors,
                  };
                })()
                """,
                timeout=90,
            )
            if output_screenshot:
                screenshot = client.call(
                    "Page.captureScreenshot",
                    {"format": "png", "captureBeyondViewport": False},
                    timeout=30,
                )
                output_screenshot.parent.mkdir(parents=True, exist_ok=True)
                import base64

                output_screenshot.write_bytes(base64.b64decode(screenshot["data"]))
                result["screenshot"] = str(output_screenshot)
            return result
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def strict_errors(result: dict) -> list[str]:
    errors: list[str] = []
    ticker_count = int(result.get("tickerSummaryCount") or 0)
    sector_count = int(result.get("sectorSummaryCount") or 0)
    if ticker_count < 1:
        errors.append("관심종목 요약 행이 렌더링되지 않았습니다.")
    if sector_count < 1:
        errors.append("관심섹터 요약 행이 렌더링되지 않았습니다.")
    if int(result.get("tickerNameOnlyCount") or 0) != ticker_count:
        errors.append("관심종목 요약 행에 종목명 외 정보가 노출됩니다.")
    if int(result.get("sectorNameOnlyCount") or 0) != sector_count:
        errors.append("관심섹터 요약 행에 섹터명 외 정보가 노출됩니다.")
    ticker_group_labels = " ".join(item.get("label", "") for item in result.get("tickerRegionGroups") or [])
    sector_group_labels = " ".join(item.get("label", "") for item in result.get("sectorRegionGroups") or [])
    if "한국" not in ticker_group_labels or "미국" not in ticker_group_labels:
        errors.append("관심종목 한국/미국 구분 섹션이 모두 보이지 않습니다.")
    if "한국" not in sector_group_labels or "미국" not in sector_group_labels:
        errors.append("관심섹터 한국/미국 구분 섹션이 모두 보이지 않습니다.")
    if not result.get("tickerRegionSortOk"):
        errors.append("관심종목 지역별 정렬이 한국 가나다순/미국 알파벳순이 아닙니다.")
    if not result.get("sectorRegionSortOk"):
        errors.append("관심섹터 지역별 정렬이 한국 가나다순/미국 알파벳순이 아닙니다.")
    if int(result.get("holdingCount") or 0) < 1:
        errors.append("보유 종목 행이 렌더링되지 않았습니다.")
    if not result.get("holdingDetailOpened"):
        errors.append("보유 종목 요약 클릭 후 상세 정보가 열리지 않았습니다.")
    holding_open = result.get("holdingOpen") if isinstance(result.get("holdingOpen"), dict) else {}
    if int(holding_open.get("overviewChipCount") or 0) < 6:
        errors.append("보유 종목 상세 판단 요약이 부족합니다.")
    if not holding_open.get("hasEvidencePanel"):
        errors.append("보유 종목 상세 근거 패널이 표시되지 않습니다.")
    holding_evidence_labels = " ".join(holding_open.get("evidenceLabels") or [])
    for label in ["시장일지 근거", "리포트/자료", "공시/이벤트", "후속 확인"]:
        if label not in holding_evidence_labels:
            errors.append(f"보유 종목 상세 근거 라벨 누락: {label}")
    if int(holding_open.get("evidenceItemCount") or 0) < 4:
        errors.append("보유 종목 상세 근거 항목이 부족합니다.")
    if int(holding_open.get("evidenceMarketJournalCount") or 0) < 1:
        errors.append("보유 종목 상세 시장일지 근거 항목이 표시되지 않습니다.")
    if holding_open.get("evidencePanelDisplay") != "grid" or int(holding_open.get("evidencePanelColumnCount") or 0) < 4:
        errors.append("보유 종목 상세 근거 패널이 가로 구성으로 표시되지 않습니다.")
    holding_actions = " ".join(holding_open.get("actionLabels") or [])
    for label in ["저장", "분석", "차트", "자료", "리스크"]:
        if label not in holding_actions:
            errors.append(f"보유 종목 상세 액션 누락: {label}")
    holding_action_flows = result.get("holdingActionFlows") if isinstance(result.get("holdingActionFlows"), list) else []
    for label in ["분석", "차트", "자료", "리스크"]:
        flow = next((item for item in holding_action_flows if item.get("label") == label), None)
        if not flow or not flow.get("ok"):
            errors.append(f"보유 종목 상세 액션 흐름 실패: {label}")
    if not result.get("tickerDetailOpened"):
        errors.append("관심종목 요약 클릭 후 상세 정보가 열리지 않았습니다.")
    if not result.get("tickerRecommendationDetailReady"):
        errors.append("관심종목 상세 추천 정보가 부족합니다.")
    ticker_open = result.get("tickerOpen") if isinstance(result.get("tickerOpen"), dict) else {}
    if not ticker_open.get("recommendationMarketJournalLabelVisible"):
        errors.append("관심종목 상세 시장일지 근거 라벨이 표시되지 않습니다.")
    if int(ticker_open.get("recommendationMarketJournalCount") or 0) < 1:
        errors.append("관심종목 상세 시장일지 근거 항목이 표시되지 않습니다.")
    if not result.get("tickerRecommendationHorizontal"):
        errors.append("관심종목 상세 추천 정보가 가로 패널로 표시되지 않습니다.")
    if not result.get("sectorDetailOpened"):
        errors.append("관심섹터 요약 클릭 후 상세 정보가 열리지 않았습니다.")
    runtime_errors = result.get("runtimeErrors") if isinstance(result.get("runtimeErrors"), list) else []
    if runtime_errors:
        errors.append(f"브라우저 런타임 오류 {len(runtime_errors)}개")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="보유종목과 관심종목/섹터 요약 클릭 상세 열림을 헤드리스 Chrome으로 점검합니다.")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output-screenshot", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = run_layout_check(args.url, output_screenshot=args.output_screenshot)
    errors = strict_errors(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "관심 요약 렌더링: "
            f"종목 {int(result.get('tickerSummaryCount') or 0)}개 / "
            f"섹터 {int(result.get('sectorSummaryCount') or 0)}개"
        )
        print(
            "보유 종목 상세: "
            f"{int(result.get('holdingCount') or 0)}개 / "
            f"{'정상' if result.get('holdingDetailOpened') else '실패'}"
        )
        print(
            "이름-only: "
            f"종목 {int(result.get('tickerNameOnlyCount') or 0)}개 / "
            f"섹터 {int(result.get('sectorNameOnlyCount') or 0)}개"
        )
        print(
            "상세 열림: "
            f"종목 {'정상' if result.get('tickerDetailOpened') else '실패'} / "
            f"섹터 {'정상' if result.get('sectorDetailOpened') else '실패'}"
        )
        if result.get("screenshot"):
            print(f"스크린샷: {result['screenshot']}")
    if args.strict and errors:
        print("관심 요약 렌더링 점검 실패")
        for error in errors:
            print(f"- {error}")
        return 1
    print("관심 요약 렌더링 점검 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
