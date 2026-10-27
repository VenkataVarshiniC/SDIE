# Financial valuation case study

## Case classification

This is a **clearly hypothetical** FY27 capital-allocation case for a mid-market software company. It does not describe actual results, guidance, or hindsight knowledge for any named company. The machine-readable input is [`case-studies/software-product-capital-allocation.json`](../case-studies/software-product-capital-allocation.json).

## Decision

Choose among three product investments under an $8.5 million capital ceiling:

| Investment | Initial capital | Base NPV | IRR | Payback | Downside NPV | Key rule |
|---|---:|---:|---:|---:|---:|---|
| Data foundation modernization | $2.50m | $1.279m | 24.0% | 3.19 years | $0.030m | None |
| Enterprise AI workflow module | $4.50m | $4.392m | 35.6% | 2.67 years | $0.265m | Requires data foundation |
| International self-serve expansion | $3.00m | $2.550m | 32.6% | 2.77 years | $(0.207)m | None |

All investment cash flows are synthetic analyst forecasts. The discount rate is 9.34%, anchored to the January 2026 U.S. Software (System & Application) industry cost of capital. Using an industry average for a project is a starting point, not a project-specific WACC calculation.

## Five-year operating model

The representative enterprise AI module forecast begins with $12.0 million of related base revenue and a $4.5 million initial investment.

Base-case drivers:

- Annual revenue growth: 12%, 15%, 18%, 16%, 12%.
- Gross margin: 78%.
- Operating expenses: 58% of revenue.
- D&A: 3% of revenue.
- Tax rate: 25%.
- Capital expenditures: 6% of revenue.
- Working capital: 8% of revenue.
- Discount rate: 9.34%.
- Terminal value: none.

Formula chain:

1. `Revenue_t = Revenue_(t-1) × (1 + growth_t)`
2. `EBITDA = Revenue × gross margin − operating expenses`
3. `EBIT = EBITDA − D&A`
4. `NOPAT = EBIT − max(EBIT × tax rate, 0)`
5. `FCFF = NOPAT + D&A − capex − change in working capital`
6. The existing SDIE NPV/IRR/payback services value `[-initial investment, FCFF_1 … FCFF_5]`.

Base forecast output:

| Year | Revenue | EBITDA | EBIT | Capex | Change in NWC | FCFF |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | $13.440m | $2.688m | $2.285m | $0.806m | $0.115m | $1.195m |
| 2 | $15.456m | $3.091m | $2.628m | $0.927m | $0.161m | $1.346m |
| 3 | $18.238m | $3.648m | $3.100m | $1.094m | $0.223m | $1.556m |
| 4 | $21.156m | $4.231m | $3.597m | $1.269m | $0.233m | $1.829m |
| 5 | $23.695m | $4.739m | $4.028m | $1.422m | $0.203m | $2.107m |

Base forecast valuation: NPV $1.537 million, IRR 20.5%, payback 3.22 years.

## Scenarios and sensitivity

Scenario probabilities are analyst assumptions: 25% downside, 50% base, and 25% upside.

| Scenario | NPV | IRR |
|---|---:|---:|
| Downside | $(4.226)m | (49.2)% |
| Base | $1.537m | 20.5% |
| Upside | $5.917m | 46.1% |

Probability-weighted expected NPV: **$1.191 million**.

One-way sensitivity uses analyst-assumed shocks: ±2 percentage points for growth, discount rate, and capex; ±3 points for gross margin. Gross margin is the largest modeled driver, ranging from $(0.019) million to $3.093 million of NPV. The constant annual revenue-growth break-even is approximately **(0.12)%**.

## Reproduction

From `backend/`:

```powershell
.\.venv\Scripts\python.exe scripts\run_financial_case_study.py --pdf ..\docs\FY27-investment-memo.pdf
```

The script validates the JSON against the public API schemas, calls the same application services as the endpoints, prints JSON results, and optionally renders the PDF.
