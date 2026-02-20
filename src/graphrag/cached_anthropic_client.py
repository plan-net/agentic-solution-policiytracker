"""
Cached Anthropic client for Graphiti that injects cache_control breakpoints
for Anthropic's explicit prompt caching (90% discount on cached reads).

Anthropic requires explicit cache_control: {"type": "ephemeral"} on content
blocks to enable caching. This client overrides _generate_response() to add
cache breakpoints on:
  1. Tool definitions (last tool) — constant across calls
  2. System message — converted to content blocks with cache_control
  3. Schema prefix in user messages — ENTITY TYPES / FACT TYPES XML blocks
"""

import json
import logging
import re
import typing
from typing import Any

import anthropic
from pydantic import BaseModel

from graphiti_core.llm_client.anthropic_client import AnthropicClient
from graphiti_core.llm_client.config import LLMConfig, ModelSize
from graphiti_core.llm_client.errors import RateLimitError, RefusalError
from graphiti_core.prompts.models import Message

logger = logging.getLogger(__name__)

# Schema XML tags that contain constant content across calls (cacheable)
SCHEMA_TAGS = ['ENTITY TYPES', 'FACT TYPES']

# Tags that contain per-call variable content (should NOT be cached)
VARIABLE_CONTENT_TAGS = [
    'PREVIOUS MESSAGES', 'PREVIOUS_MESSAGES',
    'CURRENT MESSAGE', 'CURRENT_MESSAGE',
    'TEXT', 'EXTRACTED ENTITIES', 'EXTRACTED FACTS',
    'ENTITIES', 'JSON', 'MESSAGE',
    'REFERENCE_TIME', 'REFERENCE TIME',
    'SOURCE DESCRIPTION',
]


class CachedAnthropicClient(AnthropicClient):
    """Anthropic client with explicit cache_control for schema caching.

    Injects up to 3 cache breakpoints per request to enable Anthropic's
    prompt caching, which provides a 90% discount on cached input token reads.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        cache: bool = False,
        client: Any = None,
        max_tokens: int = 8192,
    ) -> None:
        super().__init__(config=config, cache=cache, client=client, max_tokens=max_tokens)
        self._cache_optimization_logged = False

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        """Generate a response with cache_control breakpoints injected.

        Overrides the parent to convert plain strings into content block arrays
        with cache_control markers, enabling Anthropic's prompt caching.
        """
        system_message = messages[0]
        user_messages = messages[1:]

        max_creation_tokens: int = self._resolve_max_tokens(max_tokens, self.model)

        try:
            # 1. Create tools with cache_control on the last tool definition
            tools, tool_choice = self._create_tool(response_model)
            cached_tools = _add_cache_to_tools(tools)

            # 2. Convert system message to content blocks with cache_control
            system_blocks = _create_cached_system(system_message.content)

            # 3. Convert user messages — split schema from variable content
            anthropic_messages = self._create_cached_messages(user_messages)

            if not self._cache_optimization_logged:
                logger.debug(
                    'Anthropic prompt cache: injecting cache_control breakpoints '
                    '(tools=%s, system=1, user_schema=%s)',
                    len(cached_tools) > 0,
                    any(
                        isinstance(m.get('content'), list)
                        for m in anthropic_messages
                    ),
                )
                self._cache_optimization_logged = True

            result = await self.client.messages.create(
                system=system_blocks,
                max_tokens=max_creation_tokens,
                temperature=self.temperature,
                messages=anthropic_messages,
                model=self.model,
                tools=cached_tools,
                tool_choice=tool_choice,
            )

            # Response extraction — same logic as parent class
            for content_item in result.content:
                if content_item.type == 'tool_use':
                    if isinstance(content_item.input, dict):
                        tool_args: dict[str, Any] = content_item.input
                    else:
                        tool_args = json.loads(str(content_item.input))
                    return tool_args

            for content_item in result.content:
                if content_item.type == 'text':
                    return self._extract_json_from_text(content_item.text)
                else:
                    raise ValueError(
                        f'Could not extract structured data from model response: {result.content}'
                    )

            raise ValueError(
                f'Could not extract structured data from model response: {result.content}'
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(
                f'Rate limit exceeded. Please try again later. Error: {e}'
            ) from e
        except anthropic.APIError as e:
            if 'refused to respond' in str(e).lower():
                raise RefusalError(str(e)) from e
            raise e
        except Exception as e:
            raise e

    def _create_cached_messages(
        self, messages: list[Message]
    ) -> list[dict[str, Any]]:
        """Convert user messages, splitting schema into cached content blocks.

        For user messages containing schema XML blocks (ENTITY TYPES, FACT TYPES)
        that appear BEFORE variable content, splits them into multi-block messages
        with cache_control on the schema block.
        """
        result: list[dict[str, Any]] = []

        for m in messages:
            if m.role == 'user':
                schema_part, variable_part = split_schema_from_content(m.content)
                if schema_part:
                    result.append({
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': schema_part,
                                'cache_control': {'type': 'ephemeral'},
                            },
                            {
                                'type': 'text',
                                'text': variable_part,
                            },
                        ],
                    })
                else:
                    result.append({'role': m.role, 'content': m.content})
            else:
                result.append({'role': m.role, 'content': m.content})

        return result


def _add_cache_to_tools(tools: list[Any]) -> list[Any]:
    """Add cache_control to the last tool definition.

    Tool schemas are constant across calls (they're derived from Pydantic models),
    so caching them avoids re-processing on every request.
    """
    if not tools:
        return tools

    cached_tools = list(tools)  # shallow copy
    cached_tools[-1] = {**cached_tools[-1], 'cache_control': {'type': 'ephemeral'}}
    return cached_tools


def _create_cached_system(system_content: str) -> list[dict[str, Any]]:
    """Convert system message string to content blocks with cache_control.

    Anthropic's API accepts system as either a string or a list of content blocks.
    Using content blocks allows us to add cache_control markers.
    """
    return [
        {
            'type': 'text',
            'text': system_content,
            'cache_control': {'type': 'ephemeral'},
        }
    ]


def split_schema_from_content(content: str) -> tuple[str | None, str]:
    """Extract schema XML blocks that appear BEFORE variable content.

    Only extracts schema if it appears as a prefix (before any variable content
    tags like <TEXT>, <CURRENT MESSAGE>, etc.). This ensures we don't accidentally
    cache per-call variable data.

    For example:
    - extract_text: "<ENTITY TYPES>...</ENTITY TYPES>\\n<TEXT>..." -> schema extracted
    - classify_nodes: "<EXTRACTED ENTITIES>...\\n<ENTITY TYPES>..." -> schema NOT extracted
      (because EXTRACTED ENTITIES is variable content that appears first)

    Returns:
        Tuple of (schema_part, remaining_content). schema_part is None if no
        schema blocks were found in the prefix region.
    """
    # Find the position of the first variable content tag
    first_variable_pos = len(content)
    for tag in VARIABLE_CONTENT_TAGS:
        match = re.search(rf'<{tag}>', content)
        if match and match.start() < first_variable_pos:
            first_variable_pos = match.start()

    # Only look for schema blocks in the prefix (before first variable content)
    prefix_content = content[:first_variable_pos]

    schema_blocks: list[str] = []
    remaining = content

    for tag in SCHEMA_TAGS:
        pattern = rf'(<{tag}>.*?</{tag}>)'
        match = re.search(pattern, prefix_content, re.DOTALL)
        if match:
            schema_blocks.append(match.group(1))
            # Remove the schema block from the full content
            start = match.start()
            end = match.end()
            remaining = remaining[:start] + remaining[end:]

    if schema_blocks:
        schema_part = '\n\n'.join(schema_blocks).strip()
        return schema_part, remaining.strip()

    return None, content
