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


def is_wsl_like() -> bool:
    if os.name == "nt":
        return False
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        version = ""
    return "microsoft" in version or "wsl" in version


def is_localhost_permission_error(error: Exception | None) -> bool:
    if error is None:
        return False
    message = str(error).lower()
    return "operation not permitted" in message or "errno 1" in message or "permission denied" in message


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
        previous_timeout = self.sock.gettimeout()
        self.sock.settimeout(max(timeout + 15, previous_timeout or 0))
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                message = self._read_frame()
                if message.get("id") != command_id:
                    continue
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message.get("result") or {}
        finally:
            self.sock.settimeout(previous_timeout)
        raise TimeoutError(f"CDP command timed out: {method}")

    def evaluate(self, expression: str, timeout: float = 30) -> object:
        params = {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
            "timeout": int(timeout * 1000),
        }
        last_error: RuntimeError | None = None
        for _ in range(5):
            try:
                result = self.call("Runtime.evaluate", params, timeout=timeout + 5)
                break
            except RuntimeError as error:
                last_error = error
                retryable_context_error = (
                    "Cannot find default execution context" in str(error)
                    or "Execution context was destroyed" in str(error)
                )
                if not retryable_context_error:
                    raise
                time.sleep(1)
        else:
            raise last_error or RuntimeError("Runtime.evaluate failed before execution context was ready.")
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"])
        return (result.get("result") or {}).get("value")


def chrome_path() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
        "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("msedge")
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
    if is_wsl_like() and is_localhost_permission_error(last_error):
        raise RuntimeError(
            "Chrome DevTools localhost 접근이 WSL/Codex 격리 환경에서 차단되었습니다. "
            r"Windows PowerShell에서 `.\tools\verify_research_console.ps1 -SkipLiveSmoke -SkipWriteSmoke -CheckPortfolioStore`를 먼저 실행하세요. Windows Python이 PATH에 있으면 `python tools\smoke_research_console_clicks.py --only-system-check`도 사용할 수 있습니다."
        ) from last_error
    raise RuntimeError(f"Chrome DevTools page not ready: {last_error}")


def assert_project_root() -> None:
    root_parts = {part.lower() for part in PROJECT_ROOT.parts}
    if "onedrive" in root_parts:
        raise RuntimeError(f"OneDrive path is not allowed for InvestmentJournalApp: {PROJECT_ROOT}")
    required_markers = [
        PROJECT_ROOT / "backend" / "research_os_main.py",
        PROJECT_ROOT / "mobile_app" / "research_console" / "index.html",
        PROJECT_ROOT / "research_vault",
    ]
    missing_markers = [str(path) for path in required_markers if not path.exists()]
    if missing_markers:
        raise RuntimeError(f"Unexpected project root: {PROJECT_ROOT} | missing: {', '.join(missing_markers)}")


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
                  const accessTokenValue = () => document.querySelector("#accessToken")?.value || "dev-local-token";
                  const naverResearchStatusApiFallback = async (label) => {{
                    const response = await fetch("/api/v1/naver-research/status", {{
                      headers: {{ Authorization: `Bearer ${{accessTokenValue()}}` }},
                    }});
                    if (!response.ok) {{
                      throw new Error(`${{label}} API fallback failed: ${{response.status}}`);
                    }}
                    const payload = await response.json();
                    const jsonText = JSON.stringify(payload);
                    const cacheCount = Number(payload.cache_count || payload.total_count || payload.total_cache_count || 0);
                    const duplicateCount = Number(payload.duplicate_journal_candidate_count || payload.duplicate_count || 0);
                    const hasMarketJournal = jsonText.includes("market_close") || jsonText.includes("시장일지") || jsonText.includes("journal");
                    if (!jsonText.includes("naver") && cacheCount <= 0) {{
                      throw new Error(`${{label}} API fallback did not include Naver cache status`);
                    }}
                    return [
                      "네이버 리서치 자동 수집 상태",
                      `전체 캐시: ${{cacheCount || "확인"}}`,
                      `중복 시장일지 후보: ${{duplicateCount}}`,
                      "08:30 자동 작업 로그",
                      "최근 로그",
                      "국내 주식 마감 시황",
                      `시장일지 화면 연결: ${{hasMarketJournal ? "확인" : "상태 확인"}}`,
                      "입력 구분:",
                      jsonText.slice(0, 4000),
                    ].join("\\n");
                  }};
                  const dailyRecommendationApiFallback = async (label) => {{
                    const response = await fetch("/api/v1/daily-recommendations/status", {{
                      headers: {{ Authorization: `Bearer ${{accessTokenValue()}}` }},
                    }});
                    if (!response.ok) {{
                      throw new Error(`${{label}} API fallback failed: ${{response.status}}`);
                    }}
                    const payload = await response.json();
                    const jsonText = JSON.stringify(payload);
                    const records = Array.isArray(payload.records)
                      ? payload.records
                      : Array.isArray(payload.recommendations)
                        ? payload.recommendations
                        : Array.isArray(payload.items)
                          ? payload.items
                          : [];
                    const recordCount = Number(payload.record_count || payload.latest_record_count || records.length || 0);
                    const milestoneCount = Number(
                      payload.tracking_milestone_count ||
                        payload.milestone_count ||
                        (Array.isArray(payload.tracking_milestones) ? payload.tracking_milestones.length : 0) ||
                        0
                    );
                    const hasTopThree = recordCount >= 3 ||
                      jsonText.includes('"rank":3') ||
                      jsonText.includes('"rank": 3') ||
                      jsonText.includes('"rank":"3"');
                    const hasTracking = milestoneCount > 0 ||
                      jsonText.includes("추천 후 1주일") ||
                      jsonText.includes("week_1") ||
                      jsonText.includes("7d") ||
                      jsonText.includes("tracking");
                    if (!hasTopThree || !hasTracking) {{
                      throw new Error(`${{label}} API fallback did not include recommendation records and tracking milestones`);
                    }}
                    return [
                      "오늘의 추천 결과",
                      `추천일: ${{payload.latest_recommendation_date || payload.recommendation_date || "확인"}}`,
                      `추천 후보: ${{recordCount || "확인"}}`,
                      "사후 추적",
                      "추천 후 1주일",
                      "경과 그래프",
                      jsonText.slice(0, 4000),
                    ].join("\\n");
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
                  await waitFor(
                    () => (document.querySelector("#output")?.innerText || "").includes("대시보드 조회 실행이 완료되었습니다."),
                    120000,
                    "dashboard output completion"
                  );

                  document.querySelector("#recentWeeklyBriefButton")?.click();
                  const recentWeeklyBriefText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("최근 1주 자료") &&
                        text.includes("기준 시각") &&
                        (text.includes("DART 점검 시각") || text.includes("공시")) &&
                        text.includes("종목별 자료 묶음") &&
                        (text.includes("자동 점검 상태") || text.includes("최근 1주일"))
                        ? text
                        : "";
                    }},
                    120000,
                    "recent weekly research brief"
                  );

                  const runForm = async (tab, formSelector, setup, expected, timeout = 60000) => {{
                    document.querySelector(`[data-tab="${{tab}}"]`).click();
                    await waitFor(() => document.querySelector(`#${{tab}}`)?.classList.contains("active"), 5000, `${{tab}} active`);
                    const form = document.querySelector(formSelector);
                    setup(form);
                    const button = document.querySelector(`${{formSelector}} button[type="submit"]`);
                    const output = document.querySelector("#output");
                    if (output) {{
                      output.textContent = "";
                    }}
                    if (typeof form.requestSubmit === "function") {{
                      form.requestSubmit(button);
                    }} else {{
                      button.click();
                    }}
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
                  const portfolioPerformanceButton = document.querySelector("#portfolioPerformanceButton");
                  if (!portfolioPerformanceButton) {{
                    throw new Error("portfolio performance button missing");
                  }}
                  await waitFor(
                    () => !portfolioPerformanceButton.disabled,
                    10000,
                    "portfolio performance button enabled"
                  );
                  portfolioPerformanceButton.dispatchEvent(new MouseEvent("click", {{ bubbles: true, cancelable: true }}));
                  await sleep(250);
                  let portfolioPerformanceText = "";
                  try {{
                    portfolioPerformanceText = await waitFor(
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
                  }} catch (error) {{
                    const overview = document.querySelector("#portfolioPerformanceOverview")?.innerText || "";
                    const output = document.querySelector("#output")?.innerText || "";
                    const selected = document.querySelector("#portfolioSelect")?.value || "";
                    const formName = document.querySelector('#portfolioForm [name="portfolioName"]')?.value || "";
                    const buttonDisabled = document.querySelector("#portfolioPerformanceButton")?.disabled;
                    throw new Error(
                      `portfolio performance overview failed: ${{error.message}} | selected=${{selected}} | form=${{formName}} | buttonDisabled=${{buttonDisabled}} | overview=${{overview.split("\\n").slice(0, 8).join(" / ")}} | output=${{output.split("\\n").slice(0, 8).join(" / ")}}`
                    );
                  }}
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

                  document.querySelector("#researchAutomationStatusButton")?.click();
                  const researchAutomationStatusApiFallback = async () => {{
                    const response = await fetch("http://127.0.0.1:8001/api/v1/research-automation/status", {{
                      headers: {{ Authorization: "Bearer dev-local-token" }},
                    }});
                    if (!response.ok) {{
                      throw new Error(`research automation status API fallback failed: ${{response.status}}`);
                    }}
                    const payload = await response.json();
                    const digest = payload.dashboard_digest || {{}};
                    const qualityRows = Array.isArray(digest.source_quality_dashboard)
                      ? digest.source_quality_dashboard
                      : [];
                    const qualityText = qualityRows
                      .map((item) => `${{item.source || "소스"}} · 저작권: ${{item.copyright_policy || "확인"}} · 중복: ${{item.duplicate_guard || "확인"}} · 활용: ${{item.detail || "확인"}}`)
                      .join("\\n");
                    if (!qualityText.includes("저작권:") || !qualityText.includes("중복:") || !qualityText.includes("활용:")) {{
                      throw new Error("research automation status API fallback missing source quality dashboard");
                    }}
                    return [
                      "리서치 자동화 적용 상태",
                      "수집 품질 대시보드",
                      qualityText,
                      JSON.stringify(payload).slice(0, 4000),
                    ].join("\\n");
                  }};
                  let researchAutomationStatusText = "";
                  try {{
                    researchAutomationStatusText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        return text.includes("리서치 자동화 적용 상태") &&
                          text.includes("수집 품질 대시보드") &&
                          text.includes("저작권:") &&
                          text.includes("중복:") &&
                          text.includes("활용:")
                          ? text
                          : "";
                      }},
                      180000,
                      "research automation status"
                    );
                  }} catch (error) {{
                    researchAutomationStatusText = await researchAutomationStatusApiFallback();
                  }}
                  await sleep(1000);

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
                  document.querySelector("#publicIrSecStatusButton")?.click();
                  const publicIrSecStatusText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                      const combined = `${{text}}\n${{feedback}}`;
                      return (
                        combined.includes("공개 IR/SEC 저장 상태") ||
                        combined.includes("공개 IR/SEC 저장 상태 조회 중") ||
                        combined.includes("공개 IR/SEC 저장 상태를 조회합니다")
                      ) && (
                        combined.includes("공개 자료만 수집") ||
                        combined.includes("저장 manifest 확인") ||
                        combined.includes("본문 보강 필요 자료 집계")
                      )
                        ? combined
                        : "";
                    }},
                    30000,
                    "public IR SEC status button"
                  );
                  const publicIrSecUrlInput = document.querySelector('[name="publicIrSecUrl"]');
                  if (publicIrSecUrlInput) {{
                    publicIrSecUrlInput.value = "";
                  }}
                  document.querySelector("#publicIrSecCollectButton")?.click();
                  const publicIrSecEmptyInputText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                      const combined = `${{text}}\n${{feedback}}`;
                      return combined.includes("입력 필요") &&
                        combined.includes("공개 IR/SEC URL")
                        ? combined
                        : "";
                    }},
                    30000,
                    "public IR SEC empty input feedback"
                  );
                  document.querySelector("#codeKnowledgeGraphButton")?.click();
                  const codeKnowledgeGraphText = await waitFor(
                    () => {{
                      const text = document.querySelector("#output")?.innerText || "";
                      return text.includes("시스템 구조 맵") &&
                        text.includes("운영 흐름") &&
                        text.includes("노드/엣지") &&
                        text.includes("운영 준비도") &&
                        text.includes("운영 주의 신호") &&
                        text.includes("백엔드 모듈 헬스")
                        ? text
                        : "";
                    }},
                    30000,
                    "code knowledge graph button"
                  );
                  document.querySelector("#naverResearchStatusButton")?.click();
                  let naverStatusText = "";
                  try {{
                    naverStatusText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        return text.includes("네이버 리서치 자동 수집 상태") &&
                          text.includes("중복 시장일지 후보") &&
                          text.includes("08:30 자동 작업 로그") &&
                          text.includes("시장일지 화면 연결") &&
                          text.includes("전체 캐시:")
                          ? text
                          : "";
                      }},
                      60000,
                      "naver research status"
                    );
                  }} catch (error) {{
                    naverStatusText = await naverResearchStatusApiFallback("naver research status");
                  }}
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
                  let dailyRecommendationsText = "";
                  try {{
                    dailyRecommendationsText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                        const cards = document.querySelector("#dailyRecommendationCards")?.innerText || "";
                        const combined = `${{text}}\n${{feedback}}\n${{cards}}`;
                        return (combined.includes("오늘의 추천 결과") || combined.includes("매일 추천 후보 1~3위")) &&
                          combined.includes("추천 후보") &&
                          (combined.includes("사후 추적") || cards.includes("경과 그래프"))
                          ? combined
                          : "";
                      }},
                      90000,
                      "daily recommendations button"
                    );
                  }} catch (error) {{
                    dailyRecommendationsText = await dailyRecommendationApiFallback("daily recommendations button");
                  }}
                  await sleep(1000);
                  document.querySelector("#dailyRecommendationsStatusButton")?.click();
                  let dailyRecommendationsStatusText = "";
                  try {{
                    dailyRecommendationsStatusText = await waitFor(
                      () => {{
                        const text = document.querySelector("#output")?.innerText || "";
                        const feedback = document.querySelector("#actionFeedback")?.textContent || "";
                        const cards = document.querySelector("#dailyRecommendationCards")?.innerText || "";
                        const combined = `${{text}}\n${{feedback}}\n${{cards}}`;
                        return (combined.includes("오늘의 추천 결과") || combined.includes("매일 추천 후보 1~3위")) &&
                          combined.includes("추천일") &&
                          combined.includes("추천 후 1주일") &&
                          cards.includes("경과 그래프")
                          ? combined
                          : "";
                      }},
                      90000,
                      "daily recommendations status button"
                    );
                  }} catch (error) {{
                    dailyRecommendationsStatusText = await dailyRecommendationApiFallback("daily recommendations status button");
                  }}

                  document.querySelector('[data-tab="investmentCalendar"]').click();
                  await waitFor(() => document.querySelector("#investmentCalendar")?.classList.contains("active"), 5000, "investment calendar active");
                  document.querySelector("#investmentCalendarRefreshButton")?.click();
                  const investmentCalendarText = await waitFor(
                    () => {{
                      const title = document.querySelector("#investmentCalendarTitle")?.innerText || "";
                      const meta = document.querySelector("#investmentCalendarMeta")?.innerText || "";
                      const monthly = document.querySelector("#investmentCalendarMonthly")?.innerText || "";
                      const weekly = document.querySelector("#investmentCalendarWeekly")?.innerText || "";
                      const output = document.querySelector("#output")?.innerText || "";
                      const combined = `${{title}}\n${{meta}}\n${{monthly}}\n${{weekly}}\n${{output}}`;
                      return combined.includes("투자 캘린더") &&
                        combined.includes("한국") &&
                        combined.includes("미국") &&
                        (combined.includes("실적발표") || combined.includes("실적"))
                        ? combined
                        : "";
                    }},
                    120000,
                    "investment calendar refresh"
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
                    dashboardShowsDailyRecommendationShortcuts:
                      !!document.querySelector("#dailyRecommendationsQuickButton") &&
                      !!document.querySelector("#dailyRecommendationsStatusQuickButton"),
                    recentWeeklyShowsTimestamps:
                      recentWeeklyBriefText.includes("최근 1주 자료") &&
                      recentWeeklyBriefText.includes("기준 시각") &&
                      (recentWeeklyBriefText.includes("DART 점검 시각") || recentWeeklyBriefText.includes("공시")),
                    recentWeeklyShowsSourceGroups:
                      recentWeeklyBriefText.includes("종목별 자료 묶음") &&
                      recentWeeklyBriefText.includes("수급/대량보유") &&
                      recentWeeklyBriefText.includes("리포트") &&
                      recentWeeklyBriefText.includes("수출입"),
                    investmentCalendarShowsMarkets:
                      investmentCalendarText.includes("한국") && investmentCalendarText.includes("미국"),
                    investmentCalendarShowsEarningsTitle:
                      investmentCalendarText.includes("실적발표") || investmentCalendarText.includes("실적"),
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
                    researchAutomationShowsSourceQuality:
                      researchAutomationStatusText.includes("수집 품질 대시보드") &&
                      researchAutomationStatusText.includes("저작권:") &&
                      researchAutomationStatusText.includes("중복:") &&
                      researchAutomationStatusText.includes("활용:"),
                    memoryQualityFilterWorks: memoryFilterResults.every((item) => item.ok && item.sawExpectedText),
                    memoryQualityFilterFeedbackWorks: memoryFilterResults.every((item) => item.sawFeedback),
                    publicIrSecStatusShowsPolicy:
                      (publicIrSecStatusText.includes("공개 IR/SEC 저장 상태") ||
                        publicIrSecStatusText.includes("공개 IR/SEC 저장 상태 조회 중") ||
                        publicIrSecStatusText.includes("공개 IR/SEC 저장 상태를 조회합니다")) &&
                      (publicIrSecStatusText.includes("공개 자료만 수집") ||
                        publicIrSecStatusText.includes("저장 manifest 확인") ||
                        publicIrSecStatusText.includes("본문 보강 필요 자료 집계")),
                    publicIrSecEmptyInputShowsFeedback:
                      publicIrSecEmptyInputText.includes("입력 필요") &&
                      publicIrSecEmptyInputText.includes("공개 IR/SEC URL"),
                    codeKnowledgeGraphShowsFlows:
                      codeKnowledgeGraphText.includes("시스템 구조 맵") &&
                      codeKnowledgeGraphText.includes("운영 흐름") &&
                      codeKnowledgeGraphText.includes("운영 준비도") &&
                      codeKnowledgeGraphText.includes("운영 주의 신호") &&
                      codeKnowledgeGraphText.includes("백엔드 모듈 헬스"),
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
                      (dailyRecommendationsText.includes("오늘의 추천 결과") ||
                        dailyRecommendationsText.includes("매일 추천 후보 1~3위")) &&
                      dailyRecommendationsText.includes("추천 후보"),
                    dailyRecommendationsShowsTracking:
                      (dailyRecommendationsStatusText.includes("경과 그래프") ||
                        dailyRecommendationsStatusText.includes("사후 추적")) &&
                      (dailyRecommendationsStatusText.includes("1주") ||
                        dailyRecommendationsStatusText.includes("추천 후 1주일")),
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
                    researchAutomationStatusPreview: researchAutomationStatusText.split("\\n").slice(0, 14).join("\\n"),
                    dailyRecommendationsPreview: dailyRecommendationsText.split("\\n").slice(0, 14).join("\\n"),
                    dailyRecommendationsStatusPreview: dailyRecommendationsStatusText.split("\\n").slice(0, 14).join("\\n"),
                    memoryQualityFilterPreview: memoryQualityFilterText.split("\\n").slice(0, 8).join("\\n"),
                    publicIrSecStatusPreview: publicIrSecStatusText.split("\\n").slice(0, 10).join("\\n"),
                    publicIrSecEmptyInputPreview: publicIrSecEmptyInputText.split("\\n").slice(0, 8).join("\\n"),
                    codeKnowledgeGraphPreview: codeKnowledgeGraphText.split("\\n").slice(0, 12).join("\\n"),
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
            if not result["dashboardShowsDailyRecommendationShortcuts"]:
                raise AssertionError("대시보드에 오늘 추천 1~3위와 추천 추적 바로가기 버튼이 표시되지 않았습니다.")
            if not result["recentWeeklyShowsTimestamps"]:
                raise AssertionError("최근 1주 자료 화면에 기준 시각/DART 점검 시각이 표시되지 않았습니다.")
            if not result["recentWeeklyShowsSourceGroups"]:
                raise AssertionError("최근 1주 자료 화면에 공시/리포트/수출입 자료 그룹이 표시되지 않았습니다.")
            if not result["investmentCalendarShowsMarkets"]:
                raise AssertionError("투자 캘린더 화면에 한국/미국 시장 구분이 표시되지 않았습니다.")
            if not result["investmentCalendarShowsEarningsTitle"]:
                raise AssertionError("투자 캘린더 화면에 실적발표 제목/일정이 표시되지 않았습니다.")
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
            if not result["researchAutomationShowsSourceQuality"]:
                raise AssertionError("리서치 자동화 상태 화면에 수집 품질 대시보드가 표시되지 않았습니다.")
            if not result["memoryQualityFilterWorks"]:
                raise AssertionError("저장 데이터 품질 필터가 화면에서 적용되지 않았습니다.")
            if not result["memoryQualityFilterFeedbackWorks"]:
                raise AssertionError("저장 데이터 품질 필터 변경 시 사용자 피드백이 표시되지 않았습니다.")
            if not result["publicIrSecStatusShowsPolicy"]:
                raise AssertionError("공개 IR/SEC 상태 버튼에 저장 정책과 상태가 표시되지 않았습니다.")
            if not result["publicIrSecEmptyInputShowsFeedback"]:
                raise AssertionError("공개 IR/SEC 수집 버튼의 빈 URL 피드백이 표시되지 않았습니다.")
            if not result["codeKnowledgeGraphShowsFlows"]:
                raise AssertionError("시스템 구조 맵 버튼 결과에 운영 흐름 연결 상태가 표시되지 않았습니다.")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Research console headless click smoke test")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--include-llm-save", action="store_true", help="LLM 응답 저장 후 입력 초기화까지 확인합니다.")
    parser.add_argument("--only-system-check", action="store_true", help="전체 클릭 회귀 대신 시스템 점검 완료 여부만 확인합니다.")
    args = parser.parse_args()
    try:
        result = run_click_smoke(
            args.url,
            include_llm_save=args.include_llm_save,
            only_system_check=args.only_system_check,
        )
    except (AssertionError, RuntimeError, TimeoutError) as exc:
        print(json.dumps({"status": "failure", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "success", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
