/**
 * JURIS AI — ADMIN PORTAL AUTH API FUNCTIONS
 *
 * Typed wrappers for backend auth endpoints.
 * Inline implementation for Turbopack (Next.js 16) compatibility.
 * Canonical source: client/shared/api/auth.ts
 */

import { apiClient, ApiError } from './apiClient';
import type { AuthUser } from './apiTypes';

export type { AuthUser };

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
 * Throws for other errors (network, 5xx).
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
 * Returns the authenticated user on success.
 */
export async function loginWithPassword(body: LoginRequest): Promise<AuthUser> {
  return apiClient.post<AuthUser>('/auth/login', body);
}

/**
 * POST /auth/register
 */
export async function registerUser(body: RegisterRequest): Promise<AuthUser> {
  return apiClient.post<AuthUser>('/auth/register', body);
}

/**
 * POST /auth/logout
 */
export async function logout(): Promise<void> {
  await apiClient.post<void>('/auth/logout');
}

import { getApiBaseUrl } from './apiClient';

const API_BASE_URL = getApiBaseUrl();

export function buildGoogleLoginUrl(
  intent: 'signin' | 'signup',
  callbackOrigin: string,
  callbackPath = '/auth/google/callback',
): string {
  const redirectUri = encodeURIComponent(`${callbackOrigin}${callbackPath}`);
  return `${API_BASE_URL}/auth/google/login?intent=${intent}&redirect_uri=${redirectUri}`;
}
