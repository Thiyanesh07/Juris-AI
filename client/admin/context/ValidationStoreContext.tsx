'use client';

import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import { ValidationItem, ValidationStatus, ValidationCategory } from '@/lib/types';
import { apiClient } from '@/lib/apiClient';

export interface BackendValidationItem {
  id: string;
  item_type: string;
  status: string;
  confidence: number;
  proposed_payload?: Record<string, any>;
  evidence_text?: string | null;
  source_document_id?: string | null;
  source_chunk_id?: string | null;
  page_number?: number | null;
  reviewer_id?: string | null;
  decision_timestamp?: string | null;
  rejection_note?: string | null;
  created_at: string;
}

export function mapBackendValidationItem(i: BackendValidationItem): ValidationItem {
  const payload = i.proposed_payload || {};
  const label =
    payload.label ||
    payload.name ||
    payload.title ||
    payload.metadata_key ||
    (payload.source && payload.target ? `${payload.source} → ${payload.target}` : `Extracted ${i.item_type}`);

  const title =
    payload.title ||
    payload.name ||
    payload.label ||
    (payload.source && payload.target
      ? `${payload.source} → ${payload.relation || 'RELATES_TO'} → ${payload.target}`
      : `${i.item_type} validation item`);

  let relationship: ValidationItem['relationship'] | undefined = undefined;
  if (payload.source && payload.target) {
    relationship = {
      source: String(payload.source),
      relation: String(payload.relation || payload.relationship || 'RELATES_TO'),
      target: String(payload.target),
    };
  }

  return {
    id: i.id,
    title: title,
    itemType: (i.item_type?.toUpperCase() as ValidationCategory) || 'ENTITY',
    status: (i.status?.toUpperCase() as ValidationStatus) || 'PENDING',
    confidenceScore: typeof i.confidence === 'number' ? Math.round(i.confidence * 100) : 0,
    sourceDocumentId: i.source_document_id ? String(i.source_document_id) : '',
    sourceDocumentTitle:
      payload.document_title ||
      payload.source_title ||
      (i.source_document_id ? `Document ${String(i.source_document_id).slice(0, 8)}` : 'Source Document'),
    sourceLocation: i.page_number
      ? `Page ${i.page_number}`
      : (i.source_chunk_id ? `Chunk ${i.source_chunk_id}` : undefined),
    sourceTextSnippet: i.evidence_text || '',
    proposedLabel: label,
    createdAt: i.created_at || new Date().toISOString(),
    reviewedBy: i.reviewer_id ? String(i.reviewer_id) : undefined,
    reviewedAt: i.decision_timestamp || undefined,
    reviewNote: i.rejection_note || undefined,
    relationship: relationship,
    entityId: payload.entity_id || payload.id ? String(payload.entity_id || payload.id) : undefined,
    metadataKey: payload.metadata_key || undefined,
    metadataValue: payload.metadata_value || undefined,
  };
}

interface ValidationStoreContextType {
  validationItems: ValidationItem[];
  searchQuery: string;
  typeFilter: string;
  statusFilter: string;
  confidenceFilter: string;
  isLoading: boolean;
  error: string | null;
  isSubmitting: boolean;
  submittingIds: Set<string>;
  setSearchQuery: (query: string) => void;
  setTypeFilter: (type: string) => void;
  setStatusFilter: (status: string) => void;
  setConfidenceFilter: (conf: string) => void;
  resetFilters: () => void;
  getItemById: (id: string) => ValidationItem | undefined;
  fetchItemById: (id: string) => Promise<ValidationItem | null>;
  approveItem: (id: string, note?: string) => Promise<boolean>;
  rejectItem: (id: string, note: string) => Promise<boolean>;
  bulkApproveItems: (ids: string[]) => Promise<number>;
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
  const [validationItems, setValidationItems] = useState<ValidationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingIds, setSubmittingIds] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [confidenceFilter, setConfidenceFilter] = useState('ALL');

  const fetchValidationItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ items: BackendValidationItem[]; total: number }>('/validation?page_size=100');
      const items = res?.items || [];
      const mapped: ValidationItem[] = items.map(mapBackendValidationItem);
      setValidationItems(mapped);
    } catch (err: any) {
      setError(err?.message || 'Failed to load validation queue from server.');
      setValidationItems([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    apiClient
      .get<{ items: BackendValidationItem[]; total: number }>('/validation?page_size=100')
      .then((res) => {
        if (!active) return;
        const items = res?.items || [];
        const mapped: ValidationItem[] = items.map(mapBackendValidationItem);
        setValidationItems(mapped);
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err?.message || 'Failed to load validation queue from server.');
        setValidationItems([]);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const getItemById = useCallback(
    (id: string): ValidationItem | undefined => {
      return validationItems.find((item) => item.id === id);
    },
    [validationItems]
  );

  const fetchItemById = useCallback(
    async (id: string): Promise<ValidationItem | null> => {
      const existing = validationItems.find((item) => item.id === id);
      if (existing) return existing;

      try {
        const res = await apiClient.get<BackendValidationItem>(`/validation/${id}`);
        if (!res || !res.id) return null;
        return mapBackendValidationItem(res);
      } catch {
        return null;
      }
    },
    [validationItems]
  );

  const approveItem = useCallback(
    async (id: string, note?: string): Promise<boolean> => {
      if (submittingIds.has(id)) return false;

      setSubmittingIds((prev) => new Set(prev).add(id));
      try {
        const res = await apiClient.post<BackendValidationItem>(`/validation/${id}/approve`);
        setValidationItems((prev) =>
          prev.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: 'APPROVED',
                  reviewedBy: res?.reviewer_id ? String(res.reviewer_id) : 'Current Administrator',
                  reviewedAt: res?.decision_timestamp || new Date().toISOString(),
                  reviewNote: note || i.reviewNote || 'Approved into trusted knowledge layer.',
                }
              : i
          )
        );
        return true;
      } catch (err: any) {
        throw err;
      } finally {
        setSubmittingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }
    },
    [submittingIds]
  );

  const rejectItem = useCallback(
    async (id: string, note: string): Promise<boolean> => {
      const trimmedNote = (note || '').trim();
      if (!trimmedNote) {
        throw new Error('A rejection note is required.');
      }
      if (submittingIds.has(id)) return false;

      setSubmittingIds((prev) => new Set(prev).add(id));
      try {
        const res = await apiClient.post<BackendValidationItem>(`/validation/${id}/reject`, {
          rejection_note: trimmedNote,
        });
        setValidationItems((prev) =>
          prev.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: 'REJECTED',
                  reviewedBy: res?.reviewer_id ? String(res.reviewer_id) : 'Current Administrator',
                  reviewedAt: res?.decision_timestamp || new Date().toISOString(),
                  reviewNote: trimmedNote,
                }
              : i
          )
        );
        return true;
      } catch (err: any) {
        throw err;
      } finally {
        setSubmittingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }
    },
    [submittingIds]
  );

  const bulkApproveItems = useCallback(
    async (ids: string[]): Promise<number> => {
      if (ids.length === 0 || isSubmitting) return 0;

      setIsSubmitting(true);
      try {
        const res = await apiClient.post<{ approved_count: number }>('/validation/bulk-approve', {
          item_ids: ids,
        });
        const approvedCount = res?.approved_count ?? ids.length;
        const validIds = new Set(ids);
        setValidationItems((prev) =>
          prev.map((i) =>
            validIds.has(i.id) && i.status === 'PENDING'
              ? {
                  ...i,
                  status: 'APPROVED',
                  reviewedBy: 'Current Administrator',
                  reviewedAt: new Date().toISOString(),
                  reviewNote: 'Bulk approved in quality queue.',
                }
              : i
          )
        );
        return approvedCount;
      } catch (err: any) {
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [isSubmitting]
  );

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
        error,
        isSubmitting,
        submittingIds,
        setSearchQuery,
        setTypeFilter,
        setStatusFilter,
        setConfidenceFilter,
        resetFilters,
        getItemById,
        fetchItemById,
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
