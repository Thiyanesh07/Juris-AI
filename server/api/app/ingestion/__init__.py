"""Legal corpus ingestion and hierarchy-aware chunking pipeline (G03)."""

from app.ingestion.chunker import ChunkConfig, ChunkResult, chunk_pages
from app.ingestion.extractor import PageRecord, extract_pages
from app.ingestion.hierarchy import HierarchyContext, Level, detect_hierarchy
from app.ingestion.normalizer import normalize_text
from app.ingestion.persister import save_chunks, save_pages, save_raw_pdf, save_structure
from app.ingestion.pipeline import IngestionError, run_pipeline
from app.ingestion.validator import ValidationResult, validate_pdf

__all__ = [
    "ChunkConfig",
    "ChunkResult",
    "HierarchyContext",
    "IngestionError",
    "Level",
    "PageRecord",
    "ValidationResult",
    "chunk_pages",
    "detect_hierarchy",
    "extract_pages",
    "normalize_text",
    "run_pipeline",
    "save_chunks",
    "save_pages",
    "save_raw_pdf",
    "save_structure",
    "validate_pdf",
]
