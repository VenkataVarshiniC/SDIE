"""SQLAlchemy ORM mapping. Only file allowed to import sqlalchemy in this
context. `search_vector` is a STORED GENERATED column defined in the
migration (raw SQL — SQLAlchemy's declarative layer can't express Postgres
generated columns cleanly), so it's declared here read-only: the app never
writes to it, Postgres maintains it from `content` automatically.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from sdie.shared_kernel.infrastructure.database import Base


class DocumentORM(Base):
    __tablename__ = "evidence_documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_label: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # GENERATED ALWAYS AS (...) STORED in Postgres. `Computed()` tells
    # SQLAlchemy to never include this column in INSERT/UPDATE statements —
    # required, since Postgres rejects any explicit value (even NULL) for a
    # generated column. The actual DDL lives in the Alembic migration; this
    # declaration must match it.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), nullable=True
    )

    __table_args__ = (
        {"comment": "RLS enforced — see migrations/versions/0002_evidence_and_synthesis.py"},
    )
