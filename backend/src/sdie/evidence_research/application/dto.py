from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IngestDocumentCommand:
    tenant_id: UUID
    title: str
    source_label: str
    content: str


@dataclass(frozen=True, slots=True)
class DocumentResult:
    document_id: UUID
    title: str
    source_label: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SearchEvidenceQuery:
    tenant_id: UUID
    query: str
    limit: int = 5


@dataclass(frozen=True, slots=True)
class CitationResult:
    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float
