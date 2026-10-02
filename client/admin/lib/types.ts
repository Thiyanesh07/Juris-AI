/**
 * JURIS AI — ADMIN PORTAL DOMAIN TYPES
 * Phase 2, Phase 5 & Phase 7 Architecture Specification
 */

export type UserRole = 'USER' | 'ADMIN' | 'SUPER_ADMIN';

export type UserStatus = 'ACTIVE' | 'INACTIVE' | 'PENDING' | 'SUSPENDED';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  status: UserStatus;
  organization?: string;
  createdAt: string;
  lastActiveAt?: string;
  avatarUrl?: string;
  isProtected?: boolean;
}

export type DocumentTypeCategory =
  | 'Constitution'
  | 'Act'
  | 'Amendment Act'
  | 'Rule'
  | 'Regulation'
  | 'Judgment'
  | 'Notification'
  | 'Other';

export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED' | 'ARCHIVED';

export interface Document {
  id: string;
  title: string;
  fileName: string;
  fileSizeBytes: number;
  mimeType: string;
  documentType: DocumentTypeCategory;
  source: string;
  authority?: string;
  jurisdiction?: string;
  publicationDate?: string;
  effectiveDate?: string;
  version?: string;
  status: DocumentStatus;
  pageCount?: number;
  uploadedBy: string;
  createdAt: string;
  updatedAt: string;
  latestJobId?: string;
}

export type IngestionJobStatus =
  | 'QUEUED'
  | 'PARSING'
  | 'EXTRACTING_ENTITIES'
  | 'BUILDING_INDEX'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface IngestionJob {
  id: string;
  documentId: string;
  documentTitle: string;
  status: IngestionJobStatus;
  progressPercentage: number;
  workerNode?: string; // e.g. 'worker-01', 'worker-02', 'worker-03', 'worker-04' (CPU-compatible)
  chunksCount?: number;
  entitiesExtractedCount?: number;
  relationshipsExtractedCount?: number;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string; // e.g., 'Statute', 'Precedent', 'Court', 'Judge', 'Party'
  properties: Record<string, unknown>;
  degree?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string; // e.g., 'CITES', 'OVERRULES', 'APPLIES', 'MODIFIES'
  weight?: number;
  properties?: Record<string, unknown>;
}

export type ValidationCategory = 'ENTITY' | 'RELATIONSHIP' | 'CITATION' | 'DOCUMENT_METADATA';

export type ValidationStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface ValidationItem {
  id: string;
  title: string;
  itemType: ValidationCategory;
  sourceDocumentId: string;
  sourceDocumentTitle: string;
  sourceLocation?: string;
  sourceTextSnippet: string;
  proposedLabel: string;
  confidenceScore: number; // Percentage e.g. 98, 91, 84, 72
  status: ValidationStatus;
  createdAt: string;
  reviewedBy?: string;
  reviewedAt?: string;
  reviewNote?: string;
  entityId?: string;
  relationship?: {
    source: string;
    relation: string;
    target: string;
  };
  metadataKey?: string;
  metadataValue?: string;
}

export type AuditCategory =
  | 'AUTHENTICATION'
  | 'USER_MANAGEMENT'
  | 'ADMIN_MANAGEMENT'
  | 'DOCUMENT'
  | 'INGESTION'
  | 'KNOWLEDGE_GRAPH'
  | 'VALIDATION'
  | 'SYSTEM'
  | 'SECURITY';

export type AuditActionResult = 'SUCCESS' | 'FAILURE' | 'WARNING';

export type AuditSeverity = 'INFO' | 'WARNING' | 'ERROR';

export interface AuditEvent {
  id: string;
  timestamp: string;
  category: AuditCategory;
  action: string;
  result: AuditActionResult;
  severity: AuditSeverity;
  actorId: string;
  actorName: string;
  actorEmail: string;
  actorRole: UserRole;
  resourceType?: string;
  resourceId?: string;
  resourceName?: string;
  description: string;
  ipAddress?: string;
  userAgent?: string;
  metadata?: Record<string, unknown>;
  beforeState?: Record<string, unknown>;
  afterState?: Record<string, unknown>;
}

export type SettingFieldType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'SELECT' | 'PASSWORD';

export interface SystemSettingField {
  id: string;
  key: string;
  label: string;
  description?: string;
  type: SettingFieldType;
  value: string | number | boolean;
  options?: Array<{ label: string; value: string }>;
  isSecret?: boolean;
}

export interface SystemSettingSection {
  id: string;
  title: string;
  description: string;
  fields: SystemSettingField[];
}
