"""Decision science domain services. Deterministic given a seed — Monte
Carlo results must be reproducible for audit purposes, so every simulation
call requires an explicit seed rather than relying on global RNG state."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from sdie.decision_analysis.domain.entities import DecisionAnalysisError

# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------


class DistributionType(str, Enum):
    NORMAL = "normal"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"
    LOGNORMAL = "lognormal"


@dataclass(frozen=True, slots=True)
class DistributionSpec:
    """Describes the uncertainty on one input variable. Parameter meaning
    depends on `kind`:
      NORMAL:     params = (mean, std_dev)
      TRIANGULAR: params = (min, mode, max)
      UNIFORM:    params = (min, max)
      LOGNORMAL:  params = (mean_of_log, std_of_log)
    """

    name: str
    kind: DistributionType
    params: tuple[float, ...]

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        match self.kind:
            case DistributionType.NORMAL:
                mean, std = self.params
                return rng.normal(mean, std, size)
            case DistributionType.TRIANGULAR:
                lo, mode, hi = self.params
                return rng.triangular(lo, mode, hi, size)
            case DistributionType.UNIFORM:
                lo, hi = self.params
                return rng.uniform(lo, hi, size)
            case DistributionType.LOGNORMAL:
                mu, sigma = self.params
                return rng.lognormal(mu, sigma, size)
        raise DecisionAnalysisError(f"Unsupported distribution kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    iterations: int
    seed: int
    mean: float
    std_dev: float
    percentile_5: float
    percentile_50: float
    percentile_95: float
    probability_negative: float
    raw_samples: np.ndarray  # kept for downstream charting; not serialized as-is


def run_monte_carlo(
    *,
    variables: list[DistributionSpec],
    payoff_fn,
    iterations: int = 10_000,
    seed: int,
) -> MonteCarloResult:
    """`payoff_fn` takes a dict[var_name -> np.ndarray] of sampled values
    (vectorized across `iterations`) and returns an np.ndarray of payoffs.
    Keeping payoff_fn vectorized avoids a Python-level loop over 10k+
    iterations — this is the difference between a sub-second and a
    multi-second sensitivity run at scale."""
    if iterations < 100:
        raise DecisionAnalysisError("iterations must be >= 100 for a stable estimate")
    if not variables:
        raise DecisionAnalysisError("At least one input variable is required")

    rng = np.random.default_rng(seed)
    samples = {v.name: v.sample(rng, iterations) for v in variables}
    payoffs = payoff_fn(samples)

    if not isinstance(payoffs, np.ndarray) or payoffs.shape != (iterations,):
        raise DecisionAnalysisError(
            "payoff_fn must return an ndarray of shape (iterations,)"
        )

    return MonteCarloResult(
        iterations=iterations,
        seed=seed,
        mean=float(np.mean(payoffs)),
        std_dev=float(np.std(payoffs, ddof=1)),
        percentile_5=float(np.percentile(payoffs, 5)),
        percentile_50=float(np.percentile(payoffs, 50)),
        percentile_95=float(np.percentile(payoffs, 95)),
        probability_negative=float(np.mean(payoffs < 0)),
        raw_samples=payoffs,
    )


# ---------------------------------------------------------------------------
# Multi-criteria decision analysis (weighted sum model)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Criterion:
    name: str
    weight: float  # 0..1, all criteria weights must sum to 1.0
    higher_is_better: bool = True


@dataclass(frozen=True, slots=True)
class MCDAOption:
    name: str
    scores: dict[str, float]  # criterion name -> raw score


@dataclass(frozen=True, slots=True)
class MCDARanking:
    option: str
    weighted_score: float
    normalized_scores: dict[str, float]


def rank_options_mcda(
    criteria: list[Criterion], options: list[MCDAOption]
) -> list[MCDARanking]:
    """Weighted sum model with min-max normalization per criterion —
    the standard, explainable MCDA approach (as opposed to AHP, which
    requires pairwise comparison matrices; TOPSIS, which requires a
    distance-to-ideal computation). Chosen because every number in the
    output is traceable to a raw input score and a stated weight, which
    matters more here than marginal ranking precision.
    """
    total_weight = sum(c.weight for c in criteria)
    if abs(total_weight - 1.0) > 1e-6:
        raise DecisionAnalysisError(f"Criteria weights must sum to 1.0, got {total_weight}")
    if not options:
        raise DecisionAnalysisError("At least one option is required")

    criterion_names = [c.name for c in criteria]
    for opt in options:
        missing = set(criterion_names) - set(opt.scores.keys())
        if missing:
            raise DecisionAnalysisError(f"Option '{opt.name}' missing scores for: {missing}")

    normalized: dict[str, dict[str, float]] = {opt.name: {} for opt in options}

    for criterion in criteria:
        values = [opt.scores[criterion.name] for opt in options]
        lo, hi = min(values), max(values)
        span = hi - lo
        for opt in options:
            raw = opt.scores[criterion.name]
            if span == 0:
                norm = 1.0
            elif criterion.higher_is_better:
                norm = (raw - lo) / span
            else:
                norm = (hi - raw) / span
            normalized[opt.name][criterion.name] = norm

    rankings = []
    for opt in options:
        weighted_score = sum(
            normalized[opt.name][c.name] * c.weight for c in criteria
        )
        rankings.append(
            MCDARanking(
                option=opt.name,
                weighted_score=weighted_score,
                normalized_scores=normalized[opt.name],
            )
        )

    return sorted(rankings, key=lambda r: r.weighted_score, reverse=True)


# ---------------------------------------------------------------------------
# Decision tree: expected monetary value + expected value of perfect info
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Outcome:
    name: str
    probability: float
    payoff: float


@dataclass(frozen=True, slots=True)
class DecisionOption:
    name: str
    outcomes: list[Outcome]

    def __post_init__(self) -> None:
        total = sum(o.probability for o in self.outcomes)
        if abs(total - 1.0) > 1e-6:
            raise DecisionAnalysisError(
                f"Outcome probabilities for '{self.name}' must sum to 1.0, got {total}"
            )

    @property
    def expected_value(self) -> float:
        return sum(o.probability * o.payoff for o in self.outcomes)

    @property
    def best_case(self) -> float:
        return max(o.payoff for o in self.outcomes)

    @property
    def worst_case(self) -> float:
        return min(o.payoff for o in self.outcomes)


@dataclass(frozen=True, slots=True)
class DecisionTreeResult:
    ranked_options: list[tuple[str, float]]  # (option name, EMV) descending
    recommended_option: str
    expected_value_with_perfect_info: float
    expected_value_of_perfect_information: float


def evaluate_decision_tree(options: list[DecisionOption]) -> DecisionTreeResult:
    """Expected Monetary Value decision rule plus Expected Value of Perfect
    Information — EVPI tells the executive the maximum they should be
    willing to pay for better market research before deciding, which is a
    direct, quantified bridge to the Evidence & Research context."""
    if not options:
        raise DecisionAnalysisError("At least one option is required")

    ranked = sorted(
        ((opt.name, opt.expected_value) for opt in options), key=lambda x: x[1], reverse=True
    )
    recommended = ranked[0][0]

    all_outcome_names = {o.name for opt in options for o in opt.outcomes}
    ev_perfect_info = 0.0
    for outcome_name in all_outcome_names:
        best_payoff_for_outcome = max(
            (o.payoff for opt in options for o in opt.outcomes if o.name == outcome_name),
            default=0.0,
        )
        probability = next(
            (o.probability for opt in options for o in opt.outcomes if o.name == outcome_name),
            0.0,
        )
        ev_perfect_info += probability * best_payoff_for_outcome

    evpi = ev_perfect_info - ranked[0][1]

    return DecisionTreeResult(
        ranked_options=ranked,
        recommended_option=recommended,
        expected_value_with_perfect_info=ev_perfect_info,
        expected_value_of_perfect_information=evpi,
    )


# ---------------------------------------------------------------------------
# Bayesian updating — for revising option probabilities as evidence arrives
# ---------------------------------------------------------------------------


def bayesian_update(
    prior: dict[str, float], likelihoods: dict[str, float]
) -> dict[str, float]:
    """P(H|E) proportional to P(E|H) * P(H). `prior` and `likelihoods` are
    keyed by the same hypothesis labels. Used when new market-research
    evidence should shift confidence across competing strategic hypotheses
    (fed by the Evidence & Research context's structured findings)."""
    if abs(sum(prior.values()) - 1.0) > 1e-6:
        raise DecisionAnalysisError("Prior probabilities must sum to 1.0")
    missing = set(prior.keys()) - set(likelihoods.keys())
    if missing:
        raise DecisionAnalysisError(f"Missing likelihoods for hypotheses: {missing}")

    unnormalized = {h: prior[h] * likelihoods[h] for h in prior}
    total = sum(unnormalized.values())
    if total == 0:
        raise DecisionAnalysisError("Total evidence probability is zero — check likelihoods")

    return {h: v / total for h, v in unnormalized.items()}
