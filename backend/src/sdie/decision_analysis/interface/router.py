from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.decision_analysis.application.dto import (
    CriterionInput,
    DecisionOptionInput,
    DistributionInput,
    EvaluateDecisionTreeCommand,
    MCDAOptionInput,
    OutcomeInput,
    RankOptionsCommand,
    RunMonteCarloCommand,
)
from sdie.decision_analysis.application.use_cases import (
    ClearAnalysisHistoryUseCase,
    EvaluateDecisionTreeUseCase,
    GetDecisionAnalysisUseCase,
    ListDecisionAnalysesUseCase,
    RankOptionsUseCase,
    RunMonteCarloUseCase,
)
from sdie.decision_analysis.domain.entities import DecisionAnalysisError
from sdie.decision_analysis.infrastructure.repository import SqlAlchemyDecisionAnalysisRepository
from sdie.decision_analysis.interface.schemas import (
    EvaluateDecisionTreeRequest,
    EvaluateDecisionTreeResponse,
    MCDARankingSchema,
    MonteCarloResponse,
    RankOptionsRequest,
    RankOptionsResponse,
    RunMonteCarloRequest,
    WeightRobustnessSchema,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus

router = APIRouter(prefix="/decision-analysis", tags=["decision-analysis"])


class AnalysisSummarySchema(BaseModel):
    analysis_id: UUID
    title: str
    method: str
    recommended_option: str
    result_data: dict
    created_at: datetime


class ClearHistoryResponse(BaseModel):
    deleted_count: int


@router.delete("/analyses", response_model=ClearHistoryResponse)
async def clear_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ClearHistoryResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    deleted_count = await ClearAnalysisHistoryUseCase(repository).execute(
        TenantId(principal.tenant_id)
    )
    await session.commit()
    return ClearHistoryResponse(deleted_count=deleted_count)


@router.get("/analyses", response_model=list[AnalysisSummarySchema])
async def list_analyses(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[AnalysisSummarySchema]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    analyses = await ListDecisionAnalysesUseCase(repository).execute(TenantId(principal.tenant_id))
    return [
        AnalysisSummarySchema(
            analysis_id=a.id,
            title=a.title,
            method=a.method,
            recommended_option=a.recommended_option or "",
            result_data=a.result_data,
            created_at=a.created_at,
        )
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisSummarySchema)
async def get_analysis(
    analysis_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> AnalysisSummarySchema:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    analysis = await GetDecisionAnalysisUseCase(repository).execute(
        analysis_id, TenantId(principal.tenant_id)
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisSummarySchema(
        analysis_id=analysis.id,
        title=analysis.title,
        method=analysis.method,
        recommended_option=analysis.recommended_option or "",
        result_data=analysis.result_data,
        created_at=analysis.created_at,
    )


@router.post("/mcda/rank", response_model=RankOptionsResponse, status_code=status.HTTP_201_CREATED)
async def rank_options(
    request: RankOptionsRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RankOptionsResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    use_case = RankOptionsUseCase(repository, get_event_bus())

    command = RankOptionsCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        criteria=[CriterionInput(c.name, c.weight, c.higher_is_better) for c in request.criteria],
        options=[MCDAOptionInput(o.name, o.scores) for o in request.options],
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except DecisionAnalysisError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return RankOptionsResponse(
        analysis_id=result.analysis_id,
        rankings=[
            MCDARankingSchema(
                option=r.option, weighted_score=r.weighted_score, normalized_scores=r.normalized_scores
            )
            for r in result.rankings
        ],
        recommended_option=result.recommended_option,
        weight_robustness=[
            WeightRobustnessSchema(
                criterion=r.criterion,
                current_weight=r.current_weight,
                flips_at_weight=r.flips_at_weight,
                direction=r.direction,
            )
            for r in result.weight_robustness
        ],
        flags=result.flags,
    )


@router.post(
    "/decision-tree/evaluate", response_model=EvaluateDecisionTreeResponse, status_code=status.HTTP_201_CREATED
)
async def evaluate_decision_tree(
    request: EvaluateDecisionTreeRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> EvaluateDecisionTreeResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    use_case = EvaluateDecisionTreeUseCase(repository, get_event_bus())

    command = EvaluateDecisionTreeCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        options=[
            DecisionOptionInput(
                name=o.name,
                outcomes=[OutcomeInput(out.name, out.probability, out.payoff) for out in o.outcomes],
            )
            for o in request.options
        ],
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except DecisionAnalysisError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return EvaluateDecisionTreeResponse(
        analysis_id=result.analysis_id,
        ranked_options=result.ranked_options,
        recommended_option=result.recommended_option,
        expected_value_with_perfect_info=result.expected_value_with_perfect_info,
        expected_value_of_perfect_information=result.expected_value_of_perfect_information,
        flags=result.flags,
        probability_breakeven=result.probability_breakeven,
    )


@router.post("/monte-carlo/run", response_model=MonteCarloResponse, status_code=status.HTTP_201_CREATED)
async def run_monte_carlo(
    request: RunMonteCarloRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> MonteCarloResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDecisionAnalysisRepository(session)
    use_case = RunMonteCarloUseCase(repository, get_event_bus())

    command = RunMonteCarloCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        variables=[DistributionInput(v.name, v.kind, v.params) for v in request.variables],
        fixed_costs=request.fixed_costs,
        iterations=request.iterations,
        seed=request.seed,
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except DecisionAnalysisError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return MonteCarloResponse(
        analysis_id=result.analysis_id,
        iterations=result.iterations,
        seed=result.seed,
        mean=result.mean,
        std_dev=result.std_dev,
        percentile_5=result.percentile_5,
        percentile_50=result.percentile_50,
        percentile_95=result.percentile_95,
        probability_negative=result.probability_negative,
    )
