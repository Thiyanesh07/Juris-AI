'use client';

import React from 'react';
import { TimelineEvent } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Clock, Calendar, Landmark, BookOpen, FileCheck } from 'lucide-react';

interface TimelineTabProps {
  timeline: TimelineEvent[];
  timelineAvailable: boolean;
}

export const LegalTimelineTab: React.FC<TimelineTabProps> = ({ timeline, timelineAvailable }) => {
  const getDocIcon = (type: TimelineEvent['documentType']) => {
    switch (type) {
      case 'CONSTITUTION':
        return <Landmark className="h-4 w-4 text-[#1D4E8A]" />;
      case 'JUDGMENT':
        return <BookOpen className="h-4 w-4 text-[#7C3AED]" />;
      case 'AMENDMENT':
        return <FileCheck className="h-4 w-4 text-[#059669]" />;
      default:
        return <Calendar className="h-4 w-4 text-[#D97706]" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-[#1D4E8A]" />
          <div>
            <h2 className="text-base font-bold text-[#17253A] font-sans">Evolutionary Legal Timeline</h2>
            <p className="text-xs text-[#526176] font-mono">
              {timelineAvailable
                ? 'Chronological progression of constitutional provisions, amendments, and precedent judgments'
                : 'Timeline data not available for this result'}
            </p>
          </div>
        </div>
      </div>

      {timelineAvailable && timeline.length > 0 ? (
        <div className="card p-6 relative">
          <div className="timeline-line" />
          <div className="space-y-8 relative">
            {timeline.map((event, idx) => (
              <div key={event.id} className="flex items-start gap-4 group">
                {/* Dot */}
                <div className="h-6 w-6 rounded-full bg-white border-2 border-[#1D4E8A] flex items-center justify-center shrink-0 z-10 shadow-xs group-hover:scale-110 transition-transform">
                  <span className="w-2 h-2 rounded-full bg-[#1D4E8A]" />
                </div>
                {/* Event Content */}
                <div className="flex-1 bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0] group-hover:border-[#CBD5E0] transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#1D4E8A] bg-[#E8F0FD] px-2 py-0.5 rounded-md border border-[#BFDBFE]">
                        {event.year}
                      </span>
                      <span className="flex items-center gap-1 text-xs font-semibold text-[#17253A] font-sans">
                        {getDocIcon(event.documentType)}
                        {event.title}
                      </span>
                    </div>
                    <Badge variant={event.importance === 'HIGH' ? 'primary' : 'default'}>
                      {event.documentType}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#526176] leading-relaxed font-sans">{event.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Timeline unavailable — no dedicated backend timeline endpoint exists */
        <div className="card p-8 bg-[#F8FAFC] min-h-[200px] flex flex-col items-center justify-center gap-4 border-[#CBD5E0] border-dashed">
          <Clock className="h-10 w-10 text-[#CBD5E0]" />
          <div className="text-center space-y-2">
            <p className="text-sm font-bold text-[#526176] font-sans">Temporal Evidence Unavailable</p>
            <p className="text-xs text-[#718096] font-mono max-w-md">
              No authoritative temporal milestones or amendment dates were detected in the retrieved evidence for this legal query.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
