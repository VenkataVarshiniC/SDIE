from __future__ import annotations

from uuid import UUID

import numpy as np

from sdie.decision_analysis.application.dto import (
    EvaluateDecisionTreeCommand,
    EvaluateDecisionTreeResult,
    HistogramBinDTO,
    MCDARankingResult,
    MonteCarloResultDTO,
    RankOptionsCommand,
    RankOptionsResult,
    RunMonteCarloCommand,
    WeightRobustnessResult,
)
from sdie.decision_analysis.application.ports import DecisionAnalysisRepository
from sdie.decision_analysis.domain.entities import DecisionAnalysis, DecisionAnalysisError
from sdie.decision_analysis.domain.services import (
    Criterion,
    DecisionOption,
    DistributionSpec,
    DistributionType,
    MCDAOption,
    Outcome,
    decision_tree_evpi_flags,
    decision_tree_probability_breakeven,
    evaluate_decision_tree,
    mcda_concentration_flags,
    mcda_weight_robustness,
    rank_options_mcda,
    run_monte_carlo,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.event_bus import InProcessEventBus


class RankOptionsUseCase:
    def __init__(self, repository: DecisionAnalysisRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: RankOptionsCommand) -> RankOptionsResult:
        tenant_id = TenantId(command.tenant_id)

        criteria = [Criterion(c.name, c.weight, c.higher_is_better) for c in command.criteria]
        options = [MCDAOption(o.name, o.scores) for o in command.options]

        rankings = rank_options_mcda(criteria, options)

        analysis = DecisionAnalysis.create(tenant_id=tenant_id, title=command.title, method="mcda_weighted_sum")
        result_data = {
            "rankings": [
                {
                    "option": r.option,
                    "weighted_score": r.weighted_score,
                    "normalized_scores": r.normalized_scores,
                }
                for r in rankings
            ]
        }
        analysis.complete(rankings[0].option, result_data)
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

        robustness = mcda_weight_robustness(criteria, options)
        flags = mcda_concentration_flags(criteria)

        return RankOptionsResult(
            analysis_id=analysis.id,
            rankings=[
                MCDARankingResult(r.option, r.weighted_score, r.normalized_scores) for r in rankings
            ],
            recommended_option=rankings[0].option,
            weight_robustness=[
                WeightRobustnessResult(
                    criterion=r.criterion,
                    current_weight=r.current_weight,
                    flips_at_weight=r.flips_at_weight,
                    direction=r.direction,
                )
                for r in robustness
            ],
            flags=flags,
        )


class EvaluateDecisionTreeUseCase:
    def __init__(self, repository: DecisionAnalysisRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: EvaluateDecisionTreeCommand) -> EvaluateDecisionTreeResult:
        tenant_id = TenantId(command.tenant_id)

        options = [
            DecisionOption(
                name=o.name,
                outcomes=[Outcome(out.name, out.probability, out.payoff) for out in o.outcomes],
            )
            for o in command.options
        ]

        result = evaluate_decision_tree(options)

        analysis = DecisionAnalysis.create(tenant_id=tenant_id, title=command.title, method="decision_tree_emv")
        result_data = {
            "ranked_options": [[name, emv] for name, emv in result.ranked_options],
            "expected_value_with_perfect_info": result.expected_value_with_perfect_info,
            "expected_value_of_perfect_information": result.expected_value_of_perfect_information,
        }
        analysis.complete(result.recommended_option, result_data)
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

        flags = decision_tree_evpi_flags(result)

        probability_breakeven = None
        if len(options) == 2 and len(options[0].outcomes) == 2 and len(options[1].outcomes) == 2:
            shared_outcome = options[0].outcomes[0].name
            try:
                breakeven = decision_tree_probability_breakeven(options, shared_outcome)
                probability_breakeven = {
                    "outcome_name": breakeven.outcome_name,
                    "option_a": breakeven.option_a,
                    "option_b": breakeven.option_b,
                    "breakeven_probability": breakeven.breakeven_probability,
                }
            except DecisionAnalysisError:
                pass  # outcomes weren't shared between the two options — no closed-form breakeven applies

        return EvaluateDecisionTreeResult(
            analysis_id=analysis.id,
            ranked_options=result.ranked_options,
            recommended_option=result.recommended_option,
            expected_value_with_perfect_info=result.expected_value_with_perfect_info,
            expected_value_of_perfect_information=result.expected_value_of_perfect_information,
            flags=flags,
            probability_breakeven=probability_breakeven,
        )


class RunMonteCarloUseCase:
    """Default payoff model is additive: payoff = sum(sampled variables) -
    fixed_costs. This covers the common case (revenue driver uncertainty
    minus known costs) without a full formula DSL. A formula-DSL payoff
    (arbitrary expressions over variables) is a natural extension point on
    this use case, not a redesign — see the `payoff_fn` seam in the domain
    service."""

    def __init__(self, repository: DecisionAnalysisRepository, event_bus: InProcessEventBus):
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, command: RunMonteCarloCommand) -> MonteCarloResultDTO:
        tenant_id = TenantId(command.tenant_id)

        variables = [
            DistributionSpec(v.name, DistributionType(v.kind), v.params) for v in command.variables
        ]

        def additive_payoff(samples: dict[str, np.ndarray]) -> np.ndarray:
            total = np.zeros(command.iterations)
            for arr in samples.values():
                total += arr
            return total - command.fixed_costs

        result = run_monte_carlo(
            variables=variables,
            payoff_fn=additive_payoff,
            iterations=command.iterations,
            seed=command.seed,
        )

        analysis = DecisionAnalysis.create(tenant_id=tenant_id, title=command.title, method="monte_carlo")
        result_data = {
            "mean": result.mean,
            "std_dev": result.std_dev,
            "percentile_5": result.percentile_5,
            "percentile_50": result.percentile_50,
            "percentile_95": result.percentile_95,
            "probability_negative": result.probability_negative,
            "seed": result.seed,
            "iterations": result.iterations,
        }
        analysis.complete(f"mean_payoff={result.mean:.2f}", result_data)
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

        histogram = self._build_histogram(result.raw_samples)

        return MonteCarloResultDTO(
            analysis_id=analysis.id,
            iterations=result.iterations,
            seed=result.seed,
            mean=result.mean,
            std_dev=result.std_dev,
            percentile_5=result.percentile_5,
            percentile_50=result.percentile_50,
            percentile_95=result.percentile_95,
            probability_negative=result.probability_negative,
            histogram=histogram,
        )

    @staticmethod
    def _build_histogram(samples: np.ndarray, *, bins: int = 30) -> list[HistogramBinDTO]:
        """Bins the domain layer's already-computed raw samples for
        charting. This is presentation-shaping, not analysis — the
        underlying numbers all come from run_monte_carlo() in the domain
        layer, untouched."""
        counts, edges = np.histogram(samples, bins=bins)
        return [
            HistogramBinDTO(bin_start=float(edges[i]), bin_end=float(edges[i + 1]), count=int(counts[i]))
            for i in range(len(counts))
        ]


class ListDecisionAnalysesUseCase:
    def __init__(self, repository: DecisionAnalysisRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> list[DecisionAnalysis]:
        return await self._repository.list_for_tenant(tenant_id)


class GetDecisionAnalysisUseCase:
    def __init__(self, repository: DecisionAnalysisRepository):
        self._repository = repository

    async def execute(self, analysis_id: UUID, tenant_id: TenantId) -> DecisionAnalysis | None:
        return await self._repository.get(analysis_id, tenant_id)


class ClearAnalysisHistoryUseCase:
    def __init__(self, repository: DecisionAnalysisRepository):
        self._repository = repository

    async def execute(self, tenant_id: TenantId) -> int:
        return await self._repository.delete_all_for_tenant(tenant_id)
