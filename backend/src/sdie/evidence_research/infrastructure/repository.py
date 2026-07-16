"""Repository implementation, including retrieval.

Design decision: lexical full-text search (Postgres tsvector/ts_rank), not
vector similarity search, for this first version of the Evidence & Research
context. Two reasons, both concrete rather than hand-wavy:

1. Zero extra infrastructure. This works on any Postgres — a free hosted
   tier, a native local install, anything — with no extension to enable and
   no embedding API to configure. Given this platform's own constraint
   (no Docker, developer-supplied free-tier database), that materially
   matters.
2. It's what actually ships correctly today. Semantic vector search needs
   an embedding model; Groq doesn't serve one, so wiring vector search now
   would mean either adding a second LLM vendor just for embeddings or
   shipping an unfinished stub. Lexical search is a complete, real
   retrieval mechanism on its own — plenty of production RAG systems start
   here and add vector search as a second retrieval path later.

The abstraction boundary is unchanged: `DocumentRepository.search()` is the
seam. Adding vector search later means adding a second implementation
behind this port (or a hybrid rank fusing both), not restructuring any
caller.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.evidence_research.application.ports import DocumentRepository
from sdie.evidence_research.domain.entities import Citation, Document
from sdie.evidence_research.domain.services import extract_excerpt
from sdie.evidence_research.infrastructure.orm import DocumentORM
from sdie.shared_kernel.domain.value_objects import TenantId


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, document: Document) -> None:
        orm = DocumentORM(
            id=document.id,
            tenant_id=document.tenant_id.value,
            title=document.title,
            source_label=document.source_label,
            content=document.content,
            created_at=document.created_at,
        )
        merged = await self._session.merge(orm)
        self._session.add(merged)
        await self._session.flush()

    async def get(self, document_id: UUID, tenant_id: TenantId) -> Document | None:
        stmt = select(DocumentORM).where(
            DocumentORM.id == document_id, DocumentORM.tenant_id == tenant_id.value
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_tenant(self, tenant_id: TenantId) -> list[Document]:
        stmt = (
            select(DocumentORM)
            .where(DocumentORM.tenant_id == tenant_id.value)
            .order_by(DocumentORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def search(self, tenant_id: TenantId, query: str, limit: int = 5) -> list[Citation]:
        tsquery = func.plainto_tsquery("english", query)
        rank = func.ts_rank(DocumentORM.search_vector, tsquery).label("rank")

        stmt = (
            select(DocumentORM, rank)
            .where(
                DocumentORM.tenant_id == tenant_id.value,
                DocumentORM.search_vector.op("@@")(tsquery),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)

        query_terms = query.split()
        citations = []
        for row, score in result.all():
            excerpt = extract_excerpt(row.content, query_terms)
            citations.append(
                Citation(
                    document_id=row.id,
                    document_title=row.title,
                    source_label=row.source_label,
                    excerpt=excerpt,
                    relevance_score=float(score),
                )
            )
        return citations

    @staticmethod
    def _to_domain(row: DocumentORM) -> Document:
        doc = Document(
            id=row.id,
            tenant_id=TenantId(row.tenant_id),
            title=row.title,
            source_label=row.source_label,
            content=row.content,
            created_at=row.created_at,
        )
        doc.__post_init__()
        return doc
