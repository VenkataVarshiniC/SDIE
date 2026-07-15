"""Groq adapter implementing LLMPort. This is the only file in the codebase
allowed to import the `groq` SDK — everything else depends on LLMPort.

Groq is used here for its free/low-cost tier and low-latency inference
(LPU-backed), running open-weight models (Llama, etc.) rather than a
proprietary model API. Tradeoff worth being explicit about: model quality
and instruction-following on complex synthesis tasks can lag top-tier
proprietary models, which matters more for the Recommendation Synthesis
and Evidence Research contexts than for e.g. simple extraction tasks.
Because everything routes through LLMPort, upgrading specific use cases to
a stronger provider later is a per-adapter swap, not a rewrite.
"""
from __future__ import annotations

import json
import logging

from groq import AsyncGroq
from groq import GroqError as _GroqSDKError

from sdie.config import get_settings
from sdie.shared_kernel.application.ports import LLMError, LLMPort, LLMResponse

logger = logging.getLogger(__name__)


class GroqLLMClient(LLMPort):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        resolved_key = api_key or settings.groq_api_key
        if not resolved_key:
            raise LLMError(
                "SDIE_GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
                "and put it in backend/.env"
            )
        self._model = model or settings.groq_model
        self._client = AsyncGroq(api_key=resolved_key)

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else None,
            )
        except _GroqSDKError as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc

        choice = response.choices[0]
        content = choice.message.content or ""

        if json_mode:
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise LLMError(
                    f"Groq returned invalid JSON despite json_mode=True: {exc}"
                ) from exc

        usage = response.usage
        return LLMResponse(
            content=content,
            model=response.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
