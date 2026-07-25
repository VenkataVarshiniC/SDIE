from __future__ import annotations

import io
from uuid import UUID

import pdfplumber
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from sdie.evidence_research.application.dto import IngestDocumentCommand, SearchEvidenceQuery
from sdie.evidence_research.application.use_cases import (
    ClearEvidenceHistoryUseCase,
    GetDocumentUseCase,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    SearchEvidenceUseCase,
)
from sdie.evidence_research.domain.entities import EvidenceResearchError
from sdie.evidence_research.infrastructure.repository import SqlAlchemyDocumentRepository
from sdie.evidence_research.interface.schemas import (
    CitationResponse,
    ClearHistoryResponse,
    DocumentDetailResponse,
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


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise EvidenceResearchError(f"Could not read this PDF: {exc}") from exc

    text = "\n\n".join(p for p in pages_text if p.strip())
    if not text.strip():
        raise EvidenceResearchError(
            "No extractable text found in this PDF — it may be a scanned image without a text "
            "layer, which this platform doesn't OCR."
        )
    return text


@router.post(
    "/documents/upload-pdf", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def ingest_pdf(
    title: str = Form(...),
    source_label: str = Form(...),
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """Extracts text from an uploaded PDF (via pdfplumber) and ingests it
    exactly like a pasted-text document — same use case, same citation
    guarantees downstream. Text extraction only; scanned PDFs without a
    text layer aren't OCR'd."""
    if file.content_type not in ("application/pdf", "application/x-pdf") and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File must be a PDF")

    pdf_bytes = await file.read()

    try:
        content = _extract_pdf_text(pdf_bytes)
    except EvidenceResearchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    use_case = IngestDocumentUseCase(repository, get_event_bus())

    command = IngestDocumentCommand(
        tenant_id=principal.tenant_id, title=title, source_label=source_label, content=content
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


@router.delete("/documents", response_model=ClearHistoryResponse)
async def clear_document_history(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ClearHistoryResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    deleted_count = await ClearEvidenceHistoryUseCase(repository).execute(TenantId(principal.tenant_id))
    await session.commit()
    return ClearHistoryResponse(deleted_count=deleted_count)


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


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DocumentDetailResponse:
    await set_tenant_context(session, principal.tenant_id)
    repository = SqlAlchemyDocumentRepository(session)
    result = await GetDocumentUseCase(repository).execute(document_id, TenantId(principal.tenant_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentDetailResponse(
        document_id=result.document_id,
        title=result.title,
        source_label=result.source_label,
        content=result.content,
        created_at=result.created_at,
    )
