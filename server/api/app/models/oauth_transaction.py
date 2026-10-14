"""Short-lived, single-use Google OAuth transactions."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin


class OAuthTransaction(CreatedAtMixin, Base):
    """Server-side state for one Google authorization attempt."""

    __tablename__ = "oauth_transactions"

    state_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_binding: Mapped[str] = mapped_column(String(64), nullable=False)
    intent: Mapped[str] = mapped_column(String(16), nullable=False)
    return_to: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
