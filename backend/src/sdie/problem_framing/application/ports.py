from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.problem_framing.domain.entities import FrameworkAnalysis
from sdie.shared_kernel.domain.value_objects import TenantId


class FrameworkAnalysisRepository(ABC):
    @abstractmethod
    async def save(self, analysis: FrameworkAnalysis) -> None: ...

    @abstractmethod
    async def get(self, analysis_id: UUID, tenant_id: TenantId) -> FrameworkAnalysis | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[FrameworkAnalysis]: ...
