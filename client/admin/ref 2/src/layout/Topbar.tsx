import { useState } from 'react';
import { ChevronDown, User, Lock, LogOut, Bell } from 'lucide-react';

interface TopbarProps {
  onSignOut: () => void;
}

export default function Topbar({ onSignOut }: TopbarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <header
      className="flex items-center justify-between px-5"
      style={{
        height: 56,
        background: '#EFF3F7',
        borderBottom: '1px solid #C5D5E8',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
      }}
    >
      {/* left spacer — brand is in sidebar */}
      <div style={{ width: 232 }} />

      {/* Right controls */}
      <div className="flex items-center gap-3">
        {/* Status pill */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
          style={{ background: '#D0EDDB', fontSize: 11 }}
        >
          <span
            className="rounded-full"
            style={{ width: 6, height: 6, background: '#1E6B45', display: 'inline-block', flexShrink: 0 }}
          />
          <span style={{ color: '#1E6B45', fontWeight: 500, fontFamily: 'JetBrains Mono, monospace' }}>
            All Systems Normal
          </span>
        </div>

        {/* Bell */}
        <button
          className="flex items-center justify-center rounded"
          style={{ width: 32, height: 32, background: 'none', border: 'none', cursor: 'pointer', color: '#526176', position: 'relative' }}
        >
          <Bell size={15} />
          <span
            className="absolute top-1 right-1 rounded-full"
            style={{ width: 6, height: 6, background: '#2563A8' }}
          />
        </button>

        {/* Profile */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(v => !v)}
            className="flex items-center gap-2.5 rounded px-2 py-1.5 transition-colors"
            style={{
              background: dropdownOpen ? '#D9E7F5' : 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <div
              className="flex items-center justify-center rounded-full"
              style={{ width: 30, height: 30, background: '#2563A8', color: '#fff', fontSize: 12, fontWeight: 600 }}
            >
              SA
            </div>
            <div className="text-left hidden sm:block">
              <div style={{ fontSize: 12, fontWeight: 500, color: '#17253A', lineHeight: 1.2 }}>Super Administrator</div>
              <div style={{ fontSize: 10, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>SUPER ADMIN</div>
            </div>
            <ChevronDown size={13} style={{ color: '#526176' }} />
          </button>

          {dropdownOpen && (
            <>
              <div
                className="fixed inset-0"
                style={{ zIndex: 49 }}
                onClick={() => setDropdownOpen(false)}
              />
              <div
                className="absolute right-0 top-full mt-1 rounded overflow-hidden"
                style={{
                  zIndex: 50,
                  background: '#F5F7FA',
                  border: '1px solid #C5D5E8',
                  minWidth: 180,
                  boxShadow: '0 4px 16px rgba(23,37,58,0.08)',
                }}
              >
                <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid #C5D5E8' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#17253A' }}>Super Administrator</div>
                  <div style={{ fontSize: 11, color: '#526176' }}>superadmin@juris.ai</div>
                </div>
                {[
                  { label: 'Profile', Icon: User },
                  { label: 'Security', Icon: Lock },
                ].map(({ label, Icon }) => (
                  <button
                    key={label}
                    className="w-full flex items-center gap-2.5 px-3 py-2 transition-colors"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#17253A', textAlign: 'left' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}
                  >
                    <Icon size={13} style={{ color: '#526176' }} />
                    {label}
                  </button>
                ))}
                <div style={{ borderTop: '1px solid #C5D5E8' }}>
                  <button
                    onClick={() => { setDropdownOpen(false); onSignOut(); }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 transition-colors"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#8B2E2E', textAlign: 'left' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#F5D9D9')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}
                  >
                    <LogOut size={13} />
                    Sign Out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
