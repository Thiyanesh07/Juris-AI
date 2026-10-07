'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole, UserStatus } from '@/lib/types';
import { INITIAL_MOCK_USERS } from '@/data/users';
import { INITIAL_MOCK_ADMINS } from '@/data/administrators';
import { apiClient } from '@/lib/apiClient';

interface BackendUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserStoreContextType {
  users: User[];
  admins: User[];
  isLoading: boolean;
  addUser: (userData: Omit<User, 'id' | 'createdAt'>) => User;
  addAdmin: (adminData: Omit<User, 'id' | 'createdAt'>) => User;
  updateUser: (id: string, updates: Partial<User>) => boolean;
  toggleUserStatus: (id: string) => boolean;
  deleteUser: (id: string) => boolean;
  getUserById: (id: string) => User | undefined;
  refreshUsers: () => Promise<void>;
}

const UserStoreContext = createContext<UserStoreContextType | undefined>(undefined);

function mapRoleToFrontend(roleStr: string): UserRole {
  const u = roleStr.toUpperCase();
  if (u === 'SUPER_ADMIN') return 'SUPER_ADMIN';
  if (u === 'ADMIN') return 'ADMIN';
  return 'USER';
}

export const UserStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<User[]>(INITIAL_MOCK_USERS);
  const [admins, setAdmins] = useState<User[]>(INITIAL_MOCK_ADMINS);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const [uRes, aRes] = await Promise.all([
        apiClient.get<{ items: BackendUser[] }>('/admin/users?page_size=100').catch(() => ({ items: [] })),
        apiClient.get<{ items: BackendUser[] }>('/admin/admins?page_size=100').catch(() => ({ items: [] })),
      ]);

      if (uRes.items && uRes.items.length > 0) {
        const mappedUsers: User[] = uRes.items.map((u) => ({
          id: u.id,
          name: u.name || u.email.split('@')[0],
          email: u.email,
          role: mapRoleToFrontend(u.role),
          status: u.is_active ? 'ACTIVE' : 'INACTIVE',
          organization: 'Juris AI Legal Network',
          createdAt: u.created_at || new Date().toISOString(),
          lastActiveAt: 'Recently',
        }));
        setUsers(mappedUsers);
      }

      if (aRes.items && aRes.items.length > 0) {
        const mappedAdmins: User[] = aRes.items.map((a) => ({
          id: a.id,
          name: a.name || a.email.split('@')[0],
          email: a.email,
          role: mapRoleToFrontend(a.role),
          status: a.is_active ? 'ACTIVE' : 'INACTIVE',
          organization: 'Juris AI Operations',
          createdAt: a.created_at || new Date().toISOString(),
          lastActiveAt: 'Active Now',
          isProtected: a.role.toUpperCase() === 'SUPER_ADMIN',
        }));
        setAdmins(mappedAdmins);
      }
    } catch {
      // Fallback to local
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const getUserById = (id: string): User | undefined => {
    return users.find((u) => u.id === id) || admins.find((a) => a.id === id);
  };

  const addUser = (userData: Omit<User, 'id' | 'createdAt'>): User => {
    const newId = `usr_${Date.now().toString().slice(-6)}`;
    const newUser: User = {
      ...userData,
      id: newId,
      createdAt: new Date().toISOString(),
      lastActiveAt: 'Just now',
    };
    setUsers((prev) => [newUser, ...prev]);
    return newUser;
  };

  const addAdmin = (adminData: Omit<User, 'id' | 'createdAt'>): User => {
    const newId = `usr_admin_${Date.now().toString().slice(-6)}`;
    const newAdmin: User = {
      ...adminData,
      role: 'ADMIN',
      id: newId,
      createdAt: new Date().toISOString(),
      lastActiveAt: 'Just now',
    };

    // Attempt backend provision
    apiClient.post('/admin/admins', {
      email: adminData.email,
      name: adminData.name,
      password: 'TemporaryPassword123!',
      role: 'admin',
    }).catch(() => {});

    setAdmins((prev) => [newAdmin, ...prev]);
    return newAdmin;
  };

  const updateUser = (id: string, updates: Partial<User>): boolean => {
    const existing = getUserById(id);
    if (!existing) return false;

    if (existing.isProtected) {
      if (updates.role && updates.role !== 'SUPER_ADMIN') return false;
      if (updates.status && updates.status !== 'ACTIVE') return false;
    }

    // Call backend API if valid UUID
    if (id.includes('-')) {
      apiClient.put(`/admin/users/${id}`, {
        name: updates.name,
        role: updates.role ? updates.role.toLowerCase() : undefined,
        is_active: updates.status ? updates.status === 'ACTIVE' : undefined,
      }).catch(() => {});
    }

    if (existing.role === 'SUPER_ADMIN' || admins.some((a) => a.id === id)) {
      setAdmins((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)));
    } else {
      setUsers((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)));
    }
    return true;
  };

  const toggleUserStatus = (id: string): boolean => {
    const target = getUserById(id);
    if (!target || target.isProtected) return false;

    const nextStatus: UserStatus = target.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    return updateUser(id, { status: nextStatus });
  };

  const deleteUser = (id: string): boolean => {
    const target = getUserById(id);
    if (!target || target.isProtected || target.role === 'SUPER_ADMIN') return false;

    setUsers((prev) => prev.filter((u) => u.id !== id));
    setAdmins((prev) => prev.filter((a) => a.id !== id));
    return true;
  };

  return (
    <UserStoreContext.Provider
      value={{
        users,
        admins,
        isLoading,
        addUser,
        addAdmin,
        updateUser,
        toggleUserStatus,
        deleteUser,
        getUserById,
        refreshUsers: fetchUsers,
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

