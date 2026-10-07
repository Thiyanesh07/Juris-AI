'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { ValidationItem, ValidationStatus, ValidationCategory } from '@/lib/types';
import { INITIAL_MOCK_VALIDATION_ITEMS } from '@/data/validation';
import { apiClient } from '@/lib/apiClient';

interface BackendValidationItem {
  id: string;
  item_type: string;
  source_document_title?: string;
  proposed_label?: string;
  confidence_score?: number;
  status: string;
  rejection_note?: string;
  created_at: string;
}

interface ValidationStoreContextType {
  validationItems: ValidationItem[];
  searchQuery: string;
  typeFilter: string;
  statusFilter: string;
  confidenceFilter: string;
  isLoading: boolean;
  setSearchQuery: (query: string) => void;
  setTypeFilter: (type: string) => void;
  setStatusFilter: (status: string) => void;
  setConfidenceFilter: (conf: string) => void;
  resetFilters: () => void;
  getItemById: (id: string) => ValidationItem | undefined;
  approveItem: (id: string, note?: string) => boolean;
  rejectItem: (id: string, note: string) => boolean;
  bulkApproveItems: (ids: string[]) => number;
  filteredItems: ValidationItem[];
  metrics: {
    pending: number;
    approved: number;
    rejected: number;
    highConfidencePending: number;
  };
  refreshValidationItems: () => Promise<void>;
}

const ValidationStoreContext = createContext<ValidationStoreContextType | undefined>(undefined);

export const ValidationStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [validationItems, setValidationItems] = useState<ValidationItem[]>(INITIAL_MOCK_VALIDATION_ITEMS);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [confidenceFilter, setConfidenceFilter] = useState('ALL');

  const fetchValidationItems = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<{ items: BackendValidationItem[] }>('/validation?page_size=100');
      if (res && res.items && res.items.length > 0) {
        const mapped: ValidationItem[] = res.items.map((i) => ({
          id: i.id,
          title: i.proposed_label || `Extracted ${i.item_type}`,
          itemType: (i.item_type.toUpperCase() as ValidationCategory) || 'ENTITY',
          status: (i.status.toUpperCase() as ValidationStatus) || 'PENDING',
          confidenceScore: i.confidence_score ? Math.round(i.confidence_score * 100) : 92,
          sourceDocumentId: `doc_${i.id.slice(0, 8)}`,
          sourceDocumentTitle: i.source_document_title || 'Constitution of India',
          proposedLabel: i.proposed_label || `Extracted ${i.item_type}`,
          sourceTextSnippet: 'Extracted legal provision and evidence from indexed chunk.',
          createdAt: i.created_at || new Date().toISOString(),
        }));
        setValidationItems(mapped);
      }
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchValidationItems();
  }, [fetchValidationItems]);

  const getItemById = (id: string): ValidationItem | undefined => {
    return validationItems.find((item) => item.id === id);
  };

  const approveItem = (id: string, note?: string): boolean => {
    const item = getItemById(id);
    if (!item) return false;

    if (id.includes('-')) {
      apiClient.post(`/validation/${id}/approve`).catch(() => {});
    }

    setValidationItems((prev) =>
      prev.map((i) =>
        i.id === id
          ? {
              ...i,
              status: 'APPROVED',
              reviewedBy: 'Super Administrator',
              reviewedAt: new Date().toISOString(),
              reviewNote: note || i.reviewNote || 'Evidence and relationship structure approved.',
            }
          : i
      )
    );
    return true;
  };

  const rejectItem = (id: string, note: string): boolean => {
    if (!note || !note.trim()) return false;

    const item = getItemById(id);
    if (!item) return false;

    if (id.includes('-')) {
      apiClient.post(`/validation/${id}/reject`, { rejection_note: note.trim() }).catch(() => {});
    }

    setValidationItems((prev) =>
      prev.map((i) =>
        i.id === id
          ? {
              ...i,
              status: 'REJECTED',
              reviewedBy: 'Super Administrator',
              reviewedAt: new Date().toISOString(),
              reviewNote: note.trim(),
            }
          : i
      )
    );
    return true;
  };

  const bulkApproveItems = (ids: string[]): number => {
    const validIds = new Set(ids);
    let count = 0;

    const realUuidIds = ids.filter(i => i.includes('-'));
    if (realUuidIds.length > 0) {
      apiClient.post('/validation/bulk-approve', { item_ids: realUuidIds }).catch(() => {});
    }

    setValidationItems((prev) =>
      prev.map((i) => {
        if (validIds.has(i.id) && i.status === 'PENDING') {
          count++;
          return {
            ...i,
            status: 'APPROVED',
            reviewedBy: 'Super Administrator',
            reviewedAt: new Date().toISOString(),
            reviewNote: 'Bulk approved in quality control queue.',
          };
        }
        return i;
      })
    );
    return count;
  };

  const resetFilters = () => {
    setSearchQuery('');
    setTypeFilter('ALL');
    setStatusFilter('ALL');
    setConfidenceFilter('ALL');
  };

  const filteredItems = useMemo(() => {
    return validationItems.filter((item) => {
      const matchesSearch =
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.proposedLabel.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.sourceDocumentTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesType = typeFilter === 'ALL' || item.itemType === typeFilter;
      const matchesStatus = statusFilter === 'ALL' || item.status === statusFilter;

      let matchesConfidence = true;
      if (confidenceFilter === 'HIGH') matchesConfidence = item.confidenceScore >= 90;
      else if (confidenceFilter === 'MEDIUM')
        matchesConfidence = item.confidenceScore >= 70 && item.confidenceScore < 90;
      else if (confidenceFilter === 'LOW') matchesConfidence = item.confidenceScore < 70;

      return matchesSearch && matchesType && matchesStatus && matchesConfidence;
    });
  }, [validationItems, searchQuery, typeFilter, statusFilter, confidenceFilter]);

  const metrics = useMemo(() => {
    const pending = validationItems.filter((i) => i.status === 'PENDING').length;
    const approved = validationItems.filter((i) => i.status === 'APPROVED').length;
    const rejected = validationItems.filter((i) => i.status === 'REJECTED').length;
    const highConfidencePending = validationItems.filter(
      (i) => i.status === 'PENDING' && i.confidenceScore >= 90
    ).length;
    return { pending, approved, rejected, highConfidencePending };
  }, [validationItems]);

  return (
    <ValidationStoreContext.Provider
      value={{
        validationItems,
        searchQuery,
        typeFilter,
        statusFilter,
        confidenceFilter,
        isLoading,
        setSearchQuery,
        setTypeFilter,
        setStatusFilter,
        setConfidenceFilter,
        resetFilters,
        getItemById,
        approveItem,
        rejectItem,
        bulkApproveItems,
        filteredItems,
        metrics,
        refreshValidationItems: fetchValidationItems,
      }}
    >
      {children}
    </ValidationStoreContext.Provider>
  );
};

export const useValidationStore = () => {
  const context = useContext(ValidationStoreContext);
  if (!context) {
    throw new Error('useValidationStore must be used within a ValidationStoreProvider');
  }
  return context;
};

