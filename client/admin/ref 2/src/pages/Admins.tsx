import { useState } from 'react';
import { Plus, Shield, Eye, Edit2, Ban, X, Info } from 'lucide-react';
import { ADMINS, User } from '../data';

function Modal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.email || !form.password) { setError('All fields are required.'); return; }
    onClose();
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(23,37,58,0.4)' }}>
      <div className="rounded-lg w-full max-w-md" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 8px 40px rgba(23,37,58,0.14)' }}>
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid #C5D5E8' }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>Create Administrator</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176' }}><X size={16} /></button>
        </div>
        <form onSubmit={submit} className="px-6 py-5 space-y-4">
          {error && (
            <div style={{ background: '#F5D9D9', color: '#8B2E2E', border: '1px solid #E5C5C5', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>{error}</div>
          )}
          <div style={{ background: '#E0EEF9', border: '1px solid #C5D5E8', borderRadius: 6, padding: '10px 12px', fontSize: 12, color: '#183B5B' }}>
            <div className="flex gap-2">
              <Info size={13} style={{ flexShrink: 0, marginTop: 1, color: '#2563A8' }} />
              <span>New administrators are created at the <strong>ADMIN</strong> role level. Super Admin accounts are system-controlled and cannot be created through this interface.</span>
            </div>
          </div>
          {[
            { label: 'Full Name', key: 'name', type: 'text', placeholder: 'Rajiv Sharma' },
            { label: 'Email Address', key: 'email', type: 'email', placeholder: 'admin@juris.ai' },
            { label: 'Temporary Password', key: 'password', type: 'password', placeholder: 'Minimum 12 characters' },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 5 }}>{label}</label>
              <input
                type={type}
                placeholder={placeholder}
                value={(form as any)[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                style={{ width: '100%', padding: '8px 12px', fontSize: 13, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
                onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
              />
            </div>
          ))}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 5 }}>Role</label>
            <div style={{ padding: '8px 12px', background: '#E7EDF4', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176' }}>
              ADMIN — Administrative access (fixed)
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#526176', padding: '8px 12px', background: '#E7EDF4', borderRadius: 6, border: '1px solid #C5D5E8' }}>
            Created by: <strong>Super Administrator</strong>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose} style={{ flex: 1, padding: '8px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>Cancel</button>
            <button type="submit" style={{ flex: 1, padding: '8px 16px', background: '#2563A8', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: 'pointer' }}>Create Administrator</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Admins() {
  const [admins] = useState<User[]>(ADMINS);
  const [showCreate, setShowCreate] = useState(false);

  const superAdmin = admins.find(a => a.role === 'SUPER_ADMIN')!;
  const regularAdmins = admins.filter(a => a.role === 'ADMIN');

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Administrators</h1>
          <p style={{ fontSize: 13, color: '#526176' }}>Manage privileged access to the Juris AI administration system.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded"
          style={{ background: '#2563A8', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#1E5296')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#2563A8')}
        >
          <Plus size={14} /> Create Administrator
        </button>
      </div>

      {/* Role hierarchy */}
      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, padding: '16px 20px' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', marginBottom: 14, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>
          ROLE HIERARCHY
        </div>
        <div className="flex items-start gap-0" style={{ maxWidth: 320 }}>
          {[
            { role: 'SUPER ADMIN', desc: 'Full system control', color: '#183B5B', bg: '#D9E7F5' },
            { role: 'ADMIN', desc: 'Administrative access', color: '#2563A8', bg: '#E0EEF9' },
            { role: 'USER', desc: 'Research access', color: '#526176', bg: '#EFF3F7' },
          ].map((r, i) => (
            <div key={r.role} className="flex flex-col items-center">
              <div
                className="px-4 py-2 rounded text-center"
                style={{ background: r.bg, minWidth: 130 }}
              >
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 600, color: r.color, letterSpacing: '0.06em' }}>{r.role}</div>
                <div style={{ fontSize: 10, color: '#526176', marginTop: 2 }}>{r.desc}</div>
              </div>
              {i < 2 && (
                <div style={{ width: 1, height: 16, background: '#C5D5E8', margin: '0 auto' }} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Super Admin card */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', marginBottom: 10, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>
          SUPER ADMINISTRATOR
        </div>
        <div
          className="rounded-lg p-5 flex items-center gap-4"
          style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderLeft: '3px solid #183B5B' }}
        >
          <div
            className="flex items-center justify-center rounded-full flex-shrink-0"
            style={{ width: 44, height: 44, background: '#183B5B', color: '#fff', fontSize: 14, fontWeight: 700 }}
          >
            SA
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span style={{ fontSize: 14, fontWeight: 600, color: '#17253A' }}>{superAdmin.name}</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#183B5B', background: '#D9E7F5', padding: '2px 6px', borderRadius: 3, fontWeight: 600, letterSpacing: '0.06em' }}>SUPER ADMIN</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#526176', background: '#EFF3F7', padding: '2px 6px', borderRadius: 3, letterSpacing: '0.04em' }}>SYSTEM BOOTSTRAPPED</span>
            </div>
            <div style={{ fontSize: 12, color: '#526176', marginTop: 3 }}>{superAdmin.email}</div>
            <div style={{ fontSize: 11, color: '#526176', marginTop: 2 }}>Status: <span style={{ color: '#1E6B45', fontWeight: 500 }}>Protected</span> · Last active: {superAdmin.lastActive}</div>
          </div>
          <div style={{ fontSize: 11, color: '#526176', textAlign: 'right', flexShrink: 0 }}>
            <Shield size={14} style={{ color: '#183B5B', display: 'block', marginLeft: 'auto', marginBottom: 4 }} />
            No destructive actions available
          </div>
        </div>
      </div>

      {/* Admins table */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', marginBottom: 10, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>
          ADMINISTRATORS ({regularAdmins.length})
        </div>
        <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['NAME', 'EMAIL', 'ROLE', 'STATUS', 'CREATED BY', 'LAST ACTIVE', 'ACTIONS'].map((h, i) => (
                    <th key={h} style={{ textAlign: i === 6 ? 'right' : 'left', fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {regularAdmins.map((admin, i) => (
                  <tr
                    key={admin.id}
                    style={{ borderBottom: i < regularAdmins.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                  >
                    <td style={{ padding: '11px 16px' }}>
                      <div className="flex items-center gap-2.5">
                        <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width: 28, height: 28, background: '#D9E7F5', color: '#2563A8', fontSize: 10, fontWeight: 700 }}>
                          {admin.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 500, color: '#17253A' }}>{admin.name}</span>
                      </div>
                    </td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176' }}>{admin.email}</td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#2563A8', background: '#D9E7F5', padding: '2px 6px', borderRadius: 3, fontWeight: 600 }}>ADMIN</span>
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span className="px-2 py-0.5 rounded-full" style={{ background: admin.status === 'Active' ? '#D0EDDB' : '#F5D9D9', color: admin.status === 'Active' ? '#1E6B45' : '#8B2E2E', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
                        {admin.status}
                      </span>
                    </td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176' }}>{admin.createdBy}</td>
                    <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>{admin.lastActive}</td>
                    <td style={{ padding: '11px 16px' }}>
                      <div className="flex items-center justify-end gap-2">
                        {[{ Icon: Eye, title: 'View', color: '#526176' }, { Icon: Edit2, title: 'Edit', color: '#526176' }, { Icon: Ban, title: 'Disable', color: '#7A5A0F' }].map(({ Icon, title, color }) => (
                          <button key={title} title={title} style={{ background: 'none', border: 'none', cursor: 'pointer', color, padding: 3, borderRadius: 4 }}
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
        </div>
      </div>

      {showCreate && <Modal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
