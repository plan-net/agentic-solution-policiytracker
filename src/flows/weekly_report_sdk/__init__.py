"""Weekly Report SDK Flow - Claude Agent SDK based report generation.

This module provides a weekly regulatory intelligence report generator
using Claude's native tool-use capabilities via the MCP protocol.
"""

from .processor import execute_weekly_report

__all__ = ["execute_weekly_report"]
