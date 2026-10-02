/**
 * JURIS AI — ADMIN PORTAL API SERVICE (Phase 11 — Backend Integration Foundation)
 *
 * Portal-local API boundary for the admin UI.
 * All imports from @/lib/* (within project root — required for Turbopack).
 *
 * ── INTEGRATION STATUS ────────────────────────────────────────────────────────
 *
 * REAL (backend endpoint exists and is integrated):
 *   ✅ auth.me              GET  /auth/me
 *   ✅ auth.logout          POST /auth/logout
 *   ✅ health.check         GET  /health
 *   ✅ documents.list       GET  /documents
 *   ✅ documents.get        GET  /documents/{id}
 *   ✅ documents.upload     POST /documents/upload  (ADMIN only)
 *   ✅ documents.reprocess  POST /documents/{id}/reprocess  (ADMIN only)
 *   ✅ documents.chunks     GET  /documents/{id}/chunks
 *   ✅ documents.jobs       GET  /documents/{id}/jobs
 *   ✅ evaluation.list      GET  /evaluation  (ADMIN only)
 *   ✅ evaluation.get       GET  /evaluation/{id}  (ADMIN only)
 *
 * MOCK (no backend endpoint exists yet):
 *   🔲 users.list      — no /users endpoint in backend
 *   🔲 users.getById   — no /users/{id} endpoint in backend
 *   🔲 graph.getNodes  — no graph HTTP endpoints (Neo4j used internally only)
 *   🔲 graph.getEdges  — no graph HTTP endpoints
 *   🔲 validation.list — no /validation endpoint in backend
 *   🔲 audit.list      — no /audit endpoint in backend
 *   🔲 settings.get    — no /settings endpoint in backend
 * ─────────────────────────────────────────────────────────────────────────────
 */

import {
  listDocuments,
  getDocument,
  getDocumentChunks,
  getDocumentJobs,
  uploadDocument,
  reprocessDocument,
} from './apiDocuments';

import { checkHealth } from './health';
import { listEvaluationRuns, getEvaluationRun } from './apiEvaluation';

import {
  User,
  GraphNode,
  GraphEdge,
  ValidationItem,
  AuditEvent,
  SystemSettingSection,
} from './types';

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ── Real Backend API ──────────────────────────────────────────────────────────

/** Documents API — real backend */
export const documentsApi = {
  list: listDocuments,
  get: getDocument,
  getChunks: getDocumentChunks,
  getJobs: getDocumentJobs,
  upload: uploadDocument,
  reprocess: reprocessDocument,
};

/** Health API — real backend */
export const healthApi = {
  check: checkHealth,
};

/** Evaluation API — real backend */
export const evaluationApi = {
  list: listEvaluationRuns,
  get: getEvaluationRun,
};

// ── Mock API Boundaries (pending backend implementation) ─────────────────────

/** Users API — MOCK: no /users endpoint exists in backend yet */
export const usersApi = {
  list: async (): Promise<PaginatedResult<User>> => {
    return { items: [], total: 0, page: 1, pageSize: 10 };
  },
  getById: async (_id: string): Promise<User | null> => {
    return null;
  },
};

/** Graph API — MOCK: no graph HTTP endpoints exist (Neo4j used internally) */
export const graphApi = {
  getNodes: async (): Promise<GraphNode[]> => {
    return [];
  },
  getEdges: async (): Promise<GraphEdge[]> => {
    return [];
  },
};

/** Validation API — MOCK: no /validation endpoint exists in backend yet */
export const validationApi = {
  listPending: async (): Promise<ValidationItem[]> => {
    return [];
  },
};

/** Audit API — MOCK: no /audit endpoint exists in backend yet */
export const auditApi = {
  listEvents: async (): Promise<PaginatedResult<AuditEvent>> => {
    return { items: [], total: 0, page: 1, pageSize: 10 };
  },
};

/** Settings API — MOCK: no /settings endpoint exists in backend yet */
export const settingsApi = {
  getSections: async (): Promise<SystemSettingSection[]> => {
    return [];
  },
};

/**
 * Legacy combined api object — preserved for backward compatibility.
 * @deprecated Use the named exports (documentsApi, healthApi, etc.) instead.
 */
export const api = {
  users: usersApi,
  documents: {
    list: async () => {
      const result = await listDocuments();
      return {
        items: result.items,
        total: result.total,
        page: result.page,
        pageSize: result.page_size,
      };
    },
  },
  ingestion: {
    listJobs: async (): Promise<PaginatedResult<{ id: string; documentId: string; documentTitle: string; status: string }>> => {
      return { items: [], total: 0, page: 1, pageSize: 10 };
    },
  },
  graph: graphApi,
  validation: validationApi,
  audit: auditApi,
  settings: settingsApi,
};
