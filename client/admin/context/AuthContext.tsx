'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { AuthUser, fetchCurrentUser, signOut, isAdminRole } from '@/lib/authClient';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  /** Call after any action that might change auth state (e.g., after redirect back from Google) */
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const me = await fetchCurrentUser();
      setUser(me);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await signOut();
    setUser(null);
    window.location.href = '/admin/login';
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const AuthContextProvider = AuthProvider;

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/**
 * Hook that asserts admin access.
 * Redirects to /admin/login if not authenticated or not an admin role.
 * Returns null while loading.
 */
export function useRequireAdmin(): AuthUser | null {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && (!user || !isAdminRole(user))) {
      window.location.href = '/admin/login';
    }
  }, [user, loading]);

  if (loading) return null;
  if (!user || !isAdminRole(user)) return null;
  return user;
}
