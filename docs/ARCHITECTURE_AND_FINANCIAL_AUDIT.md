# Architecture and financial-model audit

Audit date: 2026-10-26. Baseline commit: `64c4a30` (`main`). Implementation branch: `codex/financial-capital-allocation`.

## Existing capability assessment

| Capability | Baseline status | Evidence and limitation | Enhancement in this branch |
|---|---|---|---|
| DCF / NPV | Complete for explicit cash-flow series | End-of-period convention, period 0 undiscounted, `Decimal`/`Money`; no operating-driver forecast | Five-year FCFF forecast feeds the same `net_present_value` service |
| IRR | Complete for conventional cash flows | Newton method with bisection fallback; multiple-IRR cash-flow patterns remain economically ambiguous | Bounded divergent Newton steps before fallback |
| Payback | Complete and tested | Undiscounted fractional payback; correctly returns `None` beyond horizon | Reused for forecasts and portfolios |
| Sensitivity | Partial | Changed one cash-flow amount in one period; did not trace operating drivers | Revenue growth, gross margin, discount rate, and capex one-way stresses plus revenue-growth break-even |
| Probability-weighted scenarios | Complete | Required probabilities to total 100%; valued caller-supplied cash-flow scenarios | Driver-based downside/base/upside forecasts now use the same probability discipline |
| Industry cost of capital | Complete but partly analyst-assumed | Jan. 2026 Damodaran observed WACC points were correct; ±1.5 pp ranges and 1.5× IRR hurdles were assumptions | Documentation now separates observed values from ranges/multipliers; banking limitation is surfaced as a flag |
| Monte Carlo | Complete and tested | Seeded normal, triangular, uniform, and lognormal inputs; meaningful only when users provide defensible distributions | No change; not used in the synthetic case because no empirically supported distributions are available |
| Decision trees | Complete and tested | EMV, EVPI, and two-option probability break-even | No change |
| MCDA | Complete and tested | Weighted ranking plus weight-robustness; strategic scores are not financial value | Kept separate from NPV-maximizing capital allocation |
| Recommendation synthesis | Complete | Auditable structured rationale, evidence citations, overrides, optional grounded narrative | No change |
| PDF reporting | Partial | One-page recommendation and engagement deck, not a finance-committee report | Ten-section executive investment memo with forecast, scenarios, sensitivities, risks, and allocation |
| PostgreSQL / APIs | Complete for existing aggregates | Tenant-scoped repositories, row-level context, migrations, and backward-compatible v1 APIs | New forecast/allocation endpoints are deterministic and stateless; existing persisted contracts unchanged |
| Automated tests | Substantial but documentation was stale | Baseline collection found 98 unit tests and 34 integration tests, not the README's older counts | New finance tests cover FCFF, NPV, working capital, taxes, scenarios, optimizer constraints, downside, and PDF |

## Architecture decision

The implementation stays inside the `financial_modeling` bounded context:

- `domain/forecasting.py` converts operating assumptions to FCFF.
- `domain/capital_allocation.py` evaluates investments and solves an exact binary capital-budget problem.
- `application/planning.py` maps primitive inputs to domain value objects and orchestrates stateless analyses.
- Existing `domain/services.py` remains the single source for NPV, IRR, and payback.
- `interface/schemas.py` and `interface/router.py` add backward-compatible API contracts.
- `infrastructure/reportlab_investment_memo.py` is the only new finance component coupled to ReportLab.

This avoids duplicate valuation logic and avoids a migration for analyses that are computed from a complete request and returned immediately.

## Small coherent milestones used

1. Pure five-year forecast and exact optimizer with hand-verifiable tests.
2. Backward-compatible APIs and executive PDF renderer.
3. Capital-allocation dashboard and reproducible synthetic case.
4. Full validation, methodology documents, and resume evidence.

## Remaining numerical and scope limitations

- Annual, end-of-period discounting; no mid-year convention.
- No terminal value in the five-year case. This is conservative but unsuitable for enterprise-value claims without an explicit continuing-value assumption.
- Taxes are floored at zero; net operating loss carryforwards and tax shields are not modeled.
- Nominal versus real cash flows and inflation must be kept consistent by the analyst.
- IRR can be ambiguous for non-conventional cash flows with multiple sign changes; NPV should remain the primary value measure.
- Exact feasible-set enumeration is intentionally limited to 20 shortlisted projects (up to 1,048,576 combinations).
- Scenario probabilities and downside cash flows are analyst assumptions in the synthetic case, not observed frequencies.
- No genuine forecast-accuracy metric exists because the case has no actual-versus-forecast time series.

## Benchmark verification

The official NYU Stern table states that the U.S. sector data are as of January 2026 and reports a 9.34% cost of capital for Software (System & Application). The implementation preserves that observed point estimate. The working range (point ±1.5 percentage points) and hurdle rate (1.5× WACC) remain explicitly labeled analyst conventions, not Damodaran observations.

Source: [NYU Stern / Aswath Damodaran — Cost of Capital by Sector](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html).
