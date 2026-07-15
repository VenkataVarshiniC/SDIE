"""Application-layer DTOs. These cross use-case boundaries; HTTP schemas in
the interface layer are separate and map to/from these — the API contract
is allowed to evolve independently of the use-case contract."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CashFlowInput:
    period: int
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CreateCashFlowModelCommand:
    tenant_id: UUID
    project_name: str
    currency: str
    discount_rate_percent: Decimal
    cash_flows: list[CashFlowInput]


@dataclass(frozen=True, slots=True)
class CashFlowModelResult:
    model_id: UUID
    project_name: str
    currency: str
    discount_rate_percent: Decimal
    npv: Decimal
    irr_percent: Decimal | None
    payback_period: Decimal | None


@dataclass(frozen=True, slots=True)
class ScenarioInput:
    name: str
    cash_flows: list[CashFlowInput]
    probability_percent: Decimal | None = None


@dataclass(frozen=True, slots=True)
class EvaluateScenariosCommand:
    tenant_id: UUID
    project_name: str
    currency: str
    discount_rate_percent: Decimal
    scenarios: list[ScenarioInput]


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    name: str
    npv: Decimal
    irr_percent: Decimal | None
    probability_percent: Decimal | None


@dataclass(frozen=True, slots=True)
class EvaluateScenariosResult:
    outcomes: list[ScenarioOutcome]
    probability_weighted_npv: Decimal | None


@dataclass(frozen=True, slots=True)
class SensitivityInput:
    tenant_id: UUID
    currency: str
    discount_rate_percent: Decimal
    base_cash_flows: list[CashFlowInput]
    variable_name: str
    variable_period: int
    low_amount: Decimal
    base_amount: Decimal
    high_amount: Decimal


@dataclass(frozen=True, slots=True)
class SensitivityOutcome:
    variable: str
    npv_low: Decimal
    npv_base: Decimal
    npv_high: Decimal
    swing: Decimal
