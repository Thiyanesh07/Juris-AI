'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { ADMIN_ROUTES } from '@/constants/routes';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { UserPlus, ArrowLeft, CheckCircle2, AlertCircle, Lock } from 'lucide-react';

export default function CreateUserPage() {
  const router = useRouter();
  const { createUser } = useUserStore();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [organization, setOrganization] = useState('');

  const [errors, setErrors] = useState<{ name?: string; email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const validate = (): boolean => {
    const errs: { name?: string; email?: string; password?: string } = {};
    if (!name.trim()) errs.name = 'Full name is required.';
    if (!email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = 'Please enter a valid email address.';
    }
    if (password && password.length < 8) {
      errs.password = 'Password must be at least 8 characters long.';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setSuccessMessage(null);
    setSubmitError(null);

    try {
      const created = await createUser({
        name: name.trim(),
        email: email.trim(),
        password: password.trim() ? password.trim() : undefined,
      });

      setSuccessMessage(`User "${created.name}" created successfully.`);

      setTimeout(() => {
        router.push(ADMIN_ROUTES.USERS);
      }, 800);
    } catch (err: any) {
      const msg = err?.message || 'Failed to provision user.';
      if (msg.toLowerCase().includes('already registered') || err?.status === 409) {
        setErrors((prev) => ({ ...prev, email: 'This email address is already registered.' }));
      } else {
        setSubmitError(msg);
      }
    } finally {
      setIsLoading(false);
    }
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

      {submitError && (
        <div className="p-4 rounded-xl bg-[#FBEAEB] border border-[#F5C2C7] text-[#8B2E2E] text-sm font-mono flex items-center gap-2 animate-in fade-in">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{submitError}</span>
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

          <div>
            <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
              Initial Password (Optional)
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
              }}
              placeholder="Min 8 characters (or leave empty for Google OAuth)"
              error={!!errors.password}
            />
            {errors.password ? (
              <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> {errors.password}
              </p>
            ) : (
              <p className="text-[11px] text-[#718096] font-mono mt-1">
                Leave blank if the user will sign in with Google OAuth.
              </p>
            )}
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
