# Executive investment decision memo

**Decision:** Fund the data foundation modernization and enterprise AI workflow module; defer international self-serve expansion under the current $8.5 million ceiling.

## Business context

A hypothetical mid-market software company must allocate FY27 growth capital across three indivisible investments. The case uses synthetic forecasts solely to demonstrate traceable corporate-finance decision support.

## Capital requirement

The recommended combination deploys $7.0 million, or 82.35% of available capital. The enterprise AI investment depends on the data foundation, and the recommendation satisfies that prerequisite.

## Financial findings

The selected portfolio has modeled NPV of $5.671 million, IRR of 31.57%, and payback of 2.84 years at a 9.34% discount rate. The defined baseline—data foundation plus international expansion—has NPV of $3.829 million. Optimization adds $1.842 million of NPV.

The representative enterprise AI operating forecast produces $1.537 million of base-case NPV, a 20.5% IRR, and payback in 3.22 years over the explicit five-year horizon.

## Scenarios and sensitivity

The enterprise AI downside, base, and upside NPVs are $(4.226) million, $1.537 million, and $5.917 million. At 25% / 50% / 25% probabilities, expected NPV is $1.191 million.

Gross margin is the most material tested driver. A 3-point downside shock reduces NPV to approximately $(0.019) million. Increasing capex from 6% to 8% of revenue reduces NPV to $0.154 million. The annual constant-growth break-even is approximately (0.12)%.

## Risks and constraints

- Migration timing and platform-reuse savings affect the data foundation.
- Enterprise adoption and inference costs affect the AI module.
- Localization, acquisition cost, and conversion affect international expansion.
- The portfolio's downside NPV remains positive at $0.295 million, but the $5.376 million gap from base NPV shows substantial forecast exposure.
- Industry WACC is a benchmark, not a substitute for project-specific risk estimation.

## Recommendation

Approve the selected $7.0 million portfolio, stage-gate the AI module against data-foundation milestones, and monitor gross margin, capex, and enterprise adoption as explicit decision triggers. Re-run the optimizer if the capital ceiling or downside cash flows change.

The generated ten-section PDF version is available from the capital-allocation dashboard and from `scripts/run_financial_case_study.py --pdf <path>`.
