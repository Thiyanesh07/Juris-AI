'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { UserStatus } from '@/lib/types';
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
import { ArrowLeft, Edit3, Power, Trash2, Save, X, ShieldCheck, Lock, Building, Calendar, Clock } from 'lucide-react';

export default function AdminDetailPage() {
  const params = useParams();
  const router = useRouter();
  const adminId = params?.id as string;

  const { getUserById, updateUser, toggleUserStatus, deleteUser } = useUserStore();
  const admin = getUserById(adminId);

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(admin?.name || '');
  const [email, setEmail] = useState(admin?.email || '');
  const [organization, setOrganization] = useState(admin?.organization || '');
  const [status, setStatus] = useState<UserStatus>(admin?.status || 'ACTIVE');

  const [confirmDialog, setConfirmDialog] = useState<'toggle' | 'delete' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  if (!admin) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="Administrator Not Found"
          subtitle="The requested administrator record could not be found."
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.ADMINS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Administrators
            </Button>
          }
        />
        <EmptyState
          title="Administrator Record Not Found"
          description="The operator ID does not exist in local session store."
        />
      </div>
    );
  }

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (admin.isProtected) return;

    setIsProcessing(true);
    setTimeout(() => {
      updateUser(admin.id, {
        name,
        email,
        organization,
        status,
      });

      setIsProcessing(false);
      setIsEditing(false);
    }, 300);
  };

  const handleConfirmAction = () => {
    if (admin.isProtected) return;

    setIsProcessing(true);
    setTimeout(() => {
      if (confirmDialog === 'toggle') {
        toggleUserStatus(admin.id);
      } else if (confirmDialog === 'delete') {
        deleteUser(admin.id);
        router.push(ADMIN_ROUTES.ADMINS);
        return;
      }
      setIsProcessing(false);
      setConfirmDialog(null);
    }, 300);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <PageHeader
        title={admin.name}
        subtitle={`Administrator ID: ${admin.id}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.ADMINS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Administrators
            </Button>
            {!admin.isProtected && (
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
                  variant={admin.status === 'ACTIVE' ? 'destructive' : 'secondary'}
                  size="sm"
                  onClick={() => setConfirmDialog('toggle')}
                >
                  <Power className="h-3.5 w-3.5 mr-1.5" />
                  {admin.status === 'ACTIVE' ? 'Disable Access' : 'Reactivate'}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmDialog('delete')}
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  Delete Operator
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* Super Admin Protection Alert Banner */}
      {admin.isProtected && (
        <div className="p-4 rounded-xl bg-[#D9E7F5] border border-[#B5D3EE] flex items-center gap-3 text-xs text-[#17253A]">
          <Lock className="h-5 w-5 text-[#2563A8] shrink-0" />
          <div>
            <h4 className="font-bold text-sm">Protected Super Administrator Account</h4>
            <p className="text-[#526176] mt-0.5">
              This account is managed by the system bootstrap configuration and cannot be deleted, disabled, or demoted.
            </p>
          </div>
        </div>
      )}

      {/* Main Admin Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#D9E1EA] gap-4">
          <div className="flex items-center gap-4">
            <AvatarInitials name={admin.name} size="lg" />
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold font-serif text-[#17253A]">{admin.name}</h2>
                <Badge variant={admin.status === 'ACTIVE' ? 'success' : 'error'}>
                  {admin.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                </Badge>
              </div>
              <p className="text-xs font-mono text-[#526176] mt-1">{admin.email}</p>
            </div>
          </div>

          <Badge variant="primary" size="md">
            <ShieldCheck className="h-4 w-4 mr-1.5" />
            {admin.role}
          </Badge>
        </div>

        {/* View / Edit Mode */}
        {isEditing && !admin.isProtected ? (
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
                  Department / Division
                </label>
                <Input value={organization} onChange={(e) => setOrganization(e.target.value)} />
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Account Status
                </label>
                <Select value={status} onChange={(e) => setStatus(e.target.value as UserStatus)}>
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Disabled</option>
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
                <Building className="h-3.5 w-3.5 text-[#2563A8]" /> Department / Division
              </span>
              <p className="font-semibold text-[#17253A]">{admin.organization || 'Juris AI Operations'}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-[#2563A8]" /> Created Date
              </span>
              <p className="font-semibold text-[#17253A]">{formatDate(admin.createdAt)}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-[#2563A8]" /> Last Active Timestamp
              </span>
              <p className="font-semibold text-[#17253A]">
                {admin.lastActiveAt ? formatDate(admin.lastActiveAt) : 'Never'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Dialogs */}
      {confirmDialog === 'toggle' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setConfirmDialog(null)}
          onConfirm={handleConfirmAction}
          title={admin.status === 'ACTIVE' ? 'Disable Operator?' : 'Reactivate Operator?'}
          message={`Are you sure you want to ${
            admin.status === 'ACTIVE' ? 'disable' : 'reactivate'
          } access for administrator ${admin.name}?`}
          confirmText={admin.status === 'ACTIVE' ? 'Disable Operator' : 'Reactivate'}
          variant={admin.status === 'ACTIVE' ? 'danger' : 'primary'}
          isLoading={isProcessing}
        />
      )}

      {confirmDialog === 'delete' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setConfirmDialog(null)}
          onConfirm={handleConfirmAction}
          title="Delete Operator?"
          message={`Are you sure you want to permanently delete administrator ${admin.name} (${admin.email})?`}
          confirmText="Delete Operator"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
