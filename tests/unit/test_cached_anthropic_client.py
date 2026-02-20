"""Tests for CachedAnthropicClient prompt cache optimization."""

import pytest

from src.graphrag.cached_anthropic_client import (
    _add_cache_to_tools,
    _create_cached_system,
    split_schema_from_content,
)


# ─── Sample schema content matching real Graphiti prompts ───


ENTITY_TYPES_SCHEMA = """<ENTITY TYPES>
[
  {"id": 1, "name": "Person", "description": "A human individual"},
  {"id": 2, "name": "Organization", "description": "A corporate or government entity"},
  {"id": 3, "name": "Location", "description": "A geographical place"}
]
</ENTITY TYPES>"""

FACT_TYPES_SCHEMA = """<FACT TYPES>
[
  {"name": "WORKS_AT", "description": "Employment relationship"},
  {"name": "LOCATED_IN", "description": "Location relationship"}
]
</FACT TYPES>"""


# ─── Tests for _add_cache_to_tools ───


class TestAddCacheToTools:
    def test_adds_cache_control_to_last_tool(self):
        tools = [
            {'name': 'tool_a', 'input_schema': {}},
            {'name': 'tool_b', 'input_schema': {}},
        ]
        result = _add_cache_to_tools(tools)
        assert 'cache_control' not in result[0]
        assert result[-1]['cache_control'] == {'type': 'ephemeral'}

    def test_single_tool(self):
        tools = [{'name': 'only_tool', 'input_schema': {}}]
        result = _add_cache_to_tools(tools)
        assert result[0]['cache_control'] == {'type': 'ephemeral'}
        assert result[0]['name'] == 'only_tool'

    def test_empty_tools(self):
        result = _add_cache_to_tools([])
        assert result == []

    def test_does_not_mutate_original(self):
        tools = [{'name': 'tool_a', 'input_schema': {}}]
        result = _add_cache_to_tools(tools)
        assert 'cache_control' not in tools[0]
        assert 'cache_control' in result[0]


# ─── Tests for _create_cached_system ───


class TestCreateCachedSystem:
    def test_converts_string_to_blocks(self):
        result = _create_cached_system("You are a helpful assistant.")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['type'] == 'text'
        assert result[0]['text'] == "You are a helpful assistant."

    def test_has_cache_control(self):
        result = _create_cached_system("System message.")
        assert result[0]['cache_control'] == {'type': 'ephemeral'}


# ─── Tests for split_schema_from_content (Anthropic-specific) ───


class TestSplitSchemaFromContent:
    def test_extracts_entity_types_before_variable_content(self):
        """extract_text prompt: schema appears BEFORE <TEXT>."""
        content = f"""
{ENTITY_TYPES_SCHEMA}

<TEXT>
John works at Acme Corp.
</TEXT>

Given the above text, extract entities."""
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert '<ENTITY TYPES>' in schema_part
        assert '</ENTITY TYPES>' in schema_part
        assert '<TEXT>' in remaining
        assert 'John works at Acme' in remaining

    def test_extracts_fact_types_before_variable_content(self):
        """extract_edges prompt: schema appears BEFORE <PREVIOUS_MESSAGES>."""
        content = f"""
{FACT_TYPES_SCHEMA}

<PREVIOUS_MESSAGES>
[]
</PREVIOUS_MESSAGES>

<CURRENT_MESSAGE>
John works at Acme.
</CURRENT_MESSAGE>"""
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert '<FACT TYPES>' in schema_part
        assert '<PREVIOUS_MESSAGES>' in remaining

    def test_does_not_extract_schema_after_variable_content(self):
        """classify_nodes prompt: schema appears AFTER <EXTRACTED ENTITIES>."""
        content = """
<EXTRACTED ENTITIES>
[{"name": "John", "uuid": "abc"}]
</EXTRACTED ENTITIES>

<ENTITY TYPES>
[{"id": 1, "name": "Person"}]
</ENTITY TYPES>

Classify the extracted entities."""
        schema_part, remaining = split_schema_from_content(content)
        # Schema appears AFTER variable content — should NOT be extracted
        assert schema_part is None
        assert '<ENTITY TYPES>' in remaining

    def test_no_schema_returns_none(self):
        content = "Just extract a summary of the entity."
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is None
        assert remaining == content

    def test_preserves_all_variable_content(self):
        content = f"""
{ENTITY_TYPES_SCHEMA}

<PREVIOUS MESSAGES>
["msg1"]
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
John works at Acme Corp.
</CURRENT MESSAGE>"""
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert '<PREVIOUS MESSAGES>' in remaining
        assert '<CURRENT MESSAGE>' in remaining
        assert 'John works at Acme Corp' in remaining

    def test_extract_message_prompt_pattern(self):
        """extract_message: <ENTITY TYPES> before <PREVIOUS MESSAGES>."""
        content = f"""
{ENTITY_TYPES_SCHEMA}

<PREVIOUS MESSAGES>
[]
</PREVIOUS MESSAGES>

<CURRENT MESSAGE>
Bob: I just joined Acme.
</CURRENT MESSAGE>

Instructions:
Extract entity nodes from the CURRENT MESSAGE."""
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert 'Person' in schema_part
        assert 'Bob: I just joined Acme' in remaining


# ─── Tests for CachedAnthropicClient message construction ───


class TestCachedMessages:
    """Test _create_cached_messages via the split_schema_from_content helper."""

    def test_schema_split_produces_two_parts(self):
        content = f"{ENTITY_TYPES_SCHEMA}\n\n<TEXT>\nHello world.\n</TEXT>"
        schema_part, variable_part = split_schema_from_content(content)
        assert schema_part is not None
        assert variable_part is not None
        assert len(schema_part) > 50  # schema should be substantial
        assert '<TEXT>' in variable_part

    def test_schema_part_suitable_for_caching(self):
        """Schema part should be identical across calls — good for caching."""
        content1 = f"{ENTITY_TYPES_SCHEMA}\n\n<TEXT>\nDocument A content.\n</TEXT>"
        content2 = f"{ENTITY_TYPES_SCHEMA}\n\n<TEXT>\nDocument B content.\n</TEXT>"
        schema1, _ = split_schema_from_content(content1)
        schema2, _ = split_schema_from_content(content2)
        assert schema1 == schema2  # identical schema = cache hit

    def test_variable_parts_differ_across_calls(self):
        """Variable parts should differ — confirming they're not cached."""
        content1 = f"{ENTITY_TYPES_SCHEMA}\n\n<TEXT>\nDocument A.\n</TEXT>"
        content2 = f"{ENTITY_TYPES_SCHEMA}\n\n<TEXT>\nDocument B.\n</TEXT>"
        _, var1 = split_schema_from_content(content1)
        _, var2 = split_schema_from_content(content2)
        assert var1 != var2


# ─── Edge cases ───


class TestEdgeCases:
    def test_empty_content(self):
        schema_part, remaining = split_schema_from_content("")
        assert schema_part is None
        assert remaining == ""

    def test_schema_only_content(self):
        """Content that is only schema with no variable content."""
        schema_part, remaining = split_schema_from_content(ENTITY_TYPES_SCHEMA)
        assert schema_part is not None
        assert '<ENTITY TYPES>' in schema_part
        assert remaining == ""  # nothing left after extraction

    def test_reference_time_is_variable(self):
        """REFERENCE_TIME should be treated as variable content."""
        content = f"""
{FACT_TYPES_SCHEMA}

<REFERENCE_TIME>
2025-01-01T00:00:00Z
</REFERENCE_TIME>

Extract facts."""
        schema_part, remaining = split_schema_from_content(content)
        # FACT TYPES appears before REFERENCE_TIME, so it should be extracted
        assert schema_part is not None
        assert '<FACT TYPES>' in schema_part
        assert '<REFERENCE_TIME>' in remaining
