export type UserRole = 'USER' | 'ADMIN' | 'SUPER_ADMIN';
export type UserStatus = 'Active' | 'Disabled';
export type DocStatus = 'Indexed' | 'Processing' | 'Pending Validation' | 'Failed' | 'Archived';
export type ValidationStatus = 'Pending' | 'Approved' | 'Rejected';
export type JobStatus = 'Running' | 'Completed' | 'Failed' | 'Paused';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  created: string;
  lastActive: string;
  createdBy?: string;
}

export interface Document {
  id: string;
  title: string;
  type: string;
  source: string;
  version: string;
  status: DocStatus;
  uploaded: string;
  uploadedBy: string;
  entities?: number;
  relations?: number;
  pages?: number;
  effectiveDate?: string;
}

export interface IngestionJob {
  id: string;
  docTitle: string;
  stage: string;
  progress: number;
  entities: number;
  relations: number;
  startedAt: string;
  status: JobStatus;
  duration?: string;
  completedAt?: string;
}

export interface ValidationItem {
  id: string;
  type: 'ENTITY' | 'RELATION';
  entity: string;
  source: string;
  confidence: number;
  status: ValidationStatus;
  model: string;
  passage: string;
  docMeta: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  role: UserRole;
  action: string;
  resource: string;
  result: 'Success' | 'Failed';
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'DOCUMENT' | 'ARTICLE' | 'SECTION' | 'ACT' | 'JUDGMENT' | 'COURT' | 'LEGAL PRINCIPLE' | 'AMENDMENT' | 'RULE';
  x: number;
  y: number;
  status: 'Validated' | 'Pending' | 'Rejected';
  source?: string;
  description?: string;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label: string;
}

// ── Users ──────────────────────────────────────────────────────────────────

export const USERS: User[] = [
  { id: 'u1', name: 'Arun Kumar', email: 'arun.kumar@example.com', role: 'USER', status: 'Active', created: 'Sep 24, 2026', lastActive: 'Today', createdBy: 'Super Administrator' },
  { id: 'u2', name: 'Priya Nair', email: 'priya.nair@example.com', role: 'USER', status: 'Active', created: 'Sep 21, 2026', lastActive: 'Yesterday', createdBy: 'Rajiv Sharma' },
  { id: 'u3', name: 'Rahul Singh', email: 'rahul.singh@example.com', role: 'USER', status: 'Disabled', created: 'Sep 12, 2026', lastActive: 'Sep 18, 2026', createdBy: 'Super Administrator' },
  { id: 'u4', name: 'Sunita Menon', email: 'sunita.menon@example.com', role: 'USER', status: 'Active', created: 'Sep 8, 2026', lastActive: 'Today', createdBy: 'Rajiv Sharma' },
  { id: 'u5', name: 'Vikram Joshi', email: 'vikram.joshi@example.com', role: 'USER', status: 'Active', created: 'Sep 2, 2026', lastActive: '2 days ago', createdBy: 'Super Administrator' },
  { id: 'u6', name: 'Ananya Chatterjee', email: 'ananya.c@example.com', role: 'USER', status: 'Active', created: 'Aug 29, 2026', lastActive: 'Today', createdBy: 'Meera Pillai' },
  { id: 'u7', name: 'Deepak Verma', email: 'deepak.verma@example.com', role: 'USER', status: 'Disabled', created: 'Aug 20, 2026', lastActive: 'Aug 27, 2026', createdBy: 'Rajiv Sharma' },
  { id: 'u8', name: 'Kavitha Reddy', email: 'kavitha.r@example.com', role: 'USER', status: 'Active', created: 'Aug 14, 2026', lastActive: 'Yesterday', createdBy: 'Super Administrator' },
  { id: 'u9', name: 'Arjun Patel', email: 'arjun.patel@example.com', role: 'USER', status: 'Active', created: 'Aug 10, 2026', lastActive: '3 days ago', createdBy: 'Meera Pillai' },
  { id: 'u10', name: 'Shweta Iyer', email: 'shweta.iyer@example.com', role: 'USER', status: 'Active', created: 'Aug 5, 2026', lastActive: 'Today', createdBy: 'Rajiv Sharma' },
  { id: 'u11', name: 'Rohit Das', email: 'rohit.das@example.com', role: 'USER', status: 'Active', created: 'Jul 28, 2026', lastActive: 'Today', createdBy: 'Super Administrator' },
  { id: 'u12', name: 'Nandita Srinivas', email: 'nandita.s@example.com', role: 'USER', status: 'Disabled', created: 'Jul 20, 2026', lastActive: 'Jul 31, 2026', createdBy: 'Meera Pillai' },
];

export const ADMINS: User[] = [
  { id: 'sa1', name: 'Super Administrator', email: 'superadmin@juris.ai', role: 'SUPER_ADMIN', status: 'Active', created: 'Jan 1, 2026', lastActive: 'Today' },
  { id: 'a1', name: 'Rajiv Sharma', email: 'rajiv.sharma@juris.ai', role: 'ADMIN', status: 'Active', created: 'Feb 14, 2026', lastActive: 'Today', createdBy: 'Super Administrator' },
  { id: 'a2', name: 'Meera Pillai', email: 'meera.pillai@juris.ai', role: 'ADMIN', status: 'Active', created: 'Mar 10, 2026', lastActive: 'Yesterday', createdBy: 'Super Administrator' },
  { id: 'a3', name: 'Suresh Gupta', email: 'suresh.gupta@juris.ai', role: 'ADMIN', status: 'Disabled', created: 'Apr 22, 2026', lastActive: 'Aug 30, 2026', createdBy: 'Super Administrator' },
];

// ── Documents ──────────────────────────────────────────────────────────────

export const DOCUMENTS: Document[] = [
  { id: 'd1', title: 'Constitution of India', type: 'Constitution', source: 'Government of India', version: 'v1', status: 'Indexed', uploaded: 'Jan 15, 2026', uploadedBy: 'Super Administrator', entities: 8421, relations: 24680, pages: 468, effectiveDate: 'Jan 26, 1950' },
  { id: 'd2', title: 'Indian Penal Code, 1860', type: 'Statute', source: 'Government of India', version: 'v2', status: 'Indexed', uploaded: 'Jan 20, 2026', uploadedBy: 'Rajiv Sharma', entities: 6304, relations: 18920, pages: 312, effectiveDate: 'Oct 6, 1860' },
  { id: 'd3', title: 'Code of Criminal Procedure, 1973', type: 'Statute', source: 'Government of India', version: 'v1', status: 'Indexed', uploaded: 'Feb 3, 2026', uploadedBy: 'Rajiv Sharma', entities: 4812, relations: 14360, pages: 284, effectiveDate: 'Apr 1, 1974' },
  { id: 'd4', title: 'Constitution (First Amendment) Act, 1951', type: 'Amendment', source: 'Government of India', version: 'v1', status: 'Pending Validation', uploaded: 'Mar 12, 2026', uploadedBy: 'Meera Pillai', entities: 342, relations: 890, pages: 24, effectiveDate: 'Jun 18, 1951' },
  { id: 'd5', title: 'Supreme Court Judgments — Vol. XII', type: 'Judgments', source: 'Supreme Court of India', version: 'v3', status: 'Processing', uploaded: 'Sep 24, 2026', uploadedBy: 'Rajiv Sharma', entities: 0, relations: 0, pages: 1240 },
  { id: 'd6', title: 'Right to Information Act, 2005', type: 'Statute', source: 'Government of India', version: 'v1', status: 'Indexed', uploaded: 'Apr 5, 2026', uploadedBy: 'Meera Pillai', entities: 1820, relations: 5640, pages: 68, effectiveDate: 'Oct 12, 2005' },
  { id: 'd7', title: 'Information Technology Act, 2000', type: 'Statute', source: 'Government of India', version: 'v2', status: 'Indexed', uploaded: 'Apr 18, 2026', uploadedBy: 'Super Administrator', entities: 2104, relations: 6320, pages: 94, effectiveDate: 'Oct 17, 2000' },
  { id: 'd8', title: 'Companies Act, 2013', type: 'Statute', source: 'Government of India', version: 'v1', status: 'Failed', uploaded: 'May 7, 2026', uploadedBy: 'Rajiv Sharma', entities: 0, relations: 0, pages: 516 },
  { id: 'd9', title: 'Constitution (Forty-Second Amendment) Act, 1976', type: 'Amendment', source: 'Government of India', version: 'v1', status: 'Indexed', uploaded: 'May 20, 2026', uploadedBy: 'Super Administrator', entities: 412, relations: 1080, pages: 32, effectiveDate: 'Jan 3, 1977' },
  { id: 'd10', title: 'High Court Rules — Delhi', type: 'Rule', source: 'Delhi High Court', version: 'v1', status: 'Archived', uploaded: 'Jun 10, 2026', uploadedBy: 'Meera Pillai', entities: 0, relations: 0, pages: 186 },
];

// ── Ingestion Jobs ──────────────────────────────────────────────────────────

export const INGESTION_ACTIVE: IngestionJob[] = [
  { id: 'j1', docTitle: 'Supreme Court Judgments — Vol. XII', stage: 'Entity Extraction', progress: 78, entities: 3821, relations: 8942, startedAt: '09:42 AM', status: 'Running' },
  { id: 'j2', docTitle: 'Constitution (First Amendment) Act, 1951', stage: 'Relation Extraction', progress: 45, entities: 342, relations: 416, startedAt: '10:15 AM', status: 'Running' },
];

export const INGESTION_COMPLETED: IngestionJob[] = [
  { id: 'j3', docTitle: 'Right to Information Act, 2005', stage: 'Completed', progress: 100, entities: 1820, relations: 5640, startedAt: '08:00 AM', status: 'Completed', duration: '38 min', completedAt: 'Sep 28, 08:38 AM' },
  { id: 'j4', docTitle: 'Information Technology Act, 2000', stage: 'Completed', progress: 100, entities: 2104, relations: 6320, startedAt: 'Sep 27, 02:10 PM', status: 'Completed', duration: '52 min', completedAt: 'Sep 27, 03:02 PM' },
  { id: 'j5', docTitle: 'Code of Criminal Procedure, 1973', stage: 'Completed', progress: 100, entities: 4812, relations: 14360, startedAt: 'Sep 26, 11:00 AM', status: 'Completed', duration: '1h 24 min', completedAt: 'Sep 26, 12:24 PM' },
  { id: 'j6', docTitle: 'Companies Act, 2013', stage: 'Failed — Text Extraction Error', progress: 12, entities: 0, relations: 0, startedAt: 'May 7, 09:30 AM', status: 'Failed', duration: '8 min', completedAt: 'May 7, 09:38 AM' },
];

// ── Graph ──────────────────────────────────────────────────────────────────

export const GRAPH_NODES: GraphNode[] = [
  { id: 'constitution', label: 'Constitution of India', type: 'DOCUMENT', x: 420, y: 260, status: 'Validated', source: 'Constitution.pdf', description: 'The supreme law of India, adopted on 26 November 1949.' },
  { id: 'art14', label: 'Article 14', type: 'ARTICLE', x: 620, y: 180, status: 'Validated', source: 'Constitution.pdf', description: 'Right to equality before law.' },
  { id: 'art21', label: 'Article 21', type: 'ARTICLE', x: 660, y: 280, status: 'Validated', source: 'Constitution.pdf', description: 'Protection of life and personal liberty.' },
  { id: 'art32', label: 'Article 32', type: 'ARTICLE', x: 620, y: 380, status: 'Validated', source: 'Constitution.pdf', description: 'Right to constitutional remedies.' },
  { id: 'art19', label: 'Article 19', type: 'ARTICLE', x: 520, y: 140, status: 'Validated', source: 'Constitution.pdf', description: 'Protection of certain rights regarding freedom of speech.' },
  { id: 'ipc', label: 'Indian Penal Code', type: 'ACT', x: 200, y: 260, status: 'Validated', source: 'IPC.pdf', description: 'The main criminal code of India.' },
  { id: 'sec302', label: 'Section 302', type: 'SECTION', x: 100, y: 160, status: 'Validated', source: 'IPC.pdf', description: 'Punishment for murder.' },
  { id: 'sec376', label: 'Section 376', type: 'SECTION', x: 90, y: 360, status: 'Validated', source: 'IPC.pdf', description: 'Punishment for rape.' },
  { id: 'supremecourt', label: 'Supreme Court', type: 'COURT', x: 380, y: 80, status: 'Validated', source: 'Constitution.pdf', description: 'Apex court of the Indian judicial system.' },
  { id: 'delhihc', label: 'Delhi High Court', type: 'COURT', x: 580, y: 80, status: 'Validated', source: 'HC-Rules.pdf', description: 'High Court for the National Capital Territory of Delhi.' },
  { id: 'kesavananda', label: 'Kesavananda Bharati', type: 'JUDGMENT', x: 340, y: 440, status: 'Validated', source: 'Judgments-XII.pdf', description: 'Landmark case establishing the Basic Structure doctrine.' },
  { id: 'maneka', label: 'Maneka Gandhi Case', type: 'JUDGMENT', x: 540, y: 460, status: 'Validated', source: 'Judgments-XII.pdf', description: 'Expanded the scope of Article 21.' },
  { id: 'equality', label: 'Right to Equality', type: 'LEGAL PRINCIPLE', x: 760, y: 180, status: 'Validated', source: 'Constitution.pdf', description: 'Fundamental legal principle enshrined in Part III.' },
  { id: 'life', label: 'Right to Life', type: 'LEGAL PRINCIPLE', x: 780, y: 300, status: 'Validated', source: 'Constitution.pdf', description: 'Broad constitutional protection for life and liberty.' },
  { id: 'firstamend', label: '1st Amendment 1951', type: 'AMENDMENT', x: 260, y: 120, status: 'Pending', source: 'Amendment-1951.pdf', description: 'Added restrictions to freedom of speech and expression.' },
  { id: 'rti', label: 'RTI Act, 2005', type: 'ACT', x: 180, y: 420, status: 'Validated', source: 'RTI.pdf', description: 'Right to Information Act providing access to public records.' },
];

export const GRAPH_EDGES: GraphEdge[] = [
  { id: 'e1', from: 'constitution', to: 'art14', label: 'CONTAINS' },
  { id: 'e2', from: 'constitution', to: 'art21', label: 'CONTAINS' },
  { id: 'e3', from: 'constitution', to: 'art32', label: 'CONTAINS' },
  { id: 'e4', from: 'constitution', to: 'art19', label: 'CONTAINS' },
  { id: 'e5', from: 'art14', to: 'equality', label: 'DEFINES' },
  { id: 'e6', from: 'art21', to: 'life', label: 'DEFINES' },
  { id: 'e7', from: 'art32', to: 'supremecourt', label: 'JURISDICTION' },
  { id: 'e8', from: 'ipc', to: 'sec302', label: 'CONTAINS' },
  { id: 'e9', from: 'ipc', to: 'sec376', label: 'CONTAINS' },
  { id: 'e10', from: 'supremecourt', to: 'kesavananda', label: 'DECIDED' },
  { id: 'e11', from: 'supremecourt', to: 'maneka', label: 'DECIDED' },
  { id: 'e12', from: 'kesavananda', to: 'constitution', label: 'INTERPRETS' },
  { id: 'e13', from: 'maneka', to: 'art21', label: 'INTERPRETS' },
  { id: 'e14', from: 'firstamend', to: 'constitution', label: 'AMENDS' },
  { id: 'e15', from: 'firstamend', to: 'art19', label: 'RESTRICTS' },
  { id: 'e16', from: 'delhihc', to: 'art14', label: 'APPLIES' },
  { id: 'e17', from: 'rti', to: 'art19', label: 'IMPLEMENTS' },
  { id: 'e18', from: 'equality', to: 'life', label: 'RELATED_TO' },
];

// ── Validation ─────────────────────────────────────────────────────────────

export const VALIDATION_ITEMS: ValidationItem[] = [
  { id: 'v1', type: 'RELATION', entity: 'Article 14 → Right to Equality', source: 'Constitution.pdf', confidence: 96, status: 'Pending', model: 'legal-graph-v2', passage: 'Article 14 of the Constitution of India guarantees the Right to Equality, stating that "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India."', docMeta: 'Constitution of India, Part III, Page 18' },
  { id: 'v2', type: 'ENTITY', entity: 'Supreme Court of India', source: 'Judgments-XII.pdf', confidence: 98, status: 'Pending', model: 'ner-legal-v3', passage: 'The Supreme Court of India, in its capacity as the apex judicial body, exercised its powers under Article 136 of the Constitution to grant special leave to appeal.', docMeta: 'Supreme Court Judgments Vol. XII, Page 42' },
  { id: 'v3', type: 'RELATION', entity: 'IPC → Section 302', source: 'IPC.pdf', confidence: 94, status: 'Pending', model: 'legal-graph-v2', passage: 'Section 302 of the Indian Penal Code prescribes punishment for murder: "Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine."', docMeta: 'Indian Penal Code 1860, Chapter XVI, Page 84' },
  { id: 'v4', type: 'ENTITY', entity: 'Kesavananda Bharati v. State of Kerala', source: 'Judgments-XII.pdf', confidence: 99, status: 'Pending', model: 'ner-legal-v3', passage: 'In Kesavananda Bharati v. State of Kerala (AIR 1973 SC 1461), the Supreme Court held that the Parliament cannot amend the basic structure of the Constitution.', docMeta: 'Supreme Court Judgments Vol. XII, Page 178' },
  { id: 'v5', type: 'RELATION', entity: 'Amendment 1951 → Article 19', source: 'Amendment-1951.pdf', confidence: 88, status: 'Pending', model: 'legal-graph-v2', passage: 'The Constitution (First Amendment) Act, 1951, added clauses (2) and (6) to Article 19, restricting absolute freedom of speech and expression in the interests of public order and national security.', docMeta: 'Constitution (First Amendment) Act 1951, Page 3' },
  { id: 'v6', type: 'RELATION', entity: 'Article 21 → Right to Life', source: 'Constitution.pdf', confidence: 97, status: 'Approved', model: 'legal-graph-v2', passage: 'Article 21 provides: "No person shall be deprived of his life or personal liberty except according to procedure established by law."', docMeta: 'Constitution of India, Part III, Page 20' },
  { id: 'v7', type: 'ENTITY', entity: 'Delhi High Court', source: 'HC-Rules.pdf', confidence: 91, status: 'Approved', model: 'ner-legal-v3', passage: 'The Delhi High Court, established under the High Courts Act, 1861, exercises original and appellate jurisdiction over the National Capital Territory of Delhi.', docMeta: 'Delhi High Court Rules, Page 1' },
  { id: 'v8', type: 'RELATION', entity: 'RTI Act → Article 19', source: 'RTI.pdf', confidence: 85, status: 'Rejected', model: 'legal-graph-v2', passage: 'The Right to Information Act, 2005, seeks to operationalize the fundamental right to information under Article 19(1)(a) of the Constitution.', docMeta: 'RTI Act 2005, Preamble, Page 1' },
];

// ── Audit ──────────────────────────────────────────────────────────────────

export const AUDIT_EVENTS: AuditEvent[] = [
  { id: 'ae1', timestamp: 'Sep 28, 10:42 AM', actor: 'Super Administrator', role: 'SUPER_ADMIN', action: 'Created Administrator', resource: 'Meera Pillai (Admin #3)', result: 'Success' },
  { id: 'ae2', timestamp: 'Sep 28, 10:18 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Uploaded Document', resource: 'Supreme Court Judgments Vol. XII', result: 'Success' },
  { id: 'ae3', timestamp: 'Sep 28, 09:56 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Approved Relation', resource: 'Article 21 → Right to Life', result: 'Success' },
  { id: 'ae4', timestamp: 'Sep 28, 09:42 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Started Ingestion', resource: 'Supreme Court Judgments Vol. XII', result: 'Success' },
  { id: 'ae5', timestamp: 'Sep 28, 09:32 AM', actor: 'Super Administrator', role: 'SUPER_ADMIN', action: 'Disabled User', resource: 'Rahul Singh (User #3)', result: 'Success' },
  { id: 'ae6', timestamp: 'Sep 28, 09:15 AM', actor: 'Meera Pillai', role: 'ADMIN', action: 'Approved Entity', resource: 'Delhi High Court', result: 'Success' },
  { id: 'ae7', timestamp: 'Sep 28, 08:54 AM', actor: 'Meera Pillai', role: 'ADMIN', action: 'Rejected Relation', resource: 'RTI Act → Article 19', result: 'Success' },
  { id: 'ae8', timestamp: 'Sep 28, 08:38 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Ingestion Completed', resource: 'RTI Act, 2005', result: 'Success' },
  { id: 'ae9', timestamp: 'Sep 28, 08:00 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Started Ingestion', resource: 'RTI Act, 2005', result: 'Success' },
  { id: 'ae10', timestamp: 'Sep 27, 04:12 PM', actor: 'Super Administrator', role: 'SUPER_ADMIN', action: 'Modified System Settings', resource: 'Session Duration → 8h', result: 'Success' },
  { id: 'ae11', timestamp: 'Sep 27, 03:02 PM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Ingestion Completed', resource: 'Information Technology Act, 2000', result: 'Success' },
  { id: 'ae12', timestamp: 'Sep 27, 02:10 PM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Started Ingestion', resource: 'Information Technology Act, 2000', result: 'Success' },
  { id: 'ae13', timestamp: 'Sep 27, 12:48 PM', actor: 'Super Administrator', role: 'SUPER_ADMIN', action: 'Created User', resource: 'Arun Kumar (User #1)', result: 'Success' },
  { id: 'ae14', timestamp: 'Sep 27, 11:20 AM', actor: 'Meera Pillai', role: 'ADMIN', action: 'Uploaded Document', resource: 'RTI Act, 2005', result: 'Success' },
  { id: 'ae15', timestamp: 'Sep 27, 10:05 AM', actor: 'Rajiv Sharma', role: 'ADMIN', action: 'Login', resource: 'Admin Portal', result: 'Success' },
  { id: 'ae16', timestamp: 'Sep 26, 03:30 PM', actor: 'Unknown', role: 'USER', action: 'Login Attempt', resource: 'Admin Portal', result: 'Failed' },
];

export const ACTIVITY_FEED = [
  { id: 'af1', actor: 'Super Administrator', action: 'created administrator', target: 'Meera Pillai', time: '12 minutes ago', type: 'admin' },
  { id: 'af2', actor: 'Rajiv Sharma', action: 'uploaded document', target: 'Constitution of India PDF', time: '28 minutes ago', type: 'document' },
  { id: 'af3', actor: 'System', action: 'ingestion job completed', target: 'RTI Act, 2005', time: '42 minutes ago', type: 'ingestion' },
  { id: 'af4', actor: 'Rajiv Sharma', action: 'approved relation', target: 'Article 21 → Right to Life', time: '1 hour ago', type: 'validation' },
  { id: 'af5', actor: 'Super Administrator', action: 'disabled user account', target: 'Rahul Singh', time: '2 hours ago', type: 'user' },
  { id: 'af6', actor: 'Meera Pillai', action: 'started ingestion pipeline', target: 'IPC 1860', time: '3 hours ago', type: 'ingestion' },
];
