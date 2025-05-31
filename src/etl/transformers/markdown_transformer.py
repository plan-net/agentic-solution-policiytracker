"""
Transform news articles to markdown format with metadata.
"""

import re
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()


class MarkdownTransformer:
    """Transforms news articles into markdown documents with frontmatter metadata."""

    def __init__(self) -> None:
        logger.info("Initialized MarkdownTransformer")

    def transform_article(self, article: dict[str, Any]) -> tuple[str, str]:
        """
        Transform article data to markdown format.

        Args:
            article: Normalized article data

        Returns:
            Tuple of (markdown_content, suggested_filename)
        """
        try:
            # Generate frontmatter with temporal metadata
            frontmatter = self._generate_frontmatter(article)

            # Generate markdown body
            body = self._generate_body(article)

            # Combine frontmatter and body
            markdown_content = f"{frontmatter}\n\n{body}"

            # Generate filename
            filename = self._generate_filename(article)

            return markdown_content, filename

        except Exception as e:
            logger.error(f"Failed to transform article: {e}")
            raise

    def _generate_frontmatter(self, article: dict[str, Any]) -> str:
        """Generate YAML frontmatter with article metadata."""
        # Key temporal fields for Graphiti
        frontmatter_data = {
            # Essential fields
            "title": article.get("title", "Untitled"),
            "url": article.get("url", ""),
            # Temporal fields (critical for temporal graph)
            "published_date": article.get("published_date", ""),
            "collected_date": article.get("collected_date", datetime.now().isoformat()),
            # Source information
            "source": article.get("source", "Unknown"),
            "source_url": article.get("source_url", ""),
            "author": article.get("author", ""),
            # Content metadata
            "description": article.get("description", ""),
            "language": article.get("language", "en"),
            "topics": article.get("topics", []),
            # Collection metadata
            "collection_type": article.get("collection_type", ""),
            # Tracking
            "apify_id": article.get("apify_id", ""),
            "apify_run_id": article.get("apify_run_id", ""),
        }

        # Build frontmatter string
        lines = ["---"]
        for key, value in frontmatter_data.items():
            if isinstance(value, list):
                if value:  # Only include non-empty lists
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
            elif value:  # Only include non-empty values
                # Escape quotes in strings
                if isinstance(value, str) and ('"' in value or "\n" in value):
                    value = value.replace('"', '\\"')
                    lines.append(f'{key}: "{value}"')
                else:
                    lines.append(f"{key}: {value}")
        lines.append("---")

        return "\n".join(lines)

    def _generate_body(self, article: dict[str, Any]) -> str:
        """Generate clean markdown body with minimal redundancy."""
        parts = []

        # Title (only once, from frontmatter)
        title = article.get("title", "Untitled")
        parts.append(f"# {title}")
        parts.append("")

        # Compact metadata (no redundancy with frontmatter)
        if article.get("author"):
            parts.append(f"*By {article['author']}*")
            parts.append("")

        # Description/Summary first (most valuable content)
        if article.get("description"):
            parts.append(article["description"])
            parts.append("")

        # Main content
        content = article.get("content", "")
        if content and content.strip():
            # Clean up content
            content = self._clean_content(content)
            parts.append(content)
        else:
            # More informative message about missing content
            parts.append(
                "**Note:** Full article content not available. This appears to be a headline/summary from RSS feeds."
            )
            parts.append("")
            parts.append(
                f"📰 **Read full article:** [{article.get('url', '')}]({article.get('url', '')})"
            )

        # Topics (if any)
        if article.get("topics"):
            parts.append("")
            parts.append("**Topics:** " + ", ".join(article["topics"]))

        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """Clean and format article content."""
        # Remove excessive whitespace
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        # Remove common artifacts
        content = re.sub(r"Advertisement\s*\n", "", content)
        content = re.sub(r"Continue reading\.\.\.", "", content)

        # Ensure paragraphs are properly separated
        paragraphs = content.split("\n\n")
        cleaned_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Skip very short paragraphs
                cleaned_paragraphs.append(para)

        return "\n\n".join(cleaned_paragraphs)

    def _generate_filename(self, article: dict[str, Any]) -> str:
        """Generate a safe filename for the article."""
        # Use published date for chronological ordering
        date_str = "unknown_date"
        if article.get("published_date"):
            try:
                # Parse and format date
                date_str = article["published_date"][:10].replace("-", "")  # YYYYMMDD
            except:
                date_str = datetime.now().strftime("%Y%m%d")

        # Clean title for filename
        title = article.get("title", "untitled")
        title_slug = self._slugify(title)[:50]  # Limit length

        # Include source for uniqueness
        source = self._slugify(article.get("source", "unknown"))[:20]

        # Combine elements
        filename = f"{date_str}_{source}_{title_slug}.md"

        return filename

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        # Convert to lowercase
        text = text.lower()

        # Replace spaces and special characters
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        return text
