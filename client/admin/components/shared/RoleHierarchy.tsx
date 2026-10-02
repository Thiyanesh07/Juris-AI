import React from 'react';
import { cn } from '@/lib/utils';
import { ShieldCheck, Shield, User } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

export interface RoleHierarchyProps {
  className?: string;
}

export const RoleHierarchy: React.FC<RoleHierarchyProps> = ({ className }) => {
  return (
    <div className={cn('p-5 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] space-y-4', className)}>
      <h4 className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider border-b border-[#D9E1EA] pb-2">
        RBAC Privilege Hierarchy
      </h4>

      {/* SUPER_ADMIN */}
      <div className="p-3 rounded-lg bg-[#D9E7F5] border border-[#B5D3EE] flex items-start gap-3">
        <div className="p-1.5 rounded bg-[#2563A8] text-white">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#17253A]">SUPER_ADMIN</span>
            <Badge variant="primary" size="sm">System Bootstrapped</Badge>
          </div>
          <p className="text-xs text-[#526176] mt-0.5">
            Full system control. System-bootstrapped only. Cannot be created or deleted via UI interface.
          </p>
        </div>
      </div>

      {/* ADMIN */}
      <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#C9D4E1] flex items-start gap-3 ml-4">
        <div className="p-1.5 rounded bg-[#3B82D0] text-white">
          <Shield className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#17253A]">ADMIN</span>
            <Badge variant="default" size="sm">Operational Admin</Badge>
          </div>
          <p className="text-xs text-[#526176] mt-0.5">
            Operational administration. User management, document management, ingestion, graph validation, and audit access.
          </p>
        </div>
      </div>

      {/* USER */}
      <div className="p-3 rounded-lg bg-[#EFF3F7]/50 border border-[#D9E1EA] flex items-start gap-3 ml-8">
        <div className="p-1.5 rounded bg-[#718096] text-white">
          <User className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#17253A]">USER</span>
            <Badge variant="outline" size="sm">End User Portal</Badge>
          </div>
          <p className="text-xs text-[#526176] mt-0.5">
            Standard research user. Must not access /admin operational routes.
          </p>
        </div>
      </div>
    </div>
  );
};
