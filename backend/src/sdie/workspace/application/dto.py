from __future__ import annotations

from dataclasses import dataclass, field
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


# --- full engagement deck export ---
#
# These are deliberately plain, presentation-shaped structs rather than
# each source context's own DTOs (FrameworkAnalysisResult,
# CashFlowModelResult, etc.) — the same pragmatic call made for
# recommendation_synthesis's one-pager `supporting_data: dict`. Building
# the deck against each context's real DTOs would couple workspace's
# rendering to five other contexts' internal shapes; a plain struct the
# router populates keeps the coupling at the router (interface) layer,
# where cross-context composition is already the accepted pattern.


@dataclass(frozen=True, slots=True)
class ProblemFramingDeckSection:
    title: str
    framework: str
    entries: dict[str, list[str]]
    completion_ratio: float


@dataclass(frozen=True, slots=True)
class EvidenceDocumentSummary:
    title: str
    source_label: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class FinancialModelDeckSection:
    project_name: str
    npv: str
    irr_percent: str | None
    payback_period: str | None
    flags: list[str]


@dataclass(frozen=True, slots=True)
class DecisionAnalysisDeckSection:
    title: str
    method: str
    recommended_option: str
    result_data: dict


@dataclass(frozen=True, slots=True)
class SynthesisDeckSection:
    title: str
    recommended_option: str
    current_recommendation: str
    confidence_note: str
    evidence_citations: list[EvidenceDocumentSummary]
    override_count: int


@dataclass(frozen=True, slots=True)
class EngagementDeckData:
    problem_framing: ProblemFramingDeckSection | None = None
    evidence_documents: list[EvidenceDocumentSummary] = field(default_factory=list)
    financial_model: FinancialModelDeckSection | None = None
    decision_analysis: DecisionAnalysisDeckSection | None = None
    synthesis: SynthesisDeckSection | None = None
