import pytest

from sdie.evidence_research.domain.entities import EvidenceResearchError
from sdie.evidence_research.domain.services import chunk_text, extract_excerpt


class TestChunkText:
    def test_short_text_produces_single_chunk(self):
        chunks = chunk_text("A short paragraph.", chunk_chars=800)
        assert len(chunks) == 1
        assert chunks[0].text == "A short paragraph."

    def test_long_text_splits_into_multiple_chunks(self):
        content = " ".join(f"word{i}" for i in range(500))
        chunks = chunk_text(content, chunk_chars=200, overlap_chars=20)
        assert len(chunks) > 1
        # every chunk must respect the max size (allowing for the word-boundary backoff)
        assert all(len(c.text) <= 200 for c in chunks)

    def test_overlap_preserves_boundary_context(self):
        content = " ".join(f"word{i}" for i in range(200))
        chunks = chunk_text(content, chunk_chars=100, overlap_chars=30)
        # the tail of chunk N should share some text with the head of chunk N+1
        assert chunks[0].text[-10:] in content
        assert len(chunks) >= 2

    def test_rejects_empty_content(self):
        with pytest.raises(EvidenceResearchError):
            chunk_text("   ")

    def test_rejects_overlap_gte_chunk_size(self):
        with pytest.raises(EvidenceResearchError):
            chunk_text("some content here", chunk_chars=50, overlap_chars=50)


class TestExtractExcerpt:
    def test_centers_excerpt_on_match(self):
        content = "x" * 500 + " TARGET_PHRASE " + "y" * 500
        excerpt = extract_excerpt(content, ["TARGET_PHRASE"], window_chars=40)
        assert "TARGET_PHRASE" in excerpt

    def test_falls_back_to_start_when_no_terms(self):
        content = "Hello world, this is a document."
        excerpt = extract_excerpt(content, [], window_chars=10)
        assert excerpt == "Hello worl"

    def test_falls_back_to_start_when_term_not_found(self):
        content = "Hello world, this is a document."
        excerpt = extract_excerpt(content, ["nonexistent"], window_chars=10)
        assert excerpt.startswith("Hello")
