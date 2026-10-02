/**
 * JURIS AI — SHARED API CONFIGURATION
 *
 * Single source of truth for the backend base URL and request defaults.
 * The backend is always FastAPI on http://localhost:8000 (dev).
 *
 * Set NEXT_PUBLIC_API_URL in each portal's .env.local to override.
 * Never put secrets here.
 */

/**
 * Backend base URL.
 * Reads NEXT_PUBLIC_API_URL from the environment; falls back to localhost:8000.
 */
export const API_BASE_URL: string =
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) ||
  'http://localhost:8000';

/**
 * Default headers for JSON API requests.
 */
export const JSON_HEADERS: HeadersInit = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

/**
 * Default fetch options shared by all authenticated requests.
 * credentials: 'include' forwards the HttpOnly session cookie.
 */
export const DEFAULT_FETCH_OPTIONS: RequestInit = {
  credentials: 'include',
  cache: 'no-store',
};
