import { useState } from 'react';
import { Search, Plus, Eye, RefreshCw, Archive, AlertCircle, X, Upload } from 'lucide-react';
import { DOCUMENTS, Document, DocStatus } from '../data';

function StatusBadge({ status }: { status: DocStatus }) {
  const map: Record<DocStatus, { bg: string; color: string }> = {
    Indexed: { bg: '#D0EDDB', color: '#1E6B45' },
    Processing: { bg: '#D9E7F5', color: '#2563A8' },
    'Pending Validation': { bg: '#FBF3D4', color: '#7A5A0F' },
    Failed: { bg: '#F5D9D9', color: '#8B2E2E' },
    Archived: { bg: '#EFF3F7', color: '#526176' },
  };
  const s = map[status] || { bg: '#EFF3F7', color: '#526176' };
  return (
    <span style={{ background: s.bg, color: s.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, fontWeight: 500, whiteSpace: 'nowrap' }}>
      {status}
    </span>
  );
}

function UploadModal({ onClose }: { onClose: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<string | null>(null);
  const [step, setStep] = useState<'upload' | 'meta'>('upload');
  const [meta, setMeta] = useState({ title: '', type: 'Statute', source: '', version: 'v1', effectiveDate: '' });

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(23,37,58,0.4)' }}>
      <div className="rounded-lg w-full max-w-lg" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 8px 40px rgba(23,37,58,0.14)' }}>
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid #C5D5E8' }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>
            {step === 'upload' ? 'Upload Legal Document' : 'Document Metadata'}
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176' }}><X size={16} /></button>
        </div>

        {step === 'upload' ? (
          <div className="px-6 py-5 space-y-4">
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => { e.preventDefault(); setDragging(false); setFile(e.dataTransfer.files[0]?.name || null); }}
              onClick={() => setFile('Constitution-Amendment.pdf')}
              className="rounded-lg flex flex-col items-center justify-center gap-3 cursor-pointer"
              style={{
                border: `2px dashed ${dragging ? '#2563A8' : '#C5D5E8'}`,
                background: dragging ? '#E0EEF9' : '#EFF3F7',
                padding: '40px 24px',
                transition: 'all 0.15s',
              }}
            >
              <Upload size={24} style={{ color: file ? '#2563A8' : '#526176' }} />
              {file ? (
                <div className="text-center">
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#2563A8' }}>{file}</div>
                  <div style={{ fontSize: 11, color: '#526176', marginTop: 4 }}>Click to change file</div>
                </div>
              ) : (
                <div className="text-center">
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#17253A' }}>Drop PDF here or click to browse</div>
                  <div style={{ fontSize: 11, color: '#526176', marginTop: 4 }}>Supported formats: PDF, DOCX, TXT · Max 500MB</div>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={onClose} style={{ flex: 1, padding: '8px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>Cancel</button>
              <button onClick={() => file && setStep('meta')} style={{ flex: 1, padding: '8px 16px', background: file ? '#2563A8' : '#8EB4DA', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: file ? 'pointer' : 'not-allowed' }}>Next</button>
            </div>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-4">
            {[
              { label: 'Document Title', key: 'title', type: 'text', placeholder: 'e.g. Constitution (Fifty-Second Amendment) Act, 1985' },
              { label: 'Source', key: 'source', type: 'text', placeholder: 'e.g. Government of India' },
              { label: 'Version', key: 'version', type: 'text', placeholder: 'v1' },
              { label: 'Effective Date', key: 'effectiveDate', type: 'text', placeholder: 'e.g. Jan 26, 1950' },
            ].map(({ label, key, type, placeholder }) => (
              <div key={key}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 5 }}>{label}</label>
                <input type={type} placeholder={placeholder} value={(meta as any)[key]} onChange={e => setMeta(m => ({ ...m, [key]: e.target.value }))}
                  style={{ width: '100%', padding: '8px 12px', fontSize: 13, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
                  onFocus={e => (e.target.style.borderColor = '#3B82D0')} onBlur={e => (e.target.style.borderColor = '#C5D5E8')} />
              </div>
            ))}
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 5 }}>Document Type</label>
              <select value={meta.type} onChange={e => setMeta(m => ({ ...m, type: e.target.value }))}
                style={{ width: '100%', padding: '8px 12px', fontSize: 13, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}>
                {['Constitution', 'Statute', 'Amendment', 'Judgments', 'Rule', 'Regulation'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setStep('upload')} style={{ flex: 1, padding: '8px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>Back</button>
              <button onClick={onClose} style={{ flex: 1, padding: '8px 16px', background: '#2563A8', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: 'pointer' }}>Upload & Queue Ingestion</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Documents() {
  const [docs] = useState<Document[]>(DOCUMENTS);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<DocStatus | 'All'>('All');
  const [showUpload, setShowUpload] = useState(false);
  const [selected, setSelected] = useState<Document | null>(null);

  const FILTERS: (DocStatus | 'All')[] = ['All', 'Indexed', 'Processing', 'Pending Validation', 'Failed', 'Archived'];

  const filtered = docs
    .filter(d => filter === 'All' || d.status === filter)
    .filter(d => d.title.toLowerCase().includes(search.toLowerCase()) || d.type.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Legal Documents</h1>
          <p style={{ fontSize: 13, color: '#526176' }}>Manage the authoritative legal corpus used by Juris AI.</p>
        </div>
        <button onClick={() => setShowUpload(true)} className="flex items-center gap-2 px-4 py-2 rounded"
          style={{ background: '#2563A8', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#1E5296')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#2563A8')}>
          <Plus size={14} /> Upload Document
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#526176' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search documents…"
            style={{ width: '100%', padding: '7px 12px 7px 32px', fontSize: 13, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
            onFocus={e => (e.target.style.borderColor = '#3B82D0')} onBlur={e => (e.target.style.borderColor = '#C5D5E8')} />
        </div>
        <div className="flex gap-1 flex-wrap" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, padding: 3 }}>
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{ padding: '4px 10px', borderRadius: 4, fontSize: 11, border: 'none', cursor: 'pointer', background: filter === f ? '#2563A8' : 'transparent', color: filter === f ? '#fff' : '#526176', whiteSpace: 'nowrap' }}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['DOCUMENT', 'TYPE', 'SOURCE', 'VERSION', 'STATUS', 'UPLOADED', 'ACTIONS'].map((h, i) => (
                  <th key={h} style={{ textAlign: i === 6 ? 'right' : 'left', fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc, i) => (
                <tr key={doc.id} style={{ borderBottom: i < filtered.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}>
                  <td style={{ padding: '11px 16px' }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: '#17253A', cursor: 'pointer' }} onClick={() => setSelected(doc)}>
                      {doc.title}
                    </div>
                    {doc.effectiveDate && <div style={{ fontSize: 11, color: '#526176', marginTop: 2 }}>Effective: {doc.effectiveDate}</div>}
                  </td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176', whiteSpace: 'nowrap' }}>{doc.type}</td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176' }}>{doc.source}</td>
                  <td style={{ padding: '11px 16px' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#526176', background: '#E7EDF4', padding: '2px 6px', borderRadius: 3 }}>{doc.version}</span>
                  </td>
                  <td style={{ padding: '11px 16px' }}><StatusBadge status={doc.status} /></td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>{doc.uploaded}</td>
                  <td style={{ padding: '11px 16px' }}>
                    <div className="flex items-center justify-end gap-2">
                      {[
                        { Icon: Eye, title: 'View', color: '#526176', onClick: () => setSelected(doc) },
                        { Icon: RefreshCw, title: 'Reprocess', color: '#2563A8' },
                        { Icon: Archive, title: 'Archive', color: '#526176' },
                      ].map(({ Icon, title, color, onClick }) => (
                        <button key={title} title={title} onClick={onClick} style={{ background: 'none', border: 'none', cursor: 'pointer', color, padding: 3, borderRadius: 4 }}
                          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
                          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
                          <Icon size={13} />
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '10px 16px', borderTop: '1px solid #C5D5E8', background: '#EFF3F7', fontSize: 11, color: '#526176' }}>
          Showing {filtered.length} of {docs.length} documents
        </div>
      </div>

      {/* Document detail panel */}
      {selected && (
        <div className="fixed inset-0 z-50 flex" style={{ background: 'rgba(23,37,58,0.4)' }} onClick={() => setSelected(null)}>
          <div className="ml-auto h-full flex flex-col" style={{ width: 420, background: '#F5F7FA', borderLeft: '1px solid #C5D5E8', boxShadow: '-8px 0 40px rgba(23,37,58,0.1)' }} onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid #C5D5E8', flexShrink: 0 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>Document Details</div>
              </div>
              <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176' }}><X size={16} /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              <div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#17253A', lineHeight: 1.3 }}>{selected.title}</div>
                <div style={{ marginTop: 6 }}><StatusBadge status={selected.status} /></div>
              </div>
              {[
                { label: 'Document Type', value: selected.type },
                { label: 'Source', value: selected.source },
                { label: 'Version', value: selected.version },
                { label: 'Effective Date', value: selected.effectiveDate || '—' },
                { label: 'Uploaded By', value: selected.uploadedBy },
                { label: 'Upload Date', value: selected.uploaded },
                { label: 'Pages', value: selected.pages ? `${selected.pages.toLocaleString()} pages` : '—' },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #E7EDF4' }}>
                  <span style={{ fontSize: 12, color: '#526176' }}>{label}</span>
                  <span style={{ fontSize: 12, color: '#17253A', fontWeight: 500, textAlign: 'right', maxWidth: '55%' }}>{value}</span>
                </div>
              ))}
              <div style={{ marginTop: 4 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', marginBottom: 10, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>PROCESSING STATUS</div>
                {[
                  { label: 'Text Extraction', val: selected.status === 'Failed' ? 'Failed' : 'Complete', ok: selected.status !== 'Failed' },
                  { label: 'Entity Extraction', val: selected.entities ? `${selected.entities.toLocaleString()} entities` : (selected.status === 'Processing' ? 'In Progress' : '—'), ok: !!selected.entities },
                  { label: 'Relation Extraction', val: selected.relations ? `${selected.relations.toLocaleString()} relations` : (selected.status === 'Processing' ? 'In Progress' : '—'), ok: !!selected.relations },
                  { label: 'Vector Embedding', val: selected.status === 'Indexed' ? 'Complete' : selected.status === 'Processing' ? 'Queued' : '—', ok: selected.status === 'Indexed' },
                  { label: 'Graph Indexing', val: selected.status === 'Indexed' ? 'Complete' : '—', ok: selected.status === 'Indexed' },
                  { label: 'Validation', val: selected.status === 'Pending Validation' ? 'Pending Review' : selected.status === 'Indexed' ? 'Approved' : '—', ok: selected.status === 'Indexed' },
                ].map(({ label, val, ok }) => (
                  <div key={label} className="flex items-center justify-between py-1.5">
                    <span style={{ fontSize: 12, color: '#526176' }}>{label}</span>
                    <span style={{ fontSize: 11, color: ok ? '#1E6B45' : val === '—' ? '#526176' : val.includes('Progress') ? '#2563A8' : '#8B2E2E', fontFamily: 'JetBrains Mono, monospace', background: ok ? '#D0EDDB' : '#E7EDF4', padding: '1px 6px', borderRadius: 3 }}>{val}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="px-5 py-4 space-y-2" style={{ borderTop: '1px solid #C5D5E8', flexShrink: 0 }}>
              {['View Source', 'Reprocess Document', 'View Processing Logs'].map(label => (
                <button key={label} style={{ width: '100%', padding: '8px 12px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 12, color: '#17253A', cursor: 'pointer', textAlign: 'left' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#D9E7F5')}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#EFF3F7')}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}
