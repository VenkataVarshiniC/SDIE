from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source_label: str = Field(min_length=1, max_length=500, description="e.g. 'Gartner 2026 report, p.14'")
    content: str = Field(min_length=1)


class DocumentResponse(BaseModel):
    document_id: UUID
    title: str
    source_label: str
    created_at: datetime


class SearchEvidenceRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class CitationResponse(BaseModel):
    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float
