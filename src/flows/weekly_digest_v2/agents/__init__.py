"""
Weekly Digest v2 Agent Module.

Implements a 3-agent architecture for the Weekly Regulatory Intelligence Digest:
1. ResearchPlannerAgent: Plans research based on YAML configurations
2. ToolExecutorAgent: Executes all tool calls and extracts findings
3. ReportSynthesizer: Generates executive summary and prepares report

The ReportOrchestrator coordinates these agents in a LangGraph workflow.

Legacy:
- ConfigurableCategoryResearcher: DEPRECATED - logic moved to ToolExecutorAgent
"""

from src.flows.weekly_digest_v2.agents.base import (
    ToolResult,
    WeeklyDigestState,
)
from src.flows.weekly_digest_v2.agents.orchestrator import ReportOrchestrator
from src.flows.weekly_digest_v2.agents.report_synthesizer import ReportSynthesizer
from src.flows.weekly_digest_v2.agents.research_planner import ResearchPlannerAgent
from src.flows.weekly_digest_v2.agents.tool_executor import ToolExecutorAgent

# Keep ConfigurableCategoryResearcher for backwards compatibility
from src.flows.weekly_digest_v2.agents.category_researchers import (
    ConfigurableCategoryResearcher,
)

__all__ = [
    # New 3-agent architecture
    "ResearchPlannerAgent",
    "ToolExecutorAgent",
    "ReportSynthesizer",
    "ReportOrchestrator",
    # State types
    "WeeklyDigestState",
    "ToolResult",
    # Legacy (deprecated)
    "ConfigurableCategoryResearcher",
]
