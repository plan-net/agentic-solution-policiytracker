"""Unit tests for FindPathsTool (Tool 8)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.chat.tools.traverse import FindPathsTool


class TestFindPathsTool:
    """Test suite for FindPathsTool with Cypher-based path finding."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        client = MagicMock()
        client.driver = MagicMock()
        return client

    @pytest.fixture
    def paths_tool(self, mock_graphiti_client):
        """Create FindPathsTool instance with mock client."""
        return FindPathsTool(graphiti_client=mock_graphiti_client)

    # Tests for _find_entity_node

    @pytest.mark.asyncio
    async def test_find_entity_node_success(self, paths_tool, mock_graphiti_client):
        """Test successful entity node finding."""
        # Mock Neo4j session and result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "uuid": "entity-123-uuid",
                    "name": "Meta",
                    "labels": ["Entity", "Company"],
                    "properties": {"industry": "technology"},
                }
            ]
        )

        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        result = await paths_tool._find_entity_node("Meta")

        # Assert
        assert result is not None
        assert result["uuid"] == "entity-123-uuid"
        assert result["name"] == "Meta"
        assert "Company" in result["labels"]

        # Verify query was executed
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        query = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        params = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("params", {})
        assert "MATCH (n:Entity)" in query
        assert params.get("entity_name") == "Meta"

    @pytest.mark.asyncio
    async def test_find_entity_node_not_found(self, paths_tool, mock_graphiti_client):
        """Test entity node not found."""
        # Mock Neo4j session with empty result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        result = await paths_tool._find_entity_node("NonExistentEntity")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_entity_node_handles_exception(self, paths_tool, mock_graphiti_client):
        """Test _find_entity_node handles exceptions gracefully."""
        # Mock session to raise exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        result = await paths_tool._find_entity_node("Meta")

        # Assert - should return None on error
        assert result is None

    # Tests for _find_paths_cypher

    @pytest.mark.asyncio
    async def test_find_paths_cypher_success(self, paths_tool, mock_graphiti_client):
        """Test successful path finding via Cypher."""
        # Mock Neo4j session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "path_nodes": [
                        {"uuid": "source-uuid", "name": "Meta", "types": ["Entity", "Company"]},
                        {
                            "uuid": "intermediate-uuid",
                            "name": "EU Digital Services Act",
                            "types": ["Entity", "Policy"],
                        },
                        {
                            "uuid": "target-uuid",
                            "name": "European Commission",
                            "types": ["Entity", "Organization"],
                        },
                    ],
                    "path_relationships": [
                        {
                            "type": "SUBJECT_TO",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with DSA requirements",
                            "properties": {},
                        },
                        {
                            "type": "ENFORCED_BY",
                            "source_name": "EU Digital Services Act",
                            "target_name": "European Commission",
                            "fact": "Commission enforces DSA regulations",
                            "properties": {},
                        },
                    ],
                    "path_length": 2,
                }
            ]
        )

        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await paths_tool._find_paths_cypher(
            source_uuid="source-uuid", target_uuid="target-uuid", max_path_length=4, max_paths=5
        )

        # Assert
        assert len(results) == 1
        assert results[0]["path_length"] == 2
        assert len(results[0]["path_nodes"]) == 3
        assert len(results[0]["path_relationships"]) == 2

        # Verify query structure
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        query = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        params = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("params", {})
        assert "allShortestPaths" in query
        assert params["source_uuid"] == "source-uuid"
        assert params["target_uuid"] == "target-uuid"

    @pytest.mark.asyncio
    async def test_find_paths_cypher_no_paths(self, paths_tool, mock_graphiti_client):
        """Test _find_paths_cypher with no paths found."""
        # Mock Neo4j session with empty result
        mock_session = AsyncMock()
        mock_empty_result = AsyncMock()
        mock_empty_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(return_value=mock_empty_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await paths_tool._find_paths_cypher(
            source_uuid="source-uuid", target_uuid="target-uuid", max_path_length=4, max_paths=5
        )

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_find_paths_cypher_handles_exception(self, paths_tool, mock_graphiti_client):
        """Test _find_paths_cypher handles exceptions gracefully."""
        # Mock session to raise exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j query error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await paths_tool._find_paths_cypher(
            source_uuid="source-uuid", target_uuid="target-uuid", max_path_length=4, max_paths=5
        )

        # Assert - should return empty list on error
        assert results == []

    # Tests for _arun

    @pytest.mark.asyncio
    async def test_arun_source_entity_not_found(self, paths_tool):
        """Test _arun when source entity is not found."""
        # Mock _find_entity_node to return None for source
        paths_tool._find_entity_node = AsyncMock(return_value=None)

        # Execute
        result = await paths_tool._arun(source_entity="NonExistent", target_entity="Meta")

        # Assert
        assert "not found" in result
        assert "NonExistent" in result
        assert "Source entity" in result

    @pytest.mark.asyncio
    async def test_arun_target_entity_not_found(self, paths_tool):
        """Test _arun when target entity is not found."""
        # Mock _find_entity_node: source found, target not found
        async def mock_find(entity_name):
            if entity_name == "Meta":
                return {"uuid": "meta-uuid", "name": "Meta", "labels": ["Entity", "Company"]}
            return None

        paths_tool._find_entity_node = AsyncMock(side_effect=mock_find)

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="NonExistent")

        # Assert
        assert "not found" in result
        assert "NonExistent" in result
        assert "Target entity" in result

    @pytest.mark.asyncio
    async def test_arun_success_with_paths(self, paths_tool):
        """Test _arun with successful path discovery."""
        # Mock _find_entity_node for both entities
        async def mock_find(entity_name):
            if entity_name == "Meta":
                return {"uuid": "meta-uuid", "name": "Meta", "labels": ["Entity", "Company"]}
            elif entity_name == "European Commission":
                return {
                    "uuid": "commission-uuid",
                    "name": "European Commission",
                    "labels": ["Entity", "Organization"],
                }
            return None

        paths_tool._find_entity_node = AsyncMock(side_effect=mock_find)

        # Mock _find_paths_cypher
        paths_tool._find_paths_cypher = AsyncMock(
            return_value=[
                {
                    "path_nodes": [
                        {"uuid": "meta-uuid", "name": "Meta", "types": ["Entity", "Company"]},
                        {
                            "uuid": "dsa-uuid",
                            "name": "EU Digital Services Act",
                            "types": ["Entity", "Policy"],
                        },
                        {
                            "uuid": "commission-uuid",
                            "name": "European Commission",
                            "types": ["Entity", "Organization"],
                        },
                    ],
                    "path_relationships": [
                        {
                            "type": "SUBJECT_TO",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with DSA requirements",
                            "properties": {},
                        },
                        {
                            "type": "ENFORCED_BY",
                            "source_name": "EU Digital Services Act",
                            "target_name": "European Commission",
                            "fact": "Commission enforces DSA",
                            "properties": {},
                        },
                    ],
                    "path_length": 2,
                }
            ]
        )

        # Mock source extraction
        paths_tool._extract_source_from_episode = AsyncMock(return_value=None)

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="European Commission")

        # Assert
        assert "Connection Paths: Meta ↔ European Commission" in result
        assert "**Paths Found**: 1" in result
        assert "### Path 1 (2 hops)" in result
        assert "EU Digital Services Act" in result
        assert "SUBJECT_TO" in result
        assert "ENFORCED_BY" in result
        assert "**Path Chain**:" in result

        # Verify summary sections
        assert "## Summary" in result
        assert "### Entities Found" in result
        assert "### Relationships Discovered" in result

    @pytest.mark.asyncio
    async def test_arun_no_paths_found(self, paths_tool):
        """Test _arun when no paths are found."""
        # Mock _find_entity_node for both entities
        async def mock_find(entity_name):
            if entity_name == "Meta":
                return {"uuid": "meta-uuid", "name": "Meta", "labels": ["Entity", "Company"]}
            elif entity_name == "Unrelated Entity":
                return {
                    "uuid": "unrelated-uuid",
                    "name": "Unrelated Entity",
                    "labels": ["Entity", "Organization"],
                }
            return None

        paths_tool._find_entity_node = AsyncMock(side_effect=mock_find)

        # Mock _find_paths_cypher to return empty list
        paths_tool._find_paths_cypher = AsyncMock(return_value=[])

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="Unrelated Entity")

        # Assert
        assert "Connection Paths: Meta ↔ Unrelated Entity" in result
        assert "No paths found" in result
        assert "**Suggestions:**" in result

    @pytest.mark.asyncio
    async def test_arun_handles_exception(self, paths_tool):
        """Test _arun handles exceptions gracefully."""
        # Mock _find_entity_node to raise exception
        paths_tool._find_entity_node = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="Google")

        # Assert
        assert "Error finding paths" in result
        assert "Database error" in result

    @pytest.mark.asyncio
    async def test_arun_with_longer_path(self, paths_tool):
        """Test _arun with longer path (3+ hops)."""
        # Mock _find_entity_node
        async def mock_find(entity_name):
            if entity_name == "Meta":
                return {"uuid": "meta-uuid", "name": "Meta", "labels": ["Entity", "Company"]}
            elif entity_name == "Target":
                return {"uuid": "target-uuid", "name": "Target", "labels": ["Entity", "Organization"]}
            return None

        paths_tool._find_entity_node = AsyncMock(side_effect=mock_find)

        # Mock _find_paths_cypher with 4-hop path
        paths_tool._find_paths_cypher = AsyncMock(
            return_value=[
                {
                    "path_nodes": [
                        {"uuid": "meta-uuid", "name": "Meta", "types": ["Entity", "Company"]},
                        {"uuid": "node2-uuid", "name": "Node2", "types": ["Entity", "Policy"]},
                        {"uuid": "node3-uuid", "name": "Node3", "types": ["Entity", "Regulation"]},
                        {"uuid": "node4-uuid", "name": "Node4", "types": ["Entity", "Committee"]},
                        {"uuid": "target-uuid", "name": "Target", "types": ["Entity", "Organization"]},
                    ],
                    "path_relationships": [
                        {
                            "type": "SUBJECT_TO",
                            "source_name": "Meta",
                            "target_name": "Node2",
                            "fact": "Fact 1",
                            "properties": {},
                        },
                        {
                            "type": "IMPLEMENTS",
                            "source_name": "Node2",
                            "target_name": "Node3",
                            "fact": "Fact 2",
                            "properties": {},
                        },
                        {
                            "type": "ENFORCED_BY",
                            "source_name": "Node3",
                            "target_name": "Node4",
                            "fact": "Fact 3",
                            "properties": {},
                        },
                        {
                            "type": "OVERSEES",
                            "source_name": "Node4",
                            "target_name": "Target",
                            "fact": "Fact 4",
                            "properties": {},
                        },
                    ],
                    "path_length": 4,
                }
            ]
        )

        # Mock source extraction
        paths_tool._extract_source_from_episode = AsyncMock(return_value=None)

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="Target", max_path_length=6)

        # Assert
        assert "### Path 1 (4 hops)" in result
        assert all(node in result for node in ["Meta", "Node2", "Node3", "Node4", "Target"])

    @pytest.mark.asyncio
    async def test_arun_with_summary_sections(self, paths_tool):
        """Test _arun includes proper summary sections."""
        # Mock _find_entity_node
        async def mock_find(entity_name):
            if entity_name == "Meta":
                return {"uuid": "meta-uuid", "name": "Meta", "labels": ["Entity", "Company"]}
            elif entity_name == "EU":
                return {"uuid": "eu-uuid", "name": "EU", "labels": ["Entity", "Organization"]}
            return None

        paths_tool._find_entity_node = AsyncMock(side_effect=mock_find)

        # Mock _find_paths_cypher
        paths_tool._find_paths_cypher = AsyncMock(
            return_value=[
                {
                    "path_nodes": [
                        {"uuid": "meta-uuid", "name": "Meta", "types": ["Entity", "Company"]},
                        {"uuid": "dsa-uuid", "name": "EU DSA", "types": ["Entity", "Policy"]},
                        {"uuid": "eu-uuid", "name": "EU", "types": ["Entity", "Organization"]},
                    ],
                    "path_relationships": [
                        {
                            "type": "SUBJECT_TO",
                            "source_name": "Meta",
                            "target_name": "EU DSA",
                            "fact": "Meta subject to DSA",
                            "properties": {"created_at": "2024-01-15"},
                        },
                        {
                            "type": "ENFORCED_BY",
                            "source_name": "EU DSA",
                            "target_name": "EU",
                            "fact": "DSA enforced by EU",
                            "properties": {},
                        },
                    ],
                    "path_length": 2,
                }
            ]
        )

        # Mock source extraction
        paths_tool._extract_source_from_episode = AsyncMock(
            return_value={"url": "https://example.com", "title": "Source doc", "date": "20240115"}
        )

        # Execute
        result = await paths_tool._arun(source_entity="Meta", target_entity="EU")

        # Assert summary sections
        assert "## Summary" in result
        assert "### Entities Found" in result
        assert "Meta" in result
        assert "EU DSA" in result
        assert "### Relationships Discovered" in result
        assert "SUBJECT_TO" in result
        assert "ENFORCED_BY" in result
        assert "### Temporal Aspects" in result
        assert "2024-01-15" in result
