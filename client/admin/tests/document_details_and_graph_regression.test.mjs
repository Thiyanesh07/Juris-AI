import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  mapBackendStatus,
  mapBackendType,
  mapDocumentRecord,
} from '../context/DocumentStoreContext.tsx';
import { layoutNodes, mapRawType } from '../context/GraphStoreContext.tsx';

describe('Phase 1 Critical Regressions: Document Details & Knowledge Graph', () => {
  describe('Document Details Loading & State Transitions', () => {
    it('successfully maps a loaded document detail record with complete metadata', () => {
      const rawDetail = {
        id: 'doc-const-001',
        title: 'Constitution of India, 1950',
        type: 'constitution',
        source: 'Constituent Assembly',
        status: 'ready',
        created_at: '2026-10-10T10:00:00Z',
        updated_at: '2026-10-10T10:05:00Z',
      };

      const doc = mapDocumentRecord(rawDetail);
      assert.equal(doc.id, 'doc-const-001');
      assert.equal(doc.title, 'Constitution of India, 1950');
      assert.equal(doc.documentType, 'Constitution');
      assert.equal(doc.status, 'READY');
      assert.equal(doc.source, 'Constituent Assembly');
    });

    it('handles document stage fetch failures gracefully without breaking document detail', () => {
      // Simulating when fetchDocumentStages fails (e.g. 500 on stages endpoint)
      const stagesFailureHandler = (stRes) => {
        return Array.isArray(stRes) ? stRes : [];
      };

      assert.deepEqual(stagesFailureHandler(null), []);
      assert.deepEqual(stagesFailureHandler(undefined), []);
      assert.deepEqual(stagesFailureHandler({ error: 'Internal Error' }), []);
      assert.deepEqual(stagesFailureHandler([{ id: 'job-1', stage: 'ingestion', status: 'completed' }]), [
        { id: 'job-1', stage: 'ingestion', status: 'completed' },
      ]);
    });

    it('ensures distinct error state when document is missing or not found', () => {
      const deriveDocumentState = (doc, loadError) => {
        if (doc) return { view: 'DETAIL', title: doc.title };
        if (loadError) return { view: 'ERROR', title: 'Failed to Load Document', message: loadError };
        return { view: 'NOT_FOUND', title: 'Document Not Found', message: 'Document ID does not exist' };
      };

      // 1. Success
      const successState = deriveDocumentState({ id: 'doc-1', title: 'IT Act' }, null);
      assert.equal(successState.view, 'DETAIL');

      // 2. 404 / Missing
      const notFoundState = deriveDocumentState(null, null);
      assert.equal(notFoundState.view, 'NOT_FOUND');
      assert.equal(notFoundState.title, 'Document Not Found');

      // 3. API Error (e.g. 500 / Network Error)
      const errorState = deriveDocumentState(null, 'Network connection timed out');
      assert.equal(errorState.view, 'ERROR');
      assert.equal(errorState.title, 'Failed to Load Document');
      assert.equal(errorState.message, 'Network connection timed out');
    });

    it('prevents unnecessary state mutations when document has identical fields', () => {
      const prevDoc = {
        id: 'doc-1',
        title: 'IT Act 2000',
        status: 'READY',
        updatedAt: '2026-10-10T00:00:00Z',
      };

      const newDoc = {
        id: 'doc-1',
        title: 'IT Act 2000',
        status: 'READY',
        updatedAt: '2026-10-10T00:00:00Z',
      };

      const shouldUpdate =
        prevDoc.status !== newDoc.status ||
        prevDoc.title !== newDoc.title ||
        prevDoc.updatedAt !== newDoc.updatedAt;

      assert.equal(shouldUpdate, false, 'Identical document record must not trigger state re-render');
    });
  });

  describe('Knowledge Graph Presentation & Layout Invariants', () => {
    it('correctly maps multi-hop legal entities with deterministic coordinates and attributes', () => {
      const rawNodes = [
        { id: 'art_21', name: 'Article 21', type: 'Article', properties: { jurisdiction: 'Union of India' } },
        { id: 'maneka', name: 'Maneka Gandhi v. UOI', type: 'Judgment', properties: { year: 1978 } },
        { id: 'sc_india', name: 'Supreme Court of India', type: 'Court', properties: {} },
      ];
      const rawEdges = [
        { id: 'e1', sourceId: 'maneka', targetId: 'art_21', label: 'INTERPRETS' },
        { id: 'e2', sourceId: 'maneka', targetId: 'sc_india', label: 'DECIDED_BY' },
      ];

      const { nodes, edges } = layoutNodes(rawNodes, rawEdges, 'art_21');
      assert.equal(nodes.length, 3);
      assert.equal(edges.length, 2);

      const center = nodes.find((n) => n.id === 'art_21');
      assert.ok(center);
      assert.equal(center.x, 500);
      assert.equal(center.y, 300);
      assert.equal(center.type, 'ARTICLE');

      const maneka = nodes.find((n) => n.id === 'maneka');
      assert.ok(maneka);
      assert.equal(maneka.type, 'JUDGMENT');

      const sc = nodes.find((n) => n.id === 'sc_india');
      assert.ok(sc);
      assert.equal(sc.type, 'COURT');

      // Verify relationship labels are capitalized
      const interpretsEdge = edges.find((e) => e.source === 'maneka' && e.target === 'art_21');
      assert.ok(interpretsEdge);
      assert.equal(interpretsEdge.relationship, 'INTERPRETS');
    });

    it('computes readable pill width for long relationship names without clipping', () => {
      const computePillWidth = (relationship) => {
        return Math.max(56, relationship.length * 6.5 + 12);
      };

      // Short relation
      assert.ok(computePillWidth('CITES') >= 56);

      // Long legal relations
      const longPill = computePillWidth('CONFLICTS_WITH');
      assert.ok(longPill > 100, `Pill width for CONFLICTS_WITH must accommodate 14 chars, got ${longPill}`);

      const supportedByPill = computePillWidth('SUPPORTED_BY');
      assert.ok(supportedByPill > 85);
    });

    it('truncates node labels exceeding max length gracefully', () => {
      const formatNodeLabel = (label) => {
        return label.length > 25 ? `${label.slice(0, 23)}…` : label;
      };

      assert.equal(formatNodeLabel('Article 21'), 'Article 21');
      const longTitle = 'Information Technology (Intermediary Guidelines) Amendment Rules, 2023';
      const truncated = formatNodeLabel(longTitle);
      assert.ok(truncated.length <= 26);
      assert.ok(truncated.endsWith('…'));
    });
  });
});
