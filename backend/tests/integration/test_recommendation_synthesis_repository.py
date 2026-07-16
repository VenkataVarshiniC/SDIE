import uuid

from sdie.recommendation_synthesis.domain.entities import (
    DecisionRationale,
    EvidenceCitation,
    QuantSourceRef,
)
from sdie.recommendation_synthesis.infrastructure.repository import (
    SqlAlchemyDecisionRationaleRepository,
)
from tests.integration.conftest import requires_db


@requires_db
class TestDecisionRationaleRepository:
    async def test_save_and_get_round_trips_citations_and_overrides(
        self, tenant_scoped_session, tenant_id
    ):
        repo = SqlAlchemyDecisionRationaleRepository(tenant_scoped_session)

        rationale = DecisionRationale.create(
            tenant_id=tenant_id,
            title="Integration test rationale",
            quant_source=QuantSourceRef(context="decision_analysis", analysis_id=uuid.uuid4()),
            recommended_option="Acquire competitor",
            confidence_note="High confidence",
            evidence_citations=[
                EvidenceCitation(
                    document_id=uuid.uuid4(),
                    document_title="Test doc",
                    source_label="Test source",
                    excerpt="Some excerpt text",
                    relevance_score=0.5,
                )
            ],
        )
        rationale.override(
            overridden_by="test.analyst", reason="test reason", new_recommended_option="Partner / JV"
        )

        await repo.save(rationale)
        loaded = await repo.get(rationale.id, tenant_id)

        assert loaded is not None
        assert loaded.recommended_option == "Acquire competitor"  # original preserved
        assert loaded.current_recommendation == "Partner / JV"  # override applied
        assert len(loaded.evidence_citations) == 1
        assert loaded.evidence_citations[0].document_title == "Test doc"
        assert len(loaded.overrides) == 1
        assert loaded.overrides[0].reason == "test reason"

    async def test_get_returns_none_for_unknown_id(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDecisionRationaleRepository(tenant_scoped_session)
        result = await repo.get(uuid.uuid4(), tenant_id)
        assert result is None
