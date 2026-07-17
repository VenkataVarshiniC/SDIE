import numpy as np
import pytest

from sdie.decision_analysis.domain.entities import DecisionAnalysisError
from sdie.decision_analysis.domain.services import (
    Criterion,
    DecisionOption,
    DistributionSpec,
    DistributionType,
    MCDAOption,
    Outcome,
    bayesian_update,
    evaluate_decision_tree,
    rank_options_mcda,
    run_monte_carlo,
)


class TestMCDA:
    def test_ranks_options_by_weighted_score(self):
        criteria = [
            Criterion("cost", weight=0.6, higher_is_better=False),
            Criterion("quality", weight=0.4, higher_is_better=True),
        ]
        options = [
            MCDAOption("vendor_a", {"cost": 100, "quality": 8}),
            MCDAOption("vendor_b", {"cost": 200, "quality": 10}),
        ]
        rankings = rank_options_mcda(criteria, options)

        assert rankings[0].option == "vendor_a"
        assert rankings[0].weighted_score == pytest.approx(0.6)
        assert rankings[1].option == "vendor_b"
        assert rankings[1].weighted_score == pytest.approx(0.4)

    def test_rejects_weights_not_summing_to_one(self):
        criteria = [Criterion("cost", weight=0.5), Criterion("quality", weight=0.6)]
        options = [MCDAOption("a", {"cost": 1, "quality": 1}), MCDAOption("b", {"cost": 2, "quality": 2})]
        with pytest.raises(DecisionAnalysisError):
            rank_options_mcda(criteria, options)

    def test_rejects_option_missing_criterion_score(self):
        criteria = [Criterion("cost", weight=1.0)]
        options = [MCDAOption("a", {"cost": 1}), MCDAOption("b", {})]
        with pytest.raises(DecisionAnalysisError):
            rank_options_mcda(criteria, options)


class TestDecisionTree:
    def test_emv_and_evpi(self):
        options = [
            DecisionOption(
                "expand",
                [Outcome("high_demand", 0.5, 1000), Outcome("low_demand", 0.5, -200)],
            ),
            DecisionOption(
                "status_quo",
                [Outcome("high_demand", 0.5, 100), Outcome("low_demand", 0.5, 100)],
            ),
        ]
        result = evaluate_decision_tree(options)

        assert result.recommended_option == "expand"
        assert result.ranked_options[0] == ("expand", pytest.approx(400.0))
        assert result.ranked_options[1] == ("status_quo", pytest.approx(100.0))
        assert result.expected_value_with_perfect_info == pytest.approx(550.0)
        assert result.expected_value_of_perfect_information == pytest.approx(150.0)

    def test_rejects_outcome_probabilities_not_summing_to_one(self):
        with pytest.raises(DecisionAnalysisError):
            DecisionOption("bad", [Outcome("a", 0.5, 100), Outcome("b", 0.3, 200)])


class TestBayesianUpdate:
    def test_updates_posterior_correctly(self):
        prior = {"hypothesis_a": 0.5, "hypothesis_b": 0.5}
        likelihoods = {"hypothesis_a": 0.8, "hypothesis_b": 0.2}
        posterior = bayesian_update(prior, likelihoods)

        assert posterior["hypothesis_a"] == pytest.approx(0.8)
        assert posterior["hypothesis_b"] == pytest.approx(0.2)
        assert sum(posterior.values()) == pytest.approx(1.0)

    def test_rejects_prior_not_summing_to_one(self):
        with pytest.raises(DecisionAnalysisError):
            bayesian_update({"a": 0.5, "b": 0.4}, {"a": 0.5, "b": 0.5})


class TestMCDAWeightRobustness:
    def test_flip_point_matches_analytical_solution(self):
        # From TestMCDA.test_ranks_options_by_weighted_score: at cost weight
        # 0.6 vendor_a wins 0.6-0.4. Score_a(w_cost) = w_cost,
        # Score_b(w_cost) = 1 - w_cost (worked out by hand from the
        # normalized scores in that test). They're equal at w_cost = 0.5,
        # so decreasing cost's weight to just below 0.5 must flip it.
        from sdie.decision_analysis.domain.services import mcda_weight_robustness

        criteria = [
            Criterion("cost", weight=0.6, higher_is_better=False),
            Criterion("quality", weight=0.4, higher_is_better=True),
        ]
        options = [
            MCDAOption("vendor_a", {"cost": 100, "quality": 8}),
            MCDAOption("vendor_b", {"cost": 200, "quality": 10}),
        ]

        results = mcda_weight_robustness(criteria, options, resolution=0.01)
        cost_result = next(r for r in results if r.criterion == "cost")

        assert cost_result.direction == "decrease"
        assert cost_result.flips_at_weight == pytest.approx(0.5, abs=0.02)

    def test_never_flips_returns_none(self):
        from sdie.decision_analysis.domain.services import mcda_weight_robustness

        # vendor_a dominates on every criterion — no weight redistribution changes that
        criteria = [
            Criterion("cost", weight=0.5, higher_is_better=False),
            Criterion("quality", weight=0.5, higher_is_better=True),
        ]
        options = [
            MCDAOption("vendor_a", {"cost": 50, "quality": 10}),
            MCDAOption("vendor_b", {"cost": 100, "quality": 5}),
        ]

        results = mcda_weight_robustness(criteria, options, resolution=0.05)
        assert all(r.flips_at_weight is None for r in results)
        assert all(r.direction == "stable" for r in results)


class TestDecisionTreeProbabilityBreakeven:
    def test_matches_analytical_breakeven(self):
        from sdie.decision_analysis.domain.services import decision_tree_probability_breakeven

        options = [
            DecisionOption(
                "expand", [Outcome("high_demand", 0.5, 1000), Outcome("low_demand", 0.5, -200)]
            ),
            DecisionOption(
                "status_quo", [Outcome("high_demand", 0.5, 100), Outcome("low_demand", 0.5, 100)]
            ),
        ]

        result = decision_tree_probability_breakeven(options, "high_demand")

        # hand-solved: p*1000 + (1-p)*-200 = p*100 + (1-p)*100 => p = 0.25
        assert result.breakeven_probability == pytest.approx(0.25)

    def test_rejects_more_than_two_options(self):
        from sdie.decision_analysis.domain.services import decision_tree_probability_breakeven

        options = [
            DecisionOption("a", [Outcome("x", 0.5, 1), Outcome("y", 0.5, 2)]),
            DecisionOption("b", [Outcome("x", 0.5, 1), Outcome("y", 0.5, 2)]),
            DecisionOption("c", [Outcome("x", 0.5, 1), Outcome("y", 0.5, 2)]),
        ]
        with pytest.raises(DecisionAnalysisError):
            decision_tree_probability_breakeven(options, "x")

    def test_rejects_outcome_not_present(self):
        from sdie.decision_analysis.domain.services import decision_tree_probability_breakeven

        options = [
            DecisionOption("a", [Outcome("x", 0.5, 1), Outcome("y", 0.5, 2)]),
            DecisionOption("b", [Outcome("x", 0.5, 1), Outcome("y", 0.5, 2)]),
        ]
        with pytest.raises(DecisionAnalysisError):
            decision_tree_probability_breakeven(options, "nonexistent")


class TestMonteCarlo:
    def test_same_seed_is_reproducible(self):
        variables = [DistributionSpec("revenue", DistributionType.NORMAL, (1000.0, 100.0))]

        def payoff(samples):
            return samples["revenue"] - 800.0

        result_1 = run_monte_carlo(variables=variables, payoff_fn=payoff, iterations=5000, seed=7)
        result_2 = run_monte_carlo(variables=variables, payoff_fn=payoff, iterations=5000, seed=7)

        assert result_1.mean == result_2.mean
        assert result_1.std_dev == result_2.std_dev

    def test_mean_converges_near_analytical_expectation(self):
        variables = [DistributionSpec("revenue", DistributionType.NORMAL, (1000.0, 50.0))]

        def payoff(samples):
            return samples["revenue"] - 800.0

        result = run_monte_carlo(variables=variables, payoff_fn=payoff, iterations=50_000, seed=1)
        # E[revenue] - 800 = 200, large-sample mean should land close to it
        assert result.mean == pytest.approx(200.0, abs=2.0)

    def test_rejects_payoff_fn_with_wrong_shape(self):
        variables = [DistributionSpec("x", DistributionType.UNIFORM, (0.0, 1.0))]
        with pytest.raises(DecisionAnalysisError):
            run_monte_carlo(
                variables=variables,
                payoff_fn=lambda s: np.array([1.0, 2.0]),  # wrong shape
                iterations=1000,
                seed=1,
            )
