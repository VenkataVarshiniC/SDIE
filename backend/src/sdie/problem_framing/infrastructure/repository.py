from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.problem_framing.application.ports import FrameworkAnalysisRepository
from sdie.problem_framing.domain.entities import Framework, FrameworkAnalysis
from sdie.problem_framing.infrastructure.orm import FrameworkAnalysisORM
from sdie.shared_kernel.domain.value_objects import TenantId


class SqlAlchemyFrameworkAnalysisRepository(FrameworkAnalysisRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, analysis: FrameworkAnalysis) -> None:
        orm = FrameworkAnalysisORM(
            id=analysis.id,
            tenant_id=analysis.tenant_id.value,
            title=analysis.title,
            framework=analysis.framework.value,
            entries=analysis.entries,
            created_at=analysis.created_at,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, analysis_id: UUID, tenant_id: TenantId) -> FrameworkAnalysis | None:
        stmt = select(FrameworkAnalysisORM).where(
            FrameworkAnalysisORM.id == analysis_id,
            FrameworkAnalysisORM.tenant_id == tenant_id.value,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_tenant(self, tenant_id: TenantId) -> list[FrameworkAnalysis]:
        stmt = (
            select(FrameworkAnalysisORM)
            .where(FrameworkAnalysisORM.tenant_id == tenant_id.value)
            .order_by(FrameworkAnalysisORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: FrameworkAnalysisORM) -> FrameworkAnalysis:
        analysis = FrameworkAnalysis(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            title=row.title,
            framework=Framework(row.framework),
            entries=row.entries,
            created_at=row.created_at,
        )
        analysis.__post_init__()
        return analysis
