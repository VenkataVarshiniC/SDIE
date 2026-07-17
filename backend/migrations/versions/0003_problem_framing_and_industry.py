"""industry benchmark field + problem framing analyses

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_cash_flow_models",
        sa.Column("industry", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "problem_framing_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("framework", sa.String(length=50), nullable=False),
        sa.Column("entries", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_problem_framing_analyses_tenant_id", "problem_framing_analyses", ["tenant_id"]
    )
    op.alter_column("problem_framing_analyses", "entries", server_default=None)

    op.execute("ALTER TABLE problem_framing_analyses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE problem_framing_analyses FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON problem_framing_analyses
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON problem_framing_analyses")
    op.drop_table("problem_framing_analyses")
    op.drop_column("financial_cash_flow_models", "industry")
