/**
 * JURIS AI — ADMIN PORTAL API CLIENT
 *
 * Inline copy of shared/api/client.ts for Turbopack compatibility.
 * Canonical source: client/shared/api/client.ts
 *
 * Key behaviors:
 *  - credentials: 'include' → forwards HttpOnly session cookie
 *  - Structured error handling → throws ApiError (never swallows)
 *  - 401 handling → throws ApiError with code UNAUTHORIZED
 *  - Network failure → throws ApiError with code NETWORK_ERROR
 */

import { ApiError, statusToErrorCode, extractDetail } from './apiErrors';

export function getApiBaseUrl(): string {
  // 1. Browser runtime check
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local');

    if (!isLocal) {
      const envUrl = process.env.NEXT_PUBLIC_API_URL;
      if (envUrl && envUrl.trim() !== '' && !envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
        return envUrl.trim().replace(/\/+$/, '');
      }
      return 'https://juris-ai-fhjw.onrender.com';
    }

    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envUrl && envUrl.trim() !== '') {
      return envUrl.trim().replace(/\/+$/, '');
    }
    return 'http://localhost:8000';
  }

  // 2. Server-side / Node / Build-time check
  const envUrl = typeof process !== 'undefined' ? process.env.NEXT_PUBLIC_API_URL : undefined;
  if (typeof process !== 'undefined' && process.env.NODE_ENV === 'production') {
    if (envUrl && envUrl.trim() !== '' && !envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
      return envUrl.trim().replace(/\/+$/, '');
    }
    return 'https://juris-ai-fhjw.onrender.com';
  }

  if (envUrl && envUrl.trim() !== '') {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://localhost:8000';
}

export const API_BASE_URL: string = getApiBaseUrl();

const JSON_HEADERS: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

const DEFAULT_FETCH_OPTIONS: RequestInit = {
  credentials: 'include',
  cache: 'no-store',
};

async function parseError(res: Response): Promise<ApiError> {
  const code = statusToErrorCode(res.status);
  let detail: string | string[];
  try {
    const body: unknown = await res.json();
    detail = extractDetail(body);
  } catch {
    detail = res.statusText || `HTTP ${res.status}`;
  }
  return new ApiError(code, detail, res.status);
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...DEFAULT_FETCH_OPTIONS,
      ...init,
      headers: {
        ...JSON_HEADERS,
        ...(init.headers ?? {}),
      },
    });
  } catch (err) {
    throw new ApiError(
      'NETWORK_ERROR',
      err instanceof Error ? err.message : 'Network request failed',
      null,
    );
  }

  if (!res.ok) {
    throw await parseError(res);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError('SERVER_ERROR', 'Response was not valid JSON', res.status);
  }
}

export const apiClient = {
  get<T>(path: string, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, { method: 'GET', ...init });
  },
  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },
  put<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },
  patch<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },
  delete<T>(path: string, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, { method: 'DELETE', ...init });
  },
  upload<T>(path: string, formData: FormData, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'POST',
      body: formData,
      headers: {},
      ...init,
    });
  },
};

export { ApiError } from './apiErrors';
export type { ApiErrorCode } from './apiErrors';
