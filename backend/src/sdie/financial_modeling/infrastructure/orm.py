"""SQLAlchemy ORM mapping. This is the ONLY file in this context allowed
to import sqlalchemy. Domain and application layers stay framework-free."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
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

    __table_args__ = (
        # Row-level security is enabled via a migration (see alembic/env)
        # binding tenant_id to the session's current_setting('app.tenant_id').
        {"comment": "RLS enforced — see migrations/rls_policies.sql"},
    )
