from decimal import Decimal

import pytest

from sdie.financial_modeling.domain.entities import CashFlow, FinancialModelingError
from sdie.financial_modeling.domain.services import (
    ScenarioDefinition,
    evaluate_scenarios,
    internal_rate_of_return,
    net_present_value,
    one_way_sensitivity,
    payback_period,
    probability_weighted_npv,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage


def cf(period: int, amount: str, currency: str = "USD") -> CashFlow:
    return CashFlow(period, Money(Decimal(amount), currency))


class TestNetPresentValue:
    def test_zero_npv_at_breakeven_rate(self):
        # -1000 now, +1100 in one year, at 10% discount => NPV == 0 exactly
        flows = [cf(0, "-1000"), cf(1, "1100")]
        result = net_present_value(flows, Percentage.from_percent(10))
        assert result.amount == Decimal("0.00")

    def test_zero_discount_rate_is_simple_sum(self):
        flows = [cf(0, "-1000"), cf(1, "500"), cf(2, "500"), cf(3, "500")]
        result = net_present_value(flows, Percentage.from_percent(0))
        assert result.amount == Decimal("500.00")

    def test_rejects_empty_cash_flows(self):
        with pytest.raises(FinancialModelingError):
            net_present_value([], Percentage.from_percent(10))

    def test_rejects_mixed_currency(self):
        flows = [cf(0, "-1000", "USD"), cf(1, "1100", "EUR")]
        with pytest.raises(FinancialModelingError):
            net_present_value(flows, Percentage.from_percent(10))


class TestInternalRateOfReturn:
    def test_matches_known_breakeven_rate(self):
        flows = [cf(0, "-1000"), cf(1, "1100")]
        irr = internal_rate_of_return(flows)
        assert irr is not None
        assert irr.as_percent() == pytest.approx(Decimal("10"), abs=Decimal("0.01"))

    def test_returns_none_when_all_flows_same_sign(self):
        flows = [cf(0, "1000"), cf(1, "500")]
        assert internal_rate_of_return(flows) is None

    def test_multi_period_irr_is_reasonable(self):
        # -1000, +400 x4 -> IRR should be materially positive and NPV(IRR) ~ 0
        flows = [cf(0, "-1000"), cf(1, "400"), cf(2, "400"), cf(3, "400"), cf(4, "400")]
        irr = internal_rate_of_return(flows)
        assert irr is not None
        npv_at_irr = net_present_value(flows, irr)
        assert abs(npv_at_irr.amount) < Decimal("1.00")


class TestPaybackPeriod:
    def test_fractional_payback(self):
        flows = [cf(0, "-1000"), cf(1, "400"), cf(2, "400"), cf(3, "400"), cf(4, "400")]
        payback = payback_period(flows)
        assert payback == Decimal("2.5")

    def test_never_pays_back_returns_none(self):
        flows = [cf(0, "-1000"), cf(1, "100")]
        assert payback_period(flows) is None


class TestSensitivity:
    def test_swing_reflects_range(self):
        base_flows = [cf(0, "-1000"), cf(1, "500")]
        result = one_way_sensitivity(
            variable_name="year_1_revenue",
            base_cash_flows=base_flows,
            discount_rate=Percentage.from_percent(0),
            variable_period=1,
            low_amount=Decimal("300"),
            base_amount=Decimal("500"),
            high_amount=Decimal("700"),
        )
        assert result.npv_low.amount == Decimal("-700.00")
        assert result.npv_base.amount == Decimal("-500.00")
        assert result.npv_high.amount == Decimal("-300.00")
        assert result.swing.amount == Decimal("400.00")


class TestAssumptionFlags:
    def test_flags_discount_rate_below_industry_range(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "1100")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(2),
            cash_flows=flows,
            irr=None,
            industry="software",
        )
        assert any("below the typical" in f for f in flags)

    def test_flags_discount_rate_above_industry_range(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "1100")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(40),
            cash_flows=flows,
            irr=None,
            industry="software",
        )
        assert any("above the typical" in f for f in flags)

    def test_no_flag_for_discount_rate_within_range(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "1100")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(12),
            cash_flows=flows,
            irr=None,
            industry="software",
        )
        assert not any("discount rate" in f for f in flags)

    def test_flags_unrealistically_high_irr(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "1100")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(12),
            cash_flows=flows,
            irr=Percentage.from_percent(50),
            industry="software",
        )
        assert any("IRR" in f for f in flags)

    def test_flags_no_positive_cash_flow_period(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "-100"), cf(2, "-50")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(10), cash_flows=flows, irr=None
        )
        assert any("cash-negative" in f for f in flags)

    def test_defaults_to_general_industry_when_unspecified(self):
        from sdie.financial_modeling.domain.services import evaluate_assumption_flags

        flows = [cf(0, "-1000"), cf(1, "1100")]
        flags = evaluate_assumption_flags(
            discount_rate=Percentage.from_percent(10), cash_flows=flows, irr=None, industry=None
        )
        assert flags == []  # 10% is within the "general" 8-12% band


class TestScenarios:
    def test_probability_weighted_npv(self):
        scenarios = [
            ScenarioDefinition(
                "downside", [cf(0, "-1000"), cf(1, "800")], Percentage.from_percent(25)
            ),
            ScenarioDefinition(
                "base", [cf(0, "-1000"), cf(1, "1200")], Percentage.from_percent(50)
            ),
            ScenarioDefinition(
                "upside", [cf(0, "-1000"), cf(1, "1600")], Percentage.from_percent(25)
            ),
        ]
        results = evaluate_scenarios(scenarios, Percentage.from_percent(0))
        weighted = probability_weighted_npv(results)
        # NPVs at 0%: downside=-200, base=200, upside=600
        # weighted = 0.25*-200 + 0.5*200 + 0.25*600 = -50+100+150 = 200
        assert weighted.amount == Decimal("200.00")

    def test_rejects_probabilities_not_summing_to_one(self):
        scenarios = [
            ScenarioDefinition("a", [cf(0, "-1000"), cf(1, "1200")], Percentage.from_percent(60)),
            ScenarioDefinition("b", [cf(0, "-1000"), cf(1, "1200")], Percentage.from_percent(60)),
        ]
        results = evaluate_scenarios(scenarios, Percentage.from_percent(0))
        with pytest.raises(FinancialModelingError):
            probability_weighted_npv(results)
