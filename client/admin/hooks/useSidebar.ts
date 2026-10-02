import { useState, useEffect } from 'react';

export function useSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Read initial preference if needed
  useEffect(() => {
    const saved = localStorage.getItem('juris_admin_sidebar_collapsed');
    if (saved !== null) {
      setIsCollapsed(saved === 'true');
    }
  }, []);

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('juris_admin_sidebar_collapsed', String(next));
      return next;
    });
  };

  return { isCollapsed, setIsCollapsed, toggleSidebar };
}
