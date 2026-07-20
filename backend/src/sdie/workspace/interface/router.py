from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.decision_analysis.infrastructure.repository import SqlAlchemyDecisionAnalysisRepository
from sdie.evidence_research.infrastructure.repository import SqlAlchemyDocumentRepository
from sdie.financial_modeling.infrastructure.repository import SqlAlchemyCashFlowModelRepository
from sdie.problem_framing.infrastructure.repository import SqlAlchemyFrameworkAnalysisRepository
from sdie.recommendation_synthesis.infrastructure.repository import (
    SqlAlchemyDecisionRationaleRepository,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus
from sdie.workspace.application.dto import (
    AddEvidenceCommand,
    CreateEngagementCommand,
    LinkDecisionAnalysisCommand,
    LinkFinancialModelCommand,
    LinkProblemFramingCommand,
    LinkRationaleCommand,
)
from sdie.workspace.application.use_cases import (
    AddEvidenceUseCase,
    CreateEngagementUseCase,
    GetEngagementUseCase,
    LinkDecisionAnalysisUseCase,
    LinkFinancialModelUseCase,
    LinkProblemFramingUseCase,
    LinkRationaleUseCase,
    ListEngagementsUseCase,
)
from sdie.workspace.domain.entities import WorkspaceError
from sdie.workspace.infrastructure.repository import SqlAlchemyEngagementRepository
from sdie.workspace.interface.schemas import (
    AddEvidenceRequest,
    CreateEngagementRequest,
    EngagementResponse,
    LinkDecisionAnalysisRequest,
    LinkFinancialModelRequest,
    LinkProblemFramingRequest,
    LinkRationaleRequest,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _to_response(result) -> EngagementResponse:
    return EngagementResponse(
        engagement_id=result.engagement_id,
        title=result.title,
        status=result.status,
        problem_framing_analysis_id=result.problem_framing_analysis_id,
        evidence_document_ids=result.evidence_document_ids,
        financial_model_id=result.financial_model_id,
        decision_analysis_id=result.decision_analysis_id,
        rationale_id=result.rationale_id,
        created_at=result.created_at,
    )


@router.post("/engagements", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    request: CreateEngagementRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyEngagementRepository(session)
    use_case = CreateEngagementUseCase(repository, get_event_bus())

    command = CreateEngagementCommand(tenant_id=principal.tenant_id, title=request.title)

    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _to_response(result)


@router.get("/engagements", response_model=list[EngagementResponse])
async def list_engagements(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[EngagementResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyEngagementRepository(session)
    results = await ListEngagementsUseCase(repository).execute(TenantId(principal.tenant_id))
    return [_to_response(r) for r in results]


@router.get("/engagements/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(
    engagement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyEngagementRepository(session)
    result = await GetEngagementUseCase(repository).execute(engagement_id, TenantId(principal.tenant_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return _to_response(result)


@router.post("/engagements/{engagement_id}/link-problem-framing", response_model=EngagementResponse)
async def link_problem_framing(
    engagement_id: UUID,
    request: LinkProblemFramingRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    use_case = LinkProblemFramingUseCase(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyFrameworkAnalysisRepository(session),
        get_event_bus(),
    )
    command = LinkProblemFramingCommand(
        tenant_id=principal.tenant_id, engagement_id=engagement_id, analysis_id=request.analysis_id
    )
    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)


@router.post("/engagements/{engagement_id}/link-evidence", response_model=EngagementResponse)
async def link_evidence(
    engagement_id: UUID,
    request: AddEvidenceRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    use_case = AddEvidenceUseCase(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyDocumentRepository(session),
        get_event_bus(),
    )
    command = AddEvidenceCommand(
        tenant_id=principal.tenant_id, engagement_id=engagement_id, document_id=request.document_id
    )
    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)


@router.post("/engagements/{engagement_id}/link-financial-model", response_model=EngagementResponse)
async def link_financial_model(
    engagement_id: UUID,
    request: LinkFinancialModelRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    use_case = LinkFinancialModelUseCase(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyCashFlowModelRepository(session),
        get_event_bus(),
    )
    command = LinkFinancialModelCommand(
        tenant_id=principal.tenant_id, engagement_id=engagement_id, model_id=request.model_id
    )
    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)


@router.post("/engagements/{engagement_id}/link-decision-analysis", response_model=EngagementResponse)
async def link_decision_analysis(
    engagement_id: UUID,
    request: LinkDecisionAnalysisRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    use_case = LinkDecisionAnalysisUseCase(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyDecisionAnalysisRepository(session),
        get_event_bus(),
    )
    command = LinkDecisionAnalysisCommand(
        tenant_id=principal.tenant_id, engagement_id=engagement_id, analysis_id=request.analysis_id
    )
    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)


@router.post("/engagements/{engagement_id}/link-rationale", response_model=EngagementResponse)
async def link_rationale(
    engagement_id: UUID,
    request: LinkRationaleRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EngagementResponse:
    await set_tenant_context(session, principal.tenant_id)
    use_case = LinkRationaleUseCase(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyDecisionRationaleRepository(session),
        get_event_bus(),
    )
    command = LinkRationaleCommand(
        tenant_id=principal.tenant_id, engagement_id=engagement_id, rationale_id=request.rationale_id
    )
    try:
        result = await use_case.execute(command)
        await session.commit()
    except WorkspaceError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(result)
