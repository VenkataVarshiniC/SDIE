"""Five-year operating forecasts that convert accounting drivers to FCFF.

The forecast deliberately stops at free cash flow. Valuation is delegated to
the existing NPV/IRR/payback services so there is one discounting convention
throughout the bounded context.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from sdie.financial_modeling.domain.entities import CashFlow, FinancialModelingError
from sdie.financial_modeling.domain.services import (
    internal_rate_of_return,
    net_present_value,
    payback_period,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage

FORECAST_YEARS = 5


@dataclass(frozen=True, slots=True)
class OperatingForecastAssumptions:
    project_name: str
    currency: str
    base_revenue: Money
    initial_investment: Money
    revenue_growth_rates: tuple[Percentage, ...]
    gross_margin: Percentage
    operating_expense_rate: Percentage
    depreciation_amortization_rate: Percentage
    tax_rate: Percentage
    capital_expenditure_rate: Percentage
    working_capital_rate: Percentage
    discount_rate: Percentage

    def __post_init__(self) -> None:
        if not self.project_name.strip():
            raise FinancialModelingError("project_name must not be empty")
        if self.base_revenue.currency != self.currency or self.initial_investment.currency != self.currency:
            raise FinancialModelingError("Forecast amounts must use the forecast currency")
        if self.base_revenue.amount < 0:
            raise FinancialModelingError("base_revenue cannot be negative")
        if self.initial_investment.amount <= 0:
            raise FinancialModelingError("initial_investment must be positive")
        if len(self.revenue_growth_rates) != FORECAST_YEARS:
            raise FinancialModelingError(f"revenue_growth_rates must contain exactly {FORECAST_YEARS} values")
        if any(rate.fraction <= Decimal("-1") for rate in self.revenue_growth_rates):
            raise FinancialModelingError("revenue growth cannot be -100% or lower")
        for label, rate in (
            ("gross_margin", self.gross_margin),
            ("operating_expense_rate", self.operating_expense_rate),
            ("depreciation_amortization_rate", self.depreciation_amortization_rate),
            ("tax_rate", self.tax_rate),
            ("capital_expenditure_rate", self.capital_expenditure_rate),
            ("working_capital_rate", self.working_capital_rate),
        ):
            if not Decimal("0") <= rate.fraction <= Decimal("1"):
                raise FinancialModelingError(f"{label} must be between 0% and 100%")
        if self.discount_rate.fraction < 0:
            raise FinancialModelingError("discount_rate cannot be negative")


@dataclass(frozen=True, slots=True)
class ForecastYear:
    year: int
    revenue_growth: Percentage
    revenue: Money
    gross_profit: Money
    operating_expenses: Money
    ebitda: Money
    depreciation_amortization: Money
    ebit: Money
    taxes: Money
    nopat: Money
    capital_expenditures: Money
    change_in_working_capital: Money
    free_cash_flow: Money


@dataclass(frozen=True, slots=True)
class OperatingForecastResult:
    assumptions: OperatingForecastAssumptions
    years: tuple[ForecastYear, ...]
    valuation_cash_flows: tuple[CashFlow, ...]
    npv: Money
    irr: Percentage | None
    payback_period: Decimal | None


@dataclass(frozen=True, slots=True)
class ForecastScenario:
    name: str
    probability: Percentage
    assumptions: OperatingForecastAssumptions


@dataclass(frozen=True, slots=True)
class ForecastScenarioResult:
    name: str
    probability: Percentage
    forecast: OperatingForecastResult


@dataclass(frozen=True, slots=True)
class ForecastScenarioAnalysis:
    scenarios: tuple[ForecastScenarioResult, ...]
    probability_weighted_npv: Money


@dataclass(frozen=True, slots=True)
class ForecastSensitivityPoint:
    driver: str
    case: str
    input_percent: Decimal
    npv: Money


@dataclass(frozen=True, slots=True)
class ForecastSensitivityAnalysis:
    points: tuple[ForecastSensitivityPoint, ...]
    break_even_revenue_growth_percent: Decimal | None


def build_operating_forecast(assumptions: OperatingForecastAssumptions) -> OperatingForecastResult:
    """Build FCFF using EBIT(1-t) + D&A - capex - change in NWC.

    Taxes are floored at zero because this compact model does not model net
    operating loss carryforwards. D&A is deducted once to reach EBIT and
    added back once as a non-cash expense.
    """
    years, cash_flows = _forecast_components(assumptions)
    cash_flow_list = list(cash_flows)
    return OperatingForecastResult(
        assumptions=assumptions,
        years=years,
        valuation_cash_flows=cash_flows,
        npv=net_present_value(cash_flow_list, assumptions.discount_rate),
        irr=internal_rate_of_return(cash_flow_list),
        payback_period=payback_period(cash_flow_list),
    )


def _forecast_components(
    assumptions: OperatingForecastAssumptions,
) -> tuple[tuple[ForecastYear, ...], tuple[CashFlow, ...]]:
    years: list[ForecastYear] = []
    prior_revenue = assumptions.base_revenue
    prior_working_capital = prior_revenue * assumptions.working_capital_rate.fraction

    for year, growth in enumerate(assumptions.revenue_growth_rates, start=1):
        revenue = prior_revenue * (Decimal("1") + growth.fraction)
        gross_profit = revenue * assumptions.gross_margin.fraction
        operating_expenses = revenue * assumptions.operating_expense_rate.fraction
        ebitda = gross_profit - operating_expenses
        depreciation_amortization = revenue * assumptions.depreciation_amortization_rate.fraction
        ebit = ebitda - depreciation_amortization
        taxes = Money(max(ebit.amount, Decimal("0")) * assumptions.tax_rate.fraction, assumptions.currency)
        nopat = ebit - taxes
        capital_expenditures = revenue * assumptions.capital_expenditure_rate.fraction
        working_capital = revenue * assumptions.working_capital_rate.fraction
        change_in_working_capital = working_capital - prior_working_capital
        free_cash_flow = (
            nopat + depreciation_amortization - capital_expenditures - change_in_working_capital
        )

        years.append(
            ForecastYear(
                year=year,
                revenue_growth=growth,
                revenue=revenue,
                gross_profit=gross_profit,
                operating_expenses=operating_expenses,
                ebitda=ebitda,
                depreciation_amortization=depreciation_amortization,
                ebit=ebit,
                taxes=taxes,
                nopat=nopat,
                capital_expenditures=capital_expenditures,
                change_in_working_capital=change_in_working_capital,
                free_cash_flow=free_cash_flow,
            )
        )
        prior_revenue = revenue
        prior_working_capital = working_capital

    cash_flows = (
        CashFlow(0, -assumptions.initial_investment),
        *(CashFlow(row.year, row.free_cash_flow) for row in years),
    )
    return tuple(years), cash_flows


def evaluate_forecast_scenarios(scenarios: tuple[ForecastScenario, ...]) -> ForecastScenarioAnalysis:
    if not scenarios:
        raise FinancialModelingError("At least one forecast scenario is required")
    total_probability = sum((scenario.probability.fraction for scenario in scenarios), Decimal("0"))
    if abs(total_probability - Decimal("1")) > Decimal("0.001"):
        raise FinancialModelingError(f"Scenario probabilities must sum to 100%, got {total_probability * 100}%")

    results = tuple(
        ForecastScenarioResult(
            name=scenario.name,
            probability=scenario.probability,
            forecast=build_operating_forecast(scenario.assumptions),
        )
        for scenario in scenarios
    )
    currency = results[0].forecast.npv.currency
    if any(result.forecast.npv.currency != currency for result in results):
        raise FinancialModelingError("All scenarios must use one currency")
    weighted = sum(
        (result.forecast.npv.amount * result.probability.fraction for result in results),
        Decimal("0"),
    )
    return ForecastScenarioAnalysis(results, Money(weighted, currency))


def analyze_forecast_sensitivity(
    assumptions: OperatingForecastAssumptions,
) -> ForecastSensitivityAnalysis:
    """Run transparent, fixed one-way shocks around the supplied base case.

    Growth, discount rate, and capex use +/-2 percentage points; gross
    margin uses +/-3 points. These are analyst-assumed stress ranges, not
    observed industry volatility.
    """

    def shifted_growth(delta_percent: Decimal) -> OperatingForecastAssumptions:
        delta = Percentage.from_percent(delta_percent)
        return replace(
            assumptions,
            revenue_growth_rates=tuple(
                Percentage(rate.fraction + delta.fraction) for rate in assumptions.revenue_growth_rates
            ),
        )

    def shifted_rate(field_name: str, delta_percent: Decimal) -> OperatingForecastAssumptions:
        current = getattr(assumptions, field_name)
        shifted = max(Decimal("0"), current.fraction + Percentage.from_percent(delta_percent).fraction)
        return replace(assumptions, **{field_name: Percentage(shifted)})

    driver_cases: tuple[tuple[str, str, Decimal, OperatingForecastAssumptions], ...] = (
        ("revenue_growth", "low", Decimal("-2"), shifted_growth(Decimal("-2"))),
        ("revenue_growth", "base", Decimal("0"), assumptions),
        ("revenue_growth", "high", Decimal("2"), shifted_growth(Decimal("2"))),
        ("gross_margin", "low", Decimal("-3"), shifted_rate("gross_margin", Decimal("-3"))),
        ("gross_margin", "base", Decimal("0"), assumptions),
        ("gross_margin", "high", Decimal("3"), shifted_rate("gross_margin", Decimal("3"))),
        ("discount_rate", "low", Decimal("-2"), shifted_rate("discount_rate", Decimal("-2"))),
        ("discount_rate", "base", Decimal("0"), assumptions),
        ("discount_rate", "high", Decimal("2"), shifted_rate("discount_rate", Decimal("2"))),
        ("capital_expenditures", "low", Decimal("-2"), shifted_rate("capital_expenditure_rate", Decimal("-2"))),
        ("capital_expenditures", "base", Decimal("0"), assumptions),
        ("capital_expenditures", "high", Decimal("2"), shifted_rate("capital_expenditure_rate", Decimal("2"))),
    )
    points = tuple(
        ForecastSensitivityPoint(
            driver=driver,
            case=case,
            input_percent=delta,
            npv=build_operating_forecast(shocked).npv,
        )
        for driver, case, delta, shocked in driver_cases
    )
    return ForecastSensitivityAnalysis(
        points=points,
        break_even_revenue_growth_percent=_break_even_revenue_growth(assumptions),
    )


def _break_even_revenue_growth(assumptions: OperatingForecastAssumptions) -> Decimal | None:
    def npv_at(rate_percent: Decimal) -> Decimal:
        candidate = replace(
            assumptions,
            revenue_growth_rates=(Percentage.from_percent(rate_percent),) * FORECAST_YEARS,
        )
        _, cash_flows = _forecast_components(candidate)
        return net_present_value(list(cash_flows), candidate.discount_rate).amount

    low, high = Decimal("-90"), Decimal("200")
    low_npv, high_npv = npv_at(low), npv_at(high)
    if low_npv == 0:
        return low
    if high_npv == 0:
        return high
    if low_npv * high_npv > 0:
        return None
    for _ in range(160):
        mid = (low + high) / Decimal("2")
        mid_npv = npv_at(mid)
        if abs(mid_npv) < Decimal("0.01"):
            return mid.quantize(Decimal("0.01"))
        if low_npv * mid_npv <= 0:
            high = mid
        else:
            low = mid
            low_npv = mid_npv
    return ((low + high) / Decimal("2")).quantize(Decimal("0.01"))
