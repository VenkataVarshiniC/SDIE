"""Exact 0-1 capital-budget optimization for a finite project pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sdie.financial_modeling.domain.entities import CashFlow, FinancialModelingError
from sdie.financial_modeling.domain.services import (
    internal_rate_of_return,
    net_present_value,
    payback_period,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage

MAX_EXACT_OPPORTUNITIES = 20


@dataclass(frozen=True, slots=True)
class InvestmentOpportunity:
    investment_id: str
    name: str
    initial_capital: Money
    future_cash_flows: tuple[Money, ...]
    downside_cash_flows: tuple[Money, ...]
    risk_assumption: str
    strategic_priority: int
    dependencies: tuple[str, ...] = ()
    mutually_exclusive_group: str | None = None

    def __post_init__(self) -> None:
        if not self.investment_id.strip() or not self.name.strip():
            raise FinancialModelingError("Investment id and name must not be empty")
        if self.initial_capital.amount <= 0:
            raise FinancialModelingError(f"{self.investment_id}: initial_capital must be positive")
        if not self.future_cash_flows:
            raise FinancialModelingError(f"{self.investment_id}: future_cash_flows must not be empty")
        if len(self.future_cash_flows) != len(self.downside_cash_flows):
            raise FinancialModelingError(
                f"{self.investment_id}: downside and base cash-flow horizons must match"
            )
        currency = self.initial_capital.currency
        if any(flow.currency != currency for flow in self.future_cash_flows + self.downside_cash_flows):
            raise FinancialModelingError(f"{self.investment_id}: all cash flows must use {currency}")
        if not self.risk_assumption.strip():
            raise FinancialModelingError(f"{self.investment_id}: risk_assumption must not be empty")
        if not 1 <= self.strategic_priority <= 5:
            raise FinancialModelingError("strategic_priority must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class InvestmentMetrics:
    opportunity: InvestmentOpportunity
    npv: Money
    irr: Percentage | None
    payback_period: Decimal | None
    downside_npv: Money
    downside_exposure: Money


@dataclass(frozen=True, slots=True)
class CapitalAllocationResult:
    capital_budget: Money
    discount_rate: Percentage
    opportunity_metrics: tuple[InvestmentMetrics, ...]
    selected_investment_ids: tuple[str, ...]
    rejected_investment_ids: tuple[str, ...]
    capital_used: Money
    capital_utilization_percent: Decimal
    portfolio_cash_flows: tuple[CashFlow, ...]
    portfolio_npv: Money
    portfolio_irr: Percentage | None
    portfolio_payback_period: Decimal | None
    downside_portfolio_npv: Money
    downside_exposure: Money
    baseline_investment_ids: tuple[str, ...]
    baseline_npv: Money
    incremental_npv_vs_baseline: Money
    optimization_method: str


def evaluate_investment(
    opportunity: InvestmentOpportunity,
    discount_rate: Percentage,
) -> InvestmentMetrics:
    base_flows = _cash_flows(opportunity, downside=False)
    downside_flows = _cash_flows(opportunity, downside=True)
    npv = net_present_value(base_flows, discount_rate)
    downside_npv = net_present_value(downside_flows, discount_rate)
    return InvestmentMetrics(
        opportunity=opportunity,
        npv=npv,
        irr=internal_rate_of_return(base_flows),
        payback_period=payback_period(base_flows),
        downside_npv=downside_npv,
        downside_exposure=Money(max(npv.amount - downside_npv.amount, Decimal("0")), npv.currency),
    )


def optimize_capital_allocation(
    *,
    opportunities: tuple[InvestmentOpportunity, ...],
    capital_budget: Money,
    discount_rate: Percentage,
    baseline_investment_ids: tuple[str, ...] | None = None,
) -> CapitalAllocationResult:
    """Maximize portfolio NPV subject to budget and logical constraints.

    Every binary project combination is evaluated, which is an exact 0-1
    capital-budget solution (not an IRR ranking heuristic). The explicit
    20-project ceiling keeps worst-case work bounded at about one million
    combinations, appropriate for an investment-committee shortlist.
    """
    if capital_budget.amount <= 0:
        raise FinancialModelingError("capital_budget must be positive")
    if not opportunities:
        raise FinancialModelingError("At least one investment opportunity is required")
    if len(opportunities) > MAX_EXACT_OPPORTUNITIES:
        raise FinancialModelingError(
            f"Exact optimization supports at most {MAX_EXACT_OPPORTUNITIES} opportunities"
        )
    ids = [opportunity.investment_id for opportunity in opportunities]
    if len(set(ids)) != len(ids):
        raise FinancialModelingError("investment_id values must be unique")
    id_set = set(ids)
    if any(dependency not in id_set for item in opportunities for dependency in item.dependencies):
        raise FinancialModelingError("Every dependency must reference an investment in the request")
    if any(item.initial_capital.currency != capital_budget.currency for item in opportunities):
        raise FinancialModelingError("Capital budget and investments must use one currency")

    metrics = tuple(evaluate_investment(item, discount_rate) for item in opportunities)
    metric_by_id = {metric.opportunity.investment_id: metric for metric in metrics}

    best_ids: tuple[str, ...] = ()
    best_npv = Decimal("0")
    best_priority = 0
    best_capital = Decimal("0")
    for mask in range(1 << len(opportunities)):
        candidate_ids = tuple(ids[index] for index in range(len(ids)) if mask & (1 << index))
        if not _is_feasible(candidate_ids, metric_by_id, capital_budget.amount):
            continue
        candidate_npv = sum((metric_by_id[item_id].npv.amount for item_id in candidate_ids), Decimal("0"))
        candidate_priority = sum(
            metric_by_id[item_id].opportunity.strategic_priority for item_id in candidate_ids
        )
        candidate_capital = sum(
            (metric_by_id[item_id].opportunity.initial_capital.amount for item_id in candidate_ids),
            Decimal("0"),
        )
        score = (candidate_npv, candidate_priority, -candidate_capital)
        best_score = (best_npv, best_priority, -best_capital)
        if score > best_score:
            best_ids = candidate_ids
            best_npv = candidate_npv
            best_priority = candidate_priority
            best_capital = candidate_capital

    if baseline_investment_ids is None:
        baseline_ids = _irr_greedy_baseline(metrics, capital_budget.amount)
    else:
        baseline_ids = baseline_investment_ids
        if any(item_id not in id_set for item_id in baseline_ids):
            raise FinancialModelingError("baseline_investment_ids contains an unknown investment")
        if not _is_feasible(baseline_ids, metric_by_id, capital_budget.amount):
            raise FinancialModelingError("baseline_investment_ids is not a feasible portfolio")

    portfolio = _portfolio_values(best_ids, metric_by_id, discount_rate, capital_budget.currency)
    baseline = _portfolio_values(baseline_ids, metric_by_id, discount_rate, capital_budget.currency)
    capital_used = Money(best_capital, capital_budget.currency)
    return CapitalAllocationResult(
        capital_budget=capital_budget,
        discount_rate=discount_rate,
        opportunity_metrics=metrics,
        selected_investment_ids=best_ids,
        rejected_investment_ids=tuple(item_id for item_id in ids if item_id not in set(best_ids)),
        capital_used=capital_used,
        capital_utilization_percent=(best_capital / capital_budget.amount * Decimal("100")).quantize(
            Decimal("0.01")
        ),
        portfolio_cash_flows=portfolio[0],
        portfolio_npv=portfolio[1],
        portfolio_irr=portfolio[2],
        portfolio_payback_period=portfolio[3],
        downside_portfolio_npv=portfolio[4],
        downside_exposure=Money(
            max(portfolio[1].amount - portfolio[4].amount, Decimal("0")), capital_budget.currency
        ),
        baseline_investment_ids=baseline_ids,
        baseline_npv=baseline[1],
        incremental_npv_vs_baseline=Money(
            portfolio[1].amount - baseline[1].amount, capital_budget.currency
        ),
        optimization_method=(
            "Exact 0-1 feasible-set enumeration maximizing portfolio NPV; strategic priority "
            "breaks NPV ties, then lower capital use."
        ),
    )


def _cash_flows(opportunity: InvestmentOpportunity, *, downside: bool) -> list[CashFlow]:
    future = opportunity.downside_cash_flows if downside else opportunity.future_cash_flows
    return [
        CashFlow(0, -opportunity.initial_capital),
        *(CashFlow(period, amount) for period, amount in enumerate(future, start=1)),
    ]


def _is_feasible(
    selected_ids: tuple[str, ...],
    metric_by_id: dict[str, InvestmentMetrics],
    budget: Decimal,
) -> bool:
    selected = set(selected_ids)
    capital = sum(
        (metric_by_id[item_id].opportunity.initial_capital.amount for item_id in selected),
        Decimal("0"),
    )
    if capital > budget:
        return False
    groups: set[str] = set()
    for item_id in selected:
        opportunity = metric_by_id[item_id].opportunity
        if not set(opportunity.dependencies).issubset(selected):
            return False
        if opportunity.mutually_exclusive_group:
            if opportunity.mutually_exclusive_group in groups:
                return False
            groups.add(opportunity.mutually_exclusive_group)
    return True


def _irr_greedy_baseline(
    metrics: tuple[InvestmentMetrics, ...],
    budget: Decimal,
) -> tuple[str, ...]:
    """A familiar but non-optimal comparison policy: highest IRR first."""
    metric_by_id = {metric.opportunity.investment_id: metric for metric in metrics}
    ordered = sorted(
        metrics,
        key=lambda metric: metric.irr.fraction if metric.irr else Decimal("-Infinity"),
        reverse=True,
    )
    selected: set[str] = set()

    def add_dependencies(item_id: str, target: set[str]) -> None:
        for dependency in metric_by_id[item_id].opportunity.dependencies:
            if dependency not in target:
                target.add(dependency)
                add_dependencies(dependency, target)

    for metric in ordered:
        proposed = set(selected)
        proposed.add(metric.opportunity.investment_id)
        add_dependencies(metric.opportunity.investment_id, proposed)
        ordered_proposed = tuple(
            item.opportunity.investment_id
            for item in metrics
            if item.opportunity.investment_id in proposed
        )
        if _is_feasible(ordered_proposed, metric_by_id, budget):
            selected = proposed
    return tuple(item.opportunity.investment_id for item in metrics if item.opportunity.investment_id in selected)


def _portfolio_values(
    selected_ids: tuple[str, ...],
    metric_by_id: dict[str, InvestmentMetrics],
    discount_rate: Percentage,
    currency: str,
) -> tuple[tuple[CashFlow, ...], Money, Percentage | None, Decimal | None, Money]:
    if not selected_ids:
        zero_flows = (CashFlow(0, Money.zero(currency)),)
        return zero_flows, Money.zero(currency), None, None, Money.zero(currency)
    selected = [metric_by_id[item_id].opportunity for item_id in selected_ids]
    horizon = max(len(item.future_cash_flows) for item in selected)
    base_amounts = [-sum((item.initial_capital.amount for item in selected), Decimal("0"))]
    downside_amounts = list(base_amounts)
    for period in range(horizon):
        base_amounts.append(
            sum(
                (
                    item.future_cash_flows[period].amount
                    for item in selected
                    if period < len(item.future_cash_flows)
                ),
                Decimal("0"),
            )
        )
        downside_amounts.append(
            sum(
                (
                    item.downside_cash_flows[period].amount
                    for item in selected
                    if period < len(item.downside_cash_flows)
                ),
                Decimal("0"),
            )
        )
    base_flows = tuple(
        CashFlow(period, Money(amount, currency)) for period, amount in enumerate(base_amounts)
    )
    downside_flows = [
        CashFlow(period, Money(amount, currency)) for period, amount in enumerate(downside_amounts)
    ]
    base_list = list(base_flows)
    return (
        base_flows,
        net_present_value(base_list, discount_rate),
        internal_rate_of_return(base_list),
        payback_period(base_list),
        net_present_value(downside_flows, discount_rate),
    )
