/**
 * JURIS AI — ADMIN PORTAL AUTH CLIENT (Phase 11 — Backend Integration)
 *
 * All auth API calls go through the backend (FastAPI on :8000).
 * Session cookies are HttpOnly and managed entirely server-side.
 * The frontend never sees the Google client secret.
 *
 * Phase 11 changes:
 *  - Uses portal-local apiAuth.ts (within project root — required for Turbopack)
 *  - fetchCurrentUser returns null on 401 (never throws for unauthenticated)
 *  - signOut calls real backend POST /auth/logout
 *
 * IMPORTANT: The HttpOnly 'legalgraph_session' cookie is NEVER read or written
 * by JavaScript. It is forwarded automatically on every credentials:'include' request.
 */

export type { AuthUser } from './apiTypes';

import type { AuthUser } from './apiTypes';
import { fetchCurrentUser as apiFetchCurrentUser, logout as apiLogout } from './apiAuth';

const _API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/**
 * GET /auth/me
 *
 * Fetch the currently authenticated user from the backend session.
 * Returns null if the session cookie is absent or invalid (401).
 */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  return apiFetchCurrentUser();
}

/**
 * Build the Google OAuth login URL for the admin portal.
 * The backend redirects back to /admin/auth/google/callback after OAuth.
 */
export function getGoogleLoginUrl(returnTo?: string): string {
  const origin =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3001';
  const callbackUrl = `${origin}/admin/auth/google/callback`;
  const base = `${_API_BASE}/auth/google/login?intent=signin&redirect_uri=${encodeURIComponent(callbackUrl)}`;
  if (returnTo) {
    return `${base}&return_to=${encodeURIComponent(returnTo)}`;
  }
  return base;
}

/**
 * POST /auth/logout
 *
 * Sign out — clears the server-side session cookie.
 */
export async function signOut(): Promise<void> {
  return apiLogout();
}

/**
 * Check if a user has at least ADMIN role.
 * Backend returns lowercase: 'admin' | 'super_admin' | 'user'
 */
export function isAdminRole(user: AuthUser | null): boolean {
  if (!user) return false;
  return user.role === 'admin' || user.role === 'super_admin';
}

/**
 * Check if a user has SUPER_ADMIN role.
 */
export function isSuperAdminRole(user: AuthUser | null): boolean {
  if (!user) return false;
  return user.role === 'super_admin';
}

/**
 * Map backend role string to a display label.
 */
export function getRoleLabel(role: AuthUser['role']): string {
  switch (role) {
    case 'super_admin': return 'SUPER ADMIN';
    case 'admin': return 'ADMIN';
    case 'user': return 'USER';
    default: return String(role).toUpperCase();
  }
}
