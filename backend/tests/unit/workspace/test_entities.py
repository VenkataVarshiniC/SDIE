from uuid import uuid4

import pytest

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.domain.entities import Engagement, EngagementStatus, WorkspaceError


def make_engagement(**overrides):
    defaults = dict(tenant_id=TenantId(uuid4()), title="Market entry decision")
    defaults.update(overrides)
    return Engagement.create(**defaults)


class TestEngagementCreation:
    def test_starts_in_framing_status(self):
        engagement = make_engagement()
        assert engagement.status == EngagementStatus.FRAMING
        assert engagement.problem_framing_analysis_id is None
        assert engagement.evidence_document_ids == []

    def test_rejects_empty_title(self):
        with pytest.raises(WorkspaceError):
            make_engagement(title="   ")

    def test_raises_creation_event(self):
        engagement = make_engagement()
        events = engagement.pull_pending_events()
        assert len(events) == 1
        assert events[0].title == "Market entry decision"


class TestStageLinking:
    def test_link_problem_framing_advances_to_evidence_gathering(self):
        engagement = make_engagement()
        engagement.link_problem_framing(uuid4())
        assert engagement.status == EngagementStatus.EVIDENCE_GATHERING

    def test_add_evidence_advances_to_evidence_gathering(self):
        engagement = make_engagement()
        doc_id = uuid4()
        engagement.add_evidence(doc_id)
        assert engagement.status == EngagementStatus.EVIDENCE_GATHERING
        assert doc_id in engagement.evidence_document_ids

    def test_add_evidence_is_idempotent(self):
        engagement = make_engagement()
        doc_id = uuid4()
        engagement.add_evidence(doc_id)
        engagement.add_evidence(doc_id)
        assert engagement.evidence_document_ids == [doc_id]

    def test_link_financial_model_advances_to_quant_analysis(self):
        engagement = make_engagement()
        engagement.link_financial_model(uuid4())
        assert engagement.status == EngagementStatus.QUANT_ANALYSIS

    def test_link_decision_analysis_advances_to_quant_analysis(self):
        engagement = make_engagement()
        engagement.link_decision_analysis(uuid4())
        assert engagement.status == EngagementStatus.QUANT_ANALYSIS

    def test_link_rationale_without_quant_reaches_synthesis_not_complete(self):
        engagement = make_engagement()
        engagement.link_rationale(uuid4())
        assert engagement.status == EngagementStatus.SYNTHESIS

    def test_reaches_complete_only_with_rationale_and_quant_analysis(self):
        engagement = make_engagement()
        engagement.link_decision_analysis(uuid4())
        engagement.link_rationale(uuid4())
        assert engagement.status == EngagementStatus.COMPLETE

    def test_reaches_complete_with_financial_model_instead_of_decision_analysis(self):
        engagement = make_engagement()
        engagement.link_financial_model(uuid4())
        engagement.link_rationale(uuid4())
        assert engagement.status == EngagementStatus.COMPLETE

    def test_flexible_ordering_evidence_before_framing_still_reaches_complete(self):
        # deliberately out of the "natural" order — evidence and quant analysis
        # linked before problem framing — status should still compute correctly
        engagement = make_engagement()
        engagement.add_evidence(uuid4())
        engagement.link_decision_analysis(uuid4())
        engagement.link_rationale(uuid4())
        engagement.link_problem_framing(uuid4())
        assert engagement.status == EngagementStatus.COMPLETE

    def test_relinking_financial_model_updates_reference(self):
        engagement = make_engagement()
        first_id = uuid4()
        second_id = uuid4()
        engagement.link_financial_model(first_id)
        engagement.link_financial_model(second_id)
        assert engagement.financial_model_id == second_id

    def test_each_link_raises_stage_completed_event(self):
        engagement = make_engagement()
        engagement.pull_pending_events()
        engagement.link_financial_model(uuid4())
        events = engagement.pull_pending_events()
        assert len(events) == 1
        assert events[0].stage == "financial_model"
