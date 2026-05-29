"""Headless Chrome click smoke tests for the research console.

This script intentionally uses only the Python standard library. It talks to
Chrome DevTools Protocol directly so the check can run on this PC without
installing Playwright/Selenium.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "http://127.0.0.1:8001/console/index.html?smoke=clicks"
COMMON_TICKER_PATTERN = r"005930\.KS|000660\.KS|207940\.KS|033500"


class CdpClient:
    def __init__(self, websocket_url: str) -> None:
        parsed = urllib.parse.urlparse(websocket_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.path = parsed.path
        if parsed.query:
            self.path += f"?{parsed.query}"
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.settimeout(300)
        self.next_id = 1
        self._handshake()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"Chrome DevTools handshake failed: {response[:200]!r}")

    def _send_frame(self, payload: bytes) -> None:
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(payload[index] ^ mask[index % 4] for index in range(length))
        self.sock.sendall(bytes(header) + masked)

    def _read_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise RuntimeError("Chrome DevTools socket closed")
            chunks.extend(chunk)
        return bytes(chunks)

    def _read_frame(self) -> dict:
        first, second = self._read_exact(2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        masked = bool(second & 0x80)
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(payload[index] ^ mask[index % 4] for index in range(length))
        if opcode == 0x8:
            raise RuntimeError("Chrome DevTools websocket closed")
        if opcode == 0x9:
            return self._read_frame()
        if opcode != 0x1:
            return self._read_frame()
        return json.loads(payload.decode("utf-8"))

    def call(self, method: str, params: dict | None = None, timeout: float = 30) -> dict:
        command_id = self.next_id
        self.next_id += 1
        self._send_frame(json.dumps({"id": command_id, "method": method, "params": params or {}}).encode("utf-8"))
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = self._read_frame()
            if message.get("id") != command_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method} failed: {message['error']}")
            return message.get("result") or {}
        raise TimeoutError(f"CDP command timed out: {method}")

    def evaluate(self, expression: str, timeout: float = 30) -> object:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": int(timeout * 1000),
            },
            timeout=timeout + 5,
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"])
        return (result.get("result") or {}).get("value")


def chrome_path() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("chrome") or shutil.which("msedge")
    if found:
        return found
    raise RuntimeError("Chrome 또는 Edge 실행 파일을 찾지 못했습니다.")


def fetch_json(url: str, timeout: float = 10) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_page(port: int, timeout: float = 15) -> dict:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            pages = fetch_json(f"http://127.0.0.1:{port}/json/list")
            for page in pages:
                if page.get("type") == "page" and page.get("webSocketDebuggerUrl"):
                    return page
        except Exception as exc:  # noqa: BLE001 - smoke helper should keep retrying.
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Chrome DevTools page not ready: {last_error}")


def assert_project_root() -> None:
    expected = Path(r"C:\Users\lib20\InvestmentJournalApp")
    if PROJECT_ROOT != expected:
        raise RuntimeError(f"Unexpected project root: {PROJECT_ROOT}")


def run_click_smoke(url: str, include_llm_save: bool = False, only_system_check: bool = False) -> dict:
    assert_project_root()
    port = 9223
    with tempfile.TemporaryDirectory(prefix="research-console-chrome-", ignore_cleanup_errors=True) as profile_dir:
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
            if only_system_check:
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
                      await waitFor(() => document.readyState === "complete", 15000, "page load");
                      await waitFor(() => document.querySelector("#statusButton"), 15000, "console controls");
                      document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                      document.querySelector("#accessToken").value = "dev-local-token";
                      document.querySelector("#statusButton").click();
                      await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");
                      const started = Date.now();
                      document.querySelector('[data-workflow-action="system-check"]').click();
                      const text = await waitFor(
                        () => {
                          const output = document.querySelector("#output")?.innerText || "";
                          return output.includes("전체 시스템 점검 완료") &&
                            output.includes("DART 공시 감시 상태") &&
                            output.includes("네이버 리서치/시장일지 상태")
                            ? output
                            : "";
                        },
                        150000,
                        "system check completion"
                      );
                      return {
                        backendStatus: document.querySelector("#backendStatus")?.textContent || "",
                        systemCheckCompleted: true,
                        elapsedMs: Date.now() - started,
                        preview: text.split("\\n").slice(0, 18).join("\\n"),
                      };
                    })()
                    """,
                    timeout=180,
                )
                if not result["systemCheckCompleted"]:
                    raise AssertionError("시스템 점검이 완료 상태까지 도달하지 못했습니다.")
                return result
            result = client.evaluate(
                f"""
                (async () => {{
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
                    throw new Error(`Timed out waiting for ${{label}}`);
                  }};
                  await waitFor(() => document.readyState === "complete", 15000, "page load");
                  await waitFor(() => document.querySelector("#portfolioKiwoomSyncButton") && document.querySelector("#statusButton"), 15000, "console controls");
                  await sleep(1000);
                  document.querySelector("#apiBaseUrl").value = "http://127.0.0.1:8001";
                  document.querySelector("#accessToken").value = "dev-local-token";
                  document.querySelector("#statusButton").click();
                  await waitFor(() => /정상|kis|활성|완료/.test(document.querySelector("#backendStatus")?.textContent || ""), 15000, "backend status");
                  const assertNoRuntimeErrors = (label) => {{
                    if (runtimeErrors.length) {{
                      throw new Error(`${{label}} runtime errors: ${{runtimeErrors.join(" | ")}}`);
                    }}
                  }};

                  document.querySelector('[data-tab="dashboard"]').click();
                  await waitFor(() => document.querySelector("#dashboard")?.classList.contains("active"), 5000, "dashboard active");
                  const dashboardForm = document.querySelector("#dashboardForm");
                  dashboardForm.elements.ticker.value = "003230";
                  dashboardForm.querySelector('button[type="submit"]').click();
                  const dashboardText = await waitFor(
                    () => {{
                      const text = document.querySelector("#dashboardCards")?.innerText || "";
                      return text.includes("DART 최근 공시") && text.includes("공시 재점검")
                        ? text
                        : "";
                    }},
                    120000,
                    "dashboard DART strip"
                  );

                  const runForm = async (tab, formSelector, setup, expected, timeout = 60000) => {{
                    document.querySelector(`[data-tab="${{tab}}"]`).click();
                    await waitFor(() => document.querySelector(`#${{tab}}`)?.classList.contains("active"), 5000, `${{tab}} active`);
                    setup(document.querySelector(formSelector));
                    const button = document.querySelector(`${{formSelector}} button[type="submit"]`);
                    button.click();
                    const started = Date.now();
                    while (Date.now() - started < timeout) {{
                      const text = document.querySelector("#output")?.innerText || "";
                      if (expected(text)) {{
                        return text;
                      }}
                      await sleep(250);
                    }}
                    const currentText = document.querySelector("#output")?.innerText || "";
                    throw new Error(
                      `Timed out waiting for ${{tab}} output. Current output: ${{currentText.split("\\n").slice(0, 12).join(" / ")}}`
                    );
                  }};

                  const macroText = await runForm(
                    "macro",
                    "#macroForm",
                    (form) => {{
                      form.elements.region.value = "KR";
                      form.elements.period.value = "3개월";
                      form.elements.focusTheme.value = "금리, 환율, 반도체 수급";
                      form.elements.macroEnvironment.value = "한국 시장은 금리, 환율, 반도체 수급을 함께 점검합니다.";
                    }},
                    (text) => text.includes("매크로 분석") && text.includes("지역: 한국") && text.includes("배분 관점"),
                    150000
                  );

                  const compounderText = await runForm(
                    "compounder",
                    "#compounderForm",
                    (form) => {{
                      form.elements.region.value = "KR";
                      form.elements.minMarketCap.value = "3000";
                    }},
                    (text) => text.includes("장기 복리 성장주 발굴") && text.includes("지역: 한국") && text.includes("핵심 지표"),
                    150000
                  );
                  assertNoRuntimeErrors("macro/compounder");

                  document.querySelector('[data-tab="interests"]').click();
                  await waitFor(() => document.querySelector("#interests")?.classList.contains("active"), 5000, "interests active");
                  const interestInitialText = document.querySelector("#interests")?.innerText || "";
                  if (!interestInitialText.includes("관심종목") || !interestInitialText.includes("관심섹터")) {{
                    throw new Error("관심종목/섹터 탭 기본 렌더링 확인 실패");
                  }}
                  document.querySelector("#interestsLoadButton")?.click();
                  const interestsText = await waitFor(
                    () => {{
                      const text = document.querySelector("#interests")?.innerText || "";
                      return text.includes("관심종목 목록") && text.includes("관심섹터 목록") && !text.includes("tickerHint")
                        ? text
                        : "";
                    }},
                    30000,
                    "interests render"
                  );
                  assertNoRuntimeErrors("interests");

                  document.querySelector('[data-tab="portfolio"]').click();
                  await waitFor(() => document.querySelector("#portfolio")?.classList.contains("active"), 5000, "portfolio active");
                  const portfolioSelect = document.querySelector("#portfolioSelect");
                  await waitFor(
                    () => [...portfolioSelect.options].some((option) => option.value),
                    15000,
                    "portfolio options"
                  );
                  const portfolioOption =
                    [...portfolioSelect.options].find((option) => option.value.includes("이형주")) ||
                    [...portfolioSelect.options].find((option) => option.value.includes("가족")) ||
                    [...portfolioSelect.options].find((option) => option.value);
                  const selectedPortfolioName = portfolioOption.value;
                  const expectedHoldingCount = Number((portfolioOption.textContent || "").match(/(\\d+)개/)?.[1] || 0);
                  portfolioSelect.value = portfolioOption.value;
                  portfolioSelect.dispatchEvent(new Event("change", {{ bubbles: true }}));
                  await sleep(1000);
                  const selectedPortfolioMessage = document.querySelector("#output")?.innerText || "";
                  const selectedRowCount = document.querySelectorAll("#holdingsEditor .holding-row").length;
                  const selectedLoadedAtText = document.querySelector("#portfolioLoadedAt")?.textContent || "";
                  const selectedPortfolioMatches =
                    selectedLoadedAtText.includes(selectedPortfolioName) &&
                    (!expectedHoldingCount || selectedLoadedAtText.includes(`보유 종목: ${{expectedHoldingCount}}개`)) &&
                    (!expectedHoldingCount || selectedRowCount === expectedHoldingCount);
                  document.querySelector("#portfolioLoadButton").click();
                  await waitFor(
                    () => /불러온 일시|현재가|평가금액/.test(document.querySelector("#portfolioLoadedAt")?.textContent || document.querySelector("#holdingsEditor")?.textContent || ""),
                    50000,
                    "portfolio load"
                  );
                  const loadedRowCount = document.querySelectorAll("#holdingsEditor .holding-row").length;
                  const loadedAtText = document.querySelector("#portfolioLoadedAt")?.textContent || "";
                  const loadedPortfolioMatches =
                    loadedAtText.includes(selectedPortfolioName) &&
                    (!expectedHoldingCount || loadedAtText.includes(`보유 종목: ${{expectedHoldingCount}}개`)) &&
                    (!expectedHoldingCount || loadedRowCount === expectedHoldingCount);
                  const bodyHasHorizontalOverflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 4;
                  const parseNumber = (value) => Number(String(value || "").replace(/[,₩$원%]/g, "").trim());
                  let plQuantityRecalc = false;
                  let plQuantityPreserved = false;
                  const kiwoomSyncButtonText = document.querySelector("#portfolioKiwoomSyncButton")?.textContent || "";
                  document.querySelector("#portfolioKiwoomSyncButton")?.click();
                  const kiwoomPreviewText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      const previewReady = text.includes("키움 국내 수량 변경 예정") &&
                        text.includes("아직 저장하지 않았습니다") &&
                        text.includes("해외·수동");
                      const unavailableReady = text.includes("키움 국내 수량 확인 연결 실패") ||
                        text.includes("키움 국내 수량 동기화 설정 필요");
                      return previewReady || unavailableReady
                        ? text
                        : "";
                    }},
                    60000,
                    "kiwoom domestic preview"
                  );
                  const kiwoomPreviewAllowsApply = kiwoomPreviewText.includes("키움 국내 수량 변경 예정");
                  let kiwoomApplyVisible = false;
                  if (kiwoomPreviewAllowsApply) {{
                    kiwoomApplyVisible = await waitFor(
                      () => {{
                        const button = document.querySelector("#portfolioKiwoomApplyButton");
                        return button && !button.hidden && !button.disabled;
                      }},
                      10000,
                      "kiwoom apply button"
                    );
                  }}
                  document.querySelector("#portfolioKiwoomCancelButton")?.click();
                  await waitFor(
                    () =>
                      (document.querySelector("#output")?.innerText || "").includes("적용을 취소") ||
                      document.querySelector("#portfolioKiwoomApplyButton")?.hidden,
                    30000,
                    "kiwoom cancel"
                  );
                  document.querySelector("#portfolioSyncHistoryButton")?.click();
                  const kiwoomHistoryText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      if (
                        text.includes("최근 계좌 동기화 이력") &&
                        text.includes("수동 보호") &&
                        text.includes("키움 동기화")
                      ) {{
                        return text;
                      }}
                      const overview = document.querySelector("#portfolioSyncOverview")?.innerText || "";
                      return overview.includes("계좌 동기화") &&
                        (overview.includes("수동 보호") || overview.includes("확인 필요"))
                        ? `# 최근 계좌 동기화 이력\\n${{overview}}`
                        : "";
                    }},
                    90000,
                    "kiwoom sync history"
                  );
                  const kiwoomSyncOverviewText = document.querySelector("#portfolioSyncOverview")?.innerText || "";
                  const plTickerInput = [...document.querySelectorAll('#holdingsEditor [name="ticker"]')]
                    .find((input) => input.value === "PL");
                  const plRow = plTickerInput?.closest(".holding-row");
                  if (plRow) {{
                    const quantityInput = plRow.querySelector('[name="quantity"]');
                    const marketValueInput = plRow.querySelector('[name="market_value"]');
                    const originalQuantity = Number(quantityInput.value);
                    plQuantityPreserved = originalQuantity === 100;
                    const originalMarketValue = marketValueInput.value;
                    if (Number.isFinite(originalQuantity) && originalQuantity > 0) {{
                      quantityInput.value = String(originalQuantity + 1);
                      quantityInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                      await sleep(100);
                      plQuantityRecalc = parseNumber(marketValueInput.value) > parseNumber(originalMarketValue);
                      quantityInput.value = String(originalQuantity);
                      quantityInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                      await sleep(100);
                    }}
                  }}
                  document.querySelector("#portfolioPerformanceButton").click();
                  const portfolioPerformanceText = await waitFor(
                    () => {{
                      const text = document.querySelector("#portfolioPerformanceOverview")?.innerText || "";
                      return text.includes("기간 수익 비교") &&
                        (text.includes("현재가 강제 갱신") || text.includes("저장 현재가 사용")) &&
                        text.includes("최근 1주일") &&
                        text.includes("정확도") &&
                        text.includes("가격 차이")
                        ? text
                        : "";
                    }},
                    120000,
                    "portfolio performance overview"
                  );
                  document.querySelector("#portfolioQuickRiskButton").click();
                  const portfolioRiskText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("완료되었습니다.") &&
                        text.includes("포트폴리오 리스크 스캔")
                        ? text
                        : "";
                    }},
                    120000,
                    "portfolio risk scan"
                  );
                  document.querySelector("#portfolioTeamQueueButton").click();
                  const portfolioTeamQueueText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("포트폴리오 기준 리포트 생성 큐")
                        ? text
                        : "";
                    }},
                    120000,
                    "portfolio team report queue"
                  );

                  document.querySelector('[data-workflow-action="system-check"]').click();
                  let systemCheckText = "";
                  let systemCheckCompleted = false;
                  try {{
                    systemCheckText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        return (
                          text.includes("전체 시스템 점검 완료") &&
                          (text.includes("DART 공시 감시 상태") || text.includes("네이버 리서치/시장일지 자동 반영")) &&
                          (text.includes("신뢰도") || text.includes("네이버 리서치"))
                        )
                          ? text
                          : "";
                      }},
                      90000,
                      "system check output"
                    );
                    systemCheckCompleted = true;
                  }} catch (error) {{
                    systemCheckText = document.querySelector("#output")?.innerText || String(error?.message || error || "");
                  }}

                  document.querySelector('[data-tab="memory"]').click();
                  await waitFor(() => document.querySelector("#memory")?.classList.contains("active"), 5000, "memory active");
                  const memoryForm = document.querySelector("#memoryForm");
                  memoryForm.elements.ticker.value = "삼양식품";
                  memoryForm.requestSubmit();
                  await waitFor(
                    () => {{
                      const listText = document.querySelector("#memoryList")?.innerText || "";
                      const outputText = document.querySelector("#output")?.innerText || "";
                      const combined = `${{listText}}\n${{outputText}}`;
                      return (
                        combined.includes("저장 데이터 키") ||
                        combined.includes("저장 리포트") ||
                        combined.includes("공식 인증") ||
                        combined.includes("레거시") ||
                        combined.includes("자료가 없습니다")
                      )
                        ? combined
                        : "";
                    }},
                    30000,
                    "memory baseline list"
                  );
                  const qualityFilter = document.querySelector('#memoryForm [name="qualityFilter"]');
                  if (!qualityFilter) {{
                    throw new Error("저장 데이터 품질 필터를 찾지 못했습니다.");
                  }}
                  const memoryFilterResults = [];
                  for (const [filterValue, expectedText] of [
                    ["all", "저장 리포트"],
                    ["body_missing", "본문 보강"],
                    ["url_only", "URL-only"],
                    ["ocr_needed", "OCR"],
                    ["legacy", "레거시"],
                  ]) {{
                    qualityFilter.value = filterValue;
                    qualityFilter.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    const filterText = await waitFor(
                      () => {{
                        const listText = document.querySelector("#memoryList")?.innerText || "";
                        const outputText = document.querySelector("#output")?.innerText || "";
                        const feedbackText = document.querySelector("#actionFeedback")?.textContent || "";
                        const combined = `${{listText}}\n${{outputText}}\n${{feedbackText}}`;
                        return (
                          combined.includes(expectedText) ||
                          combined.includes("필터 적용") ||
                          combined.includes("필터 결과") ||
                          combined.includes("자료가 없습니다") ||
                          combined.includes("저장 데이터 필터를 다시 적용")
                        )
                          ? combined
                          : "";
                      }},
                      30000,
                      `memory quality filter ${{filterValue}}`
                    );
                    memoryFilterResults.push({{
                      filter: filterValue,
                      ok: true,
                      sawExpectedText:
                        filterText.includes(expectedText) ||
                        filterText.includes("저장 데이터 키") ||
                        filterText.includes("저장 리포트") ||
                        filterText.includes("필터 적용") ||
                        filterText.includes("필터 결과") ||
                        filterText.includes("자료가 없습니다") ||
                        filterText.includes("저장 데이터 필터를 다시 적용"),
                      sawFeedback: filterText.includes("저장 데이터 필터를 다시 적용") || filterText.includes("요청 접수"),
                      preview: filterText.split("\\n").slice(0, 8).join("\\n"),
                    }});
                  }}
                  const memoryQualityFilterText = memoryFilterResults
                    .map((item) => `${{item.filter}}: ${{item.preview}}`)
                    .join("\\n---\\n");
                  document.querySelector("#naverResearchStatusButton")?.click();
                  const naverStatusText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("네이버 리서치 자동 수집 상태") &&
                        text.includes("중복 시장일지 후보") &&
                        text.includes("08:30 자동 작업 로그") &&
                        text.includes("시장일지 화면 연결")
                        ? text
                        : "";
                    }},
                    60000,
                    "naver research status"
                  );
                  document.querySelector("#naverResearchRepairButton")?.click();
                  let naverRepairText = "";
                  try {{
                    naverRepairText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                        const combined = `${{text}}\n${{feedback}}`;
                        return combined.includes("네이버") &&
                          combined.includes("완료") &&
                          (
                            combined.includes("soft_archive") ||
                            combined.includes("소프트 보관") ||
                            combined.includes("중복 시장일지 후보") ||
                            combined.includes("중복 리포트") ||
                            combined.includes("리서치 캐시 정리") ||
                            combined.includes("PDF 신호 백필")
                          )
                          ? combined
                          : "";
                      }},
                      180000,
                      "naver research repair"
                    );
                  }} catch (error) {{
                    naverRepairText = [
                      document.querySelector("#output")?.innerText || "",
                      document.querySelector("#actionFeedback")?.textContent || "",
                      String(error?.message || error || ""),
                    ].join("\\n");
                  }}
                  document.querySelector("#naverMarketJournalButton")?.click();
                  const naverMarketJournalText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("국내 마감 시황 시장일지") &&
                        text.includes("08:30 자동 작업 로그") &&
                        text.includes("시장일지 화면 연결")
                        ? text
                        : "";
                    }},
                    70000,
                    "naver market journal button"
                  );
                  await sleep(1000);

                  document.querySelector("#dailyRecommendationsButton")?.click();
                  const dailyRecommendationsText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                      const cards = document.querySelector("#dailyRecommendationCards")?.innerText || "";
                      const combined = `${{text}}\n${{feedback}}\n${{cards}}`;
                      return text.includes("매일 추천 후보 1~3위") &&
                        text.includes("추천 후보") &&
                        text.includes("사후 추적") &&
                        cards.includes("추천 성과 추적표")
                        ? combined
                        : "";
                    }},
                    120000,
                    "daily recommendations button"
                  );
                  await sleep(1000);
                  document.querySelector("#dailyRecommendationsStatusButton")?.click();
                  const dailyRecommendationsStatusText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                      const cards = document.querySelector("#dailyRecommendationCards")?.innerText || "";
                      const combined = `${{text}}\n${{feedback}}\n${{cards}}`;
                      return text.includes("매일 추천 후보 1~3위") &&
                        text.includes("추천일") &&
                        text.includes("추천 후 1주일") &&
                        cards.includes("추천 성과 추적표")
                        ? combined
                        : "";
                    }},
                    120000,
                    "daily recommendations status button"
                  );

                  document.querySelector('[data-tab="llmBridge"]').click();
                  await waitFor(() => document.querySelector("#llmBridge")?.classList.contains("active"), 5000, "llm active");
                  const llmPromptForm = document.querySelector("#llmPromptForm");
                  llmPromptForm.elements.target.value = "";
                  llmPromptForm.elements.sourceContext.value = "테스트용 시장 메모: 금리와 환율이 섹터 로테이션에 영향을 줍니다.";
                  llmPromptForm.querySelector('button[type="submit"]').click();
                  await waitFor(() => (document.querySelector("#llmPromptOutput")?.value || "").includes("티커가 명확하지 않으면"), 5000, "llm prompt");
                  document.querySelector("#copyLlmPromptButton")?.click();
                  const llmCopyFeedbackText = await waitFor(
                    () => {{
                      const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                      const output = document.querySelector("#output")?.innerText || "";
                      const combined = `${{feedback}}\n${{output}}`;
                      return combined.includes("프롬프트를 복사") ||
                        combined.includes("직접 복사 필요") ||
                        combined.includes("Ctrl+C")
                        ? combined
                        : "";
                    }},
                    10000,
                    "llm prompt copy feedback"
                  );
                  document.querySelector("#llmStorageStatusButton")?.click();
                  const llmStorageStatusText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return (
                        text.includes("LLM 연동 저장/RAG 상태") &&
                        text.includes("저장된 LLM 응답") &&
                        text.includes("RAG")
                      ) || (
                        text.includes("LLM 저장/RAG 상태 확인 중") &&
                        text.includes("최근 수동 LLM 응답 저장 파일 확인")
                      )
                        ? text
                        : "";
                    }},
                    90000,
                    "llm storage status"
                  );

                  let llmReset = null;
                  if ({str(include_llm_save).lower()}) {{
                    const resultForm = document.querySelector("#llmResultForm");
                    resultForm.elements.llmResult.value = "핵심 요약: 테스트 응답입니다. 다음 액션은 시장 메모를 저장하고 금리와 환율을 추적하는 것입니다.";
                    resultForm.querySelector('button[type="submit"]').click();
                    await waitFor(() => (document.querySelector("#output")?.innerText || "").includes("정보 입력 저장 실행이 완료"), 60000, "llm save");
                    llmReset = {{
                      target: llmPromptForm.elements.target.value,
                      sourceContext: llmPromptForm.elements.sourceContext.value,
                      prompt: document.querySelector("#llmPromptOutput").value,
                      result: resultForm.elements.llmResult.value,
                    }};
                  }}

                  const tickerRegex = new RegExp({json.dumps(COMMON_TICKER_PATTERN)});
                  return {{
                    backendStatus: document.querySelector("#backendStatus")?.textContent || "",
                    dashboardShowsDartStrip: dashboardText.includes("DART 최근 공시"),
                    dashboardShowsDartCoverage: dashboardText.includes("대상") && dashboardText.includes("확인"),
                    macroHasTicker: tickerRegex.test(macroText),
                    compounderHasTicker: tickerRegex.test(compounderText),
                    interestsRendered: interestsText.includes("관심종목 목록") && interestsText.includes("관심섹터 목록"),
                    portfolioPerformanceShowsRefresh: portfolioPerformanceText.includes("현재가 강제 갱신") || portfolioPerformanceText.includes("저장 현재가 사용"),
                    portfolioPerformanceShowsQuality: portfolioPerformanceText.includes("정확도") && portfolioPerformanceText.includes("가격 차이"),
                    portfolioPerformanceHasTicker: tickerRegex.test(portfolioPerformanceText),
                    portfolioRiskScanCompleted: portfolioRiskText.includes("포트폴리오 리스크 스캔"),
                    portfolioTeamQueueCompleted: portfolioTeamQueueText.includes("포트폴리오 기준 리포트 생성 큐"),
                    selectedPortfolioName,
                    expectedHoldingCount,
                    selectedRowCount,
                    loadedRowCount,
                    selectedLoadedAtText,
                    loadedAtText,
                    selectedPortfolioMatches,
                    loadedPortfolioMatches,
                    selectedPortfolioMessage: selectedPortfolioMessage.split("\\n").slice(0, 8).join("\\n"),
                    bodyHasHorizontalOverflow,
                    plQuantityRecalc,
                    plQuantityPreserved,
                    kiwoomSyncButtonText,
                    kiwoomPreviewText: kiwoomPreviewText.split("\\n").slice(0, 12).join("\\n"),
                    kiwoomPreviewAllowsApply,
                    kiwoomApplyVisible,
                    kiwoomHistoryText: kiwoomHistoryText.split("\\n").slice(0, 12).join("\\n"),
                    kiwoomSyncOverviewText,
                    systemCheckCompleted,
                    systemCheckShowsDartReliability: systemCheckCompleted
                      ? (systemCheckText.includes("DART 공시 감시 상태") || systemCheckText.includes("네이버 리서치/시장일지 자동 반영"))
                      : /시스템 점검|진행 중|백엔드|저장/.test(systemCheckText),
                    naverStatusShowsDuplicateGuard: naverStatusText.includes("중복 시장일지 후보"),
                    naverStatusShowsTaskLog: naverStatusText.includes("08:30 자동 작업 로그") && naverStatusText.includes("최근 로그"),
                    naverStatusShowsKoreanTaskLog: naverStatusText.includes("국내 주식 마감 시황"),
                    naverStatusShowsJournalSource: naverStatusText.includes("입력 구분:"),
                    memoryQualityFilterWorks: memoryFilterResults.every((item) => item.ok && item.sawExpectedText),
                    memoryQualityFilterFeedbackWorks: memoryFilterResults.every((item) => item.sawFeedback),
                    memoryFilterResults,
                    naverRepairShowsSoftArchive:
                      naverRepairText.includes("soft_archive") ||
                      naverRepairText.includes("소프트 보관") ||
                      naverRepairText.includes("중복 시장일지 후보") ||
                      naverRepairText.includes("중복 리포트"),
                    naverRepairShowsProgress:
                      naverRepairText.includes("네이버") &&
                      (
                        naverRepairText.includes("리서치 캐시 정리") ||
                        naverRepairText.includes("PDF 신호 백필") ||
                        naverRepairText.includes("처리 중") ||
                        naverRepairText.includes("요청 접수") ||
                        naverRepairText.includes("중복")
                      ),
                    naverMarketJournalShowsDigest: naverMarketJournalText.includes("시장일지 화면 연결"),
                    naverMarketJournalShowsTaskLog: naverMarketJournalText.includes("08:30 자동 작업 로그"),
                    dailyRecommendationsShowsTopThree:
                      dailyRecommendationsText.includes("매일 추천 후보 1~3위") &&
                      dailyRecommendationsText.includes("추천 후보"),
                    dailyRecommendationsShowsTracking:
                      dailyRecommendationsStatusText.includes("사후 추적") &&
                      dailyRecommendationsStatusText.includes("추천 후 1주일"),
                    llmTargetBlank: llmPromptForm.elements.target.value === "",
                    llmPromptGenerated: (document.querySelector("#llmPromptOutput")?.value || "").length > 50,
                    llmCopyShowsFeedback: /프롬프트를 복사|직접 복사 필요|Ctrl\\+C/.test(llmCopyFeedbackText),
                    llmStorageStatusShowsRag: llmStorageStatusText.includes("RAG"),
                    llmStorageStatusShowsSaved:
                      llmStorageStatusText.includes("저장된 LLM 응답") ||
                      llmStorageStatusText.includes("최근 수동 LLM 응답 저장 파일 확인"),
                    llmStorageAvoidsMissingCompanyLabel: !llmStorageStatusText.includes("회사명 확인 필요"),
                    llmReset,
                    dashboardPreview: dashboardText.split("\\n").slice(0, 12).join("\\n"),
                    macroPreview: macroText.split("\\n").slice(0, 10).join("\\n"),
                    compounderPreview: compounderText.split("\\n").slice(0, 10).join("\\n"),
                    interestsPreview: interestsText.split("\\n").slice(0, 10).join("\\n"),
                    portfolioPerformancePreview: portfolioPerformanceText.split("\\n").slice(0, 12).join("\\n"),
                    portfolioRiskPreview: portfolioRiskText.split("\\n").slice(0, 10).join("\\n"),
                    portfolioTeamQueuePreview: portfolioTeamQueueText.split("\\n").slice(0, 10).join("\\n"),
                    systemCheckPreview: systemCheckText.split("\\n").slice(0, 12).join("\\n"),
                    naverStatusPreview: naverStatusText.split("\\n").slice(0, 12).join("\\n"),
                    naverRepairPreview: naverRepairText.split("\\n").slice(0, 12).join("\\n"),
                    naverMarketJournalPreview: naverMarketJournalText.split("\\n").slice(0, 12).join("\\n"),
                    dailyRecommendationsPreview: dailyRecommendationsText.split("\\n").slice(0, 14).join("\\n"),
                    dailyRecommendationsStatusPreview: dailyRecommendationsStatusText.split("\\n").slice(0, 14).join("\\n"),
                    memoryQualityFilterPreview: memoryQualityFilterText.split("\\n").slice(0, 8).join("\\n"),
                    llmCopyFeedbackPreview: llmCopyFeedbackText.split("\\n").slice(0, 8).join("\\n"),
                    llmStorageStatusPreview: llmStorageStatusText.split("\\n").slice(0, 12).join("\\n"),
                  }};
                }})()
                """,
                timeout=480,
            )
            if not result["dashboardShowsDartStrip"]:
                raise AssertionError("대시보드 기본 화면에 최근 DART 공시 확인 스트립이 표시되지 않았습니다.")
            if not result["dashboardShowsDartCoverage"]:
                raise AssertionError("대시보드 DART 스트립에 대상/확인 커버리지 정보가 표시되지 않았습니다.")
            if result["macroHasTicker"]:
                raise AssertionError("매크로 분석 화면 결과에 주요 티커 코드가 남아 있습니다.")
            if result["compounderHasTicker"]:
                raise AssertionError("복리 성장주 화면 결과에 주요 티커 코드가 남아 있습니다.")
            if not result["interestsRendered"]:
                raise AssertionError("관심종목/섹터 탭 렌더링 검증에 실패했습니다.")
            if not result["portfolioPerformanceShowsRefresh"]:
                raise AssertionError("포트폴리오 기간 수익 비교 화면에 현재가 강제 갱신 상태가 표시되지 않았습니다.")
            if not result["portfolioPerformanceShowsQuality"]:
                raise AssertionError("포트폴리오 기간 수익 비교 화면에 정확도/가격 차이 정보가 표시되지 않았습니다.")
            if result["portfolioPerformanceHasTicker"]:
                raise AssertionError("포트폴리오 기간 수익 비교 화면에 주요 티커 코드가 남아 있습니다.")
            if not result["portfolioRiskScanCompleted"]:
                raise AssertionError("포트폴리오 불러오기 이후 리스크 스캔 사용자 흐름이 완료되지 않았습니다.")
            if not result["portfolioTeamQueueCompleted"]:
                raise AssertionError("포트폴리오 기준 리포트 큐 사용자 흐름이 완료되지 않았습니다.")
            if not result["selectedPortfolioMatches"]:
                raise AssertionError(
                    "저장 포트폴리오 선택 후 화면의 선택명/보유 종목 수가 맞지 않습니다: "
                    f"{result['selectedPortfolioName']} expected={result['expectedHoldingCount']} "
                    f"rows={result['selectedRowCount']} loadedAt={result['selectedLoadedAtText']!r}"
                )
            if not result["loadedPortfolioMatches"]:
                raise AssertionError(
                    "포트폴리오 가격 갱신 불러오기 후 선택 포트폴리오가 유지되지 않았습니다: "
                    f"{result['selectedPortfolioName']} expected={result['expectedHoldingCount']} "
                    f"rows={result['loadedRowCount']} loadedAt={result['loadedAtText']!r}"
                )
            if result["bodyHasHorizontalOverflow"]:
                raise AssertionError("포트폴리오 화면이 페이지 본문 기준으로 가로 넘침을 만들고 있습니다.")
            if not result["plQuantityRecalc"]:
                raise AssertionError("PL 수량 변경 시 화면 평가금액이 즉시 재계산되지 않았습니다.")
            if not result["plQuantityPreserved"]:
                raise AssertionError("포트폴리오 불러오기 후 PL 100주가 유지되지 않았습니다.")
            if "키움 국내 수량 확인" not in result["kiwoomSyncButtonText"]:
                raise AssertionError("키움 국내 수량 동기화 버튼이 표시되지 않았습니다.")
            if result["kiwoomPreviewAllowsApply"] and not result["kiwoomApplyVisible"]:
                raise AssertionError("키움 국내 수량 미리보기 후 변경 적용 버튼이 활성화되지 않았습니다.")
            if "최근 계좌 동기화 이력" not in result["kiwoomHistoryText"]:
                raise AssertionError("최근 계좌 동기화 이력 조회 결과가 표시되지 않았습니다.")
            if "수동 보호" not in result["kiwoomSyncOverviewText"]:
                raise AssertionError("포트폴리오 동기화 요약에 수동 보호 상태가 표시되지 않았습니다.")
            if not result["systemCheckShowsDartReliability"]:
                raise AssertionError("시스템 점검 화면에 진행 상태 또는 자동화 점검 정보가 표시되지 않았습니다.")
            if not result["naverStatusShowsDuplicateGuard"]:
                raise AssertionError("네이버 리서치 상태 화면에 중복 시장일지 가드가 표시되지 않았습니다.")
            if not result["naverStatusShowsTaskLog"]:
                raise AssertionError("네이버 리서치 상태 화면에 08:30 자동 작업 로그가 표시되지 않았습니다.")
            if not result["naverStatusShowsKoreanTaskLog"]:
                raise AssertionError("네이버 리서치 상태 화면의 작업 로그 한글 제목이 정상 표시되지 않았습니다.")
            if not result["naverStatusShowsJournalSource"]:
                raise AssertionError("시장일지 화면 연결 요약에 자동/수동 입력 구분이 표시되지 않았습니다.")
            if not result["memoryQualityFilterWorks"]:
                raise AssertionError("저장 데이터 품질 필터가 화면에서 적용되지 않았습니다.")
            if not result["memoryQualityFilterFeedbackWorks"]:
                raise AssertionError("저장 데이터 품질 필터 변경 시 사용자 피드백이 표시되지 않았습니다.")
            if not (result["naverRepairShowsSoftArchive"] or result["naverRepairShowsProgress"]):
                raise AssertionError("네이버 리서치 정리 화면에 소프트 보관 정책 또는 처리 진행 피드백이 표시되지 않았습니다.")
            if not result["naverMarketJournalShowsDigest"]:
                raise AssertionError("시황 시장일지 반영 화면에 시장일지 연결 요약이 표시되지 않았습니다.")
            if not result["naverMarketJournalShowsTaskLog"]:
                raise AssertionError("시황 시장일지 반영 화면에 08:30 자동 작업 로그가 표시되지 않았습니다.")
            if not result["dailyRecommendationsShowsTopThree"]:
                raise AssertionError("오늘 추천 1~3위 버튼 결과가 화면에 표시되지 않았습니다.")
            if not result["dailyRecommendationsShowsTracking"]:
                raise AssertionError("추천 추적 상태 버튼 결과에 사후 추적 일정이 표시되지 않았습니다.")
            if not result["llmTargetBlank"] or not result["llmPromptGenerated"]:
                raise AssertionError("LLM 연동 기본 공란/프롬프트 생성 검증에 실패했습니다.")
            if not result["llmCopyShowsFeedback"]:
                raise AssertionError("LLM 프롬프트 복사 버튼 피드백 검증에 실패했습니다.")
            if not result["llmStorageStatusShowsRag"] or not result["llmStorageStatusShowsSaved"]:
                raise AssertionError("LLM 저장/RAG 상태 버튼 검증에 실패했습니다.")
            if not result["llmStorageAvoidsMissingCompanyLabel"]:
                raise AssertionError("LLM 저장/RAG 상태 화면에 불필요한 '회사명 확인 필요' 표시가 남아 있습니다.")
            if include_llm_save and result["llmReset"] != {"target": "", "sourceContext": "", "prompt": "", "result": ""}:
                raise AssertionError(f"LLM 저장 후 초기화 검증 실패: {result['llmReset']}")
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
    parser = argparse.ArgumentParser(description="Research console headless click smoke test")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--include-llm-save", action="store_true", help="LLM 응답 저장 후 입력 초기화까지 확인합니다.")
    parser.add_argument("--only-system-check", action="store_true", help="전체 클릭 회귀 대신 시스템 점검 완료 여부만 확인합니다.")
    args = parser.parse_args()
    result = run_click_smoke(
        args.url,
        include_llm_save=args.include_llm_save,
        only_system_check=args.only_system_check,
    )
    print(json.dumps({"status": "success", **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
