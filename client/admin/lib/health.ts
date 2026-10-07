/**
 * JURIS AI — ADMIN PORTAL HEALTH API
 *
 * Typed wrappers for backend health endpoints.
 * Inline implementation for Turbopack (Next.js 16) compatibility.
 * Canonical source: client/shared/api/health.ts
 *
 * Real backend endpoints:
 *   GET /health           → HealthResponse (always 200)
 *   GET /health/database  → DatabaseHealthResponse (200 or 503)
 */

import { apiClient, ApiError } from './apiClient';
import type { HealthResponse, DatabaseHealthResponse } from './apiTypes';

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
    const isOk = health.status === 'ok';
    return {
      status: isOk ? 'CONNECTED' : 'DEGRADED',
      detail: isOk ? 'All core infrastructure services connected' : 'One or more backend components degraded',
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
 * GET /stats or GET /public/stats
 */
export async function fetchPublicStats() {
  try {
    return await apiClient.get<import('./apiTypes').PublicStatsResponse>('/stats');
  } catch {
    return null;
  }
}

/**
 * GET /health/database
 *
 * Returns database-specific health.
 */
export async function checkDatabaseHealth(): Promise<{
  status: 'ok' | 'unavailable' | 'error';
  detail: string;
}> {
  try {
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
