# Juris AI Backend FastAPI Container
FROM python:3.12-slim

WORKDIR /app

# Set environment defaults for container runtime
ENV DATA_DIR=/app/data

# Copy project configuration & dependency lockfile from server/api
COPY server/api/pyproject.toml server/api/uv.lock* ./

# Install runtime tools (curl for healthchecks) and temporary build-essential,
# install uv, resolve dependencies against PyTorch CPU wheel index,
# install packages system-wide without caching wheels, then purge build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && pip install --no-cache-dir uv \
    && uv pip compile pyproject.toml --extra-index-url https://download.pytorch.org/whl/cpu -o requirements.txt \
    && uv pip install --no-cache --system --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache

# Copy application source code and migration scripts from server/api
COPY server/api/app ./app
COPY server/api/alembic ./alembic
COPY server/api/alembic.ini .

# Copy runtime-required FAISS vector index artifacts from root data directory
COPY data/indexes/legal_chunks ./data/indexes/legal_chunks

# Copy pre-exported InLegalBERT ONNX model artifacts from root data directory
COPY data/models/inlegalbert ./data/models/inlegalbert

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
