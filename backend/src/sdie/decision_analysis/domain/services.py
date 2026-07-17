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
# Red flags — the sanity checks a senior reviewer runs by instinct. These
# don't block anything; they surface alongside the recommendation so the
# reader knows what to double-check before trusting it.
# ---------------------------------------------------------------------------


def mcda_concentration_flags(criteria: list[Criterion], *, threshold: float = 0.6) -> list[str]:
    flags = []
    for c in criteria:
        if c.weight >= threshold:
            flags.append(
                f"'{c.name}' carries {c.weight:.0%} of the total weight — a single criterion this "
                "dominant means the recommendation is really a decision about that one factor. "
                "Confirm that reflects genuine priority, not a placeholder weight."
            )
    return flags


def decision_tree_evpi_flags(result: DecisionTreeResult, *, materiality_ratio: float = 0.3) -> list[str]:
    flags = []
    best_emv = result.ranked_options[0][1]
    if best_emv != 0 and result.expected_value_of_perfect_information / abs(best_emv) >= materiality_ratio:
        flags.append(
            f"The value of perfect information (EVPI = {result.expected_value_of_perfect_information:,.0f}) "
            f"is at least {materiality_ratio:.0%} of the best option's expected value. It may be worth "
            "commissioning more research or evidence before committing to this decision."
        )
    return flags


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


# ---------------------------------------------------------------------------
# Robustness analysis — "how much would an input have to move to change the
# answer?" This is the question a senior reviewer asks that a point
# estimate alone never surfaces.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WeightRobustness:
    criterion: str
    current_weight: float
    flips_at_weight: float | None  # None if the ranking never flips within (0,1)
    direction: str  # "increase", "decrease", or "stable"


def _renormalize(criteria: list[Criterion], target: Criterion, new_weight: float) -> list[Criterion]:
    remaining = 1.0 - new_weight
    other_total = sum(c.weight for c in criteria if c.name != target.name)
    if other_total == 0:
        raise DecisionAnalysisError("Cannot renormalize when all other weights are zero")
    return [
        Criterion(target.name, new_weight, target.higher_is_better)
        if c.name == target.name
        else Criterion(c.name, c.weight / other_total * remaining, c.higher_is_better)
        for c in criteria
    ]


def mcda_weight_robustness(
    criteria: list[Criterion], options: list[MCDAOption], *, resolution: float = 0.01
) -> list[WeightRobustness]:
    """For each criterion, scans how far its weight would have to move
    (renormalizing every other weight proportionally to keep the total at
    1.0) before the top-ranked option changes. A criterion with a small
    flip distance means the recommendation is fragile with respect to that
    weight; a criterion that never flips within (0,1) means the
    recommendation is robust to disagreement about that weight entirely.
    """
    baseline = rank_options_mcda(criteria, options)
    top_option = baseline[0].option
    steps = int(1 / resolution)

    results = []
    for target in criteria:
        flip_weight: float | None = None
        direction = "stable"
        for i in range(1, steps):
            delta = i * resolution
            found = False
            for sign in (1, -1):
                candidate = target.weight + sign * delta
                if not (0.0 < candidate < 1.0):
                    continue
                new_criteria = _renormalize(criteria, target, candidate)
                ranking = rank_options_mcda(new_criteria, options)
                if ranking[0].option != top_option:
                    flip_weight = candidate
                    direction = "increase" if sign > 0 else "decrease"
                    found = True
                    break
            if found:
                break
        results.append(
            WeightRobustness(
                criterion=target.name,
                current_weight=target.weight,
                flips_at_weight=flip_weight,
                direction=direction,
            )
        )
    return results


@dataclass(frozen=True, slots=True)
class ProbabilityBreakeven:
    outcome_name: str
    option_a: str
    option_b: str
    breakeven_probability: float | None  # probability of `outcome_name` at which EMV(a) == EMV(b)


def decision_tree_probability_breakeven(
    options: list[DecisionOption], outcome_name: str
) -> ProbabilityBreakeven:
    """Closed-form breakeven: for exactly two options that each have exactly
    two outcomes (one being `outcome_name`), finds the probability of
    `outcome_name` at which the two options' EMVs are equal. Below that
    probability one option wins, above it the other does — this is the
    number a decision-maker should actually be uncertain-checking against,
    not the point estimate probability itself.

    Deliberately scoped to two options / two outcomes: that's the case with
    an exact linear solution. A fully general n-option, n-outcome
    sensitivity surface is a real extension (see the payoff_fn seam used
    elsewhere for the same kind of scoping decision) but adds meaningfully
    more complexity for a case decision-makers rarely need — usually the
    live question is "which of these two paths, under this one uncertain
    event."
    """
    if len(options) != 2:
        raise DecisionAnalysisError(
            "Probability breakeven currently supports exactly two options"
        )

    def _two_outcome_payoffs(option: DecisionOption) -> tuple[float, float]:
        if len(option.outcomes) != 2:
            raise DecisionAnalysisError(
                f"Option '{option.name}' must have exactly two outcomes for breakeven analysis"
            )
        target = next((o for o in option.outcomes if o.name == outcome_name), None)
        other = next((o for o in option.outcomes if o.name != outcome_name), None)
        if target is None or other is None:
            raise DecisionAnalysisError(
                f"Option '{option.name}' does not have an outcome named '{outcome_name}'"
            )
        return target.payoff, other.payoff

    a_target, a_other = _two_outcome_payoffs(options[0])
    b_target, b_other = _two_outcome_payoffs(options[1])

    # EMV_a(p) = p*a_target + (1-p)*a_other; EMV_b(p) analogous.
    # Equal when p * [(a_target - a_other) - (b_target - b_other)] = b_other - a_other
    denominator = (a_target - a_other) - (b_target - b_other)
    if denominator == 0:
        return ProbabilityBreakeven(outcome_name, options[0].name, options[1].name, None)

    p = (b_other - a_other) / denominator
    breakeven = p if 0.0 <= p <= 1.0 else None
    return ProbabilityBreakeven(outcome_name, options[0].name, options[1].name, breakeven)
