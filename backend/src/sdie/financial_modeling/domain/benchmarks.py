"""Static industry benchmark table. Deliberately not a database table or an
external data feed for v1: these are stable, slow-changing reference
ranges (typical WACC, typical hurdle rates), and hardcoding them here keeps
the check fast, offline, and auditable — you can read exactly what
threshold flagged a given assumption. Extending or correcting a benchmark
is a one-line change reviewed like any other code change, which is
appropriate for numbers that inform real capital decisions.
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


INDUSTRY_BENCHMARKS: dict[Industry, IndustryBenchmark] = {
    "software": IndustryBenchmark("software", Decimal("10"), Decimal("14"), Decimal("20")),
    "retail": IndustryBenchmark("retail", Decimal("8"), Decimal("12"), Decimal("15")),
    "manufacturing": IndustryBenchmark("manufacturing", Decimal("9"), Decimal("13"), Decimal("15")),
    "energy": IndustryBenchmark("energy", Decimal("7"), Decimal("11"), Decimal("12")),
    "healthcare": IndustryBenchmark("healthcare", Decimal("8"), Decimal("11"), Decimal("14")),
    "general": IndustryBenchmark("general", Decimal("8"), Decimal("12"), Decimal("15")),
}


def get_benchmark(industry: str | None) -> IndustryBenchmark:
    return INDUSTRY_BENCHMARKS.get((industry or "general").lower(), INDUSTRY_BENCHMARKS["general"])
