/**
 * JURIS AI — SHARED API ERROR TYPES
 *
 * Structured error hierarchy for all API responses.
 * Used across admin, user, and landing portals.
 */

/** HTTP status codes we handle explicitly */
export type ApiErrorCode =
  | 'UNAUTHORIZED'      // 401 — not authenticated
  | 'FORBIDDEN'         // 403 — authenticated but insufficient role/permission
  | 'NOT_FOUND'         // 404 — resource does not exist
  | 'CONFLICT'          // 409 — duplicate resource
  | 'VALIDATION_ERROR'  // 422 — request body failed validation
  | 'RATE_LIMITED'      // 429 — too many requests
  | 'SERVER_ERROR'      // 500+ — unexpected backend failure
  | 'SERVICE_UNAVAILABLE' // 503 — backend dependency (DB/Neo4j) unreachable
  | 'NETWORK_ERROR'     // network failure / CORS
  | 'UNKNOWN';          // any other status

export class ApiError extends Error {
  public readonly code: ApiErrorCode;
  public readonly status: number | null;
  public readonly detail: string | string[];

  constructor(
    code: ApiErrorCode,
    detail: string | string[],
    status: number | null = null,
  ) {
    const message =
      typeof detail === 'string' ? detail : detail.join('; ');
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.detail = detail;
  }

  /** True when the session has expired or was never established. */
  get isUnauthenticated(): boolean {
    return this.code === 'UNAUTHORIZED';
  }

  /** True when the session is valid but the role is insufficient. */
  get isForbidden(): boolean {
    return this.code === 'FORBIDDEN';
  }

  /** User-facing message suitable for display in a toast or error banner. */
  get userMessage(): string {
    switch (this.code) {
      case 'UNAUTHORIZED':
        return 'Your session has expired. Please sign in again.';
      case 'FORBIDDEN':
        return 'You do not have permission to perform this action.';
      case 'NOT_FOUND':
        return 'The requested resource was not found.';
      case 'CONFLICT':
        return 'This resource already exists.';
      case 'VALIDATION_ERROR':
        return typeof this.detail === 'string'
          ? this.detail
          : `Validation error: ${this.detail.join(', ')}`;
      case 'RATE_LIMITED':
        return 'Too many requests. Please wait a moment and try again.';
      case 'SERVER_ERROR':
        return 'An unexpected server error occurred. Please try again.';
      case 'SERVICE_UNAVAILABLE':
        return 'A backend service is temporarily unavailable. Please try again shortly.';
      case 'NETWORK_ERROR':
        return 'Could not reach the server. Check your network connection.';
      default:
        return 'An unexpected error occurred.';
    }
  }
}

/**
 * Map an HTTP status code to an ApiErrorCode.
 */
export function statusToErrorCode(status: number): ApiErrorCode {
  if (status === 401) return 'UNAUTHORIZED';
  if (status === 403) return 'FORBIDDEN';
  if (status === 404) return 'NOT_FOUND';
  if (status === 409) return 'CONFLICT';
  if (status === 422) return 'VALIDATION_ERROR';
  if (status === 429) return 'RATE_LIMITED';
  if (status === 503) return 'SERVICE_UNAVAILABLE';
  if (status >= 500) return 'SERVER_ERROR';
  return 'UNKNOWN';
}

/**
 * Extract a readable detail message from a FastAPI error response body.
 * FastAPI 422 errors put field errors inside `detail` as an array.
 */
export function extractDetail(body: unknown): string | string[] {
  if (!body || typeof body !== 'object') return 'Request failed';
  const b = body as Record<string, unknown>;

  if (Array.isArray(b['detail'])) {
    // FastAPI validation errors: [{loc, msg, type}]
    return (b['detail'] as Array<{ msg?: string; message?: string }>).map(
      (e) => e.msg ?? e.message ?? JSON.stringify(e),
    );
  }

  if (typeof b['detail'] === 'string') return b['detail'];
  if (typeof b['message'] === 'string') return b['message'];
  return 'Request failed';
}
