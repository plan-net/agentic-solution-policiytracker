"""
Bundestag Common Infrastructure.

Shared utilities, base classes, and helpers for all Bundestag data ingestion flows.
Provides deterministic, reusable components for entity creation and Neo4j operations.
"""

from src.flows.bundestag_common.base_flow import BaseBundestagFlow
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager
from src.flows.bundestag_common.field_extractors import (
    extract_fraktion,
    extract_wahlperioden,
    extract_committee_memberships,
    extract_person_roles,
)

__all__ = [
    "BaseBundestagFlow",
    "Neo4jUpsertManager",
    "extract_fraktion",
    "extract_wahlperioden",
    "extract_committee_memberships",
    "extract_person_roles",
]
