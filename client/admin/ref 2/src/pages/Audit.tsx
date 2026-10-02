import { useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { AUDIT_EVENTS, AuditEvent, UserRole } from '../data';

function RoleBadge({ role }: { role: UserRole }) {
  const map = {
    SUPER_ADMIN: { bg: '#D9E7F5', color: '#183B5B' },
    ADMIN: { bg: '#E0EEF9', color: '#2563A8' },
    USER: { bg: '#EFF3F7', color: '#526176' },
  };
  const s = map[role];
  return <span style={{ background: s.bg, color: s.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 9, padding: '2px 6px', borderRadius: 3, fontWeight: 600, letterSpacing: '0.04em' }}>{role}</span>;
}

function ResultBadge({ result }: { result: 'Success' | 'Failed' }) {
  return (
    <span style={{ background: result === 'Success' ? '#D0EDDB' : '#F5D9D9', color: result === 'Success' ? '#1E6B45' : '#8B2E2E', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 500 }}>
      {result}
    </span>
  );
}

const ACTION_CATEGORIES = ['All Actions', 'User Management', 'Document Upload', 'Ingestion', 'Validation', 'System Settings', 'Authentication'];

function matchesCategory(event: AuditEvent, cat: string) {
  if (cat === 'All Actions') return true;
  const a = event.action.toLowerCase();
  if (cat === 'User Management') return a.includes('user') || a.includes('administrator');
  if (cat === 'Document Upload') return a.includes('upload') || a.includes('document');
  if (cat === 'Ingestion') return a.includes('ingestion') || a.includes('started');
  if (cat === 'Validation') return a.includes('approved') || a.includes('rejected') || a.includes('validation');
  if (cat === 'System Settings') return a.includes('settings') || a.includes('modified');
  if (cat === 'Authentication') return a.includes('login') || a.includes('sign');
  return true;
}

export default function Audit() {
  const [events] = useState<AuditEvent[]>(AUDIT_EVENTS);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<'All' | UserRole>('All');
  const [resultFilter, setResultFilter] = useState<'All' | 'Success' | 'Failed'>('All');
  const [categoryFilter, setCategoryFilter] = useState('All Actions');

  const filtered = events.filter(e => {
    const matchSearch = !search || e.actor.toLowerCase().includes(search.toLowerCase()) || e.action.toLowerCase().includes(search.toLowerCase()) || e.resource.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === 'All' || e.role === roleFilter;
    const matchResult = resultFilter === 'All' || e.result === resultFilter;
    const matchCat = matchesCategory(e, categoryFilter);
    return matchSearch && matchRole && matchResult && matchCat;
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Audit Logs</h1>
        <p style={{ fontSize: 13, color: '#526176' }}>Track administrative and system actions across Juris AI.</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Events', value: events.length, color: '#17253A' },
          { label: 'Today', value: events.filter(e => e.timestamp.startsWith('Sep 28')).length, color: '#2563A8' },
          { label: 'Success', value: events.filter(e => e.result === 'Success').length, color: '#1E6B45' },
          { label: 'Failed', value: events.filter(e => e.result === 'Failed').length, color: '#8B2E2E' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ fontSize: 10, color: '#526176', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4, letterSpacing: '0.04em' }}>{label.toUpperCase()}</div>
            <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#526176' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search actor, action, resource…"
            style={{ width: '100%', padding: '7px 12px 7px 32px', fontSize: 13, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
            onFocus={e => (e.target.style.borderColor = '#3B82D0')} onBlur={e => (e.target.style.borderColor = '#C5D5E8')} />
        </div>

        <select value={roleFilter} onChange={e => setRoleFilter(e.target.value as any)}
          style={{ padding: '7px 10px', fontSize: 12, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none', cursor: 'pointer' }}>
          <option value="All">All Roles</option>
          <option value="SUPER_ADMIN">SUPER ADMIN</option>
          <option value="ADMIN">ADMIN</option>
          <option value="USER">USER</option>
        </select>

        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          style={{ padding: '7px 10px', fontSize: 12, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none', cursor: 'pointer' }}>
          {ACTION_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <div className="flex gap-1" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, padding: 3 }}>
          {(['All', 'Success', 'Failed'] as const).map(f => (
            <button key={f} onClick={() => setResultFilter(f)}
              style={{ padding: '4px 10px', borderRadius: 4, fontSize: 12, border: 'none', cursor: 'pointer', background: resultFilter === f ? '#2563A8' : 'transparent', color: resultFilter === f ? '#fff' : '#526176' }}>
              {f}
            </button>
          ))}
        </div>

        <span style={{ fontSize: 12, color: '#526176', flexShrink: 0 }}>{filtered.length} events</span>
      </div>

      {/* Dense audit table */}
      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['TIMESTAMP', 'ACTOR', 'ROLE', 'ACTION', 'RESOURCE', 'RESULT'].map((h, i) => (
                  <th key={h} style={{ textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '48px 16px', color: '#526176', fontSize: 13 }}>
                    No audit events match the current filters.
                  </td>
                </tr>
              )}
              {filtered.map((event, i) => (
                <tr key={event.id}
                  style={{ borderBottom: i < filtered.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}>
                  <td style={{ padding: '9px 14px', whiteSpace: 'nowrap' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#526176' }}>{event.timestamp}</span>
                  </td>
                  <td style={{ padding: '9px 14px' }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#17253A' }}>{event.actor}</span>
                  </td>
                  <td style={{ padding: '9px 14px' }}><RoleBadge role={event.role} /></td>
                  <td style={{ padding: '9px 14px', fontSize: 12, color: '#17253A' }}>{event.action}</td>
                  <td style={{ padding: '9px 14px', fontSize: 12, color: '#526176', maxWidth: 240 }}>
                    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{event.resource}</span>
                  </td>
                  <td style={{ padding: '9px 14px' }}><ResultBadge result={event.result} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '10px 16px', borderTop: '1px solid #C5D5E8', background: '#EFF3F7', fontSize: 11, color: '#526176', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Showing {filtered.length} of {events.length} events</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>Retention: 90 days · Last refresh: Sep 28, 10:42 AM</span>
        </div>
      </div>
    </div>
  );
}
