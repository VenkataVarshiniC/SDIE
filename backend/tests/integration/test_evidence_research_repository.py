import uuid

from sdie.evidence_research.domain.entities import Document
from sdie.evidence_research.infrastructure.repository import SqlAlchemyDocumentRepository
from tests.integration.conftest import requires_db


@requires_db
class TestDocumentRepository:
    async def test_save_and_get_round_trips(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDocumentRepository(tenant_scoped_session)
        doc = Document.create(
            tenant_id=tenant_id,
            title="Test report",
            source_label="Internal memo, Q3 2026",
            content="The pricing strategy should account for regional currency volatility.",
        )
        await repo.save(doc)

        loaded = await repo.get(doc.id, tenant_id)
        assert loaded is not None
        assert loaded.title == "Test report"
        assert "currency volatility" in loaded.content

    async def test_search_finds_matching_document_via_generated_tsvector(
        self, tenant_scoped_session, tenant_id
    ):
        """This is the test that actually proves the GENERATED ALWAYS
        column works — a unit test can't touch this, since Postgres itself
        computes search_vector on insert."""
        repo = SqlAlchemyDocumentRepository(tenant_scoped_session)
        doc = Document.create(
            tenant_id=tenant_id,
            title="Cloud market analysis",
            source_label="Gartner 2026",
            content="Acquisition remains the fastest route to market share in enterprise cloud.",
        )
        await repo.save(doc)

        citations = await repo.search(tenant_id, "acquisition market", limit=5)

        assert len(citations) == 1
        assert citations[0].document_id == doc.id
        assert citations[0].relevance_score > 0

    async def test_search_respects_tenant_isolation(self, db_session, tenant_id):
        from sdie.shared_kernel.domain.value_objects import TenantId
        from sdie.shared_kernel.infrastructure.database import set_tenant_context

        other_tenant = TenantId(uuid.uuid4())
        repo = SqlAlchemyDocumentRepository(db_session)

        await set_tenant_context(db_session, other_tenant.value)
        other_doc = Document.create(
            tenant_id=other_tenant,
            title="Other tenant's document",
            source_label="Confidential",
            content="This mentions acquisition strategy too.",
        )
        await repo.save(other_doc)

        # Switch session to our tenant and confirm we can't see the other tenant's document
        await set_tenant_context(db_session, tenant_id.value)
        citations = await repo.search(tenant_id, "acquisition", limit=5)
        assert all(c.document_id != other_doc.id for c in citations)

    async def test_search_returns_empty_for_no_match(self, tenant_scoped_session, tenant_id):
        repo = SqlAlchemyDocumentRepository(tenant_scoped_session)
        doc = Document.create(
            tenant_id=tenant_id,
            title="Unrelated report",
            source_label="Internal",
            content="This document discusses employee onboarding procedures.",
        )
        await repo.save(doc)

        citations = await repo.search(tenant_id, "quantum computing blockchain", limit=5)
        assert citations == []
