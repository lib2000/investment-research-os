const DEFAULT_API_BASE_URL = "http://127.0.0.1:8010";
const DEFAULT_DEV_TOKEN = "dev-local-token";

export const apiConfig = {
  baseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL,
  token: process.env.EXPO_PUBLIC_DEV_USER_TOKEN || DEFAULT_DEV_TOKEN,
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function throwIfNotOk(response: Response): Promise<void> {
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    let code = `HTTP_${response.status}`;
    try {
      const payload = await response.json();
      message = payload?.error?.message || payload?.detail || message;
      code = payload?.error?.code || code;
    } catch {
      // Keep the HTTP status fallback when the response body is not JSON.
    }
    throw new ApiError(response.status, code, message);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  await throwIfNotOk(response);

  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiConfig.token}`,
    },
  });

  return parseResponse<T>(response);
}

export async function apiGetText(path: string): Promise<string> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    headers: {
      Accept: "text/csv, text/plain, */*",
      Authorization: `Bearer ${apiConfig.token}`,
    },
  });

  await throwIfNotOk(response);
  return response.text();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiConfig.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return parseResponse<T>(response);
}

export async function apiPostText<T>(
  path: string,
  body: string,
  contentType = "text/csv; charset=utf-8",
): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiConfig.token}`,
      "Content-Type": contentType,
    },
    body,
  });

  return parseResponse<T>(response);
}

export async function apiPostFormData<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiConfig.token}`,
    },
    body,
  });

  return parseResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiConfig.token}`,
    },
  });

  return parseResponse<T>(response);
}
