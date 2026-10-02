/**
 * JURIS AI — SHARED API LAYER
 *
 * Central export for all shared API infrastructure.
 *
 * Usage in portals:
 *   import { apiClient, fetchCurrentUser, ApiError } from '@/shared/api';
 *
 * Or import specific modules:
 *   import { submitLegalQuery } from '@/shared/api/research';
 *   import { listDocuments } from '@/shared/api/documents';
 *   import { checkHealth } from '@/shared/api/health';
 */

// Core infrastructure
export { apiClient, apiFetch } from './client';
export { ApiError } from './errors';
export type { ApiErrorCode } from './errors';
export { API_BASE_URL } from './config';

// Types
export type {
  AuthUser,
  BackendUserRole,
  DocumentSummary,
  DocumentDetail,
  DocumentUploadResponse,
  ReprocessResponse,
  DocumentChunk,
  PaginatedChunks,
  ProcessingJob,
  PaginatedDocuments,
  HealthResponse,
  DatabaseHealthResponse,
  DatabaseComponent,
  RetrievalRequest,
  RetrievalEvidence,
  RetrievalResponse,
  HybridRetrievalRequest,
  HybridEvidence,
  HybridGraphContext,
  HybridGraphEntityContext,
  HybridRetrievalResponse,
  QAAskRequest,
  QAAskResponse,
  QACitation,
  QARetrievalMeta,
  EvaluationRun,
  PaginatedEvaluationRuns,
  Paginated,
} from './types';

// Utility functions
export { normalizeRoleToUppercase, normalizeRoleToLowercase } from './types';

// Auth API
export {
  fetchCurrentUser,
  loginWithPassword,
  registerUser,
  logout,
  buildGoogleLoginUrl,
  buildAdminGoogleLoginUrl,
} from './auth';

// Health API
export {
  checkHealth,
  checkDatabaseHealth,
  checkHealthRaw,
} from './health';
export type { HealthStatus, HealthCheckResult } from './health';

// Documents API
export {
  listDocuments,
  getDocument,
  getDocumentChunks,
  getDocumentJobs,
  uploadDocument,
  reprocessDocument,
} from './documents';

// Research API
export {
  submitLegalQuery,
  denseSearch,
  hybridSearch,
  rebuildVectorIndex,
} from './research';

// Evaluation API
export {
  listEvaluationRuns,
  getEvaluationRun,
} from './evaluation';
