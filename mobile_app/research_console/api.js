const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001";
const runtimeApiBaseUrl =
  typeof process !== "undefined" && process.env
    ? process.env.EXPO_PUBLIC_API_BASE_URL
    : null;

/**
 * React Native에서는 실제 기기와 로컬 PC가 다른 네트워크 주소를 사용합니다.
 * 개발 기기에서는 API_BASE_URL에 PC의 내부 IP를 넣어 호출하세요.
 */
export let API_BASE_URL = runtimeApiBaseUrl || DEFAULT_API_BASE_URL;

export function setApiBaseUrl(url) {
  API_BASE_URL = (url || DEFAULT_API_BASE_URL).trim().replace(/\/$/, "");
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  const { accessToken, timeoutMs = 0, signal: optionSignal, ...fetchOptions } = options;
  const controller = timeoutMs > 0 ? new AbortController() : null;
  const timeoutId = controller
    ? setTimeout(() => controller.abort(new Error(`요청 시간이 ${Math.round(timeoutMs / 1000)}초를 넘었습니다.`)), timeoutMs)
    : null;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchOptions,
      signal: controller?.signal || optionSignal,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken
          ? { Authorization: `Bearer ${accessToken}` }
          : {}),
        ...(fetchOptions.headers || {}),
      },
    });
  } catch (error) {
    const abortedMessage = controller?.signal?.aborted
      ? `요청 시간이 ${Math.round(timeoutMs / 1000)}초를 넘었습니다.`
      : error?.message || String(error);
    throw new ApiError(
      `API 연결 실패: ${API_BASE_URL}${path} - ${abortedMessage}`,
      0
    );
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(
      `HTTP error: ${response.status}${detail ? ` - ${detail}` : ""}`,
      response.status
    );
  }

  return response.json();
}

async function requestBlob(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.accessToken
          ? { Authorization: `Bearer ${options.accessToken}` }
          : {}),
        ...(options.headers || {}),
      },
    });
  } catch (error) {
    throw new ApiError(
      `API 연결 실패: ${API_BASE_URL}${path} - ${
        error?.message || String(error)
      }`,
      0
    );
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(
      `HTTP error: ${response.status}${detail ? ` - ${detail}` : ""}`,
      response.status
    );
  }

  const disposition = response.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  const filename = filenameMatch
    ? decodeURIComponent(filenameMatch[1].replace(/"/g, ""))
    : "research-os-result.xlsx";
  return { blob: await response.blob(), filename };
}

export async function exportResultXlsx(
  accessToken,
  { title = "분석 결과", module = "화면 결과", resultText, resultJson = null }
) {
  return requestBlob("/api/v1/export/result-xlsx", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      title,
      module,
      result_text: resultText,
      result_json: resultJson,
      generated_at: new Date().toISOString(),
    }),
  });
}


export async function fetchInvestmentCalendar(accessToken) {
  return request("/api/v1/investment-calendar/latest", {
    method: "GET",
    accessToken,
  });
}

/**
 * 백엔드 서버에 접속하여 정규화된 매매 내역을 가져옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Array>} 매매 데이터 배열
 */
export async function fetchTrades(accessToken) {
  try {
    const json = await request("/api/v1/trades", {
      method: "GET",
      accessToken,
    });

    return json.data;
  } catch (error) {
    console.error("데이터를 불러오는 중 오류 발생:", error);
    return [];
  }
}

/**
 * 현재 백엔드가 어떤 증권사 Adapter를 우선 사용하는지 확인합니다.
 *
 * @returns {Promise<Object|null>} 증권사 연동 상태
 */
export async function fetchBrokerageStatus() {
  try {
    return request("/api/v1/brokerage/status", {
      method: "GET",
    });
  } catch (error) {
    console.error("증권사 연동 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 분석용 데이터 프로바이더 상태와 자동 주입 설정을 확인합니다.
 *
 * @returns {Promise<Object|null>} 데이터 프로바이더 상태
 */
export async function fetchDataProviderStatus() {
  try {
    return request("/api/v1/data-providers/status", {
      method: "GET",
    });
  } catch (error) {
    console.error("데이터 프로바이더 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchCodeKnowledgeGraph(accessToken) {
  return request("/api/v1/system/code-knowledge-graph", {
    method: "GET",
    accessToken,
  });
}

/**
 * 이미지/PDF OCR 런타임 연결 상태를 확인합니다.
 *
 * @returns {Promise<Object|null>} Tesseract 실행 파일과 언어팩 연결 상태
 */
export async function fetchOcrStatus() {
  try {
    return request("/api/v1/ocr/status", {
      method: "GET",
    });
  } catch (error) {
    console.error("OCR 연결 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * DART 신규 공시 자동 감시 상태를 확인합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} DART 신규 공시 감시 캐시와 최근 실패/저장 상태
 */
export async function fetchDartFilingWatchStatus(accessToken) {
  try {
    return request("/api/v1/dart/filings/status", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("DART 신규 공시 감시 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * DART 신규 공시 자동 감시를 즉시 재실행합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {{tickers?: string[], force?: boolean, saveResult?: boolean}} options 재점검 옵션
 * @returns {Promise<Object|null>} 재점검 결과
 */
export async function refreshDartFilingWatch(accessToken, options = {}) {
  try {
    return await request("/api/v1/dart/filings/refresh", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        tickers: options.tickers || undefined,
        force: Boolean(options.force),
        save_result: options.saveResult !== false,
      }),
    });
  } catch (error) {
    console.error("DART 신규 공시 감시를 재실행하는 중 오류 발생:", error);
    return null;
  }
}


/**
 * 보유/관심종목 기준 최근 공시, 리포트, 수출입 자료를 1주일 단위로 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {{days?: number, refreshIfDue?: boolean}} options 조회 기간과 DART 보강 실행 여부
 * @returns {Promise<Object|null>} 최근 1주일 리서치 브리프
 */
export async function fetchPublicIrSecStatus(accessToken, limit = 10) {
  try {
    return request(`/api/v1/public-ir-sec/status?limit=${encodeURIComponent(limit)}`, {
      method: "GET",
      accessToken,
      timeoutMs: 30000,
    });
  } catch (error) {
    console.error("공개 IR/SEC 상태 조회 중 오류 발생:", error);
    return null;
  }
}

export async function collectPublicIrSec(
  accessToken,
  { url, targetKey = "PUBLIC_IR_SEC", saveResult = true, force = false, noScreenshot = true } = {}
) {
  try {
    return request("/api/v1/public-ir-sec/collect", {
      method: "POST",
      accessToken,
      timeoutMs: 60000,
      body: JSON.stringify({
        url,
        target_key: targetKey,
        save_result: saveResult,
        force,
        no_screenshot: noScreenshot,
      }),
    });
  } catch (error) {
    console.error("공개 IR/SEC 자료 수집 중 오류 발생:", error);
    return null;
  }
}


export async function fetchRecentWeeklyResearchBrief(accessToken, options = {}) {
  const params = new URLSearchParams();
  params.set("days", String(options.days || 7));
  params.set("refresh_if_due", options.refreshIfDue === false ? "false" : "true");
  try {
    return await request(`/api/v1/research/recent-weekly-brief?${params.toString()}`, {
      method: "GET",
      accessToken,
      timeoutMs: 45000,
    });
  } catch (error) {
    console.error("최근 1주일 리서치 브리프를 불러오는 중 오류 발생:", error);
    if (error?.status === 404) {
      return {
        status: "route_missing",
        module: "recent_weekly_research_brief_route_missing",
        message: "실행 중인 백엔드가 최근 1주 자료 API를 아직 반영하지 않았습니다.",
        requested_path: `/api/v1/research/recent-weekly-brief?${params.toString()}`,
        next_actions: [
          "백엔드를 최신 코드로 재시작하세요.",
          "PowerShell에서 C:\\Users\\lib20\\InvestmentJournalApp 이동 후 .\\scripts\\start-research-backend.ps1 -Port 8001을 실행하세요.",
          "브라우저를 새로고침한 뒤 최근 1주 자료 버튼을 다시 누르세요.",
        ],
      };
    }
    return null;
  }
}


/**
 * 백엔드 상태 이상을 서버 로그와 향후 모바일 푸시 훅에 기록합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} payload 상태 이상 요약
 * @returns {Promise<Object|null>} 기록 결과
 */
export async function reportBackendHealthAlert(accessToken, payload) {
  try {
    return request("/api/v1/alerts/backend-health", {
      method: "POST",
      accessToken,
      body: JSON.stringify(payload || {}),
    });
  } catch (error) {
    console.warn("백엔드 상태 알림 기록 중 오류 발생:", error);
    return null;
  }
}

/**
 * 공식 티커 인증 후 현재 데이터 프로바이더가 반환하는 최신 스냅샷을 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커
 * @returns {Promise<Object|null>} 가격/재무 데이터 주입 포인트
 */
export async function fetchLatestDataSnapshot(accessToken, ticker) {
  try {
    return request(`/api/v1/data-providers/snapshot/${ticker}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("최신 데이터 스냅샷을 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 공식 티커 인증을 실행합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 입력 티커
 * @returns {Promise<Object|null>} 공식 티커 인증 결과
 */
export async function verifyTickerSymbol(accessToken, ticker, options = {}) {
  try {
    const query = options.fast ? "?fast=true" : "";
    return request(`/api/v1/tickers/verify/${encodeURIComponent(ticker)}${query}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("공식 티커 인증 중 오류 발생:", error);
    return null;
  }
}

/**
 * 공식 티커 인증과 회사별 분석 초점/핵심 KPI 프로필을 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 입력 티커
 * @returns {Promise<Object|null>} 회사 프로필
 */
export async function fetchTickerProfile(accessToken, ticker, options = {}) {
  try {
    const query = options.refreshExternal === false ? "?refresh_external=false" : "";
    return request(`/api/v1/tickers/profile/${ticker}${query}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("회사 프로필을 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커 인증 경로를 로컬 레지스트리, 자동 캐시, FMP 조회 단계별로 진단합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 진단할 티커
 * @returns {Promise<Object|null>} 티커 진단 결과
 */
export async function fetchTickerDiagnostics(accessToken, ticker) {
  try {
    return request(`/api/v1/tickers/diagnose/${ticker}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("티커 진단을 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * FMP 등 외부 데이터로 자동 인증되어 저장된 티커 캐시를 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} 자동 인증 티커 캐시
 */
export async function fetchTickerRegistryCache(accessToken) {
  try {
    return request("/api/v1/tickers/cache", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("티커 인증 캐시를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 수동 LLM 연동으로 저장한 응답과 원 프롬프트가 저장 데이터/RAG에 연결됐는지 확인합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {number} limit 최근 항목 조회 개수
 * @returns {Promise<Object|null>} LLM 저장 및 RAG 연결 상태
 */
export async function fetchLlmBridgeStorageStatus(accessToken, limit = 10) {
  const query = new URLSearchParams({ limit: String(limit || 10) });
  try {
    return request(`/api/v1/llm-bridge/storage-status?${query}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("LLM 연동 저장 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 자동 인증 티커 캐시에서 특정 티커를 삭제합니다. 로컬 공식 레지스트리는 삭제하지 않습니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 삭제할 캐시 티커
 * @returns {Promise<Object|null>} 삭제 후 캐시 상태
 */
export async function deleteTickerRegistryCacheEntry(accessToken, ticker) {
  try {
    return request(`/api/v1/tickers/cache/${ticker}`, {
      method: "DELETE",
      accessToken,
    });
  } catch (error) {
    console.error("티커 인증 캐시 삭제 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커 중심 대시보드 데이터를 불러옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커
 * @returns {Promise<Object|null>} 저장 리서치와 다음 액션 요약
 */
export async function fetchTickerDashboard(accessToken, ticker) {
  try {
    return request(`/api/v1/dashboard/${ticker}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("티커 대시보드를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커 입력 후 실행 버튼을 누르면 모듈 1(기관급 분석)로 이동하면서 즉시 분석을 시작합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 분석 입력값
 * @param {string} params.ticker 분석 대상 티커
 * @param {string} [params.investmentPeriod] 투자 기간
 * @param {string} [params.focusArea] 중점 분석 내용
 * @param {boolean} [params.autoInjectData] 시장/재무 데이터 자동 주입 여부
 * @returns {Promise<Object|null>} 기관급 분석 결과
 */
export async function runInstitutionalStockBreakdown(
  accessToken,
  {
    ticker,
    investmentPeriod = "3 years",
    focusArea = null,
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/analysis/modules/institutional-stock-breakdown/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        investment_period: investmentPeriod,
        focus_area: focusArea,
        auto_run: true,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("기관급 분석을 실행하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 16개 리서치 체크리스트 완료 현황을 서버에 보내 투자 준비도와 다음 단계를 생성합니다.
 * 진행바는 화면에서 checkedItems.length / 16로 즉시 갱신하고, 이 함수는 분석 버튼에서 호출합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 체크리스트 입력값
 * @param {string} params.ticker 분석 대상 티커
 * @param {Array<string>} params.checkedItems 완료된 체크리스트 key 목록
 * @param {string} [params.notes] 사용자의 보충 메모
 * @returns {Promise<Object|null>} 투자 준비도 평가 결과
 */
export async function assessResearchChecklist(
  accessToken,
  { ticker, checkedItems, notes = null, realtimeData = [], saveResult = true }
) {
  try {
    return request("/api/v1/research/checklist/assess", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        checked_items: checkedItems,
        notes,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("리서치 체크리스트를 분석하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 현재가, 매매 스타일, 허용 리스크를 바탕으로 구조화된 매매 전략을 생성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 매매 전략 입력값
 * @param {string} params.ticker 분석 대상 티커
 * @param {number} params.currentPrice 현재가
 * @param {string} [params.style] 매매 스타일
 * @param {string} [params.riskTolerance] 허용 리스크
 * @param {number|null} [params.portfolioSize] 계좌 또는 포트폴리오 규모
 * @param {number} [params.riskPerTradePct] 1회 거래 허용 손실 비율
 * @param {string|null} [params.marketStructure] 사용자가 지정한 시장 구조
 * @param {boolean} [params.autoInjectData] 시장/재무 데이터 자동 주입 여부
 * @param {Array<Object>} [params.realtimeData] 실시간 또는 사용자 주입 데이터
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 매매 전략 결과
 */
export async function runSmartTradeSetup(
  accessToken,
  {
    ticker,
    currentPrice,
    style = "swing",
    riskTolerance = "보통",
    portfolioSize = null,
    riskPerTradePct = 0.01,
    marketStructure = null,
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/analysis/modules/smart-trade-setup/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        current_price: currentPrice,
        style,
        risk_tolerance: riskTolerance,
        portfolio_size: portfolioSize,
        risk_per_trade_pct: riskPerTradePct,
        market_structure: marketStructure,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("스마트 매매 전략을 생성하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 네이버 증권 국내 일별 시세를 기반으로 6개 핵심 보조지표 차트 분석을 실행합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 차트 분석 입력값
 * @param {string} params.ticker 국내 6자리 종목코드
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 차트 분석 결과
 */
export async function runNaverChartAnalysis(
  accessToken,
  { ticker, saveResult = true }
) {
  const query = new URLSearchParams({
    ticker,
    save_result: String(saveResult),
  });
  return request(`/api/v1/analysis/modules/naver-chart/run?${query}`, {
    method: "POST",
    accessToken,
  });
}

/**
 * 실적 발표 수치와 주가 반응을 바탕으로 시장 반응, 센티먼트 변화, 다음 실적 전 추적 항목을 분석합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 실적 반응 분석 입력값
 * @returns {Promise<Object|null>} 실적 반응 분석 결과
 */
export async function runEarningsReactionAnalyzer(
  accessToken,
  {
    ticker,
    quarter,
    earningsReportDate = null,
    priceReaction,
    previousEarningsDate = null,
    previousEarningsSummary = null,
    nextEarningsDate = null,
    nextEarningsGuidance = null,
    epsReported = null,
    epsExpected = null,
    revenueReported = null,
    revenueExpected = null,
    guidanceChange = "유지",
    managementTone = null,
    marketContext = null,
    keyNumbers = {},
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/analysis/modules/earnings-reaction/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        quarter,
        earnings_report_date: earningsReportDate,
        price_reaction: priceReaction,
        previous_earnings_date: previousEarningsDate,
        previous_earnings_summary: previousEarningsSummary,
        next_earnings_date: nextEarningsDate,
        next_earnings_guidance: nextEarningsGuidance,
        eps_reported: epsReported,
        eps_expected: epsExpected,
        revenue_reported: revenueReported,
        revenue_expected: revenueExpected,
        guidance_change: guidanceChange,
        management_tone: managementTone,
        market_context: marketContext,
        key_numbers: keyNumbers,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("실적 반응 분석을 실행하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 매크로 환경을 바탕으로 유망 섹터와 후보 기업을 발굴합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 섹터 기회 발굴 입력값
 * @returns {Promise<Object|null>} 섹터 기회 분석 결과
 */
export async function runSectorOpportunityFinder(
  accessToken,
  {
    macroEnvironment,
    period = "6개월",
    region = "KR",
    style = "균형형",
    focusTheme = "",
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/analysis/modules/sector-opportunity/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        macro_environment: macroEnvironment,
        period,
        region,
        style,
        focus_theme: focusTheme,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("섹터 기회 발굴을 실행하는 중 오류 발생:", error);
    return null;
  }
}

export async function runEarningsFilingNoteWorkflow(
  accessToken,
  {
    ticker,
    earningsCall = "",
    filingMaterial = "",
    modelNotes = "",
    fileName = null,
    fileMimeType = null,
    fileSize = null,
    fileContentBase64 = null,
    autoInjectData = true,
    saveResult = true,
  }
) {
  return request("/api/v1/workflows/earnings-filing-note", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      ticker,
      earnings_call: earningsCall,
      filing_material: filingMaterial,
      model_notes: modelNotes,
      file_name: fileName,
      file_mime_type: fileMimeType,
      file_size: fileSize,
      file_content_base64: fileContentBase64,
      auto_inject_data: autoInjectData,
      save_result: saveResult,
    }),
  });
}

export async function runGpLpStagingWorkflow(
  accessToken,
  {
    fundName = "GP 패키지",
    gpPackage = "",
    valuationMethod = "멀티플/DCF 혼합",
    baseCase = "기준 시나리오",
    fileName = null,
    fileMimeType = null,
    fileSize = null,
    fileContentBase64 = null,
    saveResult = true,
  }
) {
  return request("/api/v1/workflows/gp-lp-staging", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      fund_name: fundName,
      gp_package: gpPackage,
      valuation_method: valuationMethod,
      base_case: baseCase,
      file_name: fileName,
      file_mime_type: fileMimeType,
      file_size: fileSize,
      file_content_base64: fileContentBase64,
      save_result: saveResult,
    }),
  });
}

/**
 * 매출 성장, 마진, 경쟁 우위, 확장성 조건으로 장기 복리 성장주 후보를 선별합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 복리 성장주 스크리닝 입력값
 * @returns {Promise<Object|null>} 장기 복리 성장주 분석 결과
 */
export async function runLongTermCompounderFinder(
  accessToken,
  {
    screeningCriteria,
    minMarketCap = null,
    maxMarketCap = null,
    sector = "전체",
    region = "KR",
    style = "퀄리티 성장",
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/analysis/modules/long-term-compounder/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        screening_criteria: screeningCriteria,
        min_market_cap: minMarketCap,
        max_market_cap: maxMarketCap,
        sector,
        region,
        style,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("장기 복리 성장주 발굴을 실행하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커별로 같은 워크스페이스에 자동 저장된 Markdown 리서치 파일 목록을 불러옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커
 * @param {{ includeArchived?: boolean }} [options] 보관 문서 포함 여부
 * @returns {Promise<Array>} 저장된 리서치 파일 메타데이터 배열
 */
export async function fetchResearchMemoryFiles(accessToken, ticker, options = {}) {
  const params = new URLSearchParams();
  if (options.includeArchived) {
    params.set("include_archived", "true");
  }
  const query = params.toString();
  try {
    return request(`/api/v1/research-memory/${encodeURIComponent(ticker)}${query ? `?${query}` : ""}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("리서치 메모리 파일 목록을 불러오는 중 오류 발생:", error);
    return { files: [], data_warnings: [] };
  }
}

/**
 * 저장된 리포트를 삭제하지 않고 보관/복원 상태만 변경합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커 또는 저장 키
 * @param {string} fileName 파일명
 * @param {{ archived: boolean, reason?: string }} payload 보관 여부와 사유
 * @returns {Promise<Object|null>} 갱신된 Markdown 본문과 메타데이터
 */
export async function archiveResearchMemoryFile(accessToken, ticker, fileName, payload) {
  return request(
    `/api/v1/research-memory/${encodeURIComponent(ticker)}/files/${encodeURIComponent(fileName)}/archive`,
    {
      method: "PATCH",
      accessToken,
      body: JSON.stringify({
        archived: Boolean(payload.archived),
        reason: payload.reason || null,
      }),
    }
  );
}

/**
 * 레거시 저장 파일을 삭제하지 않고 일괄 소프트 보관합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커 또는 저장 키
 * @param {{ reason?: string }} [payload] 보관 사유
 * @returns {Promise<Object>} 일괄 보관 결과
 */
export async function archiveLegacyResearchMemoryFiles(accessToken, ticker, payload = {}) {
  return request(
    `/api/v1/research-memory/${encodeURIComponent(ticker)}/legacy/archive`,
    {
      method: "PATCH",
      accessToken,
      body: JSON.stringify({
        archived: true,
        reason: payload.reason || "레거시 파일 처리 정책에 따라 소프트 보관",
      }),
    }
  );
}

/**
 * 저장된 Markdown 리포트 본문을 불러옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커
 * @param {string} fileName 파일명
 * @returns {Promise<Object|null>} Markdown 본문과 메타데이터
 */
export async function fetchResearchMemoryFile(accessToken, ticker, fileName) {
  return request(
    `/api/v1/research-memory/${encodeURIComponent(ticker)}/files/${encodeURIComponent(fileName)}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

/**
 * 본문 추출이 제한된 저장 리포트에 사용자가 복사한 원문을 보강합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커 또는 저장 키
 * @param {string} fileName 파일명
 * @param {{ bodyText: string, note?: string }} payload 보강 본문과 선택 메모
 * @returns {Promise<Object|null>} 갱신된 Markdown 본문과 메타데이터
 */
export async function supplementResearchMemoryFile(accessToken, ticker, fileName, payload) {
  return request(
    `/api/v1/research-memory/${encodeURIComponent(ticker)}/files/${encodeURIComponent(fileName)}/body-supplement`,
    {
      method: "PATCH",
      accessToken,
      body: JSON.stringify({
        body_text: payload.bodyText,
        note: payload.note || null,
      }),
    }
  );
}

/**
 * 전체 research_vault manifest를 불러옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Array>} 리서치 manifest entry 배열
 */
export async function fetchResearchManifest(accessToken) {
  try {
    const json = await request("/api/v1/research-memory", {
      method: "GET",
      accessToken,
    });

    return json.entries;
  } catch (error) {
    console.error("리서치 manifest를 불러오는 중 오류 발생:", error);
    return [];
  }
}

/**
 * manifest에 저장된 보고서/메모를 RAG 문서 색인으로 백필합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} 백필 결과
 */
export async function backfillRagMemoryDocuments(accessToken) {
  try {
    return request("/api/v1/rag/memory/backfill", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("RAG 문서 색인을 백필하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 기존 저장 데이터의 첨부 파일 OCR을 현재 런타임 기준으로 다시 처리합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {{ includeArchived?: boolean, force?: boolean, limit?: number, saveResult?: boolean }} [options] 재처리 옵션
 * @returns {Promise<Object|null>} OCR 재처리 결과
 */
export async function reprocessResearchMemoryOcr(accessToken, options = {}) {
  return request("/api/v1/research-memory/ocr/reprocess", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      include_archived: Boolean(options.includeArchived),
      force: Boolean(options.force),
      limit: options.limit || null,
      save_result: options.saveResult !== false,
    }),
  });
}

/**
 * 현재 저장 자료를 종목별 Dossier로 합성하고 RAG 투자 논거 스냅샷을 갱신합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커 또는 회사명
 * @param {boolean} saveResult 저장 여부
 * @returns {Promise<Object|null>} Dossier 합성 결과
 */
export async function synthesizeDossier(accessToken, ticker, saveResult = true) {
  try {
    return request(
      `/api/v1/dossier/${encodeURIComponent(ticker)}/synthesize?save_result=${
        saveResult ? "true" : "false"
      }`,
      {
        method: "POST",
        accessToken,
      }
    );
  } catch (error) {
    console.error("Dossier 합성 중 오류 발생:", error);
    return null;
  }
}

/**
 * 외부 리서치 캐시, RAG 색인, Dossier 합성, 일일 브리핑을 순서대로 실행합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 실행 옵션
 * @returns {Promise<Object|null>} 자동화 실행 결과
 */
export async function runResearchAutomation(
  accessToken,
  { limit = 30, saveResult = true } = {}
) {
  try {
    return request(
      `/api/v1/research-automation/run?limit=${encodeURIComponent(
        limit
      )}&save_result=${saveResult ? "true" : "false"}`,
      {
        method: "POST",
        accessToken,
      }
    );
  } catch (error) {
    console.error("리서치 자동화 실행 중 오류 발생:", error);
    return null;
  }
}

/**
 * 자동 리서치 파이프라인의 기능별 적용 상태를 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} 기능별 자동화 상태
 */
export async function fetchResearchAutomationStatus(accessToken) {
  try {
    return request("/api/v1/research-automation/status", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("리서치 자동화 상태 조회 중 오류 발생:", error);
    return null;
  }
}

/**
 * 저장 데이터의 대표 자료/중복 의심 자료 묶음을 생성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 실행 옵션
 * @returns {Promise<Object|null>} 중복 리뷰 결과
 */
export async function runStorageDuplicateReview(
  accessToken,
  { limit = 80, saveResult = true } = {}
) {
  try {
    return request(
      `/api/v1/research-automation/dedupes/review?limit=${encodeURIComponent(
        limit
      )}&save_result=${saveResult ? "true" : "false"}`,
      {
        method: "POST",
        accessToken,
      }
    );
  } catch (error) {
    console.error("저장 데이터 중복 리뷰 중 오류 발생:", error);
    return null;
  }
}

/**
 * 중복 리뷰 우선순위 종목의 Dossier를 다시 합성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 실행 옵션
 * @returns {Promise<Object|null>} Dossier 재합성 큐 결과
 */
export async function runDedupedDossierRefresh(
  accessToken,
  { limit = 8, saveResult = true } = {}
) {
  try {
    return request(
      `/api/v1/research-automation/dedupes/refresh-dossiers?limit=${encodeURIComponent(
        limit
      )}&save_result=${saveResult ? "true" : "false"}`,
      {
        method: "POST",
        accessToken,
      }
    );
  } catch (error) {
    console.error("중복 리뷰 기반 Dossier 재합성 중 오류 발생:", error);
    return null;
  }
}

/**
 * 보유/관심 종목 Dossier와 최근 시장 자료를 묶은 일일 브리핑을 생성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {boolean} saveResult 저장 여부
 * @returns {Promise<Object|null>} 일일 브리핑
 */
export async function fetchDailyBriefing(accessToken, saveResult = false) {
  try {
    return request(
      `/api/v1/daily-briefing?save_result=${saveResult ? "true" : "false"}`,
      {
        method: "GET",
        accessToken,
      }
    );
  } catch (error) {
    console.error("일일 브리핑을 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 매일 추천 후보 1~3위와 사후 추적 상태를 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} 일일 추천/추적 상태
 */
export async function fetchDailyRecommendationsStatus(accessToken) {
  try {
    return request("/api/v1/daily-recommendations/status", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("일일 추천 상태 조회 중 오류 발생:", error);
    return null;
  }
}

/**
 * 오늘의 추천 후보 1~3위를 생성하고 별도 항목으로 저장합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 실행 옵션
 * @returns {Promise<Object|null>} 일일 추천 실행 결과
 */
export async function runDailyRecommendations(
  accessToken,
  { force = false, saveResult = true } = {}
) {
  try {
    return request(
      `/api/v1/daily-recommendations/run?force=${force ? "true" : "false"}&save_result=${
        saveResult ? "true" : "false"
      }`,
      {
        method: "POST",
        accessToken,
      }
    );
  } catch (error) {
    console.error("일일 추천 실행 중 오류 발생:", error);
    return null;
  }
}

/**
 * 저장된 추천 후보의 1주/15일/1달/3달/6달 추적 상태를 갱신합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @returns {Promise<Object|null>} 추적 갱신 결과
 */
export async function trackDailyRecommendations(accessToken) {
  try {
    return request("/api/v1/daily-recommendations/track", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("일일 추천 추적 갱신 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커 또는 리서치 키 기준으로 검색 가능한 RAG 문서를 조회합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} key 티커 또는 리서치 키
 * @param {Object} options 검색 옵션
 * @param {string|null} [options.query] 검색어
 * @param {number} [options.limit] 반환 개수
 * @param {boolean} [options.includeLowQuality] 저품질/격리 문서 포함 여부
 * @returns {Promise<Object|null>} RAG 문서 검색 결과
 */
export async function searchRagMemoryDocuments(
  accessToken,
  { key, query = null, limit = 8, includeLowQuality = false }
) {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      include_low_quality: includeLowQuality ? "true" : "false",
    });
    if (query) {
      params.set("query", query);
    }
    return request(
      `/api/v1/rag/memory/search/${encodeURIComponent(key)}?${params.toString()}`,
      {
        method: "GET",
        accessToken,
      }
    );
  } catch (error) {
    console.error("RAG 문서를 검색하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 전체 저장 데이터/RAG 색인을 자연어로 검색합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 검색 옵션
 * @param {string} options.query 자연어 검색어
 * @param {number} [options.limit] 반환 개수
 * @param {boolean} [options.includeLowQuality] 저품질/격리 문서 포함 여부
 * @returns {Promise<Object|null>} 전체 RAG 검색 결과
 */
export async function searchAllRagMemoryDocuments(
  accessToken,
  { query, limit = 12, includeLowQuality = false }
) {
  try {
    const params = new URLSearchParams({
      query: query || "",
      limit: String(limit),
      include_low_quality: includeLowQuality ? "true" : "false",
    });
    return request(`/api/v1/rag/memory/search?${params.toString()}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("전체 RAG 문서를 검색하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 전체 저장 데이터/RAG 검색 결과를 투자 판단 보고서로 합성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} options 합성 옵션
 * @param {string} options.query 자연어 검색어
 * @param {number} [options.limit] 검색/합성에 사용할 최대 문서 수
 * @param {boolean} [options.includeLowQuality] 저품질/격리 문서 포함 여부
 * @param {boolean} [options.saveResult] 합성 보고서 저장 여부
 * @returns {Promise<Object|null>} 검색 결과 합성 보고서
 */
export async function synthesizeRagSearchResults(
  accessToken,
  { query, limit = 12, includeLowQuality = false, saveResult = true }
) {
  try {
    return request("/api/v1/rag/memory/synthesize", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        query,
        limit,
        include_low_quality: includeLowQuality,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("RAG 검색 결과를 합성하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 티커별 투자 논거와 watch item을 불러옵니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {string} ticker 조회할 티커
 * @returns {Promise<Object|null>} theses와 watch_items
 */
export async function fetchInvestmentTheses(accessToken, ticker) {
  try {
    return request(`/api/v1/research-memory/${ticker}/theses`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("투자 논거를 불러오는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 새 뉴스/데이터/메모가 기존 투자 논거를 강화, 약화, 혼합, 중립 중 어디로 움직이는지 평가합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 영향도 분석 입력값
 * @param {string} params.ticker 분석 대상 티커
 * @param {Array<Object>} params.newData 새로 주입할 데이터
 * @param {string} [params.userQuestion] 사용자의 추가 질문
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 투자 논거 영향도 분석 결과
 */
export async function runThesisImpactReview(
  accessToken,
  { ticker, newData, userQuestion = null, saveResult = true }
) {
  try {
    return request("/api/v1/research-memory/thesis-impact/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        new_data: newData,
        user_question: userQuestion,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("투자 논거 영향도를 분석하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 사용자가 수집한 투자 정보나 메모를 즉시 저장하고, 선택적으로 기존 투자 논거 영향도를 분석합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 캡처 입력값
 * @param {string} params.ticker 관련 티커
 * @param {string} params.title 캡처 제목
 * @param {string} params.rawContent 원문 또는 메모
 * @param {string} [params.sourceType] source type
 * @param {string} [params.sourceUrl] 출처 URL
 * @param {string} [params.asOf] 데이터 기준 시각
 * @param {number} [params.confidence] 출처 신뢰도
 * @param {Array<string>} [params.tags] 사용자 태그
 * @param {boolean} [params.runThesisImpact] 기존 thesis 영향도 분석 여부
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 캡처 및 연결 영향도 분석 결과
 */
export async function captureResearchItem(
  accessToken,
  {
    ticker,
    title,
    rawContent,
    sourceType = "user_memo",
    sourceUrl = null,
    asOf = null,
    confidence = 0.8,
    tags = [],
    runThesisImpact = true,
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/research-memory/capture", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        title,
        raw_content: rawContent,
        source_type: sourceType,
        source_url: sourceUrl,
        as_of: asOf,
        confidence,
        tags,
        run_thesis_impact: runThesisImpact,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("투자 정보를 캡처하는 중 오류 발생:", error);
    return null;
  }
}

/**
 * 텍스트 또는 파일 내용을 보내면 백엔드가 티커, 제목, 출처 유형, 신뢰도를 자동 분류해 저장합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 자동 캡처 입력값
 * @param {string} params.rawContent 텍스트 또는 읽어온 파일 본문
 * @param {string|null} [params.sourceUrl] 웹사이트 주소
 * @param {string|null} [params.fileName] 파일명
 * @param {boolean} [params.runThesisImpact] 기존 투자 논거 영향도 분석 여부
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 자동 캡처 및 연결 영향도 분석 결과
 */
export async function autoCaptureResearchItem(
  accessToken,
  {
    rawContent,
    sourceUrl = null,
    fileName = null,
    fileMimeType = null,
    fileSize = null,
    fileContentBase64 = null,
    runThesisImpact = true,
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/research-memory/auto-capture", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        raw_content: rawContent,
        source_url: sourceUrl,
        file_name: fileName,
        file_mime_type: fileMimeType,
        file_size: fileSize,
        file_content_base64: fileContentBase64,
        run_thesis_impact: runThesisImpact,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("투자 정보를 자동 캡처하는 중 오류 발생:", error);
    return null;
  }
}

export async function previewSourceUrl(accessToken, sourceUrl) {
  return request("/api/v1/source-url/preview", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ source_url: sourceUrl }),
  });
}

export async function fetchNewsInbox(accessToken, limit = 30, filter = "all") {
  const query = new URLSearchParams({
    limit: String(limit),
    filter: filter || "all",
  });
  return request(`/api/v1/news/inbox?${query.toString()}`, {
    method: "GET",
    accessToken,
  });
}

export async function fetchStorageQualityDashboard(accessToken) {
  return request("/api/v1/storage/quality-dashboard", {
    method: "GET",
    accessToken,
  });
}

export async function fetchKcifReportsWatch(accessToken, { limit = 30, refresh = false, saveResult = true } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    refresh: refresh ? "true" : "false",
    save_result: saveResult ? "true" : "false",
  });
  return request(`/api/v1/kcif/reports/watch?${query.toString()}`, {
    method: "GET",
    accessToken,
  });
}

export async function refreshKcifReportsWatch(accessToken, { limit = 30, saveResult = true } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    save_result: saveResult ? "true" : "false",
  });
  return request(`/api/v1/kcif/reports/refresh?${query.toString()}`, {
    method: "POST",
    accessToken,
  });
}

export async function fetchRegionalBusinessSourcesWatch(
  accessToken,
  { limit = 40, refresh = false, saveResult = true } = {}
) {
  const query = new URLSearchParams({
    limit: String(limit),
    refresh: refresh ? "true" : "false",
    save_result: saveResult ? "true" : "false",
  });
  return request(`/api/v1/regional-sources/business/watch?${query.toString()}`, {
    method: "GET",
    accessToken,
  });
}

export async function refreshRegionalBusinessSourcesWatch(
  accessToken,
  { limit = 40, saveResult = true } = {}
) {
  const query = new URLSearchParams({
    limit: String(limit),
    save_result: saveResult ? "true" : "false",
  });
  return request(`/api/v1/regional-sources/business/refresh?${query.toString()}`, {
    method: "POST",
    accessToken,
  });
}

export async function ingestNewsInbox(
  accessToken,
  { rawContent = "", sourceUrl = "", title = "", confidence = 0.78 } = {}
) {
  return request("/api/v1/news/inbox/ingest", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      raw_content: rawContent,
      source_url: sourceUrl,
      title,
      confidence,
    }),
  });
}

export async function promoteNewsInboxItem(accessToken, id) {
  return request("/api/v1/news/inbox/promote", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ id }),
  });
}

export async function updateNewsInboxItem(accessToken, id, action) {
  return request("/api/v1/news/inbox/action", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ id, action }),
  });
}

/**
 * 보유 종목 기반 포트폴리오 리스크 스캔을 실행합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 포트폴리오 입력값
 * @param {string} [params.portfolioName] 포트폴리오 이름
 * @param {Array<Object>} params.holdings 보유 종목 목록
 * @param {number} [params.portfolioValue] 총 포트폴리오 가치
 * @param {number} [params.maxSinglePositionWeight] 단일 종목 최대 허용 비중
 * @param {number} [params.maxSectorWeight] 섹터 최대 허용 비중
 * @param {number} [params.maxThemeWeight] 테마 최대 허용 비중
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 포트폴리오 리스크 스캔 결과
 */
export async function runPortfolioRiskScan(
  accessToken,
  {
    portfolioName = "default",
    holdings,
    portfolioValue = null,
    maxSinglePositionWeight = 0.2,
    maxSectorWeight = 0.35,
    maxThemeWeight = 0.4,
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/portfolio/risk-scan", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        portfolio_name: portfolioName,
        holdings,
        portfolio_value: portfolioValue,
        max_single_position_weight: maxSinglePositionWeight,
        max_sector_weight: maxSectorWeight,
        max_theme_weight: maxThemeWeight,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("포트폴리오 리스크 스캔 중 오류 발생:", error);
    return null;
  }
}

/**
 * 누적 시장일지와 포트폴리오 상태를 바탕으로 강화학습형 정책 최적화 후보를 생성합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 최적화 입력값
 * @param {string} [params.portfolioName] 포트폴리오 이름
 * @param {Array<Object>} [params.holdings] 보유 종목 목록
 * @param {string} [params.marketState] 현재 시장 상태 요약
 * @param {string} [params.objective] 목표 함수
 * @param {string} [params.riskProfile] 위험 성향
 * @param {number} [params.learningHorizonDays] 학습 관찰 기간
 * @param {number} [params.maxPositionWeight] 단일 종목 권장 상한
 * @param {boolean} [params.saveResult] Markdown/JSON 자동 저장 여부
 * @returns {Promise<Object|null>} 강화학습형 정책 최적화 결과
 */
export async function runReinforcementPortfolioOptimizer(
  accessToken,
  {
    portfolioName = "default",
    holdings = [],
    marketState = "",
    objective = "risk_adjusted_return",
    riskProfile = "balanced",
    learningHorizonDays = 90,
    maxPositionWeight = 0.2,
    saveResult = true,
  }
) {
  try {
    return request("/api/v1/portfolio/reinforcement-optimizer", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        portfolio_name: portfolioName,
        holdings,
        market_state: marketState,
        objective,
        risk_profile: riskProfile,
        learning_horizon_days: learningHorizonDays,
        max_position_weight: maxPositionWeight,
        save_result: saveResult,
      }),
    });
  } catch (error) {
    console.error("강화학습형 포트폴리오 최적화 중 오류 발생:", error);
    return null;
  }
}

export async function fetchPortfolios(accessToken) {
  return request("/api/v1/portfolios", {
    method: "GET",
    accessToken,
  });
}

export async function fetchPortfolio(accessToken, portfolioName, options = {}) {
  const params = new URLSearchParams();
  if (Object.prototype.hasOwnProperty.call(options, "refreshPrices")) {
    params.set("refresh_prices", options.refreshPrices ? "true" : "false");
  }
  if (Object.prototype.hasOwnProperty.call(options, "persistRefresh")) {
    params.set("persist_refresh", options.persistRefresh ? "true" : "false");
  }
  const query = params.toString();
  return request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}${query ? `?${query}` : ""}`, {
    method: "GET",
    accessToken,
    signal: options.signal,
  });
}

export async function fetchPortfolioIntelligentTable(accessToken, portfolioName, options = {}) {
  const params = new URLSearchParams();
  if (Object.prototype.hasOwnProperty.call(options, "refreshPrices")) {
    params.set("refresh_prices", options.refreshPrices ? "true" : "false");
  }
  if (Object.prototype.hasOwnProperty.call(options, "forcePriceRefresh")) {
    params.set("force_price_refresh", options.forcePriceRefresh ? "true" : "false");
  }
  if (Object.prototype.hasOwnProperty.call(options, "persistRefresh")) {
    params.set("persist_refresh", options.persistRefresh ? "true" : "false");
  }
  const query = params.toString();
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/intelligent-table${query ? `?${query}` : ""}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchPortfolioPerformance(
  accessToken,
  portfolioName,
  { forcePriceRefresh = false } = {}
) {
  const params = new URLSearchParams({
    force_price_refresh: forcePriceRefresh ? "true" : "false",
  });
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/performance?${params.toString()}`,
    {
      method: "GET",
      accessToken,
      timeoutMs: 30000,
    }
  );
}

export async function fetchTargetConsensusScan(
  accessToken,
  { portfolioName = "__all__", includeInterests = true, refreshMissingPrices = false } = {}
) {
  const query = new URLSearchParams({
    portfolio_name: portfolioName || "__all__",
    include_interests: includeInterests ? "true" : "false",
    refresh_missing_prices: refreshMissingPrices ? "true" : "false",
  });
  return request(`/api/v1/valuation/target-consensus-scan?${query}`, {
    method: "GET",
    accessToken,
  });
}

export async function fetchPortfolioNpsFlow(accessToken, portfolioName) {
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/institutional-flow/nps`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchTickerNpsFlow(accessToken, ticker) {
  return request(`/api/v1/institutional-flow/nps/${encodeURIComponent(ticker)}`, {
    method: "GET",
    accessToken,
  });
}

export async function fetchPortfolioConnectivity(accessToken) {
  return request("/api/v1/portfolios/connectivity", {
    method: "GET",
    accessToken,
  });
}

export async function fetchPortfolioAnalysisStatus(accessToken) {
  return request("/api/v1/portfolios/analysis-status", {
    method: "GET",
    accessToken,
  });
}

export async function fetchPortfolioTeamReportQueue(accessToken) {
  return request("/api/v1/portfolios/team-report-queue", {
    method: "GET",
    accessToken,
  });
}

export async function importPortfolioFile(accessToken, { fileName, contentBase64 }) {
  return request("/api/v1/portfolios/import-file", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      file_name: fileName,
      content_base64: contentBase64,
    }),
  });
}

export async function savePortfolio(
  accessToken,
  {
    portfolioName = "default",
    holdings = [],
    portfolioValue = null,
    maxSinglePositionWeight = 0.2,
    maxSectorWeight = 0.35,
    maxThemeWeight = 0.4,
    notes = "",
  }
) {
  return request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}`, {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      portfolio_name: portfolioName,
      holdings,
      portfolio_value: portfolioValue,
      max_single_position_weight: maxSinglePositionWeight,
      max_sector_weight: maxSectorWeight,
      max_theme_weight: maxThemeWeight,
      notes,
    }),
  });
}

export async function deletePortfolio(accessToken, portfolioName) {
  return request(`/api/v1/portfolios/${encodeURIComponent(portfolioName)}`, {
    method: "DELETE",
    accessToken,
  });
}

export async function syncKiwoomDomesticPortfolio(accessToken, portfolioName) {
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/sync/kiwoom-domestic`,
    {
      method: "POST",
      accessToken,
    }
  );
}

export async function previewKiwoomDomesticPortfolioSync(accessToken, portfolioName) {
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/sync/kiwoom-domestic/preview`,
    {
      method: "POST",
      accessToken,
    }
  );
}

export async function fetchPortfolioSyncHistory(accessToken, portfolioName, { limit = 10 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  return request(
    `/api/v1/portfolios/${encodeURIComponent(portfolioName)}/sync-history?${params.toString()}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchInterests(accessToken) {
  return request("/api/v1/interests", {
    method: "GET",
    accessToken,
  });
}

export async function saveInterests(accessToken, { tickers = [], sectors = [] }) {
  return request("/api/v1/interests", {
    method: "PUT",
    accessToken,
    body: JSON.stringify({ tickers, sectors }),
  });
}

export async function addInterestTicker(accessToken, ticker) {
  return request("/api/v1/interests/tickers", {
    method: "POST",
    accessToken,
    body: JSON.stringify(ticker || {}),
  });
}

export async function addInterestSector(accessToken, sector) {
  return request("/api/v1/interests/sectors", {
    method: "POST",
    accessToken,
    body: JSON.stringify(sector || {}),
  });
}

export async function fetchInterestAutomationBoard(accessToken, saveResult = true) {
  return request(
    `/api/v1/interests/automation-board?save_result=${saveResult ? "true" : "false"}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchMarketCloseJournal(accessToken, market = "ALL") {
  return request(
    `/api/v1/market-close-journal?market=${encodeURIComponent(market)}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchNaverResearchStatus(accessToken) {
  return request("/api/v1/naver-research/status", {
    method: "GET",
    accessToken,
  });
}

export async function repairNaverResearchCache(
  accessToken,
  {
    pdfBackfillLimit = 20,
    refreshMetadata = true,
    saveResult = false,
    archiveDuplicates = false,
  } = {}
) {
  const params = new URLSearchParams();
  params.set("pdf_backfill_limit", String(pdfBackfillLimit));
  params.set("refresh_metadata", refreshMetadata ? "true" : "false");
  params.set("save_result", saveResult ? "true" : "false");
  params.set("archive_duplicates", archiveDuplicates ? "true" : "false");
  return request(`/api/v1/naver-research/repair?${params.toString()}`, {
    method: "POST",
    accessToken,
  });
}

export async function refreshNaverMarketCloseJournal(accessToken, force = true) {
  return request(
    `/api/v1/naver-research/market-close-journal/refresh?force=${force ? "true" : "false"}`,
    {
      method: "POST",
      accessToken,
    }
  );
}

export async function fetchNaverMarketCloseTaskStatus(accessToken, logLimit = 20) {
  return request(
    `/api/v1/naver-research/market-close-journal/task-status?log_limit=${encodeURIComponent(logLimit)}`,
    {
      method: "GET",
      accessToken,
    }
  );
}

export async function fetchCustomsTradeSnapshot(
  accessToken,
  {
    startYymm = "",
    endYymm = "",
    itemCode = "",
    countryCode = "",
    saveResult = true,
  } = {}
) {
  const params = new URLSearchParams();
  if (startYymm) params.set("start_yymm", startYymm);
  if (endYymm) params.set("end_yymm", endYymm);
  if (itemCode) params.set("item_code", itemCode);
  if (countryCode) params.set("country_code", countryCode);
  params.set("save_result", saveResult ? "true" : "false");
  return request(`/api/v1/macro/customs-trade/latest?${params.toString()}`, {
    method: "GET",
    accessToken,
  });
}

export async function saveMarketCloseReview(
  accessToken,
  {
    market = "US",
    sessionDate = null,
    rawSummary,
    sourceUrl = null,
    fileName = null,
    fileMimeType = null,
    fileSize = null,
    fileContentBase64 = null,
    saveResult = true,
  }
) {
  return request("/api/v1/market-close-journal/review", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      market,
      session_date: sessionDate,
      raw_summary: rawSummary,
      source_url: sourceUrl,
      file_name: fileName,
      file_mime_type: fileMimeType,
      file_size: fileSize,
      file_content_base64: fileContentBase64,
      save_result: saveResult,
    }),
  });
}

/**
 * 7개 분석 스킬이 협업하는 종합 분석 보고서를 생성하고 Markdown으로 자동 저장합니다.
 *
 * @param {string} accessToken 앱 로그인 이후 발급받은 사용자 액세스 토큰
 * @param {Object} params 팀 분석 입력값
 * @param {string} params.ticker 분석 대상 티커
 * @param {string} [params.investmentPeriod] 투자 기간
 * @param {string} [params.region] 지역
 * @param {string} [params.style] 투자 스타일
 * @param {string} [params.focusArea] 중점 분석 내용
 * @param {boolean} [params.includeTradeSetup] 매매 전략 포함 여부
 * @param {boolean} [params.includeCompounderScreen] 복리 성장주 스크리닝 포함 여부
 * @param {boolean} [params.autoInjectData] 시장/재무 데이터 자동 주입 여부
 * @param {Array<Object>} [params.realtimeData] 실시간 또는 사용자 주입 데이터
 * @param {boolean} [params.saveResult] Markdown 자동 저장 여부
 * @param {boolean} [params.refreshDossier] 저장 직후 Dossier도 즉시 갱신할지 여부
 * @returns {Promise<Object|null>} 협업 분석 보고서
 */
export async function runCollaborativeTeamReport(
  accessToken,
  {
    ticker,
    investmentPeriod = "3 years",
    region = "US",
    style = "balanced",
    focusArea = null,
    includeTradeSetup = true,
    includeCompounderScreen = true,
    autoInjectData = true,
    realtimeData = [],
    saveResult = true,
    refreshDossier = false,
  }
) {
  try {
    return request("/api/v1/analysis/team-report/run", {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        ticker,
        investment_period: investmentPeriod,
        region,
        style,
        focus_area: focusArea,
        include_trade_setup: includeTradeSetup,
        include_compounder_screen: includeCompounderScreen,
        auto_inject_data: autoInjectData,
        realtime_data: realtimeData,
        save_result: saveResult,
        refresh_dossier: refreshDossier,
      }),
    });
  } catch (error) {
    console.error("협업 분석 보고서를 생성하는 중 오류 발생:", error);
    return null;
  }
}
