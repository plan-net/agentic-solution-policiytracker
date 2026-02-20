"""Tests for intelligent chunk limiting in HybridDocumentChunker."""

import pytest

from src.flows.data_ingestion.document_chunker import HybridDocumentChunker, count_tokens


def _make_document(target_tokens: int, with_headers: bool = True) -> str:
    """Generate a synthetic document with approximately target_tokens tokens."""
    # Each word is roughly 1 token; build paragraphs under headers
    words_per_paragraph = 200
    paragraphs_needed = max(1, target_tokens // words_per_paragraph)

    sections = []
    for i in range(paragraphs_needed):
        if with_headers and i % 5 == 0:
            sections.append(f"\n## Section {i // 5 + 1}\n")
        paragraph = " ".join(f"word{j}" for j in range(words_per_paragraph))
        sections.append(paragraph + "\n")

    doc = "\n".join(sections)
    # Trim or pad to approximate target
    actual = count_tokens(doc)
    if actual > target_tokens * 1.2:
        # Truncate to rough target
        encoding = __import__("tiktoken").encoding_for_model("gpt-4")
        tokens = encoding.encode(doc)[:target_tokens]
        doc = encoding.decode(tokens)
    return doc


class TestAdaptiveChunkSizing:
    """Tests for adaptive chunk size calculation."""

    def test_no_limiting_when_under_budget(self):
        """Document that fits within max_chunks should not be modified."""
        # ~3000 tokens at 1500/chunk = ~2 chunks, well under max_chunks=20
        doc = _make_document(3000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=20,
        )
        chunks = chunker.create_chunks(doc)
        assert len(chunks) <= 20
        # No adaptive metadata should be present
        assert not any(c.get("adaptive_chunk_size") for c in chunks)

    def test_adaptive_sizing_increases_chunk_size(self):
        """Large document should get larger chunks to stay within budget."""
        # ~30000 tokens at 1500/chunk = ~22 chunks, over max_chunks=10
        doc = _make_document(30000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
        )
        chunks = chunker.create_chunks(doc)
        assert len(chunks) <= 10
        # Adaptive metadata should be present
        assert any(c.get("adaptive_chunk_size") for c in chunks)

    def test_adaptive_sizing_respects_max_adaptive_tokens(self):
        """Adaptive sizing should not exceed MAX_ADAPTIVE_TOKENS."""
        # Very large doc that would need >8000 tokens/chunk to fit in 5 chunks
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=8000,
        )
        chunks = chunker.create_chunks(doc)
        # May exceed 5 chunks since adaptive is capped at 8000
        # But each chunk should not exceed 8000 tokens (with some tolerance for headers)
        for chunk in chunks:
            assert chunk["token_count"] <= 8500  # small tolerance for header prepending

    def test_disabled_when_max_chunks_zero(self):
        """max_chunks=0 should mean unlimited - no adaptive sizing."""
        doc = _make_document(30000)
        chunker_unlimited = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=0,
        )
        chunks_unlimited = chunker_unlimited.create_chunks(doc)

        chunker_default = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
        )
        chunks_default = chunker_default.create_chunks(doc)

        # Both should produce the same number of chunks
        assert len(chunks_unlimited) == len(chunks_default)
        # No adaptive metadata
        assert not any(c.get("adaptive_chunk_size") for c in chunks_unlimited)


class TestSmartSampling:
    """Tests for smart sampling fallback."""

    def test_smart_sampling_reduces_chunks(self):
        """When adaptive sizing hits ceiling, smart sampling should reduce chunks."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
            max_adaptive_tokens=4000,  # Low ceiling to force sampling
            chunk_limit_fallback="smart_sample",
        )
        chunks = chunker.create_chunks(doc)
        assert len(chunks) <= 10

    def test_smart_sampling_preserves_coverage(self):
        """Smart sampling should keep first, last, and middle chunks."""
        # Create a chunker that will force smart sampling
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=8,
            max_adaptive_tokens=2000,  # Very low ceiling
            chunk_limit_fallback="smart_sample",
        )

        # Generate a large document
        doc = _make_document(50000)
        chunks = chunker.create_chunks(doc)

        assert len(chunks) <= 8
        # Chunk indices should be contiguous 0..N-1
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_truncate_fallback(self):
        """Truncate fallback should keep first N chunks only."""
        doc = _make_document(50000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="truncate",
        )
        chunks = chunker.create_chunks(doc)
        assert len(chunks) <= 5


class TestChunkIndexIntegrity:
    """Tests for chunk index integrity after limiting."""

    def test_indices_contiguous_after_adaptive(self):
        """After adaptive sizing, chunk indices should be 0..N-1."""
        doc = _make_document(30000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
        )
        chunks = chunker.create_chunks(doc)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_indices_contiguous_after_smart_sampling(self):
        """After smart sampling, chunk indices should be 0..N-1."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=8,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample",
        )
        chunks = chunker.create_chunks(doc)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_total_chunks_matches_actual_count(self):
        """total_chunks metadata should match actual chunk list length."""
        doc = _make_document(50000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=12,
        )
        chunks = chunker.create_chunks(doc)
        for chunk in chunks:
            assert chunk["total_chunks"] == len(chunks)


class TestChunkerReuse:
    """Tests that chunker can be reused after adaptive sizing."""

    def test_chunker_resets_after_adaptive(self):
        """After processing a large doc, chunker should reset for the next doc."""
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
        )

        # First: large document triggers adaptive
        large_doc = _make_document(30000)
        large_chunks = chunker.create_chunks(large_doc)
        assert len(large_chunks) <= 10

        # Second: small document should use original chunk size
        small_doc = _make_document(3000)
        small_chunks = chunker.create_chunks(small_doc)
        # Should NOT have adaptive metadata
        assert not any(c.get("adaptive_chunk_size") for c in small_chunks)
        # max_tokens should be back to original
        assert chunker.max_tokens == 1500
