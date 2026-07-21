from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.decision_analysis.infrastructure.repository import SqlAlchemyDecisionAnalysisRepository
from sdie.financial_modeling.infrastructure.repository import SqlAlchemyCashFlowModelRepository
from sdie.recommendation_synthesis.application.dto import (
    CreateRationaleCommand,
    EvidenceCitationInput,
    OverrideRationaleCommand,
)
from sdie.recommendation_synthesis.application.use_cases import (
    ClearRationaleHistoryUseCase,
    CreateRationaleUseCase,
    GenerateNarrativeUseCase,
    GenerateOnePagerUseCase,
    GetRationaleUseCase,
    ListRationalesUseCase,
    OverrideRationaleUseCase,
)
from sdie.recommendation_synthesis.domain.entities import RecommendationSynthesisError
from sdie.recommendation_synthesis.infrastructure.renderer_provider import get_one_pager_renderer
from sdie.recommendation_synthesis.infrastructure.repository import (
    SqlAlchemyDecisionRationaleRepository,
)
from sdie.recommendation_synthesis.interface.schemas import (
    ClearHistoryResponse,
    CreateRationaleRequest,
    EvidenceCitationSchema,
    NarrativeResponse,
    OverrideRationaleRequest,
    OverrideSchema,
    RationaleResponse,
)
from sdie.shared_kernel.application.ports import LLMError, LLMPort
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus
from sdie.shared_kernel.infrastructure.llm.provider import get_llm_client

router = APIRouter(prefix="/recommendation-synthesis", tags=["recommendation-synthesis"])


def _to_response(result) -> RationaleResponse:
    return RationaleResponse(
        rationale_id=result.rationale_id,
        title=result.title,
        quant_context=result.quant_context,
        quant_analysis_id=result.quant_analysis_id,
        recommended_option=result.recommended_option,
        current_recommendation=result.current_recommendation,
        confidence_note=result.confidence_note,
        evidence_citations=[
            EvidenceCitationSchema(
                document_id=c.document_id,
                document_title=c.document_title,
                source_label=c.source_label,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
            )
            for c in result.evidence_citations
        ],
        overrides=[
            OverrideSchema(
                overridden_by=o.overridden_by,
                reason=o.reason,
                new_recommended_option=o.new_recommended_option,
                overridden_at=o.overridden_at,
            )
            for o in result.overrides
        ],
        created_at=result.created_at,
    )


@router.post("/rationales", response_model=RationaleResponse, status_code=status.HTTP_201_CREATED)
async def create_rationale(
    request: CreateRationaleRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RationaleResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    use_case = CreateRationaleUseCase(repository, get_event_bus())

    command = CreateRationaleCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        quant_context=request.quant_context,
        quant_analysis_id=request.quant_analysis_id,
        recommended_option=request.recommended_option,
        confidence_note=request.confidence_note,
        evidence_citations=[
            EvidenceCitationInput(
                document_id=c.document_id,
                document_title=c.document_title,
                source_label=c.source_label,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
            )
            for c in request.evidence_citations
        ],
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except RecommendationSynthesisError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _to_response(result)


@router.get("/rationales", response_model=list[RationaleResponse])
async def list_rationales(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[RationaleResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    results = await ListRationalesUseCase(repository).execute(TenantId(principal.tenant_id))
    return [_to_response(r) for r in results]


@router.delete("/rationales", response_model=ClearHistoryResponse)
async def clear_rationale_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ClearHistoryResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    deleted_count = await ClearRationaleHistoryUseCase(repository).execute(TenantId(principal.tenant_id))
    await session.commit()
    return ClearHistoryResponse(deleted_count=deleted_count)


@router.get("/rationales/{rationale_id}", response_model=RationaleResponse)
async def get_rationale(
    rationale_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RationaleResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    result = await GetRationaleUseCase(repository).execute(rationale_id, TenantId(principal.tenant_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rationale not found")
    return _to_response(result)


@router.post("/rationales/{rationale_id}/override", response_model=RationaleResponse)
async def override_rationale(
    rationale_id: UUID,
    request: OverrideRationaleRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RationaleResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    use_case = OverrideRationaleUseCase(repository, get_event_bus())

    command = OverrideRationaleCommand(
        tenant_id=principal.tenant_id,
        rationale_id=rationale_id,
        overridden_by=request.overridden_by,
        reason=request.reason,
        new_recommended_option=request.new_recommended_option,
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except RecommendationSynthesisError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _to_response(result)


@router.post("/rationales/{rationale_id}/narrative", response_model=NarrativeResponse)
async def generate_narrative(
    rationale_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    llm: LLMPort = Depends(get_llm_client),
) -> NarrativeResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionRationaleRepository(session)
    use_case = GenerateNarrativeUseCase(repository, llm)

    try:
        narrative = await use_case.execute(rationale_id, TenantId(principal.tenant_id))
    except RecommendationSynthesisError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return NarrativeResponse(rationale_id=rationale_id, narrative=narrative)


@router.get("/rationales/{rationale_id}/one-pager")
async def generate_one_pager(
    rationale_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Generates a board-ready one-page PDF memo. This is the one endpoint
    in the platform allowed to reach into another bounded context's
    repository directly — composing across contexts for a presentation
    artifact is an interface-layer responsibility, not a domain or
    application one. The rationale itself never depends on those
    repositories; only this route does, to fetch the numbers behind the
    'SUPPORTING ANALYSIS' section."""
    await set_tenant_context(session, principal.tenant_id)
    rationale_repository = SqlAlchemyDecisionRationaleRepository(session)

    tenant_id = TenantId(principal.tenant_id)
    rationale = await GetRationaleUseCase(rationale_repository).execute(rationale_id, tenant_id)
    if rationale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rationale not found")

    supporting_data: dict | None = None
    if rationale.quant_context == "decision_analysis":
        analysis = await SqlAlchemyDecisionAnalysisRepository(session).get(
            rationale.quant_analysis_id, tenant_id
        )
        supporting_data = analysis.result_data if analysis else None
    elif rationale.quant_context == "financial_modeling":
        model = await SqlAlchemyCashFlowModelRepository(session).get(
            rationale.quant_analysis_id, tenant_id
        )
        if model is not None:
            supporting_data = {
                "npv": str(model.npv.amount) if model.npv else None,
                "irr_percent": str(model.irr.as_percent()) if model.irr else None,
                "payback_period": str(model.payback_period) if model.payback_period else None,
            }

    use_case = GenerateOnePagerUseCase(rationale_repository, get_one_pager_renderer())
    try:
        pdf_bytes = await use_case.execute(rationale_id, tenant_id, supporting_data)
    except RecommendationSynthesisError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    filename = f"decision-memo-{rationale_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
