import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  formatDate,
  formatDateTime,
  formatBytes,
  getInitials,
} from '../lib/utils.ts';

import {
  layoutNodes,
  mapRawType,
} from '../context/GraphStoreContext.tsx';

describe('Phase 5 — Admin UI Polish, Date Robustness & Layout Invariants', () => {

  describe('1. Admin Date Formatting & Edge Cases', () => {
    it('formats valid ISO dates cleanly in UTC format', () => {
      const res = formatDate('2026-10-20T14:48:37Z');
      assert.equal(res, '20 Oct 2026');
    });

    it('formats valid ISO timestamps with hour:minute and UTC indicator', () => {
      const res = formatDateTime('2026-10-20T14:48:37Z');
      assert.equal(res, '20 Oct 2026, 14:48 UTC');
    });

    it('returns honest placeholder for missing or empty date values', () => {
      assert.equal(formatDate(''), '—');
      assert.equal(formatDate(null), '—');
      assert.equal(formatDate(undefined), '—');
      assert.equal(formatDateTime(''), '—');
      assert.equal(formatDateTime(null), '—');
      assert.equal(formatDateTime(undefined), '—');
    });

    it('handles invalid date strings without throwing or returning "Invalid Date"', () => {
      assert.equal(formatDate('not-a-date'), '—');
      assert.equal(formatDate('2026-13-45T99:99:99'), '—');
      assert.equal(formatDateTime('malformed'), '—');
    });

    it('preserves input timestamp integrity without mutation', () => {
      const raw = '2026-08-15T12:00:00Z';
      const formatted = formatDate(raw);
      assert.equal(formatted, '15 Aug 2026');
      assert.equal(raw, '2026-08-15T12:00:00Z');
    });
  });

  describe('2. Byte Size & User Initials Formatting', () => {
    it('formats zero bytes honestly', () => {
      assert.equal(formatBytes(0), '0 Bytes');
    });

    it('formats bytes, kilobytes, and megabytes accurately', () => {
      assert.equal(formatBytes(512), '512 Bytes');
      assert.equal(formatBytes(1024), '1 KB');
      assert.equal(formatBytes(1048576), '1 MB');
      assert.equal(formatBytes(2621440), '2.5 MB');
    });

    it('extracts two-character initials for single or multi-word user names', () => {
      assert.equal(getInitials(''), 'JA');
      assert.equal(getInitials('Admin'), 'AD');
      assert.equal(getInitials('Super Administrator'), 'SA');
      assert.equal(getInitials('Chief Justice of India'), 'CI');
    });
  });

  describe('3. Knowledge Graph Topology & Layout Robustness', () => {
    it('handles empty graph layout gracefully', () => {
      const res = layoutNodes([], []);
      assert.deepEqual(res.nodes, []);
      assert.deepEqual(res.edges, []);
    });

    it('centers single node graph accurately when centerId is provided', () => {
      const res = layoutNodes([{ id: 'art21', label: 'Article 21', type: 'ARTICLE' }], [], 'art21');
      assert.equal(res.nodes.length, 1);
      assert.equal(res.nodes[0].id, 'art21');
      assert.equal(res.nodes[0].x, 500);
      assert.equal(res.nodes[0].y, 300);
    });

    it('assigns non-overlapping radial positions to 1-hop and 2-hop neighbors', () => {
      const rawNodes = [
        { id: 'center', label: 'Article 21', type: 'ARTICLE' },
        { id: 'hop1_a', label: 'Maneka Gandhi', type: 'JUDGMENT' },
        { id: 'hop1_b', label: 'Article 14', type: 'ARTICLE' },
        { id: 'hop2_a', label: 'Golden Triangle', type: 'DOCTRINE' },
      ];

      const rawEdges = [
        { id: 'e1', sourceId: 'center', targetId: 'hop1_a', label: 'INTERPRETS' },
        { id: 'e2', sourceId: 'center', targetId: 'hop1_b', label: 'INTERRELATES' },
        { id: 'e3', sourceId: 'hop1_b', targetId: 'hop2_a', label: 'EMBODIES' },
      ];

      const res = layoutNodes(rawNodes, rawEdges, 'center');
      assert.equal(res.nodes.length, 4);

      // Verify no duplicate positions
      const positions = new Set(res.nodes.map((n) => `${n.x},${n.y}`));
      assert.equal(positions.size, 4, 'All nodes must have unique non-overlapping positions');

      // Verify center node is at (500, 300)
      const centerNode = res.nodes.find((n) => n.id === 'center');
      assert.ok(centerNode);
      assert.equal(centerNode.x, 500);
      assert.equal(centerNode.y, 300);
    });

    it('maps legal entity types faithfully without dropping attributes', () => {
      assert.equal(mapRawType('ARTICLE'), 'ARTICLE');
      assert.equal(mapRawType('SECTION'), 'SECTION');
      assert.equal(mapRawType('JUDGMENT'), 'JUDGMENT');
      assert.equal(mapRawType('AMENDMENT'), 'AMENDMENT');
      assert.equal(mapRawType('COURT'), 'COURT');
      assert.equal(mapRawType('DOCTRINE'), 'ARTICLE');
      assert.equal(mapRawType('UNKNOWN_STATUTE'), 'ACT');
    });
  });
});
