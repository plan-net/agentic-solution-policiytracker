"""
PDF Handler for Bundestag Drucksache documents.

This module handles downloading, extracting, and converting PDF documents
from the Bundestag API into structured markdown format.
"""

import asyncio
import io
import ssl
from datetime import datetime

import aiohttp
import structlog
from pypdf import PdfReader

from .storage_manager import DrucksacheStorageManager

logger = structlog.get_logger(__name__)


class DrucksachePDFHandler:
    """
    Handles PDF operations for Bundestag Drucksache documents.

    This class provides functionality to:
    - Download PDFs from Bundestag API with SSL bypass
    - Extract text content page-by-page
    - Generate structured markdown output
    """

    def __init__(self, storage_manager: DrucksacheStorageManager):
        """
        Initialize the PDF handler.

        Args:
            storage_manager: Storage manager for saving/loading documents
        """
        self.storage_manager = storage_manager
        self.logger = logger.bind(component="DrucksachePDFHandler")

        # Create SSL context that bypasses certificate verification
        # Required for Bundestag API
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def download_pdf(
        self, pdf_url: str, max_retries: int = 3, initial_delay: float = 1.0
    ) -> bytes:
        """
        Download PDF from URL with retry logic and exponential backoff.

        Args:
            pdf_url: URL of the PDF to download
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds for exponential backoff (default: 1.0)

        Returns:
            PDF content as bytes

        Raises:
            aiohttp.ClientError: If download fails after all retries
            ValueError: If URL is invalid or response is not a PDF
        """
        if not pdf_url or not pdf_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid PDF URL: {pdf_url}")

        self.logger.info("Starting PDF download", pdf_url=pdf_url, max_retries=max_retries)

        last_error = None
        delay = initial_delay

        for attempt in range(1, max_retries + 1):
            try:
                connector = aiohttp.TCPConnector(ssl=self.ssl_context)
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout

                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    self.logger.debug(
                        "Download attempt",
                        attempt=attempt,
                        max_retries=max_retries,
                        pdf_url=pdf_url,
                    )

                    async with session.get(pdf_url) as response:
                        response.raise_for_status()

                        # Verify content type
                        content_type = response.headers.get("Content-Type", "")
                        if "application/pdf" not in content_type.lower():
                            self.logger.warning(
                                "Unexpected content type",
                                content_type=content_type,
                                pdf_url=pdf_url,
                            )

                        pdf_bytes = await response.read()

                        # Verify we got actual content
                        if len(pdf_bytes) == 0:
                            raise ValueError("Downloaded PDF is empty")

                        # Basic PDF validation - check magic number
                        if not pdf_bytes.startswith(b"%PDF"):
                            raise ValueError("Downloaded content is not a valid PDF")

                        self.logger.info(
                            "PDF downloaded successfully",
                            pdf_url=pdf_url,
                            size_bytes=len(pdf_bytes),
                            attempt=attempt,
                        )

                        return pdf_bytes

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                last_error = e
                self.logger.warning(
                    "PDF download attempt failed",
                    attempt=attempt,
                    max_retries=max_retries,
                    pdf_url=pdf_url,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                # Don't sleep after the last attempt
                if attempt < max_retries:
                    self.logger.debug(
                        "Retrying after delay", delay_seconds=delay, next_attempt=attempt + 1
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries exhausted
        self.logger.error(
            "PDF download failed after all retries",
            pdf_url=pdf_url,
            max_retries=max_retries,
            last_error=str(last_error),
        )
        raise last_error

    def extract_pages_from_pdf(self, pdf_bytes: bytes) -> list[dict]:
        """
        Extract text content from PDF page-by-page.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            List of dictionaries containing page information:
            [{
                "page_number": 1,
                "page_text": "extracted text...",
                "char_count": 1234,
                "has_content": True
            }, ...]

        Raises:
            ValueError: If PDF is malformed or cannot be parsed
            Exception: For other PDF processing errors
        """
        self.logger.info("Starting PDF text extraction", pdf_size_bytes=len(pdf_bytes))

        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)

            page_count = len(reader.pages)
            self.logger.info("PDF loaded", page_count=page_count)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            pages = []

            for page_num in range(page_count):
                try:
                    page = reader.pages[page_num]
                    page_text = page.extract_text()

                    # Clean up the text
                    if page_text:
                        page_text = page_text.strip()
                    else:
                        page_text = ""

                    char_count = len(page_text)
                    has_content = char_count > 0

                    page_info = {
                        "page_number": page_num + 1,  # 1-indexed for humans
                        "page_text": page_text,
                        "char_count": char_count,
                        "has_content": has_content,
                    }

                    pages.append(page_info)

                    self.logger.debug(
                        "Page extracted",
                        page_number=page_num + 1,
                        char_count=char_count,
                        has_content=has_content,
                    )

                except Exception as e:
                    self.logger.error(
                        "Error extracting page",
                        page_number=page_num + 1,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # Add empty page entry to maintain page numbering
                    pages.append(
                        {
                            "page_number": page_num + 1,
                            "page_text": "",
                            "char_count": 0,
                            "has_content": False,
                            "error": str(e),
                        }
                    )

            total_chars = sum(p["char_count"] for p in pages)
            pages_with_content = sum(1 for p in pages if p["has_content"])

            self.logger.info(
                "PDF text extraction complete",
                page_count=page_count,
                pages_with_content=pages_with_content,
                total_characters=total_chars,
            )

            return pages

        except Exception as e:
            self.logger.error(
                "PDF extraction failed",
                error=str(e),
                error_type=type(e).__name__,
                pdf_size_bytes=len(pdf_bytes),
            )

            if "EOF marker not found" in str(e) or "Invalid PDF" in str(e):
                raise ValueError(f"Malformed PDF: {str(e)}")

            raise

    def generate_markdown(self, drucksache_nummer: str, wahlperiode: int, pages: list[dict]) -> str:
        """
        Generate markdown document with frontmatter and page headers.

        Args:
            drucksache_nummer: Drucksache number (e.g., "20/1234")
            wahlperiode: Electoral period number
            pages: List of page dictionaries from extract_pages_from_pdf

        Returns:
            Formatted markdown string with YAML frontmatter
        """
        self.logger.info(
            "Generating markdown",
            drucksache_nummer=drucksache_nummer,
            wahlperiode=wahlperiode,
            page_count=len(pages),
        )

        # Get current timestamp
        extraction_date = datetime.utcnow().isoformat()

        # Count pages with actual content
        pages_with_content = sum(1 for p in pages if p.get("has_content", False))
        total_chars = sum(p.get("char_count", 0) for p in pages)

        # Build markdown document
        markdown_lines = []

        # Add YAML frontmatter
        markdown_lines.extend(
            [
                "---",
                f"drucksache_nummer: {drucksache_nummer}",
                f"wahlperiode: {wahlperiode}",
                f"page_count: {len(pages)}",
                f"pages_with_content: {pages_with_content}",
                f"total_characters: {total_chars}",
                f"extraction_date: {extraction_date}",
                "---",
                "",
            ]
        )

        # Add document title
        markdown_lines.extend([f"# Drucksache {drucksache_nummer}", ""])

        # Add each page
        for page_info in pages:
            page_num = page_info["page_number"]
            page_text = page_info["page_text"]
            has_content = page_info.get("has_content", False)

            # Page header
            markdown_lines.extend([f"## Page {page_num}", ""])

            # Page content or note if empty
            if has_content and page_text:
                markdown_lines.extend([page_text, ""])
            elif "error" in page_info:
                markdown_lines.extend([f"*[Error extracting page: {page_info['error']}]*", ""])
            else:
                markdown_lines.extend(["*[No text content on this page]*", ""])

            # Add separator between pages (except after last page)
            if page_num < len(pages):
                markdown_lines.extend(["---", ""])

        markdown_content = "\n".join(markdown_lines)

        self.logger.info(
            "Markdown generation complete",
            drucksache_nummer=drucksache_nummer,
            page_count=len(pages),
            markdown_length=len(markdown_content),
        )

        return markdown_content

    async def process_pdf(self, pdf_url: str, drucksache_nummer: str, wahlperiode: int) -> dict:
        """
        Complete PDF processing pipeline: download, extract, and generate markdown.

        Args:
            pdf_url: URL of the PDF to process
            drucksache_nummer: Drucksache number (e.g., "20/1234")
            wahlperiode: Electoral period number

        Returns:
            Dictionary containing:
            {
                "drucksache_nummer": str,
                "wahlperiode": int,
                "pdf_url": str,
                "page_count": int,
                "pages_with_content": int,
                "total_characters": int,
                "markdown_content": str,
                "extraction_date": str
            }

        Raises:
            Exception: If any step of the pipeline fails
        """
        self.logger.info(
            "Starting PDF processing pipeline",
            pdf_url=pdf_url,
            drucksache_nummer=drucksache_nummer,
            wahlperiode=wahlperiode,
        )

        try:
            # Step 1: Download PDF
            pdf_bytes = await self.download_pdf(pdf_url)

            # Step 2: Extract pages
            pages = self.extract_pages_from_pdf(pdf_bytes)

            # Step 3: Generate markdown
            markdown_content = self.generate_markdown(
                drucksache_nummer=drucksache_nummer, wahlperiode=wahlperiode, pages=pages
            )

            # Compile results
            pages_with_content = sum(1 for p in pages if p.get("has_content", False))
            total_chars = sum(p.get("char_count", 0) for p in pages)

            result = {
                "drucksache_nummer": drucksache_nummer,
                "wahlperiode": wahlperiode,
                "pdf_url": pdf_url,
                "page_count": len(pages),
                "pages_with_content": pages_with_content,
                "total_characters": total_chars,
                "markdown_content": markdown_content,
                "extraction_date": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                "PDF processing pipeline complete",
                drucksache_nummer=drucksache_nummer,
                page_count=len(pages),
                pages_with_content=pages_with_content,
            )

            return result

        except Exception as e:
            self.logger.error(
                "PDF processing pipeline failed",
                pdf_url=pdf_url,
                drucksache_nummer=drucksache_nummer,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
