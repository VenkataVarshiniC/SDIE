from decimal import Decimal

from sdie.financial_modeling.domain.entities import CashFlow, CashFlowModel
from sdie.financial_modeling.domain.services import (
    internal_rate_of_return,
    net_present_value,
    payback_period,
)
from sdie.financial_modeling.infrastructure.repository import SqlAlchemyCashFlowModelRepository
from sdie.shared_kernel.domain.value_objects import Money, Percentage
from tests.integration.conftest import requires_db


@requires_db
class TestCashFlowModelRepository:
    async def test_save_and_get_round_trips_full_aggregate(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyCashFlowModelRepository(tenant_scoped_session)
        discount_rate = Percentage.from_percent(Decimal("9"))
        cash_flows = [
            CashFlow(0, Money(Decimal("-1000"), "USD")),
            CashFlow(1, Money(Decimal("1200"), "USD")),
        ]

        model = CashFlowModel.create(
            tenant_id=tenant_id, project_name="Integration test project", discount_rate=discount_rate
        )
        npv = net_present_value(cash_flows, discount_rate)
        irr = internal_rate_of_return(cash_flows)
        payback = payback_period(cash_flows)
        model.attach_evaluation(cash_flows=cash_flows, npv=npv, irr=irr, payback_period=payback)

        await repo.save(model)
        loaded = await repo.get(model.id, tenant_id)

        assert loaded is not None
        assert loaded.project_name == "Integration test project"
        assert loaded.npv is not None
        assert loaded.npv.amount == npv.amount
        assert len(loaded.cash_flows) == 2
        assert loaded.cash_flows[0].amount.amount == Decimal("-1000.00")

    async def test_list_for_tenant_only_returns_own_tenant(
        self, tenant_scoped_session, tenant_id
    ):
        repo = SqlAlchemyCashFlowModelRepository(tenant_scoped_session)
        discount_rate = Percentage.from_percent(Decimal("5"))
        cash_flows = [CashFlow(0, Money(Decimal("-500"), "USD")), CashFlow(1, Money(Decimal("600"), "USD"))]

        model = CashFlowModel.create(tenant_id=tenant_id, project_name="Only mine", discount_rate=discount_rate)
        npv = net_present_value(cash_flows, discount_rate)
        model.attach_evaluation(cash_flows=cash_flows, npv=npv, irr=None, payback_period=None)
        await repo.save(model)

        results = await repo.list_for_tenant(tenant_id)
        assert any(m.project_name == "Only mine" for m in results)

    async def test_get_returns_none_for_unknown_id(self, tenant_scoped_session, tenant_id):
        import uuid

        repo = SqlAlchemyCashFlowModelRepository(tenant_scoped_session)
        result = await repo.get(uuid.uuid4(), tenant_id)
        assert result is None
