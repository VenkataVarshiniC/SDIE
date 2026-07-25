import io

import pytest
from reportlab.pdfgen import canvas

from sdie.evidence_research.domain.entities import EvidenceResearchError
from sdie.evidence_research.interface.router import _extract_pdf_text


def _make_pdf_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(72, 720, text)
    c.save()
    return buffer.getvalue()


class TestExtractPdfText:
    def test_extracts_real_text_from_a_generated_pdf(self):
        pdf_bytes = _make_pdf_bytes("Acquisitions saw 23 percent faster time-to-revenue.")
        text = _extract_pdf_text(pdf_bytes)
        assert "Acquisitions saw 23 percent faster time-to-revenue." in text

    def test_raises_on_garbage_bytes(self):
        with pytest.raises(EvidenceResearchError):
            _extract_pdf_text(b"this is not a pdf file at all")

    def test_raises_on_empty_page_pdf(self):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.showPage()
        c.save()
        with pytest.raises(EvidenceResearchError):
            _extract_pdf_text(buffer.getvalue())
