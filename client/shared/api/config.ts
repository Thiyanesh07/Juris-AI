/**
 * JURIS AI — SHARED API CONFIGURATION
 *
 * Single source of truth for the backend base URL and request defaults.
 * The backend is always FastAPI on http://localhost:8000 (dev).
 *
 * Set NEXT_PUBLIC_API_URL in each portal's .env.local to override.
 * Never put secrets here.
 */

export function getApiBaseUrl(): string {
  const envUrl = typeof process !== 'undefined' ? process.env.NEXT_PUBLIC_API_URL : undefined;
  if (envUrl && envUrl.trim() !== '') {
    return envUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return 'https://juris-ai-fhjw.onrender.com';
    }
  } else if (typeof process !== 'undefined' && process.env.NODE_ENV === 'production') {
    return 'https://juris-ai-fhjw.onrender.com';
  }
  return 'http://localhost:8000';
}

export const API_BASE_URL: string = getApiBaseUrl();

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
