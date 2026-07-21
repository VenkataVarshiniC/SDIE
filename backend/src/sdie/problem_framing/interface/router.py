from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.problem_framing.application.dto import CreateFrameworkAnalysisCommand
from sdie.problem_framing.application.use_cases import (
    ClearFrameworkAnalysisHistoryUseCase,
    CreateFrameworkAnalysisUseCase,
    GetFrameworkAnalysisUseCase,
    GetFrameworkTemplateUseCase,
    ListFrameworkAnalysesUseCase,
)
from sdie.problem_framing.domain.entities import ProblemFramingError
from sdie.problem_framing.infrastructure.repository import SqlAlchemyFrameworkAnalysisRepository
from sdie.problem_framing.interface.schemas import (
    ClearHistoryResponse,
    CreateFrameworkAnalysisRequest,
    FrameworkAnalysisResponse,
    FrameworkSectionSchema,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus

router = APIRouter(prefix="/problem-framing", tags=["problem-framing"])


def _to_response(result) -> FrameworkAnalysisResponse:
    return FrameworkAnalysisResponse(
        analysis_id=result.analysis_id,
        title=result.title,
        framework=result.framework,
        entries=result.entries,
        completion_ratio=result.completion_ratio,
        created_at=result.created_at,
    )


@router.get("/templates/{framework}", response_model=list[FrameworkSectionSchema])
async def get_template(framework: str) -> list[FrameworkSectionSchema]:
    try:
        sections = GetFrameworkTemplateUseCase().execute(framework)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown framework: {framework}"
        ) from exc
    return [
        FrameworkSectionSchema(key=s.key, label=s.label, guiding_question=s.guiding_question)
        for s in sections
    ]


@router.post("/analyses", response_model=FrameworkAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: CreateFrameworkAnalysisRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> FrameworkAnalysisResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyFrameworkAnalysisRepository(session)
    use_case = CreateFrameworkAnalysisUseCase(repository, get_event_bus())

    command = CreateFrameworkAnalysisCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        framework=request.framework,
        entries=request.entries,
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except ProblemFramingError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _to_response(result)


@router.get("/analyses", response_model=list[FrameworkAnalysisResponse])
async def list_analyses(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[FrameworkAnalysisResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyFrameworkAnalysisRepository(session)
    results = await ListFrameworkAnalysesUseCase(repository).execute(TenantId(principal.tenant_id))
    return [_to_response(r) for r in results]


@router.delete("/analyses", response_model=ClearHistoryResponse)
async def clear_analysis_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ClearHistoryResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyFrameworkAnalysisRepository(session)
    deleted_count = await ClearFrameworkAnalysisHistoryUseCase(repository).execute(
        TenantId(principal.tenant_id)
    )
    await session.commit()
    return ClearHistoryResponse(deleted_count=deleted_count)


@router.get("/analyses/{analysis_id}", response_model=FrameworkAnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> FrameworkAnalysisResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyFrameworkAnalysisRepository(session)
    result = await GetFrameworkAnalysisUseCase(repository).execute(analysis_id, TenantId(principal.tenant_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return _to_response(result)
