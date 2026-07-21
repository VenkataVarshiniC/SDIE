import uuid

from sdie.workspace.domain.entities import Engagement, EngagementStatus
from sdie.workspace.infrastructure.repository import SqlAlchemyEngagementRepository
from tests.integration.conftest import requires_db


@requires_db
class TestEngagementRepository:
    async def test_save_and_get_round_trips_full_aggregate(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyEngagementRepository(tenant_scoped_session)

        engagement = Engagement.create(tenant_id=tenant_id, title="Integration test engagement")
        model_id = uuid.uuid4()
        rationale_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        engagement.add_evidence(doc_id)
        engagement.link_financial_model(model_id)
        engagement.link_rationale(rationale_id)

        await repo.save(engagement)
        loaded = await repo.get(engagement.id, tenant_id)

        assert loaded is not None
        assert loaded.title == "Integration test engagement"
        assert loaded.status == EngagementStatus.COMPLETE
        assert loaded.financial_model_id == model_id
        assert loaded.rationale_id == rationale_id
        assert loaded.evidence_document_ids == [doc_id]

    async def test_list_for_tenant_orders_most_recent_first(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyEngagementRepository(tenant_scoped_session)

        first = Engagement.create(tenant_id=tenant_id, title="First")
        await repo.save(first)
        second = Engagement.create(tenant_id=tenant_id, title="Second")
        await repo.save(second)

        results = await repo.list_for_tenant(tenant_id)
        titles = [r.title for r in results]
        assert titles.index("Second") < titles.index("First")

    async def test_get_returns_none_for_unknown_id(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyEngagementRepository(tenant_scoped_session)
        result = await repo.get(uuid.uuid4(), tenant_id)
        assert result is None

    async def test_relinking_updates_and_persists_status(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyEngagementRepository(tenant_scoped_session)

        engagement = Engagement.create(tenant_id=tenant_id, title="Progressive engagement")
        await repo.save(engagement)

        loaded = await repo.get(engagement.id, tenant_id)
        assert loaded is not None
        assert loaded.status == EngagementStatus.FRAMING

        loaded.link_decision_analysis(uuid.uuid4())
        await repo.save(loaded)

        reloaded = await repo.get(engagement.id, tenant_id)
        assert reloaded is not None
        assert reloaded.status == EngagementStatus.QUANT_ANALYSIS

    async def test_delete_all_for_tenant_removes_only_that_tenant(self, db_session, tenant_id):
        from sdie.shared_kernel.domain.value_objects import TenantId
        from sdie.shared_kernel.infrastructure.database import set_tenant_context

        repo = SqlAlchemyEngagementRepository(db_session)

        await set_tenant_context(db_session, tenant_id.value)
        mine = Engagement.create(tenant_id=tenant_id, title="Mine")
        await repo.save(mine)

        other_tenant = TenantId(uuid.uuid4())
        await set_tenant_context(db_session, other_tenant.value)
        theirs = Engagement.create(tenant_id=other_tenant, title="Theirs")
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
        repo = SqlAlchemyEngagementRepository(tenant_scoped_session)
        deleted_count = await repo.delete_all_for_tenant(tenant_id)
        assert deleted_count == 0
