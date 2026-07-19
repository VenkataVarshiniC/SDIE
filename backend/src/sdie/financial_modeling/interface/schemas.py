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
