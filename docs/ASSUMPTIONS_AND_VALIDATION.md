# Assumptions and validation

## Value classification

| Input class | Classification |
|---|---|
| January 2026 software WACC point estimate, 9.34% | Externally observed U.S. sector average from NYU Stern / Damodaran |
| WACC working range, point ±1.5 pp | Analyst-assumed diagnostic range |
| IRR hurdle, 1.5× WACC | Analyst-assumed convention |
| Revenue, margins, opex, D&A, tax, capex, working capital | Synthetic forecast inputs |
| Scenario probabilities | Synthetic analyst judgments |
| Investment cash flows and capital requirements | Synthetic case-study values |
| Portfolio recommendation | Calculated from synthetic inputs |

Source: [NYU Stern / Aswath Damodaran — Cost of Capital by Sector, January 2026](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html).

## Accounting-to-cash-flow controls

- EBITDA excludes D&A.
- D&A is subtracted once to calculate EBIT and added back once in FCFF.
- Taxes are applied to positive EBIT only; no unmodeled tax benefit is created for losses.
- Capex is a cash outflow and is not added to operating expense.
- Only the **change** in working capital is deducted, not the ending working-capital balance.
- Accounting profit is never substituted for free cash flow.

## Discounting convention

- Period 0 is undiscounted.
- Annual forecast cash flows occur at year-end.
- `NPV = Σ CF_t / (1 + r)^t`.
- No terminal value is included in the documented case.
- Payback is simple, undiscounted, and fractional within the crossing period.

## Hand-verifiable FCFF test

For revenue $100, 60% gross margin, opex 20% of revenue, D&A 10%, tax 20%, capex 10%, no revenue growth, and no change in working capital:

- EBITDA = $60 − $20 = $40.
- EBIT = $40 − $10 = $30.
- Taxes = $30 × 20% = $6.
- NOPAT = $24.
- FCFF = $24 + $10 − $10 − $0 = $24.
- Five annual $24 cash flows less a $100 initial investment at 0% produce NPV $20 and payback 4.1667 years.

The unit test asserts every intermediate line.

## Independent portfolio NPV cross-check

The optimized portfolio was recomputed independently from its aggregated cash flows using the direct discount-factor formula, outside the portfolio service:

| Period | Cash flow | Discount factor at 9.34% | Present value |
|---:|---:|---:|---:|
| 0 | $(7,000,000) | 1.00000000 | $(7,000,000.00) |
| 1 | $1,650,000 | 0.91457838 | $1,509,054.33 |
| 2 | $2,450,000 | 0.83645361 | $2,049,311.35 |
| 3 | $3,450,000 | 0.76500239 | $2,639,258.24 |
| 4 | $4,450,000 | 0.69965465 | $3,113,463.17 |
| 5 | $5,250,000 | 0.63988901 | $3,359,417.31 |

Sum: **$5,670,504.40**, matching SDIE to the cent.

## Constraint validation

Tests verify:

- Budget is never exceeded.
- Dependencies must exist and must be selected with their dependent project.
- At most one project per mutually exclusive group can be selected.
- The exact optimizer can beat a highest-IRR-first portfolio in a hand-verifiable case.
- Explicit baselines must themselves be feasible.
- Downside exposure is calculated on the selected portfolio.

## Forecast accuracy

No forecast-accuracy percentage is reported. The case has no historical actual-versus-forecast series, so any accuracy claim would be invented.
