"""Recommendation Synthesis domain. `DecisionRationale` is the aggregate
this whole platform's explainability claim rests on: a recommendation that
cannot be traced to a quant source, cited evidence, and an override history
is not something this platform should be able to produce.

Deliberately NOT calling an LLM anywhere in this file — synthesis of the
*prose* explanation is an application-layer concern (it calls LLMPort); the
domain layer only knows about the structured facts that make a
recommendation auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import TenantId


class RecommendationSynthesisError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QuantSourceRef:
    """Points at the exact quant analysis this rationale is built from —
    'financial_modeling' or 'decision_analysis' plus that context's own
    aggregate id. Not a foreign key across bounded contexts (that would
    violate the boundary); just an opaque reference the reader can use to
    go look up the source analysis via that context's own API."""

    context: str  # "financial_modeling" | "decision_analysis"
    analysis_id: UUID


@dataclass(frozen=True, slots=True)
class EvidenceCitation:
    """Mirrors evidence_research.domain.entities.Citation but is this
    context's own value object — bounded contexts don't share domain
    types, even read-only ones, or a change to Citation's shape in
    evidence_research would silently ripple into this context's persisted
    data."""

    document_id: UUID
    document_title: str
    source_label: str
    excerpt: str
    relevance_score: float


@dataclass(frozen=True, slots=True)
class Override:
    """A human analyst overriding the system's recommendation. Recorded,
    never silently applied — the original recommendation is retained
    alongside it, so nothing is lost from the audit trail."""

    overridden_by: str
    reason: str
    new_recommended_option: str
    overridden_at: datetime


@dataclass(frozen=True, kw_only=True)
class DecisionRationaleCreated(DomainEvent):
    rationale_id: UUID
    recommended_option: str


@dataclass(frozen=True, kw_only=True)
class RecommendationOverridden(DomainEvent):
    rationale_id: UUID
    new_recommended_option: str
    reason: str


@dataclass(slots=True)
class DecisionRationale(AggregateRoot):
    id: UUID
    tenant_id: TenantId
    title: str
    quant_source: QuantSourceRef
    recommended_option: str
    confidence_note: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    evidence_citations: list[EvidenceCitation] = field(default_factory=list)
    overrides: list[Override] = field(default_factory=list)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        title: str,
        quant_source: QuantSourceRef,
        recommended_option: str,
        confidence_note: str,
        evidence_citations: list[EvidenceCitation] | None = None,
    ) -> DecisionRationale:
        if not title.strip():
            raise RecommendationSynthesisError("title must not be empty")
        if not recommended_option.strip():
            raise RecommendationSynthesisError("recommended_option must not be empty")

        rationale = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            title=title,
            quant_source=quant_source,
            recommended_option=recommended_option,
            confidence_note=confidence_note,
            evidence_citations=evidence_citations or [],
        )
        rationale.raise_event(
            DecisionRationaleCreated(
                tenant_id=tenant_id.value,
                rationale_id=rationale.id,
                recommended_option=recommended_option,
            )
        )
        return rationale

    @property
    def current_recommendation(self) -> str:
        """The recommendation currently in force — the latest override if
        one exists, otherwise the original quant-derived recommendation.
        The original is never mutated or deleted; this property is a view,
        not a destructive update."""
        return self.overrides[-1].new_recommended_option if self.overrides else self.recommended_option

    def override(self, *, overridden_by: str, reason: str, new_recommended_option: str) -> None:
        if not reason.strip():
            raise RecommendationSynthesisError(
                "An override without a stated reason defeats the purpose of an audit trail"
            )
        if not new_recommended_option.strip():
            raise RecommendationSynthesisError("new_recommended_option must not be empty")

        override = Override(
            overridden_by=overridden_by,
            reason=reason,
            new_recommended_option=new_recommended_option,
            overridden_at=datetime.now(UTC),
        )
        self.overrides.append(override)
        self.raise_event(
            RecommendationOverridden(
                tenant_id=self.tenant_id.value,
                rationale_id=self.id,
                new_recommended_option=new_recommended_option,
                reason=reason,
            )
        )
