import { useState } from 'react';
import { CheckCircle, XCircle, Eye, X, AlertTriangle } from 'lucide-react';
import { VALIDATION_ITEMS, ValidationItem, ValidationStatus } from '../data';

function ConfidenceBadge({ pct }: { pct: number }) {
  const color = pct >= 95 ? '#1E6B45' : pct >= 85 ? '#7A5A0F' : '#8B2E2E';
  const bg = pct >= 95 ? '#D0EDDB' : pct >= 85 ? '#FBF3D4' : '#F5D9D9';
  return (
    <span style={{ background: bg, color, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, fontWeight: 600 }}>
      {pct}%
    </span>
  );
}

function TypeBadge({ type }: { type: 'ENTITY' | 'RELATION' }) {
  return (
    <span style={{ background: type === 'ENTITY' ? '#E0EEF9' : '#D9E7F5', color: type === 'ENTITY' ? '#183B5B' : '#2563A8', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, fontWeight: 600 }}>
      {type}
    </span>
  );
}

function StatusBadge({ status }: { status: ValidationStatus }) {
  const map = {
    Pending: { bg: '#FBF3D4', color: '#7A5A0F' },
    Approved: { bg: '#D0EDDB', color: '#1E6B45' },
    Rejected: { bg: '#F5D9D9', color: '#8B2E2E' },
  };
  const s = map[status];
  return <span style={{ background: s.bg, color: s.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, fontWeight: 500 }}>{status}</span>;
}

function ReviewModal({ item, onClose, onApprove, onReject }: {
  item: ValidationItem;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(23,37,58,0.4)' }}>
      <div className="rounded-lg w-full max-w-xl" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 8px 40px rgba(23,37,58,0.14)', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div className="flex items-center justify-between px-6 py-4 flex-shrink-0" style={{ borderBottom: '1px solid #C5D5E8' }}>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>Validation Review</h2>
            <div className="flex items-center gap-2 mt-1">
              <TypeBadge type={item.type} />
              <ConfidenceBadge pct={item.confidence} />
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176' }}><X size={16} /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Entity */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: 8 }}>EXTRACTED {item.type}</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>{item.entity}</div>
          </div>

          {/* Source passage — visually prominent */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: 8 }}>SOURCE PASSAGE</div>
            <div style={{ background: '#E0EEF9', border: '1px solid #C5D5E8', borderLeft: '3px solid #2563A8', borderRadius: '0 6px 6px 0', padding: '12px 14px' }}>
              <p style={{ fontSize: 13, color: '#17253A', lineHeight: 1.6, fontStyle: 'italic' }}>
                "{item.passage}"
              </p>
            </div>
          </div>

          {/* Document metadata */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: 8 }}>DOCUMENT METADATA</div>
            <div style={{ background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, padding: '10px 14px' }}>
              <div style={{ fontSize: 12, color: '#17253A', fontWeight: 500 }}>{item.docMeta}</div>
              <div style={{ fontSize: 11, color: '#526176', marginTop: 4 }}>Source file: {item.source}</div>
            </div>
          </div>

          {/* Model info */}
          <div className="flex gap-4">
            {[
              { label: 'Model', value: item.model },
              { label: 'Confidence', value: `${item.confidence}%` },
              { label: 'Type', value: item.type },
            ].map(({ label, value }) => (
              <div key={label} style={{ flex: 1, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, padding: '8px 12px' }}>
                <div style={{ fontSize: 10, color: '#526176', fontFamily: 'JetBrains Mono, monospace', marginBottom: 3 }}>{label.toUpperCase()}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#17253A', fontFamily: 'JetBrains Mono, monospace' }}>{value}</div>
              </div>
            ))}
          </div>

          {item.confidence < 90 && (
            <div style={{ background: '#FBF3D4', border: '1px solid #E8D98A', borderRadius: 6, padding: '10px 12px', display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#7A5A0F' }}>
              <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>Confidence below 90%. Manual review is strongly recommended before approving.</span>
            </div>
          )}
        </div>

        <div className="px-6 py-4 flex gap-3 flex-shrink-0" style={{ borderTop: '1px solid #C5D5E8' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '9px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>
            Request Further Review
          </button>
          <button onClick={() => { onReject(item.id); onClose(); }}
            style={{ flex: 1, padding: '9px 16px', background: '#F5D9D9', border: '1px solid #E5C5C5', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#8B2E2E', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <XCircle size={14} /> Reject
          </button>
          <button onClick={() => { onApprove(item.id); onClose(); }}
            style={{ flex: 1, padding: '9px 16px', background: '#2563A8', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <CheckCircle size={14} /> Approve
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Validation() {
  const [items, setItems] = useState<ValidationItem[]>(VALIDATION_ITEMS);
  const [tab, setTab] = useState<ValidationStatus>('Pending');
  const [reviewing, setReviewing] = useState<ValidationItem | null>(null);

  function approve(id: string) { setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'Approved' as const } : i)); }
  function reject(id: string) { setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'Rejected' as const } : i)); }

  const displayed = items.filter(i => i.status === tab);

  const counts = {
    Pending: items.filter(i => i.status === 'Pending').length,
    Approved: items.filter(i => i.status === 'Approved').length,
    Rejected: items.filter(i => i.status === 'Rejected').length,
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Validation Queue</h1>
        <p style={{ fontSize: 13, color: '#526176' }}>Review extracted legal entities and relationships before they become trusted knowledge.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {([['Pending', '#FBF3D4', '#7A5A0F'], ['Approved', '#D0EDDB', '#1E6B45'], ['Rejected', '#F5D9D9', '#8B2E2E']] as const).map(([label, bg, color]) => (
          <div key={label} style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, padding: '14px 16px' }}>
            <div style={{ fontSize: 11, color: '#526176', marginBottom: 6 }}>{label}</div>
            <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 28, color: '#183B5B' }}>{counts[label as ValidationStatus]}</div>
            <div style={{ display: 'inline-block', background: bg, color, fontFamily: 'JetBrains Mono, monospace', fontSize: 9, padding: '1px 6px', borderRadius: 3, marginTop: 4 }}>
              {label.toUpperCase()}
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #C5D5E8', display: 'flex', gap: 0 }}>
        {(['Pending', 'Approved', 'Rejected'] as ValidationStatus[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: '9px 20px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: tab === t ? 600 : 400, color: tab === t ? '#2563A8' : '#526176', borderBottom: tab === t ? '2px solid #2563A8' : '2px solid transparent', marginBottom: -1 }}>
            {t}
            <span style={{ marginLeft: 6, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, background: tab === t ? '#D9E7F5' : '#EFF3F7', color: tab === t ? '#2563A8' : '#526176', padding: '1px 5px', borderRadius: 3 }}>
              {counts[t]}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
        {displayed.length === 0 ? (
          <div style={{ padding: '60px 24px', textAlign: 'center', color: '#526176', fontSize: 13 }}>
            No {tab.toLowerCase()} items.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['TYPE', 'ENTITY / RELATION', 'SOURCE', 'CONFIDENCE', 'STATUS', 'ACTIONS'].map((h, i) => (
                    <th key={h} style={{ textAlign: i === 5 ? 'right' : 'left', fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayed.map((item, i) => (
                  <tr key={item.id} style={{ borderBottom: i < displayed.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}>
                    <td style={{ padding: '11px 16px' }}><TypeBadge type={item.type} /></td>
                    <td style={{ padding: '11px 16px', fontSize: 13, fontWeight: 500, color: '#17253A' }}>{item.entity}</td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176' }}>{item.source}</td>
                    <td style={{ padding: '11px 16px' }}><ConfidenceBadge pct={item.confidence} /></td>
                    <td style={{ padding: '11px 16px' }}><StatusBadge status={item.status} /></td>
                    <td style={{ padding: '11px 16px' }}>
                      <div className="flex items-center justify-end gap-2">
                        <button onClick={() => setReviewing(item)} title="Review"
                          style={{ padding: '4px 10px', background: '#D9E7F5', border: '1px solid #C5D5E8', borderRadius: 5, fontSize: 12, color: '#2563A8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 500 }}>
                          <Eye size={12} /> Review
                        </button>
                        {item.status === 'Pending' && (
                          <>
                            <button onClick={() => approve(item.id)} title="Approve"
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#1E6B45', padding: 3, borderRadius: 4 }}
                              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#D0EDDB')}
                              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
                              <CheckCircle size={14} />
                            </button>
                            <button onClick={() => reject(item.id)} title="Reject"
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8B2E2E', padding: 3, borderRadius: 4 }}
                              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F5D9D9')}
                              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
                              <XCircle size={14} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {reviewing && (
        <ReviewModal
          item={reviewing}
          onClose={() => setReviewing(null)}
          onApprove={approve}
          onReject={reject}
        />
      )}
    </div>
  );
}
