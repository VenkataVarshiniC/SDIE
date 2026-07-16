from uuid import uuid4

import pytest

from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    QuantSourceRef,
    RecommendationSynthesisError,
)
from sdie.shared_kernel.domain.value_objects import TenantId


def make_rationale(**overrides) -> DecisionRationale:
    defaults = dict(
        tenant_id=TenantId(uuid4()),
        title="Market entry approach",
        quant_source=QuantSourceRef(context="decision_analysis", analysis_id=uuid4()),
        recommended_option="Acquire competitor",
        confidence_note="High confidence; weighted score margin > 0.3",
    )
    defaults.update(overrides)
    return DecisionRationale.create(**defaults)


class TestDecisionRationaleCreation:
    def test_current_recommendation_defaults_to_original(self):
        rationale = make_rationale()
        assert rationale.current_recommendation == "Acquire competitor"
        assert rationale.overrides == []

    def test_rejects_empty_title(self):
        with pytest.raises(RecommendationSynthesisError):
            make_rationale(title="  ")

    def test_rejects_empty_recommended_option(self):
        with pytest.raises(RecommendationSynthesisError):
            make_rationale(recommended_option="")

    def test_raises_creation_event(self):
        rationale = make_rationale()
        events = rationale.pull_pending_events()
        assert len(events) == 1
        assert events[0].recommended_option == "Acquire competitor"


class TestOverride:
    def test_override_updates_current_recommendation_but_keeps_original(self):
        rationale = make_rationale()
        rationale.pull_pending_events()  # clear creation event

        rationale.override(
            overridden_by="jane.analyst",
            reason="Regulatory risk not captured in the MCDA weights",
            new_recommended_option="Partner / JV",
        )

        assert rationale.current_recommendation == "Partner / JV"
        assert rationale.recommended_option == "Acquire competitor"  # original preserved
        assert len(rationale.overrides) == 1
        assert rationale.overrides[0].reason == "Regulatory risk not captured in the MCDA weights"

    def test_rejects_override_without_reason(self):
        rationale = make_rationale()
        with pytest.raises(RecommendationSynthesisError):
            rationale.override(overridden_by="jane", reason="  ", new_recommended_option="X")

    def test_rejects_override_with_empty_new_option(self):
        rationale = make_rationale()
        with pytest.raises(RecommendationSynthesisError):
            rationale.override(overridden_by="jane", reason="valid reason", new_recommended_option="")

    def test_multiple_overrides_keep_full_history(self):
        rationale = make_rationale()
        rationale.override(overridden_by="jane", reason="reason one", new_recommended_option="Option B")
        rationale.override(overridden_by="bob", reason="reason two", new_recommended_option="Option C")

        assert rationale.current_recommendation == "Option C"
        assert len(rationale.overrides) == 2
        assert rationale.overrides[0].new_recommended_option == "Option B"
