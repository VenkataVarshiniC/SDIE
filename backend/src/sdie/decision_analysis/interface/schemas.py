from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CriterionSchema(BaseModel):
    name: str
    weight: float = Field(ge=0, le=1)
    higher_is_better: bool = True


class MCDAOptionSchema(BaseModel):
    name: str
    scores: dict[str, float]


class RankOptionsRequest(BaseModel):
    title: str
    criteria: list[CriterionSchema] = Field(min_length=1)
    options: list[MCDAOptionSchema] = Field(min_length=2)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> RankOptionsRequest:
        total = sum(c.weight for c in self.criteria)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"criteria weights must sum to 1.0, got {total}")
        return self


class MCDARankingSchema(BaseModel):
    option: str
    weighted_score: float
    normalized_scores: dict[str, float]


class WeightRobustnessSchema(BaseModel):
    criterion: str
    current_weight: float
    flips_at_weight: float | None
    direction: str


class RankOptionsResponse(BaseModel):
    analysis_id: UUID
    rankings: list[MCDARankingSchema]
    recommended_option: str
    weight_robustness: list[WeightRobustnessSchema] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class OutcomeSchema(BaseModel):
    name: str
    probability: float = Field(ge=0, le=1)
    payoff: float


class DecisionOptionSchema(BaseModel):
    name: str
    outcomes: list[OutcomeSchema] = Field(min_length=1)


class EvaluateDecisionTreeRequest(BaseModel):
    title: str
    options: list[DecisionOptionSchema] = Field(min_length=2)


class EvaluateDecisionTreeResponse(BaseModel):
    analysis_id: UUID
    ranked_options: list[tuple[str, float]]
    recommended_option: str
    expected_value_with_perfect_info: float
    expected_value_of_perfect_information: float
    flags: list[str] = Field(default_factory=list)
    probability_breakeven: dict | None = None


class DistributionSchema(BaseModel):
    name: str
    kind: str = Field(pattern="^(normal|triangular|uniform|lognormal)$")
    params: tuple[float, ...]


class HistogramBinSchema(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class RunMonteCarloRequest(BaseModel):
    title: str
    variables: list[DistributionSchema] = Field(min_length=1)
    fixed_costs: float = 0.0
    iterations: int = Field(default=10_000, ge=100, le=1_000_000)
    seed: int = 42


class MonteCarloResponse(BaseModel):
    analysis_id: UUID
    iterations: int
    seed: int
    mean: float
    std_dev: float
    percentile_5: float
    percentile_50: float
    percentile_95: float
    probability_negative: float
    histogram: list[HistogramBinSchema] = Field(default_factory=list)
