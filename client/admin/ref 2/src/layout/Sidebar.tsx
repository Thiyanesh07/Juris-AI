import {
  LayoutDashboard, Users, Shield, FileText, GitBranch,
  Network, CheckSquare, ScrollText, Settings, ChevronRight,
} from 'lucide-react';

export type Page =
  | 'dashboard' | 'users' | 'admins' | 'documents' | 'ingestion'
  | 'knowledge-graph' | 'validation' | 'audit' | 'settings';

interface SidebarProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS: { id: Page; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { id: 'users', label: 'Users', Icon: Users },
  { id: 'admins', label: 'Administrators', Icon: Shield },
  { id: 'documents', label: 'Documents', Icon: FileText },
  { id: 'ingestion', label: 'Ingestion', Icon: GitBranch },
  { id: 'knowledge-graph', label: 'Knowledge Graph', Icon: Network },
  { id: 'validation', label: 'Validation', Icon: CheckSquare },
  { id: 'audit', label: 'Audit Logs', Icon: ScrollText },
  { id: 'settings', label: 'Settings', Icon: Settings },
];

export default function Sidebar({ currentPage, onNavigate, collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className="flex flex-col h-full transition-all duration-200"
      style={{
        width: collapsed ? 56 : 232,
        background: '#EFF3F7',
        borderRight: '1px solid #C5D5E8',
        flexShrink: 0,
      }}
    >
      {/* Brand */}
      <div
        className="flex items-center gap-2.5 px-4 py-0"
        style={{ height: 56, borderBottom: '1px solid #C5D5E8', flexShrink: 0 }}
      >
        <div
          className="flex items-center justify-center rounded"
          style={{ width: 28, height: 28, background: '#2563A8', flexShrink: 0 }}
        >
          <span style={{ color: '#fff', fontSize: 12, fontWeight: 700, fontFamily: 'DM Serif Display, serif', letterSpacing: '-0.5px' }}>J</span>
        </div>
        {!collapsed && (
          <div>
            <div style={{ fontFamily: 'DM Serif Display, serif', fontSize: 15, color: '#183B5B', lineHeight: 1 }}>
              Juris AI
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#526176', letterSpacing: '0.08em', lineHeight: 1.2, marginTop: 2 }}>
              ADMIN CONSOLE
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {NAV_ITEMS.map(({ id, label, Icon }) => {
          const active = currentPage === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              title={collapsed ? label : undefined}
              className="w-full flex items-center gap-3 text-left transition-colors"
              style={{
                padding: collapsed ? '8px 16px' : '8px 16px',
                marginBottom: 1,
                background: active ? '#D9E7F5' : 'transparent',
                color: active ? '#2563A8' : '#526176',
                borderLeft: active ? '2px solid #2563A8' : '2px solid transparent',
                fontSize: 13,
                fontWeight: active ? 500 : 400,
                cursor: 'pointer',
                border: 'none',
                borderRadius: 0,
                justifyContent: collapsed ? 'center' : 'flex-start',
              }}
              onMouseEnter={e => {
                if (!active) {
                  (e.currentTarget as HTMLButtonElement).style.background = '#E7EDF4';
                  (e.currentTarget as HTMLButtonElement).style.color = '#17253A';
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.color = '#526176';
                }
              }}
            >
              <Icon size={15} className="flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div style={{ padding: '12px 14px', borderTop: '1px solid #C5D5E8' }}>
        <button
          onClick={onToggle}
          className="flex items-center justify-center w-full transition-colors"
          style={{ color: '#526176', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
        >
          <ChevronRight
            size={14}
            style={{ transform: collapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition: 'transform 0.2s' }}
          />
        </button>
      </div>
    </aside>
  );
}
