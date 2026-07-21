from __future__ import annotations

from uuid import UUID

from sdie.problem_framing.application.dto import (
    CreateFrameworkAnalysisCommand,
    FrameworkAnalysisResult,
    FrameworkSectionResult,
)
from sdie.problem_framing.application.ports import FrameworkAnalysisRepository
from sdie.problem_framing.domain.entities import Framework, FrameworkAnalysis, get_template
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus


def _to_result(analysis: FrameworkAnalysis) -> FrameworkAnalysisResult:
    return FrameworkAnalysisResult(
        analysis_id=analysis.id,
        title=analysis.title,
        framework=analysis.framework.value,
        entries=analysis.entries,
        completion_ratio=analysis.completion_ratio,
        created_at=analysis.created_at,
    )


class GetFrameworkTemplateUseCase:
    def execute(self, framework: str) -> list[FrameworkSectionResult]:
        sections = get_template(Framework(framework))
        return [
            FrameworkSectionResult(key=s.key, label=s.label, guiding_question=s.guiding_question)
            for s in sections
        ]


class CreateFrameworkAnalysisUseCase:
    def __init__(self, repository: FrameworkAnalysisRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: CreateFrameworkAnalysisCommand) -> FrameworkAnalysisResult:
        tenant_id = TenantId(command.tenant_id)
        analysis = FrameworkAnalysis.create(
            tenant_id=tenant_id,
            title=command.title,
            framework=Framework(command.framework),
            entries=command.entries,
        )
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())
        return _to_result(analysis)


class ListFrameworkAnalysesUseCase:
    def __init__(self, repository: FrameworkAnalysisRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[FrameworkAnalysisResult]:
        analyses = await self._repository.list_for_tenant(tenant_id)
        return [_to_result(a) for a in analyses]


class GetFrameworkAnalysisUseCase:
    def __init__(self, repository: FrameworkAnalysisRepository):
        self._repository = repository

    async def execute(self, analysis_id: UUID, tenant_id: TenantId) -> FrameworkAnalysisResult | None:
        analysis = await self._repository.get(analysis_id, tenant_id)
        return _to_result(analysis) if analysis else None


class ClearFrameworkAnalysisHistoryUseCase:
    def __init__(self, repository: FrameworkAnalysisRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> int:
        return await self._repository.delete_all_for_tenant(tenant_id)
