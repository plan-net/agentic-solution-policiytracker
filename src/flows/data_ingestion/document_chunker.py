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

# Default configuration (can be overridden)
DEFAULT_MAX_TOKENS = 120000  # Safety margin below 128K limit
DEFAULT_OVERLAP_RATIO = 0.10  # 10% overlap
MIN_CHUNK_TOKENS = 1000  # Minimum viable chunk size


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
        self, max_tokens: int = DEFAULT_MAX_TOKENS, overlap_ratio: float = DEFAULT_OVERLAP_RATIO
    ):
        """
        Initialize chunker with configuration.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_ratio: Overlap between chunks as ratio (0.1 = 10%)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = int(max_tokens * overlap_ratio)

        logger.info(
            "Initialized hybrid chunker",
            max_tokens=max_tokens,
            overlap_tokens=self.overlap_tokens,
            overlap_percentage=int(overlap_ratio * 100),
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

        # Character-based estimate for RecursiveCharacterTextSplitter
        # Rough estimate: 4 characters ≈ 1 token
        char_chunk_size = max_tokens * 4
        char_overlap = self.overlap_tokens * 4

        self.paragraph_splitter = RecursiveCharacterTextSplitter(
            chunk_size=char_chunk_size,
            chunk_overlap=char_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=count_tokens,  # Use actual token counting
        )

    def create_chunks(self, content: str) -> list[dict[str, any]]:
        """
        Main chunking pipeline: semantic → paragraph → fixed-size.

        Args:
            content: Full document content

        Returns:
            List of chunk dictionaries with metadata
        """
        # Step 1: Extract and preserve frontmatter
        frontmatter, body = extract_frontmatter(content)

        logger.debug(
            "Starting hybrid chunking",
            has_frontmatter=bool(frontmatter),
            body_length=len(body),
            estimated_tokens=count_tokens(body),
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

        # Step 4: Add metadata
        for i, chunk in enumerate(final_chunks):
            chunk.update(
                {
                    "chunk_index": i,
                    "total_chunks": len(final_chunks),
                    "has_frontmatter": bool(frontmatter),
                    "token_count": count_tokens(chunk["text"]),
                }
            )

        # Step 5: Prepend frontmatter to first chunk only
        if frontmatter and final_chunks:
            final_chunks[0]["text"] = f"---\n{frontmatter}\n---\n\n{final_chunks[0]['text']}"
            final_chunks[0]["token_count"] = count_tokens(final_chunks[0]["text"])
            logger.debug("Added frontmatter to first chunk")

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
