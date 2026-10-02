/**
 * JURIS AI — USER PORTAL AUTH CLIENT (Phase 11 — Backend Integration)
 *
 * Handles Google OAuth and session verification against backend (FastAPI).
 * Session cookies are HttpOnly and set by backend upon OAuth completion.
 *
 * Uses portal-local apiClient.ts (within project root — required for Turbopack).
 *
 * IMPORTANT: The HttpOnly 'legalgraph_session' cookie is NEVER read or written
 * by JavaScript. It is forwarded automatically on every credentials:'include' request.
 */

import { apiClient, ApiError } from './apiClient';

const _API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type BackendUserRole = 'user' | 'admin' | 'super_admin';

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  image_url: string | null;
  role: BackendUserRole;
  is_active: boolean;
  last_login_at: string | null;
}

/**
 * GET /auth/me
 *
 * Returns the currently authenticated user, or null on 401.
 * Throws on network failure or 5xx errors.
 */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  try {
    return await apiClient.get<AuthUser>('/auth/me');
  } catch (err) {
    if (err instanceof ApiError && err.code === 'UNAUTHORIZED') {
      return null;
    }
    throw err;
  }
}

/**
 * POST /auth/logout
 *
 * Clears the server-side session. Returns true on success.
 */
export async function signOut(): Promise<boolean> {
  try {
    await apiClient.post<void>('/auth/logout');
    return true;
  } catch {
    return false;
  }
}

/**
 * Build the Google OAuth login URL for the user portal.
 *
 * @param redirectPath  Optional path to redirect to after login (e.g. '/research')
 * @param intent        'signin' or 'signup'
 */
export function getGoogleLoginUrl(
  redirectPath?: string,
  intent: 'signin' | 'signup' = 'signin',
): string {
  const origin =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3002';
  const callbackUrl = `${origin}/auth/google/callback`;
  const state = redirectPath ? encodeURIComponent(redirectPath) : '';
  return `${_API_BASE}/auth/google/login?redirect_uri=${encodeURIComponent(callbackUrl)}&state=${state}&intent=${intent}`;
}
