"""Application boundary for forecasts and capital-allocation analysis."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sdie.financial_modeling.domain.capital_allocation import (
    CapitalAllocationResult,
    InvestmentOpportunity,
    optimize_capital_allocation,
)
from sdie.financial_modeling.domain.forecasting import (
    ForecastScenario,
    ForecastScenarioAnalysis,
    ForecastSensitivityAnalysis,
    OperatingForecastAssumptions,
    OperatingForecastResult,
    analyze_forecast_sensitivity,
    build_operating_forecast,
    evaluate_forecast_scenarios,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage


@dataclass(frozen=True, slots=True)
class OperatingForecastInput:
    project_name: str
    currency: str
    base_revenue: Decimal
    initial_investment: Decimal
    revenue_growth_percent_by_year: tuple[Decimal, ...]
    gross_margin_percent: Decimal
    operating_expense_percent_of_revenue: Decimal
    depreciation_amortization_percent_of_revenue: Decimal
    tax_rate_percent: Decimal
    capital_expenditure_percent_of_revenue: Decimal
    working_capital_percent_of_revenue: Decimal
    discount_rate_percent: Decimal


@dataclass(frozen=True, slots=True)
class OperatingForecastScenarioInput:
    name: str
    probability_percent: Decimal
    assumptions: OperatingForecastInput


@dataclass(frozen=True, slots=True)
class AnalyzeOperatingForecastCommand:
    base_case: OperatingForecastInput
    scenarios: tuple[OperatingForecastScenarioInput, ...]


@dataclass(frozen=True, slots=True)
class OperatingForecastAnalysisResult:
    base_case: OperatingForecastResult
    scenarios: ForecastScenarioAnalysis
    sensitivity: ForecastSensitivityAnalysis


@dataclass(frozen=True, slots=True)
class InvestmentOpportunityInput:
    investment_id: str
    name: str
    initial_capital: Decimal
    future_cash_flows: tuple[Decimal, ...]
    downside_cash_flows: tuple[Decimal, ...]
    risk_assumption: str
    strategic_priority: int
    dependencies: tuple[str, ...]
    mutually_exclusive_group: str | None


@dataclass(frozen=True, slots=True)
class OptimizeCapitalAllocationCommand:
    currency: str
    capital_budget: Decimal
    discount_rate_percent: Decimal
    investments: tuple[InvestmentOpportunityInput, ...]
    baseline_investment_ids: tuple[str, ...] | None = None


class AnalyzeOperatingForecastUseCase:
    async def execute(self, command: AnalyzeOperatingForecastCommand) -> OperatingForecastAnalysisResult:
        base_assumptions = _forecast_assumptions(command.base_case)
        scenario_analysis = evaluate_forecast_scenarios(
            tuple(
                ForecastScenario(
                    name=item.name,
                    probability=Percentage.from_percent(item.probability_percent),
                    assumptions=_forecast_assumptions(item.assumptions),
                )
                for item in command.scenarios
            )
        )
        return OperatingForecastAnalysisResult(
            base_case=build_operating_forecast(base_assumptions),
            scenarios=scenario_analysis,
            sensitivity=analyze_forecast_sensitivity(base_assumptions),
        )


class OptimizeCapitalAllocationUseCase:
    async def execute(self, command: OptimizeCapitalAllocationCommand) -> CapitalAllocationResult:
        currency = command.currency
        opportunities = tuple(
            InvestmentOpportunity(
                investment_id=item.investment_id,
                name=item.name,
                initial_capital=Money(item.initial_capital, currency),
                future_cash_flows=tuple(Money(amount, currency) for amount in item.future_cash_flows),
                downside_cash_flows=tuple(
                    Money(amount, currency) for amount in item.downside_cash_flows
                ),
                risk_assumption=item.risk_assumption,
                strategic_priority=item.strategic_priority,
                dependencies=item.dependencies,
                mutually_exclusive_group=item.mutually_exclusive_group,
            )
            for item in command.investments
        )
        return optimize_capital_allocation(
            opportunities=opportunities,
            capital_budget=Money(command.capital_budget, currency),
            discount_rate=Percentage.from_percent(command.discount_rate_percent),
            baseline_investment_ids=command.baseline_investment_ids,
        )


def _forecast_assumptions(item: OperatingForecastInput) -> OperatingForecastAssumptions:
    return OperatingForecastAssumptions(
        project_name=item.project_name,
        currency=item.currency,
        base_revenue=Money(item.base_revenue, item.currency),
        initial_investment=Money(item.initial_investment, item.currency),
        revenue_growth_rates=tuple(
            Percentage.from_percent(rate) for rate in item.revenue_growth_percent_by_year
        ),
        gross_margin=Percentage.from_percent(item.gross_margin_percent),
        operating_expense_rate=Percentage.from_percent(
            item.operating_expense_percent_of_revenue
        ),
        depreciation_amortization_rate=Percentage.from_percent(
            item.depreciation_amortization_percent_of_revenue
        ),
        tax_rate=Percentage.from_percent(item.tax_rate_percent),
        capital_expenditure_rate=Percentage.from_percent(
            item.capital_expenditure_percent_of_revenue
        ),
        working_capital_rate=Percentage.from_percent(
            item.working_capital_percent_of_revenue
        ),
        discount_rate=Percentage.from_percent(item.discount_rate_percent),
    )
