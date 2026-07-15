from __future__ import annotations

import numpy as np

from sdie.decision_analysis.application.dto import (
    EvaluateDecisionTreeCommand,
    EvaluateDecisionTreeResult,
    MCDARankingResult,
    MonteCarloResultDTO,
    RankOptionsCommand,
    RankOptionsResult,
    RunMonteCarloCommand,
)
from sdie.decision_analysis.application.ports import DecisionAnalysisRepository
from sdie.decision_analysis.domain.entities import DecisionAnalysis
from sdie.decision_analysis.domain.services import (
    Criterion,
    DecisionOption,
    DistributionSpec,
    DistributionType,
    MCDAOption,
    Outcome,
    evaluate_decision_tree,
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
        analysis.complete(rankings[0].option)
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

        return RankOptionsResult(
            analysis_id=analysis.id,
            rankings=[
                MCDARankingResult(r.option, r.weighted_score, r.normalized_scores) for r in rankings
            ],
            recommended_option=rankings[0].option,
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
        analysis.complete(result.recommended_option)
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

        return EvaluateDecisionTreeResult(
            analysis_id=analysis.id,
            ranked_options=result.ranked_options,
            recommended_option=result.recommended_option,
            expected_value_with_perfect_info=result.expected_value_with_perfect_info,
            expected_value_of_perfect_information=result.expected_value_of_perfect_information,
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
        analysis.complete(f"mean_payoff={result.mean:.2f}")
        await self._repository.save(analysis)
        await self._event_bus.publish_all(analysis.pull_pending_events())

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
        )
