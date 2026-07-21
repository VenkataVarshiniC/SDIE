from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.application.ports import EngagementRepository
from sdie.workspace.domain.entities import Engagement, EngagementStatus
from sdie.workspace.infrastructure.orm import EngagementORM


class SqlAlchemyEngagementRepository(EngagementRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, engagement: Engagement) -> None:
        orm = EngagementORM(
            id=engagement.id,
            tenant_id=engagement.tenant_id.value,
            title=engagement.title,
            status=engagement.status.value,
            problem_framing_analysis_id=engagement.problem_framing_analysis_id,
            evidence_document_ids=[str(d) for d in engagement.evidence_document_ids],
            financial_model_id=engagement.financial_model_id,
            decision_analysis_id=engagement.decision_analysis_id,
            rationale_id=engagement.rationale_id,
            created_at=engagement.created_at,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, engagement_id: UUID, tenant_id: TenantId) -> Engagement | None:
        stmt = select(EngagementORM).where(
            EngagementORM.id == engagement_id, EngagementORM.tenant_id == tenant_id.value
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_tenant(self, tenant_id: TenantId) -> list[Engagement]:
        stmt = (
            select(EngagementORM)
            .where(EngagementORM.tenant_id == tenant_id.value)
            .order_by(EngagementORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete_all_for_tenant(self, tenant_id: TenantId) -> int:
        stmt = delete(EngagementORM).where(EngagementORM.tenant_id == tenant_id.value)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0

    @staticmethod
    def _to_domain(row: EngagementORM) -> Engagement:
        engagement = Engagement(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            title=row.title,
            status=EngagementStatus(row.status),
            created_at=row.created_at,
            problem_framing_analysis_id=row.problem_framing_analysis_id,
            evidence_document_ids=[UUID(d) for d in row.evidence_document_ids],
            financial_model_id=row.financial_model_id,
            decision_analysis_id=row.decision_analysis_id,
            rationale_id=row.rationale_id,
        )
        engagement.__post_init__()
        return engagement
