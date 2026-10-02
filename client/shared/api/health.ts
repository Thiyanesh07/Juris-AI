/**
 * JURIS AI — SHARED HEALTH API FUNCTIONS
 *
 * Typed wrappers for backend health endpoints.
 * All endpoints verified in server/api/app/api/routes/health.py.
 *
 * Endpoint inventory:
 *   GET /health           → HealthResponse (always 200)
 *   GET /health/database  → DatabaseHealthResponse (200 or 503)
 *
 * Used by the Admin Dashboard to display real backend connectivity status.
 */

import { apiClient } from './client';
import { ApiError } from './errors';
import type { HealthResponse, DatabaseHealthResponse } from './types';
import { API_BASE_URL } from './config';

export type HealthStatus = 'CONNECTED' | 'DEGRADED' | 'NOT_CONNECTED' | 'ERROR';

export interface HealthCheckResult {
  status: HealthStatus;
  detail: string;
  raw?: HealthResponse;
}

/**
 * GET /health
 *
 * Returns overall application health. Never throws — returns ERROR status
 * if the backend is unreachable so the caller can display a clear state.
 */
export async function checkHealth(): Promise<HealthCheckResult> {
  try {
    const health = await apiClient.get<HealthResponse>('/health');
    if (health.status === 'ok') {
      return { status: 'CONNECTED', detail: 'API and database reachable', raw: health };
    }
    return {
      status: 'DEGRADED',
      detail: `API degraded: database ${health.components?.database?.status ?? 'unknown'}`,
      raw: health,
    };
  } catch (err) {
    if (err instanceof ApiError && err.code === 'NETWORK_ERROR') {
      return { status: 'NOT_CONNECTED', detail: 'Backend unreachable' };
    }
    if (err instanceof ApiError) {
      return { status: 'ERROR', detail: err.userMessage };
    }
    return { status: 'ERROR', detail: 'Unexpected error checking health' };
  }
}

/**
 * GET /health/database
 *
 * Returns database-specific health. Returns ERROR status if the endpoint
 * is unreachable rather than throwing.
 */
export async function checkDatabaseHealth(): Promise<{
  status: 'ok' | 'unavailable' | 'error';
  detail: string;
}> {
  try {
    // This endpoint returns 503 when DB is down — apiFetch will throw ApiError
    const data = await apiClient.get<DatabaseHealthResponse>('/health/database');
    return { status: data.status, detail: data.database.error ?? 'ok' };
  } catch (err) {
    if (err instanceof ApiError && err.code === 'SERVICE_UNAVAILABLE') {
      return { status: 'unavailable', detail: 'PostgreSQL is unreachable' };
    }
    if (err instanceof ApiError && err.code === 'NETWORK_ERROR') {
      return { status: 'error', detail: 'Backend unreachable' };
    }
    return { status: 'error', detail: 'Unexpected error' };
  }
}

/**
 * Fetch a health check result without using the shared apiClient.
 * Suitable for Next.js Edge Middleware which cannot use module-level state.
 */
export async function checkHealthRaw(baseUrl: string = API_BASE_URL): Promise<HealthCheckResult> {
  try {
    const res = await fetch(`${baseUrl}/health`, {
      credentials: 'include',
      cache: 'no-store',
    });
    if (!res.ok) {
      return { status: 'ERROR', detail: `HTTP ${res.status}` };
    }
    const health = (await res.json()) as HealthResponse;
    return {
      status: health.status === 'ok' ? 'CONNECTED' : 'DEGRADED',
      detail: health.status,
      raw: health,
    };
  } catch {
    return { status: 'NOT_CONNECTED', detail: 'Backend unreachable' };
  }
}
