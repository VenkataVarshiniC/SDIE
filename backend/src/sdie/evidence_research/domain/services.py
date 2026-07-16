"""Pure domain logic for evidence handling. Deliberately does NOT include
the search/ranking algorithm itself — full-text ranking (ts_rank) is
inherently a Postgres-native operation, so that lives in the infrastructure
repository, not here. What's testable without a database is chunking and
excerpt extraction, so that's what this module covers.
"""
from __future__ import annotations

from dataclasses import dataclass

from sdie.evidence_research.domain.entities import EvidenceResearchError

_DEFAULT_CHUNK_CHARS = 800
_DEFAULT_OVERLAP_CHARS = 100


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    text: str
    start_char: int
    end_char: int


def chunk_text(
    content: str,
    *,
    chunk_chars: int = _DEFAULT_CHUNK_CHARS,
    overlap_chars: int = _DEFAULT_OVERLAP_CHARS,
) -> list[TextChunk]:
    """Splits on paragraph boundaries where possible, falling back to a
    fixed-width window with overlap so a fact split across a chunk boundary
    isn't lost entirely. Overlap must be smaller than chunk size or the
    window never advances."""
    if chunk_chars <= 0:
        raise EvidenceResearchError("chunk_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= chunk_chars:
        raise EvidenceResearchError("overlap_chars must be >= 0 and < chunk_chars")
    if not content.strip():
        raise EvidenceResearchError("content must not be empty")

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    text_len = len(content)

    while start < text_len:
        end = min(start + chunk_chars, text_len)
        # try not to cut mid-word: back off to the last whitespace boundary
        if end < text_len:
            last_space = content.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunk_str = content[start:end].strip()
        if chunk_str:
            chunks.append(TextChunk(index=index, text=chunk_str, start_char=start, end_char=end))
            index += 1

        if end >= text_len:
            break
        start = end - overlap_chars

    return chunks


def extract_excerpt(content: str, query_terms: list[str], *, window_chars: int = 240) -> str:
    """Given full document content and the terms a search matched on,
    returns a short window of surrounding text centered on the first match
    — this is what gets shown to a reader as the citation excerpt, not the
    whole document or whole chunk."""
    if not query_terms:
        return content[:window_chars].strip()

    lowered = content.lower()
    match_pos = -1
    for term in query_terms:
        pos = lowered.find(term.lower())
        if pos != -1 and (match_pos == -1 or pos < match_pos):
            match_pos = pos

    if match_pos == -1:
        return content[:window_chars].strip()

    half = window_chars // 2
    start = max(0, match_pos - half)
    end = min(len(content), match_pos + half)
    excerpt = content[start:end].strip()
    return ("…" if start > 0 else "") + excerpt + ("…" if end < len(content) else "")
