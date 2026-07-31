from uuid import uuid4

import pytest

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.application.dto import (
    DecisionAnalysisDeckSection,
    EngagementDeckData,
    EvidenceDocumentSummary,
    FinancialModelDeckSection,
    ProblemFramingDeckSection,
    SynthesisDeckSection,
)
from sdie.workspace.application.ports import EngagementDeckRendererPort, EngagementRepository
from sdie.workspace.application.use_cases import GenerateEngagementDeckUseCase
from sdie.workspace.domain.entities import Engagement, WorkspaceError
from sdie.workspace.infrastructure.reportlab_deck_renderer import ReportLabEngagementDeckRenderer


class FakeRepository(EngagementRepository):
    def __init__(self, engagement):
        self._engagement = engagement

    async def save(self, engagement):
        self._engagement = engagement

    async def get(self, engagement_id, tenant_id):
        return self._engagement

    async def list_for_tenant(self, tenant_id):
        return [self._engagement] if self._engagement else []

    async def delete_all_for_tenant(self, tenant_id):
        count = 1 if self._engagement else 0
        self._engagement = None
        return count

    async def delete(self, engagement_id, tenant_id):
        if self._engagement and self._engagement.id == engagement_id:
            self._engagement = None
            return True
        return False


class FakeRenderer(EngagementDeckRendererPort):
    def __init__(self):
        self.last_engagement = None
        self.last_deck_data = None

    def render(self, engagement, deck_data):
        self.last_engagement = engagement
        self.last_deck_data = deck_data
        return b"%PDF-fake-deck"


def make_engagement() -> Engagement:
    return Engagement.create(tenant_id=TenantId(uuid4()), title="Market entry decision")


class TestGenerateEngagementDeckUseCase:
    async def test_passes_engagement_and_deck_data_to_renderer(self):
        engagement = make_engagement()
        repo = FakeRepository(engagement)
        renderer = FakeRenderer()
        use_case = GenerateEngagementDeckUseCase(repo, renderer)

        deck_data = EngagementDeckData(
            problem_framing=ProblemFramingDeckSection(
                title="Framing", framework="swot", entries={"strengths": ["a"]}, completion_ratio=0.25
            )
        )
        result = await use_case.execute(engagement.id, engagement.tenant_id, deck_data)

        assert result == b"%PDF-fake-deck"
        assert renderer.last_engagement is engagement
        assert renderer.last_deck_data is deck_data

    async def test_works_with_empty_deck_data(self):
        engagement = make_engagement()
        repo = FakeRepository(engagement)
        renderer = FakeRenderer()
        use_case = GenerateEngagementDeckUseCase(repo, renderer)

        result = await use_case.execute(engagement.id, engagement.tenant_id, EngagementDeckData())
        assert result == b"%PDF-fake-deck"

    async def test_raises_when_engagement_not_found(self):
        repo = FakeRepository(None)
        renderer = FakeRenderer()
        use_case = GenerateEngagementDeckUseCase(repo, renderer)

        with pytest.raises(WorkspaceError):
            await use_case.execute(uuid4(), TenantId(uuid4()), EngagementDeckData())


class TestReportLabEngagementDeckRenderer:
    """Real renderer — verifies actual multi-section PDF bytes, not just
    that the port contract is satisfied."""

    def test_produces_valid_pdf_with_no_sections(self):
        engagement = make_engagement()
        renderer = ReportLabEngagementDeckRenderer()

        pdf_bytes = renderer.render(engagement, EngagementDeckData())

        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 500

    def test_produces_larger_pdf_with_all_sections_populated(self):
        engagement = make_engagement()
        renderer = ReportLabEngagementDeckRenderer()

        empty_pdf = renderer.render(engagement, EngagementDeckData())

        full_deck = EngagementDeckData(
            problem_framing=ProblemFramingDeckSection(
                title="Market structure",
                framework="five_forces",
                entries={"competitive_rivalry": ["Three incumbents dominate"]},
                completion_ratio=0.2,
            ),
            evidence_documents=[
                EvidenceDocumentSummary(
                    title="Gartner report", source_label="Gartner 2026, p.14", excerpt="Acquisitions win."
                )
            ],
            financial_model=FinancialModelDeckSection(
                project_name="EU expansion",
                npv="USD 613,573",
                irr_percent="23.5%",
                payback_period="2.6 yrs",
                flags=["Discount rate below typical range"],
            ),
            decision_analysis=DecisionAnalysisDeckSection(
                title="Market entry approach",
                method="mcda_weighted_sum",
                recommended_option="Acquire competitor",
                result_data={
                    "rankings": [
                        {"option": "Acquire competitor", "weighted_score": 0.7},
                        {"option": "Build in-house", "weighted_score": 0.3},
                    ]
                },
            ),
            synthesis=SynthesisDeckSection(
                title="Final rationale",
                recommended_option="Acquire competitor",
                current_recommendation="Partner / JV",
                confidence_note="Margin of 0.4",
                evidence_citations=[
                    EvidenceDocumentSummary(
                        title="Gartner report", source_label="Gartner 2026, p.14", excerpt="Acquisitions win."
                    )
                ],
                override_count=1,
            ),
        )
        full_pdf = renderer.render(engagement, full_deck)

        assert full_pdf.startswith(b"%PDF")
        assert len(full_pdf) > len(empty_pdf)

    def test_does_not_crash_with_only_financial_model_section(self):
        engagement = make_engagement()
        renderer = ReportLabEngagementDeckRenderer()

        deck_data = EngagementDeckData(
            financial_model=FinancialModelDeckSection(
                project_name="Test", npv="USD 100", irr_percent=None, payback_period=None, flags=[]
            )
        )
        pdf_bytes = renderer.render(engagement, deck_data)
        assert pdf_bytes.startswith(b"%PDF")

    def test_does_not_crash_with_only_evidence_section(self):
        engagement = make_engagement()
        renderer = ReportLabEngagementDeckRenderer()

        deck_data = EngagementDeckData(
            evidence_documents=[
                EvidenceDocumentSummary(title="Doc", source_label="Source", excerpt="Excerpt text.")
            ]
        )
        pdf_bytes = renderer.render(engagement, deck_data)
        assert pdf_bytes.startswith(b"%PDF")
