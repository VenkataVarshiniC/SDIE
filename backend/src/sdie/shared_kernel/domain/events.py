"""Domain event base class. Every cross-context communication happens
through events, never through one context importing another's internals."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: UUID
    correlation_id: UUID | None = None

    @property
    def event_name(self) -> str:
        return self.__class__.__name__


class AggregateRoot:
    """Base class for aggregate roots. Collects domain events raised during
    a use case so the application layer can publish them after the
    transaction commits (transactional outbox pattern in infrastructure)."""

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []

    def raise_event(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    def pull_pending_events(self) -> list[DomainEvent]:
        events, self._pending_events = self._pending_events, []
        return events
