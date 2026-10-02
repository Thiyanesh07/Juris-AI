import { useState } from 'react';
import { Save, ChevronDown, ChevronUp, Info } from 'lucide-react';

interface Section {
  id: string;
  label: string;
  description: string;
  fields: Field[];
}

type FieldType = 'select' | 'number' | 'toggle' | 'text' | 'range';

interface Field {
  id: string;
  label: string;
  description?: string;
  type: FieldType;
  value: string | number | boolean;
  options?: string[];
  min?: number;
  max?: number;
  unit?: string;
  sensitive?: boolean;
}

const INITIAL_SETTINGS: Section[] = [
  {
    id: 'auth',
    label: 'Authentication',
    description: 'Session management, password policies, and account security.',
    fields: [
      { id: 'session_duration', label: 'Session Duration', description: 'Idle session timeout for administrators.', type: 'select', value: '8 hours', options: ['1 hour', '4 hours', '8 hours', '24 hours'] },
      { id: 'pw_min_length', label: 'Minimum Password Length', description: 'Minimum character count for all user passwords.', type: 'number', value: 12, min: 8, max: 64, unit: 'characters' },
      { id: 'pw_complexity', label: 'Require Password Complexity', description: 'Enforce uppercase, lowercase, numbers, and special characters.', type: 'toggle', value: true },
      { id: 'lockout_attempts', label: 'Account Lockout Threshold', description: 'Number of failed login attempts before temporary lockout.', type: 'number', value: 5, min: 3, max: 20, unit: 'attempts' },
      { id: 'lockout_duration', label: 'Lockout Duration', description: 'Duration of account lockout after threshold exceeded.', type: 'select', value: '15 minutes', options: ['5 minutes', '15 minutes', '30 minutes', '1 hour', '24 hours'] },
      { id: 'mfa_admin', label: 'Require MFA for Administrators', description: 'Mandate multi-factor authentication for all admin accounts.', type: 'toggle', value: true },
    ],
  },
  {
    id: 'research',
    label: 'Research Configuration',
    description: 'Settings that govern the AI research and retrieval pipeline.',
    fields: [
      { id: 'max_results', label: 'Maximum Retrieval Results', description: 'Maximum number of documents returned per research query.', type: 'number', value: 20, min: 5, max: 100, unit: 'results' },
      { id: 'graph_depth', label: 'Graph Traversal Depth', description: 'Maximum hop depth for knowledge graph traversal during reasoning.', type: 'number', value: 3, min: 1, max: 8, unit: 'hops' },
      { id: 'citation_threshold', label: 'Citation Confidence Threshold', description: 'Minimum confidence for including citations in responses.', type: 'range', value: 82, min: 50, max: 99, unit: '%' },
      { id: 'temporal_analysis', label: 'Enable Temporal Legal Analysis', description: 'Track and reason about changes in law across time.', type: 'toggle', value: true },
      { id: 'multi_hop', label: 'Enable Multi-Hop Reasoning', description: 'Allow the system to chain multiple reasoning steps.', type: 'toggle', value: true },
    ],
  },
  {
    id: 'graph',
    label: 'Knowledge Graph',
    description: 'Configuration for the Neo4j-powered legal knowledge graph.',
    fields: [
      { id: 'default_depth', label: 'Default Traversal Depth', description: 'Default graph depth for entity exploration in the admin UI.', type: 'number', value: 2, min: 1, max: 6, unit: 'hops' },
      { id: 'rel_types', label: 'Active Relationship Types', description: 'Comma-separated list of relationship types to include in queries.', type: 'text', value: 'CONTAINS, INTERPRETS, AMENDS, REFERENCES, DEFINES, DECIDED, APPLIES' },
      { id: 'graph_cache_ttl', label: 'Graph Cache TTL', description: 'Time-to-live for cached graph traversal results.', type: 'select', value: '30 minutes', options: ['5 minutes', '15 minutes', '30 minutes', '1 hour', '6 hours'] },
      { id: 'show_unvalidated', label: 'Show Unvalidated Nodes in UI', description: 'Display pending/unvalidated nodes in the knowledge graph visualization.', type: 'toggle', value: true },
    ],
  },
  {
    id: 'validation',
    label: 'Validation',
    description: 'Entity and relationship validation thresholds and workflows.',
    fields: [
      { id: 'min_confidence', label: 'Minimum Confidence Score', description: 'Entities below this threshold are automatically rejected.', type: 'range', value: 70, min: 50, max: 99, unit: '%' },
      { id: 'review_threshold', label: 'Manual Review Threshold', description: 'Entities above this threshold are automatically approved without review.', type: 'range', value: 95, min: 80, max: 100, unit: '%' },
      { id: 'auto_approve', label: 'Enable Auto-Approval', description: 'Automatically approve entities exceeding the review threshold.', type: 'toggle', value: false },
      { id: 'notify_validation', label: 'Notify on Pending Validation', description: 'Send notifications when the validation queue exceeds 50 items.', type: 'toggle', value: true },
    ],
  },
  {
    id: 'audit',
    label: 'Audit',
    description: 'Audit log retention and event capture configuration.',
    fields: [
      { id: 'retention_days', label: 'Audit Log Retention', description: 'How long to retain audit events before deletion.', type: 'select', value: '90 days', options: ['30 days', '60 days', '90 days', '180 days', '1 year', '7 years'] },
      { id: 'system_events', label: 'Log System Events', description: 'Include automated system events (ingestion, cron jobs) in audit logs.', type: 'toggle', value: true },
      { id: 'failed_logins', label: 'Log Failed Login Attempts', description: 'Record and alert on failed authentication attempts.', type: 'toggle', value: true },
      { id: 'export_format', label: 'Audit Export Format', description: 'File format for audit log exports.', type: 'select', value: 'JSON', options: ['JSON', 'CSV', 'JSONL'] },
    ],
  },
  {
    id: 'system',
    label: 'System',
    description: 'Core system configuration and operational parameters.',
    fields: [
      { id: 'embedding_model', label: 'Embedding Model', description: 'Sentence embedding model used for vector indexing.', type: 'select', value: 'legal-bert-v2', options: ['legal-bert-v2', 'multilingual-e5-large', 'legal-xlm-roberta'] },
      { id: 'graph_model', label: 'NER / Graph Extraction Model', description: 'Model used for entity and relation extraction.', type: 'select', value: 'legal-graph-v2', options: ['legal-graph-v2', 'legal-graph-v3-beta', 'ner-legal-v3'] },
      { id: 'maintenance_mode', label: 'Maintenance Mode', description: 'Disable user access to Juris AI for scheduled maintenance.', type: 'toggle', value: false },
      { id: 'debug_logging', label: 'Extended Debug Logging', description: 'Enable verbose logging for all pipeline components.', type: 'toggle', value: false },
    ],
  },
];

function ToggleSwitch({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      style={{
        width: 40, height: 22, borderRadius: 11, border: 'none', cursor: 'pointer',
        background: value ? '#2563A8' : '#C5D5E8',
        position: 'relative', transition: 'background 0.15s', flexShrink: 0,
      }}
    >
      <span style={{
        position: 'absolute', top: 3, left: value ? 20 : 3, width: 16, height: 16,
        borderRadius: '50%', background: '#fff', transition: 'left 0.15s',
        boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
      }} />
    </button>
  );
}

export default function Settings() {
  const [sections, setSections] = useState<Section[]>(INITIAL_SETTINGS);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['auth', 'research']));
  const [saved, setSaved] = useState(false);

  function toggleSection(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function updateField(sectionId: string, fieldId: string, value: any) {
    setSections(prev => prev.map(s => s.id !== sectionId ? s : {
      ...s,
      fields: s.fields.map(f => f.id !== fieldId ? f : { ...f, value }),
    }));
    setSaved(false);
  }

  function saveAll() {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>System Settings</h1>
          <p style={{ fontSize: 13, color: '#526176' }}>Configure platform behaviour, security, and pipeline parameters.</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span style={{ fontSize: 12, color: '#1E6B45', fontFamily: 'JetBrains Mono, monospace' }}>✓ Saved</span>
          )}
          <button onClick={saveAll}
            className="flex items-center gap-2 px-4 py-2 rounded"
            style={{ background: '#2563A8', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#1E5296')}
            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#2563A8')}>
            <Save size={13} /> Save Settings
          </button>
        </div>
      </div>

      <div style={{ background: '#FBF3D4', border: '1px solid #E8D98A', borderRadius: 6, padding: '10px 14px', display: 'flex', gap: 8, fontSize: 12, color: '#7A5A0F', alignItems: 'flex-start' }}>
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>Changes to these settings affect all Juris AI users and systems. Review carefully before saving. Production secrets and credentials are not exposed here.</span>
      </div>

      <div className="space-y-3">
        {sections.map(section => {
          const open = expanded.has(section.id);
          return (
            <div key={section.id} style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between px-5 py-4"
                style={{ background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left' }}
              >
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#17253A' }}>{section.label}</div>
                  <div style={{ fontSize: 12, color: '#526176', marginTop: 2 }}>{section.description}</div>
                </div>
                {open ? <ChevronUp size={15} style={{ color: '#526176', flexShrink: 0 }} /> : <ChevronDown size={15} style={{ color: '#526176', flexShrink: 0 }} />}
              </button>

              {open && (
                <div style={{ borderTop: '1px solid #C5D5E8' }}>
                  {section.fields.map((field, i) => (
                    <div
                      key={field.id}
                      className="flex items-center justify-between gap-6 px-5"
                      style={{ padding: '14px 20px', borderBottom: i < section.fields.length - 1 ? '1px solid #E7EDF4' : 'none', background: '#F5F7FA' }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: '#17253A' }}>{field.label}</div>
                        {field.description && (
                          <div style={{ fontSize: 11, color: '#526176', marginTop: 3 }}>{field.description}</div>
                        )}
                      </div>
                      <div style={{ flexShrink: 0, minWidth: 180, textAlign: 'right' }}>
                        {field.type === 'toggle' && (
                          <div className="flex items-center justify-end gap-2">
                            <span style={{ fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>
                              {field.value ? 'Enabled' : 'Disabled'}
                            </span>
                            <ToggleSwitch value={field.value as boolean} onChange={v => updateField(section.id, field.id, v)} />
                          </div>
                        )}
                        {field.type === 'select' && (
                          <select
                            value={field.value as string}
                            onChange={e => updateField(section.id, field.id, e.target.value)}
                            style={{ padding: '6px 10px', fontSize: 12, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 5, color: '#17253A', outline: 'none', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace' }}
                          >
                            {field.options?.map(o => <option key={o} value={o}>{o}</option>)}
                          </select>
                        )}
                        {field.type === 'number' && (
                          <div className="flex items-center justify-end gap-2">
                            <input
                              type="number"
                              value={field.value as number}
                              min={field.min} max={field.max}
                              onChange={e => updateField(section.id, field.id, Number(e.target.value))}
                              style={{ width: 80, padding: '6px 10px', fontSize: 12, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 5, color: '#17253A', outline: 'none', fontFamily: 'JetBrains Mono, monospace', textAlign: 'right' }}
                              onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                              onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
                            />
                            {field.unit && <span style={{ fontSize: 11, color: '#526176' }}>{field.unit}</span>}
                          </div>
                        )}
                        {field.type === 'range' && (
                          <div className="flex items-center justify-end gap-3">
                            <input
                              type="range"
                              value={field.value as number}
                              min={field.min} max={field.max}
                              onChange={e => updateField(section.id, field.id, Number(e.target.value))}
                              style={{ width: 120, accentColor: '#2563A8' }}
                            />
                            <span style={{ fontSize: 12, fontWeight: 600, color: '#2563A8', fontFamily: 'JetBrains Mono, monospace', minWidth: 36 }}>
                              {field.value}{field.unit}
                            </span>
                          </div>
                        )}
                        {field.type === 'text' && (
                          <input
                            type="text"
                            value={field.value as string}
                            onChange={e => updateField(section.id, field.id, e.target.value)}
                            style={{ width: 280, padding: '6px 10px', fontSize: 11, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 5, color: '#17253A', outline: 'none', fontFamily: 'JetBrains Mono, monospace' }}
                            onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                            onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
