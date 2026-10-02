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

# Copy project configuration
COPY pyproject.toml .
RUN uv pip install --system -r <(uv pip compile pyproject.toml) || pip install --no-cache-dir fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings faiss-cpu sentence-transformers httpx python-multipart neo4j

# Copy application source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
