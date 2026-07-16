"""results persistence, evidence research, recommendation synthesis

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- financial_cash_flow_models: persist the actual cash flows + results ---
    op.add_column(
        "financial_cash_flow_models",
        sa.Column("cash_flows", postgresql.JSONB, nullable=False, server_default="[]"),
    )
    op.add_column("financial_cash_flow_models", sa.Column("npv", sa.Numeric(20, 2), nullable=True))
    op.add_column(
        "financial_cash_flow_models", sa.Column("irr_percent", sa.Numeric(20, 10), nullable=True)
    )
    op.add_column(
        "financial_cash_flow_models", sa.Column("payback_period", sa.Numeric(10, 4), nullable=True)
    )
    op.alter_column("financial_cash_flow_models", "cash_flows", server_default=None)

    # --- decision_analyses: persist the full result payload ---
    op.add_column(
        "decision_analyses",
        sa.Column("recommended_option", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "decision_analyses",
        sa.Column("result_data", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.alter_column("decision_analyses", "recommended_option", server_default=None)
    op.alter_column("decision_analyses", "result_data", server_default=None)

    # --- evidence_research ---
    op.create_table(
        "evidence_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_label", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_documents_tenant_id", "evidence_documents", ["tenant_id"])

    # Generated column + GIN index for lexical full-text search. Raw SQL
    # because Alembic's op.add_column doesn't express GENERATED ALWAYS AS.
    op.execute(
        """
        ALTER TABLE evidence_documents
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_evidence_documents_search_vector ON evidence_documents USING GIN (search_vector)"
    )

    op.execute("ALTER TABLE evidence_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evidence_documents FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON evidence_documents
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )

    # --- recommendation_synthesis ---
    op.create_table(
        "decision_rationales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("quant_context", sa.String(length=50), nullable=False),
        sa.Column("quant_analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommended_option", sa.String(length=255), nullable=False),
        sa.Column("confidence_note", sa.String(length=2000), nullable=False),
        sa.Column("evidence_citations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("overrides", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decision_rationales_tenant_id", "decision_rationales", ["tenant_id"])
    op.alter_column("decision_rationales", "evidence_citations", server_default=None)
    op.alter_column("decision_rationales", "overrides", server_default=None)

    op.execute("ALTER TABLE decision_rationales ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE decision_rationales FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON decision_rationales
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON decision_rationales")
    op.drop_table("decision_rationales")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON evidence_documents")
    op.drop_table("evidence_documents")

    op.drop_column("decision_analyses", "result_data")
    op.drop_column("decision_analyses", "recommended_option")

    op.drop_column("financial_cash_flow_models", "payback_period")
    op.drop_column("financial_cash_flow_models", "irr_percent")
    op.drop_column("financial_cash_flow_models", "npv")
    op.drop_column("financial_cash_flow_models", "cash_flows")
