import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Optional

import structlog

from src.config import settings
from src.integrations.azure_storage import AzureStorageClient
from src.models.content import ProcessedContent
from src.processors.document_reader import DocumentReader
from src.utils.exceptions import DocumentProcessingError

logger = structlog.get_logger()


class ContentProcessor:
    """Process and normalize document content with Azure Storage caching."""

    def __init__(self, use_azure: bool = None):
        self.reader = DocumentReader()
        self.use_azure = (
            use_azure if use_azure is not None else getattr(settings, "USE_AZURE_STORAGE", False)
        )
        self.azure_client = AzureStorageClient() if self.use_azure else None
        self.cache_enabled = True  # Enable caching by default

    async def process_document(
        self, file_path: str, doc_id: str, job_id: Optional[str] = None
    ) -> ProcessedContent:
        """Process a document file into structured content with caching."""
        try:
            logger.debug("Processing document", file_path=file_path, doc_id=doc_id)

            # Check cache first if enabled
            if self.cache_enabled:
                cached_content = await self._get_cached_content(file_path, doc_id)
                if cached_content:
                    logger.debug("Retrieved document from cache", doc_id=doc_id)
                    return cached_content

            # Read document (from Azure Storage or local filesystem)
            raw_text, metadata = await self.reader.read_document(
                file_path, use_azure=self.use_azure
            )

            # Normalize and clean text
            cleaned_text = self._clean_text(raw_text)

            # Extract sections if possible
            sections = self._extract_sections(cleaned_text)

            # Calculate word count
            word_count = len(cleaned_text.split()) if cleaned_text else 0

            # Detect language (simple heuristic)
            language = self._detect_language(cleaned_text)

            # Create processed content
            processed_content = ProcessedContent(
                id=doc_id,
                raw_text=cleaned_text,
                metadata=metadata,
                processing_timestamp=datetime.now(),
                word_count=word_count,
                language=language,
                sections=sections,
                extraction_errors=[],
            )

            # Cache processed content if enabled
            if self.cache_enabled:
                await self._cache_content(file_path, doc_id, processed_content, job_id)

            logger.debug(
                "Document processed successfully",
                doc_id=doc_id,
                word_count=word_count,
                sections=len(sections),
            )

            return processed_content

        except DocumentProcessingError:
            raise
        except Exception as e:
            raise DocumentProcessingError(file_path, f"Content processing failed: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Normalize unicode characters
        text = unicodedata.normalize("NFKD", text)

        # Remove null bytes and other control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize whitespace
        text = re.sub(r"\r\n", "\n", text)  # Windows line endings
        text = re.sub(r"\r", "\n", text)  # Mac line endings
        text = re.sub(r"\n{3,}", "\n\n", text)  # Multiple line breaks
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces/tabs

        # Remove excessive spaces at line starts/ends
        lines = text.split("\n")
        lines = [line.strip() for line in lines]
        text = "\n".join(lines)

        # Remove excessive whitespace at start/end
        text = text.strip()

        return text

    def _extract_sections(self, text: str) -> list[dict[str, str]]:
        """Extract document sections based on headers and structure."""
        sections = []

        if not text:
            return sections

        lines = text.split("\n")
        current_section = {"title": "Introduction", "content": []}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect headers (various patterns)
            header_match = None

            # Markdown headers
            if line.startswith("#"):
                header_match = re.match(r"^#+\s*(.+)$", line)

            # Numbered sections
            elif re.match(r"^\d+\.?\s+[A-Z]", line):
                header_match = re.match(r"^\d+\.?\s+(.+)$", line)

            # All caps headers (short lines)
            elif line.isupper() and len(line) < 80 and len(line.split()) < 10:
                header_match = type("Match", (), {"group": lambda self, n: line})()

            # Title case headers
            elif (
                line.istitle()
                and len(line) < 100
                and not any(p in line.lower() for p in [".", ",", ";", ":", "(", ")"])
            ):
                header_match = type("Match", (), {"group": lambda self, n: line})()

            if header_match:
                # Save previous section
                if current_section["content"]:
                    sections.append(
                        {
                            "title": current_section["title"],
                            "content": "\n".join(current_section["content"]),
                        }
                    )

                # Start new section
                current_section = {
                    "title": header_match.group(1) if hasattr(header_match, "group") else line,
                    "content": [],
                }
            else:
                current_section["content"].append(line)

        # Add final section
        if current_section["content"]:
            sections.append(
                {
                    "title": current_section["title"],
                    "content": "\n".join(current_section["content"]),
                }
            )

        return sections

    def _detect_language(self, text: str) -> str:
        """Simple language detection (default to English)."""
        if not text:
            return "en"

        # Simple heuristic based on common words
        english_indicators = [
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        ]

        german_indicators = [
            "der",
            "die",
            "das",
            "und",
            "oder",
            "aber",
            "in",
            "an",
            "zu",
            "für",
            "von",
            "mit",
        ]

        french_indicators = [
            "le",
            "la",
            "les",
            "et",
            "ou",
            "mais",
            "dans",
            "sur",
            "à",
            "pour",
            "de",
            "avec",
        ]

        # Count indicators in first 1000 words
        words = text.lower().split()[:1000]
        word_set = set(words)

        english_score = sum(1 for indicator in english_indicators if indicator in word_set)
        german_score = sum(1 for indicator in german_indicators if indicator in word_set)
        french_score = sum(1 for indicator in french_indicators if indicator in word_set)

        if german_score > english_score and german_score > french_score:
            return "de"
        elif french_score > english_score and french_score > german_score:
            return "fr"
        else:
            return "en"  # Default to English

    def extract_metadata_keywords(self, text: str) -> list[str]:
        """Extract potential keywords from text."""
        if not text:
            return []

        # Extract capitalized words (potential entities)
        capitalized_words = re.findall(r"\b[A-Z][a-z]+\b", text)

        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]+)"', text)

        # Extract acronyms
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)

        # Combine and deduplicate
        keywords = list(set(capitalized_words + quoted_phrases + acronyms))

        # Filter out common words
        common_words = {
            "The",
            "This",
            "That",
            "They",
            "There",
            "These",
            "Those",
            "When",
            "Where",
            "What",
            "Who",
            "Why",
            "How",
        }
        keywords = [kw for kw in keywords if kw not in common_words]

        return keywords[:20]  # Limit to 20 keywords

    def _generate_cache_key(self, file_path: str, doc_id: str) -> str:
        """Generate a unique cache key for a document."""
        # Create a hash from file path and doc_id
        content = f"{file_path}:{doc_id}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _get_cached_content(self, file_path: str, doc_id: str) -> Optional[ProcessedContent]:
        """Retrieve cached processed content."""
        if not self.use_azure or not self.azure_client:
            return None

        try:
            cache_key = self._generate_cache_key(file_path, doc_id)
            blob_name = f"processed/{cache_key}.json"

            # Download cached content from Azure Storage
            cached_data = await self.azure_client.download_json("cache", blob_name)
            if not cached_data:
                return None

            # Reconstruct ProcessedContent object
            # Convert ISO datetime strings back to datetime objects
            if "processing_timestamp" in cached_data:
                cached_data["processing_timestamp"] = datetime.fromisoformat(
                    cached_data["processing_timestamp"]
                )

            # Reconstruct metadata object
            if "metadata" in cached_data:
                metadata_dict = cached_data["metadata"]
                if "created_at" in metadata_dict:
                    metadata_dict["created_at"] = datetime.fromisoformat(
                        metadata_dict["created_at"]
                    )
                if "modified_at" in metadata_dict:
                    metadata_dict["modified_at"] = datetime.fromisoformat(
                        metadata_dict["modified_at"]
                    )

            return ProcessedContent(**cached_data)

        except Exception as e:
            logger.warning(
                "Failed to retrieve cached content",
                file_path=file_path,
                doc_id=doc_id,
                error=str(e),
            )
            return None

    async def _cache_content(
        self, file_path: str, doc_id: str, content: ProcessedContent, job_id: Optional[str] = None
    ) -> bool:
        """Cache processed content for future use."""
        if not self.use_azure or not self.azure_client:
            return False

        try:
            cache_key = self._generate_cache_key(file_path, doc_id)
            blob_name = f"processed/{cache_key}.json"

            # Convert ProcessedContent to dict for JSON serialization
            content_dict = content.dict()

            # Convert datetime objects to ISO strings for JSON serialization
            if "processing_timestamp" in content_dict:
                content_dict["processing_timestamp"] = content_dict[
                    "processing_timestamp"
                ].isoformat()

            if "metadata" in content_dict and content_dict["metadata"]:
                metadata = content_dict["metadata"]
                if "created_at" in metadata:
                    metadata["created_at"] = metadata["created_at"].isoformat()
                if "modified_at" in metadata:
                    metadata["modified_at"] = metadata["modified_at"].isoformat()

            # Upload to Azure Storage cache
            metadata = {
                "file_path": file_path,
                "doc_id": doc_id,
                "cached_at": datetime.now().isoformat(),
                "word_count": str(content.word_count),
                "language": content.language,
            }

            if job_id:
                metadata["job_id"] = job_id

            success = await self.azure_client.upload_json(
                "cache", blob_name, content_dict, metadata=metadata
            )

            if success:
                logger.debug(
                    "Cached processed content",
                    file_path=file_path,
                    doc_id=doc_id,
                    cache_key=cache_key,
                )

            return success

        except Exception as e:
            logger.warning(
                "Failed to cache processed content",
                file_path=file_path,
                doc_id=doc_id,
                error=str(e),
            )
            return False

    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """Clear cached content, optionally with a specific prefix."""
        if not self.use_azure or not self.azure_client:
            return 0

        try:
            # List all cached blobs
            blob_prefix = f"processed/{prefix}" if prefix else "processed/"
            blobs = await self.azure_client.list_blobs("cache", prefix=blob_prefix)

            deleted_count = 0
            for blob in blobs:
                try:
                    await self.azure_client.delete_blob("cache", blob.name)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        "Failed to delete cached blob", blob_name=blob.name, error=str(e)
                    )

            logger.info("Cleared cached content", count=deleted_count, prefix=prefix)
            return deleted_count

        except Exception as e:
            logger.error("Failed to clear cache", prefix=prefix, error=str(e))
            return 0
