"""HTTP layer: routers registered by app.main."""

from app.api.routes import documents, health

__all__ = ["documents", "health"]
