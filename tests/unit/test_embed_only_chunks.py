"""Tests for embed_only chunk limiting fallback strategy."""

import pytest

from src.flows.data_ingestion.document_chunker import HybridDocumentChunker, count_tokens


def _make_document(target_tokens: int, with_headers: bool = True) -> str:
    """Generate a synthetic document with approximately target_tokens tokens."""
    words_per_paragraph = 200
    paragraphs_needed = max(1, target_tokens // words_per_paragraph)

    sections = []
    for i in range(paragraphs_needed):
        if with_headers and i % 5 == 0:
            sections.append(f"\n## Section {i // 5 + 1}\n")
        paragraph = " ".join(f"word{j}" for j in range(words_per_paragraph))
        sections.append(paragraph + "\n")

    doc = "\n".join(sections)
    actual = count_tokens(doc)
    if actual > target_tokens * 1.2:
        encoding = __import__("tiktoken").encoding_for_model("gpt-4")
        tokens = encoding.encode(doc)[:target_tokens]
        doc = encoding.decode(tokens)
    return doc


class TestEmbedOnlyTagging:
    """Tests that the chunker correctly tags overflow chunks as embed_only."""

    def test_embed_only_tags_overflow_chunks(self):
        """Overflow chunks should be tagged as embed_only, first N as full."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,  # Low ceiling to force overflow
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        # All chunks should be returned (none dropped)
        assert len(chunks) > 5

        # First 5 should be full, rest embed_only
        full_chunks = [c for c in chunks if c.get("processing_mode") == "full"]
        embed_only_chunks = [c for c in chunks if c.get("processing_mode") == "embed_only"]

        assert len(full_chunks) == 5
        assert len(embed_only_chunks) == len(chunks) - 5
        assert len(full_chunks) + len(embed_only_chunks) == len(chunks)

    def test_no_tagging_when_under_limit(self):
        """When chunk count is within limit, no processing_mode tags should be set."""
        doc = _make_document(3000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=20,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        assert len(chunks) <= 20
        # No processing_mode tag should be present
        for chunk in chunks:
            assert "processing_mode" not in chunk

    def test_full_chunks_come_first(self):
        """Full-extraction chunks should be the first N chunks (document start)."""
        doc = _make_document(50000)
        max_full = 8
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=max_full,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        # Verify ordering: first max_full are "full", then all "embed_only"
        for i, chunk in enumerate(chunks):
            if i < max_full:
                assert chunk.get("processing_mode") == "full", f"Chunk {i} should be 'full'"
            else:
                assert chunk.get("processing_mode") == "embed_only", f"Chunk {i} should be 'embed_only'"


class TestEmbedOnlyPreservesAllContent:
    """Tests that embed_only strategy preserves all document content."""

    def test_no_chunks_dropped(self):
        """embed_only should return the same number of chunks as unlimited chunking."""
        doc = _make_document(50000)

        # Unlimited chunker (no limit)
        chunker_unlimited = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=0,
        )
        unlimited_chunks = chunker_unlimited.create_chunks(doc)

        # embed_only chunker with same settings but low limit
        chunker_embed = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            adaptive_chunk_size=False,  # Disable adaptive to get same base chunks
            chunk_limit_fallback="embed_only",
        )
        embed_chunks = chunker_embed.create_chunks(doc)

        # Same total chunks
        assert len(embed_chunks) == len(unlimited_chunks)

    def test_content_identical_to_unlimited(self):
        """Content of embed_only chunks should be identical to unlimited chunking."""
        doc = _make_document(20000)

        chunker_unlimited = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=0,
        )
        unlimited_chunks = chunker_unlimited.create_chunks(doc)

        chunker_embed = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=3,
            adaptive_chunk_size=False,
            chunk_limit_fallback="embed_only",
        )
        embed_chunks = chunker_embed.create_chunks(doc)

        # Compare text content
        for i in range(len(unlimited_chunks)):
            assert embed_chunks[i]["text"] == unlimited_chunks[i]["text"]


class TestEmbedOnlyChunkMetadata:
    """Tests for chunk metadata integrity with embed_only strategy."""

    def test_indices_contiguous(self):
        """Chunk indices should be contiguous 0..N-1."""
        doc = _make_document(50000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_token_counts_present(self):
        """All chunks should have token_count metadata."""
        doc = _make_document(30000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        for chunk in chunks:
            assert "token_count" in chunk
            assert chunk["token_count"] > 0

    def test_boundary_type_preserved(self):
        """All chunks should retain their boundary_type metadata."""
        doc = _make_document(30000, with_headers=True)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        for chunk in chunks:
            assert "boundary_type" in chunk


class TestBackwardCompatibility:
    """Ensure existing fallback strategies still work correctly."""

    def test_smart_sample_still_drops_chunks(self):
        """smart_sample should still reduce chunk count (no processing_mode tags)."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample",
        )
        chunks = chunker.create_chunks(doc)

        assert len(chunks) <= 10
        # No processing_mode tag should be present
        for chunk in chunks:
            assert "processing_mode" not in chunk

    def test_truncate_still_drops_chunks(self):
        """truncate should still reduce chunk count (no processing_mode tags)."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="truncate",
        )
        chunks = chunker.create_chunks(doc)

        assert len(chunks) <= 10
        for chunk in chunks:
            assert "processing_mode" not in chunk

    def test_default_fallback_is_smart_sample(self):
        """Default fallback should be smart_sample."""
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
        )
        assert chunker.chunk_limit_fallback == "smart_sample"


class TestEmbedOnlyWithAdaptiveSizing:
    """Tests for embed_only combined with adaptive chunk sizing."""

    def test_adaptive_sizing_runs_before_embed_only_tagging(self):
        """Adaptive sizing should reduce chunks first, then embed_only tags the rest."""
        doc = _make_document(30000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
            max_adaptive_tokens=8000,
            adaptive_chunk_size=True,
            chunk_limit_fallback="embed_only",
        )
        chunks = chunker.create_chunks(doc)

        # Adaptive sizing should have reduced the count enough
        # If still over 10, embed_only tags should be present
        if len(chunks) > 10:
            full_chunks = [c for c in chunks if c.get("processing_mode") == "full"]
            embed_only_chunks = [c for c in chunks if c.get("processing_mode") == "embed_only"]
            assert len(full_chunks) == 10
            assert len(embed_only_chunks) > 0
        else:
            # Adaptive sizing was enough - no tags needed
            for chunk in chunks:
                assert "processing_mode" not in chunk

    def test_chunker_resets_after_embed_only(self):
        """Chunker should reset state after processing a doc with embed_only."""
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=5,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="embed_only",
        )

        # First: large document triggers embed_only
        large_doc = _make_document(50000)
        large_chunks = chunker.create_chunks(large_doc)
        assert len(large_chunks) > 5
        assert any(c.get("processing_mode") == "embed_only" for c in large_chunks)

        # Second: small document should not have processing_mode tags
        small_doc = _make_document(3000)
        small_chunks = chunker.create_chunks(small_doc)
        for chunk in small_chunks:
            assert "processing_mode" not in chunk

        # Chunker max_tokens should be back to original
        assert chunker.max_tokens == 1500


class TestSmartSampleEmbed:
    """Tests for the smart_sample_embed combined strategy."""

    def test_smart_sample_embed_preserves_all_chunks(self):
        """All chunks should be returned (none dropped)."""
        doc = _make_document(80000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=10,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        # All chunks returned
        assert len(chunks) > 10
        # Every chunk has a processing_mode
        for chunk in chunks:
            assert chunk.get("processing_mode") in ("full", "embed_only")

    def test_smart_sample_embed_selects_first_and_last(self):
        """First ~30% and last ~20% should be tagged as full."""
        doc = _make_document(80000)
        max_chunks = 10
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=max_chunks,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        full_chunks = [c for c in chunks if c.get("processing_mode") == "full"]
        embed_chunks = [c for c in chunks if c.get("processing_mode") == "embed_only"]

        # Exactly max_chunks should be full
        assert len(full_chunks) == max_chunks
        assert len(embed_chunks) == len(chunks) - max_chunks

        # First chunks should be full (first ~30%)
        first_count = min(3, max(1, max_chunks // 3))
        for i in range(first_count):
            assert chunks[i]["processing_mode"] == "full", f"Chunk {i} should be full"

        # Last chunks should be full (last ~20%)
        last_count = min(2, max(1, max_chunks // 4))
        for i in range(len(chunks) - last_count, len(chunks)):
            assert chunks[i]["processing_mode"] == "full", f"Chunk {i} should be full"

    def test_smart_sample_embed_full_count_matches_budget(self):
        """Number of full-extraction chunks should equal MAX_CHUNKS_PER_DOCUMENT."""
        doc = _make_document(50000)
        max_chunks = 8
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=max_chunks,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        full_count = sum(1 for c in chunks if c.get("processing_mode") == "full")
        assert full_count == max_chunks

    def test_smart_sample_embed_no_tagging_when_under_limit(self):
        """When under budget, no processing_mode tags should be set."""
        doc = _make_document(3000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=20,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        assert len(chunks) <= 20
        for chunk in chunks:
            assert "processing_mode" not in chunk

    def test_smart_sample_embed_indices_contiguous(self):
        """Chunk indices should remain contiguous."""
        doc = _make_document(50000)
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=8,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_smart_sample_embed_middle_chunks_sampled(self):
        """Some middle chunks should be tagged as full (evenly sampled)."""
        doc = _make_document(80000)
        max_chunks = 10
        chunker = HybridDocumentChunker(
            max_tokens=1500,
            overlap_ratio=0.10,
            max_chunks_per_document=max_chunks,
            max_adaptive_tokens=2000,
            chunk_limit_fallback="smart_sample_embed",
        )
        chunks = chunker.create_chunks(doc)

        first_count = min(3, max(1, max_chunks // 3))
        last_count = min(2, max(1, max_chunks // 4))

        # Check that some middle chunks are full
        middle_full = [
            c for c in chunks[first_count:len(chunks) - last_count]
            if c.get("processing_mode") == "full"
        ]
        middle_budget = max_chunks - first_count - last_count
        assert len(middle_full) == middle_budget
