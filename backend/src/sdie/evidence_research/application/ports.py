from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sdie.evidence_research.domain.entities import Citation, Document
from sdie.shared_kernel.domain.value_objects import TenantId


class DocumentRepository(ABC):
    @abstractmethod
    async def save(self, document: Document) -> None: ...

    @abstractmethod
    async def get(self, document_id: UUID, tenant_id: TenantId) -> Document | None: ...

    @abstractmethod
    async def list_for_tenant(self, tenant_id: TenantId) -> list[Document]: ...

    @abstractmethod
    async def search(self, tenant_id: TenantId, query: str, limit: int = 5) -> list[Citation]:
        """Full-text search over ingested documents for this tenant.
        Ranking (ts_rank) is a Postgres-native operation, hence this lives
        behind the port rather than in the domain layer."""
        ...

    @abstractmethod
    async def delete_all_for_tenant(self, tenant_id: TenantId) -> int:
        """Deletes every ingested document for this tenant. Returns the
        number of rows deleted."""
        ...
