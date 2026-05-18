const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

/**
 * React Native에서는 실제 기기와 로컬 PC가 다른 네트워크 주소를 사용합니다.
 * 개발 기기에서는 API_BASE_URL에 PC의 내부 IP를 넣어 호출하세요.
 */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.accessToken
        ? { Authorization: `Bearer ${options.accessToken}` }
        : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    throw new ApiError(`HTTP error: ${response.status}`, response.status);
  }

  return response.json();
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

export async function fetchKiwoomBalance(accessToken) {
  try {
    return request("/api/v1/brokerage/kiwoom/balance-test", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("잔고/보유종목을 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchKiwoomTradeJournal(accessToken) {
  try {
    return request("/api/v1/brokerage/kiwoom/trade-journal-test", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("당일 매매일지를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchKiwoomOrderExecutions(accessToken) {
  try {
    return request("/api/v1/brokerage/kiwoom/order-executions-test", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("주문/체결 상세를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchPortfolio(accessToken) {
  try {
    return request("/api/v1/portfolio", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("포트폴리오를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchJournalSourceTrades(accessToken, params = {}) {
  const searchParams = new URLSearchParams();
  if (params.baseDate) {
    searchParams.set("base_date", params.baseDate);
  }
  if (params.orderDate) {
    searchParams.set("order_date", params.orderDate);
  }

  const query = searchParams.toString();
  const path = query
    ? `/api/v1/journal/source-trades?${query}`
    : "/api/v1/journal/source-trades";

  try {
    return request(path, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("매매일지 원천 데이터를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function syncKiwoomData(accessToken) {
  try {
    return request("/api/v1/sync/kiwoom", {
      method: "POST",
      accessToken,
    });
  } catch (error) {
    console.error("키움 데이터를 동기화하는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchLatestSync(accessToken) {
  try {
    return request("/api/v1/sync/latest", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("최근 동기화 상태를 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchJournalDrafts(accessToken, limit = 50) {
  try {
    return request(`/api/v1/journal/drafts?limit=${limit}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("매매일지 초안을 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function saveJournalEntry(accessToken, entry) {
  try {
    return request("/api/v1/journal/entries", {
      method: "POST",
      accessToken,
      body: JSON.stringify(entry),
    });
  } catch (error) {
    console.error("매매일지를 저장하는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchJournalEntries(accessToken, limit = 50) {
  try {
    return request(`/api/v1/journal/entries?limit=${limit}`, {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("매매일지 목록을 불러오는 중 오류 발생:", error);
    return null;
  }
}

export async function fetchJournalAnalytics(accessToken) {
  try {
    return request("/api/v1/analytics/journal", {
      method: "GET",
      accessToken,
    });
  } catch (error) {
    console.error("매매일지 분석을 불러오는 중 오류 발생:", error);
    return null;
  }
}
