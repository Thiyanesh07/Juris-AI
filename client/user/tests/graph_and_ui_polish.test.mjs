import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  formatDate,
  formatDateTime,
  truncate,
} from '../lib/utils.ts';

import {
  formatNodeDisplayLabel,
  calculateGraphBounds,
  calculateFitToView,
  layoutGraphNodes,
} from '../lib/graphLayout.ts';

import {
  normalizeGraphNodes,
  normalizeGraphEdges,
} from '../lib/normalizeQA.ts';

describe('Phase 5 — Knowledge Graph Layout & UI Polish Verification', () => {

  describe('1. Date Formatting & Robustness', () => {
    it('formats valid ISO dates cleanly and consistently in UTC', () => {
      const res = formatDate('2026-10-20T09:18:37Z');
      assert.equal(res, '20 Oct 2026');
    });

    it('formats date and time with UTC marker', () => {
      const res = formatDateTime('2026-10-20T09:18:37Z');
      assert.equal(res, '20 Oct 2026, 09:18 UTC');
    });

    it('returns honest placeholder for null, undefined, or empty date string', () => {
      assert.equal(formatDate(''), '—');
      assert.equal(formatDate(null), '—');
      assert.equal(formatDate(undefined), '—');
      assert.equal(formatDateTime(''), '—');
      assert.equal(formatDateTime(null), '—');
      assert.equal(formatDateTime(undefined), '—');
    });

    it('handles malformed date strings without crashing or returning "Invalid Date"', () => {
      assert.equal(formatDate('not-a-real-date'), '—');
      assert.equal(formatDate('2026-99-99T99:99:99'), '—');
      assert.equal(formatDateTime('corrupted-timestamp'), '—');
    });

    it('does not mutate or alter the original date input string', () => {
      const original = '2026-01-26T00:00:00Z';
      const formatted = formatDate(original);
      assert.equal(formatted, '26 Jan 2026');
      assert.equal(original, '26 Jan 2026T00:00:00Z'.length > 0 ? '2026-01-26T00:00:00Z' : original);
    });
  });

  describe('2. Node Label Density & Formatting', () => {
    it('preserves short legal labels without modification', () => {
      const label = 'Article 21';
      const res = formatNodeDisplayLabel(label, 20);
      assert.equal(res.displayLabel, 'Article 21');
      assert.equal(res.fullLabel, 'Article 21');
      assert.equal(res.isTruncated, false);
    });

    it('abbreviates long constitutional article titles to short form', () => {
      const label = 'Constitution of India, Article 21 (Protection of Life)';
      const res = formatNodeDisplayLabel(label, 20);
      assert.equal(res.displayLabel, 'Art. 21');
      assert.equal(res.fullLabel, label);
      assert.equal(res.isTruncated, true);
    });

    it('abbreviates case citations cleanly while preserving the lead petitioner', () => {
      const label = 'Kesavananda Bharati Sripadagalvaru v. State of Kerala (1973)';
      const res = formatNodeDisplayLabel(label, 24);
      assert.match(res.displayLabel, /v\.\s+…$/);
      assert.equal(res.fullLabel, label);
      assert.equal(res.isTruncated, true);
    });

    it('truncates generic long statutory labels with an ellipsis', () => {
      const label = 'The Representation of the People (Amendment) Act, 1966';
      const res = formatNodeDisplayLabel(label, 20);
      assert.ok(res.displayLabel.length <= 20);
      assert.ok(res.displayLabel.endsWith('…'));
      assert.equal(res.fullLabel, label);
      assert.equal(res.isTruncated, true);
    });
  });

  describe('3. Graph Bounding Box & Fit-to-View', () => {
    it('returns sensible default bounds for empty node array', () => {
      const bounds = calculateGraphBounds([]);
      assert.equal(bounds.width, 1000);
      assert.equal(bounds.height, 600);
      assert.equal(bounds.centerX, 500);
      assert.equal(bounds.centerY, 300);
    });

    it('accurately calculates bounding box across diverse node coordinates', () => {
      const testNodes = [
        { id: '1', label: 'A', type: 'ACT', x: 200, y: 150 },
        { id: '2', label: 'B', type: 'SECTION', x: 600, y: 450 },
      ];
      const margin = 50;
      const bounds = calculateGraphBounds(testNodes, margin);

      assert.equal(bounds.minX, 200 - margin);
      assert.equal(bounds.maxX, 600 + margin);
      assert.equal(bounds.minY, 150 - margin);
      assert.equal(bounds.maxY, 450 + margin);
      assert.equal(bounds.width, 500);
      assert.equal(bounds.height, 400);
      assert.equal(bounds.centerX, 400);
      assert.equal(bounds.centerY, 300);
    });

    it('computes fit-to-view zoom and pan offsets clamped within sensible bounds', () => {
      const bounds = {
        minX: 100,
        minY: 100,
        maxX: 900,
        maxY: 500,
        width: 800,
        height: 400,
        centerX: 500,
        centerY: 300,
      };

      const fit = calculateFitToView(bounds, 800, 440, 0.45, 1.4);
      assert.ok(fit.zoom >= 0.45 && fit.zoom <= 1.4);
      assert.equal(typeof fit.panX, 'number');
      assert.equal(typeof fit.panY, 'number');
      assert.ok(!isNaN(fit.panX));
      assert.ok(!isNaN(fit.panY));
    });
  });

  describe('4. Deterministic Collision-Free Graph Layout', () => {
    it('handles empty graph state without error', () => {
      const layout = layoutGraphNodes([], []);
      assert.deepEqual(layout, []);
    });

    it('centers single-node graph accurately', () => {
      const single = [{ id: 'n1', label: 'Constitution', type: 'ACT', x: 0, y: 0 }];
      const layout = layoutGraphNodes(single, [], 1000, 600);
      assert.equal(layout.length, 1);
      assert.equal(layout[0].x, 500);
      assert.equal(layout[0].y, 300);
    });

    it('arranges multi-hop nodes in concentric rings around seed/query without overlap', () => {
      const nodes = [
        { id: 'query_seed', label: 'Query', type: 'QUERY', isQuery: true, x: 0, y: 0 },
        { id: 'art21', label: 'Article 21', type: 'ARTICLE', isSeed: true, x: 0, y: 0 },
        { id: 'case_maneka', label: 'Maneka Gandhi', type: 'JUDGMENT', x: 0, y: 0 },
        { id: 'art14', label: 'Article 14', type: 'ARTICLE', x: 0, y: 0 },
        { id: 'bns_sec', label: 'Section 103 BNS', type: 'SECTION', x: 0, y: 0 },
      ];

      const edges = [
        { id: 'e1', sourceId: 'query_seed', targetId: 'art21', label: 'GROUNDED_IN' },
        { id: 'e2', sourceId: 'art21', targetId: 'case_maneka', label: 'INTERPRETED_BY' },
        { id: 'e3', sourceId: 'art21', targetId: 'art14', label: 'INTERRELATES_WITH' },
        { id: 'e4', sourceId: 'case_maneka', targetId: 'bns_sec', label: 'CITES' },
      ];

      const layout = layoutGraphNodes(nodes, edges, 1000, 600);
      assert.equal(layout.length, 5);

      // Verify no two nodes share the same (x, y) coordinate
      const coordSet = new Set();
      for (const n of layout) {
        const key = `${n.x},${n.y}`;
        assert.ok(!coordSet.has(key), `Collision detected at coordinate: ${key} for node ${n.id}`);
        coordSet.add(key);
      }

      // Center query seed at canvas center
      const center = layout.find((n) => n.id === 'query_seed');
      assert.ok(center);
      assert.equal(center.x, 500);
      assert.equal(center.y, 300);

      // Verify distance from center is non-zero for all connected nodes
      for (const n of layout) {
        if (n.id === 'query_seed') continue;
        const dx = n.x - 500;
        const dy = n.y - 300;
        const dist = Math.sqrt(dx * dx + dy * dy);
        assert.ok(dist >= 140, `Node ${n.id} too close to center (${dist}px)`);
      }
    });

    it('handles disconnected nodes in separate perimeter ring without overlapping connected subgraph', () => {
      const nodes = [
        { id: 'seed', label: 'Constitution', type: 'ACT', isSeed: true, x: 0, y: 0 },
        { id: 'connected', label: 'Article 21', type: 'ARTICLE', x: 0, y: 0 },
        { id: 'disconnected_1', label: 'Unlinked Statute', type: 'ACT', x: 0, y: 0 },
        { id: 'disconnected_2', label: 'Independent Rule', type: 'RULE', x: 0, y: 0 },
      ];

      const edges = [
        { id: 'e1', sourceId: 'seed', targetId: 'connected', label: 'EMBODIES' },
      ];

      const layout = layoutGraphNodes(nodes, edges, 1000, 600);
      assert.equal(layout.length, 4);

      const coordSet = new Set(layout.map((n) => `${n.x},${n.y}`));
      assert.equal(coordSet.size, 4, 'All nodes must have unique non-overlapping coordinates');
    });

    it('dynamically expands layout radius for large graphs (12+ nodes) to prevent angular crowding', () => {
      const nodes = Array.from({ length: 14 }, (_, i) => ({
        id: `node_${i}`,
        label: `Legal Entity ${i}`,
        type: i === 0 ? 'QUERY' : i % 2 === 0 ? 'ARTICLE' : 'JUDGMENT',
        isQuery: i === 0,
        x: 0,
        y: 0,
      }));

      const edges = nodes.slice(1).map((n, i) => ({
        id: `e_${i}`,
        sourceId: 'node_0',
        targetId: n.id,
        label: 'REFERENCES',
      }));

      const layout = layoutGraphNodes(nodes, edges, 1000, 600);
      assert.equal(layout.length, 14);

      const coordSet = new Set(layout.map((n) => `${n.x},${n.y}`));
      assert.equal(coordSet.size, 14, 'Every node in large graph must have distinct position');

      // Check distance between any two adjacent nodes is at least 40px
      for (let i = 1; i < layout.length; i++) {
        for (let j = i + 1; j < layout.length; j++) {
          const dx = layout[i].x - layout[j].x;
          const dy = layout[i].y - layout[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          assert.ok(dist >= 40, `Nodes ${layout[i].id} and ${layout[j].id} are too close (${dist}px)`);
        }
      }
    });
  });

  describe('5. Normalization Integration & Graph Faithfulness', () => {
    it('accurately normalizes raw backend nodes with legal entity types', () => {
      const rawNodes = [
        { id: 'art_21', label: 'Article 21', type: 'ARTICLE', isSeed: true },
        { id: 'sec_302', label: 'Section 302', type: 'SECTION' },
        { id: 'case_k', label: 'Kesavananda Bharati', type: 'JUDGMENT' },
        { id: 'amend_44', label: '44th Amendment', type: 'AMENDMENT' },
      ];

      const nodes = normalizeGraphNodes(rawNodes);
      assert.equal(nodes.length, 4);
      assert.equal(nodes[0].type, 'ARTICLE');
      assert.equal(nodes[1].type, 'SECTION');
      assert.equal(nodes[2].type, 'JUDGMENT');
      assert.equal(nodes[3].type, 'AMENDMENT');
      assert.ok(nodes[0].isSeed);
    });

    it('faithfully preserves edge provenance and typed relationships without inventing edges', () => {
      const rawEdges = [
        { id: 'e1', source_id: 'art_21', target_id: 'case_k', label: 'INTERPRETED_BY' },
        { id: 'e2', source: 'sec_302', target: 'amend_44', relationship: 'AMENDED_BY' },
      ];

      const edges = normalizeGraphEdges(rawEdges);
      assert.equal(edges.length, 2);
      assert.equal(edges[0].sourceId, 'art_21');
      assert.equal(edges[0].targetId, 'case_k');
      assert.equal(edges[0].label, 'INTERPRETED_BY');
      assert.equal(edges[1].sourceId, 'sec_302');
      assert.equal(edges[1].targetId, 'amend_44');
      assert.equal(edges[1].label, 'AMENDED_BY');
    });

    it('safely handles missing or corrupt node attributes with sensible fallbacks', () => {
      const corruptNodes = [
        { id: 'bad_1', label: '', type: 'UNKNOWN_TYPE' },
        { id: 'bad_2', label: '550e8400-e29b-41d4-a716-446655440000', type: 'ARTICLE' },
      ];

      const nodes = normalizeGraphNodes(corruptNodes);
      assert.equal(nodes.length, 2);
      assert.equal(nodes[0].label, 'Legal Authority');
      assert.equal(nodes[1].label, 'Constitutional Article');
      assert.ok(!isNaN(nodes[0].x));
      assert.ok(!isNaN(nodes[0].y));
    });
  });
});
