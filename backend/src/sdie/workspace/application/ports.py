from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.domain.entities import Engagement


class EngagementRepository(ABC):
    @abstractmethod
    async def save(self, engagement: Engagement) -> None: ...

    @abstractmethod
    async def get(self, engagement_id: UUID, tenant_id: TenantId) -> Engagement | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[Engagement]: ...
