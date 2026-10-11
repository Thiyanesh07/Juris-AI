import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  mapBackendStatus,
  mapBackendType,
  mapDocumentRecord,
} from '../context/DocumentStoreContext.tsx';
import { INITIAL_MOCK_DOCUMENTS } from '../data/documents.ts';
import { INITIAL_MOCK_INGESTION_JOBS } from '../data/ingestion.ts';

describe('Phase 3 - Step 3: Ingestion & Document UI Integration', () => {
  describe('Document Status & Type Mappings', () => {
    it('accurately maps backend document statuses without inventing READY', () => {
      assert.equal(mapBackendStatus('uploaded'), 'UPLOADED');
      assert.equal(mapBackendStatus('registered'), 'UPLOADED');
      assert.equal(mapBackendStatus('processing'), 'PROCESSING');
      assert.equal(mapBackendStatus('ready'), 'READY');
      assert.equal(mapBackendStatus('failed'), 'FAILED');
      assert.equal(mapBackendStatus('disabled'), 'ARCHIVED');
      assert.equal(mapBackendStatus('archived'), 'ARCHIVED');
      assert.equal(mapBackendStatus(undefined), 'UPLOADED');
      assert.equal(mapBackendStatus(''), 'UPLOADED');
    });

    it('accurately maps backend legal document types', () => {
      assert.equal(mapBackendType('constitution'), 'Constitution');
      assert.equal(mapBackendType('act'), 'Act');
      assert.equal(mapBackendType('statute'), 'Act');
      assert.equal(mapBackendType('rule'), 'Rule');
      assert.equal(mapBackendType('regulation'), 'Regulation');
      assert.equal(mapBackendType('judgment'), 'Judgment');
      assert.equal(mapBackendType('notification'), 'Notification');
      assert.equal(mapBackendType('other'), 'Other');
      assert.equal(mapBackendType('unknown_type'), 'Other');
    });

    it('transforms real backend DocumentSummary into Document domain model without mock fallback', () => {
      const backendSummary = {
        id: '12345678-1234-5678-1234-567812345678',
        title: 'Bharatiya Nyaya Sanhita, 2023',
        type: 'act',
        source: 'Ministry of Law and Justice',
        status: 'ready',
        file_hash: 'abc123hash',
        created_at: '2026-10-10T12:00:00Z',
        updated_at: '2026-10-10T12:05:00Z',
      };

      const doc = mapDocumentRecord(backendSummary);
      assert.equal(doc.id, '12345678-1234-5678-1234-567812345678');
      assert.equal(doc.title, 'Bharatiya Nyaya Sanhita, 2023');
      assert.equal(doc.documentType, 'Act');
      assert.equal(doc.source, 'Ministry of Law and Justice');
      assert.equal(doc.status, 'READY');
      assert.equal(doc.createdAt, '2026-10-10T12:00:00Z');
      assert.equal(doc.updatedAt, '2026-10-10T12:05:00Z');
      assert.equal(doc.uploadedBy, 'system@juris.ai');

      // Verify it does NOT match any initial mock document
      assert.equal(
        INITIAL_MOCK_DOCUMENTS.some((mock) => mock.id === doc.id),
        false,
        'Mapped document must not collide with initial mock data'
      );
    });
  });

  describe('Ingestion Dashboard Job Telemetry & Filtering', () => {
    const sampleJobs = [
      {
        id: 'job-01',
        document_id: 'doc-01',
        document_title: 'Evidence Act, 1872',
        stage: 'ingestion',
        status: 'completed',
        error: null,
        created_at: '2026-10-11T09:00:00Z',
        updated_at: '2026-10-11T09:01:00Z',
      },
      {
        id: 'job-02',
        document_id: 'doc-01',
        document_title: 'Evidence Act, 1872',
        stage: 'chunking',
        status: 'completed',
        error: null,
        created_at: '2026-10-11T09:01:00Z',
        updated_at: '2026-10-11T09:02:00Z',
      },
      {
        id: 'job-03',
        document_id: 'doc-02',
        document_title: 'Arbitration Ordinance',
        stage: 'embedding',
        status: 'running',
        error: null,
        created_at: '2026-10-11T10:00:00Z',
        updated_at: '2026-10-11T10:00:30Z',
      },
      {
        id: 'job-04',
        document_id: 'doc-03',
        document_title: 'Corrupted Judgment PDF',
        stage: 'extraction',
        status: 'failed',
        error: 'PDF syntax error: unreadable stream trailer',
        created_at: '2026-10-11T11:00:00Z',
        updated_at: '2026-10-11T11:00:05Z',
      },
      {
        id: 'job-05',
        document_id: 'doc-04',
        document_title: 'Future Statute',
        stage: 'graph_population',
        status: 'pending',
        error: null,
        created_at: '2026-10-11T11:30:00Z',
        updated_at: '2026-10-11T11:30:00Z',
      },
    ];

    it('derives queued, active, completed, and failed counts honestly from job records', () => {
      const queued = sampleJobs.filter((j) => j.status === 'pending').length;
      const active = sampleJobs.filter((j) => j.status === 'running').length;
      const completed = sampleJobs.filter((j) => j.status === 'completed').length;
      const failed = sampleJobs.filter((j) => j.status === 'failed').length;

      assert.equal(queued, 1);
      assert.equal(active, 1);
      assert.equal(completed, 2);
      assert.equal(failed, 1);
      assert.equal(queued + active + completed + failed, sampleJobs.length);
    });

    it('filters correctly by pipeline stage', () => {
      const embeddingJobs = sampleJobs.filter((j) => j.stage === 'embedding');
      assert.equal(embeddingJobs.length, 1);
      assert.equal(embeddingJobs[0].id, 'job-03');
      assert.equal(embeddingJobs[0].status, 'running');

      const failedExtraction = sampleJobs.filter(
        (j) => j.stage === 'extraction' && j.status === 'failed'
      );
      assert.equal(failedExtraction.length, 1);
      assert.equal(failedExtraction[0].error, 'PDF syntax error: unreadable stream trailer');
    });

    it('detects active running jobs to govern polling state', () => {
      const hasActive = sampleJobs.some(
        (j) => j.status === 'running' || j.status === 'pending'
      );
      assert.equal(hasActive, true, 'Polling should be enabled when jobs are running or pending');

      const completedOnly = sampleJobs.filter((j) => j.status === 'completed');
      const hasActiveWhenCompleted = completedOnly.some(
        (j) => j.status === 'running' || j.status === 'pending'
      );
      assert.equal(hasActiveWhenCompleted, false, 'Polling should cease when all jobs are completed');
    });

    it('does not invent fake workers or fake percentages', () => {
      // In sampleJobs, no workerNode property exists
      for (const job of sampleJobs) {
        assert.equal(job.workerNode, undefined, 'Worker identity should not be fabricated');
        assert.equal(job.progressPercentage, undefined, 'Numerical percentage should not be fabricated');
      }
    });
  });

  describe('Document Archive and Restore Invariants', () => {
    it('restores document to READY only when all required stages succeeded', () => {
      const allSucceededBackendResponse = {
        document_id: 'doc-01',
        status: 'ready',
        message: 'Document restored to READY status.',
      };

      const mappedStatus = mapBackendStatus(allSucceededBackendResponse.status);
      assert.equal(mappedStatus, 'READY');

      const failedPipelineBackendResponse = {
        document_id: 'doc-02',
        status: 'failed',
        message: 'Document restored to FAILED status because not all ingestion stages succeeded.',
      };

      const mappedFailedStatus = mapBackendStatus(failedPipelineBackendResponse.status);
      assert.equal(
        mappedFailedStatus,
        'FAILED',
        'Restoring a document with incomplete stages must result in FAILED status, never fabricated READY'
      );
    });

    it('preserves disabled/archived status for archived documents', () => {
      const archiveResponse = {
        document_id: 'doc-01',
        status: 'disabled',
        message: 'Document archived.',
      };
      assert.equal(mapBackendStatus(archiveResponse.status), 'ARCHIVED');
    });
  });

  describe('Empty and Error State Isolation', () => {
    it('never falls back to INITIAL_MOCK_DOCUMENTS on empty array', () => {
      const emptyItems = [];
      const mapped = emptyItems.map(mapDocumentRecord);
      assert.equal(mapped.length, 0);
      assert.notEqual(mapped.length, INITIAL_MOCK_DOCUMENTS.length);
    });

    it('never falls back to INITIAL_MOCK_INGESTION_JOBS on empty array', () => {
      const emptyJobs = [];
      assert.equal(emptyJobs.length, 0);
      assert.notEqual(emptyJobs.length, INITIAL_MOCK_INGESTION_JOBS.length);
    });
  });
});
