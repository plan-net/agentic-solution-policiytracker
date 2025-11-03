"""
Document Converter: PDF/DOCX/TXT/PPT/PPTX → Markdown

Converts various document formats to markdown for processing through
the political monitoring pipeline.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger()


class DocumentConverter:
    """Convert various document formats to markdown."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".ppt", ".pptx"}

    def __init__(self, output_dir: str = "data/input/documents_md"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized DocumentConverter with output: {self.output_dir}")

    def convert_to_markdown(self, file_path: Path) -> Tuple[str, str]:
        """
        Convert document to markdown format.

        Args:
            file_path: Path to input document

        Returns:
            Tuple of (markdown_content, output_filename)

        Raises:
            ValueError: If file format not supported
        """
        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        logger.info(f"Converting {file_path.name} ({extension}) to markdown")

        # Route to appropriate converter
        if extension == ".pdf":
            content = self._convert_pdf(file_path)
        elif extension == ".docx":
            content = self._convert_docx(file_path)
        elif extension == ".txt":
            content = self._convert_txt(file_path)
        elif extension in {".ppt", ".pptx"}:
            content = self._convert_pptx(file_path)
        else:
            raise ValueError(f"Unsupported extension: {extension}")

        # Generate metadata frontmatter
        frontmatter = self._generate_frontmatter(file_path)

        # Combine frontmatter and content
        markdown_content = f"{frontmatter}\n\n{content}"

        # Generate output filename
        output_filename = self._generate_filename(file_path)

        return markdown_content, output_filename

    def _convert_pdf(self, file_path: Path) -> str:
        """Convert PDF to markdown text."""
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf is required for PDF conversion. Install: pip install pypdf")

        try:
            reader = pypdf.PdfReader(str(file_path))
            pages = []

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    pages.append(f"## Page {page_num}\n\n{text.strip()}")

            if not pages:
                return "**Note:** No text content could be extracted from this PDF."

            return "\n\n---\n\n".join(pages)

        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return f"**Error:** Failed to extract text from PDF: {str(e)}"

    def _convert_docx(self, file_path: Path) -> str:
        """Convert DOCX to markdown text."""
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx is required for DOCX conversion. Install: pip install python-docx")

        try:
            doc = docx.Document(str(file_path))
            paragraphs = []

            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    # Detect headings based on style
                    if para.style.name.startswith("Heading"):
                        level = para.style.name.replace("Heading ", "")
                        try:
                            heading_level = int(level)
                            paragraphs.append(f"{'#' * heading_level} {text}")
                        except ValueError:
                            paragraphs.append(text)
                    else:
                        paragraphs.append(text)

            if not paragraphs:
                return "**Note:** No text content could be extracted from this DOCX."

            return "\n\n".join(paragraphs)

        except Exception as e:
            logger.error(f"DOCX conversion failed: {e}")
            return f"**Error:** Failed to extract text from DOCX: {str(e)}"

    def _convert_txt(self, file_path: Path) -> str:
        """Convert TXT to markdown text."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                return "**Note:** This text file is empty."

            return content

        except UnicodeDecodeError:
            # Try different encoding
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read().strip()
                return content
            except Exception as e:
                logger.error(f"TXT conversion failed: {e}")
                return f"**Error:** Failed to read text file: {str(e)}"
        except Exception as e:
            logger.error(f"TXT conversion failed: {e}")
            return f"**Error:** Failed to read text file: {str(e)}"

    def _convert_pptx(self, file_path: Path) -> str:
        """Convert PPT/PPTX to markdown text with slide numbers."""
        try:
            from pptx import Presentation
        except ImportError:
            raise ImportError("python-pptx is required for PPT/PPTX conversion. Install: pip install python-pptx")

        try:
            prs = Presentation(str(file_path))
            slides = []

            for slide_num, slide in enumerate(prs.slides, 1):
                slide_content = []
                slide_content.append(f"## Slide {slide_num}")

                # Extract title if present
                if slide.shapes.title:
                    title_text = slide.shapes.title.text.strip()
                    if title_text:
                        slide_content.append(f"### {title_text}")

                # Extract text from all shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text = shape.text.strip()
                        # Avoid duplicating title
                        if text and (not slide.shapes.title or text != slide.shapes.title.text.strip()):
                            slide_content.append(text)

                if len(slide_content) > 1:  # More than just the slide number
                    slides.append("\n\n".join(slide_content))

            if not slides:
                return "**Note:** No text content could be extracted from this PowerPoint."

            return "\n\n---\n\n".join(slides)

        except Exception as e:
            logger.error(f"PPTX conversion failed: {e}")
            return f"**Error:** Failed to extract text from PowerPoint: {str(e)}"

    def _generate_frontmatter(self, file_path: Path) -> str:
        """Generate YAML frontmatter with document metadata."""
        frontmatter_data = {
            "title": file_path.stem.replace("_", " ").replace("-", " ").title(),
            "source_file": file_path.name,
            "file_type": file_path.suffix.lower().replace(".", "").upper(),
            "converted_date": datetime.now().isoformat(),
            "collection_type": "adhoc_upload",
        }

        lines = ["---"]
        for key, value in frontmatter_data.items():
            if value:
                if isinstance(value, str) and ('"' in value or "\n" in value):
                    value = value.replace('"', '\\"')
                    lines.append(f'{key}: "{value}"')
                else:
                    lines.append(f"{key}: {value}")
        lines.append("---")

        return "\n".join(lines)

    def _generate_filename(self, file_path: Path) -> str:
        """Generate safe markdown filename."""
        # Use current date for chronological ordering
        date_str = datetime.now().strftime("%Y%m%d")

        # Clean filename
        name_slug = self._slugify(file_path.stem)[:50]

        # Combine elements
        filename = f"{date_str}_adhoc_{name_slug}.md"

        return filename

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        text = text.strip("-")
        return text

    async def convert_and_save(self, file_path: Path) -> Path:
        """
        Convert document to markdown and save to output directory.

        Args:
            file_path: Path to input document

        Returns:
            Path to saved markdown file
        """
        markdown_content, output_filename = self.convert_to_markdown(file_path)

        output_path = self.output_dir / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"Saved markdown to: {output_path}")

        return output_path
