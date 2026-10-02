import React from 'react';
import { cn, formatDateTime } from '@/lib/utils';
import { AuditEvent } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';

export interface ActivityFeedProps {
  events: AuditEvent[];
  className?: string;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ events, className }) => {
  if (!events || events.length === 0) {
    return (
      <div className={cn('p-6 text-center text-xs text-[#718096] font-mono', className)}>
        No recent audit events logged.
      </div>
    );
  }

  return (
    <div className={cn('divide-y divide-[#D9E1EA]', className)}>
      {events.map((event) => (
        <div key={event.id} className="py-3 px-4 flex items-start justify-between gap-4 hover:bg-[#EFF3F7]/50 transition-colors">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold text-[#17253A]">{event.actorEmail}</span>
              <span className="text-xs text-[#526176]">{event.action}</span>
            </div>
            <span className="text-[11px] font-mono text-[#718096] mt-0.5">
              Target: {event.resourceType || event.category} {event.resourceId && `(${event.resourceId})`}
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Badge
              variant={
                event.severity === 'ERROR'
                  ? 'error'
                  : event.severity === 'WARNING'
                  ? 'warning'
                  : 'default'
              }
            >
              {event.severity}
            </Badge>
            <span className="text-[11px] font-mono text-[#718096]">
              {formatDateTime(event.timestamp)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};
