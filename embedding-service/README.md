# InLegalBERT Standalone Embedding Microservice

Dedicated FastAPI microservice for `law-ai/InLegalBERT` vector embedding generation, designed for high-performance offloaded inference on Hugging Face Spaces (CPU Basic) or custom Docker runtime.

## Features

- **Exact Vector Parity:** Implements attention-mask mean pooling and L2 normalization over `law-ai/InLegalBERT` `last_hidden_state` (768 dimensions).
- **API Key Security:** Authenticates requests via `X-API-Key` or `Authorization: Bearer <key>` headers.
- **Robust Error Handling:** Strict request validation, input sanitization, and structured health reporting.
- **HF Spaces Ready:** Docker container pre-configured for Hugging Face Spaces (Port 7860, non-root user 1000).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_API_KEY` | None | Secret key required to access `/embed`. If unset, auth is disabled for local dev. |
| `EMBEDDING_MODEL_NAME` | `law-ai/InLegalBERT` | Hugging Face model repository identifier. |
| `EMBEDDING_DEVICE` | `cpu` | Execution device (`cpu` or `cuda`). |
| `EMBEDDING_BATCH_SIZE` | `16` | Maximum batch size per inference pass. |
| `EMBEDDING_MAX_TOKENS` | `512` | Tokenizer truncation limit. |
| `PRELOAD_MODEL` | `true` | Pre-load model weights into RAM on app startup. |
| `PORT` | `7860` | Server listening port. |

## Quick Start (Local Development)

### 1. Install Dependencies
```bash
cd embedding-service
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Run Service Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
```

### 3. Run Test Suite
```bash
uv run pytest
```

---

## API Specification

### 1. Health Check
`GET /health`

**Response (`200 OK`):**
```json
{
  "status": "healthy",
  "model": "law-ai/InLegalBERT",
  "model_loaded": true,
  "device": "cpu",
  "dimension": 768
}
```

### 2. Generate Embeddings
`POST /embed`

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: <YOUR_EMBEDDING_API_KEY>` (or `Authorization: Bearer <YOUR_EMBEDDING_API_KEY>`)

**Request Body:**
```json
{
  "texts": [
    "What does Article 21 protect?",
    "Relationship between Section 66A of IT Act and Article 19"
  ]
}
```

**Response (`200 OK`):**
```json
{
  "embeddings": [
    [0.0123, -0.0456, "... 768 floats ..."],
    [0.0234, -0.0567, "... 768 floats ..."]
  ],
  "dimension": 768,
  "count": 2,
  "model": "law-ai/InLegalBERT"
}
```

---

## Deployment to Hugging Face Spaces (CPU Basic)

1. Go to [Hugging Face Spaces](https://huggingface.co/new-space).
2. Set **Space Name** (e.g., `juris-inlegalbert-service`).
3. Select SDK: **Docker** (Blank template).
4. Select Space Hardware: **CPU Basic** (2 vCPU, 16 GB RAM — **100% Free**).
5. Set Visibility: **Public** or **Private**.
6. Under Space Settings $\rightarrow$ **Variables and secrets**, add:
   - Secret Key: `EMBEDDING_API_KEY` = `<your-random-secure-secret>`
7. Push files (`Dockerfile`, `requirements.txt`, `app/`) to your HF Space repo:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/juris-inlegalbert-service
   git push hf main
   ```
