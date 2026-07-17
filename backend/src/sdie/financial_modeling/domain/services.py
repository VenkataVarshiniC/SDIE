"""Deterministic financial calculations. No LLM, no I/O, no randomness
(Monte Carlo lives in decision_analysis, which explicitly models
uncertainty — this module models certainty-equivalent cash flows).

Every public function is pure: inputs in, value out, fully unit-testable
against hand-computed / spreadsheet-verified figures.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sdie.financial_modeling.domain.entities import CashFlow, FinancialModelingError
from sdie.shared_kernel.domain.value_objects import Money, Percentage

_MAX_IRR_ITERATIONS = 200
_IRR_TOLERANCE = Decimal("0.0000001")


def net_present_value(cash_flows: list[CashFlow], discount_rate: Percentage) -> Money:
    """NPV = sum( CF_t / (1 + r)^t ) for t = 0..n."""
    if not cash_flows:
        raise FinancialModelingError("cash_flows must not be empty")

    currency = cash_flows[0].amount.currency
    r = discount_rate.fraction
    total = Decimal("0")
    for cf in cash_flows:
        if cf.amount.currency != currency:
            raise FinancialModelingError("All cash flows in a model must share one currency")
        discount_factor = (Decimal("1") + r) ** cf.period
        total += cf.amount.amount / discount_factor

    return Money(total, currency)


def _npv_at_rate(cash_flows: list[CashFlow], rate: Decimal) -> Decimal:
    return sum(
        (cf.amount.amount / ((Decimal("1") + rate) ** cf.period) for cf in cash_flows),
        Decimal("0"),
    )


def internal_rate_of_return(
    cash_flows: list[CashFlow],
    *,
    guess: Decimal = Decimal("0.1"),
) -> Percentage | None:
    """IRR via Newton-Raphson with bisection fallback. Returns None if no
    real root converges (e.g. all cash flows same sign — IRR is undefined).
    """
    if not cash_flows:
        raise FinancialModelingError("cash_flows must not be empty")

    amounts = [cf.amount.amount for cf in cash_flows]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return None

    rate = guess
    for _ in range(_MAX_IRR_ITERATIONS):
        npv = _npv_at_rate(cash_flows, rate)
        # numerical derivative — avoids a second closed-form implementation to keep in sync
        delta = Decimal("0.000001")
        npv_delta = _npv_at_rate(cash_flows, rate + delta)
        derivative = (npv_delta - npv) / delta
        if derivative == 0:
            break
        new_rate = rate - npv / derivative
        if abs(new_rate - rate) < _IRR_TOLERANCE:
            return Percentage(new_rate)
        rate = new_rate
        if rate <= Decimal("-0.999"):
            rate = Decimal("-0.5")  # keep iteration in a sane domain

    return _irr_by_bisection(cash_flows)


def _irr_by_bisection(cash_flows: list[CashFlow]) -> Percentage | None:
    low, high = Decimal("-0.99"), Decimal("10.0")
    npv_low = _npv_at_rate(cash_flows, low)
    npv_high = _npv_at_rate(cash_flows, high)
    if npv_low * npv_high > 0:
        return None

    for _ in range(200):
        mid = (low + high) / 2
        npv_mid = _npv_at_rate(cash_flows, mid)
        if abs(npv_mid) < Decimal("0.01"):
            return Percentage(mid)
        if npv_low * npv_mid < 0:
            high = mid
        else:
            low = mid
            npv_low = npv_mid
    return Percentage((low + high) / 2)


def payback_period(cash_flows: list[CashFlow]) -> Decimal | None:
    """Number of periods (fractional) until cumulative cash flow turns
    non-negative. Returns None if it never does."""
    sorted_flows = sorted(cash_flows, key=lambda cf: cf.period)
    cumulative = Decimal("0")
    for i, cf in enumerate(sorted_flows):
        prev_cumulative = cumulative
        cumulative += cf.amount.amount
        if cumulative >= 0:
            if cf.amount.amount == 0:
                return Decimal(cf.period)
            fraction = -prev_cumulative / cf.amount.amount
            return Decimal(sorted_flows[i - 1].period if i > 0 else 0) + fraction
    return None


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    variable: str
    low_value: Decimal
    base_value: Decimal
    high_value: Decimal
    npv_low: Money
    npv_base: Money
    npv_high: Money

    @property
    def swing(self) -> Money:
        """The range of NPV outcomes — the standard tornado-chart metric."""
        return self.npv_high - self.npv_low if self.npv_high >= self.npv_low else self.npv_low - self.npv_high


def one_way_sensitivity(
    *,
    variable_name: str,
    base_cash_flows: list[CashFlow],
    discount_rate: Percentage,
    variable_period: int,
    low_amount: Decimal,
    base_amount: Decimal,
    high_amount: Decimal,
) -> SensitivityResult:
    """Recomputes NPV with one period's cash flow amount swapped to
    low/base/high, holding everything else constant — the textbook
    one-way sensitivity / tornado-chart input."""

    def _with_override(new_amount: Decimal) -> list[CashFlow]:
        currency = base_cash_flows[0].amount.currency
        return [
            CashFlow(cf.period, Money(new_amount, currency))
            if cf.period == variable_period
            else cf
            for cf in base_cash_flows
        ]

    npv_low = net_present_value(_with_override(low_amount), discount_rate)
    npv_base = net_present_value(_with_override(base_amount), discount_rate)
    npv_high = net_present_value(_with_override(high_amount), discount_rate)

    return SensitivityResult(
        variable=variable_name,
        low_value=low_amount,
        base_value=base_amount,
        high_value=high_amount,
        npv_low=npv_low,
        npv_base=npv_base,
        npv_high=npv_high,
    )


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    name: str
    cash_flows: list[CashFlow]
    probability: Percentage | None = None


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: str
    npv: Money
    irr: Percentage | None
    probability: Percentage | None


def evaluate_scenarios(
    scenarios: list[ScenarioDefinition], discount_rate: Percentage
) -> list[ScenarioResult]:
    results = []
    for scenario in scenarios:
        npv = net_present_value(scenario.cash_flows, discount_rate)
        irr = internal_rate_of_return(scenario.cash_flows)
        results.append(
            ScenarioResult(
                name=scenario.name, npv=npv, irr=irr, probability=scenario.probability
            )
        )
    return results


def probability_weighted_npv(results: list[ScenarioResult]) -> Money:
    weighted = [r for r in results if r.probability is not None]
    if not weighted:
        raise FinancialModelingError(
            "probability_weighted_npv requires every scenario to carry a probability"
        )
    total_probability = sum((r.probability.fraction for r in weighted), Decimal("0"))
    if abs(total_probability - Decimal("1")) > Decimal("0.001"):
        raise FinancialModelingError(
            f"Scenario probabilities must sum to 1.0, got {total_probability}"
        )
    currency = weighted[0].npv.currency
    total = sum((r.npv.amount * r.probability.fraction for r in weighted), Decimal("0"))
    return Money(total, currency)


# ---------------------------------------------------------------------------
# Red flags — sanity checks against industry benchmarks. These surface
# alongside a valuation, they don't block it: the model doesn't know
# enough about your specific deal to override your judgment, but it can
# tell you when an assumption sits outside where similar deals usually
# land.
# ---------------------------------------------------------------------------


def evaluate_assumption_flags(
    *,
    discount_rate: Percentage,
    cash_flows: list[CashFlow],
    irr: Percentage | None,
    industry: str | None = None,
) -> list[str]:
    from sdie.financial_modeling.domain.benchmarks import get_benchmark

    benchmark = get_benchmark(industry)
    flags: list[str] = []
    discount_pct = discount_rate.as_percent()

    if discount_pct < benchmark.typical_wacc_low:
        flags.append(
            f"The {discount_pct:.1f}% discount rate is below the typical {benchmark.industry} "
            f"range ({benchmark.typical_wacc_low:.0f}\u2013{benchmark.typical_wacc_high:.0f}%). "
            "A discount rate that's too low overstates NPV — confirm the cost of capital used here."
        )
    elif discount_pct > benchmark.typical_wacc_high:
        flags.append(
            f"The {discount_pct:.1f}% discount rate is above the typical {benchmark.industry} "
            f"range ({benchmark.typical_wacc_low:.0f}\u2013{benchmark.typical_wacc_high:.0f}%). "
            "Confirm this reflects genuinely higher project risk, not an overly conservative default."
        )

    if irr is not None:
        irr_pct = irr.as_percent()
        if irr_pct > benchmark.typical_irr_hurdle * 2:
            flags.append(
                f"The {irr_pct:.1f}% IRR is more than double the typical {benchmark.industry} hurdle "
                f"rate (~{benchmark.typical_irr_hurdle:.0f}%). Unusually high IRRs are often a sign of "
                "an optimistic revenue ramp or an understated cost base — worth a second look."
            )

    non_initial_flows = [cf for cf in cash_flows if cf.period > 0]
    if non_initial_flows and all(cf.amount.is_negative() for cf in non_initial_flows):
        flags.append(
            "Every period after the initial investment is still cash-negative — this model has no "
            "point at which the project generates positive cash flow within the modeled horizon."
        )

    return flags
