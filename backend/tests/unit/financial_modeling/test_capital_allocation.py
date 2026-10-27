from decimal import Decimal

import pytest

from sdie.financial_modeling.domain.capital_allocation import (
    InvestmentOpportunity,
    optimize_capital_allocation,
)
from sdie.financial_modeling.domain.entities import FinancialModelingError
from sdie.shared_kernel.domain.value_objects import Money, Percentage


def opportunity(
    investment_id: str,
    capital: str,
    cash_flow: str,
    *,
    downside: str | None = None,
    priority: int = 3,
    dependencies: tuple[str, ...] = (),
    group: str | None = None,
) -> InvestmentOpportunity:
    return InvestmentOpportunity(
        investment_id=investment_id,
        name=investment_id,
        initial_capital=Money(Decimal(capital)),
        future_cash_flows=(Money(Decimal(cash_flow)),),
        downside_cash_flows=(Money(Decimal(downside or cash_flow)),),
        risk_assumption="Synthetic one-period downside case",
        strategic_priority=priority,
        dependencies=dependencies,
        mutually_exclusive_group=group,
    )


class TestCapitalAllocationOptimization:
    def test_exact_optimizer_beats_highest_irr_first(self):
        # A has the highest IRR (50%) but consumes $60. B+C create $40 NPV,
        # versus A's $30, under the same $100 budget.
        result = optimize_capital_allocation(
            opportunities=(
                opportunity("A", "60", "90"),
                opportunity("B", "50", "70"),
                opportunity("C", "50", "70"),
            ),
            capital_budget=Money(Decimal("100")),
            discount_rate=Percentage.from_percent(0),
        )

        assert result.selected_investment_ids == ("B", "C")
        assert result.portfolio_npv.amount == Decimal("40.00")
        assert result.capital_used.amount == Decimal("100.00")
        assert result.capital_utilization_percent == Decimal("100.00")
        assert result.baseline_investment_ids == ("A",)
        assert result.baseline_npv.amount == Decimal("30.00")
        assert result.incremental_npv_vs_baseline.amount == Decimal("10.00")

    def test_downside_exposure_is_calculated_on_the_selected_portfolio(self):
        result = optimize_capital_allocation(
            opportunities=(
                opportunity("A", "60", "90", downside="60"),
                opportunity("B", "50", "75", downside="55"),
                opportunity("C", "50", "75", downside="55"),
            ),
            capital_budget=Money(Decimal("100")),
            discount_rate=Percentage.from_percent(0),
        )
        assert result.selected_investment_ids == ("B", "C")
        assert result.portfolio_npv.amount == Decimal("50.00")
        assert result.downside_portfolio_npv.amount == Decimal("10.00")
        assert result.downside_exposure.amount == Decimal("40.00")

    def test_dependencies_and_mutual_exclusion_are_enforced(self):
        result = optimize_capital_allocation(
            opportunities=(
                opportunity("platform", "30", "45"),
                opportunity("expansion", "50", "90", dependencies=("platform",)),
                opportunity("channel_a", "40", "70", group="channel"),
                opportunity("channel_b", "40", "72", group="channel"),
            ),
            capital_budget=Money(Decimal("90")),
            discount_rate=Percentage.from_percent(0),
        )
        selected = set(result.selected_investment_ids)
        if "expansion" in selected:
            assert "platform" in selected
        assert not {"channel_a", "channel_b"}.issubset(selected)

    def test_rejects_unknown_dependency(self):
        with pytest.raises(FinancialModelingError, match="dependency"):
            optimize_capital_allocation(
                opportunities=(
                    opportunity("A", "10", "20", dependencies=("missing",)),
                ),
                capital_budget=Money(Decimal("20")),
                discount_rate=Percentage.from_percent(0),
            )
