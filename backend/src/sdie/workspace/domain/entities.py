"""Workspace domain. `Engagement` is the seam that turns five independent
bounded contexts into one coherent case: it holds references (never
foreign keys — just opaque IDs, the same pattern recommendation_synthesis
uses for its `QuantSourceRef`) to artifacts produced by problem_framing,
evidence_research, financial_modeling, decision_analysis, and
recommendation_synthesis, plus a `status` that summarizes how far the
engagement has progressed.

Ordering decision (documented per the brief): stages are NOT enforced in a
strict sequence. A case team routinely gathers evidence before finishing
problem framing, or runs financial modeling and decision analysis in
parallel — forcing FRAMING -> EVIDENCE_GATHERING -> QUANT_ANALYSIS as a
rigid gate would fight how case teams actually work and add friction for
no real integrity benefit (unlike, say, a payment can't ship before it's
authorized — there's no equivalent hard dependency here). Instead,
`status` is a *computed* progress indicator, recalculated after every
link, that reflects the furthest stage reached given whatever has been
linked so far, in whatever order it happened. The one rule that IS
enforced is the honest one: `status` can only reach COMPLETE once there is
both a rationale AND at least one quant analysis backing it (financial
model or decision analysis) — a "complete" engagement without either
isn't a defensible recommendation, so COMPLETE is earned, not just
declared.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import TenantId


class WorkspaceError(ValueError):
    pass


class EngagementStatus(str, Enum):
    FRAMING = "framing"
    EVIDENCE_GATHERING = "evidence_gathering"
    QUANT_ANALYSIS = "quant_analysis"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"


@dataclass(frozen=True, kw_only=True)
class EngagementCreated(DomainEvent):
    engagement_id: UUID
    title: str


@dataclass(frozen=True, kw_only=True)
class EngagementStageCompleted(DomainEvent):
    engagement_id: UUID
    stage: str


@dataclass(slots=True)
class Engagement(AggregateRoot):
    id: UUID
    tenant_id: TenantId
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: EngagementStatus = EngagementStatus.FRAMING
    problem_framing_analysis_id: UUID | None = None
    evidence_document_ids: list[UUID] = field(default_factory=list)
    financial_model_id: UUID | None = None
    decision_analysis_id: UUID | None = None
    rationale_id: UUID | None = None

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(cls, *, tenant_id: TenantId, title: str) -> Engagement:
        if not title.strip():
            raise WorkspaceError("title must not be empty")

        engagement = cls(id=uuid4(), tenant_id=tenant_id, title=title)
        engagement.raise_event(
            EngagementCreated(tenant_id=tenant_id.value, engagement_id=engagement.id, title=title)
        )
        return engagement

    def link_problem_framing(self, analysis_id: UUID) -> None:
        self.problem_framing_analysis_id = analysis_id
        self._advance("problem_framing")

    def add_evidence(self, document_id: UUID) -> None:
        if document_id not in self.evidence_document_ids:
            self.evidence_document_ids.append(document_id)
        self._advance("evidence")

    def link_financial_model(self, model_id: UUID) -> None:
        self.financial_model_id = model_id
        self._advance("financial_model")

    def link_decision_analysis(self, analysis_id: UUID) -> None:
        self.decision_analysis_id = analysis_id
        self._advance("decision_analysis")

    def link_rationale(self, rationale_id: UUID) -> None:
        self.rationale_id = rationale_id
        self._advance("rationale")

    def _advance(self, stage: str) -> None:
        self.status = self._compute_status()
        self.raise_event(
            EngagementStageCompleted(tenant_id=self.tenant_id.value, engagement_id=self.id, stage=stage)
        )

    def _compute_status(self) -> EngagementStatus:
        has_quant = self.financial_model_id is not None or self.decision_analysis_id is not None
        if self.rationale_id is not None and has_quant:
            return EngagementStatus.COMPLETE
        if self.rationale_id is not None:
            return EngagementStatus.SYNTHESIS
        if has_quant:
            return EngagementStatus.QUANT_ANALYSIS
        if self.evidence_document_ids or self.problem_framing_analysis_id is not None:
            return EngagementStatus.EVIDENCE_GATHERING
        return EngagementStatus.FRAMING
