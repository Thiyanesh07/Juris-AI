'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { User } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { AvatarInitials } from '@/components/shared/AvatarInitials';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dropdown } from '@/components/ui/Dropdown';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import { ShieldAlert, ShieldCheck, Eye, Power, Trash2, Lock, MoreVertical } from 'lucide-react';

export default function AdminsListPage() {
  const router = useRouter();
  const { admins, toggleUserStatus, deleteUser } = useUserStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const [targetAdmin, setTargetAdmin] = useState<User | null>(null);
  const [actionType, setActionType] = useState<'toggle' | 'delete' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const filteredAdmins = useMemo(() => {
    return admins.filter((a) => {
      const matchesSearch =
        a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.email.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || a.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [admins, searchQuery, statusFilter]);

  const handleActionConfirm = () => {
    if (!targetAdmin || !actionType || targetAdmin.isProtected) return;
    setIsProcessing(true);

    setTimeout(() => {
      if (actionType === 'toggle') {
        toggleUserStatus(targetAdmin.id);
      } else if (actionType === 'delete') {
        deleteUser(targetAdmin.id);
      }

      setIsProcessing(false);
      setTargetAdmin(null);
      setActionType(null);
    }, 300);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Administrators"
        subtitle="Manage administrative roles, privilege levels, and security operators."
        actions={
          <Link href={ADMIN_ROUTES.ADMIN_NEW}>
            <Button variant="primary" size="md">
              <ShieldAlert className="h-4 w-4 mr-2" />
              Create Administrator
            </Button>
          </Link>
        }
      />

      {/* System Bootstrap Super Admin Banner Notice */}
      <div className="p-4 rounded-xl bg-[#D9E7F5] border border-[#B5D3EE] flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[#2563A8] text-white shrink-0 mt-0.5">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div className="text-xs text-[#17253A]">
          <h4 className="font-bold text-sm font-serif">Super Administrator Privilege Model</h4>
          <p className="text-[#526176] mt-0.5 leading-relaxed">
            The Super Administrator account is system-bootstrapped and protected. It cannot be deleted, disabled, or demoted through normal administrative UI interfaces.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Search administrators by name or email..."
        onReset={() => {
          setSearchQuery('');
          setStatusFilter('ALL');
        }}
        filters={
          <Select
            density="dense"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-32 bg-white text-xs"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Disabled</option>
          </Select>
        }
      />

      {/* Table & List View */}
      {filteredAdmins.length === 0 ? (
        <EmptyState
          title="No administrators found"
          description="No records match your search or filter parameters."
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP TABLE */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">Administrator</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Last Active</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {filteredAdmins.map((a) => (
                    <tr
                      key={a.id}
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.ADMIN_DETAIL(a.id))}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <AvatarInitials name={a.name} size="sm" />
                          <div className="flex flex-col">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-[#17253A] text-xs leading-tight">
                                {a.name}
                              </span>
                              {a.isProtected && (
                                <Badge variant="primary" size="sm">
                                  <Lock className="h-3 w-3 mr-1" /> Protected
                                </Badge>
                              )}
                            </div>
                            <span className="text-[11px] text-[#718096]">{a.organization}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#526176]">{a.email}</td>
                      <td className="px-4 py-3.5">
                        <Badge
                          variant={a.role === 'SUPER_ADMIN' ? 'primary' : 'default'}
                        >
                          {a.role}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant={a.status === 'ACTIVE' ? 'success' : 'error'}>
                          {a.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {formatDate(a.createdAt)}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {a.lastActiveAt ? formatDate(a.lastActiveAt) : 'Never'}
                      </td>
                      <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                        {a.isProtected ? (
                          <span className="text-xs font-mono text-[#718096] italic pr-2">
                            System Managed
                          </span>
                        ) : (
                          <Dropdown
                            trigger={
                              <button className="p-1.5 rounded-lg hover:bg-[#D9E7F5] text-[#526176] transition-colors cursor-pointer">
                                <MoreVertical className="h-4 w-4" />
                              </button>
                            }
                            items={[
                              {
                                id: 'view',
                                label: 'View Details',
                                icon: <Eye className="h-3.5 w-3.5" />,
                                onClick: () => router.push(ADMIN_DYNAMIC_ROUTES.ADMIN_DETAIL(a.id)),
                              },
                              {
                                id: 'toggle',
                                label: a.status === 'ACTIVE' ? 'Disable Account' : 'Reactivate',
                                icon: <Power className="h-3.5 w-3.5" />,
                                onClick: () => {
                                  setTargetAdmin(a);
                                  setActionType('toggle');
                                },
                              },
                              {
                                id: 'delete',
                                label: 'Delete Operator',
                                icon: <Trash2 className="h-3.5 w-3.5" />,
                                danger: true,
                                onClick: () => {
                                  setTargetAdmin(a);
                                  setActionType('delete');
                                },
                              },
                            ]}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* MOBILE CARDS LIST */}
          <div className="md:hidden space-y-3">
            {filteredAdmins.map((a) => (
              <div
                key={a.id}
                onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.ADMIN_DETAIL(a.id))}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AvatarInitials name={a.name} size="sm" />
                    <div>
                      <h4 className="text-sm font-semibold text-[#17253A] leading-tight">
                        {a.name}
                      </h4>
                      <p className="text-xs text-[#718096] font-mono">{a.email}</p>
                    </div>
                  </div>
                  <Badge variant={a.status === 'ACTIVE' ? 'success' : 'error'}>
                    {a.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                  </Badge>
                </div>

                <div className="flex items-center justify-between text-xs font-mono border-t border-[#D9E1EA] pt-2 text-[#718096]">
                  <span>Role: {a.role}</span>
                  {a.isProtected && <span className="text-[#2563A8] font-bold">Protected</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Dialogs */}
      {targetAdmin && actionType === 'toggle' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => {
            setTargetAdmin(null);
            setActionType(null);
          }}
          onConfirm={handleActionConfirm}
          title={targetAdmin.status === 'ACTIVE' ? 'Disable Administrator?' : 'Reactivate Administrator?'}
          message={`Are you sure you want to ${
            targetAdmin.status === 'ACTIVE' ? 'disable' : 'reactivate'
          } access for operator ${targetAdmin.name}?`}
          confirmText={targetAdmin.status === 'ACTIVE' ? 'Disable Operator' : 'Reactivate'}
          variant={targetAdmin.status === 'ACTIVE' ? 'danger' : 'primary'}
          isLoading={isProcessing}
        />
      )}

      {targetAdmin && actionType === 'delete' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => {
            setTargetAdmin(null);
            setActionType(null);
          }}
          onConfirm={handleActionConfirm}
          title="Delete Administrator Operator?"
          message={`Are you sure you want to permanently remove operator ${targetAdmin.name} (${targetAdmin.email})?`}
          confirmText="Delete Operator"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
