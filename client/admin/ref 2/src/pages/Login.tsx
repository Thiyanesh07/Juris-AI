import { useState } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

interface LoginProps {
  onLogin: () => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState('superadmin@juris.ai');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!email || !password) { setError('Email and password are required.'); return; }
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(); }, 900);
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: '#E7EDF4' }}
    >
      {/* Top bar */}
      <div
        className="flex items-center px-8 py-0"
        style={{ height: 56, borderBottom: '1px solid #C5D5E8', background: '#EFF3F7' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="flex items-center justify-center rounded"
            style={{ width: 28, height: 28, background: '#2563A8' }}
          >
            <span style={{ color: '#fff', fontSize: 12, fontWeight: 700, fontFamily: 'DM Serif Display, serif' }}>J</span>
          </div>
          <div>
            <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 15, color: '#183B5B', lineHeight: 1 }}>
              Juris AI
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#526176', letterSpacing: '0.08em', lineHeight: 1.2, marginTop: 2 }}>
              ADMIN CONSOLE
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div style={{ width: '100%', maxWidth: 400 }}>
          {/* Card */}
          <div
            className="rounded-lg overflow-hidden"
            style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', boxShadow: '0 2px 16px rgba(23,37,58,0.06)' }}
          >
            {/* Card header */}
            <div
              className="px-8 pt-8 pb-6"
              style={{ borderBottom: '1px solid #C5D5E8' }}
            >
              <div
                className="flex items-center justify-center w-10 h-10 rounded-full mb-4"
                style={{ background: '#D9E7F5' }}
              >
                <Lock size={16} style={{ color: '#2563A8' }} />
              </div>
              <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 22, color: '#183B5B', lineHeight: 1.1, marginBottom: 6 }}>
                Administrator Sign In
              </h1>
              <p style={{ fontSize: 13, color: '#526176', lineHeight: 1.5 }}>
                Access is restricted to authorized Juris AI administrators.
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="px-8 py-6 space-y-4">
              {error && (
                <div
                  className="px-3 py-2 rounded text-sm"
                  style={{ background: '#F5D9D9', color: '#8B2E2E', border: '1px solid #E5C5C5', fontSize: 13 }}
                >
                  {error}
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 6 }}>
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@juris.ai"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: 13,
                    background: '#EFF3F7',
                    border: '1px solid #C5D5E8',
                    borderRadius: 6,
                    color: '#17253A',
                    outline: 'none',
                  }}
                  onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                  onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#17253A', marginBottom: 6 }}>
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    style={{
                      width: '100%',
                      padding: '8px 40px 8px 12px',
                      fontSize: 13,
                      background: '#EFF3F7',
                      border: '1px solid #C5D5E8',
                      borderRadius: 6,
                      color: '#17253A',
                      outline: 'none',
                    }}
                    onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                    onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#526176', padding: 2 }}
                  >
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '9px 16px',
                  background: loading ? '#8EB4DA' : '#2563A8',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                  marginTop: 4,
                }}
                onMouseEnter={e => { if (!loading) (e.currentTarget as HTMLElement).style.background = '#1E5296'; }}
                onMouseLeave={e => { if (!loading) (e.currentTarget as HTMLElement).style.background = '#2563A8'; }}
              >
                {loading ? 'Authenticating…' : 'Sign In'}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#3B82D0' }}
                >
                  Forgot password?
                </button>
              </div>
            </form>
          </div>

          {/* Prototype notice */}
          <div
            className="mt-4 px-4 py-2 rounded text-center"
            style={{ background: '#FBF3D4', border: '1px solid #E8D98A', fontSize: 11, color: '#7A5A0F' }}
          >
            <strong>Prototype</strong> — Enter any password to continue. No real authentication.
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 24px', borderTop: '1px solid #C5D5E8', background: '#EFF3F7', textAlign: 'center' }}>
        <span style={{ fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>
          Authorized access only. Juris AI Admin Console v2.4.1
        </span>
      </div>
    </div>
  );
}
