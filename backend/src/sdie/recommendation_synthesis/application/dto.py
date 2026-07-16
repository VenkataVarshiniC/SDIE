from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvidenceCitationInput:
    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float


@dataclass(frozen=True, slots=True)
class CreateRationaleCommand:
    tenant_id: UUID
    title: str
    quant_context: str  # "financial_modeling" | "decision_analysis"
    quant_analysis_id: UUID
    recommended_option: str
    confidence_note: str
    evidence_citations: list[EvidenceCitationInput]


@dataclass(frozen=True, slots=True)
class OverrideInput:
    overridden_at: datetime
    overridden_by: str
    reason: str
    new_recommended_option: str


@dataclass(frozen=True, slots=True)
class RationaleResult:
    rationale_id: UUID
    title: str
    quant_context: str
    quant_analysis_id: UUID
    recommended_option: str
    current_recommendation: str
    confidence_note: str
    evidence_citations: list[EvidenceCitationInput]
    overrides: list[OverrideInput]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class OverrideRationaleCommand:
    tenant_id: UUID
    rationale_id: UUID
    overridden_by: str
    reason: str
    new_recommended_option: str
