import { User } from '@/lib/types';

export const INITIAL_MOCK_ADMINS: User[] = [
  {
    id: 'usr_super_admin',
    name: 'Super Administrator',
    email: 'admin@example.com',
    role: 'SUPER_ADMIN',
    status: 'ACTIVE',
    organization: 'Juris AI Core System',
    createdAt: '2026-01-01T00:00:00Z',
    lastActiveAt: '2026-09-28T12:00:00Z',
    isProtected: true, // System bootstrap protected account
  },
  {
    id: 'usr_admin_002',
    name: 'Priyanka Kapoor',
    email: 'priyanka.kapoor@juris.ai',
    role: 'ADMIN',
    status: 'ACTIVE',
    organization: 'Juris AI Operations',
    createdAt: '2026-01-10T10:00:00Z',
    lastActiveAt: '2026-09-28T09:15:00Z',
  },
  {
    id: 'usr_admin_003',
    name: 'Devendra Sharma',
    email: 'devendra.sharma@juris.ai',
    role: 'ADMIN',
    status: 'ACTIVE',
    organization: 'Juris AI Data Telemetry',
    createdAt: '2026-02-15T14:30:00Z',
    lastActiveAt: '2026-09-27T18:45:00Z',
  },
  {
    id: 'usr_admin_004',
    name: 'Tanya Banerjee',
    email: 'tanya.banerjee@juris.ai',
    role: 'ADMIN',
    status: 'INACTIVE',
    organization: 'Juris AI Security Ops',
    createdAt: '2026-03-20T11:20:00Z',
    lastActiveAt: '2026-08-30T10:00:00Z',
  },
];
