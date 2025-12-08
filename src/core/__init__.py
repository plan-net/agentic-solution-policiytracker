"""
Core Infrastructure for Political Monitoring Agents.

This module provides reusable base classes, configuration models, observability,
and rendering utilities that can be shared across multiple agent implementations
(weekly digest, monthly reports, topic-specific reports, etc.).

Modules:
    agents: Base agent classes and mixins
    config: Configuration models for reports, categories, and tool plans
    observability: Unified tracing and observability layer
    renderers: Output format renderers (markdown, PDF, etc.)
    visualization: Graph visualization utilities
"""

from src.core.agents.base_agent import AgentResult, BaseReportAgent, ReportType
from src.core.config.report_config import ReportConfig
from src.core.config.category_config import CategoryConfig, SearchType
from src.core.config.tool_plan_config import ToolPlanConfig
from src.core.observability.tracer import AgentTracer
from src.core.visualization.graph_link_builder import GraphLinkBuilder

__all__ = [
    # Agents
    "AgentResult",
    "BaseReportAgent",
    "ReportType",
    # Config
    "ReportConfig",
    "CategoryConfig",
    "SearchType",
    "ToolPlanConfig",
    # Observability
    "AgentTracer",
    # Visualization
    "GraphLinkBuilder",
]
