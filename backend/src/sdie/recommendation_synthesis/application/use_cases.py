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
