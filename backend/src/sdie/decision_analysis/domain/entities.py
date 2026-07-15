from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import TenantId


class DecisionAnalysisError(ValueError):
    pass


@dataclass(frozen=True, kw_only=True)
class DecisionAnalysisCompleted(DomainEvent):
    analysis_id: UUID
    method: str
    recommended_option: str


@dataclass(slots=True)
class DecisionAnalysis(AggregateRoot):
    """Aggregate root recording that a decision-science method was run and
    what it recommended. The heavy numerical work happens in stateless
    domain services (services.py) — this aggregate exists to make the
    *event* of running an analysis a first-class, auditable fact."""

    id: UUID
    tenant_id: TenantId
    title: str
    method: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(cls, *, tenant_id: TenantId, title: str, method: str) -> "DecisionAnalysis":
        if not title.strip():
            raise DecisionAnalysisError("title must not be empty")
        return cls(id=uuid4(), tenant_id=tenant_id, title=title, method=method)

    def complete(self, recommended_option: str) -> None:
        self.raise_event(
            DecisionAnalysisCompleted(
                tenant_id=self.tenant_id.value,
                analysis_id=self.id,
                method=self.method,
                recommended_option=recommended_option,
            )
        )
