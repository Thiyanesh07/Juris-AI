/**
 * JURIS AI — ADMIN ROUTE CONSTANTS & BUILDERS
 */

export const ADMIN_ROUTES = {
  // Authentication
  LOGIN: '/admin/login',

  // Core App Routes
  DASHBOARD: '/admin',
  USERS: '/admin/users',
  USER_NEW: '/admin/users/new',
  ADMINS: '/admin/admins',
  ADMIN_NEW: '/admin/admins/new',
  DOCUMENTS: '/admin/documents',
  INGESTION: '/admin/ingestion',
  GRAPH: '/admin/graph',
  VALIDATION: '/admin/validation',
  AUDIT: '/admin/audit',
  SETTINGS: '/admin/settings',
} as const;

export const ADMIN_DYNAMIC_ROUTES = {
  USER_DETAIL: (id: string) => `/admin/users/${id}`,
  USER_EDIT: (id: string) => `/admin/users/${id}/edit`,

  ADMIN_DETAIL: (id: string) => `/admin/admins/${id}`,
  ADMIN_EDIT: (id: string) => `/admin/admins/${id}/edit`,

  DOCUMENT_DETAIL: (id: string) => `/admin/documents/${id}`,

  INGESTION_JOB_DETAIL: (jobId: string) => `/admin/ingestion/${jobId}`,

  GRAPH_ENTITY_DETAIL: (id: string) => `/admin/graph/entity/${id}`,
  GRAPH_RELATIONSHIP_DETAIL: (id: string) => `/admin/graph/relationship/${id}`,

  AUDIT_EVENT_DETAIL: (eventId: string) => `/admin/audit/${eventId}`,
} as const;
