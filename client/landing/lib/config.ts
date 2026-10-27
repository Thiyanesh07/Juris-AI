/**
 * JURIS AI — LANDING PORTAL API CONFIGURATION
 *
 * Resolves the backend API base URL from NEXT_PUBLIC_API_URL or defaults to localhost:8000 for local dev.
 * Never hardcodes secrets or environment-specific hosts.
 */

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local');

    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    if (envUrl && envUrl.trim() !== '') {
      return envUrl.trim().replace(/\/+$/, '');
    }
    return isLocal ? 'http://localhost:8000' : '';
  }

  const envUrl = typeof process !== 'undefined' ? process.env.NEXT_PUBLIC_API_URL : undefined;
  if (envUrl && envUrl.trim() !== '') {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://localhost:8000';
}

export function getUserPortalUrl(): string {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local');

    const envUrl = process.env.NEXT_PUBLIC_USER_URL;
    if (envUrl && envUrl.trim() !== '') {
      return envUrl.trim().replace(/\/+$/, '');
    }
    return isLocal ? 'http://localhost:3002' : 'https://juris-ai-user.vercel.app';
  }

  const envUrl = typeof process !== 'undefined' ? process.env.NEXT_PUBLIC_USER_URL : undefined;
  if (envUrl && envUrl.trim() !== '') {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return process.env.NODE_ENV === 'production'
    ? 'https://juris-ai-user.vercel.app'
    : 'http://localhost:3002';
}
