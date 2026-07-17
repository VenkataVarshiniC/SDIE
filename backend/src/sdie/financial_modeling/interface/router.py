from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.financial_modeling.application.dto import (
    CashFlowInput,
    CreateCashFlowModelCommand,
    EvaluateScenariosCommand,
    ScenarioInput,
    SensitivityInput,
)
from sdie.financial_modeling.application.use_cases import (
    CreateCashFlowModelUseCase,
    EvaluateScenariosUseCase,
    GetCashFlowModelUseCase,
    ListCashFlowModelsUseCase,
    RunSensitivityAnalysisUseCase,
)
from sdie.financial_modeling.domain.entities import FinancialModelingError
from sdie.financial_modeling.infrastructure.repository import SqlAlchemyCashFlowModelRepository
from sdie.financial_modeling.interface.schemas import (
    CashFlowModelResponse,
    CreateCashFlowModelRequest,
    EvaluateScenariosRequest,
    EvaluateScenariosResponse,
    ScenarioOutcomeSchema,
    SensitivityRequest,
    SensitivityResponse,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus

router = APIRouter(prefix="/financial-modeling", tags=["financial-modeling"])


@router.post("/cash-flow-models", response_model=CashFlowModelResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_flow_model(
    request: CreateCashFlowModelRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CashFlowModelResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyCashFlowModelRepository(session)
    use_case = CreateCashFlowModelUseCase(repository, get_event_bus())

    command = CreateCashFlowModelCommand(
        tenant_id=principal.tenant_id,
        project_name=request.project_name,
        currency=request.currency,
        discount_rate_percent=request.discount_rate_percent,
        cash_flows=[CashFlowInput(cf.period, cf.amount) for cf in request.cash_flows],
        industry=request.industry,
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except FinancialModelingError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _to_response(result)


@router.get("/cash-flow-models", response_model=list[CashFlowModelResponse])
async def list_cash_flow_models(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[CashFlowModelResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyCashFlowModelRepository(session)
    use_case = ListCashFlowModelsUseCase(repository)

    results = await use_case.execute(TenantId(principal.tenant_id))
    return [_to_response(r) for r in results]


@router.get("/cash-flow-models/{model_id}", response_model=CashFlowModelResponse)
async def get_cash_flow_model(
    model_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CashFlowModelResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyCashFlowModelRepository(session)
    use_case = GetCashFlowModelUseCase(repository)

    result = await use_case.execute(model_id, TenantId(principal.tenant_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cash flow model not found")
    return _to_response(result)


def _to_response(result) -> CashFlowModelResponse:
    return CashFlowModelResponse(
        model_id=result.model_id,
        project_name=result.project_name,
        currency=result.currency,
        discount_rate_percent=result.discount_rate_percent,
        npv=result.npv,
        irr_percent=result.irr_percent,
        payback_period=result.payback_period,
        flags=result.flags,
    )


@router.post("/scenarios/evaluate", response_model=EvaluateScenariosResponse)
async def evaluate_scenarios(
    request: EvaluateScenariosRequest,
    principal: Principal = Depends(get_current_principal),
) -> EvaluateScenariosResponse:
    use_case = EvaluateScenariosUseCase()

    command = EvaluateScenariosCommand(
        tenant_id=principal.tenant_id,
        project_name=request.project_name,
        currency=request.currency,
        discount_rate_percent=request.discount_rate_percent,
        scenarios=[
            ScenarioInput(
                name=s.name,
                cash_flows=[CashFlowInput(cf.period, cf.amount) for cf in s.cash_flows],
                probability_percent=s.probability_percent,
            )
            for s in request.scenarios
        ],
    )

    try:
        result = await use_case.execute(command)
    except FinancialModelingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return EvaluateScenariosResponse(
        outcomes=[
            ScenarioOutcomeSchema(
                name=o.name, npv=o.npv, irr_percent=o.irr_percent, probability_percent=o.probability_percent
            )
            for o in result.outcomes
        ],
        probability_weighted_npv=result.probability_weighted_npv,
    )


@router.post("/sensitivity", response_model=SensitivityResponse)
async def run_sensitivity(
    request: SensitivityRequest,
    principal: Principal = Depends(get_current_principal),
) -> SensitivityResponse:
    use_case = RunSensitivityAnalysisUseCase()

    command = SensitivityInput(
        tenant_id=principal.tenant_id,
        currency=request.currency,
        discount_rate_percent=request.discount_rate_percent,
        base_cash_flows=[CashFlowInput(cf.period, cf.amount) for cf in request.base_cash_flows],
        variable_name=request.variable_name,
        variable_period=request.variable_period,
        low_amount=request.low_amount,
        base_amount=request.base_amount,
        high_amount=request.high_amount,
    )

    try:
        result = await use_case.execute(command)
    except FinancialModelingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return SensitivityResponse(
        variable=result.variable,
        npv_low=result.npv_low,
        npv_base=result.npv_base,
        npv_high=result.npv_high,
        swing=result.swing,
    )
