"""Financial modeling domain. Pure Python, zero I/O, zero LLM involvement.
Every function here must be deterministic and reproducible: same inputs,
same outputs, byte for byte. This is the layer a McKinsey reviewer will
actually check against a spreadsheet."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import Money, Percentage, TenantId


class FinancialModelingError(ValueError):
    """Domain-level validation error for this context."""


@dataclass(frozen=True, slots=True)
class CashFlow:
    """A single period's net cash flow. Period 0 is the initial investment
    and is conventionally negative."""

    period: int
    amount: Money

    def __post_init__(self) -> None:
        if self.period < 0:
            raise FinancialModelingError("Period must be >= 0")


@dataclass(frozen=True, kw_only=True)
class CashFlowModelCreated(DomainEvent):
    model_id: UUID
    project_name: str


@dataclass(frozen=True, kw_only=True)
class ScenarioEvaluated(DomainEvent):
    model_id: UUID
    scenario_name: str
    npv: Decimal
    irr: Decimal | None


@dataclass(slots=True)
class CashFlowModel(AggregateRoot):
    """Aggregate root for a discounted cash flow model. One model can hold
    several named scenarios (base/upside/downside) that share the same cash
    flow *structure* but different assumptions — cash flows are supplied
    per-scenario by the caller, this aggregate just enforces invariants and
    stores the audit-relevant identity."""

    id: UUID
    tenant_id: TenantId
    project_name: str
    currency: str
    discount_rate: Percentage
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cash_flows: list[CashFlow] = field(default_factory=list)
    npv: Money | None = None
    irr: Percentage | None = None
    payback_period: Decimal | None = None

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        project_name: str,
        currency: str = "USD",
        discount_rate: Percentage,
    ) -> CashFlowModel:
        if not project_name.strip():
            raise FinancialModelingError("project_name must not be empty")
        if discount_rate.fraction < 0:
            raise FinancialModelingError("discount_rate cannot be negative")

        model = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            project_name=project_name,
            currency=currency,
            discount_rate=discount_rate,
        )
        model.raise_event(
            CashFlowModelCreated(
                tenant_id=tenant_id.value,
                model_id=model.id,
                project_name=project_name,
            )
        )
        return model

    def attach_evaluation(
        self,
        *,
        cash_flows: list[CashFlow],
        npv: Money,
        irr: Percentage | None,
        payback_period: Decimal | None,
    ) -> None:
        """Records the base-case valuation on the aggregate itself, so it
        round-trips through persistence — a model without its computed
        results attached is not something this platform should be able to
        reload and call 'the same analysis' later."""
        self.cash_flows = cash_flows
        self.npv = npv
        self.irr = irr
        self.payback_period = payback_period
        self.raise_event(
            ScenarioEvaluated(
                tenant_id=self.tenant_id.value,
                model_id=self.id,
                scenario_name="base",
                npv=npv.amount,
                irr=irr.fraction if irr else None,
            )
        )
