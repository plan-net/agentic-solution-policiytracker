"""Agent module for weekly report generation.

Uses Claude Agent SDK for automatic agentic loop and native MCP support.
"""

from .report_agent_sdk import WeeklyReportSDKAgent
from .prompts import get_weekly_report_system_prompt, TOOLS

# Alias for backward compatibility
WeeklyReportAgent = WeeklyReportSDKAgent

__all__ = [
    "WeeklyReportAgent",
    "WeeklyReportSDKAgent",
    "get_weekly_report_system_prompt",
    "TOOLS",
]
