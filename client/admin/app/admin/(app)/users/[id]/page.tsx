'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { UserRole, UserStatus } from '@/lib/types';
import { ADMIN_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { AvatarInitials } from '@/components/shared/AvatarInitials';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import { ArrowLeft, Edit3, Power, Trash2, Save, X, Shield, ShieldCheck, Building, Calendar, Clock } from 'lucide-react';

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params?.id as string;

  const { getUserById, updateUser, toggleUserStatus, deleteUser } = useUserStore();
  const user = getUserById(userId);

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [organization, setOrganization] = useState(user?.organization || '');
  const [role, setRole] = useState<UserRole>(user?.role || 'USER');
  const [status, setStatus] = useState<UserStatus>(user?.status || 'ACTIVE');

  const [confirmDialog, setConfirmDialog] = useState<'toggle' | 'delete' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  if (!user) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="User Not Found"
          subtitle="The requested user account record could not be found."
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.USERS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Users
            </Button>
          }
        />
        <EmptyState
          title="User Record Not Found"
          description="The user ID does not exist in local session store."
        />
      </div>
    );
  }

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);

    setTimeout(() => {
      updateUser(user.id, {
        name,
        email,
        organization,
        role: user.isProtected ? 'SUPER_ADMIN' : role,
        status: user.isProtected ? 'ACTIVE' : status,
      });

      setIsProcessing(false);
      setIsEditing(false);
    }, 300);
  };

  const handleConfirmAction = () => {
    setIsProcessing(true);
    setTimeout(() => {
      if (confirmDialog === 'toggle') {
        toggleUserStatus(user.id);
      } else if (confirmDialog === 'delete') {
        deleteUser(user.id);
        router.push(ADMIN_ROUTES.USERS);
        return;
      }
      setIsProcessing(false);
      setConfirmDialog(null);
    }, 300);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header Navigation */}
      <PageHeader
        title={user.name}
        subtitle={`Account ID: ${user.id}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.USERS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Users
            </Button>
            {!user.isProtected && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsEditing(!isEditing)}
                >
                  <Edit3 className="h-3.5 w-3.5 mr-1.5" />
                  {isEditing ? 'Cancel Edit' : 'Edit Details'}
                </Button>
                <Button
                  variant={user.status === 'ACTIVE' ? 'destructive' : 'secondary'}
                  size="sm"
                  onClick={() => setConfirmDialog('toggle')}
                >
                  <Power className="h-3.5 w-3.5 mr-1.5" />
                  {user.status === 'ACTIVE' ? 'Disable Account' : 'Reactivate'}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmDialog('delete')}
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  Delete
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* User Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        {/* Profile Identity Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#D9E1EA] gap-4">
          <div className="flex items-center gap-4">
            <AvatarInitials name={user.name} size="lg" />
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold font-serif text-[#17253A]">{user.name}</h2>
                <Badge variant={user.status === 'ACTIVE' ? 'success' : 'error'}>
                  {user.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                </Badge>
                {user.isProtected && (
                  <Badge variant="primary" size="sm">
                    <ShieldCheck className="h-3 w-3 mr-1" /> Protected System
                  </Badge>
                )}
              </div>
              <p className="text-xs font-mono text-[#526176] mt-1">{user.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={user.role === 'SUPER_ADMIN' ? 'primary' : 'default'} size="md">
              <Shield className="h-3.5 w-3.5 mr-1" />
              {user.role}
            </Badge>
          </div>
        </div>

        {/* View / Edit Mode Form */}
        {isEditing ? (
          <form onSubmit={handleSaveEdit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Full Name
                </label>
                <Input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Email Address
                </label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Organization
                </label>
                <Input value={organization} onChange={(e) => setOrganization(e.target.value)} />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Role
                </label>
                <Select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  disabled={user.isProtected}
                >
                  <option value="USER">User</option>
                  <option value="ADMIN">Admin</option>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#D9E1EA]">
              <Button type="button" variant="ghost" onClick={() => setIsEditing(false)}>
                <X className="h-4 w-4 mr-1.5" /> Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isProcessing}>
                <Save className="h-4 w-4 mr-1.5" /> Save Changes
              </Button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-xs font-mono">
            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Building className="h-3.5 w-3.5 text-[#2563A8]" /> Organization
              </span>
              <p className="font-semibold text-[#17253A]">{user.organization || '—'}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-[#2563A8]" /> Account Created
              </span>
              <p className="font-semibold text-[#17253A]">{formatDate(user.createdAt)}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-[#2563A8]" /> Last Active Timestamp
              </span>
              <p className="font-semibold text-[#17253A]">
                {user.lastActiveAt ? formatDate(user.lastActiveAt) : 'Never'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Dialog Confirmations */}
      {confirmDialog === 'toggle' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setConfirmDialog(null)}
          onConfirm={handleConfirmAction}
          title={user.status === 'ACTIVE' ? 'Disable Account?' : 'Reactivate Account?'}
          message={`Are you sure you want to ${
            user.status === 'ACTIVE' ? 'disable' : 'reactivate'
          } access for ${user.name}?`}
          confirmText={user.status === 'ACTIVE' ? 'Disable' : 'Reactivate'}
          variant={user.status === 'ACTIVE' ? 'danger' : 'primary'}
          isLoading={isProcessing}
        />
      )}

      {confirmDialog === 'delete' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setConfirmDialog(null)}
          onConfirm={handleConfirmAction}
          title="Delete Account?"
          message={`Are you sure you want to permanently delete user account ${user.name} (${user.email})?`}
          confirmText="Delete Account"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
