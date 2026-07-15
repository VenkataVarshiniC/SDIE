"""LLM port. Every bounded context that needs LLM synthesis (evidence
research, recommendation synthesis, problem framing) depends on this
interface, never on a concrete vendor SDK. Swapping providers — Groq today,
something else tomorrow — is an infrastructure-layer change; no use case or
domain code changes.

Structured output is the only mode exposed on purpose (see the platform's
design decision on grounded generation): callers get back a JSON string
they must validate against a Pydantic schema, never freeform prose treated
as fact. That validation, and the mandatory citation fields on anything
persisted as a domain object, is what keeps LLM output auditable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(RuntimeError):
    """Raised when the underlying provider fails or returns something the
    caller cannot use (e.g. malformed JSON in JSON mode)."""


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LLMPort(ABC):
    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Single-turn completion. `json_mode=True` requests a JSON-object
        response from the provider (where supported) — callers must still
        validate the returned string against a Pydantic schema; json_mode
        only constrains syntax, not the schema or truthfulness of claims."""
        ...
