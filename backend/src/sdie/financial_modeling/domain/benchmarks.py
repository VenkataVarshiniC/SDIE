"""Industry benchmark table sourced from real cost-of-capital data —
NYU Stern / Prof. Aswath Damodaran's Cost of Capital by Sector dataset
(US public-company data, January 2026 snapshot; see
https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html).

Point-estimate WACC values below are the Damodaran industry averages as of
the January 2026 refresh. `typical_wacc_low`/`typical_wacc_high` are that
point estimate ± 1.5pp (a defensible working range for a single "industry"
label covering many companies of different sizes and leverage — see
Damodaran's own guidance that industry WACC is a starting point, not a
precise answer). `typical_irr_hurdle` follows the common practitioner rule
of thumb of ~1.4-1.6x WACC as a project hurdle rate (compensating for the
fact that a project-level IRR carries idiosyncratic risk a diversified
public-company WACC doesn't price in) — this multiplier is a modeling
assumption, not itself sourced from Damodaran, and is documented as such.

This is deliberately a curated snapshot, not a live feed: Damodaran
republishes annually in January, so a snapshot pinned to a cited date is
more auditable than a scraper that could silently start returning stale or
malformed data. Refreshing this table is a one-line-per-row change,
reviewed like any other code change touching a figure used in real
capital-allocation flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

Industry = str


@dataclass(frozen=True, slots=True)
class IndustryBenchmark:
    industry: str
    typical_wacc_low: Decimal
    typical_wacc_high: Decimal
    typical_irr_hurdle: Decimal
    source_wacc_point_estimate: Decimal  # the actual Damodaran figure this range is built around


def _benchmark(industry: str, wacc_point: str, hurdle_multiplier: Decimal = Decimal("1.5")) -> IndustryBenchmark:
    point = Decimal(wacc_point)
    return IndustryBenchmark(
        industry=industry,
        typical_wacc_low=point - Decimal("1.5"),
        typical_wacc_high=point + Decimal("1.5"),
        typical_irr_hurdle=(point * hurdle_multiplier).quantize(Decimal("0.1")),
        source_wacc_point_estimate=point,
    )


# Source: NYU Stern / Damodaran Cost of Capital by Sector, US data,
# January 2026 refresh. Figures are the "WACC (2026)" column.
INDUSTRY_BENCHMARKS: dict[Industry, IndustryBenchmark] = {
    "software": _benchmark("software", "9.34"),  # Software (System & Application)
    "internet_software": _benchmark("internet_software", "10.66"),  # Software (Internet)
    "retail": _benchmark("retail", "7.27"),  # Retail (General)
    "grocery_retail": _benchmark("grocery_retail", "7.24"),  # Retail (Grocery & Food)
    "manufacturing": _benchmark("manufacturing", "7.70"),  # Machinery, as a manufacturing proxy
    "auto": _benchmark("auto", "9.38"),  # Auto & Truck
    "energy": _benchmark("energy", "5.07"),  # Oil/Gas (Integrated)
    "energy_exploration": _benchmark("energy_exploration", "6.25"),  # Oil/Gas (Production & Exploration)
    "renewable_energy": _benchmark("renewable_energy", "6.04"),  # Green & Renewable Energy
    "healthcare": _benchmark("healthcare", "7.54"),  # Healthcare Products
    "biotech": _benchmark("biotech", "8.49"),  # Drugs (Biotechnology)
    "pharma": _benchmark("pharma", "7.85"),  # Drugs (Pharmaceutical)
    "banking": _benchmark("banking", "4.98"),  # Bank (Money Center) — see note below
    "telecom": _benchmark("telecom", "5.39"),  # Telecom Services
    "media_entertainment": _benchmark("media_entertainment", "7.13"),  # Entertainment
    "hospitality": _benchmark("hospitality", "7.36"),  # Hotel/Gaming
    "real_estate": _benchmark("real_estate", "5.32"),  # REIT
    "semiconductor": _benchmark("semiconductor", "10.55"),  # Semiconductor
    "aerospace_defense": _benchmark("aerospace_defense", "7.60"),  # Aerospace/Defense
    "utilities": _benchmark("utilities", "4.36"),  # Utility (General)
    "transportation": _benchmark("transportation", "6.72"),  # Transportation
    "general": _benchmark("general", "6.96"),  # Total Market (US) — the cross-sector average
}

# Financial-sector caveat, surfaced by get_benchmark's caller rather than
# silently applied: Damodaran himself flags that bank/insurer WACC is not
# meaningfully comparable to non-financial firms (regulatory capital
# requirements dominate, and "debt" for a bank is largely customer
# deposits, not financing). Callers valuing a bank or insurer should treat
# the "banking" entry here as a rough anchor only.
FINANCIAL_SECTOR_KEYS = frozenset({"banking"})


def get_benchmark(industry: str | None) -> IndustryBenchmark:
    return INDUSTRY_BENCHMARKS.get((industry or "general").lower(), INDUSTRY_BENCHMARKS["general"])
