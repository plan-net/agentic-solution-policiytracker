"""
Test that storage only saves markdown files, no JSON metadata files.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

from src.etl.storage.local import LocalStorage


class TestStorageMarkdownOnly:
    """Test that storage saves only markdown files."""
    
    @pytest.mark.asyncio
    async def test_save_document_no_json_metadata(self):
        """Test that saving a document doesn't create JSON metadata files."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize storage with temporary directory
            storage = LocalStorage(base_path=temp_dir)
            
            # Test document content
            content = """---
title: Test Document
url: https://example.com/test
published_date: 2024-03-15T10:00:00Z
author: Test Author
---

# Test Document

This is a test document with metadata in the frontmatter.
"""
            
            # Test metadata (this should NOT create a separate JSON file)
            metadata = {
                "url": "https://example.com/test",
                "source": "example.com",
                "collector_type": "test",
                "published_date": "2024-03-15T10:00:00Z"
            }
            
            # Save document with metadata
            success = await storage.save_document(
                content=content,
                path="test/test-document.md",
                metadata=metadata
            )
            
            assert success, "Document save should succeed"
            
            # Check that markdown file exists
            markdown_path = Path(temp_dir) / "test/test-document.md"
            assert markdown_path.exists(), "Markdown file should exist"
            
            # Check that NO JSON metadata file was created
            json_path = Path(temp_dir) / "test/test-document.md.meta.json"
            assert not json_path.exists(), "JSON metadata file should NOT exist"
            
            # Verify content was saved correctly
            with open(markdown_path, 'r') as f:
                saved_content = f.read()
            
            assert saved_content == content, "Saved content should match original"
    
    @pytest.mark.asyncio
    async def test_list_documents_excludes_json(self):
        """Test that listing documents excludes any JSON files."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(base_path=temp_dir)
            
            # Create test files
            test_files = [
                "article1.md",
                "article2.md", 
                "article1.md.meta.json",  # This shouldn't be listed
                "config.json"  # This shouldn't be listed
            ]
            
            for filename in test_files:
                file_path = Path(temp_dir) / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write("test content")
            
            # List documents
            documents = await storage.list_documents()
            
            # Should only include markdown files
            assert len(documents) == 2, "Should only list markdown files"
            assert "article1.md" in documents
            assert "article2.md" in documents
            
            # Should not include JSON files
            assert "article1.md.meta.json" not in documents
            assert "config.json" not in documents
    
    @pytest.mark.asyncio
    async def test_delete_document_no_json_cleanup(self):
        """Test that deleting a document doesn't try to delete non-existent JSON files."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(base_path=temp_dir)
            
            # Save a document (no JSON should be created)
            await storage.save_document(
                content="# Test\n\nContent here",
                path="test.md",
                metadata={"url": "https://example.com"}
            )
            
            # Verify only markdown exists
            markdown_path = Path(temp_dir) / "test.md"
            json_path = Path(temp_dir) / "test.md.meta.json"
            
            assert markdown_path.exists()
            assert not json_path.exists()
            
            # Delete document (should not error even though JSON doesn't exist)
            success = await storage.delete_document("test.md")
            
            assert success, "Delete should succeed"
            assert not markdown_path.exists(), "Markdown file should be deleted"
    
    def test_storage_documentation_accuracy(self):
        """Test that storage docstring accurately reflects no JSON metadata behavior."""
        
        # Check that the save_document method docstring mentions markdown only
        docstring = LocalStorage.save_document.__doc__
        
        assert "markdown only" in docstring.lower() or "no metadata files" in docstring.lower(), \
            "Docstring should indicate that only markdown files are saved"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])