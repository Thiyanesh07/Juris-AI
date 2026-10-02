"""Neo4j legal knowledge graph — extraction, client, and population."""

from app.graph.client import GraphError, Neo4jClient
from app.graph.extraction import Entity, Relation, extract_entities, extract_relations
from app.graph.population import PopulationSummary, graph_stats, populate_graph

__all__ = [
    "Entity",
    "GraphError",
    "Neo4jClient",
    "PopulationSummary",
    "Relation",
    "extract_entities",
    "extract_relations",
    "graph_stats",
    "populate_graph",
]
