from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateEngagementCommand:
    tenant_id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class EngagementResult:
    engagement_id: UUID
    title: str
    status: str
    problem_framing_analysis_id: UUID | None
    evidence_document_ids: list[UUID]
    financial_model_id: UUID | None
    decision_analysis_id: UUID | None
    rationale_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LinkProblemFramingCommand:
    tenant_id: UUID
    engagement_id: UUID
    analysis_id: UUID


@dataclass(frozen=True, slots=True)
class AddEvidenceCommand:
    tenant_id: UUID
    engagement_id: UUID
    document_id: UUID


@dataclass(frozen=True, slots=True)
class LinkFinancialModelCommand:
    tenant_id: UUID
    engagement_id: UUID
    model_id: UUID


@dataclass(frozen=True, slots=True)
class LinkDecisionAnalysisCommand:
    tenant_id: UUID
    engagement_id: UUID
    analysis_id: UUID


@dataclass(frozen=True, slots=True)
class LinkRationaleCommand:
    tenant_id: UUID
    engagement_id: UUID
    rationale_id: UUID
