"""performance: composite (tenant_id, created_at desc) indexes

Every context's list_for_tenant() query filters by tenant_id and orders by
created_at descending — the single-column tenant_id indexes from prior
migrations satisfy the filter but leave Postgres to sort the matching rows
separately. A composite index in (tenant_id, created_at DESC) order lets a
single index scan satisfy both the filter and the sort, which matters more
as each tenant's row count grows. The old single-column indexes are kept
(harmless, and other query shapes could still use them) — this migration
only adds the composite ones.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TABLES = [
    "financial_cash_flow_models",
    "decision_analyses",
    "evidence_documents",
    "decision_rationales",
    "problem_framing_analyses",
    "workspace_engagements",
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"CREATE INDEX ix_{table}_tenant_created "
            f"ON {table} (tenant_id, created_at DESC)"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_tenant_created")
