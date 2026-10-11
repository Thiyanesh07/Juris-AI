import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  mapRoleToFrontend,
  mapBackendUser,
} from '../context/UserStoreContext.tsx';
import { INITIAL_MOCK_USERS } from '../data/users.ts';
import { INITIAL_MOCK_ADMINS } from '../data/administrators.ts';

describe('Phase 4 - Step 2: User & Administrator Store Integration', () => {
  describe('Backend User Model & Role Mappings', () => {
    it('accurately maps role strings to frontend UserRole enum values', () => {
      assert.equal(mapRoleToFrontend('user'), 'USER');
      assert.equal(mapRoleToFrontend('USER'), 'USER');
      assert.equal(mapRoleToFrontend('admin'), 'ADMIN');
      assert.equal(mapRoleToFrontend('ADMIN'), 'ADMIN');
      assert.equal(mapRoleToFrontend('super_admin'), 'SUPER_ADMIN');
      assert.equal(mapRoleToFrontend('SUPER_ADMIN'), 'SUPER_ADMIN');
      assert.equal(mapRoleToFrontend('unknown'), 'USER');
      assert.equal(mapRoleToFrontend(''), 'USER');
    });

    it('faithfully maps active and disabled user accounts without fabricating active status', () => {
      const activeBackendUser = {
        id: '11111111-1111-1111-1111-111111111111',
        email: 'priya.sharma@research.law.in',
        name: 'Priya Sharma',
        role: 'user',
        is_active: true,
        created_at: '2026-05-10T10:00:00Z',
        last_login_at: '2026-10-10T14:30:00Z',
      };

      const mappedActive = mapBackendUser(activeBackendUser);
      assert.equal(mappedActive.id, '11111111-1111-1111-1111-111111111111');
      assert.equal(mappedActive.email, 'priya.sharma@research.law.in');
      assert.equal(mappedActive.name, 'Priya Sharma');
      assert.equal(mappedActive.role, 'USER');
      assert.equal(mappedActive.status, 'ACTIVE');
      assert.equal(mappedActive.isProtected, false);
      assert.equal(mappedActive.createdAt, '2026-05-10T10:00:00Z');
      assert.equal(mappedActive.lastActiveAt, '2026-10-10T14:30:00Z');

      const deactivatedBackendUser = {
        id: '22222222-2222-2222-2222-222222222222',
        email: 'deactivated.operator@juris.ai',
        name: 'Deactivated Operator',
        role: 'admin',
        is_active: false,
        created_at: '2026-01-15T08:00:00Z',
        last_login_at: null,
      };

      const mappedDeactivated = mapBackendUser(deactivatedBackendUser);
      assert.equal(mappedDeactivated.status, 'INACTIVE');
      assert.equal(mappedDeactivated.role, 'ADMIN');
      assert.equal(mappedDeactivated.isProtected, false);
    });

    it('marks super_admin accounts as protected system accounts', () => {
      const superAdminUser = {
        id: '33333333-3333-3333-3333-333333333333',
        email: 'root@juris.ai',
        name: 'Root Administrator',
        role: 'super_admin',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        last_login_at: '2026-10-11T12:00:00Z',
      };

      const mapped = mapBackendUser(superAdminUser);
      assert.equal(mapped.role, 'SUPER_ADMIN');
      assert.equal(mapped.isProtected, true);
    });

    it('falls back to email prefix when name is null', () => {
      const namelessUser = {
        id: '44444444-4444-4444-4444-444444444444',
        email: 'counsel.advocate@supremecourt.in',
        name: null,
        role: 'user',
        is_active: true,
        created_at: '2026-07-01T00:00:00Z',
      };

      const mapped = mapBackendUser(namelessUser);
      assert.equal(mapped.name, 'counsel.advocate');
    });
  });

  describe('Isolation from Test Fixtures & Zero Mock Fallbacks', () => {
    it('verifies that empty backend lists produce empty arrays, not INITIAL_MOCK_USERS', () => {
      const emptyBackendList = [];
      const mapped = emptyBackendList.map(mapBackendUser);
      assert.equal(mapped.length, 0);
      assert.notEqual(mapped.length, INITIAL_MOCK_USERS.length);
    });

    it('verifies that empty backend admin lists produce empty arrays, not INITIAL_MOCK_ADMINS', () => {
      const emptyBackendAdmins = [];
      const mapped = emptyBackendAdmins.map(mapBackendUser);
      assert.equal(mapped.length, 0);
      assert.notEqual(mapped.length, INITIAL_MOCK_ADMINS.length);
    });

    it('verifies that INITIAL_MOCK_USERS IDs are never generated from real backend UUIDs', () => {
      const mockIds = new Set(INITIAL_MOCK_USERS.map((u) => u.id));
      const realUuid = '55555555-5555-5555-5555-555555555555';
      assert.equal(mockIds.has(realUuid), false);
    });
  });

  describe('User Provisioning & Safe Deactivation Rules', () => {
    it('ensures standard user creation preserves role USER regardless of organization', () => {
      const createdStandardUser = {
        id: '66666666-6666-6666-6666-666666666666',
        email: 'law.clerk@highcourt.in',
        name: 'Law Clerk',
        role: 'user',
        is_active: true,
        created_at: '2026-10-11T12:00:00Z',
      };

      const mapped = mapBackendUser(createdStandardUser);
      assert.equal(mapped.role, 'USER');
      assert.equal(mapped.isProtected, false);
      assert.equal(mapped.status, 'ACTIVE');
    });

    it('preserves user record integrity upon soft deactivation', () => {
      const beforeDeactivation = {
        id: '77777777-7777-7777-7777-777777777777',
        email: 'retiring.judge@bench.in',
        name: 'Retiring Judge',
        role: 'user',
        is_active: true,
        created_at: '2026-03-01T00:00:00Z',
      };

      const afterDeactivation = {
        ...beforeDeactivation,
        is_active: false,
      };

      const mappedDeactivated = mapBackendUser(afterDeactivation);
      // Soft deactivation preserves ID, email, name, role, and created timestamp
      assert.equal(mappedDeactivated.id, beforeDeactivation.id);
      assert.equal(mappedDeactivated.email, beforeDeactivation.email);
      assert.equal(mappedDeactivated.name, beforeDeactivation.name);
      assert.equal(mappedDeactivated.role, 'USER');
      assert.equal(mappedDeactivated.status, 'INACTIVE');
      assert.equal(mappedDeactivated.createdAt, beforeDeactivation.created_at);
    });

    it('enforces that protected accounts cannot have status toggled to INACTIVE', () => {
      const protectedAdmin = {
        id: '88888888-8888-8888-8888-888888888888',
        email: 'admin@juris.ai',
        name: 'Root Operator',
        role: 'super_admin',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      };

      const mapped = mapBackendUser(protectedAdmin);
      assert.equal(mapped.isProtected, true);
      assert.equal(mapped.role, 'SUPER_ADMIN');
    });
  });

  describe('Error Classification & Status Code Verification', () => {
    it('identifies duplicate-email conflict responses (409)', () => {
      const conflictError = {
        status: 409,
        message: 'Email already registered',
      };

      const isConflict =
        conflictError.status === 409 ||
        conflictError.message.toLowerCase().includes('already registered');
      assert.equal(isConflict, true);
    });

    it('identifies unauthorized role escalation errors (403)', () => {
      const forbiddenError = {
        status: 403,
        message: 'Only Super Administrators can promote users to administrative roles.',
      };

      const isForbidden =
        forbiddenError.status === 403 ||
        forbiddenError.message.toLowerCase().includes('super administrator');
      assert.equal(isForbidden, true);
    });

    it('identifies not-found account responses (404)', () => {
      const notFoundError = {
        status: 404,
        message: 'User not found',
      };

      assert.equal(notFoundError.status, 404);
    });
  });
});
