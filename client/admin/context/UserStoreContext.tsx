'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole, UserStatus } from '@/lib/types';
import { apiClient } from '@/lib/apiClient';
import { BackendUser, PaginatedUsersResponse } from '@/lib/apiTypes';

export function mapRoleToFrontend(roleStr: string): UserRole {
  const u = (roleStr || '').toUpperCase();
  if (u === 'SUPER_ADMIN') return 'SUPER_ADMIN';
  if (u === 'ADMIN') return 'ADMIN';
  return 'USER';
}

export function mapBackendUser(u: BackendUser): User {
  const role = mapRoleToFrontend(u.role);
  return {
    id: u.id,
    name: u.name || u.email.split('@')[0],
    email: u.email,
    role: role,
    status: u.is_active ? 'ACTIVE' : 'INACTIVE',
    organization: role === 'USER' ? 'Juris AI Legal Network' : 'Juris AI Operations',
    createdAt: u.created_at || new Date().toISOString(),
    lastActiveAt: u.last_login_at || 'Recently',
    isProtected: role === 'SUPER_ADMIN',
  };
}

export interface UserFetchParams {
  search?: string;
  role?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

export interface UserStoreContextType {
  users: User[];
  admins: User[];
  isLoading: boolean;
  error: string | null;
  usersTotal: number;
  adminsTotal: number;
  fetchUsers: (params?: UserFetchParams) => Promise<void>;
  fetchAdmins: (params?: { page?: number; page_size?: number }) => Promise<void>;
  refreshUsers: () => Promise<void>;
  getUserById: (id: string) => User | undefined;
  fetchUserById: (id: string) => Promise<User | null>;
  createUser: (data: { email: string; name?: string | null; password?: string | null }) => Promise<User>;
  createAdmin: (data: { email: string; name: string; password: string; role?: 'admin' | 'super_admin' }) => Promise<User>;
  updateUser: (
    id: string,
    updates: { name?: string; role?: string; is_active?: boolean; status?: UserStatus; organization?: string }
  ) => Promise<User>;
  toggleUserStatus: (id: string) => Promise<User>;
  deleteUser: (id: string) => Promise<User>;
  addUser: (userData: { email: string; name?: string; password?: string }) => Promise<User>;
  addAdmin: (adminData: { email: string; name: string; password?: string; role?: 'admin' | 'super_admin' }) => Promise<User>;
}

const UserStoreContext = createContext<UserStoreContextType | undefined>(undefined);

export const UserStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [admins, setAdmins] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [usersTotal, setUsersTotal] = useState<number>(0);
  const [adminsTotal, setAdminsTotal] = useState<number>(0);

  const fetchUsers = useCallback(async (params?: UserFetchParams) => {
    setIsLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('page', String(params?.page || 1));
      q.set('page_size', String(params?.page_size || 100));
      if (params?.search && params.search.trim()) {
        q.set('search', params.search.trim());
      }
      if (params?.role && params.role !== 'ALL') {
        q.set('role', params.role.toLowerCase());
      }
      if (params?.is_active !== undefined) {
        q.set('is_active', String(params.is_active));
      }

      const res = await apiClient.get<PaginatedUsersResponse>(`/admin/users?${q.toString()}`);
      const items = res?.items || [];
      const mapped = items.map(mapBackendUser);
      setUsers(mapped);
      setUsersTotal(res?.total ?? mapped.length);
    } catch (err: any) {
      const msg = err?.message || 'Failed to fetch users from backend.';
      setError(msg);
      setUsers([]);
      setUsersTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAdmins = useCallback(async (params?: { page?: number; page_size?: number }) => {
    setIsLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set('page', String(params?.page || 1));
      q.set('page_size', String(params?.page_size || 100));

      const res = await apiClient.get<PaginatedUsersResponse>(`/admin/admins?${q.toString()}`);
      const items = res?.items || [];
      const mapped = items.map(mapBackendUser);
      setAdmins(mapped);
      setAdminsTotal(res?.total ?? mapped.length);
    } catch (err: any) {
      const msg = err?.message || 'Failed to fetch administrators from backend.';
      setError(msg);
      setAdmins([]);
      setAdminsTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshUsers = useCallback(async () => {
    await Promise.all([fetchUsers(), fetchAdmins()]);
  }, [fetchUsers, fetchAdmins]);

  useEffect(() => {
    refreshUsers();
  }, [refreshUsers]);

  const getUserById = useCallback(
    (id: string): User | undefined => {
      return users.find((u) => u.id === id) || admins.find((a) => a.id === id);
    },
    [users, admins]
  );

  const fetchUserById = useCallback(
    async (id: string): Promise<User | null> => {
      const existing = getUserById(id);
      if (existing) return existing;

      try {
        const res = await apiClient.get<BackendUser>(`/admin/users/${id}`);
        if (!res || !res.id) return null;
        const mapped = mapBackendUser(res);
        if (mapped.role === 'ADMIN' || mapped.role === 'SUPER_ADMIN') {
          setAdmins((prev) => [mapped, ...prev.filter((a) => a.id !== id)]);
        } else {
          setUsers((prev) => [mapped, ...prev.filter((u) => u.id !== id)]);
        }
        return mapped;
      } catch {
        return null;
      }
    },
    [getUserById]
  );

  const createUser = async (data: { email: string; name?: string | null; password?: string | null }): Promise<User> => {
    const payload = {
      email: data.email.trim().toLowerCase(),
      name: data.name?.trim() || null,
      password: data.password?.trim() || null,
    };

    const res = await apiClient.post<BackendUser>('/admin/users', payload);
    const mapped = mapBackendUser(res);
    setUsers((prev) => [mapped, ...prev.filter((u) => u.id !== mapped.id)]);
    setUsersTotal((prev) => prev + 1);
    return mapped;
  };

  const createAdmin = async (data: {
    email: string;
    name: string;
    password: string;
    role?: 'admin' | 'super_admin';
  }): Promise<User> => {
    const payload = {
      email: data.email.trim().toLowerCase(),
      name: data.name.trim(),
      password: data.password,
      role: data.role || 'admin',
    };

    const res = await apiClient.post<BackendUser>('/admin/admins', payload);
    const mapped = mapBackendUser(res);
    setAdmins((prev) => [mapped, ...prev.filter((a) => a.id !== mapped.id)]);
    setAdminsTotal((prev) => prev + 1);
    return mapped;
  };

  const updateUser = async (
    id: string,
    updates: { name?: string; role?: string; is_active?: boolean; status?: UserStatus; organization?: string }
  ): Promise<User> => {
    const existing = getUserById(id);
    if (existing?.isProtected) {
      if (updates.role && updates.role.toUpperCase() !== 'SUPER_ADMIN') {
        throw new Error('Cannot demote or change the role of a Super Administrator account.');
      }
      if (updates.is_active === false || updates.status === 'INACTIVE') {
        throw new Error('Super Administrator accounts cannot be disabled.');
      }
    }

    const payload: { name?: string; role?: string; is_active?: boolean } = {};
    if (updates.name !== undefined) payload.name = updates.name.trim();
    if (updates.role !== undefined) payload.role = updates.role.toLowerCase();
    if (updates.is_active !== undefined) {
      payload.is_active = updates.is_active;
    } else if (updates.status !== undefined) {
      payload.is_active = updates.status === 'ACTIVE';
    }

    const res = await apiClient.put<BackendUser>(`/admin/users/${id}`, payload);
    const mapped = mapBackendUser(res);
    if (updates.organization) {
      mapped.organization = updates.organization;
    }

    setUsers((prev) => prev.map((u) => (u.id === id ? mapped : u)));
    setAdmins((prev) => prev.map((a) => (a.id === id ? mapped : a)));
    return mapped;
  };

  const toggleUserStatus = async (id: string): Promise<User> => {
    const target = getUserById(id);
    if (!target) {
      throw new Error('User not found.');
    }
    if (target.isProtected) {
      throw new Error('Super Administrator accounts cannot be disabled.');
    }

    const nextActive = target.status !== 'ACTIVE';
    return updateUser(id, {
      is_active: nextActive,
      status: nextActive ? 'ACTIVE' : 'INACTIVE',
    });
  };

  const deleteUser = async (id: string): Promise<User> => {
    const target = getUserById(id);
    if (target?.isProtected) {
      throw new Error('Super Administrator accounts cannot be deactivated.');
    }

    const res = await apiClient.delete<BackendUser>(`/admin/users/${id}`);
    const mapped = mapBackendUser(res);

    setUsers((prev) => prev.map((u) => (u.id === id ? mapped : u)));
    setAdmins((prev) => prev.map((a) => (a.id === id ? mapped : a)));
    return mapped;
  };

  return (
    <UserStoreContext.Provider
      value={{
        users,
        admins,
        isLoading,
        error,
        usersTotal,
        adminsTotal,
        fetchUsers,
        fetchAdmins,
        refreshUsers,
        getUserById,
        fetchUserById,
        createUser,
        createAdmin,
        updateUser,
        toggleUserStatus,
        deleteUser,
        addUser: createUser,
        addAdmin: (data) =>
          createAdmin({
            email: data.email,
            name: data.name,
            password: data.password || 'TemporaryPassword123!',
            role: data.role,
          }),
      }}
    >
      {children}
    </UserStoreContext.Provider>
  );
};

export const useUserStore = () => {
  const context = useContext(UserStoreContext);
  if (!context) {
    throw new Error('useUserStore must be used within a UserStoreProvider');
  }
  return context;
};
