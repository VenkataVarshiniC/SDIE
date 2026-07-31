from uuid import uuid4

from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.workspace.application.ports import EngagementRepository
from sdie.workspace.application.use_cases import DeleteEngagementUseCase
from sdie.workspace.domain.entities import Engagement


class FakeRepository(EngagementRepository):
    def __init__(self, engagements: list[Engagement]):
        self._engagements = {e.id: e for e in engagements}

    async def save(self, engagement):
        self._engagements[engagement.id] = engagement

    async def get(self, engagement_id, tenant_id):
        return self._engagements.get(engagement_id)

    async def list_for_tenant(self, tenant_id):
        return list(self._engagements.values())

    async def delete_all_for_tenant(self, tenant_id):
        count = len(self._engagements)
        self._engagements = {}
        return count

    async def delete(self, engagement_id, tenant_id):
        if engagement_id in self._engagements:
            del self._engagements[engagement_id]
            return True
        return False


def make_engagement() -> Engagement:
    return Engagement.create(tenant_id=TenantId(uuid4()), title="Market entry decision")


class TestDeleteEngagementUseCase:
    async def test_deletes_the_matching_engagement_and_returns_true(self):
        target = make_engagement()
        other = make_engagement()
        repo = FakeRepository([target, other])
        use_case = DeleteEngagementUseCase(repo)

        deleted = await use_case.execute(target.id, target.tenant_id)

        assert deleted is True
        assert await repo.get(target.id, target.tenant_id) is None
        assert await repo.get(other.id, other.tenant_id) is other

    async def test_returns_false_when_engagement_does_not_exist(self):
        repo = FakeRepository([])
        use_case = DeleteEngagementUseCase(repo)

        deleted = await use_case.execute(uuid4(), TenantId(uuid4()))

        assert deleted is False
