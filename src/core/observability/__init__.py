"""
Observability Layer for Report Agents.

Provides unified tracing and metrics that work with both
LangWatch (for development/debugging) and Kodosumi Tracer
(for production progress updates).
"""

from src.core.observability.tracer import AgentTracer

__all__ = ["AgentTracer"]
