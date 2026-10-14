import { useSyncExternalStore, useCallback } from 'react';

const STORAGE_KEY = 'juris_admin_sidebar_collapsed';

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback);
  window.addEventListener('local-sidebar-toggle', callback);
  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener('local-sidebar-toggle', callback);
  };
}

function getSnapshot(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

function getServerSnapshot(): boolean {
  return false;
}

export function useSidebar() {
  const isCollapsed = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggleSidebar = useCallback(() => {
    const next = !(localStorage.getItem(STORAGE_KEY) === 'true');
    localStorage.setItem(STORAGE_KEY, String(next));
    window.dispatchEvent(new Event('local-sidebar-toggle'));
  }, []);

  const setIsCollapsed = useCallback((value: boolean | ((prev: boolean) => boolean)) => {
    const current = localStorage.getItem(STORAGE_KEY) === 'true';
    const next = typeof value === 'function' ? value(current) : value;
    localStorage.setItem(STORAGE_KEY, String(next));
    window.dispatchEvent(new Event('local-sidebar-toggle'));
  }, []);

  return { isCollapsed, setIsCollapsed, toggleSidebar };
}
