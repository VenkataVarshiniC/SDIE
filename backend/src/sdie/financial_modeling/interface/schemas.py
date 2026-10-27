"""HTTP-facing schemas. Deliberately separate from application DTOs so the
public API contract can evolve (versioning, backward compatibility) without
forcing changes through the use-case layer."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CashFlowSchema(BaseModel):
    period: int = Field(ge=0)
    amount: Decimal


class CreateCashFlowModelRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3, default="USD")
    discount_rate_percent: Decimal = Field(ge=0, le=100)
    cash_flows: list[CashFlowSchema] = Field(min_length=1)
    industry: str | None = Field(
        default=None,
        description="Selects a benchmark WACC/IRR range sourced from NYU Stern/Damodaran's "
        "Cost of Capital by Sector dataset (Jan 2026). Options: software, internet_software, "
        "retail, grocery_retail, manufacturing, auto, energy, energy_exploration, "
        "renewable_energy, healthcare, biotech, pharma, banking, telecom, media_entertainment, "
        "hospitality, real_estate, semiconductor, aerospace_defense, utilities, transportation. "
        "Defaults to 'general' (the total US market average) if omitted.",
    )

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, v: str) -> str:
        return v.upper()


class CashFlowModelResponse(BaseModel):
    model_id: UUID
    project_name: str
    currency: str
    discount_rate_percent: Decimal
    npv: Decimal
    irr_percent: Decimal | None
    payback_period: Decimal | None
    flags: list[str] = Field(default_factory=list)


class ScenarioSchema(BaseModel):
    name: str
    cash_flows: list[CashFlowSchema] = Field(min_length=1)
    probability_percent: Decimal | None = Field(default=None, ge=0, le=100)


class EvaluateScenariosRequest(BaseModel):
    project_name: str
    currency: str = Field(min_length=3, max_length=3, default="USD")
    discount_rate_percent: Decimal = Field(ge=0, le=100)
    scenarios: list[ScenarioSchema] = Field(min_length=1)


class ScenarioOutcomeSchema(BaseModel):
    name: str
    npv: Decimal
    irr_percent: Decimal | None
    probability_percent: Decimal | None


class EvaluateScenariosResponse(BaseModel):
    outcomes: list[ScenarioOutcomeSchema]
    probability_weighted_npv: Decimal | None


class SensitivityRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=3, default="USD")
    discount_rate_percent: Decimal = Field(ge=0, le=100)
    base_cash_flows: list[CashFlowSchema] = Field(min_length=1)
    variable_name: str
    variable_period: int = Field(ge=0)
    low_amount: Decimal
    base_amount: Decimal
    high_amount: Decimal


class SensitivityResponse(BaseModel):
    variable: str
    npv_low: Decimal
    npv_base: Decimal
    npv_high: Decimal
    swing: Decimal


class OperatingForecastAssumptionsSchema(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3, default="USD")
    base_revenue: Decimal = Field(ge=0)
    initial_investment: Decimal = Field(gt=0)
    revenue_growth_percent_by_year: list[Decimal] = Field(min_length=5, max_length=5)
    gross_margin_percent: Decimal = Field(ge=0, le=100)
    operating_expense_percent_of_revenue: Decimal = Field(ge=0, le=100)
    depreciation_amortization_percent_of_revenue: Decimal = Field(ge=0, le=100)
    tax_rate_percent: Decimal = Field(ge=0, le=100)
    capital_expenditure_percent_of_revenue: Decimal = Field(ge=0, le=100)
    working_capital_percent_of_revenue: Decimal = Field(ge=0, le=100)
    discount_rate_percent: Decimal = Field(ge=0, le=100)

    @field_validator("currency")
    @classmethod
    def forecast_currency_upper(cls, value: str) -> str:
        return value.upper()


class OperatingForecastScenarioSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    probability_percent: Decimal = Field(ge=0, le=100)
    assumptions: OperatingForecastAssumptionsSchema


class AnalyzeOperatingForecastRequest(BaseModel):
    base_case: OperatingForecastAssumptionsSchema
    scenarios: list[OperatingForecastScenarioSchema] = Field(min_length=1)


class ForecastYearSchema(BaseModel):
    year: int
    revenue_growth_percent: Decimal
    revenue: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    ebitda: Decimal
    depreciation_amortization: Decimal
    ebit: Decimal
    taxes: Decimal
    nopat: Decimal
    capital_expenditures: Decimal
    change_in_working_capital: Decimal
    free_cash_flow: Decimal


class ForecastValuationSchema(BaseModel):
    project_name: str
    npv: Decimal
    irr_percent: Decimal | None
    payback_period: Decimal | None
    years: list[ForecastYearSchema]


class ForecastScenarioOutcomeSchema(BaseModel):
    name: str
    probability_percent: Decimal
    npv: Decimal
    irr_percent: Decimal | None


class ForecastSensitivityPointSchema(BaseModel):
    driver: str
    case: str
    shock_percentage_points: Decimal
    npv: Decimal


class AnalyzeOperatingForecastResponse(BaseModel):
    base_case: ForecastValuationSchema
    scenarios: list[ForecastScenarioOutcomeSchema]
    probability_weighted_npv: Decimal
    sensitivity: list[ForecastSensitivityPointSchema]
    break_even_revenue_growth_percent: Decimal | None
    formulas: dict[str, str]
    sensitivity_range_note: str


class InvestmentOpportunitySchema(BaseModel):
    investment_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    initial_capital: Decimal = Field(gt=0)
    future_cash_flows: list[Decimal] = Field(min_length=1, max_length=10)
    downside_cash_flows: list[Decimal] = Field(min_length=1, max_length=10)
    risk_assumption: str = Field(min_length=1, max_length=1000)
    strategic_priority: int = Field(ge=1, le=5)
    dependencies: list[str] = Field(default_factory=list)
    mutually_exclusive_group: str | None = Field(default=None, max_length=100)


class CapitalAllocationRequest(BaseModel):
    portfolio_name: str = Field(min_length=1, max_length=255)
    business_context: str = Field(min_length=1, max_length=2000)
    currency: str = Field(min_length=3, max_length=3, default="USD")
    capital_budget: Decimal = Field(gt=0)
    discount_rate_percent: Decimal = Field(ge=0, le=100)
    investments: list[InvestmentOpportunitySchema] = Field(min_length=1, max_length=20)
    baseline_investment_ids: list[str] | None = None

    @field_validator("currency")
    @classmethod
    def allocation_currency_upper(cls, value: str) -> str:
        return value.upper()


class InvestmentMetricsSchema(BaseModel):
    investment_id: str
    name: str
    initial_capital: Decimal
    npv: Decimal
    irr_percent: Decimal | None
    payback_period: Decimal | None
    downside_npv: Decimal
    downside_exposure: Decimal
    risk_assumption: str
    strategic_priority: int
    dependencies: list[str]
    mutually_exclusive_group: str | None


class PortfolioCashFlowSchema(BaseModel):
    period: int
    amount: Decimal


class CapitalAllocationResponse(BaseModel):
    portfolio_name: str
    currency: str
    capital_budget: Decimal
    capital_used: Decimal
    capital_utilization_percent: Decimal
    selected_investment_ids: list[str]
    rejected_investment_ids: list[str]
    portfolio_npv: Decimal
    portfolio_irr_percent: Decimal | None
    portfolio_payback_period: Decimal | None
    downside_portfolio_npv: Decimal
    downside_exposure: Decimal
    baseline_investment_ids: list[str]
    baseline_npv: Decimal
    incremental_npv_vs_baseline: Decimal
    portfolio_cash_flows: list[PortfolioCashFlowSchema]
    investments: list[InvestmentMetricsSchema]
    optimization_method: str


class ExecutiveInvestmentMemoRequest(BaseModel):
    allocation: CapitalAllocationRequest
    forecast_analysis: AnalyzeOperatingForecastRequest
