"""FastAPI Application for InLegalBERT Standalone Microservice."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from app.embedder import EmbedderConfig, EmbeddingServiceError, StandaloneInLegalBertEmbedder

logger = logging.getLogger("inlegalbert_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Global Embedder Singleton
embedder = StandaloneInLegalBertEmbedder(
    config=EmbedderConfig(
        model_name=os.environ.get("EMBEDDING_MODEL_NAME", "law-ai/InLegalBERT"),
        device=os.environ.get("EMBEDDING_DEVICE", "cpu"),
        batch_size=int(os.environ.get("EMBEDDING_BATCH_SIZE", "16")),
        max_tokens=int(os.environ.get("EMBEDDING_MAX_TOKENS", "512")),
    )
)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
HTTP_BEARER = HTTPBearer(auto_error=False)


def get_expected_api_key() -> str | None:
    """Retrieve configured API key from environment."""
    return os.environ.get("EMBEDDING_API_KEY") or os.environ.get("INLEGALBERT_API_KEY")


async def verify_api_key(
    header_key: str | None = Security(API_KEY_HEADER),
    bearer_credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> str | None:
    """Verify request API key against EMBEDDING_API_KEY environment variable."""
    expected_key = get_expected_api_key()
    if not expected_key:
        # No API key required if not configured in environment (Development mode)
        return None

    token: str | None = None
    if header_key:
        token = header_key
    elif bearer_credentials and bearer_credentials.credentials:
        token = bearer_credentials.credentials

    if not token or token != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key header ('X-API-Key' or 'Authorization: Bearer <key>')",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Pre-load InLegalBERT model on application startup if configured."""
    logger.info("Initializing InLegalBERT Embedding Service...")
    if os.environ.get("PRELOAD_MODEL", "true").lower() in ("true", "1", "yes"):
        try:
            embedder.load_model()
        except Exception as exc:
            logger.warning("Model pre-loading failed (will retry on first request): %s", exc)
    yield
    logger.info("Shutting down InLegalBERT Embedding Service.")


app = FastAPI(
    title="InLegalBERT Standalone Embedding Service",
    description="Dedicated microservice for law-ai/InLegalBERT attention-mask mean pooling embeddings.",
    version="1.0.0",
    lifespan=lifespan,
)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., description="List of non-empty legal text strings to embed.")

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("texts list cannot be empty")
        for i, text in enumerate(v):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Text at index {i} must be a non-empty string")
        return v


class EmbedResponse(BaseModel):
    embeddings: list[list[float]] = Field(..., description="Matrix of 768-dimensional float32 L2-normalized vectors.")
    dimension: int = Field(768, description="Embedding vector dimension.")
    count: int = Field(..., description="Total vectors generated.")
    model: str = Field("law-ai/InLegalBERT", description="Model name.")


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Service operational status.")
    model: str = Field("law-ai/InLegalBERT", description="Configured embedding model.")
    model_loaded: bool = Field(..., description="Whether model weights are loaded into memory.")
    device: str = Field("cpu", description="Execution device.")
    dimension: int = Field(768, description="Output vector dimension.")


@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
async def health_check() -> HealthResponse:
    """Public health check endpoint returning model readiness status."""
    return HealthResponse(
        status="healthy",
        model=embedder.config.model_name,
        model_loaded=embedder.is_loaded,
        device=embedder.config.device,
        dimension=768,
    )


@app.post("/embed", response_model=EmbedResponse, tags=["Inference"])
async def generate_embeddings(
    request: EmbedRequest,
    _: str | None = Depends(verify_api_key),
) -> EmbedResponse:
    """Generate 768-dimensional attention-mask mean-pooled, L2-normalized embeddings."""
    try:
        vectors = embedder.embed(request.texts)
        return EmbedResponse(
            embeddings=vectors,
            dimension=768,
            count=len(vectors),
            model=embedder.config.model_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected embedding endpoint error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error producing embeddings: {exc}",
        ) from exc
