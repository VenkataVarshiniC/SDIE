# Capital allocation results

## Objective and method

Objective: **maximize total portfolio NPV** subject to an $8.5 million capital budget, project dependencies, and any mutually exclusive groups.

Each candidate is a binary decision. SDIE enumerates every feasible binary portfolio and chooses the highest NPV; summed strategic priority breaks exact NPV ties, then lower capital use. This is an exact 0-1 capital-budget solution for up to 20 shortlisted investments, not an IRR ranking.

## Recommended portfolio

Fund:

- Data foundation modernization — $2.5 million.
- Enterprise AI workflow module — $4.5 million; dependency on the data foundation is satisfied.

Defer:

- International self-serve expansion — $3.0 million.

## Calculated result

| Metric | Result |
|---|---:|
| Total candidate capital evaluated | $10.000m |
| Capital budget | $8.500m |
| Capital deployed | $7.000m |
| Capital utilization | 82.35% |
| Portfolio NPV | $5.671m |
| Portfolio IRR | 31.57% |
| Portfolio payback | 2.84 years |
| Downside portfolio NPV | $0.295m |
| Downside exposure (base NPV less downside NPV) | $5.376m |

Portfolio cash flows are `[-$7.000m, $1.650m, $2.450m, $3.450m, $4.450m, $5.250m]` for periods 0–5.

## Baseline comparison

The defined business-as-usual baseline funds the data foundation plus international self-serve expansion. It is feasible, deploys $5.5 million, and produces $3.829 million of NPV.

The optimized portfolio produces **$1.842 million of incremental NPV** versus that baseline. The baseline is an explicit comparison allocation; it is not presented as an optimum.

## Why IRR ranking is insufficient

Enterprise AI has the highest standalone IRR, but it cannot be selected without its data-foundation dependency. Capital is indivisible, so a project-by-project rank does not establish which combination maximizes value. The optimizer evaluates the dependency-compliant combinations directly.

## Decision caveat

The recommendation is a result of synthetic cash flows and a fixed discount rate. It should change when the capital ceiling, project cash flows, dependencies, downside assumptions, or risk-adjusted discount rates change.
