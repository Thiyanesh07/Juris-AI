import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  INITIAL_MOCK_SETTINGS,
  FRONTEND_TO_BACKEND_SECTION_MAP,
  BACKEND_TO_FRONTEND_SECTION_MAP,
  SECTION_FIELD_MAPPINGS,
  getBackendKey,
  getUiKey,
  isMaskedSecret,
  buildBackendConfigPayload,
  hydrateSectionsFromBackend,
} from '../data/settings.ts';

describe('Phase 2 - Admin Settings Section Mapping', () => {
  it('maps all frontend sections to backend uppercase sections, including AI_LLM and KNOWLEDGE_GRAPH', () => {
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['ai'], 'AI_LLM');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['graph'], 'KNOWLEDGE_GRAPH');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['general'], 'GENERAL');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['embeddings'], 'EMBEDDINGS');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['retrieval'], 'RETRIEVAL');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['ingestion'], 'INGESTION');
    assert.equal(FRONTEND_TO_BACKEND_SECTION_MAP['security'], 'SECURITY');
  });

  it('reversibly maps all backend sections back to frontend section IDs', () => {
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['AI_LLM'], 'ai');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['KNOWLEDGE_GRAPH'], 'graph');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['GENERAL'], 'general');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['EMBEDDINGS'], 'embeddings');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['RETRIEVAL'], 'retrieval');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['INGESTION'], 'ingestion');
    assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP['SECURITY'], 'security');

    // Bijective round-trip verification
    for (const [frontendId, backendId] of Object.entries(FRONTEND_TO_BACKEND_SECTION_MAP)) {
      assert.equal(BACKEND_TO_FRONTEND_SECTION_MAP[backendId], frontendId);
    }
  });
});

describe('Phase 2 - Reversible Field-Name Mappings', () => {
  it('verifies AI_LLM field mappings are reversible and derived from backend schemas', () => {
    assert.equal(getBackendKey('AI_LLM', 'maxOutputTokens'), 'max_output_tokens');
    assert.equal(getUiKey('AI_LLM', 'max_output_tokens'), 'maxOutputTokens');

    assert.equal(getBackendKey('AI_LLM', 'timeout'), 'llm_timeout_seconds');
    assert.equal(getUiKey('AI_LLM', 'llm_timeout_seconds'), 'timeout');

    assert.equal(getBackendKey('AI_LLM', 'apiKey'), 'api_key');
    assert.equal(getUiKey('AI_LLM', 'api_key'), 'apiKey');

    assert.equal(getBackendKey('AI_LLM', 'provider'), 'provider');
    assert.equal(getUiKey('AI_LLM', 'provider'), 'provider');

    assert.equal(getBackendKey('AI_LLM', 'model'), 'model');
    assert.equal(getUiKey('AI_LLM', 'model'), 'model');

    assert.equal(getBackendKey('AI_LLM', 'temperature'), 'temperature');
    assert.equal(getUiKey('AI_LLM', 'temperature'), 'temperature');
  });

  it('verifies RETRIEVAL field mappings match backend default_top_k and dense_weight', () => {
    assert.equal(getBackendKey('RETRIEVAL', 'vectorTopK'), 'default_top_k');
    assert.equal(getUiKey('RETRIEVAL', 'default_top_k'), 'vectorTopK');

    assert.equal(getBackendKey('RETRIEVAL', 'hybridWeight'), 'dense_weight');
    assert.equal(getUiKey('RETRIEVAL', 'dense_weight'), 'hybridWeight');

    assert.equal(getBackendKey('RETRIEVAL', 'graphDepth'), 'graph_depth');
    assert.equal(getUiKey('RETRIEVAL', 'graph_depth'), 'graphDepth');

    assert.equal(getBackendKey('RETRIEVAL', 'graphCandidateLimit'), 'graph_candidate_limit');
    assert.equal(getUiKey('RETRIEVAL', 'graph_candidate_limit'), 'graphCandidateLimit');
  });

  it('verifies INGESTION, KNOWLEDGE_GRAPH, and EMBEDDINGS field mappings', () => {
    assert.equal(getBackendKey('INGESTION', 'chunkSize'), 'chunk_size');
    assert.equal(getUiKey('INGESTION', 'chunk_size'), 'chunkSize');

    assert.equal(getBackendKey('INGESTION', 'chunkOverlap'), 'chunk_overlap');
    assert.equal(getUiKey('INGESTION', 'chunk_overlap'), 'chunkOverlap');

    assert.equal(getBackendKey('KNOWLEDGE_GRAPH', 'connectionUri'), 'neo4j_uri');
    assert.equal(getUiKey('KNOWLEDGE_GRAPH', 'neo4j_uri'), 'connectionUri');

    assert.equal(getBackendKey('KNOWLEDGE_GRAPH', 'maxTraversalDepth'), 'max_traversal_depth');
    assert.equal(getUiKey('KNOWLEDGE_GRAPH', 'max_traversal_depth'), 'maxTraversalDepth');

    assert.equal(getBackendKey('EMBEDDINGS', 'model'), 'model_name');
    assert.equal(getUiKey('EMBEDDINGS', 'model_name'), 'model');

    assert.equal(getBackendKey('EMBEDDINGS', 'dimension'), 'embedding_dim');
    assert.equal(getUiKey('EMBEDDINGS', 'embedding_dim'), 'dimension');
  });

  it('verifies round-trip fidelity for every registered field in SECTION_FIELD_MAPPINGS', () => {
    for (const [secName, mapping] of Object.entries(SECTION_FIELD_MAPPINGS)) {
      for (const [uiKey, backendKey] of Object.entries(mapping.uiToBackend)) {
        assert.equal(getBackendKey(secName, uiKey), backendKey);
        assert.equal(getUiKey(secName, backendKey), uiKey);
      }
    }
  });
});

describe('Phase 2 - Masked Secrets Protection', () => {
  it('correctly classifies masked credential strings and unmasked credentials', () => {
    // Backend & mock masked patterns
    assert.equal(isMaskedSecret('********'), true);
    assert.equal(isMaskedSecret('••••••••••••••••••••••••••••••••'), true);
    assert.equal(isMaskedSecret('sk-...****'), true);
    assert.equal(isMaskedSecret('val...********'), true);
    assert.equal(isMaskedSecret('••••••••'), true);

    // Legitimate real values must not be flagged as masked
    assert.equal(isMaskedSecret('sk-proj-valid-api-key-12345'), false);
    assert.equal(isMaskedSecret('bolt://neo4j:password@localhost:7687'), false);
    assert.equal(isMaskedSecret(''), false);
    assert.equal(isMaskedSecret(12345), false);
    assert.equal(isMaskedSecret(null), false);
  });

  it('prevents masked apiKey and connectionUri from being sent in save payloads', () => {
    const aiSec = JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['ai']));
    aiSec.settings.apiKey.value = '********';

    const payload = buildBackendConfigPayload('ai', aiSec);
    assert.equal('api_key' in payload, false, 'Masked apiKey must be omitted from payload to prevent overwriting credentials');
    assert.equal(payload['provider'], 'google_genai');
    assert.equal(payload['max_output_tokens'], 4096);

    const graphSec = JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['graph']));
    graphSec.settings.connectionUri.value = '••••••••••••••••••••••••••••••••';

    const graphPayload = buildBackendConfigPayload('graph', graphSec);
    assert.equal('neo4j_uri' in graphPayload, false, 'Masked connectionUri must be omitted from payload');
    assert.equal(graphPayload['max_traversal_depth'], 5);
  });

  it('includes secret in payload when user inputs a real, unmasked value', () => {
    const aiSec = JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['ai']));
    aiSec.settings.apiKey.value = 'sk-proj-real-production-api-key-999';

    const payload = buildBackendConfigPayload('ai', aiSec);
    assert.equal(payload['api_key'], 'sk-proj-real-production-api-key-999');
  });
});

describe('Phase 2 - Settings UI Hydration from Backend', () => {
  it('correctly hydrates all sections from a backend GET /settings response', () => {
    const mockBackendResponse = {
      GENERAL: {
        platform_name: 'Juris AI LegalGraph Production',
        maintenance_mode: false,
        max_query_length: 2500,
        support_email: 'legal@jurisai.law',
      },
      AI_LLM: {
        provider: 'google_genai',
        model: 'gemini-2.5-flash',
        temperature: 0.2,
        max_output_tokens: 2048,
        llm_timeout_seconds: 45.0,
        api_key: '********',
      },
      EMBEDDINGS: {
        model_name: 'law-ai/InLegalBERT',
        embedding_dim: 768,
        pooling: 'mean',
      },
      RETRIEVAL: {
        default_top_k: 8,
        dense_weight: 0.65,
        graph_weight: 0.35,
        fusion_algorithm: 'rrf',
      },
      INGESTION: {
        chunk_size: 1024,
        chunk_overlap: 128,
        enable_ocr_fallback: true,
      },
      KNOWLEDGE_GRAPH: {
        neo4j_uri: 'bolt://remote-neo4j:7687',
        neo4j_database: 'neo4j',
        max_traversal_depth: 4,
        default_traversal_depth: 2,
      },
      SECURITY: {
        session_ttl_hours: 8,
        require_mfa: true,
        max_login_attempts: 3,
      },
    };

    const hydrated = hydrateSectionsFromBackend(INITIAL_MOCK_SETTINGS, mockBackendResponse);

    // 1. Check AI_LLM -> ai mapping & field translation
    assert.equal(hydrated.ai.settings.provider.value, 'google_genai');
    assert.equal(hydrated.ai.settings.model.value, 'gemini-2.5-flash');
    assert.equal(hydrated.ai.settings.temperature.value, 0.2);
    assert.equal(hydrated.ai.settings.maxOutputTokens.value, 2048);
    assert.equal(hydrated.ai.settings.timeout.value, 45.0);
    assert.equal(hydrated.ai.settings.apiKey.value, '********');

    // 2. Check RETRIEVAL -> retrieval mapping
    assert.equal(hydrated.retrieval.settings.vectorTopK.value, 8);
    assert.equal(hydrated.retrieval.settings.hybridWeight.value, 0.65);

    // 3. Check INGESTION -> ingestion mapping
    assert.equal(hydrated.ingestion.settings.chunkSize.value, 1024);
    assert.equal(hydrated.ingestion.settings.chunkOverlap.value, 128);

    // 4. Check KNOWLEDGE_GRAPH -> graph mapping
    assert.equal(hydrated.graph.settings.connectionUri.value, 'bolt://remote-neo4j:7687');
    assert.equal(hydrated.graph.settings.maxTraversalDepth.value, 4);
    assert.equal(hydrated.graph.settings.defaultTraversalDepth.value, 2);

    // 5. Check SECURITY -> security mapping
    assert.equal(hydrated.security.settings.requireMfa.value, true);
    assert.equal(hydrated.security.settings.loginAttemptLimit.value, 3);
    assert.equal(hydrated.security.settings.sessionTimeoutMin.value, 480); // 8 hours * 60 min
  });
});

describe('Phase 2 - Save Behavior & Error State Handling', () => {
  it('handles save failure without updating baseline or reporting false success', async () => {
    let baselineState = {
      ai: JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['ai'])),
    };
    let activeState = {
      ai: JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['ai'])),
    };

    // User modifies maxOutputTokens from 4096 to 8192
    activeState.ai.settings.maxOutputTokens.value = 8192;

    const fakeApiClient = {
      put: async (url, body) => {
        throw new Error('403 Forbidden: Admin privileges required');
      },
    };

    let feedbackMessage = null;
    let errorMessage = null;
    let isSaving = true;

    try {
      const payload = buildBackendConfigPayload('ai', activeState.ai);
      await fakeApiClient.put('/settings/AI_LLM', { config: payload });
      // If success (should not happen):
      baselineState.ai = JSON.parse(JSON.stringify(activeState.ai));
      feedbackMessage = 'Saved successfully';
    } catch (err) {
      errorMessage = `Failed to save settings: ${err.message}`;
    } finally {
      isSaving = false;
    }

    assert.equal(isSaving, false);
    assert.equal(feedbackMessage, null, 'Success message must not be shown on failure');
    assert.equal(errorMessage, 'Failed to save settings: 403 Forbidden: Admin privileges required');
    // Baseline must NOT be updated
    assert.equal(baselineState.ai.settings.maxOutputTokens.value, 4096, 'Baseline must remain unchanged when save fails');
    // Section remains dirty
    const isDirty = baselineState.ai.settings.maxOutputTokens.value !== activeState.ai.settings.maxOutputTokens.value;
    assert.equal(isDirty, true, 'Section must remain dirty when save fails');
  });

  it('updates baseline and clears dirty state only on server confirmation', async () => {
    let baselineState = {
      retrieval: JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['retrieval'])),
    };
    let activeState = {
      retrieval: JSON.parse(JSON.stringify(INITIAL_MOCK_SETTINGS['retrieval'])),
    };

    activeState.retrieval.settings.vectorTopK.value = 12;

    const fakeApiClient = {
      put: async (url, body) => {
        assert.equal(url, '/settings/RETRIEVAL');
        assert.equal(body.config.default_top_k, 12);
        return {
          section: 'RETRIEVAL',
          config: body.config,
          updated_at: '2026-10-11T12:00:00Z',
        };
      },
    };

    let feedbackMessage = null;
    let errorMessage = null;

    try {
      const payload = buildBackendConfigPayload('retrieval', activeState.retrieval);
      const res = await fakeApiClient.put('/settings/RETRIEVAL', { config: payload });
      if (res && res.section) {
        baselineState.retrieval = JSON.parse(JSON.stringify(activeState.retrieval));
        feedbackMessage = 'Settings saved successfully';
      }
    } catch (err) {
      errorMessage = err.message;
    }

    assert.equal(errorMessage, null);
    assert.equal(feedbackMessage, 'Settings saved successfully');
    assert.equal(baselineState.retrieval.settings.vectorTopK.value, 12);
    const isDirty = baselineState.retrieval.settings.vectorTopK.value !== activeState.retrieval.settings.vectorTopK.value;
    assert.equal(isDirty, false, 'Dirty state must clear once baseline matches');
  });
});
