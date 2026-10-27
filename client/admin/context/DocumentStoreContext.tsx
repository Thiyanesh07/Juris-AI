'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Document, DocumentStatus, DocumentTypeCategory, IngestionJob, IngestionJobStatus } from '@/lib/types';
import { apiClient } from '@/lib/apiClient';
import {
  PaginatedDocuments,
  DocumentSummary,
  DocumentDetail,
  DocumentUploadResponse,
  ReprocessResponse,
  ArchiveDocumentResponse,
  RestoreDocumentResponse,
  ProcessingJobSummary,
  PaginatedProcessingJobs,
  ProcessingJob,
} from '@/lib/apiTypes';

export interface DocumentFilterParams {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
  search?: string;
}

export interface JobFilterParams {
  page?: number;
  page_size?: number;
  status?: string;
  stage?: string;
  document_id?: string;
  search?: string;
}

export interface DocumentStoreContextType {
  documents: Document[];
  documentsTotal: number;
  isLoading: boolean;
  documentsError: string | null;

  ingestionJobs: ProcessingJobSummary[];
  jobsTotal: number;
  jobsLoading: boolean;
  jobsError: string | null;
  jobCounts: Record<string, number>;

  fetchDocuments: (params?: DocumentFilterParams) => Promise<void>;
  fetchJobs: (params?: JobFilterParams) => Promise<PaginatedProcessingJobs | undefined>;
  getDocumentById: (id: string) => Document | undefined;
  fetchDocumentDetail: (id: string) => Promise<Document | undefined>;
  getJobById: (id: string) => ProcessingJobSummary | undefined;
  fetchJobDetail: (id: string) => Promise<{
    job?: ProcessingJobSummary;
    document?: Document;
    stages?: ProcessingJob[];
  }>;
  getJobsByDocumentId: (documentId: string) => ProcessingJobSummary[];
  fetchDocumentStages: (documentId: string) => Promise<ProcessingJob[]>;

  uploadDocument: (
    file: File,
    metadata: { title: string; type: string; source?: string; source_url?: string }
  ) => Promise<DocumentUploadResponse>;
  archiveDocument: (id: string) => Promise<boolean>;
  restoreDocument: (id: string) => Promise<{ success: boolean; status?: string; message?: string }>;
  reprocessDocument: (id: string) => Promise<{ success: boolean; message?: string }>;
  startIngestion: (documentId: string) => Promise<boolean>;
  retryIngestion: (jobIdOrDocId: string) => Promise<boolean>;
  cancelIngestion: (jobId: string) => boolean;

  refreshDocuments: () => Promise<void>;
  refreshJobs: () => Promise<void>;
}

const DocumentStoreContext = createContext<DocumentStoreContextType | undefined>(undefined);

export function mapBackendStatus(statusStr?: string): DocumentStatus {
  if (!statusStr) return 'UPLOADED';
  const u = statusStr.toUpperCase();
  if (u === 'READY') return 'READY';
  if (u === 'PROCESSING') return 'PROCESSING';
  if (u === 'REGISTERED' || u === 'UPLOADED') return 'UPLOADED';
  if (u === 'FAILED') return 'FAILED';
  if (u === 'DISABLED' || u === 'ARCHIVED') return 'ARCHIVED';
  return 'UPLOADED';
}

export function mapBackendType(typeStr?: string): DocumentTypeCategory {
  if (!typeStr) return 'Other';
  const u = typeStr.toUpperCase();
  if (u === 'CONSTITUTION') return 'Constitution';
  if (u === 'ACT') return 'Act';
  if (u === 'AMENDMENT ACT' || u === 'AMENDMENT_ACT') return 'Amendment Act';
  if (u === 'RULE') return 'Rule';
  if (u === 'REGULATION') return 'Regulation';
  if (u === 'JUDGMENT') return 'Judgment';
  if (u === 'NOTIFICATION') return 'Notification';
  if (u === 'STATUTE') return 'Act';
  return 'Other';
}

export function mapDocumentRecord(d: DocumentSummary | DocumentDetail): Document {
  return {
    id: d.id,
    title: d.title,
    fileName: `${d.title.toLowerCase().replace(/[^a-z0-9]+/g, '_')}.pdf`,
    fileSizeBytes: 2048500,
    mimeType: 'application/pdf',
    documentType: mapBackendType(d.type),
    source: d.source || 'Official Gazette / Parliament of India',
    authority: d.source || 'Parliament of India',
    jurisdiction: 'Union of India',
    uploadedBy: 'system@juris.ai',
    status: mapBackendStatus(d.status),
    createdAt: d.created_at || new Date().toISOString(),
    updatedAt: d.updated_at || d.created_at || new Date().toISOString(),
  };
}

export const DocumentStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsTotal, setDocumentsTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [documentsError, setDocumentsError] = useState<string | null>(null);

  const [ingestionJobs, setIngestionJobs] = useState<ProcessingJobSummary[]>([]);
  const [jobsTotal, setJobsTotal] = useState<number>(0);
  const [jobCounts, setJobCounts] = useState<Record<string, number>>({});
  const [jobsLoading, setJobsLoading] = useState<boolean>(false);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async (params?: DocumentFilterParams) => {
    setIsLoading(true);
    setDocumentsError(null);
    try {
      const query = new URLSearchParams();
      query.set('page', String(params?.page || 1));
      query.set('page_size', String(params?.page_size || 50));
      if (params?.status && params.status !== 'ALL') {
        query.set('status', params.status.toLowerCase());
      }
      if (params?.type && params.type !== 'ALL') {
        query.set('type', params.type.toLowerCase());
      }
      if (params?.search && params.search.trim()) {
        query.set('search', params.search.trim());
      }

      const res = await apiClient.get<PaginatedDocuments>(`/documents?${query.toString()}`);
      if (res && Array.isArray(res.items)) {
        setDocuments(res.items.map(mapDocumentRecord));
        setDocumentsTotal(res.total ?? res.items.length);
      } else {
        setDocuments([]);
        setDocumentsTotal(0);
      }
    } catch (err) {
      setDocuments([]);
      setDocumentsTotal(0);
      setDocumentsError(err instanceof Error ? err.message : 'Failed to fetch documents');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchJobs = useCallback(async (params?: JobFilterParams): Promise<PaginatedProcessingJobs | undefined> => {
    setJobsLoading(true);
    setJobsError(null);
    try {
      const query = new URLSearchParams();
      query.set('page', String(params?.page || 1));
      query.set('page_size', String(params?.page_size || 50));
      if (params?.status && params.status !== 'ALL') {
        query.set('status', params.status.toLowerCase());
      }
      if (params?.stage && params.stage !== 'ALL') {
        query.set('stage', params.stage.toLowerCase());
      }
      if (params?.document_id) {
        query.set('document_id', params.document_id);
      }
      if (params?.search && params.search.trim()) {
        query.set('search', params.search.trim());
      }

      const res = await apiClient.get<PaginatedProcessingJobs>(`/documents/jobs?${query.toString()}`);
      if (res && Array.isArray(res.items)) {
        setIngestionJobs(res.items);
        setJobsTotal(res.total ?? res.items.length);
        if (res.counts) {
          setJobCounts(res.counts);
        }
      } else {
        setIngestionJobs([]);
        setJobsTotal(0);
        setJobCounts({});
      }
      return res;
    } catch (err) {
      setIngestionJobs([]);
      setJobsTotal(0);
      setJobCounts({});
      setJobsError(err instanceof Error ? err.message : 'Failed to fetch processing jobs');
      return undefined;
    } finally {
      setJobsLoading(false);
    }
  }, []);

  const documentsRef = useRef<Document[]>(documents);
  const ingestionJobsRef = useRef<ProcessingJobSummary[]>(ingestionJobs);

  useEffect(() => {
    documentsRef.current = documents;
  }, [documents]);

  useEffect(() => {
    ingestionJobsRef.current = ingestionJobs;
  }, [ingestionJobs]);

  useEffect(() => {
    let active = true;
    apiClient
      .get<PaginatedDocuments>('/documents?page=1&page_size=100')
      .then((res) => {
        if (!active) return;
        if (res && Array.isArray(res.items)) {
          setDocuments(res.items.map(mapDocumentRecord));
          setDocumentsTotal(res.total ?? res.items.length);
        } else {
          setDocuments([]);
          setDocumentsTotal(0);
        }
      })
      .catch((err) => {
        if (!active) return;
        setDocuments([]);
        setDocumentsTotal(0);
        setDocumentsError(err instanceof Error ? err.message : 'Failed to fetch documents');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    apiClient
      .get<PaginatedProcessingJobs>('/documents/jobs?page=1&page_size=50')
      .then((res) => {
        if (!active) return;
        if (res && Array.isArray(res.items)) {
          setIngestionJobs(res.items);
          setJobsTotal(res.total ?? res.items.length);
        } else {
          setIngestionJobs([]);
          setJobsTotal(0);
        }
      })
      .catch((err) => {
        if (!active) return;
        setIngestionJobs([]);
        setJobsTotal(0);
        setJobsError(err instanceof Error ? err.message : 'Failed to fetch processing jobs');
      })
      .finally(() => {
        if (active) setJobsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const getDocumentById = useCallback((id: string): Document | undefined => {
    return documentsRef.current.find((d) => d.id === id);
  }, []);

  const fetchDocumentDetail = useCallback(async (id: string): Promise<Document | undefined> => {
    try {
      const res = await apiClient.get<DocumentDetail>(`/documents/${id}`);
      if (res) {
        const mapped = mapDocumentRecord(res);
        setDocuments((prev) => {
          const idx = prev.findIndex((d) => d.id === id);
          if (idx >= 0) {
            const cur = prev[idx];
            if (cur.status === mapped.status && cur.title === mapped.title && cur.updatedAt === mapped.updatedAt) {
              return prev;
            }
            const next = [...prev];
            next[idx] = mapped;
            return next;
          }
          return [mapped, ...prev];
        });
        return mapped;
      }
      return undefined;
    } catch (err) {
      // Return local cached version if available, otherwise rethrow
      const cached = documentsRef.current.find((d) => d.id === id);
      if (cached) return cached;
      throw err;
    }
  }, []);

  const getJobById = useCallback((id: string): ProcessingJobSummary | undefined => {
    return ingestionJobsRef.current.find((j) => j.id === id);
  }, []);

  const getJobsByDocumentId = useCallback((documentId: string): ProcessingJobSummary[] => {
    return ingestionJobsRef.current.filter((j) => j.document_id === documentId);
  }, []);

  const fetchDocumentStages = useCallback(async (documentId: string): Promise<ProcessingJob[]> => {
    try {
      const res = await apiClient.get<ProcessingJob[]>(`/documents/${documentId}/jobs`);
      return Array.isArray(res) ? res : [];
    } catch {
      return [];
    }
  }, []);

  const fetchJobDetail = useCallback(async (id: string): Promise<{
    job?: ProcessingJobSummary;
    document?: Document;
    stages?: ProcessingJob[];
  }> => {
    let targetJob = getJobById(id);
    let docId = targetJob?.document_id;

    if (!targetJob) {
      try {
        const queryRes = await apiClient.get<PaginatedProcessingJobs>(`/documents/jobs?page=1&page_size=100`);
        const found = queryRes.items?.find((j) => j.id === id);
        if (found) {
          targetJob = found;
          docId = found.document_id;
        }
      } catch {
        // Continue fallback
      }
    }

    if (!docId && id.includes('-')) {
      docId = id;
    }

    let doc: Document | undefined = docId ? getDocumentById(docId) : undefined;
    if (docId && !doc) {
      try {
        doc = await fetchDocumentDetail(docId);
      } catch {
        doc = undefined;
      }
    }

    let stages: ProcessingJob[] = [];
    if (docId) {
      stages = await fetchDocumentStages(docId);
    }

    return {
      job: targetJob,
      document: doc,
      stages,
    };
  }, [getJobById, getDocumentById, fetchDocumentDetail, fetchDocumentStages]);

  const archiveDocument = useCallback(async (id: string): Promise<boolean> => {
    try {
      await apiClient.post<ArchiveDocumentResponse>(`/documents/${id}/archive`);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: 'ARCHIVED' } : d))
      );
      await fetchJobs();
      return true;
    } catch (err) {
      throw err;
    }
  }, [fetchJobs]);

  const restoreDocument = useCallback(async (id: string): Promise<{ success: boolean; status?: string; message?: string }> => {
    try {
      const res = await apiClient.post<RestoreDocumentResponse>(`/documents/${id}/restore`);
      const newStatus = mapBackendStatus(res.status);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: newStatus } : d))
      );
      await fetchJobs();
      return { success: true, status: res.status, message: res.message };
    } catch (err) {
      throw err;
    }
  }, [fetchJobs]);

  const reprocessDocument = useCallback(async (id: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const res = await apiClient.post<ReprocessResponse>(`/documents/${id}/reprocess`);
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: 'PROCESSING' } : d))
      );
      await fetchJobs();
      return { success: true, message: res.message };
    } catch (err) {
      throw err;
    }
  }, [fetchJobs]);

  const startIngestion = useCallback(async (documentId: string): Promise<boolean> => {
    try {
      await reprocessDocument(documentId);
      return true;
    } catch {
      return false;
    }
  }, [reprocessDocument]);

  const retryIngestion = useCallback(async (jobIdOrDocId: string): Promise<boolean> => {
    const job = getJobById(jobIdOrDocId);
    const targetDocId = job ? job.document_id : jobIdOrDocId;
    if (!targetDocId) return false;
    try {
      await reprocessDocument(targetDocId);
      return true;
    } catch {
      return false;
    }
  }, [getJobById, reprocessDocument]);

  const cancelIngestion = useCallback((jobId: string): boolean => {
    setIngestionJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, status: 'failed', error: 'Cancelled by operator' } : j))
    );
    return true;
  }, []);

  const uploadDocument = useCallback(async (
    file: File,
    metadata: { title: string; type: string; source?: string; source_url?: string }
  ): Promise<DocumentUploadResponse> => {
    const query = new URLSearchParams();
    query.set('title', metadata.title);
    query.set('type', metadata.type.toLowerCase());
    if (metadata.source) query.set('source', metadata.source);
    if (metadata.source_url) query.set('source_url', metadata.source_url);

    const formData = new FormData();
    formData.append('file', file);

    const res = await apiClient.upload<DocumentUploadResponse>(
      `/documents/upload?${query.toString()}`,
      formData
    );

    await fetchDocuments();
    await fetchJobs();

    return res;
  }, [fetchDocuments, fetchJobs]);

  const refreshDocuments = useCallback(async () => {
    await fetchDocuments();
  }, [fetchDocuments]);

  const refreshJobs = useCallback(async () => {
    await fetchJobs();
  }, [fetchJobs]);

  const contextValue = useMemo<DocumentStoreContextType>(() => ({
    documents,
    documentsTotal,
    isLoading,
    documentsError,
    ingestionJobs,
    jobsTotal,
    jobsLoading,
    jobsError,
    jobCounts,
    fetchDocuments,
    fetchJobs,
    getDocumentById,
    fetchDocumentDetail,
    getJobById,
    fetchJobDetail,
    getJobsByDocumentId,
    fetchDocumentStages,
    uploadDocument,
    archiveDocument,
    restoreDocument,
    reprocessDocument,
    startIngestion,
    retryIngestion,
    cancelIngestion,
    refreshDocuments,
    refreshJobs,
  }), [
    documents,
    documentsTotal,
    isLoading,
    documentsError,
    ingestionJobs,
    jobsTotal,
    jobCounts,
    jobsLoading,
    jobsError,
    fetchDocuments,
    fetchJobs,
    getDocumentById,
    fetchDocumentDetail,
    getJobById,
    fetchJobDetail,
    getJobsByDocumentId,
    fetchDocumentStages,
    uploadDocument,
    archiveDocument,
    restoreDocument,
    reprocessDocument,
    startIngestion,
    retryIngestion,
    cancelIngestion,
    refreshDocuments,
    refreshJobs,
  ]);

  return (
    <DocumentStoreContext.Provider value={contextValue}>
      {children}
    </DocumentStoreContext.Provider>
  );
};

export const useDocumentStore = () => {
  const context = useContext(DocumentStoreContext);
  if (!context) {
    throw new Error('useDocumentStore must be used within a DocumentStoreProvider');
  }
  return context;
};
