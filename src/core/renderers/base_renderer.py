"""
Base Renderer Abstract Class.

Defines the interface for all output renderers, enabling
pluggable output formats (markdown, PDF, email, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRenderer(ABC):
    """
    Abstract base class for all output renderers.

    Renderers are responsible for converting structured report data
    (findings, summaries, metadata) into the final output format.

    Subclasses must implement:
    - format_name: Property returning the format name
    - render(): Async method for rendering the report
    - get_content_type(): MIME type for the output

    Example:
        class PDFRenderer(BaseRenderer):
            @property
            def format_name(self) -> str:
                return "pdf"

            async def render(self, context, template_name) -> bytes:
                # Implementation
                pass

            def get_content_type(self) -> str:
                return "application/pdf"
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """
        Return the output format name.

        Returns:
            Format name (e.g., "markdown", "pdf", "email")
        """
        pass

    @abstractmethod
    async def render(
        self,
        template_context: dict[str, Any],
        template_name: str,
    ) -> str | bytes:
        """
        Render the report to the target format.

        Takes a template context dictionary containing all the data
        needed for rendering (findings, summaries, metadata) and
        produces the final output.

        Args:
            template_context: Dictionary with all template variables
            template_name: Name of the template to use

        Returns:
            Rendered output as string (for text formats) or bytes (for binary)
        """
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """
        Return the MIME type for the output.

        Returns:
            MIME type string (e.g., "text/markdown", "application/pdf")
        """
        pass

    def validate_context(self, template_context: dict[str, Any]) -> list[str]:
        """
        Validate the template context has required fields.

        Override in subclasses to add format-specific validation.

        Args:
            template_context: Dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for essential fields
        if "week_label" not in template_context:
            errors.append("Missing required field: week_label")
        if "executive_summary" not in template_context:
            errors.append("Missing required field: executive_summary")

        return errors
