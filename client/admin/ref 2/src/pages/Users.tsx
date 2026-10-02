import { useState } from 'react';
import { Search, Plus, Eye, Edit2, Ban, Trash2, X, ChevronUp, ChevronDown } from 'lucide-react';
import { USERS, User, UserStatus } from '../data';

function Badge({ status }: { status: UserStatus }) {
  const s = status === 'Active'
    ? { bg: '#D0EDDB', color: '#1E6B45' }
    : { bg: '#F5D9D9', color: '#8B2E2E' };
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: s.bg, color: s.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}
    >
      {status}
    </span>
  );
}

type SortKey = 'name' | 'email' | 'created' | 'lastActive';

function Modal({ onClose, onSave }: { onClose: () => void; onSave: (u: Partial<User>) => void }) {
  const [form, setForm] = useState({ name: '', email: '', role: 'USER' as const, password: '' });
  const [error, setError] = useState('');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.email || !form.password) { setError('All fields are required.'); return; }
    onSave(form);
    onClose();
  }

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: 'rgba(23,37,58,0.4)' }}
    >
      <div
        className="rounded-lg w-full max-w-md"
        style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 8px 40px rgba(23,37,58,0.14)' }}
      >
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid #C5D5E8' }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#183B5B', fontFamily: 'DM Serif Display, serif' }}>Create User</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176' }}>
            <X size={16} />
          </button>
        </div>
        <form onSubmit={submit} className="px-6 py-5 space-y-4">
          {error && (
            <div style={{ background: '#F5D9D9', color: '#8B2E2E', border: '1px solid #E5C5C5', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
              {error}
            </div>
          )}
          {[
            { label: 'Full Name', key: 'name', type: 'text', placeholder: 'Arun Kumar' },
            { label: 'Email Address', key: 'email', type: 'email', placeholder: 'arun@example.com' },
            { label: 'Password', key: 'password', type: 'password', placeholder: 'Minimum 8 characters' },
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
            <select
              value={form.role}
              onChange={e => setForm(f => ({ ...f, role: e.target.value as any }))}
              style={{ width: '100%', padding: '8px 12px', fontSize: 13, background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
            >
              <option value="USER">USER — Research access</option>
              <option value="ADMIN">ADMIN — Administrative access</option>
            </select>
          </div>
          <div style={{ fontSize: 11, color: '#526176', padding: '8px 12px', background: '#E7EDF4', borderRadius: 6, border: '1px solid #C5D5E8' }}>
            Created by: <strong>Super Administrator</strong>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose}
              style={{ flex: 1, padding: '8px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>
              Cancel
            </button>
            <button type="submit"
              style={{ flex: 1, padding: '8px 16px', background: '#2563A8', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: 'pointer' }}>
              Create User
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ConfirmDialog({ title, message, danger, onConfirm, onClose }: { title: string; message: string; danger: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(23,37,58,0.4)' }}>
      <div className="rounded-lg w-full max-w-sm" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 8px 40px rgba(23,37,58,0.14)' }}>
        <div className="px-6 py-4" style={{ borderBottom: '1px solid #C5D5E8' }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: '#17253A' }}>{title}</h2>
        </div>
        <div className="px-6 py-4">
          <p style={{ fontSize: 13, color: '#526176', lineHeight: 1.5 }}>{message}</p>
        </div>
        <div className="px-6 pb-4 flex gap-2">
          <button onClick={onClose} style={{ flex: 1, padding: '8px 16px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 6, fontSize: 13, color: '#526176', cursor: 'pointer' }}>Cancel</button>
          <button onClick={() => { onConfirm(); onClose(); }}
            style={{ flex: 1, padding: '8px 16px', background: danger ? '#8B2E2E' : '#2563A8', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, color: '#fff', cursor: 'pointer' }}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Users() {
  const [users, setUsers] = useState<User[]>(USERS);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'All' | UserStatus>('All');
  const [showCreate, setShowCreate] = useState(false);
  const [confirm, setConfirm] = useState<{ type: 'disable' | 'delete'; user: User } | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortAsc, setSortAsc] = useState(true);

  const filtered = users
    .filter(u => filter === 'All' || u.status === filter)
    .filter(u => u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const v = (a[sortKey] || '').localeCompare(b[sortKey] || '');
      return sortAsc ? v : -v;
    });

  function handleSort(k: SortKey) {
    if (k === sortKey) setSortAsc(v => !v);
    else { setSortKey(k); setSortAsc(true); }
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return null;
    return sortAsc ? <ChevronUp size={11} /> : <ChevronDown size={11} />;
  }

  function disableUser(id: string) {
    setUsers(prev => prev.map(u => u.id === id ? { ...u, status: 'Disabled' } : u));
  }

  function deleteUser(id: string) {
    setUsers(prev => prev.filter(u => u.id !== id));
  }

  function createUser(data: Partial<User>) {
    const newUser: User = {
      id: `u${Date.now()}`,
      name: data.name || '',
      email: data.email || '',
      role: data.role || 'USER',
      status: 'Active',
      created: 'Sep 28, 2026',
      lastActive: '—',
      createdBy: 'Super Administrator',
    };
    setUsers(prev => [newUser, ...prev]);
  }

  const Th = ({ label, k }: { label: string; k?: SortKey }) => (
    <th
      className="text-left px-4 py-3 cursor-pointer select-none"
      style={{ fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}
      onClick={() => k && handleSort(k)}
    >
      <span className="flex items-center gap-1">{label} {k && <SortIcon k={k} />}</span>
    </th>
  );

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Users</h1>
          <p style={{ fontSize: 13, color: '#526176' }}>Manage Juris AI research users and access.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded"
          style={{ background: '#2563A8', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#1E5296')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#2563A8')}
        >
          <Plus size={14} /> Create User
        </button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#526176' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search users…"
            style={{ width: '100%', padding: '7px 12px 7px 32px', fontSize: 13, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, color: '#17253A', outline: 'none' }}
            onFocus={e => (e.target.style.borderColor = '#3B82D0')}
            onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
          />
        </div>
        <div className="flex gap-1" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 6, padding: 3 }}>
          {(['All', 'Active', 'Disabled'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 12,
                border: 'none',
                cursor: 'pointer',
                background: filter === f ? '#2563A8' : 'transparent',
                color: filter === f ? '#fff' : '#526176',
                fontWeight: filter === f ? 500 : 400,
              }}
            >
              {f}
            </button>
          ))}
        </div>
        <span style={{ fontSize: 12, color: '#526176' }}>{filtered.length} user{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <Th label="NAME" k="name" />
                <Th label="EMAIL" k="email" />
                <Th label="ROLE" />
                <Th label="STATUS" />
                <Th label="CREATED" k="created" />
                <Th label="LAST ACTIVE" k="lastActive" />
                <th style={{ fontSize: 11, fontWeight: 600, color: '#526176', background: '#EFF3F7', borderBottom: '1px solid #C5D5E8', padding: '12px 16px', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '48px 16px', color: '#526176', fontSize: 13 }}>
                    No users found.
                  </td>
                </tr>
              )}
              {filtered.map((user, i) => (
                <tr
                  key={user.id}
                  style={{ borderBottom: i < filtered.length - 1 ? '1px solid #E7EDF4' : 'none' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F0F4F8')}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                >
                  <td style={{ padding: '11px 16px' }}>
                    <div className="flex items-center gap-2.5">
                      <div
                        className="rounded-full flex items-center justify-center flex-shrink-0"
                        style={{ width: 28, height: 28, background: '#D9E7F5', color: '#2563A8', fontSize: 10, fontWeight: 700 }}
                      >
                        {user.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#17253A' }}>{user.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176' }}>{user.email}</td>
                  <td style={{ padding: '11px 16px' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#526176', background: '#E7EDF4', padding: '2px 6px', borderRadius: 3 }}>
                      {user.role}
                    </span>
                  </td>
                  <td style={{ padding: '11px 16px' }}><Badge status={user.status} /></td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>{user.created}</td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#526176', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap' }}>{user.lastActive}</td>
                  <td style={{ padding: '11px 16px' }}>
                    <div className="flex items-center justify-end gap-2">
                      {[
                        { Icon: Eye, title: 'View', color: '#526176' },
                        { Icon: Edit2, title: 'Edit', color: '#526176' },
                        { Icon: Ban, title: 'Disable', color: '#7A5A0F', onClick: () => user.status === 'Active' && setConfirm({ type: 'disable', user }) },
                        { Icon: Trash2, title: 'Delete', color: '#8B2E2E', onClick: () => setConfirm({ type: 'delete', user }) },
                      ].map(({ Icon, title, color, onClick }) => (
                        <button
                          key={title}
                          title={title}
                          onClick={onClick}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color, padding: 3, borderRadius: 4 }}
                          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
                          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}
                        >
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
          Showing {filtered.length} of {users.length} users
        </div>
      </div>

      {showCreate && <Modal onClose={() => setShowCreate(false)} onSave={createUser} />}

      {confirm && (
        <ConfirmDialog
          title={confirm.type === 'disable' ? 'Disable User Account' : 'Delete User'}
          message={confirm.type === 'disable'
            ? `Are you sure you want to disable ${confirm.user.name}? They will lose all access to Juris AI.`
            : `Are you sure you want to permanently delete ${confirm.user.name}? This action cannot be undone.`}
          danger={confirm.type === 'delete'}
          onConfirm={() => {
            if (confirm.type === 'disable') disableUser(confirm.user.id);
            else deleteUser(confirm.user.id);
          }}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  );
}
