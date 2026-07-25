from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.application.dto import EngagementDeckData
from sdie.workspace.domain.entities import Engagement


class EngagementRepository(ABC):
    @abstractmethod
    async def save(self, engagement: Engagement) -> None: ...

    @abstractmethod
    async def get(self, engagement_id: UUID, tenant_id: TenantId) -> Engagement | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[Engagement]: ...

    @abstractmethod
    async def delete_all_for_tenant(self, tenant_id: TenantId) -> int:
        """Deletes every stored engagement for this tenant. Returns the
        number of rows deleted."""
        ...


class EngagementDeckRendererPort(ABC):
    """Renders a full engagement into a multi-section case deck PDF —
    Situation / Evidence / Quant Analysis / Recommendation. An
    infrastructure concern (like LLMPort and recommendation_synthesis's
    OnePagerRendererPort): the application layer decides what data goes
    into the deck, this port decides how it's laid out on the page."""

    @abstractmethod
    def render(self, engagement: Engagement, deck_data: EngagementDeckData) -> bytes: ...
