"""In-process event bus. Modular-monolith today; the publish/subscribe
interface is identical to what a Kafka/Redpanda-backed implementation would
expose, so extracting a context into its own service later means swapping
this adapter, not rewriting call sites."""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sdie.shared_kernel.domain.events import DomainEvent

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[DomainEvent], Awaitable[None]]


class InProcessEventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            logger.debug("No subscribers for %s", event.event_name)
            return
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s (id=%s) — event bus does not "
                    "retry; failures must be handled via the outbox/DLQ in production",
                    handler,
                    event.event_name,
                    event.event_id,
                )

    async def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)


_bus = InProcessEventBus()


def get_event_bus() -> InProcessEventBus:
    return _bus
