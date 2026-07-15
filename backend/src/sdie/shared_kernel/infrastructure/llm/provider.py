"""FastAPI dependency wiring for LLMPort. Routers that need LLM synthesis
depend on `get_llm_client`, never on GroqLLMClient directly — keeps the
interface/ layer honest to the hexagonal-architecture boundary."""
from __future__ import annotations

from functools import lru_cache

from sdie.shared_kernel.application.ports import LLMPort
from sdie.shared_kernel.infrastructure.llm.groq_adapter import GroqLLMClient


@lru_cache
def get_llm_client() -> LLMPort:
    return GroqLLMClient()
