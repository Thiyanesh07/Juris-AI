'use client';

import React, { createContext, useContext, useState } from 'react';
import { User, UserRole, UserStatus } from '@/lib/types';
import { INITIAL_MOCK_USERS } from '@/data/users';
import { INITIAL_MOCK_ADMINS } from '@/data/administrators';

interface UserStoreContextType {
  users: User[];
  admins: User[];
  addUser: (userData: Omit<User, 'id' | 'createdAt'>) => User;
  addAdmin: (adminData: Omit<User, 'id' | 'createdAt'>) => User;
  updateUser: (id: string, updates: Partial<User>) => boolean;
  toggleUserStatus: (id: string) => boolean;
  deleteUser: (id: string) => boolean;
  getUserById: (id: string) => User | undefined;
}

const UserStoreContext = createContext<UserStoreContextType | undefined>(undefined);

export const UserStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [users, setUsers] = useState<User[]>(INITIAL_MOCK_USERS);
  const [admins, setAdmins] = useState<User[]>(INITIAL_MOCK_ADMINS);

  const getUserById = (id: string): User | undefined => {
    return (
      users.find((u) => u.id === id) ||
      admins.find((a) => a.id === id)
    );
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
      role: 'ADMIN', // SUPER_ADMIN cannot be assigned through ordinary UI
      id: newId,
      createdAt: new Date().toISOString(),
      lastActiveAt: 'Just now',
    };
    setAdmins((prev) => [newAdmin, ...prev]);
    return newAdmin;
  };

  const updateUser = (id: string, updates: Partial<User>): boolean => {
    const existing = getUserById(id);
    if (!existing) return false;

    // Super Admin bootstrap account cannot have its role modified or protected flag removed
    if (existing.isProtected) {
      if (updates.role && updates.role !== 'SUPER_ADMIN') {
        return false;
      }
      if (updates.status && updates.status !== 'ACTIVE') {
        return false;
      }
    }

    if (existing.role === 'SUPER_ADMIN' || admins.some((a) => a.id === id)) {
      setAdmins((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
    } else {
      setUsers((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
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
    if (!target) return false;

    // Protected Super Admin cannot be deleted
    if (target.isProtected || target.role === 'SUPER_ADMIN') {
      return false;
    }

    setUsers((prev) => prev.filter((u) => u.id !== id));
    setAdmins((prev) => prev.filter((a) => a.id !== id));
    return true;
  };

  return (
    <UserStoreContext.Provider
      value={{
        users,
        admins,
        addUser,
        addAdmin,
        updateUser,
        toggleUserStatus,
        deleteUser,
        getUserById,
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
