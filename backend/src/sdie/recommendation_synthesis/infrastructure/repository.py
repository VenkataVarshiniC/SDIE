from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.recommendation_synthesis.application.ports import DecisionRationaleRepository
from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    EvidenceCitation,
    Override,
    QuantSourceRef,
)
from sdie.recommendation_synthesis.infrastructure.orm import DecisionRationaleORM
from sdie.shared_kernel.domain.value_objects import TenantId


class SqlAlchemyDecisionRationaleRepository(DecisionRationaleRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, rationale: DecisionRationale) -> None:
        orm = DecisionRationaleORM(
            id=rationale.id,
            tenant_id=rationale.tenant_id.value,
            title=rationale.title,
            quant_context=rationale.quant_source.context,
            quant_analysis_id=rationale.quant_source.analysis_id,
            recommended_option=rationale.recommended_option,
            confidence_note=rationale.confidence_note,
            evidence_citations=[
                {
                    "document_id": str(c.document_id),
                    "document_title": c.document_title,
                    "source_label": c.source_label,
                    "excerpt": c.excerpt,
                    "relevance_score": c.relevance_score,
                }
                for c in rationale.evidence_citations
            ],
            overrides=[
                {
                    "overridden_by": o.overridden_by,
                    "reason": o.reason,
                    "new_recommended_option": o.new_recommended_option,
                    "overridden_at": o.overridden_at.isoformat(),
                }
                for o in rationale.overrides
            ],
            created_at=rationale.created_at,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, rationale_id: UUID, tenant_id: TenantId) -> DecisionRationale | None:
        stmt = select(DecisionRationaleORM).where(
            DecisionRationaleORM.id == rationale_id,
            DecisionRationaleORM.tenant_id == tenant_id.value,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_tenant(self, tenant_id: TenantId) -> list[DecisionRationale]:
        stmt = (
            select(DecisionRationaleORM)
            .where(DecisionRationaleORM.tenant_id == tenant_id.value)
            .order_by(DecisionRationaleORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: DecisionRationaleORM) -> DecisionRationale:
        rationale = DecisionRationale(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            title=row.title,
            quant_source=QuantSourceRef(context=row.quant_context, analysis_id=row.quant_analysis_id),
            recommended_option=row.recommended_option,
            confidence_note=row.confidence_note,
            created_at=row.created_at,
            evidence_citations=[
                EvidenceCitation(
                    document_id=UUID(c["document_id"]),
                    document_title=c["document_title"],
                    source_label=c["source_label"],
                    excerpt=c["excerpt"],
                    relevance_score=c["relevance_score"],
                )
                for c in row.evidence_citations
            ],
            overrides=[
                Override(
                    overridden_by=o["overridden_by"],
                    reason=o["reason"],
                    new_recommended_option=o["new_recommended_option"],
                    overridden_at=datetime.fromisoformat(o["overridden_at"]),
                )
                for o in row.overrides
            ],
        )
        rationale.__post_init__()
        return rationale
