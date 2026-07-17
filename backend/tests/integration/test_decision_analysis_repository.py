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

    async def test_delete_all_for_tenant_removes_only_that_tenant(
        self, db_session, tenant_id
    ):
        from sdie.shared_kernel.domain.value_objects import TenantId
        from sdie.shared_kernel.infrastructure.database import set_tenant_context

        repo = SqlAlchemyDecisionAnalysisRepository(db_session)

        await set_tenant_context(db_session, tenant_id.value)
        mine = DecisionAnalysis.create(tenant_id=tenant_id, title="Mine", method="mcda_weighted_sum")
        mine.complete("A", {})
        await repo.save(mine)

        other_tenant = TenantId(uuid.uuid4())
        await set_tenant_context(db_session, other_tenant.value)
        theirs = DecisionAnalysis.create(
            tenant_id=other_tenant, title="Theirs", method="mcda_weighted_sum"
        )
        theirs.complete("B", {})
        await repo.save(theirs)

        await set_tenant_context(db_session, tenant_id.value)
        deleted_count = await repo.delete_all_for_tenant(tenant_id)
        assert deleted_count == 1

        remaining = await repo.list_for_tenant(tenant_id)
        assert remaining == []

        await set_tenant_context(db_session, other_tenant.value)
        others_remaining = await repo.list_for_tenant(other_tenant)
        assert len(others_remaining) == 1

    async def test_delete_all_for_tenant_returns_zero_when_nothing_to_delete(
        self, tenant_scoped_session, tenant_id
    ):
        repo = SqlAlchemyDecisionAnalysisRepository(tenant_scoped_session)
        deleted_count = await repo.delete_all_for_tenant(tenant_id)
        assert deleted_count == 0
