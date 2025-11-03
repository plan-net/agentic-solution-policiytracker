"""
Flow 1D: Raw Document Auto-Conversion

Automatically converts raw documents (PDF, DOC, DOCX, PPT, PPTX) to markdown
format with policy-compatible metadata.
"""

from src.flows.documents_raw_converter.app import app
from src.flows.documents_raw_converter.processor import (
    execute_raw_document_conversion,
)
from src.flows.documents_raw_converter.raw_tracker import RawDocumentTracker

__all__ = ["app", "execute_raw_document_conversion", "RawDocumentTracker"]
