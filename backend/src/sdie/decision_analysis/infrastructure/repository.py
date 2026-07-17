from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.decision_analysis.application.ports import DecisionAnalysisRepository
from sdie.decision_analysis.domain.entities import DecisionAnalysis
from sdie.decision_analysis.infrastructure.orm import DecisionAnalysisORM
from sdie.shared_kernel.domain.value_objects import TenantId


class SqlAlchemyDecisionAnalysisRepository(DecisionAnalysisRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, analysis: DecisionAnalysis) -> None:
        orm = DecisionAnalysisORM(
            id=analysis.id,
            tenant_id=analysis.tenant_id.value,
            title=analysis.title,
            method=analysis.method,
            recommended_option=analysis.recommended_option or "",
            result_data=analysis.result_data,
            created_at=analysis.created_at,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, analysis_id: UUID, tenant_id: TenantId) -> DecisionAnalysis | None:
        stmt = select(DecisionAnalysisORM).where(
            DecisionAnalysisORM.id == analysis_id,
            DecisionAnalysisORM.tenant_id == tenant_id.value,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_tenant(self, tenant_id: TenantId) -> list[DecisionAnalysis]:
        stmt = (
            select(DecisionAnalysisORM)
            .where(DecisionAnalysisORM.tenant_id == tenant_id.value)
            .order_by(DecisionAnalysisORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete_all_for_tenant(self, tenant_id: TenantId) -> int:
        stmt = delete(DecisionAnalysisORM).where(DecisionAnalysisORM.tenant_id == tenant_id.value)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0

    @staticmethod
    def _to_domain(row: DecisionAnalysisORM) -> DecisionAnalysis:
        analysis = DecisionAnalysis(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            title=row.title,
            method=row.method,
            created_at=row.created_at,
            recommended_option=row.recommended_option,
            result_data=row.result_data,
        )
        analysis.__post_init__()
        return analysis
