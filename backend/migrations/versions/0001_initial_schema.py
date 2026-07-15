"""initial schema — financial modeling and decision analysis tables, with RLS

Revision ID: 0001
Revises:
Create Date: 2026-07-15

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_cash_flow_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("discount_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_financial_cash_flow_models_tenant_id",
        "financial_cash_flow_models",
        ["tenant_id"],
    )

    op.create_table(
        "decision_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_decision_analyses_tenant_id",
        "decision_analyses",
        ["tenant_id"],
    )

    # Row-level security: every tenant-scoped table gets a policy that binds
    # visibility to the session variable set by
    # shared_kernel.infrastructure.database.set_tenant_context(). This is
    # the DB-layer half of tenant isolation — application code setting
    # tenant_id on a query is a convention; this makes it a guarantee.
    #
    # NOTE: Postgres superusers (and, without FORCE, table owners) bypass
    # RLS entirely. The docker-compose `sdie` user is a superuser because
    # that's what the postgres image's POSTGRES_USER becomes on init — fine
    # for local dev, but production MUST connect as a non-superuser
    # application role for these policies to actually do anything.
    for table in ("financial_cash_flow_models", "decision_analyses"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in ("financial_cash_flow_models", "decision_analyses"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("decision_analyses")
    op.drop_table("financial_cash_flow_models")
