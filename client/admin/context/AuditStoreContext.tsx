'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { AuditEvent, AuditCategory, AuditActionResult, AuditSeverity } from '@/lib/types';
import { apiClient } from '@/lib/apiClient';

export interface BackendAuditEvent {
  id: string;
  event_type: string;
  actor_id: string | null;
  actor_email: string | null;
  event_metadata: Record<string, any> | null;
  created_at: string;
}

export function mapBackendAuditEvent(e: BackendAuditEvent): AuditEvent {
  const meta = e.event_metadata || {};
  const parts = (e.event_type || 'SYSTEM_EVENT').split('_');
  const category = (meta.category || parts[0] || 'SYSTEM').toUpperCase() as AuditCategory;
  const action = meta.action || parts.slice(1).join('_') || e.event_type;
  const result = (meta.result || 'SUCCESS').toUpperCase() as AuditActionResult;
  const severity = (meta.severity || 'INFO').toUpperCase() as AuditSeverity;

  const actorEmail = e.actor_email || '';
  const actorName = e.actor_email
    ? e.actor_email.split('@')[0]
    : (e.actor_id ? `Admin (${e.actor_id.slice(0, 8)})` : 'System Service');

  return {
    id: e.id,
    timestamp: e.created_at || new Date().toISOString(),
    actorId: e.actor_id || 'system',
    actorName: actorName,
    actorEmail: actorEmail,
    actorRole: 'ADMIN',
    category: category,
    action: action,
    result: result,
    severity: severity,
    description: meta.description || `Audit event ${e.event_type}`,
    resourceType: meta.target_resource ? meta.target_resource.split(':')[0] : undefined,
    resourceId: meta.target_resource ? meta.target_resource.split(':')[1] || meta.target_resource : undefined,
    resourceName: meta.target_resource || undefined,
    ipAddress: meta.ip_address || undefined,
    userAgent: meta.user_agent || undefined,
    beforeState: meta.before_state || undefined,
    afterState: meta.after_state || undefined,
    metadata: meta.extra || meta,
  };
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
  error: string | null;
  setSearchQuery: (query: string) => void;
  setCategoryFilter: (cat: string) => void;
  setResultFilter: (res: string) => void;
  setActorFilter: (actor: string) => void;
  setDateRangeFilter: (range: string) => void;
  setSortOrder: (order: 'NEWEST' | 'OLDEST') => void;
  resetFilters: () => void;
  getEventById: (id: string) => AuditEvent | undefined;
  fetchEventById: (id: string) => Promise<AuditEvent | null>;
  fetchAuditEvents: () => Promise<void>;
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
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [lastFetchedAt, setLastFetchedAt] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [resultFilter, setResultFilter] = useState('ALL');
  const [actorFilter, setActorFilter] = useState('ALL');
  const [dateRangeFilter, setDateRangeFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState<'NEWEST' | 'OLDEST'>('NEWEST');

  const fetchAuditEvents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ items: BackendAuditEvent[]; total: number }>('/audit?page_size=100');
      const items = res?.items || [];
      const mapped: AuditEvent[] = items.map(mapBackendAuditEvent);
      setAuditEvents(mapped);
      setLastFetchedAt(Date.now());
    } catch (err: any) {
      setError(err?.message || 'Failed to load audit events from server.');
      setAuditEvents([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    apiClient
      .get<{ items: BackendAuditEvent[]; total: number }>('/audit?page_size=100')
      .then((res) => {
        if (!active) return;
        const items = res?.items || [];
        const mapped: AuditEvent[] = items.map(mapBackendAuditEvent);
        setAuditEvents(mapped);
        setLastFetchedAt(Date.now());
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err?.message || 'Failed to load audit events from server.');
        setAuditEvents([]);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const getEventById = useCallback(
    (id: string): AuditEvent | undefined => {
      return auditEvents.find((event) => event.id === id);
    },
    [auditEvents]
  );

  const fetchEventById = useCallback(
    async (id: string): Promise<AuditEvent | null> => {
      const existing = auditEvents.find((event) => event.id === id);
      if (existing) return existing;

      try {
        const res = await apiClient.get<BackendAuditEvent>(`/audit/${id}`);
        if (!res || !res.id) return null;
        return mapBackendAuditEvent(res);
      } catch {
        return null;
      }
    },
    [auditEvents]
  );

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
      if (evt.actorId && !map.has(evt.actorId)) {
        map.set(evt.actorId, {
          id: evt.actorId,
          name: evt.actorName || evt.actorEmail || 'Unknown Actor',
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
    const baseline = lastFetchedAt;
    const oneDayAgo = baseline > 0 ? baseline - 24 * 60 * 60 * 1000 : 0;
    const today = baseline > 0
      ? auditEvents.filter((e) => {
          const t = new Date(e.timestamp).getTime();
          return !isNaN(t) && t >= oneDayAgo;
        }).length
      : 0;

    return { total, success, failure, today };
  }, [auditEvents, lastFetchedAt]);

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
        error,
        setSearchQuery,
        setCategoryFilter,
        setResultFilter,
        setActorFilter,
        setDateRangeFilter,
        setSortOrder,
        resetFilters,
        getEventById,
        fetchEventById,
        fetchAuditEvents,
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
