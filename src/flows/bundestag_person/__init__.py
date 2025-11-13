"""
Flow 5a: Bundestag Person Ingestion

Deterministic collection of German Bundestag members (MdBs) with explicit
field mapping and Neo4j MERGE operations.
"""

from .app import app

__all__ = ["app"]
