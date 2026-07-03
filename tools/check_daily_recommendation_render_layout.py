"""Headless layout check for the daily recommendation result board."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from smoke_research_console_clicks import CdpClient, assert_project_root, chrome_path, free_devtools_port, wait_for_page


DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=daily-recommendation-layout"


def run_layout_check(url: str, *, output_screenshot: Path | None = None) -> dict:
    assert_project_root()
    port = free_devtools_port()
    with tempfile.TemporaryDirectory(prefix="research-console-daily-layout-", ignore_cleanup_errors=True) as profile_dir:
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
                  const waitFor = async (predicate, timeout = 30000, label = "condition") => {
                    const started = Date.now();
                    while (Date.now() - started < timeout) {
                      const value = predicate();
                      if (value) return value;
                      await sleep(250);
                    }
                    throw new Error(`Timed out waiting for ${label}`);
                  };
                  const clippedTextElements = () => [...document.querySelectorAll(
                    "#dailyRecommendationCards article, #dailyRecommendationCards section, #dailyRecommendationCards header, " +
                    "#dailyRecommendationCards strong, #dailyRecommendationCards span, #dailyRecommendationCards small, " +
                    "#dailyRecommendationCards p, #dailyRecommendationCards b, #dailyRecommendationCards em, " +
                    "#dailyRecommendationCards button"
                  )]
                    .filter(visible)
                    .map((el) => {
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      const text = (el.textContent || "").replace(/\\s+/g, " ").trim();
                      const horizontalOverflow = el.scrollWidth > el.clientWidth + 2 && style.overflowX !== "visible";
                      const verticalOverflow = el.scrollHeight > el.clientHeight + 2 && style.overflowY !== "visible";
                      return {
                        selector: el.className || el.tagName.toLowerCase(),
                        text: text.slice(0, 120),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        clientWidth: el.clientWidth,
                        scrollWidth: el.scrollWidth,
                        clientHeight: el.clientHeight,
                        scrollHeight: el.scrollHeight,
                        horizontalOverflow,
                        verticalOverflow,
                      };
                    })
                    .filter((item) => item.text && (item.horizontalOverflow || item.verticalOverflow));

                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#statusButton") && document.querySelector("#dailyRecommendationsStatusButton"), 15000, "console controls");
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");
                  document.querySelector('button.tab[data-tab="storage"]')?.click();
                  await sleep(300);
                  document.querySelector("#dailyRecommendationsStatusButton").click();
                  await waitFor(() => {
                    const text = document.querySelector("#dailyRecommendationCards")?.innerText || "";
                    return text.includes("오늘의 추천 결과") && text.includes("한국 추천 1~3위") && text.includes("미국 추천 1~3위");
                  }, 60000, "daily recommendation cards");
                  await sleep(500);

                  const cardsRoot = document.querySelector("#dailyRecommendationCards");
                  cardsRoot.scrollIntoView({block: "start", inline: "nearest"});
                  await sleep(300);
                  const marketSections = [...cardsRoot.querySelectorAll(".daily-recommendation-market-section")].filter(visible);
                  const recommendationCards = [...cardsRoot.querySelectorAll(".daily-recommendation-market-grid > .daily-recommendation-card")].filter(visible);
                  const marketLabels = marketSections.map((section) => section.querySelector(".daily-recommendation-market-head span")?.textContent?.trim() || "");
                  const title = cardsRoot.querySelector(".daily-recommendation-board-summary strong")?.textContent?.trim() || "";
                  const cardsTop = Math.round(cardsRoot.getBoundingClientRect().top);
                  const topRankCard = document.querySelector(".daily-recommendation-top-rank[data-daily-recommendation-open]");
                  const topRankTicker = topRankCard?.dataset?.dailyRecommendationOpen || "";
                  const topRankMarket = topRankCard?.dataset?.dailyRecommendationMarket || "";
                  const topRankRank = topRankCard?.dataset?.dailyRecommendationRank || "";
                  let detailOpenedAfterTopRankClick = false;
                  let detailFocusedTicker = "";
                  let detailFocusedMarket = "";
                  let detailFocusedRank = "";
                  let detailTabActive = false;
                  if (topRankCard) {
                    topRankCard.click();
                    const openedCard = await waitFor(() => {
                      const selectorParts = [
                        topRankTicker ? `[data-daily-recommendation-ticker="${CSS.escape(topRankTicker)}"]` : "",
                        topRankMarket ? `[data-daily-recommendation-market="${CSS.escape(topRankMarket)}"]` : "",
                        topRankRank ? `[data-daily-recommendation-rank="${CSS.escape(topRankRank)}"]` : "",
                      ].filter(Boolean).join("");
                      const card = cardsRoot.querySelector(`.daily-recommendation-rank-card${selectorParts}`);
                      const detail = card?.querySelector(".daily-recommendation-detail");
                      return card && detail?.open ? card : null;
                    }, 15000, "opened daily recommendation detail");
                    detailOpenedAfterTopRankClick = true;
                    detailFocusedTicker = openedCard.dataset.dailyRecommendationTicker || "";
                    detailFocusedMarket = openedCard.dataset.dailyRecommendationMarket || "";
                    detailFocusedRank = openedCard.dataset.dailyRecommendationRank || "";
                    detailTabActive = document.querySelector('button.tab[data-tab="memory"]')?.classList.contains("active") || false;
                    cardsRoot.scrollIntoView({block: "start", inline: "nearest"});
                    await sleep(200);
                  }
                  return {
                    status: "success",
                    title,
                    marketSectionCount: marketSections.length,
                    recommendationCardCount: recommendationCards.length,
                    marketLabels,
                    topRankClickFound: Boolean(topRankCard),
                    topRankTicker,
                    topRankMarket,
                    topRankRank,
                    detailOpenedAfterTopRankClick,
                    detailFocusedTicker,
                    detailFocusedMarket,
                    detailFocusedRank,
                    detailTabActive,
                    scrolledToDailyRecommendationCards: cardsTop >= 0 && cardsTop < Math.round(window.innerHeight * 0.35),
                    dailyRecommendationCardsTop: cardsTop,
                    scrollY: Math.round(window.scrollY),
                    clippedTextElements: clippedTextElements().slice(0, 20),
                    bodyWidth: document.body.scrollWidth,
                    viewportWidth: window.innerWidth,
                    pageHasHorizontalOverflow: document.body.scrollWidth > window.innerWidth + 2,
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
    if int(result.get("marketSectionCount") or 0) < 2:
        errors.append("한국/미국 시장 섹션이 모두 렌더링되지 않았습니다.")
    if int(result.get("recommendationCardCount") or 0) < 6:
        errors.append("한국/미국 추천 카드 6개가 모두 렌더링되지 않았습니다.")
    labels = " ".join(result.get("marketLabels") or [])
    if "한국" not in labels or "미국" not in labels:
        errors.append("시장 섹션 라벨에 한국/미국이 모두 보이지 않습니다.")
    if result.get("pageHasHorizontalOverflow"):
        errors.append("페이지 전체에 가로 스크롤 오버플로가 있습니다.")
    if not result.get("scrolledToDailyRecommendationCards"):
        errors.append("추천 결과 스크린샷 대상이 카드 영역으로 스크롤되지 않았습니다.")
    if not result.get("topRankClickFound"):
        errors.append("상단 추천 후보 클릭 대상을 찾지 못했습니다.")
    if not result.get("detailOpenedAfterTopRankClick"):
        errors.append("상단 추천 후보 클릭 후 추천 상세 카드가 열리지 않았습니다.")
    if not result.get("detailTabActive"):
        errors.append("상단 추천 후보 클릭 후 추천 상세 탭으로 이동하지 않았습니다.")
    clipped = result.get("clippedTextElements") if isinstance(result.get("clippedTextElements"), list) else []
    if clipped:
        errors.append(f"추천 결과 텍스트 클리핑 {len(clipped)}개")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="오늘 추천 결과 카드 렌더링 레이아웃을 헤드리스 Chrome으로 점검합니다.")
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
        print(f"추천 결과 렌더링: {result.get('title') or '추천일 미확인'}")
        print(
            "시장 섹션/카드: "
            f"{int(result.get('marketSectionCount') or 0)}개 / "
            f"{int(result.get('recommendationCardCount') or 0)}개"
        )
        print(f"시장 라벨: {', '.join(result.get('marketLabels') or [])}")
        print(f"텍스트 클리핑: {len(result.get('clippedTextElements') or [])}개")
        if result.get("screenshot"):
            print(f"스크린샷: {result['screenshot']}")
    if args.strict and errors:
        print("추천 결과 렌더링 점검 실패")
        for error in errors:
            print(f"- {error}")
        return 1
    print("추천 결과 렌더링 점검 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
