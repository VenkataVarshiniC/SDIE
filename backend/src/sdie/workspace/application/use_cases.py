"""Workspace use cases. This is the one place in the platform where a
bounded context's application layer depends on another context's
repository port — appropriate here because orchestration validating that a
linked artifact actually exists is exactly what this context is for. The
other five contexts remain fully decoupled from each other and from
`workspace`; only `workspace` knows about them.
"""
from __future__ import annotations

from uuid import UUID

from sdie.decision_analysis.application.ports import DecisionAnalysisRepository
from sdie.evidence_research.application.ports import DocumentRepository
from sdie.financial_modeling.application.ports import CashFlowModelRepository
from sdie.problem_framing.application.ports import FrameworkAnalysisRepository
from sdie.recommendation_synthesis.application.ports import DecisionRationaleRepository
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus
from sdie.workspace.application.dto import (
    AddEvidenceCommand,
    CreateEngagementCommand,
    EngagementResult,
    LinkDecisionAnalysisCommand,
    LinkFinancialModelCommand,
    LinkProblemFramingCommand,
    LinkRationaleCommand,
)
from sdie.workspace.application.ports import EngagementRepository
from sdie.workspace.domain.entities import Engagement, WorkspaceError


def _to_result(engagement: Engagement) -> EngagementResult:
    return EngagementResult(
        engagement_id=engagement.id,
        title=engagement.title,
        status=engagement.status.value,
        problem_framing_analysis_id=engagement.problem_framing_analysis_id,
        evidence_document_ids=list(engagement.evidence_document_ids),
        financial_model_id=engagement.financial_model_id,
        decision_analysis_id=engagement.decision_analysis_id,
        rationale_id=engagement.rationale_id,
        created_at=engagement.created_at,
    )


async def _get_or_raise(
    engagement_repository: EngagementRepository, engagement_id: UUID, tenant_id: TenantId
) -> Engagement:
    engagement = await engagement_repository.get(engagement_id, tenant_id)
    if engagement is None:
        raise WorkspaceError(f"Engagement {engagement_id} not found")
    return engagement


class CreateEngagementUseCase:
    def __init__(self, repository: EngagementRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: CreateEngagementCommand) -> EngagementResult:
        engagement = Engagement.create(tenant_id=TenantId(command.tenant_id), title=command.title)
        await self._repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)


class GetEngagementUseCase:
    def __init__(self, repository: EngagementRepository):
        self._repository = repository

    async def execute(self, engagement_id: UUID, tenant_id: TenantId) -> EngagementResult | None:
        engagement = await self._repository.get(engagement_id, tenant_id)
        return _to_result(engagement) if engagement else None


class ListEngagementsUseCase:
    def __init__(self, repository: EngagementRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[EngagementResult]:
        engagements = await self._repository.list_for_tenant(tenant_id)
        return [_to_result(e) for e in engagements]


class LinkProblemFramingUseCase:
    def __init__(
        self,
        engagement_repository: EngagementRepository,
        framework_analysis_repository: FrameworkAnalysisRepository,
        event_bus: InProcessEventBus,
    ):
        self._engagement_repository = engagement_repository
        self._framework_analysis_repository = framework_analysis_repository
        self._event_bus = event_bus

    async def execute(self, command: LinkProblemFramingCommand) -> EngagementResult:
        tenant_id = TenantId(command.tenant_id)
        engagement = await _get_or_raise(self._engagement_repository, command.engagement_id, tenant_id)

        analysis = await self._framework_analysis_repository.get(command.analysis_id, tenant_id)
        if analysis is None:
            raise WorkspaceError(f"Problem framing analysis {command.analysis_id} not found")

        engagement.link_problem_framing(command.analysis_id)
        await self._engagement_repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)


class AddEvidenceUseCase:
    def __init__(
        self,
        engagement_repository: EngagementRepository,
        document_repository: DocumentRepository,
        event_bus: InProcessEventBus,
    ):
        self._engagement_repository = engagement_repository
        self._document_repository = document_repository
        self._event_bus = event_bus

    async def execute(self, command: AddEvidenceCommand) -> EngagementResult:
        tenant_id = TenantId(command.tenant_id)
        engagement = await _get_or_raise(self._engagement_repository, command.engagement_id, tenant_id)

        document = await self._document_repository.get(command.document_id, tenant_id)
        if document is None:
            raise WorkspaceError(f"Evidence document {command.document_id} not found")

        engagement.add_evidence(command.document_id)
        await self._engagement_repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)


class LinkFinancialModelUseCase:
    def __init__(
        self,
        engagement_repository: EngagementRepository,
        financial_model_repository: CashFlowModelRepository,
        event_bus: InProcessEventBus,
    ):
        self._engagement_repository = engagement_repository
        self._financial_model_repository = financial_model_repository
        self._event_bus = event_bus

    async def execute(self, command: LinkFinancialModelCommand) -> EngagementResult:
        tenant_id = TenantId(command.tenant_id)
        engagement = await _get_or_raise(self._engagement_repository, command.engagement_id, tenant_id)

        model = await self._financial_model_repository.get(command.model_id, tenant_id)
        if model is None:
            raise WorkspaceError(f"Financial model {command.model_id} not found")

        engagement.link_financial_model(command.model_id)
        await self._engagement_repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)


class LinkDecisionAnalysisUseCase:
    def __init__(
        self,
        engagement_repository: EngagementRepository,
        decision_analysis_repository: DecisionAnalysisRepository,
        event_bus: InProcessEventBus,
    ):
        self._engagement_repository = engagement_repository
        self._decision_analysis_repository = decision_analysis_repository
        self._event_bus = event_bus

    async def execute(self, command: LinkDecisionAnalysisCommand) -> EngagementResult:
        tenant_id = TenantId(command.tenant_id)
        engagement = await _get_or_raise(self._engagement_repository, command.engagement_id, tenant_id)

        analysis = await self._decision_analysis_repository.get(command.analysis_id, tenant_id)
        if analysis is None:
            raise WorkspaceError(f"Decision analysis {command.analysis_id} not found")

        engagement.link_decision_analysis(command.analysis_id)
        await self._engagement_repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)


class LinkRationaleUseCase:
    def __init__(
        self,
        engagement_repository: EngagementRepository,
        rationale_repository: DecisionRationaleRepository,
        event_bus: InProcessEventBus,
    ):
        self._engagement_repository = engagement_repository
        self._rationale_repository = rationale_repository
        self._event_bus = event_bus

    async def execute(self, command: LinkRationaleCommand) -> EngagementResult:
        tenant_id = TenantId(command.tenant_id)
        engagement = await _get_or_raise(self._engagement_repository, command.engagement_id, tenant_id)

        rationale = await self._rationale_repository.get(command.rationale_id, tenant_id)
        if rationale is None:
            raise WorkspaceError(f"Rationale {command.rationale_id} not found")

        engagement.link_rationale(command.rationale_id)
        await self._engagement_repository.save(engagement)
        await self._event_bus.publish_all(engagement.pull_pending_events())
        return _to_result(engagement)
