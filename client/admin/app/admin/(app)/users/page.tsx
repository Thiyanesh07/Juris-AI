'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useUserStore } from '@/context/UserStoreContext';
import { User, UserStatus, UserRole } from '@/lib/types';
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
import { UserPlus, Eye, ShieldAlert, Power, Trash2, ChevronLeft, ChevronRight, MoreVertical } from 'lucide-react';

export default function UsersListPage() {
  const router = useRouter();
  const { users, toggleUserStatus, deleteUser } = useUserStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  // Dialog states
  const [targetUser, setTargetUser] = useState<User | null>(null);
  const [actionType, setActionType] = useState<'toggle' | 'delete' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Filtered dataset
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch =
        u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus = statusFilter === 'ALL' || u.status === statusFilter;
      const matchesRole = roleFilter === 'ALL' || u.role === roleFilter;

      return matchesSearch && matchesStatus && matchesRole;
    });
  }, [users, searchQuery, statusFilter, roleFilter]);

  // Paginated dataset
  const totalPages = Math.ceil(filteredUsers.length / pageSize) || 1;
  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredUsers.slice(start, start + pageSize);
  }, [filteredUsers, currentPage, pageSize]);

  const handleActionConfirm = () => {
    if (!targetUser || !actionType) return;
    setIsProcessing(true);

    setTimeout(() => {
      if (actionType === 'toggle') {
        toggleUserStatus(targetUser.id);
      } else if (actionType === 'delete') {
        deleteUser(targetUser.id);
      }

      setIsProcessing(false);
      setTargetUser(null);
      setActionType(null);
    }, 300);
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setStatusFilter('ALL');
    setRoleFilter('ALL');
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Users"
        subtitle="Manage client accounts, workspace memberships, and access controls."
        actions={
          <Link href={ADMIN_ROUTES.USER_NEW}>
            <Button variant="primary" size="md">
              <UserPlus className="h-4 w-4 mr-2" />
              Create User
            </Button>
          </Link>
        }
      />

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={(val) => {
          setSearchQuery(val);
          setCurrentPage(1);
        }}
        placeholder="Search users by name or email..."
        onReset={handleResetFilters}
        filters={
          <>
            <Select
              density="dense"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-32 bg-white text-xs"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Disabled</option>
            </Select>

            <Select
              density="dense"
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-32 bg-white text-xs"
            >
              <option value="ALL">All Roles</option>
              <option value="USER">User</option>
              <option value="ADMIN">Admin</option>
            </Select>
          </>
        }
      />

      {/* Content Container */}
      {filteredUsers.length === 0 ? (
        <EmptyState
          title="No users found"
          description="No records match your search or active filter criteria. Try clearing search parameters."
          action={
            <Button variant="secondary" size="sm" onClick={handleResetFilters}>
              Reset Filters
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP TABLE (≥ 768px) */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Last Active</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {paginatedUsers.map((u) => (
                    <tr
                      key={u.id}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.USER_DETAIL(u.id))}
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <AvatarInitials name={u.name} size="sm" />
                          <div className="flex flex-col">
                            <span className="font-semibold text-[#17253A] text-xs leading-tight">
                              {u.name}
                            </span>
                            {u.organization && (
                              <span className="text-[11px] text-[#718096]">{u.organization}</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#526176]">{u.email}</td>
                      <td className="px-4 py-3.5">
                        <Badge
                          variant={u.role === 'SUPER_ADMIN' ? 'primary' : u.role === 'ADMIN' ? 'primary' : 'default'}
                        >
                          {u.role}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant={u.status === 'ACTIVE' ? 'success' : 'error'}>
                          {u.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {formatDate(u.createdAt)}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {u.lastActiveAt ? formatDate(u.lastActiveAt) : 'Never'}
                      </td>
                      <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
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
                              onClick: () => router.push(ADMIN_DYNAMIC_ROUTES.USER_DETAIL(u.id)),
                            },
                            {
                              id: 'toggle',
                              label: u.status === 'ACTIVE' ? 'Disable Account' : 'Reactivate Account',
                              icon: <Power className="h-3.5 w-3.5" />,
                              onClick: () => {
                                setTargetUser(u);
                                setActionType('toggle');
                              },
                            },
                            {
                              id: 'delete',
                              label: 'Delete User',
                              icon: <Trash2 className="h-3.5 w-3.5" />,
                              danger: true,
                              onClick: () => {
                                setTargetUser(u);
                                setActionType('delete');
                              },
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* MOBILE CARDS LIST (< 768px) */}
          <div className="md:hidden space-y-3">
            {paginatedUsers.map((u) => (
              <div
                key={u.id}
                onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.USER_DETAIL(u.id))}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AvatarInitials name={u.name} size="sm" />
                    <div>
                      <h4 className="text-sm font-semibold text-[#17253A] leading-tight">
                        {u.name}
                      </h4>
                      <p className="text-xs text-[#718096] font-mono">{u.email}</p>
                    </div>
                  </div>
                  <Badge variant={u.status === 'ACTIVE' ? 'success' : 'error'}>
                    {u.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                  </Badge>
                </div>

                <div className="flex items-center justify-between text-xs font-mono border-t border-[#D9E1EA] pt-2 text-[#718096]">
                  <span>Role: {u.role}</span>
                  <span>Created: {formatDate(u.createdAt)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] text-xs font-mono">
            <span className="text-[#526176]">
              Showing {Math.min((currentPage - 1) * pageSize + 1, filteredUsers.length)} to{' '}
              {Math.min(currentPage * pageSize, filteredUsers.length)} of {filteredUsers.length} users
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>

              <span className="px-3 py-1 bg-white rounded border border-[#C9D4E1] font-semibold text-[#17253A]">
                {currentPage} / {totalPages}
              </span>

              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialogs */}
      {targetUser && actionType === 'toggle' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => {
            setTargetUser(null);
            setActionType(null);
          }}
          onConfirm={handleActionConfirm}
          title={targetUser.status === 'ACTIVE' ? 'Disable User Account?' : 'Reactivate User Account?'}
          message={`Are you sure you want to ${
            targetUser.status === 'ACTIVE' ? 'disable' : 'reactivate'
          } access for ${targetUser.name} (${targetUser.email})?`}
          confirmText={targetUser.status === 'ACTIVE' ? 'Disable Account' : 'Reactivate'}
          variant={targetUser.status === 'ACTIVE' ? 'danger' : 'primary'}
          isLoading={isProcessing}
        />
      )}

      {targetUser && actionType === 'delete' && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => {
            setTargetUser(null);
            setActionType(null);
          }}
          onConfirm={handleActionConfirm}
          title="Delete User Account?"
          message={`Are you sure you want to permanently delete ${targetUser.name} (${targetUser.email})? This action cannot be undone.`}
          confirmText="Delete Account"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
