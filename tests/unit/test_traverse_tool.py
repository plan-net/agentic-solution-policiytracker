"""Unit tests for traverse_from_entity tool with real Neo4j graph traversal."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.chat.tools.traverse import TraverseFromEntityTool


class TestTraverseFromEntityTool:
    """Test suite for TraverseFromEntityTool with Cypher-based traversal."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client with driver."""
        client = MagicMock()
        client.driver = MagicMock()
        return client

    @pytest.fixture
    def traverse_tool(self, mock_graphiti_client):
        """Create TraverseFromEntityTool instance with mock client."""
        return TraverseFromEntityTool(graphiti_client=mock_graphiti_client)

    @pytest.mark.asyncio
    async def test_find_entity_node_success(self, traverse_tool, mock_graphiti_client):
        """Test successful entity node finding."""
        # Mock Neo4j session and result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "uuid": "entity-123-uuid",
                    "name": "Meta",
                    "labels": ["Entity", "Company"],
                    "properties": {"type": "Company", "name": "Meta"},
                }
            ]
        )

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute
        result = await traverse_tool._find_entity_node("Meta")

        # Assert
        assert result is not None
        assert result["name"] == "Meta"
        assert result["uuid"] == "entity-123-uuid"
        assert "Company" in result["labels"]

        # Verify query was called with correct parameters
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MATCH (n:Entity)" in call_args[0][0]
        assert "toLower(n.name) CONTAINS toLower($entity_name)" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_entity_node_not_found(self, traverse_tool, mock_graphiti_client):
        """Test entity node not found."""
        # Mock empty result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute
        result = await traverse_tool._find_entity_node("NonexistentEntity")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_entity_node_handles_exception(self, traverse_tool, mock_graphiti_client):
        """Test error handling in entity node finding."""
        # Mock exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute
        result = await traverse_tool._find_entity_node("Meta")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_traverse_graph_cypher_success(self, traverse_tool, mock_graphiti_client):
        """Test successful Cypher graph traversal with ALL relationship types."""
        # Mock Neo4j session and result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "target_uuid": "entity-456-uuid",
                    "target_name": "EU Digital Services Act",
                    "target_types": ["Entity", "Policy"],
                    "relationship_chain": [
                        {
                            "type": "AFFECTS",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with the EU Digital Services Act",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
                {
                    "target_uuid": "entity-789-uuid",
                    "target_name": "Google",
                    "target_types": ["Entity", "Company"],
                    "relationship_chain": [
                        {
                            "type": "COMPETES_WITH",
                            "source_name": "Meta",
                            "target_name": "Google",
                            "fact": "Meta and Google compete in the digital advertising market",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
            ]
        )

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute (no relationship_types parameter - gets all)
        results = await traverse_tool._traverse_graph_cypher(
            entity_uuid="entity-123-uuid", max_depth=2, max_results=50
        )

        # Assert
        assert len(results) == 2
        assert results[0]["target_name"] == "EU Digital Services Act"
        assert results[0]["depth"] == 1
        assert results[1]["target_name"] == "Google"

        # Verify query was called with correct parameters (no relationship type filter)
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "MATCH path =" in query
        assert "start:Entity" in query
        assert "$entity_uuid" in query
        assert params["entity_uuid"] == "entity-123-uuid"
        assert params["max_results"] == 50
        # Verify NO relationship type filter in query
        assert "WHERE all(r IN relationships(path)" not in query

    @pytest.mark.asyncio
    async def test_traverse_graph_cypher_gets_all_relationship_types(
        self, traverse_tool, mock_graphiti_client
    ):
        """Test that Cypher traversal returns ALL relationship types (no filtering)."""
        # Mock Neo4j session and result with different relationship types
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "target_uuid": "entity-456-uuid",
                    "target_name": "EU Digital Services Act",
                    "target_types": ["Entity", "Policy"],
                    "relationship_chain": [
                        {
                            "type": "AFFECTS",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with the EU Digital Services Act",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
                {
                    "target_uuid": "entity-789-uuid",
                    "target_name": "Google",
                    "target_types": ["Entity", "Company"],
                    "relationship_chain": [
                        {
                            "type": "COMPETES_WITH",
                            "source_name": "Meta",
                            "target_name": "Google",
                            "fact": "Meta and Google compete",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
            ]
        )

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute - should get ALL relationship types
        results = await traverse_tool._traverse_graph_cypher(
            entity_uuid="entity-123-uuid",
            max_depth=2,
            max_results=50,
        )

        # Assert - both different relationship types are returned
        assert len(results) == 2
        rel_types = {r["relationship_chain"][0]["type"] for r in results}
        assert "AFFECTS" in rel_types
        assert "COMPETES_WITH" in rel_types

        # Verify query does NOT include relationship type filter
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "WHERE all(r IN relationships(path)" not in query
        assert "$relationship_types" not in query

    @pytest.mark.asyncio
    async def test_traverse_graph_cypher_empty_result(self, traverse_tool, mock_graphiti_client):
        """Test Cypher traversal with no results."""
        # Mock empty result
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute
        results = await traverse_tool._traverse_graph_cypher(
            entity_uuid="entity-123-uuid", max_depth=2, max_results=50
        )

        # Assert
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_traverse_graph_cypher_handles_exception(
        self, traverse_tool, mock_graphiti_client
    ):
        """Test error handling in Cypher traversal."""
        # Mock exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j query error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_graphiti_client.driver.session = MagicMock(return_value=mock_session)

        # Execute
        results = await traverse_tool._traverse_graph_cypher(
            entity_uuid="entity-123-uuid", max_depth=2, max_results=50
        )

        # Assert - should return empty list on error
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_arun_entity_not_found(self, traverse_tool):
        """Test _arun when entity is not found."""
        # Mock _find_entity_node to return None
        traverse_tool._find_entity_node = AsyncMock(return_value=None)

        # Execute
        result = await traverse_tool._arun(entity_name="NonexistentEntity", max_depth=2)

        # Assert
        assert "❌ Entity 'NonexistentEntity' not found" in result
        assert "Suggestions:" in result

    @pytest.mark.asyncio
    async def test_arun_success_with_results(self, traverse_tool):
        """Test _arun with successful traversal results."""
        # Mock _find_entity_node
        traverse_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
                "properties": {},
            }
        )

        # Mock _traverse_graph_cypher
        traverse_tool._traverse_graph_cypher = AsyncMock(
            return_value=[
                {
                    "target_uuid": "entity-456-uuid",
                    "target_name": "EU Digital Services Act",
                    "target_types": ["Entity", "Policy"],
                    "relationship_chain": [
                        {
                            "type": "AFFECTS",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with the EU Digital Services Act",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
                {
                    "target_uuid": "entity-789-uuid",
                    "target_name": "Google",
                    "target_types": ["Entity", "Company"],
                    "relationship_chain": [
                        {
                            "type": "COMPETES_WITH",
                            "source_name": "Meta",
                            "target_name": "Google",
                            "fact": "Meta and Google compete",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                },
            ]
        )

        # Execute
        result = await traverse_tool._arun(entity_name="Meta", max_depth=2, max_results=15)

        # Assert - check for new format with relevance filtering
        assert "## Relationship Traversal from: Meta" in result
        assert "**Traversal Depth**: 2 levels" in result
        assert "**Total Entities Found**: 2 (showing top 2 most relevant)" in result
        assert "**Relevance Filtering**: Applied intelligent scoring" in result
        assert "EU Digital Services Act" in result
        assert "Google" in result
        assert "Level 1 Connections" in result
        assert "AFFECTS" in result
        assert "COMPETES_WITH" in result

    @pytest.mark.asyncio
    async def test_arun_no_connections_found(self, traverse_tool):
        """Test _arun when no connections are found."""
        # Mock _find_entity_node
        traverse_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Isolated Entity",
                "labels": ["Entity"],
                "properties": {},
            }
        )

        # Mock _traverse_graph_cypher to return empty
        traverse_tool._traverse_graph_cypher = AsyncMock(return_value=[])

        # Execute
        result = await traverse_tool._arun(entity_name="Isolated Entity", max_depth=2)

        # Assert
        assert "## Relationship Traversal from: Isolated Entity" in result
        assert "❌ No connections found within 2 hops" in result
        assert "Suggestions:" in result

    @pytest.mark.asyncio
    async def test_arun_with_relationship_filter(self, traverse_tool):
        """Test _arun with relationship type filter (parameter now ignored - backwards compatibility)."""
        # Mock _find_entity_node
        traverse_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity"],
                "properties": {},
            }
        )

        # Mock _traverse_graph_cypher (returns multiple results for filtering)
        raw_results = [
            {
                "target_uuid": "entity-456-uuid",
                "target_name": "EU Digital Services Act",
                "target_types": ["Entity", "Policy"],
                "relationship_chain": [
                    {
                        "type": "AFFECTS",
                        "source_name": "Meta",
                        "target_name": "EU Digital Services Act",
                        "fact": "Meta must comply",
                        "properties": {},
                    }
                ],
                "depth": 1,
            },
            {
                "target_uuid": "entity-789-uuid",
                "target_name": "Google",
                "target_types": ["Entity", "Company"],
                "relationship_chain": [
                    {
                        "type": "COMPETES_WITH",
                        "source_name": "Meta",
                        "target_name": "Google",
                        "fact": "Digital advertising market competition",
                        "properties": {},
                    }
                ],
                "depth": 1,
            },
        ]
        traverse_tool._traverse_graph_cypher = AsyncMock(return_value=raw_results)

        # Mock _apply_relevance_filtering to return filtered results
        filtered_results = [raw_results[0]]  # Return only first result (highest relevance)
        traverse_tool._apply_relevance_filtering = MagicMock(return_value=filtered_results)

        # Execute with relationship filter (parameter accepted but ignored)
        result = await traverse_tool._arun(
            entity_name="Meta", max_depth=2, relationship_types=["AFFECTS", "REGULATES"]
        )

        # Assert - check for new relevance filtering format (NOT old relationship filter)
        assert "**Relevance Filtering**: Applied intelligent scoring" in result
        assert "EU Digital Services Act" in result
        assert "**Total Entities Found**: 2 (showing top 1 most relevant)" in result

        # Verify relationship filter message is NOT present (deprecated feature)
        assert "**Relationship Filter**" not in result

        # Verify _traverse_graph_cypher was called WITHOUT relationship_types (gets all)
        traverse_tool._traverse_graph_cypher.assert_called_once_with(
            entity_uuid="entity-123-uuid",
            max_depth=2,
            max_results=45,  # 15 * 3 for relevance filtering
        )

        # Verify _apply_relevance_filtering was called
        traverse_tool._apply_relevance_filtering.assert_called_once_with(
            raw_results, "Meta", max_final_results=15
        )

    @pytest.mark.asyncio
    async def test_arun_handles_exception(self, traverse_tool):
        """Test _arun error handling."""
        # Mock _find_entity_node to raise exception
        traverse_tool._find_entity_node = AsyncMock(side_effect=Exception("Test error"))

        # Execute
        result = await traverse_tool._arun(entity_name="Meta", max_depth=2)

        # Assert
        assert "❌ Error traversing from Meta" in result
        assert "Test error" in result

    @pytest.mark.asyncio
    async def test_arun_multi_level_traversal(self, traverse_tool):
        """Test _arun with multi-level traversal results."""
        # Mock _find_entity_node
        traverse_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity"],
                "properties": {},
            }
        )

        # Mock _traverse_graph_cypher with multi-level results
        raw_results = [
            {
                "target_uuid": "entity-456-uuid",
                "target_name": "EU Digital Services Act",
                "target_types": ["Entity", "Policy"],
                "relationship_chain": [
                    {
                        "type": "AFFECTS",
                        "source_name": "Meta",
                        "target_name": "EU Digital Services Act",
                        "fact": "Meta must comply",
                        "properties": {},
                    }
                ],
                "depth": 1,
            },
            {
                "target_uuid": "entity-789-uuid",
                "target_name": "European Commission",
                "target_types": ["Entity", "Organization"],
                "relationship_chain": [
                    {
                        "type": "AFFECTS",
                        "source_name": "Meta",
                        "target_name": "EU Digital Services Act",
                        "fact": "Meta must comply",
                        "properties": {},
                    },
                    {
                        "type": "ENFORCES",
                        "source_name": "EU Digital Services Act",
                        "target_name": "European Commission",
                        "fact": "EC enforces DSA",
                        "properties": {},
                    },
                ],
                "depth": 2,
            },
        ]
        traverse_tool._traverse_graph_cypher = AsyncMock(return_value=raw_results)

        # Mock _apply_relevance_filtering to return all results (sorted by relevance)
        traverse_tool._apply_relevance_filtering = MagicMock(return_value=raw_results)

        # Execute
        result = await traverse_tool._arun(entity_name="Meta", max_depth=3)

        # Assert - check for new format
        assert "**Total Entities Found**: 2 (showing top 2 most relevant)" in result
        assert "**Relevance Filtering**: Applied intelligent scoring" in result
        assert "Level 1 Connections" in result
        assert "Level 2 Connections" in result
        assert "EU Digital Services Act" in result
        assert "European Commission" in result
        assert "AFFECTS" in result
        assert "ENFORCES" in result
