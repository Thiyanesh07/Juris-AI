import { useState } from 'react';
import Sidebar, { Page } from './layout/Sidebar';
import Topbar from './layout/Topbar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Admins from './pages/Admins';
import Documents from './pages/Documents';
import Ingestion from './pages/Ingestion';
import KnowledgeGraph from './pages/KnowledgeGraph';
import Validation from './pages/Validation';
import Audit from './pages/Audit';
import Settings from './pages/Settings';

function PageContent({ page }: { page: Page }) {
  switch (page) {
    case 'dashboard':     return <Dashboard />;
    case 'users':         return <Users />;
    case 'admins':        return <Admins />;
    case 'documents':     return <Documents />;
    case 'ingestion':     return <Ingestion />;
    case 'knowledge-graph': return <KnowledgeGraph />;
    case 'validation':    return <Validation />;
    case 'audit':         return <Audit />;
    case 'settings':      return <Settings />;
    default:              return <Dashboard />;
  }
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [page, setPage] = useState<Page>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />;
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#E7EDF4' }}>
      {/* Sidebar — full height, below topbar */}
      <div style={{ paddingTop: 56, display: 'flex', flexDirection: 'column', height: '100vh', flexShrink: 0, zIndex: 40 }}>
        <Sidebar
          currentPage={page}
          onNavigate={setPage}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(v => !v)}
        />
      </div>

      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, height: '100vh', overflow: 'hidden' }}>
        {/* Fixed topbar */}
        <Topbar onSignOut={() => setLoggedIn(false)} />

        {/* Scrollable content */}
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            paddingTop: 56,
            background: '#E7EDF4',
          }}
        >
          <div style={{ maxWidth: 1400, margin: '0 auto', padding: '28px 28px 48px' }}>
            <PageContent page={page} />
          </div>
        </main>
      </div>
    </div>
  );
}
