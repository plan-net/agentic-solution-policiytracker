"""
Relevance Filtering Module

Provides hybrid relevance filtering for discovered content:
1. Fast keyword-based scoring using client.yaml context
2. Optional LLM-based analysis for borderline cases
"""

from .keyword_scorer import KeywordScorer
from .llm_analyzer import LLMAnalyzer
from .relevance_filter import RelevanceFilter, FilterConfig, create_filter_from_config

__all__ = [
    "KeywordScorer",
    "LLMAnalyzer",
    "RelevanceFilter",
    "FilterConfig",
    "create_filter_from_config",
]
