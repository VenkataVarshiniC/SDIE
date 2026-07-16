from __future__ import annotations

from sdie.evidence_research.application.dto import (
    CitationResult,
    DocumentResult,
    IngestDocumentCommand,
    SearchEvidenceQuery,
)
from sdie.evidence_research.application.ports import DocumentRepository
from sdie.evidence_research.domain.entities import Document
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus


class IngestDocumentUseCase:
    def __init__(self, repository: DocumentRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: IngestDocumentCommand) -> DocumentResult:
        tenant_id = TenantId(command.tenant_id)
        document = Document.create(
            tenant_id=tenant_id,
            title=command.title,
            source_label=command.source_label,
            content=command.content,
        )
        await self._repository.save(document)
        await self._event_bus.publish_all(document.pull_pending_events())

        return DocumentResult(
            document_id=document.id,
            title=document.title,
            source_label=document.source_label,
            created_at=document.created_at,
        )


class ListDocumentsUseCase:
    def __init__(self, repository: DocumentRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[DocumentResult]:
        documents = await self._repository.list_for_tenant(tenant_id)
        return [
            DocumentResult(
                document_id=d.id, title=d.title, source_label=d.source_label, created_at=d.created_at
            )
            for d in documents
        ]


class SearchEvidenceUseCase:
    """The retrieval half of RAG. Deliberately lexical (Postgres full-text
    search), not vector similarity — see the design note on
    infrastructure/repository.py for why that's the right default here
    rather than a placeholder."""

    def __init__(self, repository: DocumentRepository):
        self._repository = repository

    async def execute(self, query: SearchEvidenceQuery) -> list[CitationResult]:
        tenant_id = TenantId(query.tenant_id)
        citations = await self._repository.search(tenant_id, query.query, query.limit)
        return [
            CitationResult(
                document_id=c.document_id,
                document_title=c.document_title,
                source_label=c.source_label,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
            )
            for c in citations
        ]
