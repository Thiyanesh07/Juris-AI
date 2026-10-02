/**
 * JURIS AI — SHARED AUTHENTICATED API CLIENT
 *
 * Central fetch wrapper for all backend API calls.
 *
 * Key behaviors:
 *  - credentials: 'include'  → forwards HttpOnly session cookie
 *  - Structured error handling → throws ApiError (never swallows)
 *  - 401 handling → throws ApiError with code UNAUTHORIZED
 *  - 403 handling → throws ApiError with code FORBIDDEN
 *  - Network failure → throws ApiError with code NETWORK_ERROR
 *
 * Authentication model:
 *   The backend manages session state via an HttpOnly cookie named
 *   "legalgraph_session". The frontend NEVER reads this cookie.
 *   All auth state is obtained by calling GET /auth/me.
 *
 * Usage:
 *   import { apiClient } from '@/shared/api/client';
 *   const user = await apiClient.get<AuthUser>('/auth/me');
 */

import { API_BASE_URL, JSON_HEADERS, DEFAULT_FETCH_OPTIONS } from './config';
import { ApiError, statusToErrorCode, extractDetail } from './errors';

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

/**
 * Core fetch wrapper. Throws ApiError on any non-2xx response or network failure.
 */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

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
    // Network-level failure (no CORS, connection refused, etc.)
    throw new ApiError(
      'NETWORK_ERROR',
      err instanceof Error ? err.message : 'Network request failed',
      null,
    );
  }

  if (!res.ok) {
    throw await parseError(res);
  }

  // 204 No Content — return undefined cast to T
  if (res.status === 204) {
    return undefined as T;
  }

  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError('SERVER_ERROR', 'Response was not valid JSON', res.status);
  }
}

/**
 * Convenience methods — the primary API surface.
 */
export const apiClient = {
  /** GET request. Returns parsed JSON or throws ApiError. */
  get<T>(path: string, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, { method: 'GET', ...init });
  },

  /** POST request with JSON body. */
  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },

  /** PUT request with JSON body. */
  put<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },

  /** PATCH request with JSON body. */
  patch<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    });
  },

  /** DELETE request. */
  delete<T>(path: string, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, { method: 'DELETE', ...init });
  },

  /**
   * POST with multipart/form-data (file upload).
   * Do not set Content-Type — the browser sets it with the boundary.
   */
  upload<T>(path: string, formData: FormData, init?: RequestInit): Promise<T> {
    return apiFetch<T>(path, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type with boundary
      ...init,
    });
  },
};

export { ApiError } from './errors';
export type { ApiErrorCode } from './errors';
