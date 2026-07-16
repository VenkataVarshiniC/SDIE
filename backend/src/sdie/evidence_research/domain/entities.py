"""Evidence & Research domain. A Document is a source of truth an analyst
ingests (a market report excerpt, an internal memo, a competitor filing).
Retrieval returns Citations — never raw prose treated as fact — so anything
downstream (Recommendation Synthesis) can point a claim back to an exact
document and excerpt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import TenantId


class EvidenceResearchError(ValueError):
    pass


@dataclass(frozen=True, kw_only=True)
class DocumentIngested(DomainEvent):
    document_id: UUID
    title: str


@dataclass(slots=True)
class Document(AggregateRoot):
    """A single ingested source document. Content is stored whole; chunking
    for retrieval happens at query time in the domain service so the
    chunking strategy can change without re-ingesting anything."""

    id: UUID
    tenant_id: TenantId
    title: str
    source_label: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls, *, tenant_id: TenantId, title: str, source_label: str, content: str
    ) -> Document:
        if not title.strip():
            raise EvidenceResearchError("title must not be empty")
        if not content.strip():
            raise EvidenceResearchError("content must not be empty")
        if not source_label.strip():
            raise EvidenceResearchError("source_label must not be empty (who/where this came from)")

        doc = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            title=title,
            source_label=source_label,
            content=content,
        )
        doc.raise_event(
            DocumentIngested(tenant_id=tenant_id.value, document_id=doc.id, title=title)
        )
        return doc


@dataclass(frozen=True, slots=True)
class Citation:
    """What gets attached to any downstream claim. `excerpt` is the exact
    text a reader can Ctrl+F for in the source document — never a
    paraphrase, so the citation is independently verifiable."""

    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float
