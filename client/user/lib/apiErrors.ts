/**
 * JURIS AI — USER PORTAL API ERRORS
 *
 * Inline copy of shared/api/errors.ts for Turbopack (Next.js 16) compatibility.
 * Canonical source: client/shared/api/errors.ts
 */

export type ApiErrorCode =
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED'
  | 'SERVER_ERROR'
  | 'SERVICE_UNAVAILABLE'
  | 'NETWORK_ERROR'
  | 'UNKNOWN';

export class ApiError extends Error {
  public readonly code: ApiErrorCode;
  public readonly status: number | null;
  public readonly detail: string | string[];

  constructor(code: ApiErrorCode, detail: string | string[], status: number | null = null) {
    const message = typeof detail === 'string' ? detail : detail.join('; ');
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.detail = detail;
  }

  get isUnauthenticated(): boolean { return this.code === 'UNAUTHORIZED'; }
  get isForbidden(): boolean { return this.code === 'FORBIDDEN'; }

  get userMessage(): string {
    switch (this.code) {
      case 'UNAUTHORIZED': return 'Your session has expired. Please sign in again.';
      case 'FORBIDDEN': return 'You do not have permission to perform this action.';
      case 'NOT_FOUND': return 'The requested resource was not found.';
      case 'CONFLICT': return 'This resource already exists.';
      case 'VALIDATION_ERROR': return typeof this.detail === 'string' ? this.detail : `Validation error: ${this.detail.join(', ')}`;
      case 'RATE_LIMITED': return 'Too many requests. Please wait a moment and try again.';
      case 'SERVER_ERROR': return 'An unexpected server error occurred. Please try again.';
      case 'SERVICE_UNAVAILABLE': return 'A backend service is temporarily unavailable.';
      case 'NETWORK_ERROR': return 'Could not reach the server. Check your network connection.';
      default: return 'An unexpected error occurred.';
    }
  }
}

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

export function extractDetail(body: unknown): string | string[] {
  if (!body || typeof body !== 'object') return 'Request failed';
  const b = body as Record<string, unknown>;
  if (Array.isArray(b['detail'])) {
    return (b['detail'] as Array<{ msg?: string; message?: string }>).map(
      (e) => e.msg ?? e.message ?? JSON.stringify(e),
    );
  }
  if (typeof b['detail'] === 'string') return b['detail'];
  if (typeof b['message'] === 'string') return b['message'];
  return 'Request failed';
}
