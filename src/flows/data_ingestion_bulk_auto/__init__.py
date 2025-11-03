"""Flow 1B: Bulk Auto-Delta Document Ingestion."""

from src.flows.data_ingestion_bulk_auto.processor import (
    execute_bulk_auto_processing,
    get_unprocessed_documents,
)
from src.flows.data_ingestion_bulk_auto.report_generator import BulkAutoReportGenerator

__all__ = [
    "execute_bulk_auto_processing",
    "get_unprocessed_documents",
    "BulkAutoReportGenerator",
]
