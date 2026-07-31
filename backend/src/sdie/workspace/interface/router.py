from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.decision_analysis.infrastructure.repository import SqlAlchemyDecisionAnalysisRepository
from sdie.evidence_research.infrastructure.repository import SqlAlchemyDocumentRepository
from sdie.financial_modeling.application.use_cases import GetCashFlowModelUseCase
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
    DecisionAnalysisDeckSection,
    EngagementDeckData,
    EvidenceDocumentSummary,
    FinancialModelDeckSection,
    LinkDecisionAnalysisCommand,
    LinkFinancialModelCommand,
    LinkProblemFramingCommand,
    LinkRationaleCommand,
    ProblemFramingDeckSection,
    SynthesisDeckSection,
)
from sdie.workspace.application.use_cases import (
    AddEvidenceUseCase,
    ClearEngagementHistoryUseCase,
    CreateEngagementUseCase,
    DeleteEngagementUseCase,
    GenerateEngagementDeckUseCase,
    GetEngagementUseCase,
    LinkDecisionAnalysisUseCase,
    LinkFinancialModelUseCase,
    LinkProblemFramingUseCase,
    LinkRationaleUseCase,
    ListEngagementsUseCase,
)
from sdie.workspace.domain.entities import WorkspaceError
from sdie.workspace.infrastructure.deck_renderer_provider import get_engagement_deck_renderer
from sdie.workspace.infrastructure.repository import SqlAlchemyEngagementRepository
from sdie.workspace.interface.schemas import (
    AddEvidenceRequest,
    ClearHistoryResponse,
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


@router.delete("/engagements", response_model=ClearHistoryResponse)
async def clear_engagement_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ClearHistoryResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyEngagementRepository(session)
    deleted_count = await ClearEngagementHistoryUseCase(repository).execute(TenantId(principal.tenant_id))
    await session.commit()
    return ClearHistoryResponse(deleted_count=deleted_count)


@router.delete("/engagements/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(
    engagement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> None:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyEngagementRepository(session)
    deleted = await DeleteEngagementUseCase(repository).execute(
        engagement_id, TenantId(principal.tenant_id)
    )
    await session.commit()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")


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


def _truncate(text: str, max_chars: int = 320) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + "\u2026"


@router.get("/engagements/{engagement_id}/deck")
async def generate_engagement_deck(
    engagement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Generates the full multi-section case deck for an engagement. This
    is the one workspace endpoint allowed to reach into all five other
    contexts' repositories directly — composing across contexts for a
    presentation artifact is an interface-layer responsibility (see the
    identical reasoning on recommendation_synthesis's one-pager endpoint).
    Sections for stages that aren't linked yet are simply omitted."""
    await set_tenant_context(session, principal.tenant_id)
    tenant_id = TenantId(principal.tenant_id)

    engagement_repository = SqlAlchemyEngagementRepository(session)
    engagement = await GetEngagementUseCase(engagement_repository).execute(engagement_id, tenant_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")

    deck_data = EngagementDeckData()

    if engagement.problem_framing_analysis_id:
        analysis = await SqlAlchemyFrameworkAnalysisRepository(session).get(
            engagement.problem_framing_analysis_id, tenant_id
        )
        if analysis is not None:
            deck_data = EngagementDeckData(
                problem_framing=ProblemFramingDeckSection(
                    title=analysis.title,
                    framework=analysis.framework.value,
                    entries=analysis.entries,
                    completion_ratio=analysis.completion_ratio,
                ),
                evidence_documents=deck_data.evidence_documents,
                financial_model=deck_data.financial_model,
                decision_analysis=deck_data.decision_analysis,
                synthesis=deck_data.synthesis,
            )

    if engagement.evidence_document_ids:
        document_repository = SqlAlchemyDocumentRepository(session)
        # Single batched query instead of one round trip per document —
        # the loop version was a classic N+1 (N network round trips to the
        # database for N linked documents); get_many() fetches them all at
        # once and we just re-order to match the engagement's link order.
        fetched_documents = await document_repository.get_many(
            list(engagement.evidence_document_ids), tenant_id
        )
        documents_by_id = {d.id: d for d in fetched_documents}
        summaries = [
            EvidenceDocumentSummary(
                title=documents_by_id[document_id].title,
                source_label=documents_by_id[document_id].source_label,
                excerpt=_truncate(documents_by_id[document_id].content),
            )
            for document_id in engagement.evidence_document_ids
            if document_id in documents_by_id
        ]
        deck_data = EngagementDeckData(
            problem_framing=deck_data.problem_framing,
            evidence_documents=summaries,
            financial_model=deck_data.financial_model,
            decision_analysis=deck_data.decision_analysis,
            synthesis=deck_data.synthesis,
        )

    if engagement.financial_model_id:
        model_result = await GetCashFlowModelUseCase(
            SqlAlchemyCashFlowModelRepository(session)
        ).execute(engagement.financial_model_id, tenant_id)
        if model_result is not None:
            deck_data = EngagementDeckData(
                problem_framing=deck_data.problem_framing,
                evidence_documents=deck_data.evidence_documents,
                financial_model=FinancialModelDeckSection(
                    project_name=model_result.project_name,
                    npv=f"{model_result.currency} {model_result.npv:,.0f}",
                    irr_percent=f"{model_result.irr_percent:.1f}%" if model_result.irr_percent else None,
                    payback_period=(
                        f"{model_result.payback_period:.1f} yrs" if model_result.payback_period else None
                    ),
                    flags=model_result.flags,
                ),
                decision_analysis=deck_data.decision_analysis,
                synthesis=deck_data.synthesis,
            )

    if engagement.decision_analysis_id:
        analysis = await SqlAlchemyDecisionAnalysisRepository(session).get(
            engagement.decision_analysis_id, tenant_id
        )
        if analysis is not None:
            deck_data = EngagementDeckData(
                problem_framing=deck_data.problem_framing,
                evidence_documents=deck_data.evidence_documents,
                financial_model=deck_data.financial_model,
                decision_analysis=DecisionAnalysisDeckSection(
                    title=analysis.title,
                    method=analysis.method,
                    recommended_option=analysis.recommended_option or "",
                    result_data=analysis.result_data,
                ),
                synthesis=deck_data.synthesis,
            )

    if engagement.rationale_id:
        rationale = await SqlAlchemyDecisionRationaleRepository(session).get(
            engagement.rationale_id, tenant_id
        )
        if rationale is not None:
            deck_data = EngagementDeckData(
                problem_framing=deck_data.problem_framing,
                evidence_documents=deck_data.evidence_documents,
                financial_model=deck_data.financial_model,
                decision_analysis=deck_data.decision_analysis,
                synthesis=SynthesisDeckSection(
                    title=rationale.title,
                    recommended_option=rationale.recommended_option,
                    current_recommendation=rationale.current_recommendation,
                    confidence_note=rationale.confidence_note,
                    evidence_citations=[
                        EvidenceDocumentSummary(
                            title=c.document_title, source_label=c.source_label, excerpt=c.excerpt
                        )
                        for c in rationale.evidence_citations
                    ],
                    override_count=len(rationale.overrides),
                ),
            )

    use_case = GenerateEngagementDeckUseCase(engagement_repository, get_engagement_deck_renderer())
    try:
        pdf_bytes = await use_case.execute(engagement_id, tenant_id, deck_data)
    except WorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    filename = f"case-deck-{engagement_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
