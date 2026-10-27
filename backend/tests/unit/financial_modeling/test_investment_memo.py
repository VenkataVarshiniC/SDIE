import io
from decimal import Decimal

import pdfplumber

from sdie.financial_modeling.application.planning import (
    AnalyzeOperatingForecastCommand,
    AnalyzeOperatingForecastUseCase,
    InvestmentOpportunityInput,
    OperatingForecastInput,
    OperatingForecastScenarioInput,
    OptimizeCapitalAllocationCommand,
    OptimizeCapitalAllocationUseCase,
)
from sdie.financial_modeling.infrastructure.reportlab_investment_memo import (
    ReportLabInvestmentMemoRenderer,
)


def forecast_input(name: str, growth: str, margin: str) -> OperatingForecastInput:
    return OperatingForecastInput(
        project_name=name,
        currency="USD",
        base_revenue=Decimal("1000000"),
        initial_investment=Decimal("500000"),
        revenue_growth_percent_by_year=(Decimal(growth),) * 5,
        gross_margin_percent=Decimal(margin),
        operating_expense_percent_of_revenue=Decimal("30"),
        depreciation_amortization_percent_of_revenue=Decimal("4"),
        tax_rate_percent=Decimal("25"),
        capital_expenditure_percent_of_revenue=Decimal("6"),
        working_capital_percent_of_revenue=Decimal("8"),
        discount_rate_percent=Decimal("10"),
    )


async def test_executive_memo_contains_required_sections_and_values():
    base = forecast_input("Product expansion", "8", "70")
    forecast = await AnalyzeOperatingForecastUseCase().execute(
        AnalyzeOperatingForecastCommand(
            base_case=base,
            scenarios=(
                OperatingForecastScenarioInput(
                    "Downside", Decimal("25"), forecast_input("Downside", "3", "65")
                ),
                OperatingForecastScenarioInput("Base", Decimal("50"), base),
                OperatingForecastScenarioInput(
                    "Upside", Decimal("25"), forecast_input("Upside", "12", "74")
                ),
            ),
        )
    )
    investments = (
        InvestmentOpportunityInput(
            investment_id="A",
            name="Core platform",
            initial_capital=Decimal("600000"),
            future_cash_flows=(Decimal("200000"),) * 5,
            downside_cash_flows=(Decimal("130000"),) * 5,
            risk_assumption="Adoption may ramp more slowly than planned.",
            strategic_priority=5,
            dependencies=(),
            mutually_exclusive_group=None,
        ),
        InvestmentOpportunityInput(
            investment_id="B",
            name="Partner channel",
            initial_capital=Decimal("400000"),
            future_cash_flows=(Decimal("150000"),) * 5,
            downside_cash_flows=(Decimal("90000"),) * 5,
            risk_assumption="Partner conversion rates are uncertain.",
            strategic_priority=4,
            dependencies=(),
            mutually_exclusive_group=None,
        ),
    )
    allocation = await OptimizeCapitalAllocationUseCase().execute(
        OptimizeCapitalAllocationCommand(
            currency="USD",
            capital_budget=Decimal("1000000"),
            discount_rate_percent=Decimal("10"),
            investments=investments,
        )
    )

    content = ReportLabInvestmentMemoRenderer().render(
        portfolio_name="FY27 product investments",
        business_context="Hypothetical capital allocation for a software product portfolio.",
        allocation=allocation,
        forecast=forecast,
    )

    assert content.startswith(b"%PDF")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Investment decision" in text
    assert "Financial projections" in text
    assert "Scenario comparison" in text
    assert "Sensitivity results" in text
    assert "Recommended capital allocation" in text
    assert "Core platform" in text
