"""Prompts for Weekly Digest v2 report generation."""

from src.flows.weekly_digest_v2.prompts.synthesis import (
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_USER_PROMPT_TEMPLATE,
)
from src.flows.weekly_digest_v2.prompts.extraction import (
    FINDING_EXTRACTION_SYSTEM_PROMPT,
    FINDING_EXTRACTION_USER_PROMPT_TEMPLATE,
)

__all__ = [
    "EXECUTIVE_SUMMARY_SYSTEM_PROMPT",
    "EXECUTIVE_SUMMARY_USER_PROMPT_TEMPLATE",
    "FINDING_EXTRACTION_SYSTEM_PROMPT",
    "FINDING_EXTRACTION_USER_PROMPT_TEMPLATE",
]
