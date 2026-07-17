from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.financial_modeling.application.ports import CashFlowModelRepository
from sdie.financial_modeling.domain.entities import CashFlow, CashFlowModel
from sdie.financial_modeling.infrastructure.orm import CashFlowModelORM
from sdie.shared_kernel.domain.value_objects import Money, Percentage, TenantId


class SqlAlchemyCashFlowModelRepository(CashFlowModelRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, model: CashFlowModel) -> None:
        orm = CashFlowModelORM(
            id=model.id,
            tenant_id=model.tenant_id.value,
            project_name=model.project_name,
            currency=model.currency,
            discount_rate=model.discount_rate.fraction,
            created_at=model.created_at,
            cash_flows=[
                {"period": cf.period, "amount": str(cf.amount.amount)} for cf in model.cash_flows
            ],
            npv=model.npv.amount if model.npv else None,
            irr_percent=model.irr.as_percent() if model.irr else None,
            payback_period=model.payback_period,
            industry=model.industry,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, model_id: UUID, tenant_id: TenantId) -> CashFlowModel | None:
        stmt = select(CashFlowModelORM).where(
            CashFlowModelORM.id == model_id,
            CashFlowModelORM.tenant_id == tenant_id.value,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def list_for_tenant(self, tenant_id: TenantId) -> list[CashFlowModel]:
        stmt = (
            select(CashFlowModelORM)
            .where(CashFlowModelORM.tenant_id == tenant_id.value)
            .order_by(CashFlowModelORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _to_domain(row: CashFlowModelORM) -> CashFlowModel:
        model = CashFlowModel(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            project_name=row.project_name,
            currency=row.currency,
            discount_rate=Percentage(Decimal(str(row.discount_rate))),
            created_at=row.created_at,
            cash_flows=[
                CashFlow(cf["period"], Money(Decimal(cf["amount"]), row.currency))
                for cf in row.cash_flows
            ],
            npv=Money(Decimal(str(row.npv)), row.currency) if row.npv is not None else None,
            irr=Percentage.from_percent(Decimal(str(row.irr_percent)))
            if row.irr_percent is not None
            else None,
            payback_period=Decimal(str(row.payback_period))
            if row.payback_period is not None
            else None,
            industry=row.industry,
        )
        model.__post_init__()
        return model
