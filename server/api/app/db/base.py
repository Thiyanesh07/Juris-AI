"""Declarative base, constraint naming conventions and shared model mixins.

Timestamp convention
--------------------
All datetimes are timezone-aware and stored as PostgreSQL ``timestamptz`` in
UTC: Python-side defaults use :func:`utc_now`, while the server-side default is
``now()`` (PostgreSQL stores timestamptz in UTC internally). ``updated_at`` is
maintained by the ORM on UPDATE statements. Calendar dates (for example
document version effective ranges) use the timezone-free ``Date`` type.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def new_uuid() -> uuid.UUID:
    """Return a random UUID4 for primary key defaults."""
    return uuid.uuid4()


def pg_enum[EnumT: enum.Enum](enum_cls: type[EnumT], name: str) -> Enum:
    """Create a native PostgreSQL enum type storing lowercase member values."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )


class Base(DeclarativeBase):
    """Declarative base for all application models (PostgreSQL only)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CreatedAtMixin:
    """Adds a non-null, timezone-aware creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Adds ``updated_at``, maintained by the ORM on UPDATE statements."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )
