"""
Cached OpenAI client for Graphiti that optimizes prompt structure for
OpenAI's automatic prompt caching (50% discount on cached prefix tokens).

OpenAI automatically caches identical byte-level prefixes of prompts.
This client moves constant schema blocks (ENTITY TYPES, FACT TYPES)
from the user message into a developer message, creating a longer
stable prefix that gets cached across sequential chunk processing calls.
"""

import logging
import re
from typing import Any

from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.prompts.models import Message

logger = logging.getLogger(__name__)

# Schema XML tags that contain constant content across calls (cacheable)
SCHEMA_TAGS = ['ENTITY TYPES', 'FACT TYPES']


class CacheFriendlyOpenAIClient(OpenAIClient):
    """OpenAI client that optimizes prompt structure for automatic prefix cache hits.

    By moving constant schema blocks into a separate developer message,
    the [system msg] + [developer: schema] prefix becomes identical across
    all calls of the same type, maximizing OpenAI's automatic cache hits.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        cache: bool = False,
        client: Any = None,
        max_tokens: int = 8192,
    ):
        super().__init__(config=config, cache=cache, client=client, max_tokens=max_tokens)
        self._cache_optimization_logged = False

    def _convert_messages_to_openai_format(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Override to restructure messages for better cache prefix matching.

        Strategy: Extract schema blocks (ENTITY TYPES, FACT TYPES) from the
        user message and place them in a developer message between system and
        user messages, creating a long, stable, cacheable prefix.
        """
        openai_messages: list[dict[str, Any]] = []

        for m in messages:
            m.content = self._clean_input(m.content)

            if m.role == 'system':
                openai_messages.append({'role': 'system', 'content': m.content})
            elif m.role == 'user':
                schema_part, variable_part = split_schema_from_content(m.content)
                if schema_part:
                    if not self._cache_optimization_logged:
                        logger.debug(
                            'Prompt cache optimization: moved %d-char schema to developer message',
                            len(schema_part),
                        )
                        self._cache_optimization_logged = True
                    # Insert schema as developer message right after system message
                    openai_messages.insert(1, {'role': 'developer', 'content': schema_part})
                    openai_messages.append({'role': 'user', 'content': variable_part})
                else:
                    openai_messages.append({'role': 'user', 'content': m.content})

        return openai_messages


def split_schema_from_content(content: str) -> tuple[str | None, str]:
    """Extract schema XML blocks from user message content.

    Detects <ENTITY TYPES>...</ENTITY TYPES> and <FACT TYPES>...</FACT TYPES>
    blocks and separates them from the rest of the content.

    Returns:
        Tuple of (schema_part, remaining_content). schema_part is None if
        no schema blocks were found.
    """
    schema_blocks: list[str] = []
    remaining = content

    for tag in SCHEMA_TAGS:
        pattern = rf'(<{tag}>.*?</{tag}>)'
        match = re.search(pattern, remaining, re.DOTALL)
        if match:
            schema_blocks.append(match.group(1))
            remaining = remaining[:match.start()] + remaining[match.end():]

    if schema_blocks:
        schema_part = '\n\n'.join(schema_blocks).strip()
        return schema_part, remaining.strip()

    return None, content
