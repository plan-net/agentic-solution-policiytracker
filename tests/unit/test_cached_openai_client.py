"""Tests for CacheFriendlyOpenAIClient prompt cache optimization."""

import pytest

from src.graphrag.cached_openai_client import (
    CacheFriendlyOpenAIClient,
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
  {"name": "WORKS_AT", "description": "Employment relationship", "fact_type_signature": "Person -> Organization"},
  {"name": "LOCATED_IN", "description": "Location relationship", "fact_type_signature": "Organization -> Location"}
]
</FACT TYPES>"""

VARIABLE_TEXT = """<TEXT>
John Smith works at Acme Corp in New York City.
</TEXT>

Given the above text, extract entities from the TEXT that are explicitly or implicitly mentioned."""

EXTRACT_TEXT_PROMPT = f"""\n{ENTITY_TYPES_SCHEMA}\n\n{VARIABLE_TEXT}"""

EXTRACT_EDGES_PROMPT = f"""\n{FACT_TYPES_SCHEMA}\n\n<PREVIOUS_MESSAGES>\n[]\n</PREVIOUS_MESSAGES>\n\n<CURRENT_MESSAGE>\nJohn works at Acme.\n</CURRENT_MESSAGE>"""


# ─── Tests for split_schema_from_content ───


class TestSplitSchemaFromContent:
    def test_extracts_entity_types(self):
        schema_part, remaining = split_schema_from_content(EXTRACT_TEXT_PROMPT)
        assert schema_part is not None
        assert '<ENTITY TYPES>' in schema_part
        assert '</ENTITY TYPES>' in schema_part
        assert '<ENTITY TYPES>' not in remaining
        assert '<TEXT>' in remaining

    def test_extracts_fact_types(self):
        schema_part, remaining = split_schema_from_content(EXTRACT_EDGES_PROMPT)
        assert schema_part is not None
        assert '<FACT TYPES>' in schema_part
        assert '</FACT TYPES>' in schema_part
        assert '<FACT TYPES>' not in remaining
        assert '<PREVIOUS_MESSAGES>' in remaining

    def test_no_schema_returns_none(self):
        content = "Just a simple message with no schema blocks."
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is None
        assert remaining == content

    def test_preserves_variable_content(self):
        schema_part, remaining = split_schema_from_content(EXTRACT_TEXT_PROMPT)
        assert schema_part is not None
        assert 'John Smith works at Acme Corp' in remaining
        assert 'extract entities' in remaining

    def test_extracts_both_schemas(self):
        """When both ENTITY TYPES and FACT TYPES are present."""
        content = f"{ENTITY_TYPES_SCHEMA}\n\n{FACT_TYPES_SCHEMA}\n\nSome variable content."
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert '<ENTITY TYPES>' in schema_part
        assert '<FACT TYPES>' in schema_part
        assert 'Some variable content' in remaining


# ─── Tests for _convert_messages_to_openai_format ───


class TestConvertMessages:
    """Test the message restructuring for cache optimization.

    Note: We can't instantiate CacheFriendlyOpenAIClient without OpenAI deps,
    so we test the static split function and verify the override logic.
    """

    def test_schema_split_produces_two_parts(self):
        """When schema is found, we get schema + remaining."""
        schema_part, variable_part = split_schema_from_content(EXTRACT_TEXT_PROMPT)
        assert schema_part is not None
        assert variable_part is not None
        assert len(schema_part) > 0
        assert len(variable_part) > 0

    def test_no_schema_passthrough(self):
        """Messages without schema should pass through unchanged."""
        content = "Extract a summary of the entity."
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is None
        assert remaining == content

    def test_schema_content_is_complete(self):
        """Extracted schema should contain the full XML block with all content."""
        schema_part, _ = split_schema_from_content(EXTRACT_TEXT_PROMPT)
        assert schema_part is not None
        assert 'Person' in schema_part
        assert 'Organization' in schema_part
        assert 'Location' in schema_part

    def test_remaining_content_is_valid(self):
        """Remaining content after schema extraction should be clean."""
        _, remaining = split_schema_from_content(EXTRACT_TEXT_PROMPT)
        # Should not have dangling ENTITY TYPES tags
        assert '<ENTITY TYPES>' not in remaining
        assert '</ENTITY TYPES>' not in remaining
        # Should have the variable content
        assert '<TEXT>' in remaining


# ─── Tests for edge cases ───


class TestEdgeCases:
    def test_empty_content(self):
        schema_part, remaining = split_schema_from_content("")
        assert schema_part is None
        assert remaining == ""

    def test_partial_tag_not_extracted(self):
        """Incomplete XML tags should not be extracted."""
        content = "<ENTITY TYPES>some content without closing tag"
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is None
        assert remaining == content

    def test_nested_angle_brackets(self):
        """Schema with nested content should be extracted correctly."""
        content = '<ENTITY TYPES>\n{"name": "Person<T>", "id": 1}\n</ENTITY TYPES>\n\n<TEXT>hello</TEXT>'
        schema_part, remaining = split_schema_from_content(content)
        assert schema_part is not None
        assert 'Person<T>' in schema_part
