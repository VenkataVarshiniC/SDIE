from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from sdie.shared_kernel.infrastructure.database import Base


class DecisionAnalysisORM(Base):
    __tablename__ = "decision_analyses"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_option: Mapped[str] = mapped_column(String(255), nullable=False)
    # Heterogeneous by method (MCDA rankings vs. decision-tree EMV/EVPI vs.
    # Monte Carlo percentiles) — JSONB avoids three near-identical child
    # tables that would each only ever be read back whole, never queried
    # by field. See the same tradeoff note in financial_modeling's ORM.
    result_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        {"comment": "RLS enforced — see migrations/versions/0001_initial_schema.py"},
    )
