from uuid import uuid4

import pytest

from sdie.problem_framing.domain.entities import (
    Framework,
    FrameworkAnalysis,
    ProblemFramingError,
    get_template,
)
from sdie.shared_kernel.domain.value_objects import TenantId


class TestFrameworkTemplates:
    def test_five_forces_has_five_sections(self):
        template = get_template(Framework.FIVE_FORCES)
        assert len(template) == 5

    def test_swot_has_four_sections(self):
        template = get_template(Framework.SWOT)
        assert len(template) == 4


class TestFrameworkAnalysis:
    def test_create_with_valid_sections(self):
        analysis = FrameworkAnalysis.create(
            tenant_id=TenantId(uuid4()),
            title="Cloud market entry",
            framework=Framework.FIVE_FORCES,
            entries={"competitive_rivalry": ["Three large incumbents dominate."]},
        )
        assert analysis.completion_ratio == pytest.approx(0.2)

    def test_rejects_unknown_section_key(self):
        with pytest.raises(ProblemFramingError):
            FrameworkAnalysis.create(
                tenant_id=TenantId(uuid4()),
                title="Bad input",
                framework=Framework.SWOT,
                entries={"not_a_real_section": ["x"]},
            )

    def test_rejects_all_empty_sections(self):
        with pytest.raises(ProblemFramingError):
            FrameworkAnalysis.create(
                tenant_id=TenantId(uuid4()),
                title="Empty",
                framework=Framework.SWOT,
                entries={"strengths": []},
            )

    def test_completion_ratio_full(self):
        analysis = FrameworkAnalysis.create(
            tenant_id=TenantId(uuid4()),
            title="Full SWOT",
            framework=Framework.SWOT,
            entries={
                "strengths": ["a"],
                "weaknesses": ["b"],
                "opportunities": ["c"],
                "threats": ["d"],
            },
        )
        assert analysis.completion_ratio == 1.0
