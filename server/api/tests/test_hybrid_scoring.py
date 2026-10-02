"""Unit tests for hybrid scoring helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.retrieval.hybrid import (
    GraphBridge,
    bridge_confidence,
    bridge_weight,
    graph_score_for_bridges,
    hybrid_fusion_score,
    normalize_dense_score,
)


def _bridge(
    *,
    chunk_id: str = "cand",
    seed: str = "seed",
    entity: str = "e1",
    seed_conf: float | None = 1.0,
    cand_conf: float | None = 1.0,
) -> GraphBridge:
    return GraphBridge(
        chunk_id=chunk_id,
        seed_chunk_id=seed,
        entity_id=entity,
        entity_label="Concept",
        entity_name="Equality",
        seed_edge_confidence=seed_conf,
        candidate_edge_confidence=cand_conf,
    )


def _score(
    bridges: list[GraphBridge],
    seed_rank_by_id: dict[str, int],
) -> float:
    return graph_score_for_bridges(bridges, seed_rank_by_id)


@pytest.mark.parametrize(
    ("bridges", "expected"),
    [
        ([_bridge(entity="e1")], 0.5),
        ([_bridge(entity="e1"), _bridge(entity="e2")], 1.0),
        (
            [_bridge(entity="e1"), _bridge(entity="e2"), _bridge(entity="e3")],
            1.0,
        ),
        ([_bridge(seed="s2", entity="e1")], 0.25),
        (
            [
                _bridge(seed="s1", entity="e1"),
                _bridge(seed="s2", entity="e2"),
            ],
            0.75,
        ),
        ([_bridge(seed_conf=0.5, cand_conf=0.8)], 0.25),
    ],
)
def test_graph_score_reference_cases(
    bridges: list[GraphBridge],
    expected: float,
) -> None:
    seed_rank = {"s1": 1, "s2": 2, "seed": 1}
    assert _score(bridges, seed_rank) == pytest.approx(expected, abs=1e-6)


def test_normalize_dense_clamps() -> None:
    assert normalize_dense_score(-0.2) == pytest.approx(0.0)
    assert normalize_dense_score(0.8) == pytest.approx(0.8)
    assert normalize_dense_score(1.0001) == pytest.approx(1.0)


def test_hybrid_fusion_uses_weights() -> None:
    assert hybrid_fusion_score(1.0, 0.0, vector_weight=0.7, graph_weight=0.3) == pytest.approx(
        0.7
    )
    assert hybrid_fusion_score(0.0, 1.0, vector_weight=0.0, graph_weight=1.0) == pytest.approx(1.0)


def test_settings_validate_hybrid_caps() -> None:
    with pytest.raises(ValidationError):
        Settings(session_secret="x", hybrid_max_paths=0)
    with pytest.raises(ValidationError):
        Settings(session_secret="x", hybrid_max_graph_candidates=51)
    settings = Settings(session_secret="x")
    assert settings.hybrid_dense_seed_top_k == 10
    assert settings.hybrid_max_paths == 100
    assert settings.hybrid_max_graph_candidates == 25
    assert settings.hybrid_graph_timeout_seconds == pytest.approx(3.0)
    assert settings.graph_max_nodes == 100
    Settings(
        session_secret="x",
        hybrid_vector_weight=1.0,
        hybrid_graph_weight=0.0,
    )
    with pytest.raises(ValidationError):
        Settings(session_secret="x", hybrid_vector_weight=0.6, hybrid_graph_weight=0.3)


def test_bridge_confidence_defaults_null_to_one() -> None:
    assert bridge_confidence(None, None) == pytest.approx(1.0)
    assert bridge_weight(1, 1.0) == pytest.approx(0.5)


def test_bridge_confidence_clamps_out_of_range() -> None:
    assert bridge_confidence(1.5, 0.8) == pytest.approx(0.8)
    assert bridge_confidence(-0.2, 0.4) == pytest.approx(0.0)


def test_duplicate_bridge_does_not_increase_score() -> None:
    seed_rank = {"seed": 1}
    bridges = [_bridge(entity="e1"), _bridge(entity="e1"), _bridge(entity="e2")]
    assert _score(bridges, seed_rank) == pytest.approx(1.0)


def test_candidate_sort_key_is_deterministic() -> None:
    from app.retrieval.hybrid import CandidateState, _candidate_sort_key

    left = CandidateState(chunk_id="c-b", hybrid_score=0.5, normalized_dense=0.4, graph_score=0.1)
    right = CandidateState(chunk_id="c-a", hybrid_score=0.5, normalized_dense=0.4, graph_score=0.1)
    assert sorted([left, right], key=_candidate_sort_key) == [right, left]
