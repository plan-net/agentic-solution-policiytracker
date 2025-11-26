"""Unit tests for GetNeighborsTool (Tool 7)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.chat.tools.traverse import GetNeighborsTool


class TestGetNeighborsTool:
    """Test suite for GetNeighborsTool with Cypher-based neighbor discovery."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        client = MagicMock()
        client.driver = MagicMock()
        return client

    @pytest.fixture
    def neighbors_tool(self, mock_graphiti_client):
        """Create GetNeighborsTool instance with mock client."""
        return GetNeighborsTool(graphiti_client=mock_graphiti_client)

    # Tests for _find_entity_node

    @pytest.mark.asyncio
    async def test_find_entity_node_success(self, neighbors_tool, mock_graphiti_client):
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
        result = await neighbors_tool._find_entity_node("Meta")

        # Assert
        assert result is not None
        assert result["uuid"] == "entity-123-uuid"
        assert result["name"] == "Meta"
        assert "Company" in result["labels"]

        # Verify query was executed
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        query = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        params = (
            call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("params", {})
        )
        assert "MATCH (n:Entity)" in query
        assert params.get("entity_name") == "Meta"

    @pytest.mark.asyncio
    async def test_find_entity_node_not_found(self, neighbors_tool, mock_graphiti_client):
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
        result = await neighbors_tool._find_entity_node("NonExistentEntity")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_entity_node_handles_exception(self, neighbors_tool, mock_graphiti_client):
        """Test _find_entity_node handles exceptions gracefully."""
        # Mock session to raise exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        result = await neighbors_tool._find_entity_node("Meta")

        # Assert - should return None on error
        assert result is None

    # Tests for _get_neighbors_cypher

    @pytest.mark.asyncio
    async def test_get_neighbors_cypher_success(self, neighbors_tool, mock_graphiti_client):
        """Test successful neighbor discovery via Cypher."""
        # Mock Neo4j session for both outgoing and incoming queries
        mock_session = AsyncMock()

        # Mock outgoing results
        mock_outgoing_result = AsyncMock()
        mock_outgoing_result.data = AsyncMock(
            return_value=[
                {
                    "neighbor_uuid": "neighbor-1-uuid",
                    "neighbor_name": "EU Digital Services Act",
                    "neighbor_types": ["Entity", "Policy"],
                    "relationship_chain": [
                        {
                            "type": "SUBJECT_TO",
                            "source_name": "Meta",
                            "target_name": "EU Digital Services Act",
                            "fact": "Meta must comply with DSA requirements",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                }
            ]
        )

        # Mock incoming results
        mock_incoming_result = AsyncMock()
        mock_incoming_result.data = AsyncMock(
            return_value=[
                {
                    "neighbor_uuid": "neighbor-2-uuid",
                    "neighbor_name": "European Commission",
                    "neighbor_types": ["Entity", "Organization"],
                    "relationship_chain": [
                        {
                            "type": "ENFORCES",
                            "source_name": "European Commission",
                            "target_name": "Meta",
                            "fact": "Commission enforces regulations on Meta",
                            "properties": {},
                        }
                    ],
                    "depth": 1,
                }
            ]
        )

        # Track call count to return different results for outgoing/incoming
        call_count = [0]

        async def mock_run(query, params):
            call_count[0] += 1
            # First call = outgoing query, second call = incoming query
            if call_count[0] == 1:
                return mock_outgoing_result
            else:
                return mock_incoming_result

        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await neighbors_tool._get_neighbors_cypher(
            entity_uuid="entity-123-uuid", max_depth=1, max_results=50
        )

        # Assert
        assert "outgoing" in results
        assert "incoming" in results
        assert len(results["outgoing"]) == 1
        assert len(results["incoming"]) == 1

        # Verify outgoing neighbor
        assert results["outgoing"][0]["neighbor_name"] == "EU Digital Services Act"
        assert "SUBJECT_TO" == results["outgoing"][0]["relationship_chain"][0]["type"]

        # Verify incoming neighbor
        assert results["incoming"][0]["neighbor_name"] == "European Commission"
        assert "ENFORCES" == results["incoming"][0]["relationship_chain"][0]["type"]

        # Verify both queries were executed
        assert mock_session.run.call_count == 2

    @pytest.mark.asyncio
    async def test_get_neighbors_cypher_empty_result(self, neighbors_tool, mock_graphiti_client):
        """Test _get_neighbors_cypher with no neighbors found."""
        # Mock Neo4j session with empty results
        mock_session = AsyncMock()
        mock_empty_result = AsyncMock()
        mock_empty_result.data = AsyncMock(return_value=[])

        mock_session.run = AsyncMock(return_value=mock_empty_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await neighbors_tool._get_neighbors_cypher(
            entity_uuid="entity-123-uuid", max_depth=1, max_results=50
        )

        # Assert
        assert results["outgoing"] == []
        assert results["incoming"] == []

    @pytest.mark.asyncio
    async def test_get_neighbors_cypher_handles_exception(
        self, neighbors_tool, mock_graphiti_client
    ):
        """Test _get_neighbors_cypher handles exceptions gracefully."""
        # Mock session to raise exception
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j query error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_graphiti_client.driver.session.return_value = mock_session

        # Execute
        results = await neighbors_tool._get_neighbors_cypher(
            entity_uuid="entity-123-uuid", max_depth=1, max_results=50
        )

        # Assert - should return empty dicts on error
        assert results["outgoing"] == []
        assert results["incoming"] == []

    # Tests for _arun

    @pytest.mark.asyncio
    async def test_arun_entity_not_found(self, neighbors_tool):
        """Test _arun when entity is not found."""
        # Mock _find_entity_node to return None
        neighbors_tool._find_entity_node = AsyncMock(return_value=None)

        # Execute
        result = await neighbors_tool._arun(entity_name="NonExistent")

        # Assert
        assert "not found" in result
        assert "NonExistent" in result

    @pytest.mark.asyncio
    async def test_arun_success_with_neighbors(self, neighbors_tool):
        """Test _arun with successful neighbor discovery."""
        # Mock _find_entity_node
        neighbors_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
            }
        )

        # Mock _get_neighbors_cypher
        neighbors_tool._get_neighbors_cypher = AsyncMock(
            return_value={
                "outgoing": [
                    {
                        "neighbor_uuid": "neighbor-1-uuid",
                        "neighbor_name": "EU Digital Services Act",
                        "neighbor_types": ["Entity", "Policy"],
                        "relationship_chain": [
                            {
                                "type": "SUBJECT_TO",
                                "source_name": "Meta",
                                "target_name": "EU Digital Services Act",
                                "fact": "Meta must comply with DSA requirements",
                                "properties": {},
                            }
                        ],
                        "depth": 1,
                    }
                ],
                "incoming": [
                    {
                        "neighbor_uuid": "neighbor-2-uuid",
                        "neighbor_name": "European Commission",
                        "neighbor_types": ["Entity", "Organization"],
                        "relationship_chain": [
                            {
                                "type": "ENFORCES",
                                "source_name": "European Commission",
                                "target_name": "Meta",
                                "fact": "Commission enforces regulations on Meta",
                                "properties": {},
                            }
                        ],
                        "depth": 1,
                    }
                ],
            }
        )

        # Mock source extraction
        neighbors_tool._extract_source_from_episode = AsyncMock(return_value=None)

        # Execute
        result = await neighbors_tool._arun(entity_name="Meta", max_depth=1)

        # Assert
        assert "Neighbors of: Meta" in result
        assert "**Total Neighbors Found**: 2 (1 outgoing, 1 incoming)" in result
        assert "Outgoing Relationships (1 neighbors)" in result
        assert "Incoming Relationships (1 neighbors)" in result
        assert "EU Digital Services Act" in result
        assert "European Commission" in result
        assert "SUBJECT_TO" in result
        assert "ENFORCES" in result

        # Verify summary sections
        assert "## Summary" in result
        assert "### Entities Found" in result
        assert "### Relationships Discovered" in result

    @pytest.mark.asyncio
    async def test_arun_no_neighbors_found(self, neighbors_tool):
        """Test _arun when no neighbors are found."""
        # Mock _find_entity_node
        neighbors_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
            }
        )

        # Mock _get_neighbors_cypher to return empty results
        neighbors_tool._get_neighbors_cypher = AsyncMock(
            return_value={"outgoing": [], "incoming": []}
        )

        # Execute
        result = await neighbors_tool._arun(entity_name="Meta")

        # Assert
        assert "Neighbors of: Meta" in result
        assert "No direct neighbors found" in result

    @pytest.mark.asyncio
    async def test_arun_with_neighbor_types_deprecated(self, neighbors_tool):
        """Test _arun with neighbor_types parameter (now deprecated)."""
        # Mock _find_entity_node
        neighbors_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
            }
        )

        # Mock _get_neighbors_cypher
        neighbors_tool._get_neighbors_cypher = AsyncMock(
            return_value={
                "outgoing": [
                    {
                        "neighbor_uuid": "neighbor-1-uuid",
                        "neighbor_name": "EU Digital Services Act",
                        "neighbor_types": ["Entity", "Policy"],
                        "relationship_chain": [
                            {
                                "type": "SUBJECT_TO",
                                "source_name": "Meta",
                                "target_name": "EU Digital Services Act",
                                "fact": "Meta must comply with DSA requirements",
                                "properties": {},
                            }
                        ],
                        "depth": 1,
                    }
                ],
                "incoming": [],
            }
        )

        # Mock source extraction
        neighbors_tool._extract_source_from_episode = AsyncMock(return_value=None)

        # Execute with neighbor_types (should be ignored)
        result = await neighbors_tool._arun(
            entity_name="Meta", max_depth=1, neighbor_types=["Policy", "Regulation"]
        )

        # Assert - neighbor_types parameter is accepted but ignored
        # Result should still contain ALL neighbors regardless of types
        assert "Neighbors of: Meta" in result
        assert "EU Digital Services Act" in result

        # Verify _get_neighbors_cypher was called without neighbor type filtering
        neighbors_tool._get_neighbors_cypher.assert_called_once()
        call_args = neighbors_tool._get_neighbors_cypher.call_args
        assert "max_depth" in call_args[1]
        # No neighbor_types filtering in Cypher query

    @pytest.mark.asyncio
    async def test_arun_handles_exception(self, neighbors_tool):
        """Test _arun handles exceptions gracefully."""
        # Mock _find_entity_node to raise exception
        neighbors_tool._find_entity_node = AsyncMock(side_effect=Exception("Database error"))

        # Execute
        result = await neighbors_tool._arun(entity_name="Meta")

        # Assert
        assert "Error getting neighbors" in result
        assert "Database error" in result

    @pytest.mark.asyncio
    async def test_arun_with_max_depth_2(self, neighbors_tool):
        """Test _arun with max_depth=2."""
        # Mock _find_entity_node
        neighbors_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
            }
        )

        # Mock _get_neighbors_cypher with depth 2 neighbors
        neighbors_tool._get_neighbors_cypher = AsyncMock(
            return_value={
                "outgoing": [
                    {
                        "neighbor_uuid": "neighbor-1-uuid",
                        "neighbor_name": "EU Digital Services Act",
                        "neighbor_types": ["Entity", "Policy"],
                        "relationship_chain": [
                            {
                                "type": "SUBJECT_TO",
                                "source_name": "Meta",
                                "target_name": "Intermediate",
                                "fact": "Meta → Intermediate",
                                "properties": {},
                            },
                            {
                                "type": "REQUIRES_COMPLIANCE",
                                "source_name": "Intermediate",
                                "target_name": "EU Digital Services Act",
                                "fact": "Intermediate → DSA",
                                "properties": {},
                            },
                        ],
                        "depth": 2,
                    }
                ],
                "incoming": [],
            }
        )

        # Mock source extraction
        neighbors_tool._extract_source_from_episode = AsyncMock(return_value=None)

        # Execute
        result = await neighbors_tool._arun(entity_name="Meta", max_depth=2)

        # Assert
        assert "**Search Depth**: 2 hop(s)" in result
        assert "SUBJECT_TO → REQUIRES_COMPLIANCE" in result

    @pytest.mark.asyncio
    async def test_arun_with_summary_sections(self, neighbors_tool):
        """Test _arun includes proper summary sections."""
        # Mock _find_entity_node
        neighbors_tool._find_entity_node = AsyncMock(
            return_value={
                "uuid": "entity-123-uuid",
                "name": "Meta",
                "labels": ["Entity", "Company"],
            }
        )

        # Mock _get_neighbors_cypher
        neighbors_tool._get_neighbors_cypher = AsyncMock(
            return_value={
                "outgoing": [
                    {
                        "neighbor_uuid": "neighbor-1-uuid",
                        "neighbor_name": "EU DSA",
                        "neighbor_types": ["Entity", "Policy"],
                        "relationship_chain": [
                            {
                                "type": "SUBJECT_TO",
                                "source_name": "Meta",
                                "target_name": "EU DSA",
                                "fact": "Meta subject to DSA",
                                "properties": {"created_at": "2024-01-15"},
                            }
                        ],
                        "depth": 1,
                    }
                ],
                "incoming": [],
            }
        )

        # Mock source extraction
        neighbors_tool._extract_source_from_episode = AsyncMock(
            return_value={"url": "https://example.com", "title": "Source doc", "date": "20240115"}
        )

        # Execute
        result = await neighbors_tool._arun(entity_name="Meta")

        # Assert summary sections
        assert "## Summary" in result
        assert "### Entities Found" in result
        assert "EU DSA" in result
        assert "### Relationships Discovered" in result
        assert "SUBJECT_TO" in result
        assert "### Temporal Aspects" in result
        assert "2024-01-15" in result
