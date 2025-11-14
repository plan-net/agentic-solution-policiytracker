"""
Storage manager for Bundestag Drucksache documents.

Handles file system organization for downloaded PDFs and extracted markdown content
with a structured directory layout by Wahlperiode (electoral period).
"""

from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class DrucksacheStorageManager:
    """
    Manages local file storage for Bundestag Drucksache documents.

    Organizes files in a structured directory hierarchy:
    - PDFs: data/input/bundestag/drucksache/pdf/wahlperiode_{N}/
    - Markdown: data/input/bundestag/drucksache/markdown/wahlperiode_{N}/

    File naming convention: Converts '20/1234' -> '20_1234.pdf' / '20_1234.md'
    """

    def __init__(self, base_dir: str = "data/input/bundestag/drucksache"):
        """
        Initialize storage manager with base directory.

        Args:
            base_dir: Base directory for all drucksache storage (default: data/input/bundestag/drucksache)
        """
        self.base_dir = Path(base_dir)
        self.pdf_dir = self.base_dir / "pdf"
        self.markdown_dir = self.base_dir / "markdown"

        logger.info(
            "Initialized DrucksacheStorageManager",
            base_dir=str(self.base_dir),
            pdf_dir=str(self.pdf_dir),
            markdown_dir=str(self.markdown_dir),
        )

    def get_pdf_path(self, drucksache_nummer: str, wahlperiode: int) -> Path:
        """
        Get the file path where a PDF should be stored.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)

        Returns:
            Path object for the PDF file

        Example:
            >>> manager.get_pdf_path('20/1234', 20)
            Path('data/input/bundestag/drucksache/pdf/wahlperiode_20/20_1234.pdf')
        """
        filename = self._normalize_filename(drucksache_nummer, ".pdf")
        return self.pdf_dir / f"wahlperiode_{wahlperiode}" / filename

    def get_markdown_path(self, drucksache_nummer: str, wahlperiode: int) -> Path:
        """
        Get the file path where markdown content should be stored.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)

        Returns:
            Path object for the markdown file

        Example:
            >>> manager.get_markdown_path('20/1234', 20)
            Path('data/input/bundestag/drucksache/markdown/wahlperiode_20/20_1234.md')
        """
        filename = self._normalize_filename(drucksache_nummer, ".md")
        return self.markdown_dir / f"wahlperiode_{wahlperiode}" / filename

    def ensure_directories_exist(self, wahlperiode: int) -> None:
        """
        Create PDF and markdown directories for a specific Wahlperiode if they don't exist.

        Args:
            wahlperiode: Electoral period number (e.g., 20)

        Raises:
            OSError: If directory creation fails due to permissions or disk issues
        """
        pdf_dir = self.pdf_dir / f"wahlperiode_{wahlperiode}"
        markdown_dir = self.markdown_dir / f"wahlperiode_{wahlperiode}"

        try:
            pdf_dir.mkdir(parents=True, exist_ok=True)
            markdown_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Ensured directories exist",
                wahlperiode=wahlperiode,
                pdf_dir=str(pdf_dir),
                markdown_dir=str(markdown_dir),
            )
        except OSError as e:
            logger.error(
                "Failed to create directories",
                wahlperiode=wahlperiode,
                error=str(e),
                pdf_dir=str(pdf_dir),
                markdown_dir=str(markdown_dir),
            )
            raise

    def save_pdf(self, drucksache_nummer: str, wahlperiode: int, pdf_bytes: bytes) -> str:
        """
        Save PDF bytes to file system.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)
            pdf_bytes: Raw PDF file content as bytes

        Returns:
            String path where the PDF was saved

        Raises:
            OSError: If file write fails due to permissions, disk full, etc.
            ValueError: If pdf_bytes is empty
        """
        if not pdf_bytes:
            raise ValueError(f"Cannot save empty PDF for {drucksache_nummer}")

        # Ensure directory exists
        self.ensure_directories_exist(wahlperiode)

        # Get file path and save
        pdf_path = self.get_pdf_path(drucksache_nummer, wahlperiode)

        try:
            pdf_path.write_bytes(pdf_bytes)
            logger.info(
                "Saved PDF",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(pdf_path),
                size_bytes=len(pdf_bytes),
            )
            return str(pdf_path)

        except OSError as e:
            logger.error(
                "Failed to save PDF",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(pdf_path),
                error=str(e),
            )
            raise

    def save_markdown(
        self, drucksache_nummer: str, wahlperiode: int, markdown_content: str
    ) -> str:
        """
        Save markdown content to file system.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)
            markdown_content: Extracted text content in markdown format

        Returns:
            String path where the markdown was saved

        Raises:
            OSError: If file write fails due to permissions, disk full, etc.
            ValueError: If markdown_content is empty
        """
        if not markdown_content or not markdown_content.strip():
            raise ValueError(f"Cannot save empty markdown for {drucksache_nummer}")

        # Ensure directory exists
        self.ensure_directories_exist(wahlperiode)

        # Get file path and save
        markdown_path = self.get_markdown_path(drucksache_nummer, wahlperiode)

        try:
            markdown_path.write_text(markdown_content, encoding="utf-8")
            logger.info(
                "Saved markdown",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(markdown_path),
                size_chars=len(markdown_content),
            )
            return str(markdown_path)

        except OSError as e:
            logger.error(
                "Failed to save markdown",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(markdown_path),
                error=str(e),
            )
            raise

    def pdf_exists(self, drucksache_nummer: str, wahlperiode: int) -> bool:
        """
        Check if a PDF file has already been downloaded.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)

        Returns:
            True if PDF exists, False otherwise

        Example:
            >>> if not manager.pdf_exists('20/1234', 20):
            ...     # Download and save PDF
        """
        pdf_path = self.get_pdf_path(drucksache_nummer, wahlperiode)
        exists = pdf_path.exists()

        if exists:
            logger.debug(
                "PDF already exists",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(pdf_path),
            )

        return exists

    def markdown_exists(self, drucksache_nummer: str, wahlperiode: int) -> bool:
        """
        Check if a markdown file has already been extracted.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            wahlperiode: Electoral period number (e.g., 20)

        Returns:
            True if markdown exists, False otherwise
        """
        markdown_path = self.get_markdown_path(drucksache_nummer, wahlperiode)
        exists = markdown_path.exists()

        if exists:
            logger.debug(
                "Markdown already exists",
                drucksache_nummer=drucksache_nummer,
                wahlperiode=wahlperiode,
                path=str(markdown_path),
            )

        return exists

    def _normalize_filename(self, drucksache_nummer: str, extension: str) -> str:
        """
        Convert Drucksache number to safe filename.

        Args:
            drucksache_nummer: Drucksache number (e.g., '20/1234')
            extension: File extension including dot (e.g., '.pdf' or '.md')

        Returns:
            Normalized filename (e.g., '20_1234.pdf')

        Example:
            >>> manager._normalize_filename('20/1234', '.pdf')
            '20_1234.pdf'
            >>> manager._normalize_filename('19/12345', '.md')
            '19_12345.md'
        """
        # Replace forward slash with underscore for file system compatibility
        safe_name = drucksache_nummer.replace("/", "_")
        return f"{safe_name}{extension}"
