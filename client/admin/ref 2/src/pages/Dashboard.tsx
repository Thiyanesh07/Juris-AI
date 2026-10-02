import { Users, FileText, Network, CheckSquare, Activity, Database, Server, Cpu, AlertTriangle } from 'lucide-react';
import { ACTIVITY_FEED } from '../data';

const KPI_CARDS = [
  { label: 'Total Users', value: '1,248', sub: '+14 this month', Icon: Users, color: '#2563A8', bg: '#D9E7F5' },
  { label: 'Active Users', value: '386', sub: '30-day active', Icon: Activity, color: '#2563A8', bg: '#D9E7F5' },
  { label: 'Legal Documents', value: '4,892', sub: '10 pending upload', Icon: FileText, color: '#2563A8', bg: '#D9E7F5' },
  { label: 'Graph Entities', value: '38,421', sub: 'Across 16 types', Icon: Network, color: '#2563A8', bg: '#D9E7F5' },
  { label: 'Relationships', value: '112,804', sub: 'In knowledge graph', Icon: Database, color: '#2563A8', bg: '#D9E7F5' },
  { label: 'Pending Validation', value: '27', sub: '5 high confidence', Icon: CheckSquare, color: '#7A5A0F', bg: '#FBF3D4' },
];

const PIPELINE_STAGES = [
  { label: 'Document Ingestion', detail: '4,892 / 4,892 documents', status: 'healthy', pct: 100 },
  { label: 'Text Extraction', detail: '4,892 documents processed', status: 'healthy', pct: 100 },
  { label: 'Legal Structure Parsing', detail: '4,843 structured', status: 'healthy', pct: 99 },
  { label: 'Entity Extraction', detail: '38,421 entities identified', status: 'healthy', pct: 100 },
  { label: 'Relation Extraction', detail: '112,804 relationships mapped', status: 'healthy', pct: 100 },
  { label: 'Embedding Generation', detail: '4,871 documents embedded', status: 'healthy', pct: 99.6 },
  { label: 'Vector Index (FAISS)', detail: '4,871 documents indexed', status: 'healthy', pct: 100 },
  { label: 'Knowledge Graph (Neo4j)', detail: 'Healthy — 38,421 nodes', status: 'healthy', pct: 100 },
  { label: 'Validation Queue', detail: '27 items awaiting review', status: 'warning', pct: null },
];

const HEALTH_SERVICES = [
  { label: 'API Gateway', status: 'Healthy', latency: '28ms' },
  { label: 'PostgreSQL', status: 'Healthy', latency: '4ms' },
  { label: 'Neo4j Graph DB', status: 'Healthy', latency: '12ms' },
  { label: 'FAISS Vector Index', status: 'Healthy', latency: '18ms' },
  { label: 'Ingestion Worker', status: 'Healthy', latency: '—' },
  { label: 'Embedding Service', status: 'Healthy', latency: '92ms' },
];

function ActivityDot({ type }: { type: string }) {
  const colors: Record<string, string> = {
    admin: '#2563A8', document: '#3B82D0', ingestion: '#526176', validation: '#1E6B45', user: '#8B2E2E',
  };
  return (
    <span
      className="rounded-full flex-shrink-0 mt-1.5"
      style={{ width: 7, height: 7, background: colors[type] || '#526176', display: 'inline-block' }}
    />
  );
}

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>
          System Overview
        </h1>
        <p style={{ fontSize: 13, color: '#526176' }}>
          Monitor the Juris AI legal knowledge and research infrastructure.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {KPI_CARDS.map(({ label, value, sub, Icon, color, bg }) => (
          <div
            key={label}
            className="rounded-lg p-4"
            style={{ background: '#F5F7FA', border: '1px solid #C5D5E8' }}
          >
            <div className="flex items-start justify-between mb-2">
              <span style={{ fontSize: 11, color: '#526176', fontWeight: 500, lineHeight: 1.3 }}>{label}</span>
              <div
                className="rounded p-1 flex-shrink-0"
                style={{ background: bg }}
              >
                <Icon size={12} style={{ color }} />
              </div>
            </div>
            <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 22, color: '#183B5B', lineHeight: 1 }}>
              {value}
            </div>
            <div style={{ fontSize: 11, color: '#526176', marginTop: 4 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Pipeline + Activity row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Pipeline */}
        <div
          className="lg:col-span-2 rounded-lg"
          style={{ background: '#F5F7FA', border: '1px solid #C5D5E8' }}
        >
          <div
            className="px-5 py-3.5 flex items-center justify-between"
            style={{ borderBottom: '1px solid #C5D5E8' }}
          >
            <div>
              <h2 style={{ fontSize: 13, fontWeight: 600, color: '#17253A' }}>Knowledge Processing Pipeline</h2>
              <p style={{ fontSize: 11, color: '#526176', marginTop: 2 }}>End-to-end ingestion and indexing status</p>
            </div>
            <span
              className="px-2 py-0.5 rounded text-xs"
              style={{ background: '#D0EDDB', color: '#1E6B45', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}
            >
              OPERATIONAL
            </span>
          </div>
          <div className="px-5 py-4 space-y-3">
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={stage.label} className="flex items-center gap-3">
                {/* Stage number */}
                <div
                  className="rounded-full flex items-center justify-center flex-shrink-0"
                  style={{
                    width: 22, height: 22,
                    background: stage.status === 'warning' ? '#FBF3D4' : '#D9E7F5',
                    color: stage.status === 'warning' ? '#7A5A0F' : '#2563A8',
                    fontSize: 10, fontWeight: 600,
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  {i + 1}
                </div>
                {/* Label + bar */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#17253A' }}>{stage.label}</span>
                    <span style={{ fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace', flexShrink: 0, marginLeft: 8 }}>
                      {stage.detail}
                    </span>
                  </div>
                  {stage.pct !== null && (
                    <div style={{ height: 3, background: '#C5D5E8', borderRadius: 2 }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${stage.pct}%`,
                          background: stage.status === 'warning' ? '#C8A830' : '#2563A8',
                          borderRadius: 2,
                        }}
                      />
                    </div>
                  )}
                </div>
                {/* Status dot */}
                <div
                  className="rounded-full flex-shrink-0"
                  style={{
                    width: 7, height: 7,
                    background: stage.status === 'warning' ? '#C8A830' : '#1E6B45',
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div
          className="rounded-lg"
          style={{ background: '#F5F7FA', border: '1px solid #C5D5E8' }}
        >
          <div
            className="px-5 py-3.5"
            style={{ borderBottom: '1px solid #C5D5E8' }}
          >
            <h2 style={{ fontSize: 13, fontWeight: 600, color: '#17253A' }}>Recent Activity</h2>
            <p style={{ fontSize: 11, color: '#526176', marginTop: 2 }}>System and administrator actions</p>
          </div>
          <div className="px-5 py-4">
            <div className="space-y-4">
              {ACTIVITY_FEED.map((ev, i) => (
                <div key={ev.id} className="flex gap-3">
                  <ActivityDot type={ev.type} />
                  <div>
                    <p style={{ fontSize: 12, color: '#17253A', lineHeight: 1.4 }}>
                      <strong>{ev.actor}</strong> {ev.action}{' '}
                      <span style={{ color: '#2563A8' }}>{ev.target}</span>
                    </p>
                    <p style={{ fontSize: 11, color: '#526176', marginTop: 2, fontFamily: 'JetBrains Mono, monospace' }}>
                      {ev.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Health */}
      <div
        className="rounded-lg"
        style={{ background: '#F5F7FA', border: '1px solid #C5D5E8' }}
      >
        <div
          className="px-5 py-3.5"
          style={{ borderBottom: '1px solid #C5D5E8' }}
        >
          <h2 style={{ fontSize: 13, fontWeight: 600, color: '#17253A' }}>System Health</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-px" style={{ background: '#C5D5E8' }}>
          {HEALTH_SERVICES.map(({ label, status, latency }) => (
            <div
              key={label}
              className="px-4 py-3"
              style={{ background: '#F5F7FA' }}
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                <span
                  className="rounded-full"
                  style={{ width: 7, height: 7, background: '#1E6B45', display: 'inline-block', flexShrink: 0 }}
                />
                <span style={{ fontSize: 11, fontWeight: 500, color: '#1E6B45', fontFamily: 'JetBrains Mono, monospace' }}>
                  {status}
                </span>
              </div>
              <div style={{ fontSize: 12, fontWeight: 500, color: '#17253A' }}>{label}</div>
              {latency !== '—' && (
                <div style={{ fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>
                  {latency}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
