# Juris AI Backend FastAPI Container
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set environment defaults for container runtime
ENV DATA_DIR=/app/data

# Copy project configuration & dependency lockfile from server/api
COPY server/api/pyproject.toml server/api/uv.lock* ./

# Compile dependencies to requirements.txt and install system-wide (compatible with /bin/sh)
RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --system -r requirements.txt

# Copy application source code and migration scripts from server/api
COPY server/api/app ./app
COPY server/api/alembic ./alembic
COPY server/api/alembic.ini .

# Copy runtime-required FAISS vector index artifacts from root data directory
COPY data/indexes/legal_chunks ./data/indexes/legal_chunks

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
