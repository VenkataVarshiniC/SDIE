from dataclasses import replace
from decimal import Decimal

from sdie.financial_modeling.domain.forecasting import (
    ForecastScenario,
    OperatingForecastAssumptions,
    analyze_forecast_sensitivity,
    build_operating_forecast,
    evaluate_forecast_scenarios,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage


def assumptions(**overrides) -> OperatingForecastAssumptions:
    values = {
        "project_name": "Hand-verifiable forecast",
        "currency": "USD",
        "base_revenue": Money(Decimal("100")),
        "initial_investment": Money(Decimal("100")),
        "revenue_growth_rates": (Percentage.from_percent(0),) * 5,
        "gross_margin": Percentage.from_percent(60),
        "operating_expense_rate": Percentage.from_percent(20),
        "depreciation_amortization_rate": Percentage.from_percent(10),
        "tax_rate": Percentage.from_percent(20),
        "capital_expenditure_rate": Percentage.from_percent(10),
        "working_capital_rate": Percentage.from_percent(10),
        "discount_rate": Percentage.from_percent(0),
    }
    values.update(overrides)
    return OperatingForecastAssumptions(**values)


class TestOperatingForecast:
    def test_fcff_formula_and_valuation_are_hand_verifiable(self):
        result = build_operating_forecast(assumptions())

        first_year = result.years[0]
        assert first_year.revenue.amount == Decimal("100.00")
        assert first_year.ebitda.amount == Decimal("40.00")
        assert first_year.depreciation_amortization.amount == Decimal("10.00")
        assert first_year.ebit.amount == Decimal("30.00")
        assert first_year.taxes.amount == Decimal("6.00")
        assert first_year.nopat.amount == Decimal("24.00")
        assert first_year.change_in_working_capital.amount == Decimal("0.00")
        assert first_year.free_cash_flow.amount == Decimal("24.00")
        assert result.npv.amount == Decimal("20.00")
        assert result.payback_period == Decimal("4.166666666666666666666666667")

    def test_working_capital_uses_change_not_full_balance(self):
        result = build_operating_forecast(
            assumptions(revenue_growth_rates=(Percentage.from_percent(10),) * 5)
        )
        assert result.years[0].revenue.amount == Decimal("110.00")
        assert result.years[0].change_in_working_capital.amount == Decimal("1.00")
        assert result.years[1].change_in_working_capital.amount == Decimal("1.10")

    def test_negative_ebit_does_not_create_an_unmodeled_tax_benefit(self):
        result = build_operating_forecast(
            assumptions(
                gross_margin=Percentage.from_percent(10),
                operating_expense_rate=Percentage.from_percent(40),
            )
        )
        assert result.years[0].ebit.amount < 0
        assert result.years[0].taxes.amount == Decimal("0.00")


class TestForecastAnalysis:
    def test_probability_weighted_scenarios(self):
        base = assumptions()
        downside = replace(base, gross_margin=Percentage.from_percent(50))
        upside = replace(base, gross_margin=Percentage.from_percent(70))
        result = evaluate_forecast_scenarios(
            (
                ForecastScenario("Downside", Percentage.from_percent(25), downside),
                ForecastScenario("Base", Percentage.from_percent(50), base),
                ForecastScenario("Upside", Percentage.from_percent(25), upside),
            )
        )
        expected = sum(
            (item.forecast.npv.amount * item.probability.fraction for item in result.scenarios),
            Decimal("0"),
        ).quantize(Decimal("0.01"))
        assert result.probability_weighted_npv.amount == expected

    def test_sensitivity_covers_required_drivers_and_break_even(self):
        result = analyze_forecast_sensitivity(assumptions())
        assert {point.driver for point in result.points} == {
            "revenue_growth",
            "gross_margin",
            "discount_rate",
            "capital_expenditures",
        }
        assert len(result.points) == 12
        assert result.break_even_revenue_growth_percent is not None
