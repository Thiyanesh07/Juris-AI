export interface SettingDefinition {
  key: string;
  label: string;
  description: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'masked' | 'multiselect' | 'slider';
  value: any;
  defaultValue: any;
  options?: Array<{ label: string; value: string }>;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  isSecret?: boolean;
  requiresSuperAdmin?: boolean;
}

export interface SettingsSectionData {
  id: string;
  title: string;
  description: string;
  iconName: string;
  settings: Record<string, SettingDefinition>;
}

export const INITIAL_MOCK_SETTINGS: Record<string, SettingsSectionData> = {
  general: {
    id: 'general',
    title: 'General Settings',
    description: 'Configure core platform identity, localization, and legal research defaults.',
    iconName: 'Globe',
    settings: {
      platformName: {
        key: 'platformName',
        label: 'Platform Name',
        description: 'Displayed branding name across application titles and notifications.',
        type: 'text',
        value: 'Juris AI',
        defaultValue: 'Juris AI',
      },
      environment: {
        key: 'environment',
        label: 'Deployment Environment',
        description: 'Current running environment instance classification.',
        type: 'text',
        value: 'Development Prototype',
        defaultValue: 'Development Prototype',
      },
      platformVersion: {
        key: 'platformVersion',
        label: 'Platform Core Version',
        description: 'Active GraphRAG engine release tag.',
        type: 'text',
        value: 'v3.4.0-dev',
        defaultValue: 'v3.4.0-dev',
      },
      defaultLanguage: {
        key: 'defaultLanguage',
        label: 'Default Language',
        description: 'Primary language for user portal interfaces and legal summary generation.',
        type: 'select',
        value: 'en-IN',
        defaultValue: 'en-IN',
        options: [
          { label: 'English (India)', value: 'en-IN' },
          { label: 'Hindi (हिंदी)', value: 'hi-IN' },
        ],
      },
      defaultJurisdiction: {
        key: 'defaultJurisdiction',
        label: 'Default Jurisdiction',
        description: 'Primary legal jurisdiction prioritized during vector & graph retrieval.',
        type: 'select',
        value: 'INDIA_SUPREME_COURT',
        defaultValue: 'INDIA_SUPREME_COURT',
        options: [
          { label: 'India (Supreme Court & High Courts)', value: 'INDIA_SUPREME_COURT' },
          { label: 'Central Statutory Acts (India Code)', value: 'INDIA_STATUTES' },
          { label: 'Constitutional Law Only', value: 'INDIA_CONSTITUTION' },
        ],
      },
      timezone: {
        key: 'timezone',
        label: 'System Timezone',
        description: 'Standard timezone for operational timestamps and ingestion log scheduling.',
        type: 'select',
        value: 'Asia/Kolkata',
        defaultValue: 'Asia/Kolkata',
        options: [
          { label: 'Asia/Kolkata (IST +05:30)', value: 'Asia/Kolkata' },
          { label: 'UTC (Coordinated Universal Time)', value: 'UTC' },
        ],
      },
      dateFormat: {
        key: 'dateFormat',
        label: 'Default Date Format',
        description: 'Display format for statutory enactment and judgment dates.',
        type: 'select',
        value: 'DD MMM YYYY',
        defaultValue: 'DD MMM YYYY',
        options: [
          { label: 'DD MMM YYYY (e.g. 28 Sep 2026)', value: 'DD MMM YYYY' },
          { label: 'YYYY-MM-DD (ISO Format)', value: 'YYYY-MM-DD' },
          { label: 'DD/MM/YYYY', value: 'DD/MM/YYYY' },
        ],
      },
      researchMode: {
        key: 'researchMode',
        label: 'Default Research Pipeline Mode',
        description: 'Default retrieval synthesis persona for user queries.',
        type: 'select',
        value: 'LEGAL_REASONING',
        defaultValue: 'LEGAL_REASONING',
        options: [
          { label: 'Legal Reasoning & Precedent Mapping', value: 'LEGAL_REASONING' },
          { label: 'Strict Statutory Concordance', value: 'STATUTORY_STRICT' },
          { label: 'Fast Multi-Hop Overview', value: 'FAST_OVERVIEW' },
        ],
      },
    },
  },

  ai: {
    id: 'ai',
    title: 'AI / LLM Provider',
    description: 'Configure downstream Large Language Model reasoning providers and generation limits.',
    iconName: 'Cpu',
    settings: {
      provider: {
        key: 'provider',
        label: 'LLM Provider Engine',
        description: 'Primary model provider for multi-hop legal query synthesis.',
        type: 'select',
        value: 'google_genai',
        defaultValue: 'google_genai',
        options: [
          { label: 'Google GenAI (Gemini 2.5 Flash)', value: 'google_genai' },
          { label: 'OpenAI Compatible (HTTP API)', value: 'openai_compatible' },
          { label: 'OpenAI (GPT-4o)', value: 'OPENAI' },
          { label: 'Anthropic (Claude 3.5 Sonnet)', value: 'ANTHROPIC' },
          { label: 'Azure OpenAI Enterprise', value: 'AZURE_OPENAI' },
        ],
      },
      model: {
        key: 'model',
        label: 'Model Name',
        description: 'Specific model checkpoint requested during reasoning calls.',
        type: 'select',
        value: 'gemini-2.5-flash',
        defaultValue: 'gemini-2.5-flash',
        options: [
          { label: 'gemini-2.5-flash (Google GenAI Default)', value: 'gemini-2.5-flash' },
          { label: 'gpt-4o-mini (OpenAI Fast)', value: 'gpt-4o-mini' },
          { label: 'gpt-4o-2024-08-06 (Recommended for Legal GraphRAG)', value: 'gpt-4o-2024-08-06' },
          { label: 'claude-3-5-sonnet-20240620', value: 'claude-3-5-sonnet-20240620' },
          { label: 'gpt-4-turbo-preview', value: 'gpt-4-turbo-preview' },
        ],
      },
      temperature: {
        key: 'temperature',
        label: 'Reasoning Temperature',
        description: 'Sampling temperature. Lower values yield deterministic, citation-strict responses.',
        type: 'slider',
        value: 0.2,
        defaultValue: 0.2,
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      maxOutputTokens: {
        key: 'maxOutputTokens',
        label: 'Max Output Tokens',
        description: 'Upper bound on tokens generated per multi-hop legal analysis.',
        type: 'number',
        value: 4096,
        defaultValue: 4096,
        min: 512,
        max: 16384,
        step: 256,
        unit: 'tokens',
      },
      timeout: {
        key: 'timeout',
        label: 'LLM API Request Timeout',
        description: 'Maximum waiting duration for LLM response before pipeline timeout.',
        type: 'number',
        value: 60,
        defaultValue: 60,
        min: 10,
        max: 300,
        step: 5,
        unit: 'seconds',
      },
      apiKey: {
        key: 'apiKey',
        label: 'LLM Provider API Key',
        description: 'Managed by server environment — secret credentials are never exposed to the browser.',
        type: 'masked',
        value: '••••••••••••••••••••••••••••••••',
        defaultValue: '••••••••••••••••••••••••••••••••',
        isSecret: true,
        requiresSuperAdmin: true,
      },
    },
  },

  embeddings: {
    id: 'embeddings',
    title: 'Embeddings & Vector Specs',
    description: 'Configure dense vector embedding models for semantic statutory similarity.',
    iconName: 'Layers',
    settings: {
      provider: {
        key: 'provider',
        label: 'Embedding Provider',
        description: 'Framework powering dense vector embeddings.',
        type: 'select',
        value: 'HUGGINGFACE_LOCAL',
        defaultValue: 'HUGGINGFACE_LOCAL',
        options: [
          { label: 'Local HuggingFace / PyTorch Pipeline', value: 'HUGGINGFACE_LOCAL' },
          { label: 'OpenAI Embeddings API', value: 'OPENAI_EMBEDDINGS' },
        ],
      },
      model: {
        key: 'model',
        label: 'Embedding Model Architecture',
        description: 'Domain-adapted Transformer model trained on Indian Legal Corpus.',
        type: 'select',
        value: 'law-ai/InLegalBERT',
        defaultValue: 'law-ai/InLegalBERT',
        options: [
          { label: 'law-ai/InLegalBERT (Law-adapted BERT for India)', value: 'law-ai/InLegalBERT' },
          { label: 'InLegalBERT (Local alias)', value: 'InLegalBERT' },
          { label: 'text-embedding-3-large (OpenAI 3072d)', value: 'text-embedding-3-large' },
          { label: 'Legal-RoBERTa-Base', value: 'Legal-RoBERTa-Base' },
        ],
      },
      dimension: {
        key: 'dimension',
        label: 'Embedding Vector Dimension',
        description: 'Dense vector output dimension size matched with FAISS vector index.',
        type: 'number',
        value: 768,
        defaultValue: 768,
        min: 384,
        max: 3072,
        step: 128,
        unit: 'dimensions',
      },
      device: {
        key: 'device',
        label: 'Compute Device Assignment',
        description: 'Hardware target for vector generation. Managed by deployment environment.',
        type: 'select',
        value: 'CPU',
        defaultValue: 'CPU',
        options: [
          { label: 'CPU (Standard Development Worker)', value: 'CPU' },
          { label: 'GPU (Available in Production Cluster)', value: 'GPU' },
        ],
      },
      batchSize: {
        key: 'batchSize',
        label: 'Vector Embedding Batch Size',
        description: 'Number of statutory paragraphs embedded in a single forward pass.',
        type: 'number',
        value: 32,
        defaultValue: 32,
        min: 1,
        max: 256,
        step: 8,
      },
      chunkEmbeddingBatch: {
        key: 'chunkEmbeddingBatch',
        label: 'Chunk Worker Concurrent Batch',
        description: 'Concurrent worker threads submitting embedding requests.',
        type: 'number',
        value: 16,
        defaultValue: 16,
        min: 1,
        max: 64,
        step: 4,
      },
    },
  },

  retrieval: {
    id: 'retrieval',
    title: 'Retrieval & GraphRAG Pipeline',
    description: 'Tune hybrid vector-graph retrieval weights, traversal depths, and citation thresholds.',
    iconName: 'GitFork',
    settings: {
      vectorTopK: {
        key: 'vectorTopK',
        label: 'Vector Top-K Nearest Neighbors',
        description: 'Number of dense vector similarity nearest neighbor chunks retrieved.',
        type: 'slider',
        value: 8,
        defaultValue: 8,
        min: 1,
        max: 50,
        step: 1,
      },
      graphDepth: {
        key: 'graphDepth',
        label: 'Graph Traversal Depth',
        description: 'Maximum edge hop depth explored during multi-hop graph expansion.',
        type: 'slider',
        value: 3,
        defaultValue: 3,
        min: 1,
        max: 5,
        step: 1,
      },
      graphCandidateLimit: {
        key: 'graphCandidateLimit',
        label: 'Graph Candidate Entity Limit',
        description: 'Upper limit of entity nodes expanded during graph traversal.',
        type: 'slider',
        value: 20,
        defaultValue: 20,
        min: 5,
        max: 100,
        step: 5,
      },
      hybridWeight: {
        key: 'hybridWeight',
        label: 'Hybrid Retrieval Weight (Vector vs Graph)',
        description: '0.00 = Graph Only, 0.50 = Equal Weighting, 1.00 = Vector Only.',
        type: 'slider',
        value: 0.5,
        defaultValue: 0.5,
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      minEvidenceScore: {
        key: 'minEvidenceScore',
        label: 'Minimum Evidence Confidence Score',
        description: 'Threshold below which retrieved evidence is omitted from LLM prompt context.',
        type: 'slider',
        value: 0.7,
        defaultValue: 0.7,
        min: 0.0,
        max: 1.0,
        step: 0.05,
      },
      citationRequirement: {
        key: 'citationRequirement',
        label: 'Legal Citation Verification Rule',
        description: 'Enforces statutory section/article citation verification on output.',
        type: 'select',
        value: 'STRICT',
        defaultValue: 'STRICT',
        options: [
          { label: 'Strict (Every legal assertion requires verified citation)', value: 'STRICT' },
          { label: 'Flexible (Allow general summary with inline references)', value: 'FLEXIBLE' },
        ],
      },
    },
  },

  ingestion: {
    id: 'ingestion',
    title: 'Ingestion Defaults',
    description: 'Configure legal document parsing, chunking parameters, and retry policies.',
    iconName: 'FileText',
    settings: {
      maxFileSizeMb: {
        key: 'maxFileSizeMb',
        label: 'Maximum Upload File Size',
        description: 'Upper file size limit for uploaded PDF/DOCX legal documents.',
        type: 'number',
        value: 50,
        defaultValue: 50,
        min: 5,
        max: 200,
        step: 5,
        unit: 'MB',
      },
      chunkSize: {
        key: 'chunkSize',
        label: 'Document Chunk Size',
        description: 'Target token size for legal text passage chunking.',
        type: 'number',
        value: 800,
        defaultValue: 800,
        min: 200,
        max: 2000,
        step: 50,
        unit: 'tokens',
      },
      chunkOverlap: {
        key: 'chunkOverlap',
        label: 'Chunk Overlap Margin',
        description: 'Overlapping token boundary between adjacent passage chunks.',
        type: 'number',
        value: 120,
        defaultValue: 120,
        min: 0,
        max: 400,
        step: 10,
        unit: 'tokens',
      },
      batchSize: {
        key: 'batchSize',
        label: 'Ingestion Batch Size',
        description: 'Number of chunks processed per background ingestion sub-task.',
        type: 'number',
        value: 16,
        defaultValue: 16,
        min: 1,
        max: 64,
        step: 4,
      },
      retryAttempts: {
        key: 'retryAttempts',
        label: 'Ingestion Pipeline Retry Limit',
        description: 'Maximum automatic retry attempts for failed OCR or extraction jobs.',
        type: 'number',
        value: 3,
        defaultValue: 3,
        min: 0,
        max: 10,
        step: 1,
      },
      processingTimeoutMin: {
        key: 'processingTimeoutMin',
        label: 'Job Execution Timeout',
        description: 'Maximum duration allowed for an ingestion job before termination.',
        type: 'number',
        value: 30,
        defaultValue: 30,
        min: 5,
        max: 120,
        step: 5,
        unit: 'minutes',
      },
    },
  },

  graph: {
    id: 'graph',
    title: 'Knowledge Graph Settings',
    description: 'Configure Neo4j database parameters, traversal constraints, and legal relationship types.',
    iconName: 'Database',
    settings: {
      provider: {
        key: 'provider',
        label: 'Graph Database Provider',
        description: 'Backing Graph DB engine powering typed legal relationships.',
        type: 'select',
        value: 'NEO4J',
        defaultValue: 'NEO4J',
        options: [
          { label: 'Neo4j Graph Database (Enterprise / Community)', value: 'NEO4J' },
          { label: 'In-Memory Development Graph (Mock)', value: 'IN_MEMORY' },
        ],
      },
      connectionStatus: {
        key: 'connectionStatus',
        label: 'Neo4j Connection Status',
        description: 'Managed server-side. No backend connection active in frontend development.',
        type: 'text',
        value: 'Not Connected (Integration Pending)',
        defaultValue: 'Not Connected (Integration Pending)',
      },
      defaultTraversalDepth: {
        key: 'defaultTraversalDepth',
        label: 'Default Traversal Depth',
        description: 'Standard exploration radius for Knowledge Graph visualizer.',
        type: 'number',
        value: 3,
        defaultValue: 3,
        min: 1,
        max: 5,
        step: 1,
      },
      maxTraversalDepth: {
        key: 'maxTraversalDepth',
        label: 'Maximum Allowed Traversal Depth',
        description: 'Hard limit on Cypher query graph expansion to prevent query timeouts.',
        type: 'number',
        value: 5,
        defaultValue: 5,
        min: 1,
        max: 10,
        step: 1,
      },
      connectionUri: {
        key: 'connectionUri',
        label: 'Neo4j Connection URI',
        description: 'Configured server-side via environment variables (e.g. bolt://localhost:7687).',
        type: 'masked',
        value: '••••••••••••••••••••••••••••••••',
        defaultValue: '••••••••••••••••••••••••••••••••',
        isSecret: true,
        requiresSuperAdmin: true,
      },
    },
  },

  security: {
    id: 'security',
    title: 'Security & Access Policies',
    description: 'Manage session timeouts, multi-factor authentication requirements, and audit retention.',
    iconName: 'ShieldCheck',
    settings: {
      sessionTimeoutMin: {
        key: 'sessionTimeoutMin',
        label: 'Admin Session Inactivity Timeout',
        description: 'Inactivity duration before administrative session automatically expires.',
        type: 'number',
        value: 30,
        defaultValue: 30,
        min: 5,
        max: 480,
        step: 5,
        unit: 'minutes',
      },
      requireMfa: {
        key: 'requireMfa',
        label: 'Require Multi-Factor Authentication (MFA)',
        description: 'Enforce TOTP MFA verification for all Administrator login accounts.',
        type: 'boolean',
        value: true,
        defaultValue: true,
        requiresSuperAdmin: true,
      },
      passwordPolicy: {
        key: 'passwordPolicy',
        label: 'Password Complexity Standard',
        description: 'Minimum complexity requirements for admin and user passwords.',
        type: 'select',
        value: 'STRONG',
        defaultValue: 'STRONG',
        options: [
          { label: 'Strong (Min 12 chars, uppercase, lowercase, number, special symbol)', value: 'STRONG' },
          { label: 'Medium (Min 8 chars, mixed case, number)', value: 'MEDIUM' },
        ],
      },
      loginAttemptLimit: {
        key: 'loginAttemptLimit',
        label: 'Account Lockout Attempt Limit',
        description: 'Failed login attempts allowed before temporary IP/account lockout.',
        type: 'number',
        value: 5,
        defaultValue: 5,
        min: 3,
        max: 10,
        step: 1,
      },
      auditLoggingEnabled: {
        key: 'auditLoggingEnabled',
        label: 'Immutable Audit Logging',
        description: 'Record all administrative read/write operations to immutable audit stream.',
        type: 'boolean',
        value: true,
        defaultValue: true,
        requiresSuperAdmin: true,
      },
      auditRetentionDays: {
        key: 'auditRetentionDays',
        label: 'Audit Log Event Retention Period',
        description: 'Duration audit event records are retained in compliance logs.',
        type: 'number',
        value: 90,
        defaultValue: 90,
        min: 30,
        max: 365,
        step: 30,
        unit: 'days',
      },
    },
  },
};

// ── Phase 2 Backend-Frontend Section Mapping ──────────────────────────────
export const FRONTEND_TO_BACKEND_SECTION_MAP: Record<string, string> = {
  general: 'GENERAL',
  ai: 'AI_LLM',
  embeddings: 'EMBEDDINGS',
  retrieval: 'RETRIEVAL',
  ingestion: 'INGESTION',
  graph: 'KNOWLEDGE_GRAPH',
  security: 'SECURITY',
};

export const BACKEND_TO_FRONTEND_SECTION_MAP: Record<string, string> = {
  GENERAL: 'general',
  AI_LLM: 'ai',
  EMBEDDINGS: 'embeddings',
  RETRIEVAL: 'retrieval',
  INGESTION: 'ingestion',
  KNOWLEDGE_GRAPH: 'graph',
  SECURITY: 'security',
};

export interface SectionFieldMapping {
  uiToBackend: Record<string, string>;
  backendToUi: Record<string, string>;
}

// ── Explicit, Reversible Field-Name Mappings ─────────────────────────────
// Derived directly from server/api/app/api/routes/settings.py (_DEFAULT_SETTINGS)
// and app/core/config.py (Settings schema).
export const SECTION_FIELD_MAPPINGS: Record<string, SectionFieldMapping> = {
  GENERAL: {
    uiToBackend: {
      platformName: 'platform_name',
      maintenanceMode: 'maintenance_mode',
      maxQueryLength: 'max_query_length',
      supportEmail: 'support_email',
      environment: 'environment',
      platformVersion: 'platform_version',
      defaultLanguage: 'default_language',
      defaultJurisdiction: 'default_jurisdiction',
      timezone: 'timezone',
      dateFormat: 'date_format',
      researchMode: 'research_mode',
    },
    backendToUi: {
      platform_name: 'platformName',
      maintenance_mode: 'maintenanceMode',
      max_query_length: 'maxQueryLength',
      support_email: 'supportEmail',
      environment: 'environment',
      platform_version: 'platformVersion',
      default_language: 'defaultLanguage',
      default_jurisdiction: 'defaultJurisdiction',
      timezone: 'timezone',
      date_format: 'dateFormat',
      research_mode: 'researchMode',
    },
  },
  AI_LLM: {
    uiToBackend: {
      provider: 'provider',
      model: 'model',
      temperature: 'temperature',
      maxOutputTokens: 'max_output_tokens',
      timeout: 'llm_timeout_seconds',
      apiKey: 'api_key',
    },
    backendToUi: {
      provider: 'provider',
      model: 'model',
      temperature: 'temperature',
      max_output_tokens: 'maxOutputTokens',
      llm_timeout_seconds: 'timeout',
      api_key: 'apiKey',
    },
  },
  EMBEDDINGS: {
    uiToBackend: {
      provider: 'provider',
      model: 'model_name',
      dimension: 'embedding_dim',
      pooling: 'pooling',
      device: 'device',
      batchSize: 'batch_size',
      chunkEmbeddingBatch: 'chunk_embedding_batch',
    },
    backendToUi: {
      provider: 'provider',
      model_name: 'model',
      embedding_dim: 'dimension',
      pooling: 'pooling',
      device: 'device',
      batch_size: 'batchSize',
      chunk_embedding_batch: 'chunkEmbeddingBatch',
    },
  },
  RETRIEVAL: {
    uiToBackend: {
      vectorTopK: 'default_top_k',
      hybridWeight: 'dense_weight',
      graphWeight: 'graph_weight',
      fusionAlgorithm: 'fusion_algorithm',
      graphDepth: 'graph_depth',
      graphCandidateLimit: 'graph_candidate_limit',
      minEvidenceScore: 'min_evidence_score',
      citationRequirement: 'citation_requirement',
    },
    backendToUi: {
      default_top_k: 'vectorTopK',
      dense_weight: 'hybridWeight',
      graph_weight: 'graphWeight',
      fusion_algorithm: 'fusionAlgorithm',
      graph_depth: 'graphDepth',
      graph_candidate_limit: 'graphCandidateLimit',
      min_evidence_score: 'minEvidenceScore',
      citation_requirement: 'citationRequirement',
    },
  },
  INGESTION: {
    uiToBackend: {
      chunkSize: 'chunk_size',
      chunkOverlap: 'chunk_overlap',
      enableOcrFallback: 'enable_ocr_fallback',
      maxFileSizeMb: 'max_file_size_mb',
      batchSize: 'batch_size',
      retryAttempts: 'retry_attempts',
      processingTimeoutMin: 'processing_timeout_min',
    },
    backendToUi: {
      chunk_size: 'chunkSize',
      chunk_overlap: 'chunkOverlap',
      enable_ocr_fallback: 'enableOcrFallback',
      max_file_size_mb: 'maxFileSizeMb',
      batch_size: 'batchSize',
      retry_attempts: 'retryAttempts',
      processing_timeout_min: 'processingTimeoutMin',
    },
  },
  KNOWLEDGE_GRAPH: {
    uiToBackend: {
      connectionUri: 'neo4j_uri',
      database: 'neo4j_database',
      defaultTraversalDepth: 'default_traversal_depth',
      maxTraversalDepth: 'max_traversal_depth',
      provider: 'provider',
      connectionStatus: 'connection_status',
    },
    backendToUi: {
      neo4j_uri: 'connectionUri',
      neo4j_database: 'database',
      default_traversal_depth: 'defaultTraversalDepth',
      max_traversal_depth: 'maxTraversalDepth',
      provider: 'provider',
      connection_status: 'connectionStatus',
    },
  },
  SECURITY: {
    uiToBackend: {
      sessionTimeoutMin: 'session_timeout_min',
      sessionTtlHours: 'session_ttl_hours',
      requireMfa: 'require_mfa',
      loginAttemptLimit: 'max_login_attempts',
      passwordPolicy: 'password_policy',
      auditLoggingEnabled: 'audit_logging_enabled',
      auditRetentionDays: 'audit_retention_days',
    },
    backendToUi: {
      session_timeout_min: 'sessionTimeoutMin',
      session_ttl_hours: 'sessionTtlHours',
      require_mfa: 'requireMfa',
      max_login_attempts: 'loginAttemptLimit',
      password_policy: 'passwordPolicy',
      audit_logging_enabled: 'auditLoggingEnabled',
      audit_retention_days: 'auditRetentionDays',
    },
  },
};

/** Get the corresponding backend key name for a given frontend UI key. */
export function getBackendKey(section: string, uiKey: string): string {
  const secUpper = section.toUpperCase();
  const mapping = SECTION_FIELD_MAPPINGS[secUpper]?.uiToBackend;
  if (mapping && mapping[uiKey]) {
    return mapping[uiKey];
  }
  // Generic reversible fallback: camelCase -> snake_case
  return uiKey.replace(/([A-Z])/g, '_$1').toLowerCase();
}

/** Get the corresponding frontend UI key name for a given backend key. */
export function getUiKey(section: string, backendKey: string): string {
  const secUpper = section.toUpperCase();
  const mapping = SECTION_FIELD_MAPPINGS[secUpper]?.backendToUi;
  if (mapping && mapping[backendKey]) {
    return mapping[backendKey];
  }
  // Generic reversible fallback: snake_case -> camelCase
  return backendKey.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Returns true if a value represents a masked credential placeholder.
 * Prevents masked strings from overwriting real server credentials on save.
 */
export function isMaskedSecret(value: any): boolean {
  if (typeof value !== 'string') return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  // All asterisks or bullet points (e.g., '********', '••••••••')
  if (/^(\*|•)+$/.test(trimmed)) return true;
  // Partial-mask pattern returned by backend (e.g., 'val...****', 'sk-...****')
  if (/^.{0,6}\.\.\.\*+$/.test(trimmed)) return true;
  // Contains bullet mask sequences
  if (trimmed.includes('••••')) return true;
  return false;
}

/** Transform setting value from UI format to backend payload format. */
export function transformValueToBackend(section: string, uiKey: string, value: any): any {
  const secUpper = section.toUpperCase();
  if (secUpper === 'RETRIEVAL' && uiKey === 'hybridWeight') {
    const num = Number(value);
    return isNaN(num) ? value : num;
  }
  if (secUpper === 'SECURITY' && uiKey === 'sessionTimeoutMin') {
    const num = Number(value);
    return isNaN(num) ? value : num;
  }
  return value;
}

/** Transform setting value from backend response format to UI format. */
export function transformValueToUi(section: string, backendKey: string, value: any): any {
  const secUpper = section.toUpperCase();
  if (secUpper === 'SECURITY' && backendKey === 'session_ttl_hours') {
    const hours = Number(value);
    if (!isNaN(hours) && hours > 0) {
      // Convert hours to minutes bounded by UI limits [5, 480]
      return Math.min(480, Math.max(5, hours * 60));
    }
  }
  if (secUpper === 'RETRIEVAL' && (backendKey === 'dense_weight' || backendKey === 'default_top_k')) {
    const num = Number(value);
    return isNaN(num) ? value : num;
  }
  return value;
}

/**
 * Build the backend config payload for a given section, excluding masked secrets
 * and ensuring coupled configuration constraints (such as hybrid vector/graph weights).
 */
export function buildBackendConfigPayload(
  sectionId: string,
  sectionData: SettingsSectionData
): Record<string, any> {
  const backendSectionName = FRONTEND_TO_BACKEND_SECTION_MAP[sectionId] || sectionId.toUpperCase();
  const configMap: Record<string, any> = {};

  Object.keys(sectionData.settings).forEach((uiKey) => {
    const def = sectionData.settings[uiKey];

    // Prevent masked secrets (e.g. ********, ••••) from overwriting stored credentials
    if ((def.isSecret || def.type === 'masked') && isMaskedSecret(def.value)) {
      return;
    }

    const backendKey = getBackendKey(backendSectionName, uiKey);
    const backendVal = transformValueToBackend(backendSectionName, uiKey, def.value);
    configMap[backendKey] = backendVal;

    // Coupled settings requirements
    if (backendSectionName === 'RETRIEVAL' && uiKey === 'hybridWeight') {
      configMap['graph_weight'] = Math.round((1 - Number(def.value)) * 100) / 100;
    }
    if (backendSectionName === 'SECURITY' && uiKey === 'sessionTimeoutMin') {
      configMap['session_ttl_hours'] = Math.round(Number(def.value) / 60) || 1;
    }
  });

  return configMap;
}

/**
 * Hydrates frontend settings definitions from GET /settings response payload.
 * Accurately translates section names (e.g. AI_LLM -> ai) and field keys.
 */
export function hydrateSectionsFromBackend(
  currentSections: Record<string, SettingsSectionData>,
  backendSections: Record<string, Record<string, any>>
): Record<string, SettingsSectionData> {
  const next: Record<string, SettingsSectionData> = JSON.parse(JSON.stringify(currentSections));

  Object.keys(backendSections).forEach((backendSecName) => {
    const frontendSecId = BACKEND_TO_FRONTEND_SECTION_MAP[backendSecName] || backendSecName.toLowerCase();
    const currentSec = next[frontendSecId];
    const backendConfig = backendSections[backendSecName];

    if (!currentSec || !backendConfig) return;

    Object.keys(backendConfig).forEach((backendKey) => {
      const rawVal = backendConfig[backendKey];
      let uiKey = getUiKey(backendSecName, backendKey);

      // Support fallback where backend returns session_ttl_hours but UI defines sessionTimeoutMin
      if (
        backendSecName === 'SECURITY' &&
        backendKey === 'session_ttl_hours' &&
        !currentSec.settings[uiKey] &&
        currentSec.settings['sessionTimeoutMin']
      ) {
        uiKey = 'sessionTimeoutMin';
      }

      if (currentSec.settings[uiKey]) {
        const transformed = transformValueToUi(backendSecName, backendKey, rawVal);
        currentSec.settings[uiKey].value = transformed;
        currentSec.settings[uiKey].defaultValue = transformed;
      }
    });
  });

  return next;
}
