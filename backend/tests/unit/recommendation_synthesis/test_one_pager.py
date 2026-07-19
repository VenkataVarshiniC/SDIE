from uuid import uuid4

import pytest

from sdie.recommendation_synthesis.application.ports import DecisionRationaleRepository, OnePagerRendererPort
from sdie.recommendation_synthesis.application.use_cases import GenerateOnePagerUseCase
from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    EvidenceCitation,
    QuantSourceRef,
    RecommendationSynthesisError,
)
from sdie.recommendation_synthesis.infrastructure.reportlab_renderer import ReportLabOnePagerRenderer
from sdie.shared_kernel.domain.value_objects import TenantId


class FakeRepository(DecisionRationaleRepository):
    def __init__(self, rationale):
        self._rationale = rationale

    async def save(self, rationale):
        self._rationale = rationale

    async def get(self, rationale_id, tenant_id):
        return self._rationale

    async def list_for_tenant(self, tenant_id):
        return [self._rationale] if self._rationale else []


class FakeRenderer(OnePagerRendererPort):
    def __init__(self):
        self.last_rationale = None
        self.last_supporting_data = None

    def render(self, rationale, supporting_data):
        self.last_rationale = rationale
        self.last_supporting_data = supporting_data
        return b"%PDF-fake"


def make_rationale() -> DecisionRationale:
    return DecisionRationale.create(
        tenant_id=TenantId(uuid4()),
        title="Market entry approach",
        quant_source=QuantSourceRef(context="decision_analysis", analysis_id=uuid4()),
        recommended_option="Acquire competitor",
        confidence_note="Margin of 0.4",
        evidence_citations=[
            EvidenceCitation(
                document_id=uuid4(),
                document_title="Gartner",
                source_label="Gartner 2026",
                excerpt="Acquisitions saw faster time-to-revenue.",
                relevance_score=0.09,
            )
        ],
    )


class TestGenerateOnePagerUseCase:
    async def test_passes_rationale_and_supporting_data_to_renderer(self):
        rationale = make_rationale()
        repo = FakeRepository(rationale)
        renderer = FakeRenderer()
        use_case = GenerateOnePagerUseCase(repo, renderer)

        supporting = {"rankings": [{"option": "A", "weighted_score": 0.7}]}
        result = await use_case.execute(rationale.id, rationale.tenant_id, supporting)

        assert result == b"%PDF-fake"
        assert renderer.last_rationale is rationale
        assert renderer.last_supporting_data == supporting

    async def test_works_without_supporting_data(self):
        rationale = make_rationale()
        repo = FakeRepository(rationale)
        renderer = FakeRenderer()
        use_case = GenerateOnePagerUseCase(repo, renderer)

        result = await use_case.execute(rationale.id, rationale.tenant_id, None)
        assert result == b"%PDF-fake"
        assert renderer.last_supporting_data is None

    async def test_raises_when_rationale_not_found(self):
        repo = FakeRepository(None)
        renderer = FakeRenderer()
        use_case = GenerateOnePagerUseCase(repo, renderer)

        with pytest.raises(RecommendationSynthesisError):
            await use_case.execute(uuid4(), TenantId(uuid4()), None)


class TestReportLabRenderer:
    """Real renderer — verifies actual PDF bytes come out, not just that
    the port contract is satisfied."""

    def test_produces_valid_pdf_bytes(self):
        rationale = make_rationale()
        renderer = ReportLabOnePagerRenderer()

        pdf_bytes = renderer.render(rationale, None)

        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000  # a real rendered page, not an empty shell

    def test_renders_with_mcda_supporting_chart(self):
        rationale = make_rationale()
        renderer = ReportLabOnePagerRenderer()

        supporting = {
            "rankings": [
                {"option": "Acquire competitor", "weighted_score": 0.7},
                {"option": "Build in-house", "weighted_score": 0.3},
            ]
        }
        pdf_bytes = renderer.render(rationale, supporting)
        assert pdf_bytes.startswith(b"%PDF")

    def test_renders_with_financial_supporting_data(self):
        rationale = make_rationale()
        renderer = ReportLabOnePagerRenderer()

        supporting = {"npv": "125000.00", "irr_percent": "18.5", "payback_period": "2.3"}
        pdf_bytes = renderer.render(rationale, supporting)
        assert pdf_bytes.startswith(b"%PDF")

    def test_renders_with_override_history(self):
        rationale = make_rationale()
        rationale.override(
            overridden_by="jane.analyst", reason="Regulatory risk", new_recommended_option="Partner / JV"
        )
        renderer = ReportLabOnePagerRenderer()

        pdf_bytes = renderer.render(rationale, None)
        assert pdf_bytes.startswith(b"%PDF")

    def test_does_not_crash_on_unrecognized_supporting_shape(self):
        rationale = make_rationale()
        renderer = ReportLabOnePagerRenderer()

        pdf_bytes = renderer.render(rationale, {"some_unexpected_key": 123})
        assert pdf_bytes.startswith(b"%PDF")
