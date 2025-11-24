#!/usr/bin/env python3
"""Quick test script to verify document preprocessing and chunking."""

from pathlib import Path

from src.flows.data_ingestion.document_chunker import HybridDocumentChunker, count_tokens
from src.flows.data_ingestion.document_preprocessor import preprocess_document


def test_preprocessing():
    """Test link removal from sample document."""
    print("=" * 80)
    print("TEST 1: Document Preprocessing (Link Removal)")
    print("=" * 80)

    # Read the sample document
    doc_path = Path("data/input/news/2025-10/20251027_nettilahja_zalando-lahjakortti.md")

    if not doc_path.exists():
        print(f"❌ Document not found: {doc_path}")
        return False

    with open(doc_path, encoding="utf-8") as f:
        original_content = f.read()

    print(f"\n📄 Original document: {doc_path.name}")
    print(f"   Length: {len(original_content)} characters")
    print(f"   Links (approx): {original_content.count('](')}")
    print(f"   Images (approx): {original_content.count('![')}")

    # Apply preprocessing
    preprocessed = preprocess_document(original_content, enable_link_removal=True)

    print("\n✨ After preprocessing:")
    print(f"   Length: {len(preprocessed)} characters")
    print(f"   Removed: {len(original_content) - len(preprocessed)} characters")
    print(f"   Links remaining: {preprocessed.count('](')}")
    print(f"   Images remaining: {preprocessed.count('![')}")

    # Show sample of cleaned content
    print("\n📝 Sample of cleaned content (first 300 chars):")
    print("-" * 80)
    print(preprocessed[:300])
    print("-" * 80)

    # Verify frontmatter was preserved
    if preprocessed.startswith("---"):
        print("\n✅ Frontmatter preserved")
    else:
        print("\n⚠️  Frontmatter not preserved")

    return True


def test_chunking():
    """Test hybrid chunking on sample document."""
    print("\n" + "=" * 80)
    print("TEST 2: Hybrid Document Chunking")
    print("=" * 80)

    # Read and preprocess the document
    doc_path = Path("data/input/news/2025-10/20251027_nettilahja_zalando-lahjakortti.md")

    with open(doc_path, encoding="utf-8") as f:
        original_content = f.read()

    preprocessed = preprocess_document(original_content, enable_link_removal=True)

    # Count tokens
    token_count = count_tokens(preprocessed)
    print("\n📊 Document stats:")
    print(f"   Total tokens: {token_count:,}")
    print(f"   Characters: {len(preprocessed):,}")

    # Initialize chunker
    print("\n🔧 Initializing hybrid chunker...")
    print("   Max tokens per chunk: 120,000")
    print("   Overlap: 10%")

    chunker = HybridDocumentChunker(max_tokens=120000, overlap_ratio=0.10)
    chunks = chunker.create_chunks(preprocessed)

    print("\n✂️  Chunking results:")
    print(f"   Total chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n   Chunk {i + 1}/{len(chunks)}:")
        print(f"      Tokens: {chunk['token_count']:,}")
        print(f"      Boundary type: {chunk['boundary_type']}")
        print(f"      Has frontmatter: {chunk.get('has_frontmatter', False)}")
        print(f"      Preview: {chunk['text'][:100]}...")

    # Verify all chunks are within limits
    max_chunk_tokens = max(c["token_count"] for c in chunks)
    if max_chunk_tokens <= 120000:
        print(f"\n✅ All chunks within token limit (max: {max_chunk_tokens:,})")
    else:
        print(f"\n❌ Chunk exceeds limit! Max: {max_chunk_tokens:,}")

    return True


def main():
    """Run all tests."""
    print("\n🧪 Testing Document Preprocessing and Chunking")
    print("=" * 80)

    try:
        # Test preprocessing
        if not test_preprocessing():
            return 1

        # Test chunking
        if not test_chunking():
            return 1

        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        print("=" * 80)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
