from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.recommendation_synthesis.domain.entities import DecisionRationale
from sdie.shared_kernel.domain.value_objects import TenantId


class DecisionRationaleRepository(ABC):
    @abstractmethod
    async def save(self, rationale: DecisionRationale) -> None: ...

    @abstractmethod
    async def get(self, rationale_id: UUID, tenant_id: TenantId) -> DecisionRationale | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[DecisionRationale]: ...


class OnePagerRendererPort(ABC):
    """Renders a DecisionRationale into a board-ready one-page PDF. An
    infrastructure concern (like LLMPort) — the application layer decides
    *what* goes in the memo, this port decides how it's laid out on a page.
    """

    @abstractmethod
    def render(self, rationale: DecisionRationale, supporting_data: dict | None) -> bytes: ...
