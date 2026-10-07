'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Document, DocumentStatus, DocumentTypeCategory, IngestionJob } from '@/lib/types';
import { INITIAL_MOCK_DOCUMENTS } from '@/data/documents';
import { INITIAL_MOCK_INGESTION_JOBS } from '@/data/ingestion';
import { apiClient } from '@/lib/apiClient';
import { PaginatedDocuments, DocumentSummary } from '@/lib/apiTypes';

interface DocumentStoreContextType {
  documents: Document[];
  ingestionJobs: IngestionJob[];
  isLoading: boolean;
  addDocument: (data: Omit<Document, 'id' | 'createdAt' | 'updatedAt' | 'status'>) => Document;
  updateDocument: (id: string, updates: Partial<Document>) => boolean;
  archiveDocument: (id: string) => boolean;
  getDocumentById: (id: string) => Document | undefined;
  startIngestion: (documentId: string) => IngestionJob | null;
  retryIngestion: (jobId: string) => boolean;
  cancelIngestion: (jobId: string) => boolean;
  getJobById: (id: string) => IngestionJob | undefined;
  getJobsByDocumentId: (documentId: string) => IngestionJob[];
  refreshDocuments: () => Promise<void>;
}

const DocumentStoreContext = createContext<DocumentStoreContextType | undefined>(undefined);

function mapBackendStatus(statusStr?: string): DocumentStatus {
  if (!statusStr) return 'READY';
  const u = statusStr.toUpperCase();
  if (u === 'READY') return 'READY';
  if (u === 'PROCESSING') return 'PROCESSING';
  if (u === 'REGISTERED' || u === 'UPLOADED') return 'UPLOADED';
  if (u === 'FAILED') return 'FAILED';
  return 'READY';
}

function mapBackendType(typeStr?: string): DocumentTypeCategory {
  if (!typeStr) return 'OTHER';
  const u = typeStr.toUpperCase();
  if (['CONSTITUTION', 'ACT', 'STATUTE', 'JUDGMENT', 'RULE', 'REGULATION'].includes(u)) {
    return u as DocumentTypeCategory;
  }
  return 'OTHER';
}

export const DocumentStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<Document[]>(INITIAL_MOCK_DOCUMENTS);
  const [ingestionJobs, setIngestionJobs] = useState<IngestionJob[]>(INITIAL_MOCK_INGESTION_JOBS);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<PaginatedDocuments>('/documents?page_size=100');
      if (res && res.items && res.items.length > 0) {
        const mappedDocs: Document[] = res.items.map((d: DocumentSummary) => ({
          id: d.id,
          title: d.title,
          fileName: `${d.title.toLowerCase().replace(/\s+/g, '_')}.pdf`,
          fileSizeBytes: 2048500,
          mimeType: 'application/pdf',
          documentType: mapBackendType(d.type),
          source: d.source || 'Parliament of India',
          uploadedBy: 'system@juris.ai',
          status: mapBackendStatus(d.status),
          authority: d.source || 'Parliament of India',
          jurisdiction: 'Union of India',
          createdAt: d.created_at || new Date().toISOString(),
          updatedAt: d.updated_at || d.created_at || new Date().toISOString(),
        }));
        setDocuments(mappedDocs);
      }
    } catch {
      // Fallback to initial documents
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const getDocumentById = (id: string): Document | undefined => {
    return documents.find((d) => d.id === id);
  };

  const getJobById = (id: string): IngestionJob | undefined => {
    return ingestionJobs.find((j) => j.id === id);
  };

  const getJobsByDocumentId = (documentId: string): IngestionJob[] => {
    return ingestionJobs.filter((j) => j.documentId === documentId);
  };

  const addDocument = (data: Omit<Document, 'id' | 'createdAt' | 'updatedAt' | 'status'>): Document => {
    const newId = `doc_${Date.now().toString().slice(-6)}`;
    const newDoc: Document = {
      ...data,
      id: newId,
      status: 'UPLOADED',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setDocuments((prev) => [newDoc, ...prev]);
    return newDoc;
  };

  const updateDocument = (id: string, updates: Partial<Document>): boolean => {
    const doc = getDocumentById(id);
    if (!doc) return false;

    setDocuments((prev) =>
      prev.map((d) => (d.id === id ? { ...d, ...updates, updatedAt: new Date().toISOString() } : d))
    );
    return true;
  };

  const archiveDocument = (id: string): boolean => {
    return updateDocument(id, { status: 'ARCHIVED' });
  };

  const startIngestion = (documentId: string): IngestionJob | null => {
    const doc = getDocumentById(documentId);
    if (!doc) return null;

    // Call real backend reprocess if UUID format
    if (documentId.includes('-')) {
      apiClient.post(`/documents/${documentId}/reprocess`).catch(() => {});
    }

    const jobId = `job_${Date.now().toString().slice(-6)}`;
    const newJob: IngestionJob = {
      id: jobId,
      documentId: doc.id,
      documentTitle: doc.title,
      status: 'PROCESSING',
      progressPercentage: 50,
      workerNode: 'backend-ingestion-worker',
      startedAt: new Date().toISOString(),
    };

    setIngestionJobs((prev) => [newJob, ...prev]);
    updateDocument(doc.id, { status: 'PROCESSING', latestJobId: jobId });
    return newJob;
  };

  const retryIngestion = (jobId: string): boolean => {
    const job = getJobById(jobId);
    if (!job) return false;
    startIngestion(job.documentId);
    return true;
  };

  const cancelIngestion = (jobId: string): boolean => {
    const job = getJobById(jobId);
    if (!job) return false;

    setIngestionJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, status: 'CANCELLED' } : j))
    );
    updateDocument(job.documentId, { status: 'FAILED' });
    return true;
  };

  return (
    <DocumentStoreContext.Provider
      value={{
        documents,
        ingestionJobs,
        isLoading,
        addDocument,
        updateDocument,
        archiveDocument,
        getDocumentById,
        startIngestion,
        retryIngestion,
        cancelIngestion,
        getJobById,
        getJobsByDocumentId,
        refreshDocuments: fetchDocuments,
      }}
    >
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

