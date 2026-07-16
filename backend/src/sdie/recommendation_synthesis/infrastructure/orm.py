from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from sdie.shared_kernel.infrastructure.database import Base


class DecisionRationaleORM(Base):
    __tablename__ = "decision_rationales"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    quant_context: Mapped[str] = mapped_column(String(50), nullable=False)
    quant_analysis_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    recommended_option: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_note: Mapped[str] = mapped_column(String(2000), nullable=False)
    # Both are lists of value objects wholly owned by this aggregate — never
    # queried independently elsewhere, so JSONB (not child tables) is the
    # right call here, consistent with the same tradeoff made in
    # financial_modeling and decision_analysis.
    evidence_citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    overrides: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        {"comment": "RLS enforced — see migrations/versions/0002_evidence_and_synthesis.py"},
    )
