# Resume evidence

## Demonstrated, reproducible metrics

These metrics come from the documented synthetic business case, not test fixtures and not claimed real-world company impact.

| Metric | Evidence |
|---|---:|
| Candidate capital evaluated | $10.0 million |
| Shared capital budget | $8.5 million |
| Recommended capital deployed | $7.0 million |
| Capital utilization | 82.35% |
| Optimized portfolio NPV | $5.671 million |
| Portfolio IRR | 31.57% |
| Incremental NPV versus defined baseline | $1.842 million |
| Downside portfolio NPV | $0.295 million |
| Downside exposure | $5.376 million |
| Named operating scenarios | 3 |
| One-way sensitivity points | 12 across 4 drivers |
| Forecast accuracy | Not reported; no actual-versus-forecast history exists |
| Automated test validation | 143/143 passed: 109 unit and 34 PostgreSQL integration tests |

## Traceability map

- Case inputs: `case-studies/software-product-capital-allocation.json`
- Reproduction: `backend/scripts/run_financial_case_study.py`
- Forecast logic: `backend/src/sdie/financial_modeling/domain/forecasting.py`
- Optimization logic: `backend/src/sdie/financial_modeling/domain/capital_allocation.py`
- Independent validation: `docs/ASSUMPTIONS_AND_VALIDATION.md`
- Results: `docs/CAPITAL_ALLOCATION_RESULTS.md`
- Executive narrative: `docs/EXECUTIVE_INVESTMENT_MEMO.md`

## Impact-first resume bullets

- **Maximized modeled portfolio value to $5.7M NPV—$1.8M above a defined baseline—by engineering an exact 0-1 capital-allocation optimizer across $10.0M of candidate software investments, budget, dependency, and exclusivity constraints.**
- **Built a traceable five-year corporate-finance forecast translating revenue growth, margins, opex, D&A, taxes, capex, and working capital into FCFF, DCF, IRR, payback, three probability-weighted scenarios, four-driver sensitivity, and break-even analysis.**
- **Delivered an executive capital-allocation dashboard and investment-committee PDF with auditable assumptions, risk/downside exposure, and reproducible APIs; expanded the automated inventory to 143 finance, decision-science, reporting, and persistence tests.**

These bullets are written for a Financial Analyst role: quantified outcome first, then analytical method, then decision-support delivery. Keep the word “modeled” when using the case-study metrics.
