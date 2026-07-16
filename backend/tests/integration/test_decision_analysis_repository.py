import uuid

from sdie.decision_analysis.domain.entities import DecisionAnalysis
from sdie.decision_analysis.infrastructure.repository import SqlAlchemyDecisionAnalysisRepository
from tests.integration.conftest import requires_db


@requires_db
class TestDecisionAnalysisRepository:
    async def test_save_and_get_round_trips_result_data(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDecisionAnalysisRepository(tenant_scoped_session)

        analysis = DecisionAnalysis.create(
            tenant_id=tenant_id, title="Integration test ranking", method="mcda_weighted_sum"
        )
        analysis.complete(
            "Option A",
            {"rankings": [{"option": "Option A", "weighted_score": 0.7}]},
        )

        await repo.save(analysis)
        loaded = await repo.get(analysis.id, tenant_id)

        assert loaded is not None
        assert loaded.recommended_option == "Option A"
        assert loaded.result_data["rankings"][0]["weighted_score"] == 0.7

    async def test_list_orders_most_recent_first(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDecisionAnalysisRepository(tenant_scoped_session)

        first = DecisionAnalysis.create(tenant_id=tenant_id, title="First", method="mcda_weighted_sum")
        first.complete("A", {})
        await repo.save(first)

        second = DecisionAnalysis.create(tenant_id=tenant_id, title="Second", method="mcda_weighted_sum")
        second.complete("B", {})
        await repo.save(second)

        results = await repo.list_for_tenant(tenant_id)
        titles = [r.title for r in results]
        assert titles.index("Second") < titles.index("First")

    async def test_get_returns_none_for_unknown_id(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDecisionAnalysisRepository(tenant_scoped_session)
        result = await repo.get(uuid.uuid4(), tenant_id)
        assert result is None
