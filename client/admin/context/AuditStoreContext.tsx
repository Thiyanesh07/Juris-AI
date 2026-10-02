'use client';

import React, { createContext, useContext, useState, useMemo } from 'react';
import { AuditEvent, AuditCategory, AuditActionResult } from '@/lib/types';
import { INITIAL_MOCK_AUDIT_EVENTS } from '@/data/audit';

interface AuditStoreContextType {
  auditEvents: AuditEvent[];
  searchQuery: string;
  categoryFilter: string;
  resultFilter: string;
  actorFilter: string;
  dateRangeFilter: string;
  sortOrder: 'NEWEST' | 'OLDEST';
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
  const [auditEvents] = useState<AuditEvent[]>(INITIAL_MOCK_AUDIT_EVENTS);

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [resultFilter, setResultFilter] = useState('ALL');
  const [actorFilter, setActorFilter] = useState('ALL');
  const [dateRangeFilter, setDateRangeFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState<'NEWEST' | 'OLDEST'>('NEWEST');

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
      // Search matches actorName, actorEmail, action, resourceName, resourceId, description, id
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

      // Date filtering logic
      let matchesDate = true;
      if (dateRangeFilter !== 'ALL') {
        const evtTime = new Date(evt.timestamp).getTime();
        const now = new Date('2026-09-28T13:50:00Z').getTime(); // Baseline reference date in mock system
        const msInDay = 24 * 60 * 60 * 1000;

        if (dateRangeFilter === 'TODAY') {
          matchesDate = now - evtTime <= msInDay;
        } else if (dateRangeFilter === '7DAYS') {
          matchesDate = now - evtTime <= 7 * msInDay;
        } else if (dateRangeFilter === '30DAYS') {
          matchesDate = now - evtTime <= 30 * msInDay;
        }
      }

      return matchesSearch && matchesCategory && matchesResult && matchesActor && matchesDate;
    });

    // Sorting
    result.sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'NEWEST' ? timeB - timeA : timeA - timeB;
    });

    return result;
  }, [auditEvents, searchQuery, categoryFilter, resultFilter, actorFilter, dateRangeFilter, sortOrder]);

  // Telemetry metrics
  const metrics = useMemo(() => {
    const total = auditEvents.length;
    const success = auditEvents.filter((e) => e.result === 'SUCCESS').length;
    const failure = auditEvents.filter((e) => e.result === 'FAILURE').length;

    const refDateStr = '2026-09-28';
    const today = auditEvents.filter((e) => e.timestamp.startsWith(refDateStr)).length;

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
