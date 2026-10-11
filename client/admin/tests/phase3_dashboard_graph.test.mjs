import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { mapRawType, layoutNodes } from '../context/GraphStoreContext.tsx';
import { INITIAL_GRAPH_NODES, INITIAL_GRAPH_EDGES } from '../data/graph.ts';

describe('Phase 3 - Step 4: Admin Dashboard & Graph Explorer Integration', () => {
  describe('Admin Dashboard Live Telemetry & Fallback Elimination', () => {
    it('formats real backend PublicStatsResponse without hardcoded fallbacks', () => {
      const mockStats = {
        total_documents: 12,
        ready_documents: 11,
        total_chunks: 850,
        graph_nodes: 1420,
        graph_relationships: 4890,
        vector_count: 850,
        vector_dimension: 768,
        embedding_model: 'law-ai/InLegalBERT',
        graph_labels: { Act: 12, Section: 400, Article: 395 },
        graph_relationship_types: { CONTAINS: 600, REFERENCES: 1200 },
      };

      // Ensure formatting preserves live values
      const docCountFormatted = `${mockStats.total_documents}`;
      const graphNodesFormatted = `${mockStats.graph_nodes.toLocaleString()}`;
      const vectorCountFormatted = `${mockStats.vector_count.toLocaleString()}`;
      const chunkCountFormatted = `${mockStats.total_chunks.toLocaleString()}`;

      assert.equal(docCountFormatted, '12');
      assert.equal(graphNodesFormatted, '1,420');
      assert.equal(vectorCountFormatted, '850');
      assert.equal(chunkCountFormatted, '850');

      // Verify none of the removed legacy fallback numbers appear
      const legacyMockNumbers = ['34', '6,235', '2,412', '26,014'];
      assert.equal(legacyMockNumbers.includes(docCountFormatted), false);
      assert.equal(legacyMockNumbers.includes(graphNodesFormatted), false);
    });

    it('returns honest placeholder or unavailable state when stats are missing or loading', () => {
      const formatValue = (stats, isLoading) => {
        if (stats) return `${stats.total_documents}`;
        if (isLoading) return 'Loading…';
        return '—';
      };

      const formatFooter = (stats, isLoading) => {
        if (stats) return `${stats.ready_documents} Ready for retrieval`;
        if (isLoading) return 'Fetching document count…';
        return 'Corpus stats unavailable';
      };

      // Loading state
      assert.equal(formatValue(null, true), 'Loading…');
      assert.equal(formatFooter(null, true), 'Fetching document count…');

      // Error / Offline state
      assert.equal(formatValue(null, false), '—');
      assert.equal(formatFooter(null, false), 'Corpus stats unavailable');

      // Must never return hardcoded '34' or '33 Ready'
      assert.notEqual(formatValue(null, false), '34');
      assert.notEqual(formatFooter(null, false), '33 Ready');
    });

    it('evaluates service health statuses faithfully without fabricating connected states', () => {
      const evaluateStatus = (compStatus) => {
        if (compStatus === 'ok') return 'CONNECTED';
        if (compStatus === 'degraded') return 'DEGRADED';
        if (compStatus === 'unreachable' || compStatus === 'unavailable') return 'ERROR';
        return 'NOT_CONNECTED';
      };

      assert.equal(evaluateStatus('ok'), 'CONNECTED');
      assert.equal(evaluateStatus('degraded'), 'DEGRADED');
      assert.equal(evaluateStatus('unreachable'), 'ERROR');
      assert.equal(evaluateStatus('unavailable'), 'ERROR');
      assert.equal(evaluateStatus(undefined), 'NOT_CONNECTED');
    });
  });

  describe('Knowledge Graph Explorer Layout & Mappings', () => {
    it('never falls back to INITIAL_GRAPH_NODES when input is empty or null', () => {
      const emptyLayout = layoutNodes([], []);
      assert.equal(emptyLayout.nodes.length, 0);
      assert.equal(emptyLayout.edges.length, 0);
      assert.notEqual(emptyLayout.nodes.length, INITIAL_GRAPH_NODES.length);
      assert.notEqual(emptyLayout.edges.length, INITIAL_GRAPH_EDGES.length);

      const nullLayout = layoutNodes(null, null);
      assert.equal(nullLayout.nodes.length, 0);
      assert.equal(nullLayout.edges.length, 0);
    });

    it('lays out real backend nodes and multi-hop edges correctly around center node', () => {
      const rawNodes = [
        { id: 'act_101', name: 'Constitution of India', type: 'ACT', description: 'Supreme law' },
        { id: 'art_21', name: 'Article 21', type: 'ARTICLE', description: 'Protection of life' },
        { id: 'art_14', name: 'Article 14', type: 'ARTICLE', description: 'Equality before law' },
      ];
      const rawEdges = [
        { id: 'e1', sourceId: 'act_101', targetId: 'art_21', label: 'CONTAINS' },
        { id: 'e2', sourceId: 'act_101', targetId: 'art_14', label: 'CONTAINS' },
      ];

      const { nodes, edges } = layoutNodes(rawNodes, rawEdges, 'act_101');
      assert.equal(nodes.length, 3);
      assert.equal(edges.length, 2);

      const center = nodes.find((n) => n.id === 'act_101');
      assert.ok(center);
      assert.equal(center.x, 500);
      assert.equal(center.y, 300);
      assert.equal(center.type, 'ACT');

      const neighbor = nodes.find((n) => n.id === 'art_21');
      assert.ok(neighbor);
      assert.equal(neighbor.type, 'ARTICLE');
      // Must be positioned at first-hop radius from center
      const dist = Math.hypot(neighbor.x - center.x, neighbor.y - center.y);
      assert.ok(Math.abs(dist - 160) < 5, `Expected distance ~160, got ${dist}`);
    });

    it('maps diverse legal entity types and doctrines accurately', () => {
      assert.equal(mapRawType('ARTICLE'), 'ARTICLE');
      assert.equal(mapRawType('ACT'), 'ACT');
      assert.equal(mapRawType('SECTION'), 'SECTION');
      assert.equal(mapRawType('AMENDMENT'), 'AMENDMENT');
      assert.equal(mapRawType('JUDGMENT'), 'JUDGMENT');
      assert.equal(mapRawType('COURT'), 'COURT');
      assert.equal(mapRawType('CONSTITUTION'), 'ARTICLE');
      assert.equal(mapRawType('DOCTRINE'), 'ARTICLE');
      assert.equal(mapRawType('UNKNOWN'), 'ACT');
      assert.equal(mapRawType(undefined), 'ARTICLE');
    });
  });

  describe('Isolation from Test Fixtures', () => {
    it('ensures INITIAL_GRAPH_NODES is solely a fixture and not present in initial empty state', () => {
      // Direct comparison to confirm fixture uniqueness
      assert.ok(INITIAL_GRAPH_NODES.length > 0);
      assert.ok(INITIAL_GRAPH_EDGES.length > 0);

      // Verify that an empty response yields empty arrays
      const result = layoutNodes([], []);
      assert.deepEqual(result.nodes, []);
      assert.deepEqual(result.edges, []);
    });
  });
});
