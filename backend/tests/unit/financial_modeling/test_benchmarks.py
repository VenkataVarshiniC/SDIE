from decimal import Decimal

from sdie.financial_modeling.domain.benchmarks import INDUSTRY_BENCHMARKS, get_benchmark


class TestIndustryBenchmarks:
    def test_software_benchmark_matches_cited_source(self):
        # Damodaran Software (System & Application), Jan 2026 refresh: 9.34%
        bench = get_benchmark("software")
        assert bench.source_wacc_point_estimate == Decimal("9.34")
        assert bench.typical_wacc_low == Decimal("7.84")
        assert bench.typical_wacc_high == Decimal("10.84")

    def test_unknown_industry_falls_back_to_general(self):
        bench = get_benchmark("not_a_real_industry")
        assert bench.industry == "general"

    def test_none_industry_falls_back_to_general(self):
        bench = get_benchmark(None)
        assert bench.industry == "general"

    def test_lookup_is_case_insensitive(self):
        assert get_benchmark("Software").industry == get_benchmark("software").industry

    def test_all_benchmarks_have_positive_wacc_range(self):
        for bench in INDUSTRY_BENCHMARKS.values():
            assert bench.typical_wacc_low < bench.typical_wacc_high
            assert bench.typical_wacc_low > 0

    def test_utilities_has_lower_wacc_than_software(self):
        # sanity check the data is directionally real: regulated utilities
        # carry materially lower cost of capital than growth software
        utilities = get_benchmark("utilities")
        software = get_benchmark("software")
        assert utilities.source_wacc_point_estimate < software.source_wacc_point_estimate
