"""Ports: interfaces the application layer depends on. Infrastructure
implements these. The application layer never imports SQLAlchemy, asyncpg,
or any concrete driver — that's the whole point of hexagonal architecture."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.financial_modeling.domain.entities import CashFlowModel
from sdie.shared_kernel.domain.value_objects import TenantId


class CashFlowModelRepository(ABC):
    @abstractmethod
    async def save(self, model: CashFlowModel) -> None: ...

    @abstractmethod
    async def get(self, model_id: UUID, tenant_id: TenantId) -> CashFlowModel | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[CashFlowModel]: ...
