from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
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
    EvaluateDecisionTreeUseCase,
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
)
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus

router = APIRouter(prefix="/decision-analysis", tags=["decision-analysis"])


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
            MCDARankingSchema(option=r.option, weighted_score=r.weighted_score, normalized_scores=r.normalized_scores)
            for r in result.rankings
        ],
        recommended_option=result.recommended_option,
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
