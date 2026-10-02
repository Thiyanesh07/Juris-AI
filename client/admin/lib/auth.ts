/**
 * JURIS AI — FRONTEND RBAC HELPER FOUNDATION
 * Role-Based Access Control definitions & permission checkers
 */

import { UserRole, User } from './types';

export const ROLE_HIERARCHY: Record<UserRole, number> = {
  SUPER_ADMIN: 3,
  ADMIN: 2,
  USER: 1,
};

/**
 * Returns true if the user's role has equal or higher privilege than requiredRole
 */
export function hasRole(currentRole: UserRole, requiredRole: UserRole): boolean {
  return (ROLE_HIERARCHY[currentRole] ?? 0) >= (ROLE_HIERARCHY[requiredRole] ?? 0);
}

export function isSuperAdmin(role: UserRole): boolean {
  return role === 'SUPER_ADMIN';
}

export function isAdmin(role: UserRole): boolean {
  return role === 'ADMIN' || role === 'SUPER_ADMIN';
}

export function canManageAdmins(actorRole: UserRole): boolean {
  return isSuperAdmin(actorRole);
}

export function canManageUsers(actorRole: UserRole): boolean {
  return isAdmin(actorRole);
}

export function canAccessAudit(actorRole: UserRole): boolean {
  return isAdmin(actorRole);
}

export function canModifySystemSettings(actorRole: UserRole): boolean {
  return isSuperAdmin(actorRole);
}

/**
 * Placeholder current session user for development / UI layout rendering.
 * Real backend authorization will replace this fixture in future phases.
 */
export const MOCK_ADMIN_USER: User = {
  id: 'usr_admin_001',
  email: 'admin@juris.ai',
  name: 'System Administrator',
  role: 'SUPER_ADMIN',
  status: 'ACTIVE',
  organization: 'Juris AI Global',
  createdAt: '2026-01-01T00:00:00Z',
  avatarUrl: undefined,
};
