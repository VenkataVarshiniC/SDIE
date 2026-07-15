from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.decision_analysis.domain.entities import DecisionAnalysis
from sdie.shared_kernel.domain.value_objects import TenantId


class DecisionAnalysisRepository(ABC):
    @abstractmethod
    async def save(self, analysis: DecisionAnalysis) -> None: ...

    @abstractmethod
    async def get(self, analysis_id: UUID, tenant_id: TenantId) -> DecisionAnalysis | None: ...
