from __future__ import annotations

from uuid import UUID

from sdie.recommendation_synthesis.application.dto import (
    CreateRationaleCommand,
    EvidenceCitationInput,
    OverrideInput,
    OverrideRationaleCommand,
    RationaleResult,
)
from sdie.recommendation_synthesis.application.ports import DecisionRationaleRepository
from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    EvidenceCitation,
    QuantSourceRef,
    RecommendationSynthesisError,
)
from sdie.shared_kernel.application.ports import LLMPort
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus


def _to_result(rationale: DecisionRationale) -> RationaleResult:
    return RationaleResult(
        rationale_id=rationale.id,
        title=rationale.title,
        quant_context=rationale.quant_source.context,
        quant_analysis_id=rationale.quant_source.analysis_id,
        recommended_option=rationale.recommended_option,
        current_recommendation=rationale.current_recommendation,
        confidence_note=rationale.confidence_note,
        evidence_citations=[
            EvidenceCitationInput(
                document_id=c.document_id,
                document_title=c.document_title,
                source_label=c.source_label,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
            )
            for c in rationale.evidence_citations
        ],
        overrides=[
            OverrideInput(
                overridden_at=o.overridden_at,
                overridden_by=o.overridden_by,
                reason=o.reason,
                new_recommended_option=o.new_recommended_option,
            )
            for o in rationale.overrides
        ],
        created_at=rationale.created_at,
    )


class CreateRationaleUseCase:
    def __init__(self, repository: DecisionRationaleRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: CreateRationaleCommand) -> RationaleResult:
        tenant_id = TenantId(command.tenant_id)

        rationale = DecisionRationale.create(
            tenant_id=tenant_id,
            title=command.title,
            quant_source=QuantSourceRef(
                context=command.quant_context, analysis_id=command.quant_analysis_id
            ),
            recommended_option=command.recommended_option,
            confidence_note=command.confidence_note,
            evidence_citations=[
                EvidenceCitation(
                    document_id=c.document_id,
                    document_title=c.document_title,
                    source_label=c.source_label,
                    excerpt=c.excerpt,
                    relevance_score=c.relevance_score,
                )
                for c in command.evidence_citations
            ],
        )

        await self._repository.save(rationale)
        await self._event_bus.publish_all(rationale.pull_pending_events())
        return _to_result(rationale)


class OverrideRationaleUseCase:
    def __init__(self, repository: DecisionRationaleRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: OverrideRationaleCommand) -> RationaleResult:
        tenant_id = TenantId(command.tenant_id)
        rationale = await self._repository.get(command.rationale_id, tenant_id)
        if rationale is None:
            raise RecommendationSynthesisError(f"Rationale {command.rationale_id} not found")

        rationale.override(
            overridden_by=command.overridden_by,
            reason=command.reason,
            new_recommended_option=command.new_recommended_option,
        )

        await self._repository.save(rationale)
        await self._event_bus.publish_all(rationale.pull_pending_events())
        return _to_result(rationale)


class GetRationaleUseCase:
    def __init__(self, repository: DecisionRationaleRepository):
        self._repository = repository

    async def execute(self, rationale_id: UUID, tenant_id: TenantId) -> RationaleResult | None:
        rationale = await self._repository.get(rationale_id, tenant_id)
        return _to_result(rationale) if rationale else None


class ListRationalesUseCase:
    def __init__(self, repository: DecisionRationaleRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[RationaleResult]:
        rationales = await self._repository.list_for_tenant(tenant_id)
        return [_to_result(r) for r in rationales]


class GenerateNarrativeUseCase:
    """Turns a structured DecisionRationale into prose — the one place in
    this platform that calls an LLM, and only ever over facts already
    proven out by the rest of the system (the quant recommendation, its
    confidence note, and citations that already have exact excerpts and
    source labels attached). The system prompt is deliberately strict about
    not introducing anything beyond those facts."""

    _SYSTEM_PROMPT = (
        "You write concise executive memos for strategic decisions. You are given a "
        "structured decision rationale: a recommendation, a confidence note, cited evidence "
        "(each with an exact excerpt and source label), and any analyst overrides. "
        "Write a 3-4 paragraph memo in professional prose. "
        "STRICT RULES: (1) Only state facts present in the input — never invent statistics, "
        "sources, or claims not given to you. (2) When referencing evidence, attribute it by "
        "its source_label exactly as given. (3) If overrides exist, the memo must lead with "
        "the current (overridden) recommendation and explain why it differs from the original "
        "quant-derived one, using the override's stated reason. (4) Do not use bullet points — "
        "write connected prose, as if for a partner review."
    )

    def __init__(self, repository: DecisionRationaleRepository, llm: LLMPort):
        self._repository = repository
        self._llm = llm

    async def execute(self, rationale_id: UUID, tenant_id: TenantId) -> str:
        rationale = await self._repository.get(rationale_id, tenant_id)
        if rationale is None:
            raise RecommendationSynthesisError(f"Rationale {rationale_id} not found")

        user_prompt = self._build_prompt(rationale)
        response = await self._llm.complete(
            system_prompt=self._SYSTEM_PROMPT, user_prompt=user_prompt, json_mode=False
        )
        return response.content

    @staticmethod
    def _build_prompt(rationale: DecisionRationale) -> str:
        lines = [
            f"Title: {rationale.title}",
            f"Original recommendation (from {rationale.quant_source.context}, "
            f"analysis {rationale.quant_source.analysis_id}): {rationale.recommended_option}",
            f"Confidence note: {rationale.confidence_note}",
            f"Current recommendation in force: {rationale.current_recommendation}",
        ]

        if rationale.evidence_citations:
            lines.append("\nCited evidence:")
            for c in rationale.evidence_citations:
                lines.append(f'- [{c.source_label}] "{c.excerpt}"')

        if rationale.overrides:
            lines.append("\nOverride history:")
            for o in rationale.overrides:
                lines.append(
                    f"- {o.overridden_by} changed the recommendation to "
                    f"'{o.new_recommended_option}' because: {o.reason}"
                )

        return "\n".join(lines)
