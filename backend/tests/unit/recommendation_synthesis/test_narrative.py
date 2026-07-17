from uuid import uuid4

import pytest

from sdie.recommendation_synthesis.application.ports import DecisionRationaleRepository
from sdie.recommendation_synthesis.application.use_cases import GenerateNarrativeUseCase
from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    EvidenceCitation,
    QuantSourceRef,
    RecommendationSynthesisError,
)
from sdie.shared_kernel.application.ports import LLMPort, LLMResponse
from sdie.shared_kernel.domain.value_objects import TenantId


class FakeRepository(DecisionRationaleRepository):
    def __init__(self, rationale: DecisionRationale | None):
        self._rationale = rationale

    async def save(self, rationale):
        self._rationale = rationale

    async def get(self, rationale_id, tenant_id):
        return self._rationale

    async def list_for_tenant(self, tenant_id):
        return [self._rationale] if self._rationale else []


class FakeLLM(LLMPort):
    def __init__(self, response_text: str = "A generated memo."):
        self.response_text = response_text
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    async def complete(self, *, system_prompt, user_prompt, json_mode=False, temperature=0.2, max_tokens=2000):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return LLMResponse(
            content=self.response_text, model="fake-model", prompt_tokens=10, completion_tokens=5
        )


def make_rationale(with_override: bool = False) -> DecisionRationale:
    rationale = DecisionRationale.create(
        tenant_id=TenantId(uuid4()),
        title="Market entry approach",
        quant_source=QuantSourceRef(context="decision_analysis", analysis_id=uuid4()),
        recommended_option="Acquire competitor",
        confidence_note="Margin of 0.4 on the MCDA score",
        evidence_citations=[
            EvidenceCitation(
                document_id=uuid4(),
                document_title="Gartner report",
                source_label="Gartner 2026, p.14",
                excerpt="Acquisitions saw 23% faster time-to-revenue.",
                relevance_score=0.09,
            )
        ],
    )
    if with_override:
        rationale.override(
            overridden_by="jane.analyst",
            reason="Regulatory risk not captured in weights",
            new_recommended_option="Partner / JV",
        )
    return rationale


class TestGenerateNarrativeUseCase:
    async def test_calls_llm_with_grounded_prompt_and_returns_content(self):
        rationale = make_rationale()
        repo = FakeRepository(rationale)
        llm = FakeLLM(response_text="This is the memo.")
        use_case = GenerateNarrativeUseCase(repo, llm)

        result = await use_case.execute(rationale.id, rationale.tenant_id)

        assert result == "This is the memo."
        assert llm.last_user_prompt is not None
        assert "Gartner 2026, p.14" in llm.last_user_prompt
        assert "Acquire competitor" in llm.last_user_prompt

    async def test_prompt_includes_override_history_when_present(self):
        rationale = make_rationale(with_override=True)
        repo = FakeRepository(rationale)
        llm = FakeLLM()
        use_case = GenerateNarrativeUseCase(repo, llm)

        await use_case.execute(rationale.id, rationale.tenant_id)

        assert "jane.analyst" in llm.last_user_prompt
        assert "Regulatory risk not captured in weights" in llm.last_user_prompt
        assert "Partner / JV" in llm.last_user_prompt

    async def test_raises_when_rationale_not_found(self):
        repo = FakeRepository(None)
        llm = FakeLLM()
        use_case = GenerateNarrativeUseCase(repo, llm)

        with pytest.raises(RecommendationSynthesisError):
            await use_case.execute(uuid4(), TenantId(uuid4()))
