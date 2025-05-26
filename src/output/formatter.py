import re
from typing import Any

import structlog

logger = structlog.get_logger()


class MarkdownFormatter:
    """Utility class for markdown formatting and text processing."""

    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special markdown characters in text."""
        if not text:
            return ""

        # Escape markdown special characters
        special_chars = ["*", "_", "`", "#", "[", "]", "(", ")", "!", "\\"]
        escaped_text = text

        for char in special_chars:
            escaped_text = escaped_text.replace(char, f"\\{char}")

        return escaped_text

    @staticmethod
    def clean_filename(filename: str) -> str:
        """Clean filename for safe markdown display."""
        if not filename:
            return "Unknown Document"

        # Remove path separators and dangerous characters
        cleaned = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Limit length
        if len(cleaned) > 100:
            name, ext = cleaned.rsplit(".", 1) if "." in cleaned else (cleaned, "")
            cleaned = name[:90] + "..." + ("." + ext if ext else "")

        return cleaned

    @staticmethod
    def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
        """Truncate text to specified length with suffix."""
        if not text or len(text) <= max_length:
            return text

        # Try to break at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:  # If we found a space near the end
            truncated = truncated[:last_space]

        return truncated + suffix

    @staticmethod
    def format_score(score: float, precision: int = 1) -> str:
        """Format score with consistent precision."""
        return f"{score:.{precision}f}"

    @staticmethod
    def format_percentage(value: float, total: float, precision: int = 1) -> str:
        """Format percentage with error handling."""
        if total == 0:
            return "0.0%"

        percentage = (value / total) * 100
        return f"{percentage:.{precision}f}%"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"

    @staticmethod
    def create_table(headers: list[str], rows: list[list[str]]) -> str:
        """Create markdown table from headers and rows."""
        if not headers or not rows:
            return ""

        # Create header row
        header_row = "| " + " | ".join(headers) + " |"

        # Create separator row
        separator_row = "|" + "|".join("---" for _ in headers) + "|"

        # Create data rows
        data_rows = []
        for row in rows:
            # Pad row if it's shorter than headers
            padded_row = row + [""] * (len(headers) - len(row))
            data_row = "| " + " | ".join(padded_row[: len(headers)]) + " |"
            data_rows.append(data_row)

        # Combine all rows
        table_lines = [header_row, separator_row] + data_rows
        return "\n".join(table_lines)

    @staticmethod
    def format_evidence_list(evidence_snippets: list[str], max_snippets: int = 3) -> str:
        """Format evidence snippets as markdown list."""
        if not evidence_snippets:
            return "*No specific evidence available*"

        formatted_snippets = []
        for snippet in evidence_snippets[:max_snippets]:
            # Clean and truncate snippet
            cleaned = snippet.strip()
            if len(cleaned) > 150:
                cleaned = cleaned[:147] + "..."

            # Escape markdown and format as quote
            escaped = MarkdownFormatter.escape_markdown(cleaned)
            formatted_snippets.append(f"> {escaped}")

        return "\n".join(formatted_snippets)

    @staticmethod
    def format_dimension_scores(dimension_scores: dict[str, Any]) -> str:
        """Format dimension scores as markdown list."""
        if not dimension_scores:
            return "*No scoring dimensions available*"

        formatted_scores = []
        for dim_name, dim_score in dimension_scores.items():
            display_name = dim_name.replace("_", " ").title()
            score_text = f"**{display_name}:** {dim_score.score:.1f}/100"

            if hasattr(dim_score, "justification") and dim_score.justification:
                score_text += f" - {dim_score.justification}"

            formatted_scores.append(score_text)

        return "\n".join(f"- {score}" for score in formatted_scores)

    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 20) -> str:
        """Create ASCII progress bar."""
        if total == 0:
            return "[" + " " * width + "] 0%"

        progress = current / total
        filled = int(progress * width)
        bar = "█" * filled + "░" * (width - filled)
        percentage = progress * 100

        return f"[{bar}] {percentage:.1f}%"

    @staticmethod
    def sanitize_for_filename(text: str) -> str:
        """Sanitize text for use in filename."""
        if not text:
            return "untitled"

        # Replace spaces and special characters
        sanitized = re.sub(r"[^\w\-_\.]", "_", text)

        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure it's not empty
        if not sanitized:
            sanitized = "untitled"

        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]

        return sanitized

    @staticmethod
    def format_metadata_table(metadata: dict[str, Any]) -> str:
        """Format metadata as markdown table."""
        if not metadata:
            return "*No metadata available*"

        rows = []
        for key, value in metadata.items():
            # Format key
            display_key = key.replace("_", " ").title()

            # Format value
            if isinstance(value, (list, tuple)):
                display_value = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                display_value = f"{len(value)} items"
            else:
                display_value = str(value)

            # Truncate long values
            if len(display_value) > 50:
                display_value = display_value[:47] + "..."

            rows.append([display_key, display_value])

        return MarkdownFormatter.create_table(["Property", "Value"], rows)
