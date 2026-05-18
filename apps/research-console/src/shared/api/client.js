const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001";

export class ApiError extends Error {
  constructor(message, { status = 0, payload = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function createApiClient({
  baseUrl = DEFAULT_API_BASE_URL,
  accessToken = "dev-local-token",
  fetchImpl = globalThis.fetch,
} = {}) {
  let currentBaseUrl = normalizeBaseUrl(baseUrl);
  let currentAccessToken = accessToken;

  async function request(path, { method = "GET", body = null, headers = {} } = {}) {
    if (!fetchImpl) {
      throw new ApiError("fetch 구현체를 찾을 수 없습니다.");
    }
    const response = await fetchImpl(`${currentBaseUrl}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(currentAccessToken ? { Authorization: `Bearer ${currentAccessToken}` } : {}),
        ...headers,
      },
      body,
    });
    const payload = await parseResponse(response);
    if (!response.ok) {
      throw new ApiError(resolveErrorMessage(response, payload), {
        status: response.status,
        payload,
      });
    }
    return payload;
  }

  return {
    request,
    setBaseUrl(nextBaseUrl) {
      currentBaseUrl = normalizeBaseUrl(nextBaseUrl);
    },
    setAccessToken(nextAccessToken) {
      currentAccessToken = String(nextAccessToken || "").trim();
    },
    get baseUrl() {
      return currentBaseUrl;
    },
  };
}

function normalizeBaseUrl(value) {
  const trimmed = String(value || DEFAULT_API_BASE_URL).trim();
  return trimmed.replace(/\/+$/, "");
}

async function parseResponse(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function resolveErrorMessage(response, payload) {
  if (payload && typeof payload === "object" && payload.detail) {
    return typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }
  return `HTTP ${response.status} ${response.statusText}`.trim();
}
