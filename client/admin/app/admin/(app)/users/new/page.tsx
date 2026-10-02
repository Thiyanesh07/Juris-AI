'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { UserRole, UserStatus } from '@/lib/types';
import { ADMIN_ROUTES } from '@/constants/routes';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { UserPlus, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react';

export default function CreateUserPage() {
  const router = useRouter();
  const { addUser } = useUserStore();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<UserRole>('USER');
  const [status, setStatus] = useState<UserStatus>('ACTIVE');
  const [organization, setOrganization] = useState('');

  const [errors, setErrors] = useState<{ name?: string; email?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const validate = (): boolean => {
    const errs: { name?: string; email?: string } = {};
    if (!name.trim()) errs.name = 'Full name is required.';
    if (!email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please enter a valid email address.';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setSuccessMessage(null);

    setTimeout(() => {
      addUser({
        name,
        email,
        role,
        status,
        organization: organization || 'General User',
      });

      setIsLoading(false);
      setSuccessMessage(`User "${name}" created successfully in local state.`);

      setTimeout(() => {
        router.push(ADMIN_ROUTES.USERS);
      }, 800);
    }, 400);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Create User"
        subtitle="Provision a new research user account for workspace access."
        actions={
          <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.USERS)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to Users
          </Button>
        }
      />

      {successMessage && (
        <div className="p-4 rounded-xl bg-[#D0EDDB] border border-[#B2E2C3] text-[#1E6B45] text-sm font-mono flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
              Full Name <span className="text-[#8B2E2E]">*</span>
            </label>
            <Input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
              }}
              placeholder="e.g. Kavya Sharma"
              error={!!errors.name}
            />
            {errors.name && (
              <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> {errors.name}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
              Email Address <span className="text-[#8B2E2E]">*</span>
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
              }}
              placeholder="e.g. kavya.sharma@research.law.in"
              error={!!errors.email}
            />
            {errors.email && (
              <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> {errors.email}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                Assign Role
              </label>
              <Select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
                <option value="USER">User (Standard Access)</option>
                <option value="ADMIN">Admin (Operational Access)</option>
              </Select>
              <p className="text-[11px] text-[#718096] mt-1">
                Super Administrator access is reserved for the system bootstrap account.
              </p>
            </div>

            <div>
              <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                Initial Account Status
              </label>
              <Select value={status} onChange={(e) => setStatus(e.target.value as UserStatus)}>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Disabled</option>
              </Select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
              Organization / Chamber / Team (Optional)
            </label>
            <Input
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="e.g. High Court Research Chamber"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#D9E1EA]">
          <Button
            type="button"
            variant="ghost"
            onClick={() => router.push(ADMIN_ROUTES.USERS)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isLoading}>
            <UserPlus className="h-4 w-4 mr-1.5" />
            Create User Account
          </Button>
        </div>
      </form>
    </div>
  );
}
