from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceCitationSchema(BaseModel):
    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float


class CreateRationaleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    quant_context: str = Field(pattern="^(financial_modeling|decision_analysis)$")
    quant_analysis_id: UUID
    recommended_option: str = Field(min_length=1, max_length=255)
    confidence_note: str = Field(min_length=1, max_length=2000)
    evidence_citations: list[EvidenceCitationSchema] = Field(default_factory=list)


class OverrideSchema(BaseModel):
    overridden_by: str
    reason: str
    new_recommended_option: str
    overridden_at: datetime


class RationaleResponse(BaseModel):
    rationale_id: UUID
    title: str
    quant_context: str
    quant_analysis_id: UUID
    recommended_option: str
    current_recommendation: str
    confidence_note: str
    evidence_citations: list[EvidenceCitationSchema]
    overrides: list[OverrideSchema]
    created_at: datetime


class OverrideRationaleRequest(BaseModel):
    overridden_by: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=2000)
    new_recommended_option: str = Field(min_length=1, max_length=255)


class NarrativeResponse(BaseModel):
    rationale_id: UUID
    narrative: str


class ClearHistoryResponse(BaseModel):
    deleted_count: int
