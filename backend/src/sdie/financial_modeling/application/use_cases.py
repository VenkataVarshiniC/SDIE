"""Use cases (interactors). Each one is a single, named business operation.
Orchestrates domain services + repository ports; contains no calculation
logic itself — that lives in domain/services.py so it stays unit-testable
without a database."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sdie.financial_modeling.application.dto import (
    CashFlowInput,
    CashFlowModelResult,
    CreateCashFlowModelCommand,
    EvaluateScenariosCommand,
    EvaluateScenariosResult,
    ScenarioOutcome,
    SensitivityInput,
    SensitivityOutcome,
)
from sdie.financial_modeling.application.ports import CashFlowModelRepository
from sdie.financial_modeling.domain.entities import CashFlow, CashFlowModel
from sdie.financial_modeling.domain.services import (
    ScenarioDefinition,
    evaluate_scenarios,
    internal_rate_of_return,
    net_present_value,
    one_way_sensitivity,
    payback_period,
    probability_weighted_npv,
)
from sdie.shared_kernel.domain.value_objects import Money, Percentage, TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus


def _to_domain_cash_flows(inputs: list[CashFlowInput], currency: str) -> list[CashFlow]:
    return [CashFlow(ci.period, Money(ci.amount, currency)) for ci in inputs]


class CreateCashFlowModelUseCase:
    def __init__(self, repository: CashFlowModelRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: CreateCashFlowModelCommand) -> CashFlowModelResult:
        tenant_id = TenantId(command.tenant_id)
        discount_rate = Percentage.from_percent(command.discount_rate_percent)

        model = CashFlowModel.create(
            tenant_id=tenant_id,
            project_name=command.project_name,
            currency=command.currency,
            discount_rate=discount_rate,
        )

        cash_flows = _to_domain_cash_flows(command.cash_flows, command.currency)
        npv = net_present_value(cash_flows, discount_rate)
        irr = internal_rate_of_return(cash_flows)
        payback = payback_period(cash_flows)

        model.attach_evaluation(cash_flows=cash_flows, npv=npv, irr=irr, payback_period=payback)
        await self._repository.save(model)
        await self._event_bus.publish_all(model.pull_pending_events())

        return CashFlowModelResult(
            model_id=model.id,
            project_name=model.project_name,
            currency=model.currency,
            discount_rate_percent=command.discount_rate_percent,
            npv=npv.amount,
            irr_percent=irr.as_percent() if irr else None,
            payback_period=payback,
        )


class ListCashFlowModelsUseCase:
    def __init__(self, repository: CashFlowModelRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[CashFlowModelResult]:
        models = await self._repository.list_for_tenant(tenant_id)
        return [_to_result(m) for m in models]


class GetCashFlowModelUseCase:
    def __init__(self, repository: CashFlowModelRepository):
        self._repository = repository

    async def execute(self, model_id: UUID, tenant_id: TenantId) -> CashFlowModelResult | None:
        model = await self._repository.get(model_id, tenant_id)
        return _to_result(model) if model else None


def _to_result(model: CashFlowModel) -> CashFlowModelResult:
    return CashFlowModelResult(
        model_id=model.id,
        project_name=model.project_name,
        currency=model.currency,
        discount_rate_percent=model.discount_rate.as_percent(),
        npv=model.npv.amount if model.npv else Decimal("0"),
        irr_percent=model.irr.as_percent() if model.irr else None,
        payback_period=model.payback_period,
    )


class EvaluateScenariosUseCase:
    """Stateless — scenario comparison does not require persistence of the
    intermediate model, only of the resulting recommendation, which is
    owned by the recommendation-synthesis context."""

    async def execute(self, command: EvaluateScenariosCommand) -> EvaluateScenariosResult:
        discount_rate = Percentage.from_percent(command.discount_rate_percent)

        scenario_defs = [
            ScenarioDefinition(
                name=s.name,
                cash_flows=_to_domain_cash_flows(s.cash_flows, command.currency),
                probability=(
                    Percentage.from_percent(s.probability_percent)
                    if s.probability_percent is not None
                    else None
                ),
            )
            for s in command.scenarios
        ]

        results = evaluate_scenarios(scenario_defs, discount_rate)

        weighted_npv = None
        if all(s.probability_percent is not None for s in command.scenarios):
            weighted_npv = probability_weighted_npv(results).amount

        return EvaluateScenariosResult(
            outcomes=[
                ScenarioOutcome(
                    name=r.name,
                    npv=r.npv.amount,
                    irr_percent=r.irr.as_percent() if r.irr else None,
                    probability_percent=r.probability.as_percent() if r.probability else None,
                )
                for r in results
            ],
            probability_weighted_npv=weighted_npv,
        )


class RunSensitivityAnalysisUseCase:
    async def execute(self, command: SensitivityInput) -> SensitivityOutcome:
        discount_rate = Percentage.from_percent(command.discount_rate_percent)
        base_cash_flows = _to_domain_cash_flows(command.base_cash_flows, command.currency)

        result = one_way_sensitivity(
            variable_name=command.variable_name,
            base_cash_flows=base_cash_flows,
            discount_rate=discount_rate,
            variable_period=command.variable_period,
            low_amount=command.low_amount,
            base_amount=command.base_amount,
            high_amount=command.high_amount,
        )

        return SensitivityOutcome(
            variable=result.variable,
            npv_low=result.npv_low.amount,
            npv_base=result.npv_base.amount,
            npv_high=result.npv_high.amount,
            swing=result.swing.amount,
        )
