"""SQLAlchemy ORM mapping. This is the ONLY file in this context allowed
to import sqlalchemy. Domain and application layers stay framework-free."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from sdie.shared_kernel.infrastructure.database import Base


class CashFlowModelORM(Base):
    __tablename__ = "financial_cash_flow_models"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    discount_rate: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cash flow line items and computed results, stored as JSONB rather than
    # a normalized child table: nothing else in this scaffold needs to query
    # individual line items relationally, and JSONB keeps the round-trip
    # (aggregate -> row -> aggregate) a single-statement operation. If a
    # future use case needs to query across line items (e.g. "all models
    # with a year-2 cash flow above $X"), normalize then — the port
    # (CashFlowModelRepository) doesn't change either way.
    cash_flows: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    npv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    irr_percent: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    payback_period: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    __table_args__ = (
        {"comment": "RLS enforced — see migrations/versions/0001_initial_schema.py"},
    )
