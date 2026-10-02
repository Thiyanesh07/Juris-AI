/**
 * JURIS AI — SHARED AUTH API FUNCTIONS
 *
 * Typed wrappers for backend auth endpoints.
 * All endpoints verified to exist in server/api/app/api/routes/auth.py.
 *
 * Endpoint inventory:
 *   GET  /auth/me          → CurrentUserResponse (AuthUser)
 *   POST /auth/login       → CurrentUserResponse (AuthUser)
 *   POST /auth/register    → CurrentUserResponse (AuthUser) [201]
 *   POST /auth/logout      → 204 No Content
 *   GET  /auth/google/login  → redirect or { url: string }
 *   GET  /auth/google/callback → CurrentUserResponse (AuthUser)
 */

import { apiClient } from './client';
import { ApiError } from './errors';
import type { AuthUser } from './types';
import { API_BASE_URL } from './config';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

/**
 * GET /auth/me
 *
 * Returns the currently authenticated user, or null on 401.
 * Never throws for 401 — treats it as "not authenticated".
 * Does throw for other errors (network, 403, 5xx).
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
 * POST /auth/login
 *
 * Email/password login. Sets the session cookie server-side.
 * Returns the authenticated user on success.
 * Throws ApiError on invalid credentials (401) or disabled account (403).
 */
export async function loginWithPassword(body: LoginRequest): Promise<AuthUser> {
  return apiClient.post<AuthUser>('/auth/login', body);
}

/**
 * POST /auth/register
 *
 * Create a new user account. Sets the session cookie server-side.
 * Throws ApiError with code CONFLICT (409) if email already exists.
 */
export async function registerUser(body: RegisterRequest): Promise<AuthUser> {
  return apiClient.post<AuthUser>('/auth/register', body);
}

/**
 * POST /auth/logout
 *
 * Clears the server-side session. Returns void on success.
 */
export async function logout(): Promise<void> {
  await apiClient.post<void>('/auth/logout');
}

/**
 * Build the Google OAuth login URL.
 *
 * The backend at GET /auth/google/login accepts:
 *   - intent: 'signin' | 'signup'
 *   - redirect_uri: the callback URL the backend should redirect to after OAuth
 *   - state: optional opaque state string
 *
 * The frontend redirects the browser to this URL to initiate the OAuth flow.
 */
export function buildGoogleLoginUrl(
  intent: 'signin' | 'signup',
  callbackOrigin: string,
  callbackPath: string = '/auth/google/callback',
): string {
  const redirectUri = encodeURIComponent(`${callbackOrigin}${callbackPath}`);
  return `${API_BASE_URL}/auth/google/login?intent=${intent}&redirect_uri=${redirectUri}`;
}

/**
 * Build the Google OAuth login URL for the admin portal.
 * Uses /admin/auth/google/callback as the callback path.
 */
export function buildAdminGoogleLoginUrl(origin: string): string {
  return buildGoogleLoginUrl('signin', origin, '/admin/auth/google/callback');
}
