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
