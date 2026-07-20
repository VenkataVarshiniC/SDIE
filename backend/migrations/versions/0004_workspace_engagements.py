"""workspace engagements — the orchestration seam across all five contexts

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("problem_framing_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_document_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("financial_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rationale_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_engagements_tenant_id", "workspace_engagements", ["tenant_id"])
    op.alter_column("workspace_engagements", "evidence_document_ids", server_default=None)

    op.execute("ALTER TABLE workspace_engagements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_engagements FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON workspace_engagements
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON workspace_engagements")
    op.drop_table("workspace_engagements")
