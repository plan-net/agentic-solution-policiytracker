"""
Core Agent Base Classes and Mixins.

Provides abstract base classes for building report agents with consistent
interfaces for execution, configuration, and observability.
"""

from src.core.agents.base_agent import (
    AgentResult,
    BaseReportAgent,
    ReportType,
)
from src.core.agents.base_researcher import (
    BaseCategoryResearcher,
    SearchResult,
)
from src.core.agents.mixins import (
    ObservabilityMixin,
    StreamingMixin,
)

__all__ = [
    "AgentResult",
    "BaseReportAgent",
    "ReportType",
    "BaseCategoryResearcher",
    "SearchResult",
    "ObservabilityMixin",
    "StreamingMixin",
]
