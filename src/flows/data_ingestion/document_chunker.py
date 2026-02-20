"""
Hybrid document chunking combining semantic boundaries with token limits.

This module implements a three-tier chunking strategy:
1. Semantic chunking by markdown headers (preserves structure)
2. Paragraph-based chunking for oversized sections
3. Fixed-size chunking with overlap as last resort

Ensures all chunks fit within token limits while preserving context.
"""

import re

import structlog
import tiktoken
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = structlog.get_logger()

# Default configuration (aligned with GraphRAGSettings in config.py)
# These values are typically overridden by graphrag_settings.MAX_EPISODE_TOKENS
DEFAULT_MAX_TOKENS = 1500  # Max tokens per chunk (matches GraphRAGSettings.MAX_EPISODE_TOKENS)
DEFAULT_OVERLAP_RATIO = 0.10  # 10% overlap (matches GraphRAGSettings.CHUNK_OVERLAP_PERCENTAGE / 100)
MIN_CHUNK_TOKENS = 50  # Minimum viable chunk size (matches GraphRAGSettings.MIN_CHUNK_TOKENS)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer (default: gpt-4)

    Returns:
        Number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, using character estimate")
        # Fallback: estimate 4 characters per token
        return len(text) // 4


def extract_frontmatter(content: str) -> tuple[str, str]:
    """
    Separate YAML frontmatter from body.

    Args:
        content: Full document content

    Returns:
        Tuple of (frontmatter, body)
    """
    pattern = r"^---\n(.*?)\n---\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return "", content


class HybridDocumentChunker:
    """
    Hybrid chunking strategy for knowledge graph extraction.

    Strategy:
    1. Split by markdown headers (semantic boundaries)
    2. Further split large sections by paragraphs
    3. Final split by fixed size with overlap if still too large

    This ensures:
    - Document structure is preserved when possible
    - All chunks fit within token limits
    - Context is maintained across chunk boundaries
    """

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
        max_chunks_per_document: int = 0,
        adaptive_chunk_size: bool = True,
        max_adaptive_tokens: int = 8000,
        chunk_limit_fallback: str = "smart_sample",
    ):
        """
        Initialize chunker with configuration.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_ratio: Overlap between chunks as ratio (0.1 = 10%)
            max_chunks_per_document: Max chunks allowed per document. 0 = unlimited.
            adaptive_chunk_size: Enable dynamic chunk size increase for large documents.
            max_adaptive_tokens: Ceiling for adaptive chunk size.
            chunk_limit_fallback: Strategy when adaptive sizing still exceeds limit:
                'smart_sample' (keep start/end/sampled middle) or 'truncate' (first N).
        """
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio
        self.overlap_tokens = int(max_tokens * overlap_ratio)
        self.original_max_tokens = max_tokens
        self.max_chunks_per_document = max_chunks_per_document
        self.adaptive_chunk_size = adaptive_chunk_size
        self.max_adaptive_tokens = max_adaptive_tokens
        self.chunk_limit_fallback = chunk_limit_fallback

        logger.info(
            "Initialized hybrid chunker",
            max_tokens=max_tokens,
            overlap_tokens=self.overlap_tokens,
            overlap_percentage=int(overlap_ratio * 100),
            max_chunks_per_document=max_chunks_per_document,
            adaptive_chunk_size=adaptive_chunk_size,
        )

        # LangChain splitters for semantic chunking
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ],
            strip_headers=False,  # Keep headers in content for context
        )

        # Use token-based chunking for consistency
        # When using length_function=count_tokens, chunk_size should be in tokens
        self.paragraph_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,  # In tokens when using count_tokens
            chunk_overlap=self.overlap_tokens,  # In tokens when using count_tokens
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=count_tokens,  # Count tokens for accurate chunking
        )

    def _calculate_adaptive_chunk_size(self, total_tokens: int) -> int:
        """
        Calculate optimal chunk size to fit within MAX_CHUNKS_PER_DOCUMENT.

        If the document would produce too many chunks at the current chunk size,
        increase the chunk size so the estimated chunk count fits the budget.

        Args:
            total_tokens: Total tokens in the document body

        Returns:
            Adjusted max_tokens value (may be same as original if no adjustment needed)
        """
        if self.max_chunks_per_document <= 0:
            return self.max_tokens

        # Estimate chunks at current size (accounting for overlap)
        effective_step = self.max_tokens - self.overlap_tokens
        if effective_step <= 0:
            effective_step = self.max_tokens
        estimated_chunks = max(1, (total_tokens + effective_step - 1) // effective_step)

        if estimated_chunks <= self.max_chunks_per_document:
            return self.max_tokens

        # Calculate new chunk size to fit within budget
        # new_step * max_chunks >= total_tokens
        new_step = (total_tokens + self.max_chunks_per_document - 1) // self.max_chunks_per_document
        new_max_tokens = int(new_step / (1.0 - self.overlap_ratio)) if self.overlap_ratio < 1.0 else new_step

        # Apply ceiling
        new_max_tokens = min(new_max_tokens, self.max_adaptive_tokens)

        logger.info(
            "Adaptive chunk sizing applied",
            original_max_tokens=self.original_max_tokens,
            new_max_tokens=new_max_tokens,
            total_document_tokens=total_tokens,
            estimated_chunks_original=estimated_chunks,
            max_chunks_allowed=self.max_chunks_per_document,
            capped_at_max=new_max_tokens == self.max_adaptive_tokens,
        )

        return new_max_tokens

    def _apply_smart_sampling(self, chunks: list[dict[str, any]]) -> list[dict[str, any]]:
        """
        Select representative chunks when adaptive sizing still exceeds the limit.

        Strategy: Keep first N chunks (document start/context), last M chunks
        (conclusions), and evenly sample from the middle to fill remaining budget.

        Args:
            chunks: Full list of chunks from chunking pipeline

        Returns:
            Reduced list of chunks with preserved coverage
        """
        max_chunks = self.max_chunks_per_document
        total = len(chunks)

        if total <= max_chunks or max_chunks <= 0:
            return chunks

        # Allocation: first ~30%, last ~20%, rest from middle
        first_count = min(3, max(1, max_chunks // 3))
        last_count = min(2, max(1, max_chunks // 4))
        middle_budget = max_chunks - first_count - last_count

        if middle_budget <= 0:
            selected = chunks[:max_chunks]
        else:
            first_chunks = chunks[:first_count]
            last_chunks = chunks[total - last_count:]

            # Evenly sample from middle
            middle_pool = chunks[first_count:total - last_count]

            if len(middle_pool) <= middle_budget:
                middle_selected = middle_pool
            else:
                step = len(middle_pool) / middle_budget
                indices = sorted(set(int(i * step) for i in range(middle_budget)))[:middle_budget]
                middle_selected = [middle_pool[i] for i in indices]

            selected = first_chunks + middle_selected + last_chunks

        logger.warning(
            "Chunk limit applied via smart sampling",
            original_chunks=total,
            selected_chunks=len(selected),
            max_chunks=max_chunks,
            first_kept=first_count,
            last_kept=last_count,
            middle_sampled=len(selected) - first_count - last_count,
            dropped_chunks=total - len(selected),
        )

        return selected

    def _apply_smart_sample_embed(self, chunks: list[dict[str, any]]) -> list[dict[str, any]]:
        """
        Smart sampling with embed-only preservation of non-selected chunks.

        Strategy: Same selection as smart_sample (first ~30%, last ~20%, sampled middle)
        get full extraction. All remaining chunks are tagged as embed_only instead of
        being dropped, preserving all document content for semantic search.

        Args:
            chunks: Full list of chunks from chunking pipeline

        Returns:
            Full list of chunks with processing_mode tags
        """
        max_chunks = self.max_chunks_per_document
        total = len(chunks)

        if total <= max_chunks or max_chunks <= 0:
            return chunks

        # Same allocation logic as smart_sample
        first_count = min(3, max(1, max_chunks // 3))
        last_count = min(2, max(1, max_chunks // 4))
        middle_budget = max_chunks - first_count - last_count

        # Build set of selected indices for full extraction
        if middle_budget <= 0:
            selected_indices = set(range(max_chunks))
        else:
            selected_indices = set(range(first_count))
            selected_indices.update(range(total - last_count, total))

            # Evenly sample from middle
            middle_pool_start = first_count
            middle_pool_end = total - last_count
            middle_pool_size = middle_pool_end - middle_pool_start

            if middle_pool_size <= middle_budget:
                selected_indices.update(range(middle_pool_start, middle_pool_end))
            else:
                step = middle_pool_size / middle_budget
                for i in range(middle_budget):
                    selected_indices.add(middle_pool_start + int(i * step))

        # Tag all chunks
        full_count = 0
        embed_count = 0
        for i, chunk in enumerate(chunks):
            if i in selected_indices:
                chunk["processing_mode"] = "full"
                full_count += 1
            else:
                chunk["processing_mode"] = "embed_only"
                embed_count += 1

        logger.info(
            "Chunk limit: smart_sample_embed applied",
            original_chunks=total,
            full_extraction=full_count,
            embed_only=embed_count,
            max_chunks=max_chunks,
            first_kept=first_count,
            last_kept=last_count,
        )

        return chunks

    def create_chunks(self, content: str) -> list[dict[str, any]]:
        """
        Main chunking pipeline: semantic → paragraph → fixed-size.

        Applies adaptive chunk sizing and chunk limiting when configured.

        Args:
            content: Full document content

        Returns:
            List of chunk dictionaries with metadata
        """
        # Step 1: Extract and preserve frontmatter
        frontmatter, body = extract_frontmatter(content)

        body_tokens = count_tokens(body)

        logger.debug(
            "Starting hybrid chunking",
            has_frontmatter=bool(frontmatter),
            body_length=len(body),
            estimated_tokens=body_tokens,
        )

        # Step 1.5: Apply adaptive chunk sizing if needed
        adaptive_applied = False
        if self.adaptive_chunk_size and self.max_chunks_per_document > 0:
            new_max_tokens = self._calculate_adaptive_chunk_size(body_tokens)
            if new_max_tokens != self.max_tokens:
                adaptive_applied = True
                self.max_tokens = new_max_tokens
                self.overlap_tokens = int(new_max_tokens * self.overlap_ratio)
                # Reinitialize paragraph splitter with new chunk size
                self.paragraph_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=new_max_tokens,
                    chunk_overlap=self.overlap_tokens,
                    separators=["\n\n", "\n", ". ", " ", ""],
                    length_function=count_tokens,
                )

        # Step 2: Initial semantic split by headers
        semantic_chunks = self._split_by_headers(body)
        logger.debug(f"Semantic split produced {len(semantic_chunks)} initial chunk(s)")

        # Step 3: Process each semantic chunk (may split further)
        final_chunks = []
        for i, semantic_chunk in enumerate(semantic_chunks):
            processed = self._process_semantic_chunk(semantic_chunk, i)
            final_chunks.extend(processed)

        logger.info(
            f"Hybrid chunking complete: {len(final_chunks)} final chunk(s)",
            boundary_types=[c["boundary_type"] for c in final_chunks],
        )

        # Step 4: Apply chunk limit fallback if still over budget
        if self.max_chunks_per_document > 0 and len(final_chunks) > self.max_chunks_per_document:
            if self.chunk_limit_fallback == "smart_sample_embed":
                # Smart sample selection with embed-only for non-selected chunks
                final_chunks = self._apply_smart_sample_embed(final_chunks)
            elif self.chunk_limit_fallback == "embed_only":
                # Tag chunks: first N get full extraction, rest get embed-only
                for i, chunk in enumerate(final_chunks):
                    chunk["processing_mode"] = "full" if i < self.max_chunks_per_document else "embed_only"
                logger.info(
                    "Chunk limit: tagging overflow chunks as embed_only",
                    full_extraction=self.max_chunks_per_document,
                    embed_only=len(final_chunks) - self.max_chunks_per_document,
                    total=len(final_chunks),
                )
            elif self.chunk_limit_fallback == "smart_sample":
                final_chunks = self._apply_smart_sampling(final_chunks)
            else:
                logger.warning(
                    "Chunk limit applied via truncation",
                    original_chunks=len(final_chunks),
                    kept_chunks=self.max_chunks_per_document,
                    dropped_chunks=len(final_chunks) - self.max_chunks_per_document,
                )
                final_chunks = final_chunks[:self.max_chunks_per_document]

        # Step 5: Add/re-index metadata
        for i, chunk in enumerate(final_chunks):
            chunk.update(
                {
                    "chunk_index": i,
                    "total_chunks": len(final_chunks),
                    "has_frontmatter": bool(frontmatter),
                    "token_count": count_tokens(chunk["text"]),
                }
            )
            if adaptive_applied:
                chunk["adaptive_chunk_size"] = True
                chunk["original_max_tokens"] = self.original_max_tokens
                chunk["adjusted_max_tokens"] = self.max_tokens

        # Step 6: Prepend frontmatter to first chunk only
        if frontmatter and final_chunks:
            final_chunks[0]["text"] = f"---\n{frontmatter}\n---\n\n{final_chunks[0]['text']}"
            final_chunks[0]["token_count"] = count_tokens(final_chunks[0]["text"])
            logger.debug("Added frontmatter to first chunk")

        # Restore original max_tokens for reuse of this chunker instance
        if adaptive_applied:
            self.max_tokens = self.original_max_tokens
            self.overlap_tokens = int(self.original_max_tokens * self.overlap_ratio)
            self.paragraph_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.original_max_tokens,
                chunk_overlap=self.overlap_tokens,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=count_tokens,
            )

        return final_chunks

    def _split_by_headers(self, body: str) -> list[dict[str, any]]:
        """
        Split document by markdown headers (semantic boundaries).

        Args:
            body: Document body (without frontmatter)

        Returns:
            List of semantic chunks with metadata
        """
        try:
            # Use LangChain's MarkdownHeaderTextSplitter
            docs = self.header_splitter.split_text(body)

            if not docs:
                return [{"text": body, "metadata": {}, "boundary_type": "full_document"}]

            chunks = []
            for doc in docs:
                chunks.append(
                    {"text": doc.page_content, "metadata": doc.metadata, "boundary_type": "header"}
                )

            return chunks

        except Exception as e:
            logger.warning(f"Header splitting failed: {e}, treating as single chunk")
            # Fallback: treat entire body as single chunk
            return [{"text": body, "metadata": {}, "boundary_type": "full_document"}]

    def _process_semantic_chunk(
        self, chunk: dict[str, any], chunk_num: int
    ) -> list[dict[str, any]]:
        """
        Process a semantic chunk with size validation and further splitting if needed.

        Args:
            chunk: Semantic chunk with text and metadata
            chunk_num: Chunk number for logging

        Returns:
            List of processed chunks (may be split further)
        """
        text = chunk["text"]
        token_count = count_tokens(text)

        logger.debug(
            f"Processing semantic chunk {chunk_num}",
            token_count=token_count,
            max_tokens=self.max_tokens,
            boundary_type=chunk["boundary_type"],
        )

        # Case 1: Chunk is within limits - keep as-is
        if token_count <= self.max_tokens:
            logger.debug(f"Chunk {chunk_num} within limits, keeping as-is")
            return [chunk]

        # Case 2: Too large - try paragraph splitting
        logger.debug(
            f"Chunk {chunk_num} exceeds limit ({token_count} tokens), trying paragraph split"
        )
        paragraph_chunks = self._split_by_paragraphs(text, chunk["metadata"])

        # Case 3: If any paragraph chunk still too large - fixed-size split
        final_chunks = []
        for i, para_chunk in enumerate(paragraph_chunks):
            para_tokens = count_tokens(para_chunk["text"])
            if para_tokens <= self.max_tokens:
                final_chunks.append(para_chunk)
            else:
                logger.debug(
                    f"Paragraph chunk {i} still too large ({para_tokens} tokens), using fixed-size split"
                )
                # Last resort: fixed-size splitting
                fixed_chunks = self._fixed_size_split(para_chunk["text"], para_chunk["metadata"])
                final_chunks.extend(fixed_chunks)

        logger.debug(f"Chunk {chunk_num} split into {len(final_chunks)} sub-chunks")
        return final_chunks

    def _split_by_paragraphs(self, text: str, metadata: dict) -> list[dict[str, any]]:
        """
        Split text by paragraph boundaries using RecursiveCharacterTextSplitter.

        Args:
            text: Text to split
            metadata: Metadata to preserve

        Returns:
            List of paragraph-based chunks
        """
        try:
            docs = self.paragraph_splitter.create_documents([text])

            chunks = []
            for doc in docs:
                chunks.append(
                    {"text": doc.page_content, "metadata": metadata, "boundary_type": "paragraph"}
                )

            return chunks

        except Exception as e:
            logger.warning(f"Paragraph splitting failed: {e}, returning as single chunk")
            # Fallback: return as single chunk
            return [{"text": text, "metadata": metadata, "boundary_type": "paragraph_fallback"}]

    def _fixed_size_split(self, text: str, metadata: dict) -> list[dict[str, any]]:
        """
        Last resort: fixed-size splitting with overlap.

        Used when semantic splitting fails to create small enough chunks.
        This guarantees all chunks will fit within token limits.

        Args:
            text: Text to split
            metadata: Metadata to preserve

        Returns:
            List of fixed-size chunks with overlap
        """
        encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = encoding.encode(text)
        total_tokens = len(tokens)

        logger.debug(
            "Fixed-size splitting",
            total_tokens=total_tokens,
            max_tokens=self.max_tokens,
            overlap_tokens=self.overlap_tokens,
        )

        chunks = []
        start = 0

        while start < total_tokens:
            end = min(start + self.max_tokens, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)

            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": metadata,
                    "boundary_type": "fixed_size",
                    "token_range": (start, end),
                }
            )

            start = end - self.overlap_tokens  # Move forward with overlap

        return chunks
