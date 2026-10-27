"""Gradio Adapter Entrypoint for Hugging Face Spaces Deployment.

Mounts the standalone InLegalBERT FastAPI application alongside an interactive
Gradio diagnostic interface, running under the free Hugging Face Gradio SDK (CPU Basic).
"""

from __future__ import annotations

import os

import gradio as gr

from app.main import app as fastapi_app, embedder


def diagnostic_embed(text: str) -> str:
    """Diagnostic helper for interactive testing in browser."""
    if not text.strip():
        return "Please enter valid legal text."
    try:
        vecs = embedder.embed([text])
        vec = vecs[0]
        norm = float(sum(x * x for x in vec) ** 0.5)
        return (
            f"Status: Success\n"
            f"Vector Dimension: {len(vec)}\n"
            f"L2 Norm: {norm:.6f}\n"
            f"Sample Values (first 5): {vec[:5]}"
        )
    except Exception as exc:
        return f"Error generating embedding: {exc}"


# Interactive Gradio Interface for browser visitors
demo = gr.Interface(
    fn=diagnostic_embed,
    inputs=gr.Textbox(
        lines=3,
        placeholder="Enter Indian legal text (e.g., Article 21 protects life and personal liberty)...",
    ),
    outputs="text",
    title="Juris AI — InLegalBERT Standalone Embedding Service",
    description=(
        "Standalone microservice serving 768-dimensional attention-mask mean-pooled InLegalBERT embeddings.\n"
        "Programmatic REST API endpoints available: POST /embed | GET /health"
    ),
)

# Mount Gradio UI at /ui, keeping root FastAPI endpoints intact (/embed, /health, /docs)
app = gr.mount_gradio_app(fastapi_app, demo, path="/ui")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
