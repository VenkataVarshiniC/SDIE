from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.evidence_research.application.dto import IngestDocumentCommand, SearchEvidenceQuery
from sdie.evidence_research.application.use_cases import (
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    SearchEvidenceUseCase,
)
from sdie.evidence_research.domain.entities import EvidenceResearchError
from sdie.evidence_research.infrastructure.repository import SqlAlchemyDocumentRepository
from sdie.evidence_research.interface.schemas import (
    CitationResponse,
    DocumentResponse,
    IngestDocumentRequest,
    SearchEvidenceRequest,
)
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.auth import Principal, get_current_principal
from sdie.shared_kernel.infrastructure.database import get_session, set_tenant_context
from sdie.shared_kernel.infrastructure.event_bus import get_event_bus

router = APIRouter(prefix="/evidence-research", tags=["evidence-research"])


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: IngestDocumentRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    use_case = IngestDocumentUseCase(repository, get_event_bus())

    command = IngestDocumentCommand(
        tenant_id=principal.tenant_id,
        title=request.title,
        source_label=request.source_label,
        content=request.content,
    )

    try:
        result = await use_case.execute(command)
        await session.commit()
    except EvidenceResearchError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return DocumentResponse(
        document_id=result.document_id,
        title=result.title,
        source_label=result.source_label,
        created_at=result.created_at,
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    results = await ListDocumentsUseCase(repository).execute(TenantId(principal.tenant_id))
    return [
        DocumentResponse(
            document_id=r.document_id, title=r.title, source_label=r.source_label, created_at=r.created_at
        )
        for r in results
    ]


@router.post("/search", response_model=list[CitationResponse])
async def search_evidence(
    request: SearchEvidenceRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[CitationResponse]:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    use_case = SearchEvidenceUseCase(repository)

    query = SearchEvidenceQuery(tenant_id=principal.tenant_id, query=request.query, limit=request.limit)
    citations = await use_case.execute(query)

    return [
        CitationResponse(
            document_id=c.document_id,
            document_title=c.document_title,
            source_label=c.source_label,
            excerpt=c.excerpt,
            relevance_score=c.relevance_score,
        )
        for c in citations
    ]
