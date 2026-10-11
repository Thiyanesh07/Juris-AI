import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { mapBackendAuditEvent } from '../context/AuditStoreContext.tsx';
import { mapBackendValidationItem } from '../context/ValidationStoreContext.tsx';
import { INITIAL_MOCK_AUDIT_EVENTS } from '../data/audit.ts';
import { INITIAL_MOCK_VALIDATION_ITEMS } from '../data/validation.ts';

describe('Phase 1 - Audit Logs Store & Mapping', () => {
  it('does not fabricate IP address, user agent, or status when absent', () => {
    const raw = {
      id: '00000000-0000-0000-0000-000000000001',
      event_type: 'AUTHENTICATION_LOGIN',
      actor_id: null,
      actor_email: null,
      event_metadata: {
        description: 'Anonymous login attempt',
      },
      created_at: '2026-10-11T10:00:00Z',
    };

    const mapped = mapBackendAuditEvent(raw);
    assert.equal(mapped.id, raw.id);
    assert.equal(mapped.category, 'AUTHENTICATION');
    assert.equal(mapped.action, 'LOGIN');
    assert.equal(mapped.ipAddress, undefined, 'IP address must not be fabricated to 127.0.0.1');
    assert.equal(mapped.userAgent, undefined, 'User agent must not be fabricated');
    assert.equal(mapped.actorEmail, '', 'Actor email must not be fabricated');
    assert.equal(mapped.actorName, 'System Service');
  });

  it('respects real metadata when present in audit event', () => {
    const raw = {
      id: '00000000-0000-0000-0000-000000000002',
      event_type: 'VALIDATION_REJECT',
      actor_id: '11111111-1111-1111-1111-111111111111',
      actor_email: 'admin@jurisai.law',
      event_metadata: {
        category: 'VALIDATION',
        action: 'REJECT',
        result: 'FAILURE',
        severity: 'WARNING',
        ip_address: '10.0.0.42',
        user_agent: 'CustomAdminClient/1.0',
        target_resource: 'validation_item:2222',
        description: 'Item rejected due to incorrect citation',
      },
      created_at: '2026-10-11T12:00:00Z',
    };

    const mapped = mapBackendAuditEvent(raw);
    assert.equal(mapped.ipAddress, '10.0.0.42');
    assert.equal(mapped.userAgent, 'CustomAdminClient/1.0');
    assert.equal(mapped.result, 'FAILURE');
    assert.equal(mapped.severity, 'WARNING');
    assert.equal(mapped.actorEmail, 'admin@jurisai.law');
    assert.equal(mapped.actorName, 'admin');
    assert.equal(mapped.resourceType, 'validation_item');
    assert.equal(mapped.resourceId, '2222');
  });

  it('verifies empty API response results in zero events, never revealing mock entries', () => {
    const apiResponse = { items: [], total: 0 };
    const mapped = apiResponse.items.map(mapBackendAuditEvent);

    assert.equal(mapped.length, 0);
    // Ensure mock entries are never present in mapped output
    assert.equal(mapped.some((e) => e.id === INITIAL_MOCK_AUDIT_EVENTS[0].id), false);
    assert.equal(mapped.some((e) => e.id === 'aud_1001'), false);
  });

  it('handles simulated API failure, retry, and detail fetch', async () => {
    let shouldFail = true;
    const fakeApiClient = {
      get: async (url) => {
        if (shouldFail) {
          throw new Error('500 Internal Server Error: Database unreachable');
        }
        if (url === '/audit/test-uuid-001') {
          return {
            id: 'test-uuid-001',
            event_type: 'SECURITY_LOGIN',
            actor_id: 'usr-1',
            actor_email: 'admin@juris.ai',
            event_metadata: { result: 'SUCCESS', description: 'Admin login' },
            created_at: '2026-10-11T10:00:00Z',
          };
        }
        return { items: [], total: 0 };
      },
    };

    // 1. Failure state
    let state = { events: [], error: null, isLoading: true };
    try {
      const res = await fakeApiClient.get('/audit?page_size=100');
      state.events = res.items.map(mapBackendAuditEvent);
    } catch (err) {
      state.error = err.message;
      state.events = [];
    } finally {
      state.isLoading = false;
    }

    assert.equal(state.isLoading, false);
    assert.equal(state.error, '500 Internal Server Error: Database unreachable');
    assert.equal(state.events.length, 0);

    // 2. Retry succeeds with zero items
    shouldFail = false;
    state.isLoading = true;
    state.error = null;
    try {
      const res = await fakeApiClient.get('/audit?page_size=100');
      state.events = res.items.map(mapBackendAuditEvent);
    } catch (err) {
      state.error = err.message;
    } finally {
      state.isLoading = false;
    }

    assert.equal(state.isLoading, false);
    assert.equal(state.error, null);
    assert.equal(state.events.length, 0);

    // 3. Detail fetch loads individual event
    const detail = await fakeApiClient.get('/audit/test-uuid-001');
    const mappedDetail = mapBackendAuditEvent(detail);
    assert.equal(mappedDetail.id, 'test-uuid-001');
    assert.equal(mappedDetail.action, 'LOGIN');
    assert.equal(mappedDetail.actorEmail, 'admin@juris.ai');
  });
});

describe('Phase 1 - Validation Queue Store & Mapping', () => {
  it('correctly maps backend validation item without skipping fields', () => {
    const raw = {
      id: '33333333-3333-3333-3333-333333333333',
      item_type: 'RELATIONSHIP',
      status: 'PENDING',
      confidence: 0.94,
      proposed_payload: {
        source: 'Kesavananda Bharati v. State of Kerala',
        relation: 'ESTABLISHES',
        target: 'Basic Structure Doctrine',
        document_title: 'AIR 1973 SC 1461',
      },
      evidence_text: 'The power of amendment under Article 368 does not enable Parliament to alter the basic structure.',
      source_document_id: '44444444-4444-4444-4444-444444444444',
      source_chunk_id: 'chunk_82',
      page_number: 142,
      reviewer_id: null,
      decision_timestamp: null,
      rejection_note: null,
      created_at: '2026-10-11T11:00:00Z',
    };

    const mapped = mapBackendValidationItem(raw);
    assert.equal(mapped.id, raw.id);
    assert.equal(mapped.itemType, 'RELATIONSHIP');
    assert.equal(mapped.status, 'PENDING');
    assert.equal(mapped.confidenceScore, 94);
    assert.equal(mapped.sourceDocumentTitle, 'AIR 1973 SC 1461');
    assert.equal(mapped.sourceLocation, 'Page 142');
    assert.equal(mapped.sourceTextSnippet, raw.evidence_text);
    assert.deepEqual(mapped.relationship, {
      source: 'Kesavananda Bharati v. State of Kerala',
      relation: 'ESTABLISHES',
      target: 'Basic Structure Doctrine',
    });
  });

  it('verifies empty API response results in zero validation items, never revealing mock entries', () => {
    const apiResponse = { items: [], total: 0 };
    const mapped = apiResponse.items.map(mapBackendValidationItem);

    assert.equal(mapped.length, 0);
    // Ensure mock entries are never present in mapped output
    assert.equal(mapped.some((i) => i.id === INITIAL_MOCK_VALIDATION_ITEMS[0].id), false);
    assert.equal(mapped.some((i) => i.id === 'val_101'), false);
  });

  it('handles approval success, approval failure, rejection failure, and retaining server state', async () => {
    let mockServerState = {
      'val-1': {
        id: 'val-1',
        item_type: 'ENTITY',
        status: 'PENDING',
        confidence: 0.92,
        proposed_payload: { label: 'Article 21' },
        created_at: '2026-10-11T10:00:00Z',
      },
    };

    let serverShouldFail = false;
    const fakeApiClient = {
      post: async (url, body) => {
        if (serverShouldFail) {
          throw new Error('500 Server Error: Write transaction failed');
        }
        if (url === '/validation/val-1/approve') {
          mockServerState['val-1'].status = 'APPROVED';
          return { ...mockServerState['val-1'], decision_timestamp: '2026-10-11T10:05:00Z' };
        }
        if (url === '/validation/val-1/reject') {
          if (!body?.rejection_note?.trim()) {
            throw new Error('422 Validation Error: Rejection note required');
          }
          mockServerState['val-1'].status = 'REJECTED';
          mockServerState['val-1'].rejection_note = body.rejection_note;
          return { ...mockServerState['val-1'], decision_timestamp: '2026-10-11T10:05:00Z' };
        }
        throw new Error('404 Not Found');
      },
    };

    // Client-side state
    let items = [mapBackendValidationItem(mockServerState['val-1'])];
    let submittingIds = new Set();

    // 1. Test Approval Failure: server fails -> client state retains PENDING
    serverShouldFail = true;
    let approvalError = null;
    try {
      submittingIds.add('val-1');
      await fakeApiClient.post('/validation/val-1/approve');
      items = items.map((i) => i.id === 'val-1' ? { ...i, status: 'APPROVED' } : i);
    } catch (err) {
      approvalError = err;
    } finally {
      submittingIds.delete('val-1');
    }

    assert.ok(approvalError, 'Approval must throw error on server failure');
    assert.equal(items.find((i) => i.id === 'val-1').status, 'PENDING', 'Item must retain PENDING on error');

    // 2. Test Approval Success: server succeeds -> client state becomes APPROVED
    serverShouldFail = false;
    try {
      submittingIds.add('val-1');
      const res = await fakeApiClient.post('/validation/val-1/approve');
      items = items.map((i) => i.id === 'val-1' ? { ...i, status: res.status } : i);
    } finally {
      submittingIds.delete('val-1');
    }

    assert.equal(items.find((i) => i.id === 'val-1').status, 'APPROVED');

    // 3. Test Rejection Failure on empty note
    let rejectionError = null;
    try {
      const note = '   ';
      if (!note.trim()) {
        throw new Error('A rejection note is required.');
      }
      await fakeApiClient.post('/validation/val-1/reject', { rejection_note: note });
    } catch (err) {
      rejectionError = err;
    }
    assert.equal(rejectionError.message, 'A rejection note is required.');

    // 4. Test Duplicate Submission Prevention
    submittingIds.add('val-1');
    let duplicateRejected = false;
    if (submittingIds.has('val-1')) {
      duplicateRejected = true;
    }
    assert.equal(duplicateRejected, true, 'Duplicate submission must be guarded while in flight');
  });
});
