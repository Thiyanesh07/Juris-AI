'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { AuditEvent } from '@/lib/types';
import { INITIAL_MOCK_AUDIT_EVENTS } from '@/data/audit';
import { apiClient } from '@/lib/apiClient';

interface BackendAuditEvent {
  id: string;
  event_type: string;
  actor_id: string | null;
  actor_email: string | null;
  event_metadata: Record<string, any> | null;
  created_at: string;
}

interface AuditStoreContextType {
  auditEvents: AuditEvent[];
  searchQuery: string;
  categoryFilter: string;
  resultFilter: string;
  actorFilter: string;
  dateRangeFilter: string;
  sortOrder: 'NEWEST' | 'OLDEST';
  isLoading: boolean;
  setSearchQuery: (query: string) => void;
  setCategoryFilter: (cat: string) => void;
  setResultFilter: (res: string) => void;
  setActorFilter: (actor: string) => void;
  setDateRangeFilter: (range: string) => void;
  setSortOrder: (order: 'NEWEST' | 'OLDEST') => void;
  resetFilters: () => void;
  getEventById: (id: string) => AuditEvent | undefined;
  filteredEvents: AuditEvent[];
  uniqueActors: Array<{ id: string; name: string; email: string; role: string }>;
  metrics: {
    total: number;
    success: number;
    failure: number;
    today: number;
  };
}

const AuditStoreContext = createContext<AuditStoreContextType | undefined>(undefined);

export const AuditStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>(INITIAL_MOCK_AUDIT_EVENTS);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [resultFilter, setResultFilter] = useState('ALL');
  const [actorFilter, setActorFilter] = useState('ALL');
  const [dateRangeFilter, setDateRangeFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState<'NEWEST' | 'OLDEST'>('NEWEST');

  const fetchAuditEvents = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<{ items: BackendAuditEvent[] }>('/audit?page_size=100');
      if (res && res.items && res.items.length > 0) {
        const mapped: AuditEvent[] = res.items.map((e) => {
          const parts = (e.event_type || 'SYSTEM_EVENT').split('_');
          const category = (parts[0] || 'SYSTEM') as any;
          const action = (parts.slice(1).join('_') || 'LOG') as any;
          return {
            id: e.id,
            timestamp: e.created_at || new Date().toISOString(),
            actorId: e.actor_id || 'system',
            actorName: e.actor_email ? e.actor_email.split('@')[0] : 'System Service',
            actorEmail: e.actor_email || 'system@juris.ai',
            actorRole: 'ADMIN' as any,
            category: category,
            action: action,
            result: 'SUCCESS' as any,
            severity: 'INFO' as any,
            description: e.event_metadata?.description || `Audit event ${e.event_type}`,
            resourceId: e.event_metadata?.target_resource || undefined,
            ipAddress: '127.0.0.1',
          };
        });
        setAuditEvents(mapped);
      }
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAuditEvents();
  }, [fetchAuditEvents]);

  const getEventById = (id: string): AuditEvent | undefined => {
    return auditEvents.find((event) => event.id === id);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setCategoryFilter('ALL');
    setResultFilter('ALL');
    setActorFilter('ALL');
    setDateRangeFilter('ALL');
    setSortOrder('NEWEST');
  };

  // Unique list of actors for filter dropdown
  const uniqueActors = useMemo(() => {
    const map = new Map<string, { id: string; name: string; email: string; role: string }>();
    auditEvents.forEach((evt) => {
      if (!map.has(evt.actorId)) {
        map.set(evt.actorId, {
          id: evt.actorId,
          name: evt.actorName,
          email: evt.actorEmail,
          role: evt.actorRole,
        });
      }
    });
    return Array.from(map.values());
  }, [auditEvents]);

  // Filtering & Sorting computation
  const filteredEvents = useMemo(() => {
    let result = auditEvents.filter((evt) => {
      const matchesSearch =
        evt.actorName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.actorEmail.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (evt.resourceName && evt.resourceName.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (evt.resourceId && evt.resourceId.toLowerCase().includes(searchQuery.toLowerCase())) ||
        evt.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory = categoryFilter === 'ALL' || evt.category === categoryFilter;
      const matchesResult = resultFilter === 'ALL' || evt.result === resultFilter;
      const matchesActor = actorFilter === 'ALL' || evt.actorId === actorFilter;

      return matchesSearch && matchesCategory && matchesResult && matchesActor;
    });

    result.sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'NEWEST' ? timeB - timeA : timeA - timeB;
    });

    return result;
  }, [auditEvents, searchQuery, categoryFilter, resultFilter, actorFilter, sortOrder]);

  const metrics = useMemo(() => {
    const total = auditEvents.length;
    const success = auditEvents.filter((e) => e.result === 'SUCCESS').length;
    const failure = auditEvents.filter((e) => e.result === 'FAILURE').length;
    const today = auditEvents.length;

    return { total, success, failure, today };
  }, [auditEvents]);

  return (
    <AuditStoreContext.Provider
      value={{
        auditEvents,
        searchQuery,
        categoryFilter,
        resultFilter,
        actorFilter,
        dateRangeFilter,
        sortOrder,
        isLoading,
        setSearchQuery,
        setCategoryFilter,
        setResultFilter,
        setActorFilter,
        setDateRangeFilter,
        setSortOrder,
        resetFilters,
        getEventById,
        filteredEvents,
        uniqueActors,
        metrics,
      }}
    >
      {children}
    </AuditStoreContext.Provider>
  );
};

export const useAuditStore = () => {
  const context = useContext(AuditStoreContext);
  if (!context) {
    throw new Error('useAuditStore must be used within an AuditStoreProvider');
  }
  return context;
};

