from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateEngagementRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class EngagementResponse(BaseModel):
    engagement_id: UUID
    title: str
    status: str
    problem_framing_analysis_id: UUID | None
    evidence_document_ids: list[UUID]
    financial_model_id: UUID | None
    decision_analysis_id: UUID | None
    rationale_id: UUID | None
    created_at: datetime


class LinkProblemFramingRequest(BaseModel):
    analysis_id: UUID


class AddEvidenceRequest(BaseModel):
    document_id: UUID


class LinkFinancialModelRequest(BaseModel):
    model_id: UUID


class LinkDecisionAnalysisRequest(BaseModel):
    analysis_id: UUID


class LinkRationaleRequest(BaseModel):
    rationale_id: UUID
