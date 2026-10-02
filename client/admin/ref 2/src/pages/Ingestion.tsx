import { useState } from 'react';
import { Play, Pause, X, Eye, ChevronDown, ChevronRight, RotateCcw } from 'lucide-react';
import { INGESTION_ACTIVE, INGESTION_COMPLETED, IngestionJob } from '../data';

const PIPELINE_STAGES = [
  'PDF Upload', 'Text Extraction', 'Legal Parsing', 'Entity Extraction',
  'Relation Extraction', 'Embedding', 'FAISS Index', 'Neo4j Graph', 'Validation',
];

function stageIndex(stage: string) {
  const map: Record<string, number> = {
    'PDF Upload': 0, 'Text Extraction': 1, 'Legal Parsing': 2,
    'Entity Extraction': 3, 'Relation Extraction': 4, 'Embedding': 5,
    'FAISS Index': 6, 'Neo4j Graph': 7, 'Validation': 8, 'Completed': 9,
  };
  return map[stage] ?? -1;
}

function JobStatusBadge({ status }: { status: IngestionJob['status'] }) {
  const map = {
    Running: { bg: '#D9E7F5', color: '#2563A8' },
    Completed: { bg: '#D0EDDB', color: '#1E6B45' },
    Failed: { bg: '#F5D9D9', color: '#8B2E2E' },
    Paused: { bg: '#FBF3D4', color: '#7A5A0F' },
  };
  const s = map[status];
  return <span style={{ background: s.bg, color: s.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, fontWeight: 500 }}>{status}</span>;
}

function ActiveJob({ job }: { job: IngestionJob }) {
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(job.progress);
  const stageIdx = stageIndex(job.stage);

  return (
    <div className="rounded-lg" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8' }}>
      <div className="px-5 pt-4 pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div style={{ fontSize: 14, fontWeight: 600, color: '#17253A' }}>{job.docTitle}</div>
            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#2563A8', background: '#D9E7F5', padding: '2px 7px', borderRadius: 3 }}>
                Stage: {job.stage}
              </span>
              <span style={{ fontSize: 11, color: '#526176' }}>Started: {job.startedAt}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button onClick={() => { setPaused(v => !v); }} title={paused ? 'Resume' : 'Pause'}
              style={{ background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, padding: '5px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#526176' }}>
              {paused ? <Play size={12} /> : <Pause size={12} />}
              {paused ? 'Resume' : 'Pause'}
            </button>
            <button title="Cancel" style={{ background: '#F5D9D9', border: '1px solid #E5C5C5', borderRadius: 6, padding: '5px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#8B2E2E' }}>
              <X size={12} /> Cancel
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ marginTop: 14 }}>
          <div className="flex justify-between mb-1.5">
            <span style={{ fontSize: 12, color: '#526176' }}>Overall progress</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#2563A8', fontWeight: 500 }}>{progress}%</span>
          </div>
          <div style={{ height: 6, background: '#D9E7F5', borderRadius: 3 }}>
            <div style={{ height: '100%', width: `${progress}%`, background: paused ? '#8EB4DA' : '#2563A8', borderRadius: 3, transition: 'width 0.5s ease' }} />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mt-4">
          {[
            { label: 'Entities', value: job.entities.toLocaleString() },
            { label: 'Relations', value: job.relations.toLocaleString() },
            { label: 'Status', value: paused ? 'Paused' : 'Running' },
          ].map(({ label, value }) => (
            <div key={label} style={{ background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, padding: '8px 12px' }}>
              <div style={{ fontSize: 10, color: '#526176', marginBottom: 3, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em' }}>{label.toUpperCase()}</div>
              <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 18, color: '#183B5B' }}>{value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline mini-tracker */}
      <div style={{ borderTop: '1px solid #C5D5E8', padding: '12px 20px', overflowX: 'auto' }}>
        <div className="flex items-center gap-0" style={{ minWidth: 600 }}>
          {PIPELINE_STAGES.map((s, i) => {
            const done = i < stageIdx;
            const active = i === stageIdx;
            return (
              <div key={s} className="flex items-center">
                <div className="flex flex-col items-center" style={{ minWidth: 70 }}>
                  <div
                    className="rounded-full flex items-center justify-center"
                    style={{
                      width: 22, height: 22,
                      background: done ? '#2563A8' : active ? '#D9E7F5' : '#E7EDF4',
                      border: active ? '2px solid #2563A8' : 'none',
                      fontSize: 9, fontWeight: 700, color: done ? '#fff' : active ? '#2563A8' : '#526176',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    {done ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize: 9, color: active ? '#2563A8' : done ? '#526176' : '#C5D5E8', marginTop: 4, textAlign: 'center', lineHeight: 1.2, fontWeight: active ? 600 : 400 }}>
                    {s}
                  </span>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div style={{ width: 20, height: 1, background: done ? '#2563A8' : '#C5D5E8', flexShrink: 0, marginTop: -12 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function Ingestion() {
  const [activeJobs] = useState<IngestionJob[]>(INGESTION_ACTIVE);
  const [completedJobs] = useState<IngestionJob[]>(INGESTION_COMPLETED);
  const [expandedCompleted, setExpandedCompleted] = useState(true);

  return (
    <div className="space-y-6">
      <div>
        <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Ingestion Pipeline</h1>
        <p style={{ fontSize: 13, color: '#526176' }}>Monitor and control legal knowledge processing.</p>
      </div>

      {/* Pipeline overview strip */}
      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, padding: '16px 20px' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', marginBottom: 14, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>
          PIPELINE ARCHITECTURE
        </div>
        <div className="flex items-start flex-wrap gap-0">
          {PIPELINE_STAGES.map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className="px-3 py-1.5 rounded text-center"
                style={{ background: '#EFF3F7', border: '1px solid #C5D5E8', fontSize: 11, color: '#17253A', fontWeight: 500, whiteSpace: 'nowrap' }}
              >
                {s}
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <ChevronRight size={12} style={{ color: '#C5D5E8', flexShrink: 0, margin: '0 2px' }} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Active Jobs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div style={{ fontSize: 13, fontWeight: 600, color: '#17253A' }}>
            Active Jobs <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#2563A8', background: '#D9E7F5', padding: '1px 7px', borderRadius: 3, marginLeft: 6 }}>{activeJobs.length}</span>
          </div>
        </div>
        {activeJobs.length === 0 ? (
          <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, padding: '40px 24px', textAlign: 'center', color: '#526176', fontSize: 13 }}>
            No active ingestion jobs.
          </div>
        ) : (
          <div className="space-y-4">
            {activeJobs.map(job => <ActiveJob key={job.id} job={job} />)}
          </div>
        )}
      </div>

      {/* Completed Jobs */}
      <div>
        <button
          onClick={() => setExpandedCompleted(v => !v)}
          className="flex items-center gap-2 mb-3 w-full text-left"
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
        >
          {expandedCompleted ? <ChevronDown size={14} style={{ color: '#526176' }} /> : <ChevronRight size={14} style={{ color: '#526176' }} />}
          <span style={{ fontSize: 13, fontWeight: 600, color: '#17253A' }}>
            Completed / Failed Jobs
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#526176', background: '#EFF3F7', padding: '1px 7px', borderRadius: 3, marginLeft: 6 }}>{completedJobs.length}</span>
          </span>
        </button>

        {expandedCompleted && (
          <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['DOCUMENT', 'DURATION', 'ENTITIES', 'RELATIONS', 'STATUS', 'COMPLETED AT', 'ACTIONS'].map((h, i) => (
                      <th key={h} style={{ textAlign: i === 6 ? 'right' : 'left', fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '11px 16px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {completedJobs.map((job, i) => (
                    <tr key={job.id} style={{ borderBottom: i < completedJobs.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                      onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                      onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}>
                      <td style={{ padding: '10px 16px', fontSize: 13, fontWeight: 500, color: '#17253A' }}>{job.docTitle}</td>
                      <td style={{ padding: '10px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>{job.duration}</td>
                      <td style={{ padding: '10px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>{job.entities > 0 ? job.entities.toLocaleString() : '—'}</td>
                      <td style={{ padding: '10px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>{job.relations > 0 ? job.relations.toLocaleString() : '—'}</td>
                      <td style={{ padding: '10px 16px' }}><JobStatusBadge status={job.status} /></td>
                      <td style={{ padding: '10px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>{job.completedAt}</td>
                      <td style={{ padding: '10px 16px' }}>
                        <div className="flex items-center justify-end gap-2">
                          <button title="View Logs" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176', padding: 3, borderRadius: 4 }}
                            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
                            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
                            <Eye size={13} />
                          </button>
                          {job.status === 'Failed' && (
                            <button title="Retry" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#2563A8', padding: 3, borderRadius: 4 }}
                              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#D9E7F5')}
                              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
                              <RotateCcw size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
