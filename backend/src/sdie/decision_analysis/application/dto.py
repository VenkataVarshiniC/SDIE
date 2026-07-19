from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CriterionInput:
    name: str
    weight: float
    higher_is_better: bool = True


@dataclass(frozen=True, slots=True)
class MCDAOptionInput:
    name: str
    scores: dict[str, float]


@dataclass(frozen=True, slots=True)
class RankOptionsCommand:
    tenant_id: UUID
    title: str
    criteria: list[CriterionInput]
    options: list[MCDAOptionInput]


@dataclass(frozen=True, slots=True)
class MCDARankingResult:
    option: str
    weighted_score: float
    normalized_scores: dict[str, float]


@dataclass(frozen=True, slots=True)
class WeightRobustnessResult:
    criterion: str
    current_weight: float
    flips_at_weight: float | None
    direction: str


@dataclass(frozen=True, slots=True)
class RankOptionsResult:
    analysis_id: UUID
    rankings: list[MCDARankingResult]
    recommended_option: str
    weight_robustness: list[WeightRobustnessResult]
    flags: list[str]


@dataclass(frozen=True, slots=True)
class OutcomeInput:
    name: str
    probability: float
    payoff: float


@dataclass(frozen=True, slots=True)
class DecisionOptionInput:
    name: str
    outcomes: list[OutcomeInput]


@dataclass(frozen=True, slots=True)
class EvaluateDecisionTreeCommand:
    tenant_id: UUID
    title: str
    options: list[DecisionOptionInput]


@dataclass(frozen=True, slots=True)
class EvaluateDecisionTreeResult:
    analysis_id: UUID
    ranked_options: list[tuple[str, float]]
    recommended_option: str
    expected_value_with_perfect_info: float
    expected_value_of_perfect_information: float
    flags: list[str]
    probability_breakeven: dict | None


@dataclass(frozen=True, slots=True)
class DistributionInput:
    name: str
    kind: str
    params: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class RunMonteCarloCommand:
    tenant_id: UUID
    title: str
    variables: list[DistributionInput]
    fixed_costs: float
    iterations: int
    seed: int


@dataclass(frozen=True, slots=True)
class HistogramBinDTO:
    bin_start: float
    bin_end: float
    count: int


@dataclass(frozen=True, slots=True)
class MonteCarloResultDTO:
    analysis_id: UUID
    iterations: int
    seed: int
    mean: float
    std_dev: float
    percentile_5: float
    percentile_50: float
    percentile_95: float
    probability_negative: float
    histogram: list[HistogramBinDTO]
