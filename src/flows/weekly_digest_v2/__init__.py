"""
Weekly Regulatory Intelligence Digest v2.

A multi-agent report generation system that produces weekly briefings on
EU and German regulatory developments. Features:

- Configuration-driven category research
- Graphiti knowledge graph integration
- LangWatch observability
- Graph visualization links
- Kodosumi flow integration

Entry Points:
    - app.fast_app: Ray Serve deployment for Kodosumi
    - processor.execute_weekly_digest: Kodosumi processor entry point
"""

from src.flows.weekly_digest_v2.models import (
    CategoryResearchResult,
    Finding,
    FindingPriority,
    ReportMetadata,
    WeeklyDigestState,
)

__all__ = [
    "CategoryResearchResult",
    "Finding",
    "FindingPriority",
    "ReportMetadata",
    "WeeklyDigestState",
]
