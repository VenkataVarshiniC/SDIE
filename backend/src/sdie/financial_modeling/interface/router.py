from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.financial_modeling.application.dto import (
    CashFlowInput,
    CreateCashFlowModelCommand,
    EvaluateScenariosCommand,
    ScenarioInput,
    SensitivityInput,
)
from sdie.financial_modeling.application.planning import (
    AnalyzeOperatingForecastCommand,
    AnalyzeOperatingForecastUseCase,
    InvestmentOpportunityInput,
    OperatingForecastInput,
    OperatingForecastScenarioInput,
    OptimizeCapitalAllocationCommand,
    OptimizeCapitalAllocationUseCase,
)
from sdie.financial_modeling.application.use_cases import (
    CreateCashFlowModelUseCase,
    EvaluateScenariosUseCase,
    GetCashFlowModelUseCase,
    ListCashFlowModelsUseCase,
    RunSensitivityAnalysisUseCase,
)
from sdie.financial_modeling.domain.entities import FinancialModelingError
from sdie.financial_modeling.infrastructure.reportlab_investment_memo import (
    ReportLabInvestmentMemoRenderer,
)
from sdie.financial_modeling.infrastructure.repository import SqlAlchemyCashFlowModelRepository
from sdie.financial_modeling.interface.schemas import (
    AnalyzeOperatingForecastRequest,
    AnalyzeOperatingForecastResponse,
    CapitalAllocationRequest,
    CapitalAllocationResponse,
    CashFlowModelResponse,
    CreateCashFlowModelRequest,
    EvaluateScenariosRequest,
    EvaluateScenariosResponse,
    ExecutiveInvestmentMemoRequest,
    ForecastScenarioOutcomeSchema,
    ForecastSensitivityPointSchema,
    ForecastValuationSchema,
    ForecastYearSchema,
    InvestmentMetricsSchema,
    OperatingForecastAssumptionsSchema,
    PortfolioCashFlowSchema,
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


@router.post("/operating-forecast/analyze", response_model=AnalyzeOperatingForecastResponse)
async def analyze_operating_forecast(
    request: AnalyzeOperatingForecastRequest,
    _principal: Principal = Depends(get_current_principal),
) -> AnalyzeOperatingForecastResponse:
    use_case = AnalyzeOperatingForecastUseCase()
    try:
        result = await use_case.execute(_forecast_command(request))
    except FinancialModelingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _forecast_response(result)


@router.post("/capital-allocation/optimize", response_model=CapitalAllocationResponse)
async def optimize_investment_portfolio(
    request: CapitalAllocationRequest,
    _principal: Principal = Depends(get_current_principal),
) -> CapitalAllocationResponse:
    use_case = OptimizeCapitalAllocationUseCase()
    try:
        result = await use_case.execute(_allocation_command(request))
    except FinancialModelingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _allocation_response(request, result)


@router.post("/capital-allocation/executive-memo")
async def generate_executive_investment_memo(
    request: ExecutiveInvestmentMemoRequest,
    _principal: Principal = Depends(get_current_principal),
) -> Response:
    try:
        allocation = await OptimizeCapitalAllocationUseCase().execute(
            _allocation_command(request.allocation)
        )
        forecast = await AnalyzeOperatingForecastUseCase().execute(
            _forecast_command(request.forecast_analysis)
        )
    except FinancialModelingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    content = ReportLabInvestmentMemoRenderer().render(
        portfolio_name=request.allocation.portfolio_name,
        business_context=request.allocation.business_context,
        allocation=allocation,
        forecast=forecast,
    )
    filename = request.allocation.portfolio_name.lower().replace(" ", "-")[:80]
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}-investment-memo.pdf"'},
    )


def _forecast_input(item: OperatingForecastAssumptionsSchema) -> OperatingForecastInput:
    return OperatingForecastInput(
        project_name=item.project_name,
        currency=item.currency,
        base_revenue=item.base_revenue,
        initial_investment=item.initial_investment,
        revenue_growth_percent_by_year=tuple(item.revenue_growth_percent_by_year),
        gross_margin_percent=item.gross_margin_percent,
        operating_expense_percent_of_revenue=item.operating_expense_percent_of_revenue,
        depreciation_amortization_percent_of_revenue=(
            item.depreciation_amortization_percent_of_revenue
        ),
        tax_rate_percent=item.tax_rate_percent,
        capital_expenditure_percent_of_revenue=(
            item.capital_expenditure_percent_of_revenue
        ),
        working_capital_percent_of_revenue=item.working_capital_percent_of_revenue,
        discount_rate_percent=item.discount_rate_percent,
    )


def _forecast_command(request: AnalyzeOperatingForecastRequest) -> AnalyzeOperatingForecastCommand:
    return AnalyzeOperatingForecastCommand(
        base_case=_forecast_input(request.base_case),
        scenarios=tuple(
            OperatingForecastScenarioInput(
                name=scenario.name,
                probability_percent=scenario.probability_percent,
                assumptions=_forecast_input(scenario.assumptions),
            )
            for scenario in request.scenarios
        ),
    )


def _forecast_response(result) -> AnalyzeOperatingForecastResponse:
    base = result.base_case
    return AnalyzeOperatingForecastResponse(
        base_case=ForecastValuationSchema(
            project_name=base.assumptions.project_name,
            npv=base.npv.amount,
            irr_percent=base.irr.as_percent() if base.irr else None,
            payback_period=base.payback_period,
            years=[
                ForecastYearSchema(
                    year=row.year,
                    revenue_growth_percent=row.revenue_growth.as_percent(),
                    revenue=row.revenue.amount,
                    gross_profit=row.gross_profit.amount,
                    operating_expenses=row.operating_expenses.amount,
                    ebitda=row.ebitda.amount,
                    depreciation_amortization=row.depreciation_amortization.amount,
                    ebit=row.ebit.amount,
                    taxes=row.taxes.amount,
                    nopat=row.nopat.amount,
                    capital_expenditures=row.capital_expenditures.amount,
                    change_in_working_capital=row.change_in_working_capital.amount,
                    free_cash_flow=row.free_cash_flow.amount,
                )
                for row in base.years
            ],
        ),
        scenarios=[
            ForecastScenarioOutcomeSchema(
                name=scenario.name,
                probability_percent=scenario.probability.as_percent(),
                npv=scenario.forecast.npv.amount,
                irr_percent=scenario.forecast.irr.as_percent() if scenario.forecast.irr else None,
            )
            for scenario in result.scenarios.scenarios
        ],
        probability_weighted_npv=result.scenarios.probability_weighted_npv.amount,
        sensitivity=[
            ForecastSensitivityPointSchema(
                driver=point.driver,
                case=point.case,
                shock_percentage_points=point.input_percent,
                npv=point.npv.amount,
            )
            for point in result.sensitivity.points
        ],
        break_even_revenue_growth_percent=result.sensitivity.break_even_revenue_growth_percent,
        formulas={
            "ebitda": "Revenue × gross margin − operating expenses",
            "ebit": "EBITDA − depreciation and amortization",
            "nopat": "EBIT − max(EBIT × tax rate, 0)",
            "free_cash_flow": "NOPAT + D&A − capex − change in working capital",
            "npv": "Σ cash flow at period t ÷ (1 + discount rate)^t",
        },
        sensitivity_range_note=(
            "Analyst-assumed one-way shocks: ±2 percentage points for revenue growth, "
            "discount rate, and capex; ±3 points for gross margin."
        ),
    )


def _allocation_command(request: CapitalAllocationRequest) -> OptimizeCapitalAllocationCommand:
    return OptimizeCapitalAllocationCommand(
        currency=request.currency,
        capital_budget=request.capital_budget,
        discount_rate_percent=request.discount_rate_percent,
        investments=tuple(
            InvestmentOpportunityInput(
                investment_id=item.investment_id,
                name=item.name,
                initial_capital=item.initial_capital,
                future_cash_flows=tuple(item.future_cash_flows),
                downside_cash_flows=tuple(item.downside_cash_flows),
                risk_assumption=item.risk_assumption,
                strategic_priority=item.strategic_priority,
                dependencies=tuple(item.dependencies),
                mutually_exclusive_group=item.mutually_exclusive_group,
            )
            for item in request.investments
        ),
        baseline_investment_ids=(
            tuple(request.baseline_investment_ids)
            if request.baseline_investment_ids is not None
            else None
        ),
    )


def _allocation_response(request: CapitalAllocationRequest, result) -> CapitalAllocationResponse:
    return CapitalAllocationResponse(
        portfolio_name=request.portfolio_name,
        currency=request.currency,
        capital_budget=result.capital_budget.amount,
        capital_used=result.capital_used.amount,
        capital_utilization_percent=result.capital_utilization_percent,
        selected_investment_ids=list(result.selected_investment_ids),
        rejected_investment_ids=list(result.rejected_investment_ids),
        portfolio_npv=result.portfolio_npv.amount,
        portfolio_irr_percent=(result.portfolio_irr.as_percent() if result.portfolio_irr else None),
        portfolio_payback_period=result.portfolio_payback_period,
        downside_portfolio_npv=result.downside_portfolio_npv.amount,
        downside_exposure=result.downside_exposure.amount,
        baseline_investment_ids=list(result.baseline_investment_ids),
        baseline_npv=result.baseline_npv.amount,
        incremental_npv_vs_baseline=result.incremental_npv_vs_baseline.amount,
        portfolio_cash_flows=[
            PortfolioCashFlowSchema(period=flow.period, amount=flow.amount.amount)
            for flow in result.portfolio_cash_flows
        ],
        investments=[
            InvestmentMetricsSchema(
                investment_id=metric.opportunity.investment_id,
                name=metric.opportunity.name,
                initial_capital=metric.opportunity.initial_capital.amount,
                npv=metric.npv.amount,
                irr_percent=metric.irr.as_percent() if metric.irr else None,
                payback_period=metric.payback_period,
                downside_npv=metric.downside_npv.amount,
                downside_exposure=metric.downside_exposure.amount,
                risk_assumption=metric.opportunity.risk_assumption,
                strategic_priority=metric.opportunity.strategic_priority,
                dependencies=list(metric.opportunity.dependencies),
                mutually_exclusive_group=metric.opportunity.mutually_exclusive_group,
            )
            for metric in result.opportunity_metrics
        ],
        optimization_method=result.optimization_method,
    )
