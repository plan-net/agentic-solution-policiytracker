"""
Output Renderers for Report Agents.

Provides pluggable renderers for different output formats:
- MarkdownRenderer: For Kodosumi integration (default)
- PDFRenderer: For downloadable reports (future)
- EmailRenderer: For email distribution (future)
"""

from src.core.renderers.base_renderer import BaseRenderer
from src.core.renderers.markdown_renderer import MarkdownRenderer

__all__ = [
    "BaseRenderer",
    "MarkdownRenderer",
]
