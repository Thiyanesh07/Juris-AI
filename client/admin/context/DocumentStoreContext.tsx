'use client';

import React, { createContext, useContext, useState } from 'react';
import { Document, DocumentStatus, DocumentTypeCategory, IngestionJob, IngestionJobStatus } from '@/lib/types';
import { INITIAL_MOCK_DOCUMENTS } from '@/data/documents';
import { INITIAL_MOCK_INGESTION_JOBS } from '@/data/ingestion';

interface DocumentStoreContextType {
  documents: Document[];
  ingestionJobs: IngestionJob[];
  addDocument: (data: Omit<Document, 'id' | 'createdAt' | 'updatedAt' | 'status'>) => Document;
  updateDocument: (id: string, updates: Partial<Document>) => boolean;
  archiveDocument: (id: string) => boolean;
  getDocumentById: (id: string) => Document | undefined;
  startIngestion: (documentId: string) => IngestionJob | null;
  retryIngestion: (jobId: string) => boolean;
  cancelIngestion: (jobId: string) => boolean;
  getJobById: (id: string) => IngestionJob | undefined;
  getJobsByDocumentId: (documentId: string) => IngestionJob[];
}

const DocumentStoreContext = createContext<DocumentStoreContextType | undefined>(undefined);

export const DocumentStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<Document[]>(INITIAL_MOCK_DOCUMENTS);
  const [ingestionJobs, setIngestionJobs] = useState<IngestionJob[]>(INITIAL_MOCK_INGESTION_JOBS);

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

    const jobId = `job_${Date.now().toString().slice(-6)}`;
    const workerNodes = ['worker-01', 'worker-02', 'worker-03', 'worker-04'];
    const assignedWorker = workerNodes[Math.floor(Math.random() * workerNodes.length)];

    const newJob: IngestionJob = {
      id: jobId,
      documentId: doc.id,
      documentTitle: doc.title,
      status: 'QUEUED',
      progressPercentage: 0,
      workerNode: assignedWorker,
      startedAt: new Date().toISOString(),
    };

    setIngestionJobs((prev) => [newJob, ...prev]);
    updateDocument(doc.id, { status: 'PROCESSING', latestJobId: jobId });

    // Frontend transition simulation: QUEUED -> PARSING -> EXTRACTING_ENTITIES -> COMPLETED
    setTimeout(() => {
      setIngestionJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: 'PARSING', progressPercentage: 30 } : j))
      );
    }, 800);

    setTimeout(() => {
      setIngestionJobs((prev) =>
        prev.map((j) =>
          j.id === jobId ? { ...j, status: 'EXTRACTING_ENTITIES', progressPercentage: 70 } : j
        )
      );
    }, 1800);

    setTimeout(() => {
      const completedTime = new Date().toISOString();
      setIngestionJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? {
                ...j,
                status: 'COMPLETED',
                progressPercentage: 100,
                completedAt: completedTime,
                chunksCount: Math.floor(Math.random() * 400) + 150,
                entitiesExtractedCount: Math.floor(Math.random() * 1200) + 400,
                relationshipsExtractedCount: Math.floor(Math.random() * 3000) + 1000,
              }
            : j
        )
      );
      updateDocument(doc.id, { status: 'READY' });
    }, 3200);

    return newJob;
  };

  const retryIngestion = (jobId: string): boolean => {
    const job = getJobById(jobId);
    if (!job) return false;

    setIngestionJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? {
              ...j,
              status: 'QUEUED',
              progressPercentage: 10,
              errorMessage: undefined,
              startedAt: new Date().toISOString(),
            }
          : j
      )
    );
    updateDocument(job.documentId, { status: 'PROCESSING' });

    setTimeout(() => {
      setIngestionJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? {
                ...j,
                status: 'COMPLETED',
                progressPercentage: 100,
                completedAt: new Date().toISOString(),
                chunksCount: 520,
                entitiesExtractedCount: 1480,
                relationshipsExtractedCount: 3200,
              }
            : j
        )
      );
      updateDocument(job.documentId, { status: 'READY' });
    }, 2000);

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
        addDocument,
        updateDocument,
        archiveDocument,
        getDocumentById,
        startIngestion,
        retryIngestion,
        cancelIngestion,
        getJobById,
        getJobsByDocumentId,
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
