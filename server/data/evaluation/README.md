# Juris AI Evaluation & Benchmarking Dataset

This directory contains the versioned ground-truth evaluation benchmark dataset for testing and comparing retrieval strategies (`VECTOR_ONLY`, `GRAPH_ONLY`, `HYBRID`) and measuring citation verification and temporal reasoning accuracy across Juris AI.

## Files
- `questions.json`: 9 representative legal research queries covering constitutional, statutory, case law, and temporal topics.
- `expected_citations.json`: Ground-truth citation strings required for each query.
- `expected_entities.json`: Canonical legal entity IDs expected to be retrieved.
- `expected_relationships.json`: Expected entity-relationship triples.
- `expected_temporal_facts.json`: Historical date boundaries, temporal operators, and milestone facts.

## Evaluated Metrics
1. **Recall@K & Precision@K:** Entity and citation retrieval accuracy.
2. **Mean Reciprocal Rank (MRR):** Rank position of the first relevant chunk/entity.
3. **Citation Verification Rate:** Proportion of generated citations successfully verified against raw corpus provenance.
4. **Temporal Fact Accuracy:** Rate of correct date extraction and legal version resolution.
